"""把重排结果整理成引用。不调用模型，也不改重排文件。"""

REFUSAL_ANSWER = "没有足够相近的段落，无法回答。"

CITATION_FIELDS = (
    "rank",
    "chunk_id",
    "paper_id",
    "sha256",
    "section_path",
    "start_page",
    "end_page",
    "text",
    "vec_score",
    "rerank_score",
)


def build_answer(payload: dict) -> dict:
    """未拒答时 answer 为 None。拒答时用固定句子，引用仍保留。"""
    citations = [{key: hit[key] for key in CITATION_FIELDS} for hit in payload["hits"]]
    return {
        "query": payload["query"],
        "refused": payload["refused"],
        "threshold": payload["threshold"],
        "vec_score_max": payload["vec_score_max"],
        "answer": REFUSAL_ANSWER if payload["refused"] else None,
        "citations": citations,
    }
