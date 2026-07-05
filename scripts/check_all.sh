#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

DB="stats/transcribe_runs.sqlite3"

if [ ! -f "$DB" ]; then
  echo "[ERROR] stats database not found: $DB" >&2
  echo "Run transcription first:" >&2
  echo "  python transcribe_m4a.py --config config.toml" >&2
  echo "or" >&2
  echo "  bash scripts/run_all.sh" >&2
  exit 1
fi

if ! command -v sqlite3 >/dev/null 2>&1; then
  echo "[ERROR] sqlite3 command not found" >&2
  exit 1
fi

sqlite3 -header -column "$DB" < query/dml/check_all.sql
