"""对评测题跑重排，按已有重排结果写概括句，或用 ragas 给概括句打分。

python -m paper_trail.evaluation
python -m paper_trail.evaluation answers
python -m paper_trail.evaluation ragas
"""

import gc
import json
import os
import sys

from paper_trail import config
from paper_trail.evaluation.answers import chunks_by_id, prepare_answer
from paper_trail.evaluation.ragas_eval import write_ragas
from paper_trail.evaluation.retrieval import question_result, retrieval_payload
from paper_trail.generation.answer import attach_number_checks, attach_summary, prompt_messages, request_summary
from paper_trail.indexing.bm25 import load_index, search
from paper_trail.indexing.dense import embed_texts, load_embedder, load_vector_index, search_vectors
from paper_trail.indexing.rerank import QUERY_TOP_K, apply_rerank, load_reranker, score_pairs
from paper_trail.indexing.rrf import CANDIDATE_K, fuse


def _write_answers() -> None:
    """读 retrieval.json，未拒答的题各请求一次模型，写入 answers.json。"""
    if not config.RETRIEVAL_PATH.is_file():
        raise SystemExit(f"找不到检索结果：{config.RETRIEVAL_PATH}")
    if not config.CHUNKS_DIR.is_dir():
        raise SystemExit(f"找不到分块目录：{config.CHUNKS_DIR}")
    retrieval = json.loads(config.RETRIEVAL_PATH.read_text(encoding="utf-8"))
    try:
        chunks = chunks_by_id(config.CHUNKS_DIR)
        prepared = [prepare_answer(question, chunks) for question in retrieval["questions"]]
    except (KeyError, FileNotFoundError) as exc:
        missing = exc.args[0] if isinstance(exc, KeyError) else exc
        raise SystemExit(f"找不到块：{missing}") from exc
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if any(not item["refused"] for item in prepared) and not api_key:
        raise SystemExit("请设置环境变量 DEEPSEEK_API_KEY")
    answers = []
    for item in prepared:
        if not item["refused"]:
            try:
                content = request_summary(prompt_messages(item["query"], item["citations"]), api_key)
                item = attach_summary(item, content)
            except Exception as exc:
                message = str(exc).replace(api_key, "***")
                raise SystemExit(f"概括句请求失败：{item['id']}：{message}") from exc
        item = attach_number_checks(item)
        answers.append(item)
        label = "拒答" if item["refused"] else "概括"
        print(f"{label}  {item['id']}")
        print(item["answer"])
        mark = "通过" if item["numbers_ok"] else "未通过"
        print(f"数字{mark}  {len(item['number_checks'])} 个")
    payload = {"question_version": retrieval["question_version"], "answers": answers}
    config.EVAL_ANSWERS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写入 {len(answers)} 条到 {config.EVAL_ANSWERS_PATH}")


def main(argv: list[str] | None = None) -> None:
    """无参数时重排。answers 时写概括句。ragas 时给已有概括句打分。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args == ["answers"]:
        _write_answers()
        return
    if args == ["ragas"]:
        write_ragas()
        return
    if args:
        raise SystemExit(
            "用法:\n"
            "  python -m paper_trail.evaluation\n"
            "  python -m paper_trail.evaluation answers\n"
            "  python -m paper_trail.evaluation ragas"
        )
    if not config.QUESTIONS_PATH.is_file():
        raise SystemExit(f"找不到评测题：{config.QUESTIONS_PATH}")
    if not config.BM25_INDEX_PATH.is_file():
        raise SystemExit(f"找不到 BM25 索引：{config.BM25_INDEX_PATH}")
    if not config.VECTOR_INDEX_PATH.is_file():
        raise SystemExit(f"找不到向量索引：{config.VECTOR_INDEX_PATH}")
    if not config.BGE_RERANKER_DIR.is_dir():
        raise SystemExit(f"找不到重排模型：{config.BGE_RERANKER_DIR}")

    questions_payload = json.loads(config.QUESTIONS_PATH.read_text(encoding="utf-8"))
    questions = questions_payload["questions"]
    bm25_index = load_index(config.BM25_INDEX_PATH)
    index, vectors = load_vector_index(config.VECTOR_INDEX_PATH, config.VECTOR_MATRIX_PATH)
    documents = index["documents"]
    embedder = load_embedder(config.BGE_M3_DIR)
    query_vectors = embed_texts(
        [question["query"] for question in questions],
        config.BGE_M3_DIR,
        model=embedder,
    )
    del embedder
    import torch

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    prepared = []
    for question, query_vector in zip(questions, query_vectors):
        bm25_hits = search(bm25_index, question["query"], CANDIDATE_K)
        vector_hits = search_vectors(vectors, documents, query_vector, CANDIDATE_K)
        prepared.append(fuse(bm25_hits, vector_hits, len(bm25_hits) + len(vector_hits)))
    del index, vectors, query_vectors, documents, bm25_index
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    reranker = load_reranker(config.BGE_RERANKER_DIR)
    results = []
    for question, fused in zip(questions, prepared):
        scores = score_pairs(question["query"], fused, config.BGE_RERANKER_DIR, model=reranker) if fused else []
        hits = apply_rerank(fused, scores, QUERY_TOP_K)
        item = question_result(question, hits)
        results.append(item)
        label = "命中" if item["hit"] else "未中"
        top = item["hits"][0]["chunk_id"] if item["hits"] else "-"
        print(f"{label}  {item['id']}  {top}")

    payload = retrieval_payload(questions_payload["question_version"], results)
    config.RETRIEVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.RETRIEVAL_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"命中 {payload['hit_count']}/{payload['question_count']}")
    print(f"写入 {config.RETRIEVAL_PATH}")


if __name__ == "__main__":
    main()
