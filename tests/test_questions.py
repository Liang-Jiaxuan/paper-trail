"""检查评测题文件的形状。不读 data/chunks，也不跑检索。"""

import json
import unittest
from pathlib import Path

QUESTIONS_PATH = Path(__file__).resolve().parents[1] / "data" / "eval" / "questions.json"


class QuestionFileTest(unittest.TestCase):
    def test_ten_questions_each_have_a_passage(self):
        payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["question_version"], 1)
        questions = payload["questions"]
        self.assertEqual(len(questions), 10)
        ids = [question["id"] for question in questions]
        self.assertEqual(len(ids), len(set(ids)))
        for question in questions:
            self.assertTrue(question["query"].strip())
            self.assertGreaterEqual(len(question["passages"]), 1)
            for passage in question["passages"]:
                self.assertTrue(passage["evidence"])
                self.assertTrue(passage["chunk_id"].startswith(passage["paper_id"] + "/"))
                self.assertGreaterEqual(passage["start_page"], 1)
                self.assertGreaterEqual(passage["end_page"], passage["start_page"])
