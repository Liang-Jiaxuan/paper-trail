"""把最近一次重排结果写成引用，并在未拒答时写英文概括句：python -m paper_trail.generation"""

import json
import os
import sys

from paper_trail import config
from paper_trail.generation.answer import (
    attach_number_checks,
    attach_summary,
    build_answer,
    prompt_messages,
    request_summary,
)

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
    if not answer["refused"]:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise SystemExit("请设置环境变量 DEEPSEEK_API_KEY")
        try:
            content = request_summary(
                prompt_messages(answer["query"], answer["citations"]),
                api_key,
            )
            answer = attach_summary(answer, content)
        except Exception as exc:
            message = str(exc).replace(api_key, "***")
            raise SystemExit(f"概括句请求失败：{message}") from exc
    answer = attach_number_checks(answer)
    config.ANSWER_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.ANSWER_PATH.write_text(
        json.dumps(answer, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"写入 {len(answer['citations'])} 条引用到 {config.ANSWER_PATH}")
    if answer["refused"]:
        print(f"拒答  {answer['answer']}")
    else:
        print(f"概括  model={answer['model']}")
        print(answer["answer"])
    mark = "通过" if answer["numbers_ok"] else "未通过"
    print(f"数字{mark}  {len(answer['number_checks'])} 个")
    for citation in answer["citations"]:
        print(
            f"{citation['rank']}  {citation['chunk_id']}  "
            f"p{citation['start_page']}-{citation['end_page']}"
        )


if __name__ == "__main__":
    main()
