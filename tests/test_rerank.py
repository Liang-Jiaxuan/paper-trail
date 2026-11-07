"""用假分数检查重排顺序。不加载 bge-reranker-v2-m3。"""

import unittest

from paper_trail.indexing.rerank import QUERY_TOP_K, apply_rerank


def row(chunk_id, rank, rrf_score, bm25_rank=None, vec_rank=None):
    return {
        "chunk_id": chunk_id,
        "paper_id": "example",
        "sha256": "abc",
        "section_path": ["Example"],
        "sequence": rank,
        "start_page": 1,
        "end_page": 1,
        "block_type": "text",
        "text": chunk_id,
        "bm25_score": None if bm25_rank is None else 1.0,
        "bm25_rank": bm25_rank,
        "vec_score": None if vec_rank is None else 0.5,
        "vec_rank": vec_rank,
        "rrf_score": rrf_score,
        "rank": rank,
    }


class RerankTest(unittest.TestCase):
    def test_higher_score_moves_ahead_and_keeps_rrf_rank(self):
        reranked = apply_rerank(
            [
                row("first", 1, 0.032, bm25_rank=1, vec_rank=4),
                row("second", 2, 0.028, bm25_rank=2, vec_rank=20),
            ],
            [0.1, 2.5],
        )
        self.assertEqual(reranked[0]["chunk_id"], "second")
        self.assertEqual(reranked[0]["rank"], 1)
        self.assertEqual(reranked[0]["rrf_rank"], 2)
        self.assertEqual(reranked[0]["rerank_score"], 2.5)
        self.assertEqual(reranked[0]["bm25_rank"], 2)
        self.assertEqual(reranked[0]["vec_rank"], 20)
        self.assertEqual(reranked[1]["rrf_rank"], 1)

    def test_missing_route_stays_empty(self):
        reranked = apply_rerank(
            [row("title", 1, 0.016, vec_rank=1)],
            [1.2],
        )
        self.assertIsNone(reranked[0]["bm25_score"])
        self.assertIsNone(reranked[0]["bm25_rank"])
        self.assertEqual(reranked[0]["vec_rank"], 1)
        self.assertEqual(reranked[0]["rerank_score"], 1.2)

    def test_keeps_five(self):
        hits = [row(f"c{i}", i, 1 / i, bm25_rank=i, vec_rank=i) for i in range(1, 7)]
        scores = [float(6 - i) for i in range(6)]
        reranked = apply_rerank(hits, scores)
        self.assertEqual(QUERY_TOP_K, 5)
        self.assertEqual(len(reranked), 5)
        self.assertEqual(reranked[-1]["chunk_id"], "c5")
        self.assertNotIn("c6", [item["chunk_id"] for item in reranked])

    def test_tie_keeps_earlier_rrf_order(self):
        reranked = apply_rerank(
            [
                row("earlier", 1, 0.03, bm25_rank=1, vec_rank=1),
                row("later", 2, 0.02, bm25_rank=2, vec_rank=2),
            ],
            [1.0, 1.0],
        )
        self.assertEqual([item["chunk_id"] for item in reranked], ["earlier", "later"])

    def test_score_count_must_match(self):
        with self.assertRaises(ValueError):
            apply_rerank([row("only", 1, 0.01, bm25_rank=1)], [])
