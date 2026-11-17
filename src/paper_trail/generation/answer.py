"""把重排结果整理成引用，并在未拒答时请 deepseek-flash 写英文概括句。"""

REFUSAL_ANSWER = "No passage is close enough to answer."
MODEL_NAME = "deepseek-flash"
BASE_URL = "https://api.deepseek.com"
SYSTEM_PROMPT = (
    "Answer in English using only the passages. "
    "Copy numbers and technical terms as written. "
    "When you use a passage, mark it with its rank, like [1]. "
    "If the passages do not contain the answer, reply with exactly: "
    "No passage is close enough to answer."
)

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
    """未拒答时 answer 为 None。拒答时用固定句子，引用仍保留。不在这里请求模型。"""
    citations = [{key: hit[key] for key in CITATION_FIELDS} for hit in payload["hits"]]
    return {
        "query": payload["query"],
        "refused": payload["refused"],
        "threshold": payload["threshold"],
        "vec_score_max": payload["vec_score_max"],
        "model": None,
        "answer": REFUSAL_ANSWER if payload["refused"] else None,
        "citations": citations,
    }


def prompt_messages(query: str, citations: list[dict]) -> list[dict]:
    """只放名次、论文、页码和整段原文。不放检索分数。"""
    blocks = [
        f"[{item['rank']}] {item['paper_id']} p{item['start_page']}-{item['end_page']}\n{item['text']}"
        for item in citations
    ]
    passages = "\n\n".join(blocks)
    user = f"Passages:\n\n{passages}\n\nQuestion:\n{query}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def summary_text(content: str | None) -> str:
    """空内容不能当成概括句。"""
    if content is None or not content.strip():
        raise ValueError("模型返回的内容是空的")
    return content


def attach_summary(answer: dict, content: str) -> dict:
    """写入模型原文和模型名。不改 refused。"""
    updated = dict(answer)
    updated["answer"] = summary_text(content)
    updated["model"] = MODEL_NAME
    return updated


def request_summary(messages: list[dict], api_key: str) -> str:
    """请求一次 deepseek-flash。思考模式关闭。"""
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=BASE_URL, timeout=120.0)
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0,
        stream=False,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return summary_text(response.choices[0].message.content)
