"""用 PyMuPDF 导出指定页。MinerU 以后写入旁边的 mineru 目录。"""

import pymupdf

from paper_trail.parsing.dump import build_document, locate_pdfs, write_index, write_page_dump
from paper_trail.parsing.order import PlacedBlock

PARSER_NAME = "pymupdf"

# B0 抽查页。页码从 1 开始。
SPOT_PAGES = {
    "shoeybi-megatron-lm": [2, 6],
    "kwon-pagedattention": [2, 5],
    "huang-gpipe": [2, 3, 4],
    "rajbhandari-zero": [2],
    "cai-medusa": [2, 7],
    "xiao-smoothquant": [2],
}


def blocks_from_page(page) -> tuple[list[PlacedBlock], list[dict], str | None]:
    """抽出文本块、图片块，以及 PyMuPDF 找到的表格框。"""
    placed = []
    for item in page.get_text("blocks"):
        x0, y0, x1, y1, text, _block_no, block_type = item[:7]
        if block_type == 1:
            placed.append(PlacedBlock(x0, y0, x1, y1, "", "image"))
        elif str(text).strip():
            placed.append(PlacedBlock(x0, y0, x1, y1, str(text).strip(), "text"))
    tables = []
    table_error = None
    try:
        finder = page.find_tables()
        for table in finder.tables:
            tables.append(
                {
                    "bbox": [round(float(value), 1) for value in table.bbox],
                    "rows": int(table.row_count),
                    "cols": int(table.col_count),
                }
            )
    except Exception as exc:
        table_error = str(exc)
    return placed, tables, table_error


def export_pymupdf(papers: list[dict], pages_by_paper: dict[str, list[int]], raw_dir, parsed_dir) -> list:
    """核对 sha256 后，把指定页写到 data/parsed/pymupdf/。"""
    pdfs = locate_pdfs(papers, raw_dir)
    written = []
    index_entries = []
    for paper in papers:
        paper_id = paper["paper_id"]
        page_numbers = pages_by_paper[paper_id]
        pdf_path = pdfs[paper_id]
        document = pymupdf.open(pdf_path)
        try:
            for page_number in page_numbers:
                if page_number < 1 or page_number > document.page_count:
                    raise ValueError(f"{paper_id} 没有第 {page_number} 页")
                page = document[page_number - 1]
                placed, tables, table_error = blocks_from_page(page)
                payload = build_document(
                    parser=PARSER_NAME,
                    paper_id=paper_id,
                    sha256=paper["sha256"],
                    source_name=pdf_path.name,
                    page=page_number,
                    page_width=float(page.rect.width),
                    page_height=float(page.rect.height),
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
    written.append(write_index(parsed_dir, PARSER_NAME, index_entries))
    return written
