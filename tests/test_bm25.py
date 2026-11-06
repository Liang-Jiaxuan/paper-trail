"""用短文本检查 BM25。不读 data/chunks，也不加载模型。"""

import json
import tempfile
import unittest
from pathlib import Path

from paper_trail.indexing.bm25 import load_index, make_index, search, tokenize, write_index


def chunk(chunk_id, text, page=1):
    return {
        "chunk_id": chunk_id,
        "paper_id": "example",
        "sha256": "abc",
        "section_path": ["Example"],
        "sequence": 0,
        "start_page": page,
        "end_page": page,
        "block_type": "text",
        "text": text,
    }


class Bm25Test(unittest.TestCase):
    def test_tokenizer_splits_hyphen_and_decimal(self):
        self.assertEqual(tokenize("Cross-Validation 8.3"), ["cross", "validation", "8", "3"])

    def test_unique_term_returns_only_that_chunk(self):
        index = make_index(
            2,
            [
                chunk("learning-rate", "The learning rate starts at 1e-4."),
                chunk("kv-cache", "PagedAttention stores the kv cache in blocks."),
            ],
        )
        hits = search(index, "kv cache")
        self.assertEqual([hit["chunk_id"] for hit in hits], ["kv-cache"])
        self.assertGreater(hits[0]["bm25_score"], 0)
        self.assertEqual(hits[0]["rank"], 1)
        self.assertNotIn("vec_score", hits[0])

    def test_empty_query_returns_nothing(self):
        index = make_index(2, [chunk("one", "PagedAttention stores blocks.")])
        self.assertEqual(search(index, "..."), [])

    def test_write_index_reloads_and_searches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            chunks = root / "chunks"
            chunks.mkdir()
            paper = {
                "chunk_version": 2,
                "paper_id": "example",
                "sha256": "abc",
                "chunks": [chunk("kv-cache", "PagedAttention stores the kv cache in blocks.")],
            }
            (chunks / "example.json").write_text(json.dumps(paper), encoding="utf-8")
            (chunks / "index.json").write_text(
                json.dumps({"chunk_version": 2, "papers": [{"paper_id": "example", "sha256": "abc", "chunks": 1}]}),
                encoding="utf-8",
            )
            path = root / "bm25" / "index.json"
            write_index(chunks, path)
            hits = search(load_index(path), "PagedAttention")
            self.assertEqual(hits[0]["chunk_id"], "kv-cache")
            self.assertEqual(hits[0]["start_page"], 1)
