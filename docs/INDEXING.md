# 索引

读 `data/chunks/`，为每块的 `text` 各建一份索引。这一阶段有两路：Okapi BM25，以及本地 bge-m3 的稠密向量。查询时用 RRF 把两路名次加在一起，再用本地 bge-reranker-v2-m3 重排，并按留下的 5 条里最高的向量分标记是否拒答。问答还没有。

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

```json
{
  "query": "15.1 PetaFLOPs",
  "top_k": 5,
  "hits": [
    {
      "...": "9 个 chunk 字段，见 CHUNKING.md",
      "bm25_score": 11.608417976766816,
      "rank": 1
    }
  ]
}
```

`"..."` 不是文件里的字段，只表示这里省略了 chunk 的 9 个字段。`hits` 里实际有 5 条。没有 `vec_score`。

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

```json
{
  "query": "15.1 PetaFLOPs",
  "top_k": 5,
  "hits": [
    {
      "...": "9 个 chunk 字段，见 CHUNKING.md",
      "vec_score": 0.6306136846542358,
      "rank": 1
    }
  ]
}
```

`"..."` 同样不是字段。`hits` 里实际有 5 条。没有 `bm25_score`。

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

前三条和第五条是小节标题，文本里没有 `15.1` 或 `PetaFLOPs`。含有完整 `15.1 PetaFLOPs` 的 `shoeybi-megatron-lm/1-introduction/0013` 在索引里，但不在这 5 条中。它在向量全序里是第 20 名，`vec_score` 是 0.5773992538452148。

## RRF

```powershell
python -m paper_trail.indexing rrf query "15.1 PetaFLOPs"
python -m paper_trail.indexing rrf query "15.1 PetaFLOPs" 80
```

第一条命令不改两份索引，也不改上面两份 `last_query.json`。它让每一路先取候选，再按 `1 / (rrf_k + 名次)` 相加，最后留下 5 条，写到 `data/indexes/rrf/last_query.json`。`rrf_k` 是 60。名次从 1 开始，指这一路候选里的位置。某一路没有命中时，那一路的分数和名次是 null，不写成 0，也不抄另一路的名次。融合分只加出现了的那一路。不传最后一个数时，候选深度是 50。传入正整数时，只对这一次查询使用那个深度。第二条命令使用 80。

```json
{
  "query": "15.1 PetaFLOPs",
  "top_k": 5,
  "candidate_k": 50,
  "rrf_k": 60,
  "hits": [
    {
      "...": "9 个 chunk 字段，见 CHUNKING.md",
      "bm25_score": 11.608417976766816,
      "bm25_rank": 1,
      "vec_score": 0.6109329462051392,
      "vec_rank": 4,
      "rrf_score": 0.032018442622950824,
      "rank": 1
    }
  ]
}
```

`"..."` 不是文件里的字段，只表示这里省略了 chunk 的 9 个字段。`hits` 里实际有 5 条。某一路没有命中时，对应的分数和名次是 `null`。下面这次结果用的是默认 50，前 5 条两路都有数。含有完整 `15.1 PetaFLOPs` 的块在向量全序里排第 20，50 盖住这个名次。

| 名次 | 页 | rrf_score | BM25 名次 | bm25_score | 向量名次 | vec_score | chunk_id |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 5 | 0.032018442622950824 | 1 | 11.608417976766816 | 4 | 0.6109329462051392 | `rajbhandari-zero/1-extended-introduction/0034` |
| 2 | 1 | 0.028693528693528692 | 3 | 7.067312054568449 | 18 | 0.5825684070587158 | `shoeybi-megatron-lm/abstract/0005` |
| 3 | 1–2 | 0.028629032258064516 | 2 | 8.452302677384164 | 20 | 0.5773992538452148 | `shoeybi-megatron-lm/1-introduction/0013` |
| 4 | 8 | 0.025188536953242836 | 5 | 6.664015225446948 | 42 | 0.5636427402496338 | `shoeybi-megatron-lm/6-conclusion-and-future-work/0103` |
| 5 | 6 | 0.0251414204902577 | 26 | 2.9752410817967854 | 14 | 0.5870702266693115 | `shoeybi-megatron-lm/5-1-1-model-and-data-parallelism/0076` |

第一条是 ZeRO 第 5 页那句 “15 Petaflops”。第二条是 Megatron-LM 第 1 页的摘要。第三条是含有完整 `15.1 PetaFLOPs` 的段落，页码 1 到 2。第四条是第 8 页的结论段。第五条是第 6 页的标题 `5.1.1. MODEL AND DATA PARALLELISM`。原先只靠向量排在前面的 `2.2 Algorithm` 不再进入这 5 条。

## 重排

```powershell
python -m paper_trail.indexing rerank query "15.1 PetaFLOPs"
python -m paper_trail.indexing rerank query "15.1 PetaFLOPs" 80
```

模型目录由环境变量 `PAPER_TRAIL_BGE_RERANKER` 指定，未设置时用 `D:\code\models\bge-reranker-v2-m3`。它从 bge-m3 接出，头是一个分类 logit。调用时 `max_length` 是 8192。`rerank_score` 是这个 logit，不再套 sigmoid，也不拿去和 `vec_score` 比。模型结构上限是 8192，微调时用的是 1024。`shoeybi-megatron-lm/c-text-samples/0177` 是 1353 token，超过微调长度，表尾效果可能下降。

第一条命令不改两份索引，也不改 BM25、稠密向量和 RRF 的 `last_query.json`。它重新做一次融合：每一路取候选，默认 50，两路合成的全部块都打分，再留下 5 条，写到 `data/indexes/rerank/last_query.json`。模型只接收查询句和每条的 `text`。`bm25_score`、`vec_score` 和 `rrf_score` 留在记录上，不送进模型。不传最后一个数时深度是 50。传入正整数时，只对这一次查询使用那个深度。第二条命令使用 80。某一路没有命中时，那一路的分数和名次仍是 null。融合名次改存在 `rrf_rank`，`rank` 是重排后的名次。

```json
{
  "query": "15.1 PetaFLOPs",
  "top_k": 5,
  "candidate_k": 50,
  "candidate_count": 95,
  "rrf_k": 60,
  "model": "BAAI/bge-reranker-v2-m3",
  "max_length": 8192,
  "threshold": 0.25,
  "vec_score_max": 0.6109329462051392,
  "refused": false,
  "hits": [
    {
      "...": "9 个 chunk 字段，见 CHUNKING.md",
      "bm25_score": 8.452302677384164,
      "bm25_rank": 2,
      "vec_score": 0.5773992538452148,
      "vec_rank": 20,
      "rrf_score": 0.028629032258064516,
      "rrf_rank": 3,
      "rerank_score": 4.191327095031738,
      "rank": 1
    }
  ]
}
```

`"..."` 不是文件里的字段。`hits` 里实际有 5 条。下面这次用默认深度 50，两路各 50 条，其中 5 个 `chunk_id` 相同，所以合成了 95 条。同时出现在两路前 50 的块，融合分至少是 `1/110 + 1/110`；只出现在一路的块，至多是 `1/61`。所以这 5 条就是融合前 5 名。`rerank_score` 可以大于 1。

| 名次 | 页 | rerank_score | 融合名次 | rrf_score | BM25 名次 | bm25_score | 向量名次 | vec_score | chunk_id |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1–2 | 4.191327095031738 | 3 | 0.028629032258064516 | 2 | 8.452302677384164 | 20 | 0.5773992538452148 | `shoeybi-megatron-lm/1-introduction/0013` |
| 2 | 1 | 2.374574899673462 | 2 | 0.028693528693528692 | 3 | 7.067312054568449 | 18 | 0.5825684070587158 | `shoeybi-megatron-lm/abstract/0005` |
| 3 | 8 | 0.6821727156639099 | 4 | 0.025188536953242836 | 5 | 6.664015225446948 | 42 | 0.5636427402496338 | `shoeybi-megatron-lm/6-conclusion-and-future-work/0103` |
| 4 | 5 | 0.09699694812297821 | 1 | 0.032018442622950824 | 1 | 11.608417976766816 | 4 | 0.6109329462051392 | `rajbhandari-zero/1-extended-introduction/0034` |
| 5 | 1 | 0.07823505997657776 | 11 | 0.015151515151515152 | 6 | 6.294495410967572 | null | null | `rajbhandari-zero/abstract/0006` |

第一条是含有完整 `15.1 PetaFLOPs` 的段落，页码 1 到 2。它在融合里是第 3 名。第二条是 Megatron-LM 第 1 页的摘要。第三条是第 8 页的结论段。第四条是 ZeRO 第 5 页那句 “15 Petaflops”，融合第 1 名落到这里。第五条是 ZeRO 第 1 页的摘要，里面有 “15 Petaflops”；它只在 BM25 候选里，融合名次是 11，向量分数和名次是 null。融合第 5 名的标题 `5.1.1. MODEL AND DATA PARALLELISM` 不再进入这 5 条。

拒答看这 5 条里最高的 `vec_score`，字段是 `vec_score_max`。大于等于 `threshold` 0.25 时 `refused` 为 false，五条都没有向量分时 `vec_score_max` 为 null、`refused` 为 true。`rrf_score` 和 `rerank_score` 不参与。上面这次的最高向量分是第 4 名的 0.6109329462051392，`refused` 是 false。命中仍全部留下。下面三次都是 2026-11-07、`candidate_k` 50，按 0.25 也都放行。

`What is the boiling point of water?` 这 6 篇答不上，`candidate_count` 是 90。5 条里最高的 `vec_score` 是 0.40087148547172546，低于 `15.1 PetaFLOPs` 那次的 0.6109329462051392。

| 名次 | 页 | vec_score | rerank_score | chunk_id |
| --- | --- | --- | --- | --- |
| 1 | 13 | 0.3828029930591583 | -2.874436378479004 | `shoeybi-megatron-lm/c-text-samples/0177` |
| 2 | 14 | 0.38788729906082153 | -3.1859498023986816 | `shoeybi-megatron-lm/c-text-samples/0178` |
| 3 | 23 | 0.3923434615135193 | -4.26680326461792 | `rajbhandari-zero/references/0209` |
| 4 | 24 | 0.3609020709991455 | -5.196231842041016 | `rajbhandari-zero/references/0214` |
| 5 | 25 | 0.40087148547172546 | -5.3026442527771 | `cai-medusa/g-2-flop-s-vs-operational-intensity-variations-in-medusa/0250` |

`super-linear speedup on 400 GPUs` 在语料里，`candidate_count` 是 77。5 条里最高的 `vec_score` 是 0.6945400238037109。第 1 名是 ZeRO 第 5 页 `rajbhandari-zero/1-extended-introduction/0035`，文本里有 “super linear speedup” 和 “64-400 GPUs”。

| 名次 | 页 | vec_score | rerank_score | chunk_id |
| --- | --- | --- | --- | --- |
| 1 | 5 | 0.6945400238037109 | 4.839119911193848 | `rajbhandari-zero/1-extended-introduction/0035` |
| 2 | 1 | 0.6131923198699951 | 2.6205317974090576 | `rajbhandari-zero/abstract/0006` |
| 3 | 17 | 0.6671919226646423 | 1.4718767404556274 | `rajbhandari-zero/10-3-super-linear-scalability/0161` |
| 4 | 23 | 0.603034496307373 | 1.2053837776184082 | `rajbhandari-zero/references/0211` |
| 5 | 24 | 0.5922790765762329 | 0.33146071434020996 | `rajbhandari-zero/references/0215` |

`How many parameters does GPT-4 have?` 这 6 篇也答不上，`candidate_count` 是 82。5 条里最高的 `vec_score` 是第 2 名的 0.6355667114257812，高于 `15.1 PetaFLOPs` 那次的 0.6109329462051392。这条是 Megatron-LM 第 6 页讲 GPT-2 参数规模的段落，没有 GPT-4 的参数量。0.25 低于这次的 0.6355667114257812，也低于 `15.1 PetaFLOPs` 的 0.6109329462051392，两句都会放行。

| 名次 | 页 | vec_score | rerank_score | chunk_id |
| --- | --- | --- | --- | --- |
| 1 | 7 | 0.5298908948898315 | 0.346469521522522 | `shoeybi-megatron-lm/5-2-language-modeling-results-using-gpt-2/0087` |
| 2 | 6 | 0.6355667114257812 | 0.21141931414604187 | `shoeybi-megatron-lm/5-1-scaling-analysis/0074` |
| 3 | 13 | 0.4994128346443176 | -0.11769899725914001 | `shoeybi-megatron-lm/c-text-samples/0177` |
| 4 | 2 | null | -0.512144923210144 | `shoeybi-megatron-lm/1-introduction/0020` |
| 5 | 1 | 0.4986346364021301 | -0.5454120635986328 | `rajbhandari-zero/1-extended-introduction/0008` |

## 还没做

- 还没有按论文过滤。有过滤时拒答检查仍要做，这一步还没写。
- 问答还没有。
- bge-m3 的稀疏向量和多向量还没有用。
