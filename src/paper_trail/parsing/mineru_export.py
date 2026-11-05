"""用 MinerU 导出指定页，并写成与 PyMuPDF 相同的 JSON。"""

from html.parser import HTMLParser

from paper_trail.parsing.dump import build_document, locate_pdfs, write_index, write_page_dump
from paper_trail.parsing.order import PlacedBlock

PARSER_NAME = "mineru"
TIER = "standard"

# 这些块下面还有子块。文字块的 content 是行内 span，不在这里展开。
_CONTAINERS = {"image", "table", "chart", "code", "list", "index"}
_IMAGE_TYPES = {"image", "image_body", "chart", "chart_body"}


def _type_name(block) -> str:
    """取出块类型的字符串。枚举和普通字符串都能用。"""
    raw = getattr(block, "type", "")
    return str(getattr(raw, "value", raw))


def _span_text(span) -> str:
    """把一个行内 span 收成字符串。链接只保留可见文字。"""
    content = getattr(span, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_span_text(child) for child in content)
    return ""


def _block_text(block) -> str:
    """取出叶子块的文字。表格正文保留 HTML。"""
    content = getattr(block, "content", None)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "".join(_span_text(span) for span in content).strip()
    return ""


class _TableShape(HTMLParser):
    """数 HTML 表格的行数，以及最宽一行的单元格数。"""

    def __init__(self) -> None:
        super().__init__()
        self.rows = 0
        self.cols = 0
        self._in_row = False
        self._row_cols = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.rows += 1
            self._in_row = True
            self._row_cols = 0
            return
        if tag not in {"td", "th"} or not self._in_row:
            return
        span = 1
        for key, value in attrs:
            if key == "colspan" and value:
                try:
                    span = max(int(value), 1)
                except ValueError:
                    span = 1
        self._row_cols += span
        self.cols = max(self.cols, self._row_cols)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr":
            self._in_row = False


def _table_shape(html: str) -> tuple[int, int] | None:
    """从表格 HTML 得到行数和列数。没有 tr 时返回 None。"""
    counter = _TableShape()
    counter.feed(html)
    if counter.rows == 0 or counter.cols == 0:
        return None
    return counter.rows, counter.cols


def _points(bbox: tuple[float, float, float, float], page_width: float, page_height: float) -> tuple[float, float, float, float]:
    """MinerU 的框是相对页宽、页高的 0–1 坐标，原点在左上，y 向下。"""
    x0, y0, x1, y1 = bbox
    return (x0 * page_width, y0 * page_height, x1 * page_width, y1 * page_height)


def _leaves(block):
    """展开图、表、列表，得到带文字或图片的叶子块。"""
    type_name = _type_name(block)
    content = getattr(block, "content", None)
    if type_name in _CONTAINERS and isinstance(content, list) and content:
        for child in content:
            yield from _leaves(child)
        return
    yield block


def blocks_from_middle(
    blocks,
    page_width: float,
    page_height: float,
) -> tuple[list[PlacedBlock], list[dict], str | None]:
    """把 MinerU 的一页换成坐标块和表格框。"""
    placed = []
    tables = []
    errors = []
    for block in blocks:
        for leaf in _leaves(block):
            bbox = getattr(leaf, "bbox", None)
            if bbox is None:
                continue
            type_name = _type_name(leaf)
            text = _block_text(leaf)
            x0, y0, x1, y1 = _points(tuple(bbox), page_width, page_height)
            if type_name == "table_body":
                shape = _table_shape(text)
                if shape is None:
                    rows, cols = 0, 0
                    errors.append("表格 HTML 里没有可数的行")
                else:
                    rows, cols = shape
                tables.append(
                    {
                        "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                        "rows": rows,
                        "cols": cols,
                    }
                )
            if type_name in _IMAGE_TYPES:
                placed.append(PlacedBlock(x0, y0, x1, y1, text, "image"))
                continue
            if text:
                placed.append(PlacedBlock(x0, y0, x1, y1, text, "text"))
    table_error = "；".join(errors) if errors else None
    return placed, tables, table_error


def _page_range(page_numbers: list[int]) -> str:
    """MinerU 的页范围是从 1 开始的逗号分隔页码。"""
    return ",".join(str(number) for number in page_numbers)


def export_mineru(papers: list[dict], pages_by_paper: dict[str, list[int]], raw_dir, parsed_dir) -> list:
    """核对 sha256 后，把指定页写到 data/parsed/mineru/。"""
    import pymupdf
    from mineru.parser import MinerUParser

    pdfs = locate_pdfs(papers, raw_dir)
    written = []
    index_entries = []
    parser = MinerUParser(tier=TIER)
    try:
        for paper in papers:
            paper_id = paper["paper_id"]
            page_numbers = pages_by_paper[paper_id]
            pdf_path = pdfs[paper_id]
            result = parser.parse(pdf_path, page_range=_page_range(page_numbers))
            by_index = {page.page_idx: page for page in result.pages}
            document = pymupdf.open(pdf_path)
            try:
                for page_number in page_numbers:
                    if page_number < 1 or page_number > document.page_count:
                        raise ValueError(f"{paper_id} 没有第 {page_number} 页")
                    middle_page = by_index.get(page_number - 1)
                    if middle_page is None:
                        raise ValueError(f"{paper_id} 的 MinerU 结果里没有第 {page_number} 页")
                    pdf_page = document[page_number - 1]
                    placed, tables, table_error = blocks_from_middle(
                        middle_page.blocks,
                        float(pdf_page.rect.width),
                        float(pdf_page.rect.height),
                    )
                    payload = build_document(
                        parser=PARSER_NAME,
                        paper_id=paper_id,
                        sha256=paper["sha256"],
                        source_name=pdf_path.name,
                        page=page_number,
                        page_width=float(pdf_page.rect.width),
                        page_height=float(pdf_page.rect.height),
                        placed=placed,
                        tables=tables,
                        table_error=table_error,
                    )
                    written.extend(write_page_dump(parsed_dir, payload))
                index_entries.append(
                    {
                        "paper_id": paper_id,
                        "sha256": paper["sha256"],
                        "source_name": pdf_path.name,
                        "pages": list(page_numbers),
                    }
                )
            finally:
                document.close()
    finally:
        parser.close()
    written.append(write_index(parsed_dir, PARSER_NAME, index_entries))
    return written
