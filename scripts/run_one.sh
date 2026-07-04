#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: bash scripts/run_one.sh CONFIG_PATH" >&2
  echo "example: bash scripts/run_one.sh configs/ja_auto.toml" >&2
  exit 1
fi

CONFIG="$1"
RUN_ONE_STARTED_AT="$(date +%s)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  . ".venv/bin/activate"
fi

if [ ! -f "$CONFIG" ]; then
  echo "[ERROR] config not found: $CONFIG" >&2
  exit 1
fi

DEVICE="$(python scripts/get_config_device.py "$CONFIG")"

if [ "$DEVICE" = "cuda" ]; then
  echo "[INFO] device=cuda; loading CUDA environment"
  # shellcheck disable=SC1091
  . "scripts/cuda_env.sh"
elif [ "$DEVICE" = "cpu" ]; then
  echo "[INFO] device=cpu; skipping CUDA environment"
else
  echo "[WARN] device is not set to cpu/cuda in $CONFIG; running without CUDA environment"
fi

python transcribe_m4a.py --config "$CONFIG" || {
  STATUS="$?"
  python scripts/record_failed_run.py "$CONFIG" "$STATUS" "$RUN_ONE_STARTED_AT" "transcribe" || true
  exit "$STATUS"
}
