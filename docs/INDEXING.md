# 索引

读 `data/chunks/`，为每块的 `text` 各建一份索引。这一阶段有两路，互不融合：Okapi BM25，以及本地 bge-m3 的稠密向量。重排和问答还没有。

在仓库根目录先激活 `paper-trail` 环境，再执行。建索引前要保证分块结果存在。`data/indexes/` 不提交。

## BM25

```powershell
python -m paper_trail.indexing
python -m paper_trail.indexing query "15.1 PetaFLOPs"
```

第一条命令写出 `data/indexes/bm25/index.json`。第二条命令读这份索引，把前 5 条写到 `data/indexes/bm25/last_query.json`。

```json
{
  "index_version": 1,
  "kind": "bm25",
  "chunk_version": 2,
  "k1": 1.5,
  "b": 0.75,
  "tokenizer": "lowercase-alnum",
  "documents": [ "...1222 条..." ]
}
```

`documents` 有 1222 条，字段和顺序与 chunk 相同，见 [CHUNKING.md](CHUNKING.md)。构建只把原文放进 `documents`，不切词，也不写分数。`k1`、`b` 和分词在查询时才用。

### 分词和打分

小写后保留连续的字母和数字。`8.3` 分成 `8` 和 `3`，`itera-tions` 分成 `itera` 和 `tions`。

`k1` 是 1.5，`b` 是 0.75。逆文档频率是 `ln((N - df + 0.5) / (df + 0.5) + 1)`。查询里有、语料里没有的词不加分。分数为 0 的块不返回。返回的分数字段只有 `bm25_score`。

### 一次查询

查询 `15.1 PetaFLOPs` 被切成 `15`、`1`、`petaflops`。`1` 在语料里很常见。原始结果在 `data/indexes/bm25/last_query.json`。

第一条是 ZeRO 第 5 页，`rajbhandari-zero/1-extended-introduction/0034`，`bm25_score` 是 11.608417976766816。文本是：

```text
38 TFlops per GPU, and aggregate performance over 15 Petaflops. This is more than 10x improvement in training speed compared to SOTA for the same model size.
```

这块较短，含有 `15` 和 `petaflops`，所以排在前面。含有完整 `15.1 PetaFLOPs` 的是第二条，Megatron-LM 第 1 到 2 页，`shoeybi-megatron-lm/1-introduction/0013`，分数 8.452302677384164。

## 稠密向量

先装 CUDA 版 torch，再装 sentence-transformers，避免后者把 torch 换成 CPU 版。本机这次用的是 `torch==2.6.0+cu126` 和 `sentence-transformers==5.7.0`。

```powershell
python -m pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu126
python -m pip install "sentence-transformers>=3,<6"
python -m paper_trail.indexing vectors
python -m paper_trail.indexing vectors query "15.1 PetaFLOPs"
```

第三条命令写出 `data/indexes/dense/index.json` 和 `data/indexes/dense/vectors.npy`。第四条命令把前 5 条写到 `data/indexes/dense/last_query.json`。

模型目录由环境变量 `PAPER_TRAIL_BGE_M3` 指定，未设置时用 `D:\code\models\bge-m3`。查询文本直接编码，不加指令前缀。返回的分数字段只有 `vec_score`。取前 5 条，分数低也照样返回。

```json
{
  "index_version": 1,
  "kind": "dense",
  "model": "BAAI/bge-m3",
  "dimension": 1024,
  "normalized": true,
  "chunk_version": 2,
  "documents": [ "...1222 条..." ]
}
```

`documents` 与 BM25 那份相同，也是 1222 条。构建时先把这 1222 条 `text` 编成 1024 维向量，做 L2 归一化，再写出 `index.json` 和 `vectors.npy`。矩阵在 `data/indexes/dense/vectors.npy`，形状是 `(1222, 1024)`，dtype 是 float32，第 i 行对应 `documents` 的第 i 条。查询时只编码查询句，内积就是余弦相似度。

### 同一次查询

查询仍是 `15.1 PetaFLOPs`。原始结果在 `data/indexes/dense/last_query.json`。

| 名次 | vec_score | chunk_id | 页 | 文本 |
| --- | --- | --- | --- | --- |
| 1 | 0.6306136846542358 | `huang-gpipe/2-2-algorithm/0022` | 3 | 2.2 Algorithm |
| 2 | 0.6296308040618896 | `rajbhandari-zero/7-1-data-parallel-communication-volume/0117` | 13 | 7.1 Data Parallel Communication Volume |
| 3 | 0.6143088936805725 | `huang-gpipe/2-3-performance-optimization/0026` | 3 | 2.3 Performance Optimization |
| 4 | 0.6109329462051392 | `rajbhandari-zero/1-extended-introduction/0034` | 5 | 见下方 |
| 5 | 0.6052886247634888 | `kwon-pagedattention/6-5-chatbot/0166` | 12 | 6.5 Chatbot |

第四条就是 BM25 排在第一的那句：

```text
38 TFlops per GPU, and aggregate performance over 15 Petaflops. This is more than 10x improvement in training speed compared to SOTA for the same model size.
```

前三条和第五条是小节标题，文本里没有 `15.1` 或 `PetaFLOPs`。含有完整 `15.1 PetaFLOPs` 的 `shoeybi-megatron-lm/1-introduction/0013` 在索引里，但不在这 5 条中。

## 还没做

- 向量和 BM25 还没有融合，也没有重排。
- 还没有按论文过滤，也没有拒答阈值。
- 问答还没有。
- bge-m3 的稀疏向量和多向量还没有用。
