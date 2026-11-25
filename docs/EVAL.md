# 评测题

10 道题在 `data/eval/questions.json`。这些题是手写的，用来对照检索结果。外层只有 `question_version` 和 `questions`。`question_version` 现在是 1，表示这一版题的字段形状。

每题有 `id`、`query` 和 `passages`。`id` 是这道题的固定名字。`query` 是英文问句，不要求含有整段证据。`passages` 里每一处是一处可接受的段落，字段是 `chunk_id`、`paper_id`、`start_page`、`end_page` 和 `evidence`。`chunk_id` 以 `paper_id/` 开头。`evidence` 是那一块 `text` 里的原样子串。同一题的几处都算对。

这些字符串从 `data/chunks/` 的块文本里核对后原样抄入。2026-11-19 核对过 15 处。`tests/test_questions.py` 只检查形状：版本是 1、10 个不重复的 `id`、问句和证据非空、`chunk_id` 前缀、结束页不早于起始页。测试不打开块文件，也不跑检索。

`python -m paper_trail.evaluation` 读取这份文件，全库重排后写入 `data/eval/retrieval.json`。它不写 `data/indexes/rerank/last_query.json`，也不写 `data/answers/last_answer.json`，也不调用概括模型。`python -m paper_trail.evaluation answers` 读 `retrieval.json`，按 `chunk_id` 从 `data/chunks/` 取回正文，再写 `data/eval/answers.json`。它不改 `retrieval.json` 和 `last_answer.json`。

`megatron-15-1-petaflops` 的问句是 8.3 billion 参数、512 GPU 上的 PetaFLOPs，三处证据都是 `15.1 PetaFLOPs`：摘要第 1 页 `shoeybi-megatron-lm/abstract/0005`，引言第 1–2 页 `shoeybi-megatron-lm/1-introduction/0013`，结论第 8 页 `shoeybi-megatron-lm/6-conclusion-and-future-work/0103`。

`zero-400-gpus` 有两处，字符串不同。摘要第 1 页 `rajbhandari-zero/abstract/0006` 的证据是 `super-linear speedup on 400 GPUs`。第 5 页 `rajbhandari-zero/1-extended-introduction/0035` 的证据是 `64-400 GPUs`。

`pagedattention-internal-fragmentation` 只收了解释原因的两块：第 2 页 `kwon-pagedattention/1-introduction/0016`，第 4 页 `kwon-pagedattention/3-1-memory-management-in-existing-systems/0057`。证据都是 `internal fragmentation`。

其余各题只有一处：

| id | 页 | 证据 |
| --- | --- | --- |
| `megatron-first-gemm` | 4 | `partition the first GEMM in this column parallel fashion` |
| `megatron-two-all-reduces` | 4 | `only two all-reduces in the forward path and two in the backward path` |
| `zero-name` | 1 和 2 | `Zero Redundancy Optimizer` |
| `gpipe-micro-batches` | 3 | `divides every mini-batch of size N into M equal micro-batches` |
| `medusa-head` | 3 | `a single layer of feed-forward network with a residual connection` |
| `medusa-frozen-backbone` | 1 | `frozen backbone LLM` |
| `smoothquant-scaling` | 2 | `mathematically equivalent per-channel scaling transformation` |

转述、要看图才能回答、或块里对不上这串字的说法，没有写成题。

## 怎么跑

在仓库根目录、`paper-trail` 环境里执行。BM25 索引、稠密向量索引和本地重排模型要已经在。

```powershell
$env:PYTHONPATH = "src"
python -m paper_trail.evaluation
```

bge-m3 只加载一次，编完 10 条问句后卸掉。bge-reranker-v2-m3 也只加载一次，再给 10 题打分。每题两路各取 50 条，`paper_ids` 是 null，融合后的全部候选都重排，留下 5 条。

结果文件不存块正文。每条有名次、分数、`chunk_id` 和页码，外加 `matched`。`matched` 只在这条的 `chunk_id` 等于某一处证据时，写下那个 `chunk_id`。

`tests/test_evaluation.py` 只用假命中检查 `chunk_id`，不加载模型。同一页上的另一个 `chunk_id` 算未中。

## 命中

前 5 条里出现某一处 `passages` 的 `chunk_id`，这道题的 `hit` 就是 true。同一页上的其他块不算。

## 2026-11-19 的结果

`retrieval.json` 里 `question_version` 是 1，`candidate_k` 是 50，`top_k` 是 5，`paper_ids` 是 null，`rrf_k` 是 60，`model` 是 `BAAI/bge-reranker-v2-m3`，`max_length` 是 8192。`hit_count` 是 9，`question_count` 是 10。下面的分数都从这份文件抄来。名次和分数仍是 2026-11-19 那次重排，`hit` 和 `matched` 改按 `chunk_id` 重算，没有再跑模型。

`megatron-15-1-petaflops` 命中。三处证据块都在前 5 条里。

- 第 1 名 `shoeybi-megatron-lm/abstract/0005`，第 1 页，`rerank_score` 5.594396591186523，`rrf_rank` 1，`rrf_score` 0.032266458495966696，BM25 名次 1，`bm25_score` 27.26429443073144，向量名次 3，`vec_score` 0.6789646148681641。`matched` 是 `shoeybi-megatron-lm/abstract/0005`。
- 第 2 名 `shoeybi-megatron-lm/1-introduction/0013`，第 1–2 页，`rerank_score` 5.538087844848633，`rrf_rank` 3，`rrf_score` 0.03177805800756621，BM25 名次 5，`bm25_score` 21.34842597569422，向量名次 1，`vec_score` 0.6854450702667236。`matched` 是 `shoeybi-megatron-lm/1-introduction/0013`。
- 第 3 名 `rajbhandari-zero/10-6-turing-nlg-the-sota-language-model-with-17b-parameters/0176`，第 19 页，`rerank_score` 4.059257984161377，`rrf_rank` 17，`rrf_score` 0.024152480721664482，BM25 名次 19，`bm25_score` 14.903788988428989，向量名次 27，`vec_score` 0.5743842720985413。`matched` 是空的。
- 第 4 名 `shoeybi-megatron-lm/6-conclusion-and-future-work/0103`，第 8 页，`rerank_score` 3.573637008666992，`rrf_rank` 4，`rrf_score` 0.030309988518943745，BM25 名次 7，`bm25_score` 20.797482740713235，向量名次 5，`vec_score` 0.6624119877815247。`matched` 是 `0103`。
- 第 5 名 `rajbhandari-zero/10-2-speed-and-model-size/0157`，第 17 页，`rerank_score` 2.331556797027588，`rrf_rank` 8，`rrf_score` 0.02862400327131466，BM25 名次 13，`bm25_score` 17.084148868663643，向量名次 7，`vec_score` 0.6556016206741333。`matched` 是空的。

`megatron-first-gemm` 命中。第 1 名就是证据块。第 2、3 名也在第 4 页，`chunk_id` 不同，`matched` 是空的。

- 第 1 名 `shoeybi-megatron-lm/3-model-parallel-transformers/0049`，第 4 页，`rerank_score` 2.467456340789795，`rrf_rank` 2，`rrf_score` 0.03225806451612903，BM25 名次 2，`bm25_score` 18.625983988786384，向量名次 2，`vec_score` 0.6184573173522949。`matched` 是 `0049`。
- 第 2 名 `shoeybi-megatron-lm/3-model-parallel-transformers/0042`，第 4 页，`rerank_score` 0.2425413876771927，`rrf_rank` 1，`rrf_score` 0.03278688524590164，BM25 名次 1，`bm25_score` 25.36886808277289，向量名次 1，`vec_score` 0.628649115562439。`matched` 是空的。
- 第 3 名 `shoeybi-megatron-lm/3-model-parallel-transformers/0053`，第 4 页，`rerank_score` 0.04031688719987869，`rrf_rank` 17，`rrf_score` 0.02408450704225352，BM25 名次 40，`bm25_score` 8.914132748899249，向量名次 11，`vec_score` 0.5219227075576782。`matched` 是空的。
- 第 4 名 `rajbhandari-zero/1-extended-introduction/0010`，第 2 页，`rerank_score` -0.6655082702636719，`rrf_rank` 7，`rrf_score` 0.028665028665028666，BM25 名次 14，`bm25_score` 11.869791446312314，向量名次 6，`vec_score` 0.5727797746658325。`matched` 是空的。
- 第 5 名 `kwon-pagedattention/4-6-distributed-execution/0111`，第 8–9 页，`rerank_score` -1.4846619367599487，`rrf_rank` 4，`rrf_score` 0.03125，BM25 名次 4，`bm25_score` 13.930563430533088，向量名次 4，`vec_score` 0.5908521413803101。`matched` 是空的。

`megatron-two-all-reduces` 命中。第 1 名是 ZeRO 的块。证据块在第 2 名。第 3 名是第 4 页上的 `0049`，`matched` 是空的。

- 第 1 名 `rajbhandari-zero/8-communication-analysis-of-zero-r/0130`，第 14 页，`rerank_score` 6.160409927368164，`rrf_rank` 1，`rrf_score` 0.032018442622950824，BM25 名次 4，`bm25_score` 24.161714979418473，向量名次 1，`vec_score` 0.7245021462440491。`matched` 是空的。
- 第 2 名 `shoeybi-megatron-lm/3-model-parallel-transformers/0054`，第 4 页，`rerank_score` 4.872010707855225，`rrf_rank` 2，`rrf_score` 0.03200204813108039，BM25 名次 3，`bm25_score` 25.298249139268247，向量名次 2，`vec_score` 0.5854880809783936。`matched` 是 `0054`。
- 第 3 名 `shoeybi-megatron-lm/3-model-parallel-transformers/0049`，第 4 页，`rerank_score` 1.0541191101074219，`rrf_rank` 6，`rrf_score` 0.02967032967032967，BM25 名次 10，`bm25_score` 17.555153563859264，向量名次 5，`vec_score` 0.5433846116065979。`matched` 是空的。
- 第 4 名 `shoeybi-megatron-lm/3-model-parallel-transformers/0057`，第 5 页，`rerank_score` 0.4270971715450287，`rrf_rank` 3，`rrf_score` 0.03128054740957967，BM25 名次 2，`bm25_score` 28.545947353017382，向量名次 6，`vec_score` 0.5431389212608337。`matched` 是空的。
- 第 5 名 `shoeybi-megatron-lm/3-model-parallel-transformers/0060`，第 5 页，`rerank_score` -0.606272280216217，`rrf_rank` 23，`rrf_score` 0.015151515151515152，只有 BM25 名次 6，`bm25_score` 18.983672797222965，`vec_score` 和 `vec_rank` 是 null。`matched` 是空的。

`zero-name` 命中。第 1 名就是摘要证据块。第 2 页的 `rajbhandari-zero/1-extended-introduction/0012` 不在前 5 条里。

- 第 1 名 `rajbhandari-zero/abstract/0004`，第 1 页，`rerank_score` 2.447185516357422，`rrf_rank` 49，`rrf_score` 0.011363636363636364，只有向量名次 28，`vec_score` 0.48817652463912964，`bm25_score` 和 `bm25_rank` 是 null。`matched` 是 `0004`。
- 第 2 名 `rajbhandari-zero/references/0214`，第 24 页，`rerank_score` 0.415918231010437，`rrf_rank` 72，`rrf_score` 0.009174311926605505，只有向量名次 49，`vec_score` 0.4713592529296875。`matched` 是空的。
- 第 3 名 `rajbhandari-zero/1-extended-introduction/0025`，第 3 页，`rerank_score` 0.20000682771205902，`rrf_rank` 2，`rrf_score` 0.0304147465437788，BM25 名次 10，`bm25_score` 6.038967629992551，向量名次 2，`vec_score` 0.5624403953552246。`matched` 是空的。
- 第 4 名 `rajbhandari-zero/references/0209`，第 23 页，`rerank_score` 0.19332171976566315，`rrf_rank` 58，`rrf_score` 0.01020408163265306，只有向量名次 38，`vec_score` 0.48141640424728394。`matched` 是空的。
- 第 5 名 `rajbhandari-zero/references/0213`，第 24 页，`rerank_score` -0.14985992014408112，`rrf_rank` 21，`rrf_score` 0.022149202872094438，BM25 名次 39，`bm25_score` 4.113512367953967，向量名次 23，`vec_score` 0.4912872016429901。`matched` 是空的。

`zero-400-gpus` 命中。两处证据块分别是第 1 名和第 2 名。

- 第 1 名 `rajbhandari-zero/abstract/0006`，第 1 页，`rerank_score` 5.592934608459473，`rrf_rank` 3，`rrf_score` 0.03055037313432836，BM25 名次 7，`bm25_score` 11.698900306607623，向量名次 4，`vec_score` 0.7077695727348328。`matched` 是 `0006`。
- 第 2 名 `rajbhandari-zero/1-extended-introduction/0035`，第 5 页，`rerank_score` 2.985670566558838，`rrf_rank` 1，`rrf_score` 0.03252247488101534，BM25 名次 1，`bm25_score` 16.99802788352117，向量名次 2，`vec_score` 0.7308525443077087。`matched` 是 `0035`。
- 第 3 名 `rajbhandari-zero/references/0209`，第 23 页，`rerank_score` 2.126471996307373，`rrf_rank` 15，`rrf_score` 0.025657894736842105，BM25 名次 20，`bm25_score` 9.292850316932817，向量名次 16，`vec_score` 0.6373242139816284。`matched` 是空的。
- 第 4 名 `rajbhandari-zero/1-extended-introduction/0032`，第 4 页，`rerank_score` 1.6954452991485596，`rrf_rank` 2，`rrf_score` 0.032266458495966696，BM25 名次 3，`bm25_score` 13.005376457582155，向量名次 1，`vec_score` 0.7678390741348267。`matched` 是空的。
- 第 5 名 `rajbhandari-zero/10-2-speed-and-model-size/0157`，第 17 页，`rerank_score` 1.635981559753418，`rrf_rank` 14，`rrf_score` 0.02574682290807064，BM25 名次 13，`bm25_score` 10.38035359239905，向量名次 23，`vec_score` 0.6269489526748657。`matched` 是空的。

`pagedattention-internal-fragmentation` 命中。第 1 名就是证据块 `0016`。第 4 页的证据块 `kwon-pagedattention/3-1-memory-management-in-existing-systems/0057` 不在前 5 条里。第 5 名是同页的 `0047`，`matched` 是空的。

- 第 1 名 `kwon-pagedattention/1-introduction/0016`，第 2 页，`rerank_score` 5.022530555725098，`rrf_rank` 2，`rrf_score` 0.03225806451612903，BM25 名次 2，`bm25_score` 27.2317801124377，向量名次 2，`vec_score` 0.6829792261123657。`matched` 是 `0016`。
- 第 2 名 `kwon-pagedattention/abstract/0005`，第 1 页，`rerank_score` 4.289462089538574，`rrf_rank` 3，`rrf_score` 0.031009615384615385，BM25 名次 5，`bm25_score` 22.295490627465135，向量名次 4，`vec_score` 0.6608744859695435。`matched` 是空的。
- 第 3 名 `kwon-pagedattention/1-introduction/0019`，第 2 页，`rerank_score` 2.4176559448242188，`rrf_rank` 1，`rrf_score` 0.032266458495966696，BM25 名次 3，`bm25_score` 25.326840651947165，向量名次 1，`vec_score` 0.734154224395752。`matched` 是空的。
- 第 4 名 `kwon-pagedattention/1-introduction/0015`，第 2 页，`rerank_score` 1.312642216682434，`rrf_rank` 5，`rrf_score` 0.029910714285714284，BM25 名次 4，`bm25_score` 23.442538317072955，向量名次 10，`vec_score` 0.6363997459411621。`matched` 是空的。
- 第 5 名 `kwon-pagedattention/2-3-batching-techniques-for-llms/0047`，第 4 页，`rerank_score` 1.1725282669067383，`rrf_rank` 4，`rrf_score` 0.030886196246139225，BM25 名次 1，`bm25_score` 34.17692157784275，向量名次 9，`vec_score` 0.6385241150856018。`matched` 是空的。

`gpipe-micro-batches` 命中。第 1 名就是证据块。第 5 名是第 3 页上的 `0027`，`matched` 是空的。

- 第 1 名 `huang-gpipe/2-2-algorithm/0024`，第 3 页，`rerank_score` 6.616547584533691，`rrf_rank` 1，`rrf_score` 0.03278688524590164，BM25 名次 1，`bm25_score` 26.04888506348862，向量名次 1，`vec_score` 0.7055422067642212。`matched` 是 `0024`。
- 第 2 名 `huang-gpipe/1-introduction/0012`，第 2 页，`rerank_score` 1.6475176811218262，`rrf_rank` 5，`rrf_score` 0.0304147465437788，BM25 名次 10，`bm25_score` 12.394695915047123，向量名次 2，`vec_score` 0.6262322664260864。`matched` 是空的。
- 第 3 名 `huang-gpipe/6-design-features-and-trade-offs/0069`，第 8 页，`rerank_score` 1.4325268268585205，`rrf_rank` 4，`rrf_score` 0.03125763125763126，BM25 名次 5，`bm25_score` 13.519665096517866，向量名次 3，`vec_score` 0.6214003562927246。`matched` 是空的。
- 第 4 名 `huang-gpipe/6-design-features-and-trade-offs/0070`，第 8 页，`rerank_score` 0.9602723717689514，`rrf_rank` 3，`rrf_score` 0.03149801587301587，BM25 名次 3，`bm25_score` 15.886037585959286，向量名次 4，`vec_score` 0.6168228983879089。`matched` 是空的。
- 第 5 名 `huang-gpipe/2-3-performance-optimization/0027`，第 3 页，`rerank_score` 0.12509013712406158，`rrf_rank` 6，`rrf_score` 0.028006267136701922，BM25 名次 9，`bm25_score` 12.442168898451612，向量名次 14，`vec_score` 0.5575018525123596。`matched` 是空的。

`medusa-head` 未中。证据块 `cai-medusa/2-1-1-medusa-heads/0029` 不在前 5 条里。第 2 名是同页的 `0032`，`chunk_id` 不同。

- 第 1 名 `cai-medusa/c-visualization-of-optimized-tree-attention/0208`，第 14 页，`rerank_score` 2.008098602294922，`rrf_rank` 1，`rrf_score` 0.032266458495966696，BM25 名次 1，`bm25_score` 14.082938370578905，向量名次 3，`vec_score` 0.5523862838745117。`matched` 是空的。
- 第 2 名 `cai-medusa/2-1-1-medusa-heads/0032`，第 3 页，`rerank_score` 0.5483041405677795，`rrf_rank` 4，`rrf_score` 0.03021353930031804，BM25 名次 11，`bm25_score` 9.881836984653773，向量名次 2，`vec_score` 0.5586618185043335。`matched` 是空的。
- 第 3 名 `cai-medusa/a-1-llm-inference-acceleration/0193`，第 13 页，`rerank_score` 0.2726794481277466，`rrf_rank` 18，`rrf_score` 0.02021535960991467，BM25 名次 47，`bm25_score` 7.248893465194364，向量名次 32，`vec_score` 0.48826414346694946。`matched` 是空的。
- 第 4 名 `cai-medusa/1-introduction/0020`，第 2 页，`rerank_score` 0.24920913577079773，`rrf_rank` 9，`rrf_score` 0.02715098147128967，BM25 名次 19，`bm25_score` 8.988787690948326，向量名次 9，`vec_score` 0.5198894739151001。`matched` 是空的。
- 第 5 名 `cai-medusa/d-results-of-speculative-decoding/0211`，第 15 页，`rerank_score` -0.20521602034568787，`rrf_rank` 2，`rrf_score` 0.030309988518943745，BM25 名次 5，`bm25_score` 11.95519620012154，向量名次 7，`vec_score` 0.5264496803283691。`matched` 是空的。

`medusa-frozen-backbone` 命中。证据块在第 2 名。第 5 名跨第 1–2 页，`chunk_id` 是 `0012`，`matched` 是空的。

- 第 1 名 `cai-medusa/1-introduction/0016`，第 2 页，`rerank_score` 3.5953903198242188，`rrf_rank` 2，`rrf_score` 0.032266458495966696，BM25 名次 3，`bm25_score` 21.741200757015893，向量名次 1，`vec_score` 0.7108737230300903。`matched` 是空的。
- 第 2 名 `cai-medusa/abstract/0005`，第 1 页，`rerank_score` 3.4886679649353027，`rrf_rank` 1，`rrf_score` 0.03252247488101534，BM25 名次 1，`bm25_score` 27.639701129039725，向量名次 2，`vec_score` 0.7049260139465332。`matched` 是 `0005`。
- 第 3 名 `cai-medusa/2-1-1-medusa-heads/0032`，第 3 页，`rerank_score` 1.7791283130645752，`rrf_rank` 4，`rrf_score` 0.030330882352941176，BM25 名次 8，`bm25_score` 18.358952423821016，向量名次 4，`vec_score` 0.6402959823608398。`matched` 是空的。
- 第 4 名 `cai-medusa/2-2-2-medusa-2-joint-training/0052`，第 5 页，`rerank_score` 1.2513422966003418，`rrf_rank` 6，`rrf_score` 0.030158730158730156，BM25 名次 10，`bm25_score` 17.860552502918576，向量名次 3，`vec_score` 0.663718581199646。`matched` 是空的。
- 第 5 名 `cai-medusa/1-introduction/0012`，第 1–2 页，`rerank_score` 1.1223548650741577，`rrf_rank` 3，`rrf_score` 0.030621785881252923，BM25 名次 2，`bm25_score` 24.812717670788523，向量名次 9，`vec_score` 0.6172481775283813。`matched` 是空的。

`smoothquant-scaling` 命中。第 1 名就是证据块。第 3 名是第 2 页上的 `0013`，`matched` 是空的。

- 第 1 名 `xiao-smoothquant/1-introduction/0014`，第 2 页，`rerank_score` 6.2205705642700195，`rrf_rank` 1，`rrf_score` 0.03278688524590164，BM25 名次 1，`bm25_score` 29.50145267486939，向量名次 1，`vec_score` 0.7328938245773315。`matched` 是 `0014`。
- 第 2 名 `xiao-smoothquant/abstract/0004`，第 1 页，`rerank_score` 5.075338363647461，`rrf_rank` 2，`rrf_score` 0.03225806451612903，BM25 名次 2，`bm25_score` 27.625907734428573，向量名次 2，`vec_score` 0.7314173579216003。`matched` 是空的。
- 第 3 名 `xiao-smoothquant/1-introduction/0013`，第 2 页，`rerank_score` 3.346884250640869，`rrf_rank` 3，`rrf_score` 0.031024531024531024，BM25 名次 3，`bm25_score` 25.851115092384628，向量名次 6，`vec_score` 0.6693935394287109。`matched` 是空的。
- 第 4 名 `xiao-smoothquant/abstract/0005`，第 1 页，`rerank_score` 3.210812568664551，`rrf_rank` 6，`rrf_score` 0.02854251012145749，BM25 名次 16，`bm25_score` 14.075159724705488，向量名次 5，`vec_score` 0.6754697561264038。`matched` 是空的。
- 第 5 名 `xiao-smoothquant/4-smoothquant/0049`，第 5 页，`rerank_score` 3.175691843032837，`rrf_rank` 8，`rrf_score` 0.02736726874657909，BM25 名次 27，`bm25_score` 11.97251101006105，向量名次 3，`vec_score` 0.7139297723770142。`matched` 是空的。

## 概括句

```powershell
$env:PYTHONPATH = "src"
python -m paper_trail.evaluation answers
```

未拒答的题各请求一次 `deepseek-flash`。拒答仍看这 5 条里最高的 `vec_score` 是否低于 0.25。密钥是 `DEEPSEEK_API_KEY`。数字检查和 `python -m paper_trail.generation` 是同一套。`numbers_ok` 只表示标出的段落里有这个数字原样，不表示概括句已经核对通过。

2026-11-23 跑了这 10 题。`question_version` 是 1。10 题的 `refused` 都是 false，`model` 都是 `deepseek-flash`，`threshold` 都是 0.25。`vec_score_max` 从 `answers.json` 抄来：

| id | retrieval_hit | vec_score_max | numbers_ok |
| --- | --- | --- | --- |
| `megatron-15-1-petaflops` | true | 0.6854450702667236 | true |
| `megatron-first-gemm` | true | 0.628649115562439 | true |
| `megatron-two-all-reduces` | true | 0.7245021462440491 | true |
| `zero-name` | true | 0.5624403953552246 | true |
| `zero-400-gpus` | true | 0.7678390741348267 | false |
| `pagedattention-internal-fragmentation` | true | 0.734154224395752 | true |
| `gpipe-micro-batches` | true | 0.7055422067642212 | true |
| `medusa-head` | false | 0.5586618185043335 | true |
| `medusa-frozen-backbone` | true | 0.7108737230300903 | true |
| `smoothquant-scaling` | true | 0.7328938245773315 | true |

`megatron-15-1-petaflops` 的 `answer` 是 `15.1 PetaFLOPs [1][2][4]`。`number_checks` 是 `15.1` 绑定名次 1、2、4，`found` 是 true。

`megatron-first-gemm` 的 `answer` 是 `Megatron-LM partitions the first GEMM in the MLP block in a column parallel fashion [1].`。没有数字，`number_checks` 是 `[]`。

`megatron-two-all-reduces` 的 `answer` 是 `One Megatron-LM transformer layer uses 4 total communication operations in the forward and backward pass [4]. It performs two all-reduces in the forward path and two in the backward path [2].`。数字 `4` 绑定名次 4 和 2，`found` 是 true。第 4 名 `0057` 里有 “4 total communication operations”。第 2 名 `0054` 里对上的是 “Figure 4”，不是 all-reduce 的次数。

`zero-name` 的 `answer` 是 `Zero Redundancy Optimizer [1].`。没有数字。

`zero-400-gpus` 的 `answer` 是 `ZeRO reports "super-linear speedup on 400 GPUs" [1]. It also observes "super linear speedup in the regime of 64-400 GPUs" [2].`。`400` 绑定名次 1，`found` 是 true。后面的 `64` 没有名次，`found` 是 false。再后面的 `400` 绑定名次 2，`found` 是 true。`64-400` 被拆成两个数字，夹在中间的 `64` 赶在下一个数字之前，没有 `[n]`。

`pagedattention-internal-fragmentation` 的 `answer` 是 `Existing systems pre-allocate a contiguous chunk of memory with the request’s maximum length (e.g., 2048 tokens) to store the KV cache of a request in contiguous space, which can result in severe internal fragmentation since the request’s actual length can be much shorter than its maximum length [1].`。数字 `2048` 绑定名次 1，`found` 是 true。

`gpipe-micro-batches` 的 `answer` 是 `GPipe first divides every mini-batch of size N into M equal micro-batches, which are pipelined through the K accelerators [1].`。没有数字。

`medusa-head` 的 `retrieval_hit` 是 false，证据块不在前 5 条里。`vec_score_max` 仍高于 0.25，所以请求了模型。`answer` 是 `No passage is close enough to answer.`。`refused` 仍是 false。没有数字。

`medusa-frozen-backbone` 的 `answer` 是 `The backbone LLM remains frozen during MEDUSA-1 training [2], and MEDUSA is directly fine-tuned on top of a frozen backbone LLM [2]. MEDUSA-1 requires minimal memory and can be further optimized with quantization techniques akin to those in QLoRA, without compromising the generation quality due to the fixed backbone model [1].`。两处数字都是 `1`。第一处绑定名次 2，第二处绑定名次 1，`found` 都是 true。对上的是段落里的 `MEDUSA-1`。

`smoothquant-scaling` 的 `answer` 是 `SmoothQuant uses a mathematically equivalent per-channel scaling transformation that significantly smooths the magnitude across the channels [1]. It smooths the activation outliers by offline migrating the quantization difficulty from activations to weights with a mathematically equivalent transformation [2].`。没有数字。

## RAGAS

```powershell
$env:PYTHONPATH = "src"
python -m paper_trail.evaluation ragas
```

读 `data/eval/answers.json` 和 `data/eval/questions.json`，不改这两份文件，也不改 `retrieval.json` 和 `last_answer.json`。用 ragas 0.4.4 的 Faithfulness、Answer Relevancy、Context Precision 和 Context Recall。评判模型是 `deepseek-v4-pro`，温度 0，`top_p` 0.1，`max_tokens` 1024，思考关闭。Answer Relevancy 反推 3 个问题，向量用本地 bge-m3。引用按名次送出整段原文。Context Precision 和 Context Recall 的参考答案是该题 `evidence` 里不重复的字符串，按出处顺序用换行接起来。10 题里只有 `zero-400-gpus` 是两句。密钥是 `DEEPSEEK_API_KEY`。再跑一次会再请求评判模型。

DeepSeek 在 2026-09-10 写过，多方测试里 V4.1-Flash 的效果超过 V4-Pro。评判模型并没有比写概括句的 `deepseek-flash` 更强。

库在抽不出陈述时给出的分数是 NaN，文件里写成 null，不填 0 或 1，平均分只算有数字的题。2026-11-25 这 10 题四项都有数字。`faithfulness_mean` 是 0.8，`answer_relevancy_mean` 是 0.7031301228706631，`context_precision_mean` 是 0.9033333332917917，`context_recall_mean` 是 0.9。四项的 count 都是 10。原始结果在 `data/eval/ragas.json`。

| id | faithfulness | answer_relevancy | context_precision | context_recall |
| --- | --- | --- | --- | --- |
| `megatron-15-1-petaflops` | 1.0 | 0.5294315344044075 | 0.9166666666361111 | 1.0 |
| `megatron-first-gemm` | 0.0 | 0.9999999999997584 | 0.9999999999 | 1.0 |
| `megatron-two-all-reduces` | 1.0 | 0.8773423043122635 | 0.9166666666361111 | 1.0 |
| `zero-name` | 1.0 | 0.5436297579009476 | 0.8333333332916666 | 1.0 |
| `zero-400-gpus` | 1.0 | 0.9548145800436486 | 0.99999999995 | 1.0 |
| `pagedattention-internal-fragmentation` | 1.0 | 0.6763315309170621 | 0.94999999997625 | 1.0 |
| `gpipe-micro-batches` | 1.0 | 0.8626017580771981 | 0.9166666666361111 | 1.0 |
| `medusa-head` | 0.0 | 0.0 | 0.49999999995 | 0.0 |
| `medusa-frozen-backbone` | 1.0 | 0.8565088712111066 | 0.999999999975 | 1.0 |
| `smoothquant-scaling` | 1.0 | 0.7306408918402395 | 0.9999999999666667 | 1.0 |

`megatron-first-gemm` 的 Faithfulness 是 0.0。`medusa-head` 的回答是 `No passage is close enough to answer.`，Faithfulness 和 Answer Relevancy 都是 0.0，Context Recall 也是 0.0，Context Precision 是 0.49999999995。其余 8 题的 Faithfulness 是 1.0，其余 9 题的 Context Recall 是 1.0。
