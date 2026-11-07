"""仓库路径和索引位置。"""

import os
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
BGE_M3_DIR = Path(os.environ.get("PAPER_TRAIL_BGE_M3", r"D:\code\models\bge-m3"))
VECTOR_INDEX_PATH = INDEXES_DIR / "dense" / "index.json"
VECTOR_MATRIX_PATH = INDEXES_DIR / "dense" / "vectors.npy"
VECTOR_QUERY_PATH = INDEXES_DIR / "dense" / "last_query.json"
RRF_QUERY_PATH = INDEXES_DIR / "rrf" / "last_query.json"
BGE_RERANKER_DIR = Path(os.environ.get("PAPER_TRAIL_BGE_RERANKER", r"D:\code\models\bge-reranker-v2-m3"))
RERANK_QUERY_PATH = INDEXES_DIR / "rerank" / "last_query.json"
