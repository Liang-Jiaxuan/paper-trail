"""检查 MinerU 的块如何换成现有 JSON，不加载模型。"""

import unittest
from types import SimpleNamespace

from paper_trail.parsing.dump import build_document
from paper_trail.parsing.mineru_export import blocks_from_middle

PAGE_WIDTH = 612.0
PAGE_HEIGHT = 792.0


def span(text):
    """构造一个只有文字的行内 span。"""
    return SimpleNamespace(type="text", content=text)


def text_block(bbox, text):
    """构造一个正文叶子块。"""
    return SimpleNamespace(type="text", bbox=bbox, content=[span(text)])


class MineruBlockTest(unittest.TestCase):
    def test_normalized_bbox_becomes_pdf_points(self):
        """0–1 坐标乘页宽和页高，得到与 PyMuPDF 相同的点。"""
        placed, tables, table_error = blocks_from_middle(
            [text_block((0.1, 0.2, 0.4, 0.5), "Hello")],
            PAGE_WIDTH,
            PAGE_HEIGHT,
        )
        document = build_document(
            parser="mineru",
            paper_id="example",
            sha256="abc",
            source_name="example.pdf",
            page=2,
            page_width=PAGE_WIDTH,
            page_height=PAGE_HEIGHT,
            placed=placed,
            tables=tables,
            table_error=table_error,
        )
        self.assertEqual(document["blocks"][0]["bbox"], [61.2, 158.4, 244.8, 396.0])
        self.assertEqual(document["blocks"][0]["text"], "Hello")
        self.assertEqual(document["parser"], "mineru")

    def test_image_caption_stays_text_and_body_stays_image(self):
        """图块拆成图片和旁边的图注，图注不并进图片文字。"""
        image = SimpleNamespace(
            type="image",
            bbox=(0.5, 0.2, 0.9, 0.6),
            content=[
                SimpleNamespace(type="image_body", bbox=(0.5, 0.2, 0.9, 0.5), content=""),
                SimpleNamespace(
                    type="image_caption",
                    bbox=(0.5, 0.5, 0.9, 0.6),
                    content=[span("Figure 1")],
                ),
            ],
        )
        placed, _, _ = blocks_from_middle([image], PAGE_WIDTH, PAGE_HEIGHT)
        kinds = [(block.kind, block.text) for block in placed]
        self.assertEqual(kinds, [("image", ""), ("text", "Figure 1")])

    def test_table_html_keeps_rows_and_text(self):
        """表格 HTML 留在正文里，并记下行数和含 colspan 的列数。"""
        html = "<table><tr><th colspan='2'>H</th></tr><tr><td>a</td><td>b</td></tr></table>"
        table = SimpleNamespace(
            type="table",
            bbox=(0.1, 0.1, 0.4, 0.3),
            content=[
                SimpleNamespace(type="table_body", bbox=(0.1, 0.1, 0.4, 0.25), content=html),
                SimpleNamespace(
                    type="table_caption",
                    bbox=(0.1, 0.25, 0.4, 0.3),
                    content=[span("Table 1")],
                ),
            ],
        )
        placed, tables, table_error = blocks_from_middle([table], PAGE_WIDTH, PAGE_HEIGHT)
        document = build_document(
            parser="mineru",
            paper_id="example",
            sha256="abc",
            source_name="example.pdf",
            page=6,
            page_width=PAGE_WIDTH,
            page_height=PAGE_HEIGHT,
            placed=placed,
            tables=tables,
            table_error=table_error,
        )
        self.assertEqual(tables, [{"bbox": [61.2, 79.2, 244.8, 198.0], "rows": 2, "cols": 2}])
        self.assertIsNone(table_error)
        self.assertEqual(placed[0].text, html)
        self.assertEqual(placed[1].text, "Table 1")
        self.assertTrue(document["blocks"][0]["overlaps_table"])

    def test_unlistable_table_still_exports_text(self):
        """HTML 里没有行时记下原因，框仍然保留。"""
        table = SimpleNamespace(
            type="table_body",
            bbox=(0.1, 0.1, 0.2, 0.2),
            content="not a table",
        )
        placed, tables, table_error = blocks_from_middle([table], PAGE_WIDTH, PAGE_HEIGHT)
        self.assertEqual(placed[0].text, "not a table")
        self.assertEqual(tables[0]["rows"], 0)
        self.assertEqual(tables[0]["cols"], 0)
        self.assertEqual(table_error, "表格 HTML 里没有可数的行")

    def test_list_emits_children_once(self):
        """列表只导出子块，不把父块再写一遍。"""
        listing = SimpleNamespace(
            type="list",
            bbox=(0.1, 0.1, 0.4, 0.4),
            content=[text_block((0.1, 0.1, 0.4, 0.2), "only child")],
        )
        placed, _, _ = blocks_from_middle([listing], PAGE_WIDTH, PAGE_HEIGHT)
        self.assertEqual([block.text for block in placed], ["only child"])
