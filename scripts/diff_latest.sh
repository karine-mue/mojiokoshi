#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

DB="stats/transcribe_runs.sqlite3"

get_output_dir() {
  local label="$1"

  sqlite3 "$DB" "
    select output_dir
    from transcribe_runs
    where run_label = '$label'
      and coalesce(is_deleted, 0) = 0
    order by id desc
    limit 1;
  "
}

make_diff() {
  local left_label="$1"
  local right_label="$2"
  local out_name="$3"

  local left_dir
  local right_dir

  left_dir="$(get_output_dir "$left_label")"
  right_dir="$(get_output_dir "$right_label")"

  if [ -z "$left_dir" ]; then
    echo "[ERROR] output_dir not found for run_label=$left_label" >&2
    exit 1
  fi

  if [ -z "$right_dir" ]; then
    echo "[ERROR] output_dir not found for run_label=$right_label" >&2
    exit 1
  fi

  if [ ! -f "$left_dir/transcript.txt" ]; then
    echo "[ERROR] transcript not found: $left_dir/transcript.txt" >&2
    exit 1
  fi

  if [ ! -f "$right_dir/transcript.txt" ]; then
    echo "[ERROR] transcript not found: $right_dir/transcript.txt" >&2
    exit 1
  fi

  mkdir -p output/diff

  local timestamp
  timestamp="$(date +%Y%m%d_%H%M%S)"
  local diff_path="output/diff/${timestamp}_${out_name}.diff"

  diff -u \
    "$left_dir/transcript.txt" \
    "$right_dir/transcript.txt" \
    > "$diff_path" || true

  echo "$diff_path"

  if [ ! -s "$diff_path" ]; then
    echo "[INFO] diff is empty: $left_label vs $right_label"
  fi
}

echo "Japanese: ja_specification vs ja_auto"
make_diff "ja_specification" "ja_auto" "ja_specification_vs_ja_auto"

echo
echo "English: en_specification vs en_auto"
make_diff "en_specification" "en_auto" "en_specification_vs_en_auto"
