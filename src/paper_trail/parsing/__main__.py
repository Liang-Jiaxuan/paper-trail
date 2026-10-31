"""导出 B0 抽查页：python -m paper_trail.parsing"""

import json

from paper_trail import config
from paper_trail.parsing.dump import papers_for_pages
from paper_trail.parsing.pymupdf_export import PARSER_NAME, SPOT_PAGES, export_pymupdf


def main() -> None:
    """读取清单，核对 PDF，并写出 PyMuPDF 抽查页。"""
    manifest = json.loads(config.MANIFEST_PATH.read_text(encoding="utf-8"))
    papers = papers_for_pages(manifest, SPOT_PAGES)
    written = export_pymupdf(papers, SPOT_PAGES, config.RAW_PDF_DIR, config.PARSED_DIR)
    print(f"写入 {len(written)} 个文件到 {config.PARSED_DIR / PARSER_NAME}")


if __name__ == "__main__":
    main()
