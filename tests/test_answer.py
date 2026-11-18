"""用假的重排结果检查引用字段和拒答句。不读索引。"""

import unittest

from paper_trail.generation.answer import (
    MODEL_NAME,
    REFUSAL_ANSWER,
    attach_number_checks,
    attach_summary,
    build_answer,
    check_numbers,
    prompt_messages,
    summary_text,
)


def payload(refused, hits):
    return {
        "query": "example",
        "refused": refused,
        "threshold": 0.25,
        "vec_score_max": None if not hits else hits[0]["vec_score"],
        "hits": hits,
    }


def hit(**overrides):
    row = {
        "rank": 1,
        "chunk_id": "example/intro/0001",
        "paper_id": "example",
        "sha256": "abc",
        "section_path": ["Example", "Intro"],
        "start_page": 1,
        "end_page": 2,
        "text": "full chunk text",
        "vec_score": 0.4,
        "rerank_score": 1.5,
        "bm25_score": 9.0,
        "rrf_score": 0.02,
    }
    row.update(overrides)
    return row


class AnswerTest(unittest.TestCase):
    def test_pass_leaves_answer_empty(self):
        answer = build_answer(payload(False, [hit()]))
        self.assertIsNone(answer["answer"])
        self.assertIsNone(answer["model"])
        self.assertFalse(answer["refused"])
        self.assertEqual(answer["threshold"], 0.25)
        self.assertEqual(answer["vec_score_max"], 0.4)
        self.assertEqual(answer["query"], "example")

    def test_refusal_uses_fixed_sentence_and_keeps_citations(self):
        answer = build_answer(payload(True, [hit(vec_score=0.2)]))
        self.assertEqual(answer["answer"], REFUSAL_ANSWER)
        self.assertEqual(REFUSAL_ANSWER, "No passage is close enough to answer.")
        self.assertIsNone(answer["model"])
        self.assertEqual(len(answer["citations"]), 1)
        self.assertEqual(answer["citations"][0]["text"], "full chunk text")

    def test_citation_keeps_selected_fields(self):
        answer = build_answer(payload(False, [hit(vec_score=None)]))
        citation = answer["citations"][0]
        self.assertEqual(
            set(citation),
            {
                "rank",
                "chunk_id",
                "paper_id",
                "sha256",
                "section_path",
                "start_page",
                "end_page",
                "text",
                "vec_score",
                "rerank_score",
            },
        )
        self.assertIsNone(citation["vec_score"])
        self.assertEqual(citation["section_path"], ["Example", "Intro"])
        self.assertEqual(citation["end_page"], 2)
        self.assertNotIn("bm25_score", citation)
        self.assertNotIn("rrf_score", citation)

    def test_empty_hits_keep_an_empty_citation_list(self):
        answer = build_answer(payload(True, []))
        self.assertEqual(answer["citations"], [])
        self.assertEqual(answer["answer"], REFUSAL_ANSWER)
        self.assertIsNone(answer["vec_score_max"])

    def test_missing_field_raises(self):
        with self.assertRaises(KeyError):
            build_answer({"query": "example", "hits": []})

    def test_prompt_sends_passage_text_and_skips_scores(self):
        messages = prompt_messages("How many?", [hit(vec_score=0.419283, rerank_score=9.876)])
        user = messages[1]["content"]
        self.assertIn("[1] example p1-2", user)
        self.assertIn("full chunk text", user)
        self.assertIn("Question:\nHow many?", user)
        self.assertNotIn("0.419283", user)
        self.assertNotIn("9.876", user)
        self.assertIn("No passage is close enough to answer.", messages[0]["content"])

    def test_attach_summary_keeps_refused_flag(self):
        answer = build_answer(payload(False, [hit()]))
        written = attach_summary(answer, "GPT-2 has 1.5B parameters [2].")
        self.assertEqual(written["answer"], "GPT-2 has 1.5B parameters [2].")
        self.assertEqual(written["model"], MODEL_NAME)
        self.assertFalse(written["refused"])
        self.assertIsNone(answer["answer"])

    def test_blank_summary_is_rejected(self):
        with self.assertRaises(ValueError):
            summary_text("  \n")

    def test_refusal_sentence_has_no_numbers(self):
        result = check_numbers(REFUSAL_ANSWER, [{"rank": 1, "text": "8.3 billion"}])
        self.assertEqual(result["number_checks"], [])
        self.assertTrue(result["numbers_ok"])

    def test_citation_marker_is_not_a_number(self):
        result = check_numbers("See the passage [1].", [{"rank": 1, "text": "no digits"}])
        self.assertEqual(result["number_checks"], [])
        self.assertTrue(result["numbers_ok"])

    def test_number_must_match_the_marked_passage(self):
        citations = [
            {"rank": 1, "text": "studied up to 8.3 billion parameters"},
            {"rank": 2, "text": "GPT-2 (1.5B)"},
        ]
        result = check_numbers("The model has 8.3 billion parameters [1].", citations)
        self.assertEqual(result["number_checks"], [{"number": "8.3", "ranks": [1], "found": True}])
        self.assertTrue(result["numbers_ok"])

    def test_decimal_does_not_match_a_longer_decimal(self):
        result = check_numbers("It reached 8.3 [1].", [{"rank": 1, "text": "reached 8.30"}])
        self.assertFalse(result["number_checks"][0]["found"])
        self.assertFalse(result["numbers_ok"])

    def test_integer_does_not_match_inside_a_decimal(self):
        result = check_numbers("The figure is 15 [1].", [{"rank": 1, "text": "15.1 PetaFLOPs"}])
        self.assertEqual(result["number_checks"][0]["number"], "15")
        self.assertFalse(result["number_checks"][0]["found"])

    def test_number_without_a_marker_fails(self):
        result = check_numbers("It uses 8.3 billion parameters.", [{"rank": 1, "text": "8.3 billion"}])
        self.assertEqual(result["number_checks"][0]["ranks"], [])
        self.assertFalse(result["number_checks"][0]["found"])
        self.assertFalse(result["numbers_ok"])

    def test_two_numbers_use_the_markers_before_the_next_number(self):
        citations = [
            {"rank": 1, "text": "8.3 billion"},
            {"rank": 2, "text": "17 billion"},
        ]
        result = check_numbers("8.3 billion [1] and 17 billion [2].", citations)
        self.assertEqual(
            result["number_checks"],
            [
                {"number": "8.3", "ranks": [1], "found": True},
                {"number": "17", "ranks": [2], "found": True},
            ],
        )

    def test_attach_number_checks_keeps_answer_and_refused(self):
        record = {
            "answer": "8.3 [1]",
            "refused": False,
            "citations": [{"rank": 1, "text": "8.3 billion"}],
        }
        checked = attach_number_checks(record)
        self.assertEqual(record["answer"], "8.3 [1]")
        self.assertFalse(record["refused"])
        self.assertTrue(checked["numbers_ok"])
        self.assertEqual(list(checked)[-3:], ["number_checks", "numbers_ok", "citations"])
