#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: scripts/restore_run.sh RUN_ID_OR_DB_ID" >&2
  echo "example by id    : scripts/restore_run.sh 1" >&2
  echo "example by run_id: scripts/restore_run.sh 20260704_214356_ja_specification_l0opback_ja" >&2
  exit 1
fi

TARGET="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

python - "$TARGET" <<'PY'
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("stats/transcribe_runs.sqlite3")

target = sys.argv[1]

if not DB_PATH.exists():
    print(f"[ERROR] stats database not found: {DB_PATH}", file=sys.stderr)
    raise SystemExit(1)

if re.fullmatch(r"[0-9]+", target):
    where_sql = "id = ?"
    where_param: int | str = int(target)
else:
    where_sql = "run_id = ?"
    where_param = target

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.execute(
        f"""
        update transcribe_runs
        set
          is_deleted = 0,
          deleted_at = null,
          delete_reason = null
        where {where_sql}
        """,
        (where_param,),
    )

    if cursor.rowcount == 0:
        print(f"[WARN] no matching run: {target}", file=sys.stderr)
PY

sqlite3 -header -column stats/transcribe_runs.sqlite3 \
'select id, run_id, coalesce(is_deleted, 0) as is_deleted, deleted_at, delete_reason from transcribe_runs order by id;'
