# 评测题

10 道题在 `data/eval/questions.json`。这是手写的金标准。外层只有 `question_version` 和 `questions`。`question_version` 现在是 1，表示这一版题的字段形状。

每题有 `id`、`query` 和 `passages`。`id` 是这道题的固定名字。`query` 是英文问句，不要求含有整段证据。`passages` 里每一处是一处可接受的段落，字段是 `chunk_id`、`paper_id`、`start_page`、`end_page` 和 `evidence`。`chunk_id` 以 `paper_id/` 开头。`evidence` 是那一块 `text` 里的原样子串。同一题的几处都算对。

这些字符串从 `data/chunks/` 的块文本里核对后原样抄入。2026-11-19 核对过 15 处。`tests/test_questions.py` 只检查形状：版本是 1、10 个不重复的 `id`、问句和证据非空、`chunk_id` 前缀、结束页不早于起始页。测试不打开块文件，也不跑检索。

目前没有检索或概括命令读取这份文件，也不会把它写入 `data/indexes/rerank/last_query.json` 或 `data/answers/last_answer.json`。后面跑重排时，这份文件才是输入。还没有用这批题跑重排，也没有调用概括模型。

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

## 还没做

- 还没有用这批题跑重排，也没有统计前 5 条里有没有命中这些段落。
- 还没有调用概括模型，也没有把 RAGAS 接进来。
