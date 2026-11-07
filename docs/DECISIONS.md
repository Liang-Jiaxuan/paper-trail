# 设计决策

本文件只记关键设计决策。阶段性成果的说明写在单独的文档里。解析见 [PARSING.md](PARSING.md)，分块见 [CHUNKING.md](CHUNKING.md)，BM25、稠密向量和 RRF 见 [INDEXING.md](INDEXING.md)。

## 语料主题

第一批论文选 LLM 训练与推理系统，分成 `llm-systems/training` 和 `llm-systems/inference` 两个标签。

选它的原因有两个。一是这些论文我读过，标注评测题时能较快找到证据所在页。二是这类论文的吞吐、显存、精度数字都依赖硬件和实验设置，适合检验系统会不会把不可比较的数字放在一起比，或者把 A 论文的结果算到 B 论文头上。

系统本身不绑定主题。论文用 `topics` 标注方向，以后可以继续加别的方向。实验用 `collections` 指定一组论文，评测用过的 collection 会冻结（`frozen: true`），之后不再改动。

B0 用这 6 篇。它们同时包含双栏、单栏、结果表和方法图，用来检查解析能不能分开这些版式。`b0-spike` 在解析和抽检完成前不冻结。

## 论文清单规则

`data/manifest.json` 只记录论文信息，不放解析结果或失败记录。

- `paper_id` 用“第一作者姓-方法名”，全小写，确定后不改，因为 chunk ID 会由它生成。暂时不知道作者时只写方法名，核实后再定。
- `year` 写首个 arXiv 版本的年份。正式发表的会议或期刊写在 `venue`。
- 钉住一份具体文件。arXiv 论文写下版本号；`sha256` 对应该文件的字节。
- `metadata_verified` 为 `false` 时，字段里的 `null` 表示还没查，不表示没有。
- 仓库只提交清单，不提交 PDF，除非论文许可明确允许再分发。

问：下载后的文件名要改成 `title` 吗？怎样确认它就是清单里的那一份？

答：不用改。`paper_id` 是这篇论文在系统里的名字，`sha256` 确认磁盘上的字节就是当时核对的那一版。文件名只方便自己查找。标题里常有冒号，Windows 不能拿它做文件名；GPipe 钉的是 NeurIPS PDF，文件名也不会是 arXiv 号。

```powershell
Get-FileHash -Algorithm SHA256 .\data\raw_pdf\1909.08053v4.pdf
```

输出的 `Hash` 与清单里的 `sha256` 相同，就是同一份文件。大小写不用区分。

## 分块读 MinerU 的 middle JSON

用 B0 那 6 篇论文里抽检的 4 页对照了 PyMuPDF 和 MinerU，记录在 [PARSING.md](PARSING.md)。这 4 页的扁平化结果里，MinerU 留下了图块、表格 HTML 和下标，阅读顺序也与 PDF 一致。2026-11-06 用现在的 middle JSON 又对照了这 4 页，顺序和内容与 PDF 一致，标题、图注、表和上下标都留着。作者肩标 `2` 没有 `superscript`，小节标题的 `level` 都是 2。这个选择只依据这 4 页。

后面的分块读 `data/parsed/mineru/<paper_id>.json`。`middle` 是 MinerU 的 middle JSON，外层加上 `paper_id` 和 `sha256`。块的类型、层级和行内样式按 MinerU 的原样保留。PyMuPDF 导出和按坐标重排的代码已从当前源码移除，对照结论留在 PARSING.md。

## 分块按标题顺序，不猜父子

分块规则见 [CHUNKING.md](CHUNKING.md)。`section_path` 保留文档标题，`chunk_id` 不重复它。后一个小节标题替换上一个。`2` 和 `2.1` 不做成父子。`continues_prev` 的正文接回前面的正文，图和表留在原来的位置。页眉、页脚、页码和脚注不进正文 chunk。

超长正文按字符切，上限 800，在句号处下刀，相邻块不重叠。一整句超过 800 才按字符硬切。多于一行的表整块留下。只有一行、去掉标签后仍超过 800 的表，去掉 `data:image` 后按正文切。解析 JSON 不改。

## 关键词用 BM25

关键词索引用 Okapi BM25，`k1` 为 1.5，`b` 为 0.75。分词只保留小写后的连续字母和数字。返回里只有 `bm25_score`。规则和一次查询见 [INDEXING.md](INDEXING.md)。

## 稠密向量用本地 bge-m3

论文是英文，而且分块里有放不进 512 token 的长表，所以嵌入用本地 `BAAI/bge-m3` 的稠密向量，1024 维，上下文 8192 token。只用稠密向量。NarrativeQA 上的 nDCG@10，bge-m3 稠密向量是 48.7，text-embedding-3-large 是 51.6，接受这个差距。索引和同一次查询见 [INDEXING.md](INDEXING.md)。

## 两路用 RRF 融合

BM25 和稠密向量在查询时融合，不另建一份索引。每一路默认取 50 条候选，查询时可以传入别的深度。再按 `1 / (60 + 名次)` 相加，最终留下 5 条。结果同时保留两路的分数和名次，缺的一路留空。规则和一次查询见 [INDEXING.md](INDEXING.md)。

## 包与环境

- 包名 `paper_trail`，`src` 布局。
- conda 环境 `paper-trail`，Python 3.12，见 `environment.yml`。
- 依赖随阶段加入 `pyproject.toml`。当前是 `mineru`、`numpy`、`sentence-transformers` 和 `torch`。

## 实现约束

解析见 [PARSING.md](PARSING.md)，分块见 [CHUNKING.md](CHUNKING.md)。分块已经做到：

- chunk ID 由 `paper_id`、当前小节和块序号生成，文档标题不写入 ID，重复构建结果不变。
- chunk 记录起止页码，不只记第一页。
- 不静默丢弃短块。
- 正文和参考文献超过 800 个字符时按句号切开，相邻块不重叠。多行表整块留下。chunk 文本里的 `data:image` 已去掉。

下面这些约束还没有做完：

- 表格区域从正文中排除，表格内容只入库一次。
- 章节、页眉页脚的识别规则针对英文论文设计。

检索：

- 拒答阈值只用向量相似度。RRF 分和 Rerank 分不参与阈值判断，分数缺失时不默认放行。
- 过滤条件同时作用于向量检索和 BM25，有过滤时也照常做阈值判断。
- CrossEncoder 在 Pipeline 初始化时加载一次。

工程与评测：

- 命令行、评测脚本和服务接口共用一个配置对象和同一条执行链路。
- 消融实验与主链路使用同一个分词器。
- 评测保存原始回答、检索候选和分数，并写明当次配置。
