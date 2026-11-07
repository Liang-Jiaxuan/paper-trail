"""建索引，或查一次。

python -m paper_trail.indexing
python -m paper_trail.indexing query "查询语句"
python -m paper_trail.indexing vectors
python -m paper_trail.indexing vectors query "查询语句"
python -m paper_trail.indexing rrf query "查询语句"
python -m paper_trail.indexing rrf query "查询语句" 50
python -m paper_trail.indexing rerank query "查询语句"
python -m paper_trail.indexing rerank query "查询语句" 50
"""

import json
import sys

from paper_trail import config
from paper_trail.indexing.bm25 import QUERY_TOP_K as BM25_TOP_K
from paper_trail.indexing.bm25 import load_index, search, write_index
from paper_trail.indexing.dense import QUERY_TOP_K as VECTOR_TOP_K
from paper_trail.indexing.dense import embed_texts, load_vector_index, search_vectors, write_vector_index
from paper_trail.indexing.rerank import MODEL_NAME as RERANK_MODEL_NAME
from paper_trail.indexing.rerank import QUERY_TOP_K as RERANK_TOP_K
from paper_trail.indexing.rerank import MAX_LENGTH as RERANK_MAX_LENGTH
from paper_trail.indexing.rerank import apply_rerank, decide_refusal, score_pairs
from paper_trail.indexing.rrf import QUERY_TOP_K as RRF_TOP_K
from paper_trail.indexing.rrf import RRF_K, candidate_k_from_arg, fuse

_USAGE = """用法:
  python -m paper_trail.indexing
  python -m paper_trail.indexing query "查询语句"
  python -m paper_trail.indexing vectors
  python -m paper_trail.indexing vectors query "查询语句"
  python -m paper_trail.indexing rrf query "查询语句"
  python -m paper_trail.indexing rrf query "查询语句" 50
  python -m paper_trail.indexing rerank query "查询语句"
  python -m paper_trail.indexing rerank query "查询语句" 50\""""


def _write_query(path, query: str, top_k: int, hits: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"query": query, "top_k": top_k, "hits": hits}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"写入 {len(hits)} 条到 {path}")


def main(argv: list[str] | None = None) -> None:
    """无参数时写 BM25。vectors 写稠密向量索引。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        payload = write_index(config.CHUNKS_DIR, config.BM25_INDEX_PATH)
        print(f"写入 {len(payload['documents'])} 块到 {config.BM25_INDEX_PATH}")
        return
    if len(args) == 2 and args[0] == "query":
        if not config.BM25_INDEX_PATH.is_file():
            raise SystemExit(f"找不到 BM25 索引：{config.BM25_INDEX_PATH}")
        hits = search(load_index(config.BM25_INDEX_PATH), args[1], BM25_TOP_K)
        _write_query(config.BM25_QUERY_PATH, args[1], BM25_TOP_K, hits)
        for hit in hits:
            print(f"{hit['rank']}  {hit['bm25_score']:.4f}  {hit['chunk_id']}  p{hit['start_page']}-{hit['end_page']}")
        return
    if args == ["vectors"]:
        payload = write_vector_index(
            config.CHUNKS_DIR,
            config.VECTOR_INDEX_PATH,
            config.VECTOR_MATRIX_PATH,
            config.BGE_M3_DIR,
        )
        print(f"写入 {len(payload['documents'])} 块到 {config.VECTOR_INDEX_PATH}")
        return
    if len(args) == 3 and args[0] == "vectors" and args[1] == "query":
        if not config.VECTOR_INDEX_PATH.is_file():
            raise SystemExit(f"找不到向量索引：{config.VECTOR_INDEX_PATH}")
        index, vectors = load_vector_index(config.VECTOR_INDEX_PATH, config.VECTOR_MATRIX_PATH)
        query_vector = embed_texts([args[2]], config.BGE_M3_DIR, batch_size=1)[0]
        hits = search_vectors(vectors, index["documents"], query_vector, VECTOR_TOP_K)
        _write_query(config.VECTOR_QUERY_PATH, args[2], VECTOR_TOP_K, hits)
        for hit in hits:
            print(f"{hit['rank']}  {hit['vec_score']:.4f}  {hit['chunk_id']}  p{hit['start_page']}-{hit['end_page']}")
        return
    if args[:2] == ["rrf", "query"] and len(args) in (3, 4):
        try:
            candidate_k = candidate_k_from_arg(args[3] if len(args) == 4 else None)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if not config.BM25_INDEX_PATH.is_file():
            raise SystemExit(f"找不到 BM25 索引：{config.BM25_INDEX_PATH}")
        if not config.VECTOR_INDEX_PATH.is_file():
            raise SystemExit(f"找不到向量索引：{config.VECTOR_INDEX_PATH}")
        bm25_hits = search(load_index(config.BM25_INDEX_PATH), args[2], candidate_k)
        index, vectors = load_vector_index(config.VECTOR_INDEX_PATH, config.VECTOR_MATRIX_PATH)
        query_vector = embed_texts([args[2]], config.BGE_M3_DIR, batch_size=1)[0]
        vector_hits = search_vectors(vectors, index["documents"], query_vector, candidate_k)
        hits = fuse(bm25_hits, vector_hits, RRF_TOP_K)
        config.RRF_QUERY_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "query": args[2],
            "top_k": RRF_TOP_K,
            "candidate_k": candidate_k,
            "rrf_k": RRF_K,
            "hits": hits,
        }
        config.RRF_QUERY_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"写入 {len(hits)} 条到 {config.RRF_QUERY_PATH}")
        for hit in hits:
            bm25_rank = "-" if hit["bm25_rank"] is None else str(hit["bm25_rank"])
            vec_rank = "-" if hit["vec_rank"] is None else str(hit["vec_rank"])
            print(
                f"{hit['rank']}  {hit['rrf_score']:.6f}  bm25#{bm25_rank} vec#{vec_rank}  "
                f"{hit['chunk_id']}  p{hit['start_page']}-{hit['end_page']}"
            )
        return
    if args[:2] == ["rerank", "query"] and len(args) in (3, 4):
        try:
            candidate_k = candidate_k_from_arg(args[3] if len(args) == 4 else None)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if not config.BM25_INDEX_PATH.is_file():
            raise SystemExit(f"找不到 BM25 索引：{config.BM25_INDEX_PATH}")
        if not config.VECTOR_INDEX_PATH.is_file():
            raise SystemExit(f"找不到向量索引：{config.VECTOR_INDEX_PATH}")
        if not config.BGE_RERANKER_DIR.is_dir():
            raise SystemExit(f"找不到重排模型：{config.BGE_RERANKER_DIR}")
        bm25_hits = search(load_index(config.BM25_INDEX_PATH), args[2], candidate_k)
        index, vectors = load_vector_index(config.VECTOR_INDEX_PATH, config.VECTOR_MATRIX_PATH)
        query_vector = embed_texts([args[2]], config.BGE_M3_DIR, batch_size=1)[0]
        vector_hits = search_vectors(vectors, index["documents"], query_vector, candidate_k)
        fused = fuse(bm25_hits, vector_hits, len(bm25_hits) + len(vector_hits))
        del index, vectors, query_vector
        import gc

        import torch

        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        scores = score_pairs(args[2], fused, config.BGE_RERANKER_DIR)
        hits = apply_rerank(fused, scores, RERANK_TOP_K)
        gate = decide_refusal(hits)
        config.RERANK_QUERY_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "query": args[2],
            "top_k": RERANK_TOP_K,
            "candidate_k": candidate_k,
            "candidate_count": len(fused),
            "rrf_k": RRF_K,
            "model": RERANK_MODEL_NAME,
            "max_length": RERANK_MAX_LENGTH,
            "threshold": gate["threshold"],
            "vec_score_max": gate["vec_score_max"],
            "refused": gate["refused"],
            "hits": hits,
        }
        config.RERANK_QUERY_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"写入 {len(hits)} 条到 {config.RERANK_QUERY_PATH}")
        shown = "null" if gate["vec_score_max"] is None else f"{gate['vec_score_max']:.6f}"
        label = "拒答" if gate["refused"] else "放行"
        print(f"{label}  threshold={gate['threshold']}  vec_score_max={shown}")
        for hit in hits:
            print(
                f"{hit['rank']}  {hit['rerank_score']:.6f}  rrf#{hit['rrf_rank']}  "
                f"{hit['chunk_id']}  p{hit['start_page']}-{hit['end_page']}"
            )
        return
    raise SystemExit(_USAGE)


if __name__ == "__main__":
    main()
