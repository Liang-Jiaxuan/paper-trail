"""查询时把 BM25 和稠密向量的名次融在一起。不重建索引。"""

from paper_trail.indexing.bm25 import _FIELDS

RRF_K = 60
QUERY_TOP_K = 5
CANDIDATE_K = 50


def candidate_k_from_arg(text: str | None) -> int:
    """不传时用默认深度。传入的必须是正整数。"""
    if text is None:
        return CANDIDATE_K
    if not text.isdigit() or int(text) < 1:
        raise ValueError("候选深度要是正整数")
    return int(text)


def _term(rank: int) -> float:
    return 1.0 / (RRF_K + rank)


def _blank(hit: dict) -> dict:
    item = {key: hit[key] for key in _FIELDS}
    item["bm25_score"] = None
    item["bm25_rank"] = None
    item["vec_score"] = None
    item["vec_rank"] = None
    item["rrf_score"] = 0.0
    return item


def fuse(bm25_hits: list[dict], vector_hits: list[dict], top_k: int = QUERY_TOP_K) -> list[dict]:
    """按 1/(60+名次) 相加。某一路没有的分数和名次留空。"""
    merged: dict[str, dict] = {}
    order: list[str] = []

    def slot(hit: dict) -> dict:
        chunk_id = hit["chunk_id"]
        if chunk_id not in merged:
            merged[chunk_id] = _blank(hit)
            order.append(chunk_id)
        return merged[chunk_id]

    for hit in bm25_hits:
        item = slot(hit)
        item["bm25_score"] = hit["bm25_score"]
        item["bm25_rank"] = hit["rank"]
        item["rrf_score"] += _term(hit["rank"])
    for hit in vector_hits:
        item = slot(hit)
        item["vec_score"] = hit["vec_score"]
        item["vec_rank"] = hit["rank"]
        item["rrf_score"] += _term(hit["rank"])

    ranked = sorted(order, key=lambda chunk_id: -merged[chunk_id]["rrf_score"])
    hits = [merged[chunk_id] for chunk_id in ranked[:top_k]]
    for rank, hit in enumerate(hits, 1):
        hit["rank"] = rank
    return hits
