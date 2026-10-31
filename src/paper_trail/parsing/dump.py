"""把一页的块写成 JSON 和可读文本。目录按解析器分开。"""

import hashlib
import json
from pathlib import Path

from paper_trail.parsing.order import PlacedBlock, overlaps_bbox, order_blocks

DUMP_VERSION = 1


class PdfMatchError(Exception):
    """清单里的论文和 data/raw_pdf 里的文件对不上。"""


def sha256_file(path: Path) -> str:
    """计算文件字节的 SHA-256，返回小写十六进制。"""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def locate_pdfs(papers: list[dict], raw_dir: Path) -> dict[str, Path]:
    """按清单中的 sha256 找到 PDF，不靠文件名。"""
    if not raw_dir.is_dir():
        raise PdfMatchError(f"找不到 PDF 目录：{raw_dir}")
    by_hash: dict[str, Path] = {}
    for path in sorted(raw_dir.glob("*.pdf")):
        digest = sha256_file(path)
        previous = by_hash.get(digest)
        if previous is not None:
            raise PdfMatchError(f"两份 PDF 的 sha256 相同：{previous.name} 与 {path.name}")
        by_hash[digest] = path
    found: dict[str, Path] = {}
    missing = []
    for paper in papers:
        path = by_hash.get(paper["sha256"].lower())
        if path is None:
            missing.append(paper["paper_id"])
        else:
            found[paper["paper_id"]] = path
    if missing:
        raise PdfMatchError("这些论文在 data/raw_pdf 里没有对应文件：" + ", ".join(missing))
    return found


def papers_for_pages(manifest: dict, pages_by_paper: dict[str, list[int]]) -> list[dict]:
    """从清单里取出要导出的论文。"""
    wanted = set(pages_by_paper)
    papers = [paper for paper in manifest["papers"] if paper["paper_id"] in wanted]
    unknown = wanted - {paper["paper_id"] for paper in papers}
    if unknown:
        raise PdfMatchError("清单里没有这些 paper_id：" + ", ".join(sorted(unknown)))
    return papers


def build_document(
    *,
    parser: str,
    paper_id: str,
    sha256: str,
    source_name: str,
    page: int,
    page_width: float,
    page_height: float,
    placed: list[PlacedBlock],
    tables: list[dict],
    table_error: str | None,
) -> dict:
    """组装一页的导出文档。表格内的文字保留，并标记 overlaps_table。"""
    ordered = order_blocks(placed, page_width, page_height)
    blocks = []
    for item in ordered:
        block = item.block
        blocks.append(
            {
                "reading_order": item.reading_order,
                "column": item.column,
                "region": item.region,
                "bbox": [
                    round(block.x0, 1),
                    round(block.y0, 1),
                    round(block.x1, 1),
                    round(block.y1, 1),
                ],
                "text": block.text,
                "kind": block.kind,
                "overlaps_table": any(
                    overlaps_bbox(block, table["bbox"]) for table in tables
                ),
            }
        )
    return {
        "dump_version": DUMP_VERSION,
        "parser": parser,
        "paper_id": paper_id,
        "sha256": sha256,
        "source_name": source_name,
        "page": page,
        "page_width": round(page_width, 1),
        "page_height": round(page_height, 1),
        "blocks": blocks,
        "tables": tables,
        "table_error": table_error,
    }


def render_page_text(document: dict) -> str:
    """把一页文档写成便于对照 PDF 的文本。"""
    lines = [
        f"parser: {document['parser']}",
        f"paper_id: {document['paper_id']}",
        f"page: {document['page']}",
        f"sha256: {document['sha256']}",
        "",
    ]
    for block in document["blocks"]:
        flags = [block["column"], block["region"]]
        if block["kind"] != "text":
            flags.append(block["kind"])
        if block["overlaps_table"]:
            flags.append("overlaps_table")
        bbox = ", ".join(f"{value:.1f}" for value in block["bbox"])
        lines.append(f"[{block['reading_order']}] {' '.join(flags)} ({bbox})")
        if block["text"]:
            lines.append(block["text"])
        lines.append("")
    if document["tables"]:
        lines.append("tables:")
        for table in document["tables"]:
            bbox = ", ".join(f"{value:.1f}" for value in table["bbox"])
            lines.append(f"- ({bbox}) {table['rows']}x{table['cols']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_page_dump(parsed_dir: Path, document: dict) -> tuple[Path, Path]:
    """写入 data/parsed/<parser>/<paper_id>/page-NNN.json 和同名 txt。"""
    folder = parsed_dir / document["parser"] / document["paper_id"]
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"page-{document['page']:03d}"
    json_path = folder / f"{stem}.json"
    text_path = folder / f"{stem}.txt"
    json_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(render_page_text(document), encoding="utf-8")
    return json_path, text_path


def write_index(parsed_dir: Path, parser: str, entries: list[dict]) -> Path:
    """写入该解析器本次导出的论文和页码。"""
    folder = parsed_dir / parser
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "index.json"
    payload = {"dump_version": DUMP_VERSION, "parser": parser, "papers": entries}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
