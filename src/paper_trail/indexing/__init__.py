"""从 chunk 构建 BM25 和 bge-m3 稠密向量索引，查询时用 RRF 融合，再用 bge-reranker-v2-m3 重排，并按向量分决定是否拒答。"""
