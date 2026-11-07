"""用 bge-m3 的稠密向量建索引。和 BM25 的融合在 rrf.py。"""

import json
from pathlib import Path

import numpy as np

from paper_trail.indexing.bm25 import documents_from_chunks

INDEX_VERSION = 1
MODEL_NAME = "BAAI/bge-m3"
DIMENSION = 1024
QUERY_TOP_K = 5
BATCH_SIZE = 32


def unit_vector(vector: np.ndarray) -> np.ndarray:
    """把向量变成单位长度。零向量保持原样。"""
    array = np.asarray(vector, dtype=np.float32)
    norm = float(np.linalg.norm(array))
    if norm == 0.0:
        return array
    return array / norm


def search_vectors(vectors: np.ndarray, documents: list[dict], query_vector: np.ndarray, top_k: int = QUERY_TOP_K) -> list[dict]:
    """内积就是余弦相似度。向量和查询都已经归一化。"""
    if len(documents) != len(vectors):
        raise ValueError("文档数和向量数不一致")
    query = unit_vector(query_vector)
    scores = np.asarray(vectors, dtype=np.float32) @ query
    order = np.argsort(-scores, kind="stable")
    hits = []
    for index in order[:top_k]:
        position = int(index)
        hit = dict(documents[position])
        hit["vec_score"] = float(scores[position])
        hits.append(hit)
    for rank, hit in enumerate(hits, 1):
        hit["rank"] = rank
    return hits


def embed_texts(texts: list[str], model_dir: Path, batch_size: int = BATCH_SIZE) -> np.ndarray:
    """用本地 bge-m3 编出归一化的稠密向量。"""
    from sentence_transformers import SentenceTransformer

    if not model_dir.is_dir():
        raise FileNotFoundError(f"找不到嵌入模型：{model_dir}")
    model = SentenceTransformer(str(model_dir))
    encoded = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 1,
    )
    vectors = np.asarray(encoded, dtype=np.float32)
    if vectors.ndim != 2 or vectors.shape[1] != DIMENSION:
        raise ValueError(f"向量维度不是 {DIMENSION}：{vectors.shape}")
    return vectors


def save_vector_index(chunk_version: int, documents: list[dict], vectors: np.ndarray, index_path: Path, vectors_path: Path) -> dict:
    """写出索引说明和向量矩阵。"""
    if len(documents) != len(vectors):
        raise ValueError("文档数和向量数不一致")
    payload = {
        "index_version": INDEX_VERSION,
        "kind": "dense",
        "model": MODEL_NAME,
        "dimension": DIMENSION,
        "normalized": True,
        "chunk_version": chunk_version,
        "documents": documents,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = vectors_path.with_suffix(".tmp.npy")
    np.save(temporary, np.asarray(vectors, dtype=np.float32))
    temporary.replace(vectors_path)
    index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def write_vector_index(chunks_dir: Path, index_path: Path, vectors_path: Path, model_dir: Path) -> dict:
    """读分块，编码，写出向量索引。"""
    chunk_version, documents = documents_from_chunks(chunks_dir)
    vectors = embed_texts([document["text"] for document in documents], model_dir)
    return save_vector_index(chunk_version, documents, vectors, index_path, vectors_path)


def load_vector_index(index_path: Path, vectors_path: Path) -> tuple[dict, np.ndarray]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if payload.get("kind") != "dense":
        raise ValueError(f"不是稠密向量索引：{index_path}")
    vectors = np.load(vectors_path)
    return payload, vectors
