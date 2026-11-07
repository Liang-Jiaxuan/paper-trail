"""用假的两路名单检查 RRF。不加载 bge-m3，也不读 data/chunks。"""

import unittest

from paper_trail.indexing.rrf import CANDIDATE_K, RRF_K, candidate_k_from_arg, fuse


def hit(chunk_id, text, rank, score, kind):
    item = {
        "chunk_id": chunk_id,
        "paper_id": "example",
        "sha256": "abc",
        "section_path": ["Example"],
        "sequence": rank,
        "start_page": 1,
        "end_page": 1,
        "block_type": "text",
        "text": text,
        "rank": rank,
    }
    if kind == "bm25":
        item["bm25_score"] = score
    else:
        item["vec_score"] = score
    return item


class RrfTest(unittest.TestCase):
    def test_both_routes_keep_their_own_scores(self):
        fused = fuse(
            [hit("sentence", "15.1 PetaFLOPs", 2, 8.4, "bm25")],
            [hit("sentence", "15.1 PetaFLOPs", 4, 0.61, "vec")],
        )
        row = fused[0]
        self.assertEqual(row["bm25_rank"], 2)
        self.assertEqual(row["vec_rank"], 4)
        self.assertEqual(row["bm25_score"], 8.4)
        self.assertEqual(row["vec_score"], 0.61)
        self.assertAlmostEqual(row["rrf_score"], 1 / (RRF_K + 2) + 1 / (RRF_K + 4))
        self.assertEqual(row["rank"], 1)

    def test_missing_route_stays_empty(self):
        fused = fuse(
            [hit("sentence", "15.1 PetaFLOPs", 2, 8.4, "bm25")],
            [hit("title", "2.2 Algorithm", 1, 0.63, "vec")],
        )
        by_id = {row["chunk_id"]: row for row in fused}
        self.assertIsNone(by_id["title"]["bm25_score"])
        self.assertIsNone(by_id["title"]["bm25_rank"])
        self.assertIsNone(by_id["sentence"]["vec_score"])
        self.assertIsNone(by_id["sentence"]["vec_rank"])
        self.assertEqual(by_id["title"]["vec_rank"], 1)
        self.assertEqual(by_id["sentence"]["bm25_rank"], 2)

    def test_a_hit_on_both_routes_ranks_above_a_single_route(self):
        fused = fuse(
            [hit("sentence", "15.1 PetaFLOPs", 2, 8.4, "bm25")],
            [
                hit("title", "2.2 Algorithm", 1, 0.63, "vec"),
                hit("sentence", "15.1 PetaFLOPs", 4, 0.61, "vec"),
            ],
        )
        self.assertEqual([row["chunk_id"] for row in fused], ["sentence", "title"])

    def test_omitted_candidate_depth_is_the_default(self):
        self.assertEqual(CANDIDATE_K, 50)
        self.assertEqual(candidate_k_from_arg(None), 50)
        self.assertEqual(candidate_k_from_arg("80"), 80)
        with self.assertRaises(ValueError):
            candidate_k_from_arg("0")
