"""用 chunk 文本建 Okapi BM25。稠密向量在 dense.py，两路还没有融合。"""

import json
import math
import re
from collections import Counter
from pathlib import Path

INDEX_VERSION = 1
K1 = 1.5
B = 0.75
QUERY_TOP_K = 5
_TOKEN = re.compile(r"[a-z0-9]+")
_FIELDS = (
    "chunk_id",
    "paper_id",
    "sha256",
    "section_path",
    "sequence",
    "start_page",
    "end_page",
    "block_type",
    "text",
)


def tokenize(text: str) -> list[str]:
    """小写后按连续的字母和数字切词。8.3 分成 8 和 3，itera-tions 分成 itera 和 tions。"""
    return _TOKEN.findall(text.lower())


def _idf(n_docs: int, df: int) -> float:
    return math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)


def _scores(doc_tokens: list[list[str]], query_tokens: list[str]) -> list[float]:
    """Okapi BM25。词不在语料里时不加分。"""
    n_docs = len(doc_tokens)
    if n_docs == 0 or not query_tokens:
        return [0.0] * n_docs
    counts = [Counter(tokens) for tokens in doc_tokens]
    lengths = [len(tokens) for tokens in doc_tokens]
    df: Counter[str] = Counter()
    for seen in counts:
        df.update(seen.keys())
    avgdl = sum(lengths) / n_docs
    idf = {term: _idf(n_docs, df[term]) for term in set(query_tokens) if df[term]}
    scores = [0.0] * n_docs
    for term in query_tokens:
        weight = idf.get(term)
        if weight is None:
            continue
        for index, seen in enumerate(counts):
            freq = seen.get(term, 0)
            if freq == 0:
                continue
            norm = 0.0 if avgdl == 0 else lengths[index] / avgdl
            denom = freq + K1 * (1.0 - B + B * norm)
            scores[index] += weight * (freq * (K1 + 1.0)) / denom
    return scores


def documents_from_chunks(chunks_dir: Path) -> tuple[int, list[dict]]:
    """按 data/chunks/index.json 的论文顺序读取块。"""
    index_path = chunks_dir / "index.json"
    if not index_path.is_file():
        raise FileNotFoundError(f"找不到分块索引：{index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    documents = []
    for paper in index["papers"]:
        path = chunks_dir / f"{paper['paper_id']}.json"
        if not path.is_file():
            raise FileNotFoundError(f"找不到分块文件：{path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        for chunk in payload["chunks"]:
            documents.append({key: chunk[key] for key in _FIELDS})
    return int(index["chunk_version"]), documents


def make_index(chunk_version: int, documents: list[dict]) -> dict:
    return {
        "index_version": INDEX_VERSION,
        "kind": "bm25",
        "chunk_version": chunk_version,
        "k1": K1,
        "b": B,
        "tokenizer": "lowercase-alnum",
        "documents": documents,
    }


def write_index(chunks_dir: Path, index_path: Path) -> dict:
    """把全部分块写成一份 BM25 索引。"""
    chunk_version, documents = documents_from_chunks(chunks_dir)
    payload = make_index(chunk_version, documents)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = index_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(index_path)
    return payload


def load_index(index_path: Path) -> dict:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if payload.get("kind") != "bm25":
        raise ValueError(f"不是 BM25 索引：{index_path}")
    return payload


def search(index: dict, query: str, top_k: int = QUERY_TOP_K) -> list[dict]:
    """按 bm25_score 从高到低返回。分数为 0 的块不返回。"""
    documents = index["documents"]
    tokens = [tokenize(document["text"]) for document in documents]
    ranked = sorted(
        enumerate(_scores(tokens, tokenize(query))),
        key=lambda item: (-item[1], item[0]),
    )
    hits = []
    for index_in_corpus, score in ranked:
        if score <= 0:
            continue
        hit = dict(documents[index_in_corpus])
        hit["bm25_score"] = score
        hits.append(hit)
        if len(hits) >= top_k:
            break
    for rank, hit in enumerate(hits, 1):
        hit["rank"] = rank
    return hits
