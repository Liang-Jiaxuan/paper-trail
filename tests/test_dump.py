"""检查 PDF 核对，以及 middle JSON 外层不改写块。"""

import json
import tempfile
import unittest
from pathlib import Path

from paper_trail.parsing.dump import (
    PdfMatchError,
    clear_paper_dir,
    locate_pdfs,
    page_numbers,
    remove_index,
    selected_papers,
    sha256_file,
    wrap_middle,
    write_paper_dump,
)


class DumpTest(unittest.TestCase):
    def test_pdfs_match_by_sha256(self):
        """文件名无关，sha256 相同才算找到；缺失或重复都报错。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "1909.08053v4.pdf"
            first.write_bytes(b"pdf-bytes")
            digest = sha256_file(first)
            papers = [{"paper_id": "shoeybi-megatron-lm", "sha256": digest}]
            found = locate_pdfs(papers, root)
            self.assertEqual(found["shoeybi-megatron-lm"], first)
            with self.assertRaises(PdfMatchError):
                locate_pdfs([{"paper_id": "missing", "sha256": "0" * 64}], root)
            duplicate = root / "copy.pdf"
            duplicate.write_bytes(b"pdf-bytes")
            with self.assertRaises(PdfMatchError):
                locate_pdfs(papers, root)

    def test_selected_papers_keep_manifest_order(self):
        """只导出 status 为 selected 的论文，顺序与清单一致。"""
        manifest = {
            "papers": [
                {"paper_id": "huang-gpipe", "status": "selected"},
                {"paper_id": "draft", "status": "candidate"},
                {"paper_id": "shoeybi-megatron-lm", "status": "selected"},
            ]
        }
        self.assertEqual(
            [paper["paper_id"] for paper in selected_papers(manifest)],
            ["huang-gpipe", "shoeybi-megatron-lm"],
        )

    def test_wrap_keeps_mineru_block_types(self):
        """外层加上身份。middle 里的类型、层级和行内样式原样留下。"""
        middle = {
            "pages": [
                {
                    "page_idx": 1,
                    "blocks": [
                        {
                            "type": "paragraph_title",
                            "level": 2,
                            "content": [
                                {"type": "text", "content": "1", "styles": ["superscript"]},
                            ],
                        }
                    ],
                }
            ]
        }
        paper = {"paper_id": "cai-medusa", "sha256": "abc"}
        document = wrap_middle(paper, "2401.10774v3.pdf", middle)
        self.assertEqual(document["dump_version"], 2)
        self.assertEqual(document["parser"], "mineru")
        self.assertEqual(document["paper_id"], "cai-medusa")
        self.assertEqual(document["sha256"], "abc")
        self.assertEqual(document["source_name"], "2401.10774v3.pdf")
        block = document["middle"]["pages"][0]["blocks"][0]
        self.assertEqual(block["type"], "paragraph_title")
        self.assertEqual(block["level"], 2)
        self.assertEqual(block["content"][0]["styles"], ["superscript"])
        self.assertNotIn("column", document)
        self.assertEqual(page_numbers(middle), [2])

    def test_remove_index_before_export(self):
        """导出开始前删掉旧 index.json，没有旧文件时也不报错。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remove_index(root, "mineru")
            index = root / "mineru" / "index.json"
            index.parent.mkdir(parents=True)
            index.write_text("{}\n", encoding="utf-8")
            remove_index(root, "mineru")
            self.assertFalse(index.exists())

    def test_paper_file_replaces_old_page_directory(self):
        """整篇 JSON 写入前删掉同名的按页目录。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "mineru" / "huang-gpipe" / "page-002.txt"
            old.parent.mkdir(parents=True)
            old.write_text("old\n", encoding="utf-8")
            clear_paper_dir(root, "huang-gpipe")
            self.assertFalse(old.parent.exists())
            document = wrap_middle(
                {"paper_id": "huang-gpipe", "sha256": "abc"},
                "gpipe.pdf",
                {"pages": [{"page_idx": 0, "blocks": []}]},
            )
            path = write_paper_dump(root, document)
            self.assertEqual(path.name, "huang-gpipe.json")
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["middle"]["pages"][0]["page_idx"], 0)
            self.assertEqual(list(path.parent.glob("*.txt")), [])
