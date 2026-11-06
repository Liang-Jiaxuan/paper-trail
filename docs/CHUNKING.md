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
shoeybi-megatron-lm/5-1-1-model-and-data-parallelism/0063
```

`section_path` 先放文档标题，也就是 MinerU 的 `doc_title`。之后每遇到一个 `paragraph_title`，用它替换上一个小节标题，不把 `2.1` 放进 `2` 的下面。标准档里这些标题的 `level` 都是 2。

一份 chunk 文件的外层是 `chunk_version`、`paper_id`、`sha256` 和 `chunks`。上面那一块在文件里是：

```json
{
  "chunk_id": "shoeybi-megatron-lm/5-1-1-model-and-data-parallelism/0063",
  "paper_id": "shoeybi-megatron-lm",
  "sha256": "fa89e54e23c0cea5cbd9d24720db7647c61af299afdb9a170c7119160e6d207a",
  "section_path": [
    "Megatron-LM: Training Multi-Billion Parameter Language Models Using Model Parallelism",
    "5.1.1. MODEL AND DATA PARALLELISM"
  ],
  "sequence": 63,
  "start_page": 6,
  "end_page": 6,
  "block_type": "text",
  "text": "Weak scaling is typically done by scaling the batch-size"
}
```

文件里的 `text` 比这里长。它从 `Throughout this section...` 开始，中间含有上面这一句。这里只写出被 Table 1 和 Figure 5 切开后又接上的那一句。

`continues_prev` 为 true 的正文接在前面最后一段正文末尾，不新开一块。行末的连字符保留：第 5 页的 `itera-` 和第 6 页的 `tions` 接成 `itera-tions`，这块的 `start_page` 是 5，`end_page` 是 6。

图和表仍是自己的 chunk，出现在它们原来的位置。被 Table 1 和 Figure 5 分开的句子仍在同一块里：`Weak scaling is typically done by scaling the batch-size`。表块里先是表注，再是 HTML。图块里留下图注。短块留下，例如单独的 `K`。

## 还没做

- 不按字数再切，相邻块没有重叠。
- 表格文字仍在表块里，没有从别的 chunk 再删一份。
- 图注留在图块里，没有另做绑定。
- 公式仍是块里的 LaTeX，没有改成普通文字。
- chunk 文本里可能仍有 `<img src="data:image/jpeg;base64,...">`。Megatron-LM 第 12 页序号 149 的表块里是 Figure 8 的 JPEG。这一页对照过 PDF：文字样本本身没有图，图是 Figure 8，和样本被收进同一格。其余页没有因此再对照。建索引时从送去嵌入的文本里去掉这种标签，不另存图片，回答旁边也不显示图。
- 索引、检索和问答还没有。
