"""判断重排前 5 条是否命中评测题里的段落。不加载模型。"""

from paper_trail.indexing.rerank import MAX_LENGTH, MODEL_NAME, QUERY_TOP_K
from paper_trail.indexing.rrf import RRF_K, CANDIDATE_K

_HIT_FIELDS = (
    "rank",
    "rrf_rank",
    "chunk_id",
    "paper_id",
    "start_page",
    "end_page",
    "section_path",
    "bm25_score",
    "bm25_rank",
    "vec_score",
    "vec_rank",
    "rrf_score",
    "rerank_score",
)


def matched_passage_ids(hit: dict, passages: list[dict]) -> list[str]:
    """chunk_id 相同的出处。同一页上的其他块不算。"""
    return [passage["chunk_id"] for passage in passages if hit["chunk_id"] == passage["chunk_id"]]


def public_hit(hit: dict, passages: list[dict]) -> dict:
    """留下名次、分数和页码。不写块正文。"""
    row = {key: hit[key] for key in _HIT_FIELDS}
    row["matched"] = matched_passage_ids(hit, passages)
    return row


def question_result(question: dict, hits: list[dict]) -> dict:
    """前 5 条里出现任一处证据的 chunk_id，这道题算命中。"""
    rows = [public_hit(hit, question["passages"]) for hit in hits]
    return {
        "id": question["id"],
        "query": question["query"],
        "hit": any(row["matched"] for row in rows),
        "hits": rows,
    }


def retrieval_payload(question_version: int, results: list[dict]) -> dict:
    """一次评测的配置和每题结果。"""
    return {
        "question_version": question_version,
        "candidate_k": CANDIDATE_K,
        "top_k": QUERY_TOP_K,
        "paper_ids": None,
        "rrf_k": RRF_K,
        "model": MODEL_NAME,
        "max_length": MAX_LENGTH,
        "hit_count": sum(1 for item in results if item["hit"]),
        "question_count": len(results),
        "questions": results,
    }
