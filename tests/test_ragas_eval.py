"""ragas 分数的空值和平均。不请求模型，也不加载 bge-m3。"""

import math
import unittest

from paper_trail.evaluation.ragas_eval import (
    STRICTNESS,
    citation_texts,
    mean_score,
    question_row,
    ragas_payload,
    reference_text,
    stored_score,
)


class StoredScoreTest(unittest.TestCase):
    def test_nan_becomes_none_and_zero_stays(self):
        self.assertIsNone(stored_score(float("nan")))
        self.assertIsNone(stored_score(None))
        self.assertEqual(stored_score(0.0), 0.0)
        self.assertEqual(stored_score(1), 1.0)

    def test_mean_skips_missing_scores(self):
        self.assertEqual(mean_score([1.0, None, 0.0]), (0.5, 2))
        self.assertEqual(mean_score([None, None]), (None, 0))

    def test_contexts_follow_rank_and_drop_scores(self):
        answer = {
            "citations": [
                {"rank": 2, "text": "second", "vec_score": 0.2},
                {"rank": 1, "text": "first", "rerank_score": 3.0},
            ]
        }
        self.assertEqual(citation_texts(answer), ["first", "second"])

    def test_reference_keeps_distinct_evidence_in_order(self):
        question = {
            "passages": [
                {"evidence": "super-linear speedup on 400 GPUs"},
                {"evidence": "64-400 GPUs"},
                {"evidence": "super-linear speedup on 400 GPUs"},
            ]
        }
        self.assertEqual(
            reference_text(question),
            "super-linear speedup on 400 GPUs\n64-400 GPUs",
        )

    def test_payload_counts_only_numeric_scores(self):
        rows = [
            question_row({"id": "kept"}, 1.0, 0.0, 1.0, 0.5),
            question_row({"id": "empty"}, math.nan, 0.5, math.nan, 1.0),
        ]
        payload = ragas_payload(1, rows, "0.4.4")
        self.assertEqual(payload["questions"][1]["faithfulness"], None)
        self.assertEqual(payload["questions"][1]["context_precision"], None)
        self.assertEqual(payload["questions"][1]["answer_relevancy"], 0.5)
        self.assertEqual(payload["faithfulness_mean"], 1.0)
        self.assertEqual(payload["faithfulness_count"], 1)
        self.assertEqual(payload["answer_relevancy_mean"], 0.25)
        self.assertEqual(payload["answer_relevancy_count"], 2)
        self.assertEqual(payload["context_precision_mean"], 1.0)
        self.assertEqual(payload["context_precision_count"], 1)
        self.assertEqual(payload["context_recall_mean"], 0.75)
        self.assertEqual(payload["context_recall_count"], 2)
        self.assertEqual(payload["strictness"], STRICTNESS)
        self.assertEqual(payload["judge_model"], "deepseek-v4-pro")
        self.assertEqual(payload["embedding_model"], "BAAI/bge-m3")
