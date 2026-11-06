# 分块

读 `data/parsed/mineru/<paper_id>.json`，按 MinerU 的块顺序写成 chunk。页眉、页脚、页码和脚注不进入正文。

## 运行

在仓库根目录先激活 `paper-trail` 环境，再执行。第二条命令执行前要保证解析结果存在。

```powershell
python -m paper_trail.parsing
python -m paper_trail.chunking
```

`python -m paper_trail.chunking` 读 `data/parsed/mineru/index.json`，为每篇写出 `data/chunks/<paper_id>.json`，另有一份 `index.json`。`data/chunks/` 不提交。

## 一个 chunk

`chunk_id` 由 `paper_id`、当前小节和从 0 开始的序号组成。文档标题不写入 ID。同一份 middle JSON 重复构建，ID 不变。

小节标题里，不是字母或数字的字符改成连字符，再转成小写。`5.1.1. MODEL AND DATA PARALLELISM` 变成 `5-1-1-model-and-data-parallelism`。序号是这篇里留下的 chunk 的次序，从 0 起，写成 4 位。页眉、页脚、页码和脚注不占号。`continues_prev` 接到已有正文上，也不新占号。它不是 MinerU 每一页里的 `index`。还没有小节标题时，ID 是 `paper_id/0000` 这种形式。

Megatron-LM 里接上 “typically done” 的那一块，ID 是：

```text
shoeybi-megatron-lm/5-1-1-model-and-data-parallelism/0077
```

`section_path` 先放文档标题，也就是 MinerU 的 `doc_title`。之后每遇到一个 `paragraph_title`，用它替换上一个小节标题，不把 `2.1` 放进 `2` 的下面。标准档里这些标题的 `level` 都是 2。

一份 chunk 文件的外层是 `chunk_version`（当前是 2）、`paper_id`、`sha256` 和 `chunks`。上面那一块在文件里是：

```json
{
  "chunk_id": "shoeybi-megatron-lm/5-1-1-model-and-data-parallelism/0077",
  "paper_id": "shoeybi-megatron-lm",
  "sha256": "fa89e54e23c0cea5cbd9d24720db7647c61af299afdb9a170c7119160e6d207a",
  "section_path": [
    "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism",
    "5.1.1. MODEL AND DATA PARALLELISM"
  ],
  "sequence": 77,
  "start_page": 6,
  "end_page": 6,
  "block_type": "text",
  "text": "Weak scaling is typically done by scaling the batch-size"
}
```

文件里的 `text` 比这里长，这一块是 765 个字符。它从 `Throughout this section...` 开始，中间含有上面这一句。这里只写出被 Table 1 和 Figure 5 切开后又接上的那一句。同一节里，Table 1 是序号 78，Figure 5 是序号 79。

`continues_prev` 为 true 的正文先接在前面最后一段正文末尾，再按下面的字数规则切开。行末的连字符保留：第 5 页的 `itera-` 和第 6 页的 `tions` 接成 `itera-tions`。这块是 `shoeybi-megatron-lm/4-2-training-optimization-and-hyperparameters/0069`，`start_page` 是 5，`end_page` 是 6。

## 超过 800 字符再切

单位是字符，也就是 Python 的 `len`。上限 `MAX_CHARS` 是 800。相邻块不重叠。短块留下。

正文和 `ref_text` 长于 800 时，先在句号处切开，再把句子装进不超过 800 字符的块。句号留在前一句。英文在 `.`、`!` 或 `?` 后面是空白、再是大写字母时切开。`Fig. 5` 和 `1.5` 的点号后面不是大写字母，不切。中文在 `。` 处切开。一整句自己超过 800 时，按 800 个字符硬切，两段不重叠。

Megatron-LM 摘要原来是一块。切开后序号 4 以 `...native PyTorch.` 结束，共 697 个字符；序号 5 从 `We illustrate this approach...` 开始，共 680 个字符。ID 是 `shoeybi-megatron-lm/abstract/0004` 和 `shoeybi-megatron-lm/abstract/0005`。

标题、图、公式、代码不按句号拆。表有多于一个 `<tr>` 时整块留下，即使超过 800。第 13 页和第 14 页的文字样本各有两行，仍各是一块，长度是 5444 和 4149，ID 是 `shoeybi-megatron-lm/c-text-samples/0177` 和 `.../0178`。只有一行、去掉标签后仍超过 800 的表，去掉 HTML 后按正文切，`block_type` 仍是 `table`。不到 800 的短表保留 HTML。

所有 chunk 文本在计长度之前去掉 `<img src="data:image/...">`。图注留在后面的文字里。`data/parsed/` 里的 middle JSON 不改，不另存 JPEG，回答旁边也不显示图。

Megatron-LM 第 12 页原来的一整格里有 Figure 8 的 JPEG、图注和一段生成样本。对照过这一页的 PDF：文字样本本身没有图。现在第一段是序号 170，`shoeybi-megatron-lm/b-2-model-parallel-random-number-generation/0170`，649 个字符，含有 `Figure 8. Grouping of GPUs for hybrid model and data parallelism with 8-way model parallel and 64-way data parallel.`，没有 `data:image`。下一段序号 171 从 `Letitia James...` 开始。标题 `C. Text Samples` 是序号 175。

图和表仍是自己的 chunk，出现在它们原来的位置。被 Table 1 和 Figure 5 分开的句子仍在同一块里：`Weak scaling is typically done by scaling the batch-size`。表块里先是表注，再是 HTML。图块里留下图注。短块留下，例如单独的 `K`。

## 还没做

- 表格文字仍在表块里，没有从别的 chunk 再删一份。多于一行的文字样本也不再按句切开。
- 图注留在图块里，没有另做绑定。
- 公式仍是块里的 LaTeX，没有改成普通文字。
- 不另存 JPEG，回答旁边也不显示图。
- 索引、检索和问答还没有。
