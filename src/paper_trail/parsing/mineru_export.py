"""用 MinerU 导出论文全文，并原样保存 middle JSON。"""

from paper_trail.parsing.dump import (
    PARSER_NAME,
    clear_paper_dir,
    locate_pdfs,
    page_numbers,
    remove_index,
    wrap_middle,
    write_index,
    write_paper_dump,
)

TIER = "standard"


def export_mineru(papers: list[dict], raw_dir, parsed_dir) -> list:
    """核对 sha256 后，把每篇的 middle JSON 写到 data/parsed/mineru/。"""
    from mineru.parser import MinerUParser

    pdfs = locate_pdfs(papers, raw_dir)
    remove_index(parsed_dir, PARSER_NAME)
    written = []
    index_entries = []
    parser = MinerUParser(tier=TIER)
    try:
        for paper in papers:
            paper_id = paper["paper_id"]
            pdf_path = pdfs[paper_id]
            result = parser.parse(pdf_path, page_range="all")
            middle = result.to_dict()
            clear_paper_dir(parsed_dir, paper_id)
            written.append(write_paper_dump(parsed_dir, wrap_middle(paper, pdf_path.name, middle)))
            index_entries.append(
                {
                    "paper_id": paper_id,
                    "sha256": paper["sha256"],
                    "source_name": pdf_path.name,
                    "pages": page_numbers(middle),
                }
            )
    finally:
        parser.close()
    written.append(write_index(parsed_dir, PARSER_NAME, index_entries))
    return written
