#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

"$PYTHON_BIN" - "${1:-}" <<'PY'
from __future__ import annotations

import difflib
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("stats/transcribe_runs.sqlite3")
OUT_DIR = Path("output/diff")

PAIRS = [
    ("ja_specification", "ja_auto", "ja_specification_vs_ja_auto"),
    ("en_specification", "en_auto", "en_specification_vs_en_auto"),
]


def safe_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value)
    value = re.sub(r"\s+", "_", value)
    return value or "unknown"


def latest_experiment_name(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        """
        select experiment_name
        from transcribe_runs
        where coalesce(is_deleted, 0) = 0
          and coalesce(status, 'success') = 'success'
          and coalesce(experiment_name, '') <> ''
        order by id desc
        limit 1
        """
    ).fetchone()

    if row is None or row[0] is None or str(row[0]).strip() == "":
        raise SystemExit("[ERROR] experiment_name not found. Pass experiment_name explicitly.")

    return str(row[0])


def get_output_dir(conn: sqlite3.Connection, experiment_name: str, run_label: str) -> tuple[str, Path]:
    row = conn.execute(
        """
        select run_id, output_dir
        from transcribe_runs
        where experiment_name = ?
          and run_label = ?
          and coalesce(is_deleted, 0) = 0
          and coalesce(status, 'success') = 'success'
          and output_dir is not null
        order by id desc
        limit 1
        """,
        (experiment_name, run_label),
    ).fetchone()

    if row is None:
        raise SystemExit(
            f"[ERROR] output_dir not found for experiment_name={experiment_name}, run_label={run_label}"
        )

    return str(row[0]), Path(str(row[1]))


def read_transcript(output_dir: Path) -> tuple[Path, list[str]]:
    transcript_path = output_dir / "transcript.txt"
    if not transcript_path.is_file():
        raise SystemExit(f"[ERROR] transcript not found: {transcript_path}")
    return transcript_path, transcript_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)


def make_diff(conn: sqlite3.Connection, experiment_name: str, left_label: str, right_label: str, out_name: str) -> None:
    left_run_id, left_dir = get_output_dir(conn, experiment_name, left_label)
    right_run_id, right_dir = get_output_dir(conn, experiment_name, right_label)

    left_file, left_lines = read_transcript(left_dir)
    right_file, right_lines = read_transcript(right_dir)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    diff_path = OUT_DIR / f"{timestamp}_{safe_filename(experiment_name)}_{safe_filename(out_name)}.diff"

    diff_lines = list(
        difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile=f"{left_run_id}/{left_file.name}",
            tofile=f"{right_run_id}/{right_file.name}",
        )
    )
    diff_path.write_text("".join(diff_lines), encoding="utf-8")

    print(diff_path)
    if not diff_lines:
        print(f"[INFO] diff is empty: {left_label} vs {right_label}")


def main() -> int:
    experiment_name = sys.argv[1].strip()

    if not DB_PATH.exists():
        print(f"[ERROR] stats database not found: {DB_PATH}", file=sys.stderr)
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        if experiment_name == "":
            experiment_name = latest_experiment_name(conn)

        print(f"Experiment: {experiment_name}")

        for left_label, right_label, out_name in PAIRS:
            print()
            print(f"{left_label} vs {right_label}")
            make_diff(conn, experiment_name, left_label, right_label, out_name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
