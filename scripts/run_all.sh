#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

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
  python transcribe_m4a.py --config "$config"
done

echo
echo "============================================================"
echo "CHECK"
echo "============================================================"
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/check.sql

echo
echo "============================================================"
echo "COMPARE"
echo "============================================================"
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare.sql

echo
echo "============================================================"
echo "COMPARE_MODEL"
echo "============================================================"
sqlite3 -header -column stats/transcribe_runs.sqlite3 < query/dml/compare_model.sql
