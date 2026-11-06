"""用抽检过的 Megatron-LM 片段检查分块。"""

import unittest

from paper_trail.chunking.build import chunks_from_document


def text_block(page_idx, index, content, continues_prev=False):
    block = {
        "type": "text",
        "index": index,
        "content": [{"type": "text", "content": content}],
    }
    if continues_prev:
        block["continues_prev"] = True
    return page_idx, block


def document_with(pages):
    """pages 是 (page_idx, blocks) 的列表。"""
    return {
        "paper_id": "shoeybi-megatron-lm",
        "sha256": "abc",
        "middle": {
            "pages": [{"page_idx": page_idx, "blocks": blocks} for page_idx, blocks in pages]
        },
    }


class ChunkingTest(unittest.TestCase):
    def test_page_break_hyphen_stays_in_one_chunk(self):
        """第 5 页结尾 itera- 和第 6 页开头 tions 接成一块，页码跨 5 到 6。"""
        document = document_with(
            [
                (
                    4,
                    [
                        {
                            "type": "header",
                            "content": [{"type": "text", "content": "Megatron-LM"}],
                        },
                        {
                            "type": "text",
                            "index": 13,
                            "content": [
                                {"type": "text", "content": "For GPT-2 models, all training is performed with sequences of 1024 subword units at a batch size of 512 for 300k itera-"}
                            ],
                        },
                    ],
                ),
                (
                    5,
                    [
                        {
                            "type": "text",
                            "index": 1,
                            "continues_prev": True,
                            "content": [{"type": "text", "content": "tions. Our learning rate of 1.5e-4 utilizes a warmup period"}],
                        },
                        {
                            "type": "page_number",
                            "content": [{"type": "text", "content": "6"}],
                        },
                    ],
                ),
            ]
        )
        chunks = chunks_from_document(document)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["start_page"], 5)
        self.assertEqual(chunks[0]["end_page"], 6)
        self.assertIn("300k itera-tions. Our learning rate", chunks[0]["text"])
        self.assertNotIn("Megatron-LM", chunks[0]["text"])
        again = chunks_from_document(document)
        self.assertEqual([item["chunk_id"] for item in chunks], [item["chunk_id"] for item in again])

    def test_table_and_figure_do_not_break_the_sentence(self):
        """Table 1 和 Figure 5 留在原处。被它们分开的句子仍是同一块。"""
        document = document_with(
            [
                (
                    5,
                    [
                        {
                            "type": "paragraph_title",
                            "level": 2,
                            "content": [{"type": "text", "content": "5.1.1. MODEL AND DATA PARALLELISM"}],
                        },
                        {
                            "type": "text",
                            "index": 8,
                            "content": [{"type": "text", "content": "Weak scaling is typically"}],
                        },
                        {
                            "type": "table",
                            "index": 10,
                            "content": [
                                {
                                    "type": "table_caption",
                                    "content": [{"type": "text", "content": "Table 1. Parameters used for scaling studies."}],
                                },
                                {
                                    "type": "table_body",
                                    "content": "<table><tr><td>1536</td><td>16</td></tr></table>",
                                },
                            ],
                        },
                        {
                            "type": "chart",
                            "index": 11,
                            "content": [
                                {"type": "chart_body", "content": ""},
                                {
                                    "type": "chart_caption",
                                    "content": [{"type": "text", "content": "Figure 5. Model and model + data parallel weak scaling efficiency."}],
                                },
                            ],
                        },
                        {
                            "type": "text",
                            "index": 13,
                            "continues_prev": True,
                            "content": [{"type": "text", "content": "done by scaling the batch-size"}],
                        },
                    ],
                )
            ]
        )
        chunks = chunks_from_document(document)
        kinds = [item["block_type"] for item in chunks]
        self.assertEqual(kinds, ["paragraph_title", "text", "table", "chart"])
        text = chunks[1]
        self.assertIn("Weak scaling is typically done by scaling the batch-size", text["text"])
        self.assertEqual(text["start_page"], 6)
        self.assertEqual(text["end_page"], 6)
        self.assertIn("<table>", chunks[2]["text"])
        self.assertIn("Table 1. Parameters", chunks[2]["text"])
        self.assertIn("Figure 5.", chunks[3]["text"])
        self.assertLess(text["sequence"], chunks[2]["sequence"])
        self.assertEqual(
            text["section_path"],
            ["5.1.1. MODEL AND DATA PARALLELISM"],
        )
        self.assertEqual(text["chunk_id"], "shoeybi-megatron-lm/5-1-1-model-and-data-parallelism/0001")

    def test_short_chunk_is_kept_and_titles_do_not_nest(self):
        """单字母块留下。后一个小节标题替换上一个，不放进它下面。"""
        document = document_with(
            [
                (
                    0,
                    [
                        {"type": "doc_title", "content": [{"type": "text", "content": "Megatron-LM"}]},
                        {"type": "paragraph_title", "level": 2, "content": [{"type": "text", "content": "2. Background"}]},
                        {"type": "text", "content": [{"type": "text", "content": "K"}]},
                        {"type": "paragraph_title", "level": 2, "content": [{"type": "text", "content": "2.1. Pretraining"}]},
                    ],
                )
            ]
        )
        chunks = chunks_from_document(document)
        self.assertEqual(chunks[2]["text"], "K")
        self.assertEqual(chunks[1]["section_path"], ["Megatron-LM", "2. Background"])
        self.assertEqual(chunks[3]["section_path"], ["Megatron-LM", "2.1. Pretraining"])
        self.assertEqual(len(chunks[3]["section_path"]), 2)
        self.assertEqual(chunks[0]["chunk_id"], "shoeybi-megatron-lm/0000")
        self.assertEqual(chunks[2]["chunk_id"], "shoeybi-megatron-lm/2-background/0002")

    def test_long_prose_splits_on_the_sentence_without_overlap(self):
        """超过 800 字符时在句号处切开。Fig. 5 不当成句号。单句超长才按字符硬切。"""
        first = "A" * 500 + ". "
        second = "The " + "B" * 500 + "."
        hard = "C" * 900
        document = document_with(
            [
                (
                    0,
                    [
                        {"type": "text", "content": [{"type": "text", "content": first + second}]},
                        {"type": "text", "content": [{"type": "text", "content": "Fig. 5 shows the result. The next point holds."}]},
                        {"type": "text", "content": [{"type": "text", "content": hard}]},
                    ],
                )
            ]
        )
        chunks = chunks_from_document(document)
        self.assertEqual(chunks[0]["text"], first.strip())
        self.assertEqual(chunks[1]["text"], second)
        self.assertNotIn(chunks[0]["text"][-20:], chunks[1]["text"])
        self.assertEqual(chunks[2]["text"], "Fig. 5 shows the result. The next point holds.")
        self.assertEqual(chunks[3]["text"], "C" * 800)
        self.assertEqual(chunks[4]["text"], "C" * 100)
        self.assertEqual([item["sequence"] for item in chunks], list(range(5)))

    def test_multirow_table_stays_and_fake_table_drops_the_image(self):
        """多行表整块留下。只有一行的表去掉 data:image 后按正文切。"""
        rows = "".join(f"<tr><td>{'D' * 100}</td></tr>" for _ in range(10))
        long = "E" * 500 + ". " + "The " + "F" * 500 + "."
        image = '<img src="data:image/jpeg;base64,AAAA"/>'
        document = document_with(
            [
                (
                    11,
                    [
                        {"type": "table", "content": [{"type": "table_body", "content": f"<table>{rows}</table>"}]},
                        {
                            "type": "table",
                            "content": [
                                {
                                    "type": "table_body",
                                    "content": f"<table><tr><td>patterns. {image}Figure 8. Grouping of GPUs. {long}</td></tr></table>",
                                }
                            ],
                        },
                    ],
                )
            ]
        )
        chunks = chunks_from_document(document)
        self.assertEqual(chunks[0]["block_type"], "table")
        self.assertIn("<table>", chunks[0]["text"])
        self.assertGreater(len(chunks[0]["text"]), 800)
        joined = " ".join(item["text"] for item in chunks[1:])
        self.assertNotIn("data:image", joined)
        self.assertIn("Figure 8. Grouping of GPUs.", joined)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(item["block_type"] == "table" for item in chunks[1:]))

    def test_long_reference_splits_like_prose(self):
        """参考文献超过 800 字符时也按句号切开。"""
        text = "Smith, A. wrote one paper. " + "The " + "R" * 500 + ". " + "Jones, B. wrote another. " + "The " + "S" * 500 + "."
        document = document_with(
            [(0, [{"type": "ref_text", "content": [{"type": "text", "content": text}]}])]
        )
        chunks = chunks_from_document(document)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(item["text"]) <= 800 for item in chunks))
        self.assertTrue(all(item["block_type"] == "ref_text" for item in chunks))
