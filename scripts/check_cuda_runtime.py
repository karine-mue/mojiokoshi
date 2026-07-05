from __future__ import annotations

import ctypes
import sys

CUDA_LIBRARY_NAMES = [
    "libcudart.so.12",
    "libcublasLt.so.12",
    "libcublas.so.12",
    "libcudnn.so.9",
]


def main() -> int:
    missing: list[str] = []
    for lib_name in CUDA_LIBRARY_NAMES:
        try:
            ctypes.CDLL(lib_name)
        except OSError as exc:
            missing.append(f"{lib_name}: {exc}")

    if missing:
        print(
            "CUDA libraries could not be loaded.\n"
            "Install optional CUDA requirements first:\n"
            "  pip install -r requirements-cuda.txt\n"
            + "\n".join(missing),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
