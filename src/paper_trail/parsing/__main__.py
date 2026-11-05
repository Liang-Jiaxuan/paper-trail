"""导出已选论文的 MinerU middle JSON：python -m paper_trail.parsing"""

import json
import sys

from paper_trail import config
from paper_trail.parsing.dump import selected_papers

_USAGE = "用法: python -m paper_trail.parsing"


def main(argv: list[str] | None = None) -> None:
    """读取清单，核对 PDF，并写出每篇论文的 middle JSON。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        raise SystemExit(_USAGE)
    manifest = json.loads(config.MANIFEST_PATH.read_text(encoding="utf-8"))
    papers = selected_papers(manifest)
    from paper_trail.parsing.mineru_export import export_mineru

    written = export_mineru(papers, config.RAW_PDF_DIR, config.PARSED_DIR)
    print(f"写入 {len(written)} 个文件到 {config.PARSED_DIR / 'mineru'}")


if __name__ == "__main__":
    main()
