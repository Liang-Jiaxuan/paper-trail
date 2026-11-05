"""按 sha256 核对 PDF，并把 MinerU 的 middle JSON 写成一篇一个文件。"""

import hashlib
import json
import shutil
from pathlib import Path

DUMP_VERSION = 2
PARSER_NAME = "mineru"


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


def selected_papers(manifest: dict) -> list[dict]:
    """按清单顺序取出 status 为 selected 的论文。"""
    return [paper for paper in manifest["papers"] if paper.get("status") == "selected"]


def page_numbers(middle: dict) -> list[int]:
    """middle 里的 page_idx 从 0 开始，这里改成从 1 开始的页码。"""
    return [int(page["page_idx"]) + 1 for page in middle["pages"]]


def wrap_middle(paper: dict, source_name: str, middle: dict) -> dict:
    """在 MinerU 的 middle JSON 外包上清单身份。不改 middle 里的块。"""
    return {
        "dump_version": DUMP_VERSION,
        "parser": PARSER_NAME,
        "paper_id": paper["paper_id"],
        "sha256": paper["sha256"],
        "source_name": source_name,
        "middle": middle,
    }


def clear_paper_dir(parsed_dir: Path, paper_id: str) -> None:
    """删掉旧的按页目录。同名路径要写成整篇 JSON，目录还在时写不进去。"""
    folder = parsed_dir / PARSER_NAME / paper_id
    if folder.is_dir():
        shutil.rmtree(folder)


def write_paper_dump(parsed_dir: Path, document: dict) -> Path:
    """写入 data/parsed/mineru/<paper_id>.json。"""
    folder = parsed_dir / PARSER_NAME
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{document['paper_id']}.json"
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def remove_index(parsed_dir: Path, parser: str) -> None:
    """导出开始前删掉旧索引。中途失败时没有 index.json，读者不会拿到新旧混合的结果。"""
    path = parsed_dir / parser / "index.json"
    if path.exists():
        path.unlink()


def write_index(parsed_dir: Path, parser: str, entries: list[dict]) -> Path:
    """写入该解析器本次导出的论文和页码。"""
    folder = parsed_dir / parser
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "index.json"
    payload = {"dump_version": DUMP_VERSION, "parser": parser, "papers": entries}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
