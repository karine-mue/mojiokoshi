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

if [[ "$TARGET" =~ ^[0-9]+$ ]]; then
  WHERE_CLAUSE="id = $TARGET"
else
  WHERE_CLAUSE="run_id = '$TARGET'"
fi

sqlite3 stats/transcribe_runs.sqlite3 <<SQL
update transcribe_runs
set
  is_deleted = 0,
  deleted_at = null,
  delete_reason = null
where $WHERE_CLAUSE;
SQL

sqlite3 -header -column stats/transcribe_runs.sqlite3 \
'select id, run_id, coalesce(is_deleted, 0) as is_deleted, deleted_at, delete_reason from transcribe_runs order by id;'
