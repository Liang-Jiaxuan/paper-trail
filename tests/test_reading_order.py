"""检查分栏阅读顺序，以及不同解析器的输出目录不会混在一起。"""

import json
import tempfile
import unittest
from pathlib import Path

from paper_trail.parsing.dump import (
    PdfMatchError,
    build_document,
    locate_pdfs,
    papers_for_pages,
    sha256_file,
    write_page_dump,
)
from paper_trail.parsing.order import PlacedBlock, order_blocks

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0


def block(x0, y0, x1, y1, text, kind="text"):
    """构造一个测试用的坐标块。"""
    return PlacedBlock(x0, y0, x1, y1, text, kind)


class ReadingOrderTest(unittest.TestCase):
    def test_left_column_is_read_before_right(self):
        """双栏页先读完左栏，再读右栏。"""
        ordered = order_blocks(
            [
                block(307, 110, 560, 140, "R1"),
                block(55, 200, 290, 230, "L2"),
                block(307, 210, 560, 240, "R2"),
                block(55, 100, 290, 130, "L1"),
            ],
            PAGE_WIDTH,
            PAGE_HEIGHT,
        )
        self.assertEqual([item.block.text for item in ordered], ["L1", "L2", "R1", "R2"])
        self.assertEqual([item.column for item in ordered], ["left", "left", "right", "right"])

    def test_full_width_block_splits_the_columns(self):
        """通栏标题和通栏图把上下两栏隔开。"""
        ordered = order_blocks(
            [
                block(307, 130, 560, 160, "R-above"),
                block(50, 400, 560, 480, "figure"),
                block(55, 500, 290, 530, "L-below"),
                block(50, 40, 560, 70, "title"),
                block(55, 120, 290, 150, "L-above"),
                block(307, 510, 560, 540, "R-below"),
            ],
            PAGE_WIDTH,
            PAGE_HEIGHT,
        )
        self.assertEqual(
            [item.block.text for item in ordered],
            ["title", "L-above", "R-above", "figure", "L-below", "R-below"],
        )
        self.assertEqual([item.reading_order for item in ordered], list(range(6)))

    def test_measured_boxes_get_the_expected_column(self):
        """GPipe 的宽行是通栏，Megatron-LM 的两栏坐标分到左右。"""
        gpipe = order_blocks([block(108, 120, 505, 140, "gpipe")], PAGE_WIDTH, PAGE_HEIGHT)
        megatron = order_blocks(
            [
                block(55, 120, 290, 140, "left"),
                block(307, 120, 560, 140, "right"),
            ],
            PAGE_WIDTH,
            PAGE_HEIGHT,
        )
        self.assertEqual(gpipe[0].column, "full")
        self.assertEqual([item.column for item in megatron], ["left", "right"])

    def test_header_and_footer_are_flagged(self):
        """页眉和页脚被标出，贯穿整页的块仍是正文。"""
        ordered = order_blocks(
            [
                block(50, 20, 200, 40, "header"),
                block(50, 100, 200, 140, "body"),
                block(400, 760, 560, 780, "footer"),
                block(40, 10, 560, 780, "span"),
            ],
            PAGE_WIDTH,
            PAGE_HEIGHT,
        )
        regions = {item.block.text: item.region for item in ordered}
        self.assertEqual(regions["header"], "header")
        self.assertEqual(regions["body"], "body")
        self.assertEqual(regions["footer"], "footer")
        self.assertEqual(regions["span"], "body")

    def test_table_overlap_is_marked_and_text_is_kept(self):
        """落在表格框里的文字保留，并带 overlaps_table。"""
        document = build_document(
            parser="pymupdf",
            paper_id="example",
            sha256="abc",
            source_name="example.pdf",
            page=2,
            page_width=PAGE_WIDTH,
            page_height=PAGE_HEIGHT,
            placed=[
                block(60, 200, 250, 230, "inside"),
                block(320, 200, 560, 230, "outside"),
            ],
            tables=[{"bbox": [50, 180, 280, 260], "rows": 2, "cols": 2}],
            table_error=None,
        )
        by_text = {item["text"]: item for item in document["blocks"]}
        self.assertTrue(by_text["inside"]["overlaps_table"])
        self.assertFalse(by_text["outside"]["overlaps_table"])
        self.assertEqual(document["table_error"], None)

    def test_parser_directories_stay_separate(self):
        """pymupdf 和 mineru 写到不同目录，JSON 里的 parser 与目录一致。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for parser in ("pymupdf", "mineru"):
                document = build_document(
                    parser=parser,
                    paper_id="example",
                    sha256="abc",
                    source_name="example.pdf",
                    page=2,
                    page_width=PAGE_WIDTH,
                    page_height=PAGE_HEIGHT,
                    placed=[block(55, 100, 290, 130, "L")],
                    tables=[],
                    table_error=None,
                )
                json_path, text_path = write_page_dump(root, document)
                self.assertEqual(json_path.parent.as_posix(), f"{root.as_posix()}/{parser}/example")
                self.assertEqual(json_path.name, "page-002.json")
                saved = json.loads(json_path.read_text(encoding="utf-8"))
                self.assertEqual(saved["parser"], parser)
                self.assertIn("parser: " + parser, text_path.read_text(encoding="utf-8"))

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

    def test_unknown_paper_id_is_rejected(self):
        """抽查页里的 paper_id 必须在清单中。"""
        manifest = {"papers": [{"paper_id": "huang-gpipe"}]}
        with self.assertRaises(PdfMatchError):
            papers_for_pages(manifest, {"not-a-paper": [2]})
