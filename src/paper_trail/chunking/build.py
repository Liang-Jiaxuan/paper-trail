"""把 MinerU middle JSON 收成可检索的 chunk。"""

import json
import re
from pathlib import Path

CHUNK_VERSION = 2
MAX_CHARS = 800

_DATA_IMAGE = re.compile(
    r"""<img\b[^>]*\bsrc=["']data:image/[^"']*["'][^>]*>""",
    re.IGNORECASE,
)
_SENTENCE_BREAK = re.compile(r"。|(?<=[.!?])\s+(?=[A-Z])")
_HTML_TAG = re.compile(r"<[^>]+>")
_TABLE_ROW = re.compile(r"<tr\b", re.IGNORECASE)

# 页眉、页脚、页码、脚注不进正文。
_SKIP_TYPES = {"header", "footer", "page_number", "page_footnote"}
_TITLE_TYPES = {"doc_title", "paragraph_title"}
_INLINE_TYPES = {"text", "equation_inline"}
_HYPHEN = re.compile(r"-{2,}")


def inline_text(node) -> str:
    """按块内顺序拼出可见文字。行内公式保留 LaTeX，表格保留 HTML。"""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        parts = [inline_text(item) for item in node]
        block_level = any(
            isinstance(item, dict) and item.get("type") not in _INLINE_TYPES for item in node
        )
        if block_level:
            return "\n".join(part for part in parts if part)
        return "".join(parts)
    if isinstance(node, dict):
        return inline_text(node.get("content"))
    return ""


def join_text(previous: str, following: str) -> str:
    """把续写接到上一段末尾。行末连字符保留，例如 itera- 接 tions。"""
    if not previous:
        return following
    if not following:
        return previous
    if previous[-1].isspace() or following[0].isspace():
        return previous + following
    return previous + following if previous.endswith("-") else previous + " " + following


def _strip_data_images(text: str) -> str:
    """去掉嵌在 HTML 里的 data:image。图注留在后面的文字里。"""
    return _DATA_IMAGE.sub("", text)


def _row_count(text: str) -> int:
    return len(_TABLE_ROW.findall(text))


def _plain_from_html(html: str) -> str:
    """一行假表里的正文。标签去掉，单元格之间留空格。"""
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</t[dh]>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr>", "\n", text, flags=re.IGNORECASE)
    text = _HTML_TAG.sub("", text)
    for source, target in (
        ("&#x27;", "'"),
        ("&quot;", '"'),
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
    ):
        text = text.replace(source, target)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _sentences(text: str) -> list[str]:
    """在句号后切开。Fig. 5 和 1.5 这种点号后面不是大写字母，不切。"""
    parts = []
    start = 0
    for match in _SENTENCE_BREAK.finditer(text):
        end = match.end() if match.group(0).startswith("。") else match.start()
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        start = match.end()
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _hard_cut(text: str) -> list[str]:
    """一句自己超过上限时按字符切开，相邻块不重叠。"""
    return [text[index : index + MAX_CHARS] for index in range(0, len(text), MAX_CHARS)]


def _pack(sentences: list[str]) -> list[str]:
    """把句子装进不超过 MAX_CHARS 的块。"""
    groups = []
    buffer = ""
    for sentence in sentences:
        pieces = _hard_cut(sentence) if len(sentence) > MAX_CHARS else [sentence]
        for piece in pieces:
            if not buffer:
                buffer = piece
            elif len(buffer) + 1 + len(piece) <= MAX_CHARS:
                buffer = f"{buffer} {piece}"
            else:
                groups.append(buffer)
                buffer = piece
    if buffer:
        groups.append(buffer)
    return groups


def _prose_pieces(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    pieces = _pack(_sentences(text))
    return pieces or [text]


def _pieces_for(chunk: dict, text: str) -> list[str]:
    """正文和参考文献超长才按句号拆。多行表和短表保留 HTML。"""
    if chunk["block_type"] in {"text", "ref_text"}:
        return _prose_pieces(text)
    if chunk["block_type"] == "table" and _row_count(text) <= 1:
        plain = _plain_from_html(text)
        if len(plain) > MAX_CHARS:
            return _prose_pieces(plain)
    return [text]


def _expand(chunks: list[dict]) -> list[dict]:
    """先去掉 data:image，再把超长正文拆开，最后重排序号和 chunk_id。"""
    expanded = []
    for chunk in chunks:
        text = _strip_data_images(chunk["text"])
        flag = chunk["_has_doc_title"]
        pieces = _pieces_for(chunk, text)
        for piece in pieces:
            item = {key: value for key, value in chunk.items() if key != "_has_doc_title"}
            item["text"] = piece
            item["section_path"] = list(chunk["section_path"])
            item["_has_doc_title"] = flag
            expanded.append(item)
    for index, item in enumerate(expanded):
        flag = item.pop("_has_doc_title")
        item["sequence"] = index
        item["chunk_id"] = _chunk_id(item["paper_id"], item["section_path"], flag, index)
    return expanded


def _slug(text: str) -> str:
    """标题变成 ID 里的一段。只留小写字母和数字。"""
    lowered = "".join(char.lower() if char.isalnum() else "-" for char in text)
    return _HYPHEN.sub("-", lowered).strip("-") or "untitled"


def _chunk_id(paper_id: str, section_path: list[str], has_doc_title: bool, sequence: int) -> str:
    """paper_id、当前小节和序号。文档标题不写入 ID。"""
    sections = section_path[1:] if has_doc_title else section_path
    number = f"{sequence:04d}"
    path = "/".join(_slug(part) for part in sections)
    if path:
        return f"{paper_id}/{path}/{number}"
    return f"{paper_id}/{number}"


def chunks_from_document(document: dict) -> list[dict]:
    """按块顺序生成 chunk。continues_prev 的正文接回前面最后一段正文。"""
    paper_id = document["paper_id"]
    sha256 = document["sha256"]
    section_path: list[str] = []
    has_doc_title = False
    chunks: list[dict] = []
    last_text: int | None = None

    for page in document["middle"]["pages"]:
        page_number = int(page["page_idx"]) + 1
        for block in page["blocks"]:
            block_type = block.get("type")
            if block_type in _SKIP_TYPES:
                continue
            text = inline_text(block.get("content"))
            if block_type in _TITLE_TYPES:
                if block_type == "doc_title":
                    section_path = [text]
                    has_doc_title = True
                elif has_doc_title:
                    section_path = [section_path[0], text]
                else:
                    section_path = [text]
                chunks.append(
                    _make_chunk(
                        paper_id, sha256, section_path, has_doc_title, len(chunks), page_number, block_type, text
                    )
                )
                continue
            if block_type == "text" and block.get("continues_prev") and last_text is not None:
                target = chunks[last_text]
                target["text"] = join_text(target["text"], text)
                target["end_page"] = max(target["end_page"], page_number)
                continue
            chunks.append(
                _make_chunk(
                    paper_id, sha256, section_path, has_doc_title, len(chunks), page_number, block_type, text
                )
            )
            if block_type == "text":
                last_text = len(chunks) - 1
    return _expand(chunks)


def _make_chunk(paper_id, sha256, section_path, has_doc_title, sequence, page_number, block_type, text) -> dict:
    path = list(section_path)
    return {
        "chunk_id": _chunk_id(paper_id, path, has_doc_title, sequence),
        "paper_id": paper_id,
        "sha256": sha256,
        "section_path": path,
        "sequence": sequence,
        "start_page": page_number,
        "end_page": page_number,
        "block_type": block_type,
        "text": text,
        "_has_doc_title": has_doc_title,
    }


def chunk_document(document: dict) -> dict:
    """一篇论文的 chunk 文件内容。"""
    return {
        "chunk_version": CHUNK_VERSION,
        "paper_id": document["paper_id"],
        "sha256": document["sha256"],
        "chunks": chunks_from_document(document),
    }


def write_chunks(parsed_dir: Path, chunks_dir: Path) -> list[Path]:
    """按解析索引写出 data/chunks/<paper_id>.json。"""
    index_path = parsed_dir / "mineru" / "index.json"
    if not index_path.is_file():
        raise FileNotFoundError(f"找不到解析索引：{index_path}")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    chunks_dir.mkdir(parents=True, exist_ok=True)
    written = []
    entries = []
    for paper in index["papers"]:
        source = parsed_dir / "mineru" / f"{paper['paper_id']}.json"
        document = json.loads(source.read_text(encoding="utf-8"))
        payload = chunk_document(document)
        path = chunks_dir / f"{paper['paper_id']}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(path)
        entries.append(
            {
                "paper_id": paper["paper_id"],
                "sha256": paper["sha256"],
                "chunks": len(payload["chunks"]),
            }
        )
    index_out = chunks_dir / "index.json"
    index_out.write_text(
        json.dumps({"chunk_version": CHUNK_VERSION, "papers": entries}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    written.append(index_out)
    return written
