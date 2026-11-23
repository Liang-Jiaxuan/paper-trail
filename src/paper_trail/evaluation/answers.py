"""用已有的重排前 5 条写评测概括句。不改 last_answer.json，也不重跑检索。"""

from paper_trail.generation.answer import build_answer
from paper_trail.indexing.bm25 import documents_from_chunks
from paper_trail.indexing.rerank import decide_refusal


def chunks_by_id(chunks_dir) -> dict[str, dict]:
    """chunk_id 到块。正文和 sha256 从分块文件取。"""
    _version, documents = documents_from_chunks(chunks_dir)
    return {document["chunk_id"]: document for document in documents}


def prepare_answer(question: dict, chunks: dict[str, dict]) -> dict:
    """补上正文后按最高 vec_score 决定是否拒答。未拒答时 answer 仍是 None。"""
    hits = []
    for hit in question["hits"]:
        chunk = chunks.get(hit["chunk_id"])
        if chunk is None:
            raise KeyError(hit["chunk_id"])
        row = dict(hit)
        row["sha256"] = chunk["sha256"]
        row["text"] = chunk["text"]
        hits.append(row)
    gate = decide_refusal(hits)
    payload = {
        "query": question["query"],
        "refused": gate["refused"],
        "threshold": gate["threshold"],
        "vec_score_max": gate["vec_score_max"],
        "hits": hits,
    }
    answer = {"id": question["id"], "retrieval_hit": question["hit"]}
    answer.update(build_answer(payload))
    return answer
