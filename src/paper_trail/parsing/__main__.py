"""导出 B0 抽查页：python -m paper_trail.parsing [pymupdf|mineru]"""

import json
import sys

from paper_trail import config
from paper_trail.parsing.dump import papers_for_pages
from paper_trail.parsing.pymupdf_export import SPOT_PAGES, export_pymupdf


def main(argv: list[str] | None = None) -> None:
    """读取清单，核对 PDF，并写出一个解析器的抽查页。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1 or (args and args[0] not in {"pymupdf", "mineru"}):
        raise SystemExit("用法: python -m paper_trail.parsing [pymupdf|mineru]")
    parser_name = args[0] if args else "pymupdf"
    manifest = json.loads(config.MANIFEST_PATH.read_text(encoding="utf-8"))
    papers = papers_for_pages(manifest, SPOT_PAGES)
    if parser_name == "mineru":
        from paper_trail.parsing.mineru_export import export_mineru

        written = export_mineru(papers, SPOT_PAGES, config.RAW_PDF_DIR, config.PARSED_DIR)
    else:
        written = export_pymupdf(papers, SPOT_PAGES, config.RAW_PDF_DIR, config.PARSED_DIR)
    print(f"写入 {len(written)} 个文件到 {config.PARSED_DIR / parser_name}")


if __name__ == "__main__":
    main()
