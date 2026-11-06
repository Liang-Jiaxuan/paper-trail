# BM25 索引

读 `data/chunks/`，为每块的 `text` 建一份 Okapi BM25 索引。这一阶段只有关键词检索。向量索引、RRF 和问答还没有。

## 运行

在仓库根目录先激活 `paper-trail` 环境，再执行。第一条命令执行前要保证分块结果存在。

```powershell
python -m paper_trail.indexing
python -m paper_trail.indexing query "15.1 PetaFLOPs"
```

第一条写出 `data/indexes/bm25/index.json`。第二条读这份索引，把前 5 条写到 `data/indexes/bm25/last_query.json`。`data/indexes/` 不提交。

当前这份索引的 `index_version` 是 1，`kind` 是 `bm25`，`chunk_version` 是 2，共 1222 块。

## 分词和打分

小写后保留连续的字母和数字。`8.3` 分成 `8` 和 `3`，`itera-tions` 分成 `itera` 和 `tions`。

`k1` 是 1.5，`b` 是 0.75。逆文档频率是 `ln((N - df + 0.5) / (df + 0.5) + 1)`。查询里有、语料里没有的词不加分。分数为 0 的块不返回。返回的分数字段只有 `bm25_score`。

## 一次查询

查询 `15.1 PetaFLOPs` 被切成 `15`、`1`、`petaflops`。`1` 在语料里很常见。原始结果在 `data/indexes/bm25/last_query.json`。

第一条是 ZeRO 第 5 页，`rajbhandari-zero/1-extended-introduction/0034`，`bm25_score` 是 11.608417976766816。文本是：

```text
38 TFlops per GPU, and aggregate performance over 15 Petaflops. This is more than 10x improvement in training speed compared to SOTA for the same model size.
```

这块较短，含有 `15` 和 `petaflops`，所以排在前面。含有完整 `15.1 PetaFLOPs` 的是第二条，Megatron-LM 第 1 到 2 页，`shoeybi-megatron-lm/1-introduction/0013`，分数 8.452302677384164。

## 还没做

- 向量索引还没有，同一批 chunk 还没有嵌入。
- 向量和 BM25 还没有融合，也没有重排。
- 还没有按论文过滤，也没有拒答阈值。
- 问答还没有。
