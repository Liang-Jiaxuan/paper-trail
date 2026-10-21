# paper-trail

一个面向学术论文 PDF 的可溯源问答助手。

目标是把双栏论文里的正文、表格和图注按正确的阅读顺序解析出来；回答问题时给出论文、页码和原文片段，并检查答案里的数字是否真的出自被引用的那一页。

第一批论文是 LLM 训练与推理系统方向。

## 当前状态

早期阶段。目前只有包结构和论文清单的格式，PDF 解析、检索和问答都还没有实现。

## 计划

1. PDF 解析：阅读顺序、表格、图注、页码与坐标
2. 结构化分块与混合检索
3. 带页码引用的问答
4. 数字与来源归属校验

## 论文与许可

仓库不包含论文 PDF。`data/manifest.json` 记录每篇论文的来源、版本和 SHA-256，可按清单自行下载。

## 运行测试

```powershell
conda env create -f environment.yml
conda activate paper-trail
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
```

设计决策见 [docs/DECISIONS.md](docs/DECISIONS.md)。
