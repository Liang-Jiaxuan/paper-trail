"""生成 chunk：python -m paper_trail.chunking"""

import sys

from paper_trail import config
from paper_trail.chunking.build import write_chunks

_USAGE = "用法: python -m paper_trail.chunking"


def main(argv: list[str] | None = None) -> None:
    """读取 data/parsed/mineru，写出 data/chunks。"""
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        raise SystemExit(_USAGE)
    written = write_chunks(config.PARSED_DIR, config.CHUNKS_DIR)
    print(f"写入 {len(written)} 个文件到 {config.CHUNKS_DIR}")


if __name__ == "__main__":
    main()
