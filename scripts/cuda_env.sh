#!/usr/bin/env bash
set -euo pipefail

SITE_PACKAGES="$(python -c 'import site; print(site.getsitepackages()[0])')"

CUDA_LIB_DIRS=(
  "$SITE_PACKAGES/nvidia/cuda_runtime/lib"
  "$SITE_PACKAGES/nvidia/cublas/lib"
  "$SITE_PACKAGES/nvidia/cudnn/lib"
)

for dir in "${CUDA_LIB_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    case ":${LD_LIBRARY_PATH:-}:" in
      *":$dir:"*) ;;
      *) export LD_LIBRARY_PATH="$dir${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
    esac
  fi
done

python - <<'PY'
import ctypes

libs = [
    "libcudart.so.12",
    "libcublasLt.so.12",
    "libcublas.so.12",
    "libcudnn.so.9",
]

missing = []
for lib in libs:
    try:
        ctypes.CDLL(lib)
    except OSError as exc:
        missing.append(f"{lib}: {exc}")

if missing:
    raise RuntimeError(
        "CUDA libraries could not be loaded.\n"
        "Install optional CUDA requirements first:\n"
        "  pip install -r requirements-cuda.txt\n"
        + "\n".join(missing)
    )
PY
