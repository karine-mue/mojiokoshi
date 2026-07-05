from __future__ import annotations

import sys
from pathlib import Path

from orchestration import run_one


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        print("usage: python run_one.py CONFIG_PATH", file=sys.stderr)
        print("example: python run_one.py configs/ja_auto.toml", file=sys.stderr)
        return 2

    project_root = Path(__file__).resolve().parent
    return run_one(argv[0], python_bin=sys.executable, project_root=project_root)


if __name__ == "__main__":
    raise SystemExit(main())
