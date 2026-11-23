"""对评测题跑一次重排。不改 last_query.json，不调用概括模型。

python -m paper_trail.evaluation
"""

import gc
import json
import sys

from paper_trail import config
from paper_trail.evaluation.retrieval import question_result, retrieval_payload
from paper_trail.indexing.bm25 import load_index, search
from paper_trail.indexing.dense import embed_texts, load_embedder, load_vector_index, search_vectors
from paper_trail.indexing.rerank import QUERY_TOP_K, apply_rerank, load_reranker, score_pairs
from paper_trail.indexing.rrf import CANDIDATE_K, fuse


def main(argv: list[str] | None = None) -> None:
    """读 questions.json，全库重排，写入 retrieval.json。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        raise SystemExit("用法:\n  python -m paper_trail.evaluation")
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
