"""仓库路径。检索和模型参数在对应阶段再加入。"""

from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parents[1]

DATA_DIR = PROJECT_ROOT / "data"
MANIFEST_PATH = DATA_DIR / "manifest.json"
RAW_PDF_DIR = DATA_DIR / "raw_pdf"
PARSED_DIR = DATA_DIR / "parsed"
CHUNKS_DIR = DATA_DIR / "chunks"
INDEXES_DIR = DATA_DIR / "indexes"
BM25_INDEX_PATH = INDEXES_DIR / "bm25" / "index.json"
BM25_QUERY_PATH = INDEXES_DIR / "bm25" / "last_query.json"
