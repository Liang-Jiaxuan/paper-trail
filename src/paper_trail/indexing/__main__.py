"""建 BM25 索引，或查一次：python -m paper_trail.indexing [query 查询语句]"""

import json
import sys

from paper_trail import config
from paper_trail.indexing.bm25 import QUERY_TOP_K, load_index, search, write_index

_USAGE = '用法: python -m paper_trail.indexing [query "查询语句"]'


def main(argv: list[str] | None = None) -> None:
    """无参数时写出索引。query 时把前 5 条写到 last_query.json。"""
    args = list(sys.argv[1:] if argv is None else argv)
    index_path = config.BM25_INDEX_PATH
    if not args:
        payload = write_index(config.CHUNKS_DIR, index_path)
        print(f"写入 {len(payload['documents'])} 块到 {index_path}")
        return
    if len(args) == 2 and args[0] == "query":
        if not index_path.is_file():
            raise SystemExit(f"找不到 BM25 索引：{index_path}")
        hits = search(load_index(index_path), args[1], QUERY_TOP_K)
        result = {"query": args[1], "top_k": QUERY_TOP_K, "hits": hits}
        query_path = config.BM25_QUERY_PATH
        query_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"写入 {len(hits)} 条到 {query_path}")
        for hit in hits:
            print(f"{hit['rank']}  {hit['bm25_score']:.4f}  {hit['chunk_id']}  p{hit['start_page']}-{hit['end_page']}")
        return
    raise SystemExit(_USAGE)


if __name__ == "__main__":
    main()
