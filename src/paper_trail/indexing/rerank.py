"""用 bge-reranker-v2-m3 给融合后的候选打分。不重建索引。"""

from pathlib import Path

import numpy as np

QUERY_TOP_K = 5
MAX_LENGTH = 8192
BATCH_SIZE = 8
MODEL_NAME = "BAAI/bge-reranker-v2-m3"


def apply_rerank(hits: list[dict], scores: list[float], top_k: int = QUERY_TOP_K) -> list[dict]:
    """按重排分从高到低留下 top_k 条。原来的融合名次改存到 rrf_rank。"""
    if len(hits) != len(scores):
        raise ValueError("候选数和分数数量不一致")
    rows = []
    for hit, score in zip(hits, scores):
        row = dict(hit)
        row["rrf_rank"] = hit["rank"]
        row["rerank_score"] = float(score)
        rows.append(row)
    rows.sort(key=lambda row: -row["rerank_score"])
    kept = rows[:top_k]
    for rank, row in enumerate(kept, 1):
        row["rank"] = rank
    return kept


def score_pairs(query: str, hits: list[dict], model_dir: Path) -> list[float]:
    """一次加载模型，对全部候选打出分类 logit。"""
    import torch.nn as nn
    from sentence_transformers import CrossEncoder

    if not model_dir.is_dir():
        raise FileNotFoundError(f"找不到重排模型：{model_dir}")
    model = CrossEncoder(
        str(model_dir),
        num_labels=1,
        max_length=MAX_LENGTH,
        activation_fn=nn.Identity(),
        local_files_only=True,
    )
    pairs = [(query, hit["text"]) for hit in hits]
    if not pairs:
        return []
    raw = model.predict(pairs, batch_size=BATCH_SIZE, show_progress_bar=False)
    return [float(score) for score in np.asarray(raw, dtype=np.float64).reshape(-1)]
