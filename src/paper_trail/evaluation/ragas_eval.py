"""用 ragas 0.4 给已有概括句打四项分数。

Faithfulness、Answer Relevancy、Context Precision、Context Recall。
不重跑检索，也不重写概括句。评判是 deepseek-v4-pro，向量是本地 bge-m3。
Context Precision 和 Context Recall 的参考答案是该题不重复的 evidence。
"""

import math

from paper_trail.indexing.dense import MODEL_NAME as EMBEDDING_MODEL

JUDGE_MODEL = "deepseek-v4-pro"
TEMPERATURE = 0
TOP_P = 0.1
MAX_TOKENS = 1024
STRICTNESS = 3


def stored_score(value) -> float | None:
    """NaN 写成 null。0 是分数，留下来。"""
    if value is None:
        return None
    number = float(value)
    if math.isnan(number):
        return None
    return number


def mean_score(values: list[float | None]) -> tuple[float | None, int]:
    """只平均有数字的题。返回值和分母。"""
    kept = [item for item in values if item is not None]
    if not kept:
        return None, 0
    return sum(kept) / len(kept), len(kept)


def citation_texts(answer: dict) -> list[str]:
    """按名次送出引用原文。不送分数。"""
    ordered = sorted(answer["citations"], key=lambda item: item["rank"])
    return [item["text"] for item in ordered]


def reference_text(question: dict) -> str:
    """按出处顺序留下不重复的 evidence。同一串字只留第一次。"""
    seen: list[str] = []
    for passage in question["passages"]:
        evidence = passage["evidence"]
        if evidence not in seen:
            seen.append(evidence)
    return "\n".join(seen)


def question_row(answer: dict, faithfulness, answer_relevancy, context_precision, context_recall) -> dict:
    """一题的四项分数。NaN 留 null。"""
    return {
        "id": answer["id"],
        "faithfulness": stored_score(faithfulness),
        "answer_relevancy": stored_score(answer_relevancy),
        "context_precision": stored_score(context_precision),
        "context_recall": stored_score(context_recall),
    }


def ragas_payload(question_version: int, rows: list[dict], ragas_version: str) -> dict:
    """加上版本、模型和平均分。平均分只算有数字的题。"""
    faithfulness_mean, faithfulness_count = mean_score([row["faithfulness"] for row in rows])
    answer_relevancy_mean, answer_relevancy_count = mean_score(
        [row["answer_relevancy"] for row in rows]
    )
    context_precision_mean, context_precision_count = mean_score(
        [row["context_precision"] for row in rows]
    )
    context_recall_mean, context_recall_count = mean_score([row["context_recall"] for row in rows])
    return {
        "question_version": question_version,
        "ragas_version": ragas_version,
        "judge_model": JUDGE_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": MAX_TOKENS,
        "thinking": "disabled",
        "strictness": STRICTNESS,
        "faithfulness_mean": faithfulness_mean,
        "faithfulness_count": faithfulness_count,
        "answer_relevancy_mean": answer_relevancy_mean,
        "answer_relevancy_count": answer_relevancy_count,
        "context_precision_mean": context_precision_mean,
        "context_precision_count": context_precision_count,
        "context_recall_mean": context_recall_mean,
        "context_recall_count": context_recall_count,
        "questions": rows,
    }


def write_ragas() -> None:
    """读 answers.json，请求评判模型，写入 ragas.json。失败时不写文件。"""
    import json
    import os

    os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

    from paper_trail import config
    from paper_trail.indexing.dense import load_embedder

    if not config.EVAL_ANSWERS_PATH.is_file():
        raise SystemExit(f"找不到概括句：{config.EVAL_ANSWERS_PATH}")
    if not config.QUESTIONS_PATH.is_file():
        raise SystemExit(f"找不到评测题：{config.QUESTIONS_PATH}")
    if not config.BGE_M3_DIR.is_dir():
        raise SystemExit(f"找不到嵌入模型：{config.BGE_M3_DIR}")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("请设置环境变量 DEEPSEEK_API_KEY")

    saved = json.loads(config.EVAL_ANSWERS_PATH.read_text(encoding="utf-8"))
    questions = json.loads(config.QUESTIONS_PATH.read_text(encoding="utf-8"))
    by_id = {question["id"]: question for question in questions["questions"]}
    missing = [answer["id"] for answer in saved["answers"] if answer["id"] not in by_id]
    if missing:
        raise SystemExit(f"找不到评测题：{', '.join(missing)}")
    answers = saved["answers"]
    embedder = load_embedder(config.BGE_M3_DIR)
    try:
        rows = _score_answers(answers, by_id, api_key, embedder)
    except Exception as exc:
        message = str(exc).replace(api_key, "***")
        raise SystemExit(f"RAGAS 打分失败：{message}") from exc
    finally:
        del embedder

    import ragas

    payload = ragas_payload(saved["question_version"], rows, ragas.__version__)
    config.RAGAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.RAGAS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Faithfulness {payload['faithfulness_mean']}  "
        f"{payload['faithfulness_count']} 题"
    )
    print(
        f"Answer Relevancy {payload['answer_relevancy_mean']}  "
        f"{payload['answer_relevancy_count']} 题"
    )
    print(
        f"Context Precision {payload['context_precision_mean']}  "
        f"{payload['context_precision_count']} 题"
    )
    print(
        f"Context Recall {payload['context_recall_mean']}  "
        f"{payload['context_recall_count']} 题"
    )
    print(f"写入 {config.RAGAS_PATH}")


def _score_answers(answers: list[dict], questions_by_id: dict, api_key: str, embedder) -> list[dict]:
    import asyncio

    from openai import AsyncOpenAI
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.llms import llm_factory
    from ragas.metrics.collections import AnswerRelevancy, ContextPrecision, ContextRecall, Faithfulness

    from paper_trail.indexing.dense import embed_texts

    class _BgeM3(BaseRagasEmbedding):
        def __init__(self, model):
            super().__init__()
            self.model = model

        def _vectors(self, texts: list[str]) -> list[list[float]]:
            from paper_trail import config

            array = embed_texts(list(texts), config.BGE_M3_DIR, model=self.model)
            return array.tolist()

        def embed_text(self, text: str, **kwargs) -> list[float]:
            return self._vectors([text])[0]

        async def aembed_text(self, text: str, **kwargs) -> list[float]:
            return self.embed_text(text)

        def embed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
            return self._vectors(texts)

        async def aembed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
            return self.embed_texts(texts)

    async def _run() -> list[dict]:
        client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=120.0,
        )
        llm = llm_factory(
            JUDGE_MODEL,
            client=client,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            max_tokens=MAX_TOKENS,
            extra_body={"thinking": {"type": "disabled"}},
        )
        embeddings = _BgeM3(embedder)
        faithfulness = Faithfulness(llm=llm)
        relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings, strictness=STRICTNESS)
        precision = ContextPrecision(llm=llm)
        recall = ContextRecall(llm=llm)
        rows = []
        for answer in answers:
            contexts = citation_texts(answer)
            reference = reference_text(questions_by_id[answer["id"]])
            faith = await faithfulness.ascore(
                user_input=answer["query"],
                response=answer["answer"],
                retrieved_contexts=contexts,
            )
            relevant = await relevancy.ascore(
                user_input=answer["query"],
                response=answer["answer"],
            )
            precise = await precision.ascore(
                user_input=answer["query"],
                reference=reference,
                retrieved_contexts=contexts,
            )
            recalled = await recall.ascore(
                user_input=answer["query"],
                retrieved_contexts=contexts,
                reference=reference,
            )
            row = question_row(answer, faith.value, relevant.value, precise.value, recalled.value)
            rows.append(row)
            print(
                f"{row['id']}  faithfulness {row['faithfulness']}  "
                f"answer_relevancy {row['answer_relevancy']}  "
                f"context_precision {row['context_precision']}  "
                f"context_recall {row['context_recall']}"
            )
        return rows

    return asyncio.run(_run())
