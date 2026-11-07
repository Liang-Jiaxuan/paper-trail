"""建索引，或查一次。

python -m paper_trail.indexing
python -m paper_trail.indexing query "查询语句"
python -m paper_trail.indexing vectors
python -m paper_trail.indexing vectors query "查询语句"
"""

import json
import sys

from paper_trail import config
from paper_trail.indexing.bm25 import QUERY_TOP_K as BM25_TOP_K
from paper_trail.indexing.bm25 import load_index, search, write_index
from paper_trail.indexing.dense import QUERY_TOP_K as VECTOR_TOP_K
from paper_trail.indexing.dense import embed_texts, load_vector_index, search_vectors, write_vector_index

_USAGE = """用法:
  python -m paper_trail.indexing
  python -m paper_trail.indexing query "查询语句"
  python -m paper_trail.indexing vectors
  python -m paper_trail.indexing vectors query "查询语句\""""


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
    raise SystemExit(_USAGE)


if __name__ == "__main__":
    main()
