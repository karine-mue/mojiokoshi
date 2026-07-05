#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

CONFIGS=(
  "configs/ja_auto.toml"
  "configs/ja_specification.toml"
  "configs/en_auto.toml"
  "configs/en_specification.toml"
)

for config in "${CONFIGS[@]}"; do
  if [ ! -f "$config" ]; then
    echo "[ERROR] config not found: $config" >&2
    exit 1
  fi
done

for config in "${CONFIGS[@]}"; do
  echo
  echo "============================================================"
  echo "RUN: $config"
  echo "============================================================"
  bash scripts/run_one.sh "$config"
done

echo
echo "============================================================"
echo "CHECK"
echo "============================================================"
bash scripts/check.sh

echo
echo "============================================================"
echo "COMPARE"
echo "============================================================"
bash scripts/compare.sh

echo
echo "============================================================"
echo "COMPARE_MODEL"
echo "============================================================"
bash scripts/compare_model.sh
