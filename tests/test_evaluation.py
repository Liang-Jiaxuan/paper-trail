"""评测命中只看 chunk_id。不读索引，也不加载模型。"""

import unittest

from paper_trail.evaluation.retrieval import question_result, retrieval_payload


def hit(**overrides) -> dict:
    row = {
        "rank": 1,
        "rrf_rank": 1,
        "chunk_id": "shoeybi-megatron-lm/abstract/0005",
        "paper_id": "shoeybi-megatron-lm",
        "start_page": 1,
        "end_page": 1,
        "section_path": ["abstract"],
        "bm25_score": 7.067312054568449,
        "bm25_rank": 3,
        "vec_score": 0.5825684070587158,
        "vec_rank": 18,
        "rrf_score": 0.028693528693528692,
        "rerank_score": 2.374574899673462,
        "text": "15.1 PetaFLOPs",
    }
    row.update(overrides)
    return row


def question(passages) -> dict:
    return {"id": "example", "query": "Where?", "passages": passages}


class ChunkIdHitTest(unittest.TestCase):
    def test_same_page_with_another_chunk_id_is_a_miss(self):
        passages = [
            {
                "chunk_id": "shoeybi-megatron-lm/abstract/0005",
                "paper_id": "shoeybi-megatron-lm",
                "start_page": 1,
                "end_page": 1,
            }
        ]
        neighbor = hit(chunk_id="shoeybi-megatron-lm/abstract/0006")
        result = question_result(question(passages), [neighbor])
        self.assertFalse(result["hit"])
        self.assertEqual(result["hits"][0]["matched"], [])
        self.assertNotIn("text", result["hits"][0])

    def test_any_listed_chunk_id_counts(self):
        passages = [
            {
                "chunk_id": "shoeybi-megatron-lm/abstract/0005",
                "paper_id": "shoeybi-megatron-lm",
                "start_page": 1,
                "end_page": 1,
            },
            {
                "chunk_id": "shoeybi-megatron-lm/1-introduction/0013",
                "paper_id": "shoeybi-megatron-lm",
                "start_page": 1,
                "end_page": 2,
            },
        ]
        other = hit(rank=1, start_page=1, end_page=2, chunk_id="shoeybi-megatron-lm/1-introduction/0014")
        later = hit(rank=2, start_page=1, end_page=2, chunk_id="shoeybi-megatron-lm/1-introduction/0013")
        result = question_result(question(passages), [other, later])
        self.assertTrue(result["hit"])
        self.assertEqual(result["hits"][0]["matched"], [])
        self.assertEqual(result["hits"][1]["matched"], ["shoeybi-megatron-lm/1-introduction/0013"])

    def test_payload_counts_hits(self):
        payload = retrieval_payload(
            1,
            [
                {"hit": True},
                {"hit": False},
            ],
        )
        self.assertEqual(payload["hit_count"], 1)
        self.assertEqual(payload["question_count"], 2)
        self.assertEqual(payload["candidate_k"], 50)
        self.assertEqual(payload["top_k"], 5)
        self.assertIsNone(payload["paper_ids"])
