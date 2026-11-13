# 引用

读 `data/indexes/rerank/last_query.json`，整理成一份引用记录。不调用模型，也不改那份重排结果。`refused` 为 false 时 `answer` 是 null。`refused` 为 true 时 `answer` 是「没有足够相近的段落，无法回答。」两种情况都留下引用。

在仓库根目录先激活 `paper-trail` 环境，再执行。重排结果要先存在。

```powershell
python -m paper_trail.generation
```

结果在 `data/answers/last_answer.json`。`data/answers/` 不提交。

每条引用保留 `rank`、`chunk_id`、`paper_id`、`sha256`、`section_path`、`start_page`、`end_page`、`text`、`vec_score`、`rerank_score`。`text` 是整段。没有向量分时 `vec_score` 仍是 null。`bm25_score`、`rrf_score`、`sequence`、`block_type`、`bm25_rank`、`vec_rank` 和 `rrf_rank` 不抄进引用。外层不抄 `top_k`、`candidate_k`、`candidate_count`、`rrf_k`、`model` 和 `max_length`。`citations` 的顺序是重排的 `rank`。

2026-11-07 用当时的重排结果跑了一次。查询是 `How many parameters does GPT-4 have?`，`refused` 是 false，`threshold` 是 0.25，`vec_score_max` 是 0.6355667114257812，`answer` 是 null。文件里有 5 条引用。下面只展开第 1 条，`text` 是文件里的整段。

```json
{
  "query": "How many parameters does GPT-4 have?",
  "refused": false,
  "threshold": 0.25,
  "vec_score_max": 0.6355667114257812,
  "answer": null,
  "citations": [
    {
      "rank": 1,
      "chunk_id": "shoeybi-megatron-lm/5-2-language-modeling-results-using-gpt-2/0087",
      "paper_id": "shoeybi-megatron-lm",
      "sha256": "fa89e54e23c0cea5cbd9d24720db7647c61af299afdb9a170c7119160e6d207a",
      "section_path": [
        "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism",
        "5.2. Language Modeling Results Using GPT-2"
      ],
      "start_page": 7,
      "end_page": 7,
      "text": "We have included samples generated from the 8.3 billion parameters model in the Appendix C. Recently researchers from Microsoft in collaboration with NVIDIA trained a 17 billion parameter GPT-2 model called Turing-NLG (Microsoft, 2020) using Megatron and showed that the accuracies further improve as they scale the model, highlighting the value of larger models.",
      "vec_score": 0.5298908948898315,
      "rerank_score": 0.346469521522522
    }
  ]
}
```

| 名次 | 页 | vec_score | rerank_score | chunk_id |
| --- | --- | --- | --- | --- |
| 1 | 7 | 0.5298908948898315 | 0.346469521522522 | `shoeybi-megatron-lm/5-2-language-modeling-results-using-gpt-2/0087` |
| 2 | 6 | 0.6355667114257812 | 0.21141931414604187 | `shoeybi-megatron-lm/5-1-scaling-analysis/0074` |
| 3 | 13 | 0.4994128346443176 | -0.11769899725914001 | `shoeybi-megatron-lm/c-text-samples/0177` |
| 4 | 2 | null | -0.512144923210144 | `shoeybi-megatron-lm/1-introduction/0020` |
| 5 | 1 | 0.4986346364021301 | -0.5454120635986328 | `rajbhandari-zero/1-extended-introduction/0008` |

`vec_score_max` 来自第 2 名，是 0.6355667114257812，高于第 1 名的 0.5298908948898315，名次仍是 2。第 3 条的 `text` 有 5444 个字符，文件里是整段。这次 `refused` 是 false，所以没有拒答句。这些段落讲的是 GPT-2 和训练规模，没有 GPT-4 的参数量。

## 还没做

- 还没有概括句，也没有调用模型。
- 还没有检查答案里的数字是否出自被引用的那一页。
- 还没有按论文过滤。
