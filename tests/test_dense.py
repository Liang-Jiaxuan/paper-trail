"""用假向量检查稠密检索。不加载 bge-m3。"""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from paper_trail.indexing.dense import load_vector_index, save_vector_index, search_vectors


def document(chunk_id, text):
    return {
        "chunk_id": chunk_id,
        "paper_id": "example",
        "sha256": "abc",
        "section_path": ["Example"],
        "sequence": 0,
        "start_page": 1,
        "end_page": 1,
        "block_type": "text",
        "text": text,
    }


class DenseTest(unittest.TestCase):
    def test_matching_direction_ranks_first(self):
        documents = [document("alpha", "pipeline parallelism"), document("beta", "kv cache")]
        vectors = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
        hits = search_vectors(vectors, documents, np.array([0.6, 0.8], dtype=np.float32))
        self.assertEqual([hit["chunk_id"] for hit in hits], ["beta", "alpha"])
        self.assertAlmostEqual(hits[0]["vec_score"], 0.8)
        self.assertEqual(hits[0]["rank"], 1)
        self.assertNotIn("bm25_score", hits[0])

    def test_save_and_load_roundtrip(self):
        documents = [document("alpha", "pipeline parallelism")]
        vectors = np.array([[1.0, 0.0]], dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            index_path = root / "index.json"
            vectors_path = root / "vectors.npy"
            save_vector_index(2, documents, vectors, index_path, vectors_path)
            loaded, matrix = load_vector_index(index_path, vectors_path)
            self.assertEqual(loaded["kind"], "dense")
            self.assertEqual(loaded["model"], "BAAI/bge-m3")
            hits = search_vectors(matrix, loaded["documents"], np.array([1.0, 0.0], dtype=np.float32))
            self.assertEqual(hits[0]["chunk_id"], "alpha")
            self.assertAlmostEqual(hits[0]["vec_score"], 1.0)
