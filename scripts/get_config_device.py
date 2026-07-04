from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: get_config_device.py CONFIG_PATH", file=sys.stderr)
        return 2

    config_path = Path(sys.argv[1])
    with config_path.open("rb") as f:
        config = tomllib.load(f)

    print(str(config.get("device", "")).strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
