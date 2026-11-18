# 引用

读 `data/indexes/rerank/last_query.json`，整理成一份引用记录，不改那份重排结果。`refused` 为 true 时不请求模型，`answer` 是 `No passage is close enough to answer.`，`model` 是 null。`refused` 为 false 时请求一次 `deepseek-flash`，把模型原文写入 `answer`，`model` 是 `deepseek-flash`。两种情况都留下引用。`refused` 不因模型写出那句固定话而改成 true。写文件前检查 `answer` 里的整数和小数是否按原样出现在它标注的段落中。`[1]` 这种名次不算数字。没有数字时 `number_checks` 是空列表，`numbers_ok` 是 true。有数字却没有 `[n]`，或数字对不上那段原文，`numbers_ok` 是 false。`8.3` 不能用 `8.30` 或 `18.3` 顶替，`15` 也不能算进 `15.1`。一个数字只绑定写在它后面、下一个数字之前的 `[n]`。`8.3 billion parameters [1]` 去第 1 条原文里找 `8.3`。`[1] says 8.3 and [2] says 17.` 里，前面的 `[1]` 不绑定 `8.3`，夹在两个数字之间的 `[2]` 被算给 `8.3`，`17` 没有名次。这种配错只写在 `number_checks` 里。`answer` 和 `refused` 不因这次检查而改，概括句照常留下。`numbers_ok` 先不当成数字已经核对通过。段落原文里的 `[1]` 不是名次。要核对的数字若是整数 `1`，第 5 条 ZeRO 原文 `Bert-large (0.3B) [1]` 里的这个 `1` 会对上，因为 `[` 和 `]` 不是数字或小数点；`8.3` 不会被这个 `[1]` 对上。

在仓库根目录先激活 `paper-trail` 环境，再执行。重排结果要先存在。

```powershell
python -m paper_trail.generation
```

结果在 `data/answers/last_answer.json`。`data/answers/` 不提交。密钥读环境变量 `DEEPSEEK_API_KEY`。请求的 `temperature` 是 0，`thinking` 是 `{"type": "disabled"}`。没设置密钥或返回内容为空时，命令退出，不写文件。

请求体是下面这种形状。`messages` 有两条：`system` 是固定提示，`user` 先放各段再放问题。每段只含名次、`paper_id`、起止页和整段 `text`。不送 `vec_score`、`rerank_score`、`chunk_id`、`sha256` 和 `section_path`。下面的 `user` 只写出 2026-11-17 那次第一块的第一句，以及问题。真实请求里第一块还有后面的 363 个字符中的其余部分，并且还有第 2 到第 5 块；第 3 块是整段 5444 个字符。

```json
{
  "model": "deepseek-flash",
  "temperature": 0,
  "stream": false,
  "thinking": {"type": "disabled"},
  "messages": [
    {
      "role": "system",
      "content": "Answer in English using only the passages. Copy numbers and technical terms as written. When you use a passage, mark it with its rank, like [1]. If the passages do not contain the answer, reply with exactly: No passage is close enough to answer."
    },
    {
      "role": "user",
      "content": "Passages:\n\n[1] shoeybi-megatron-lm p7-7\nWe have included samples generated from the 8.3 billion parameters model in the Appendix C.\n\nQuestion:\nHow many parameters does GPT-4 have?"
    }
  ]
}
```

每条引用保留 `rank`、`chunk_id`、`paper_id`、`sha256`、`section_path`、`start_page`、`end_page`、`text`、`vec_score`、`rerank_score`。`text` 是整段。没有向量分时 `vec_score` 仍是 null。`bm25_score`、`rrf_score`、`sequence`、`block_type`、`bm25_rank`、`vec_rank` 和 `rrf_rank` 不抄进引用。外层不抄重排结果里的 `top_k`、`candidate_k`、`candidate_count`、`rrf_k`、`model` 和 `max_length`。回答记录自己的 `model` 是概括句的模型名，没请求时是 null。`citations` 的顺序是重排的 `rank`。

回答记录是一个对象，字段顺序是 `query`、`refused`、`threshold`、`vec_score_max`、`model`、`answer`、`number_checks`、`numbers_ok`、`citations`。前四项从重排结果抄来。`model` 和 `answer` 属于概括句：没请求时分别是 null 和固定句，请求过后是 `deepseek-flash` 和模型原文。`number_checks` 的每一项有 `number`、`ranks`、`found`。`citations` 里每一项是上面那 10 个字段。

2026-11-17 用当时的重排结果跑了一次。查询是 `How many parameters does GPT-4 have?`，`refused` 是 false，`threshold` 是 0.25，`vec_score_max` 是 0.6355667114257812，`model` 是 `deepseek-flash`，`answer` 是 `No passage is close enough to answer.`。文件里有 5 条引用。下面只展开第 1 条，`text` 是文件里的整段。

```json
{
  "query": "How many parameters does GPT-4 have?",
  "refused": false,
  "threshold": 0.25,
  "vec_score_max": 0.6355667114257812,
  "model": "deepseek-flash",
  "answer": "No passage is close enough to answer.",
  "number_checks": [],
  "numbers_ok": true,
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

`vec_score_max` 来自第 2 名，是 0.6355667114257812，高于第 1 名的 0.5298908948898315，名次仍是 2。第 3 条的 `text` 有 5444 个字符，文件里是整段。这些段落讲的是 GPT-2 和训练规模，没有 GPT-4 的参数量。模型因此写出固定句，`refused` 仍是 false。这句里没有整数或小数，所以 `number_checks` 是 `[]`，`numbers_ok` 是 true。这次没有再请求模型。
