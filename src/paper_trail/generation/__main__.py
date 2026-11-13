"""把最近一次重排结果写成引用：python -m paper_trail.generation"""

import json
import sys

from paper_trail import config
from paper_trail.generation.answer import build_answer

_USAGE = "用法: python -m paper_trail.generation"


def main(argv: list[str] | None = None) -> None:
    """读取 data/indexes/rerank/last_query.json，写出 data/answers/last_answer.json。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        raise SystemExit(_USAGE)
    path = config.RERANK_QUERY_PATH
    if not path.is_file():
        raise SystemExit(f"找不到重排结果：{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    try:
        answer = build_answer(payload)
    except KeyError as exc:
        raise SystemExit(f"重排结果缺少字段：{exc.args[0]}") from exc
    config.ANSWER_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.ANSWER_PATH.write_text(
        json.dumps(answer, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"写入 {len(answer['citations'])} 条引用到 {config.ANSWER_PATH}")
    if answer["refused"]:
        print(f"拒答  {answer['answer']}")
    else:
        print("放行  answer=null")
    for citation in answer["citations"]:
        print(
            f"{citation['rank']}  {citation['chunk_id']}  "
            f"p{citation['start_page']}-{citation['end_page']}"
        )


if __name__ == "__main__":
    main()
