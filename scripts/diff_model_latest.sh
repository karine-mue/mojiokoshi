#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

usage() {
  cat >&2 <<'USAGE'
usage:
  scripts/diff_model_latest.sh SOURCE_LANGUAGE LANGUAGE_ARG LEFT_MODEL RIGHT_MODEL
  scripts/diff_model_latest.sh SOURCE_LANGUAGE LANGUAGE_ARG LEFT_EXPERIMENT LEFT_MODEL RIGHT_EXPERIMENT RIGHT_MODEL

examples:
  bash scripts/diff_model_latest.sh ja ja medium large-v3
  bash scripts/diff_model_latest.sh en en medium large-v3
  bash scripts/diff_model_latest.sh en auto medium large-v3
  bash scripts/diff_model_latest.sh ja ja l0opback_lang_compare medium l0opback_lang_compare_LargeV3 large-v3
USAGE
}

if [ "$#" -ne 4 ] && [ "$#" -ne 6 ]; then
  usage
  exit 1
fi

PYTHON_BIN="${PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    PYTHON_BIN="python"
  fi
fi

"$PYTHON_BIN" - "$@" <<'PY'
from __future__ import annotations

import difflib
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DB_PATH = Path("stats/transcribe_runs.sqlite3")
OUT_DIR = Path("output/diff")


def safe_filename(value: str) -> str:
    value = value.strip()
    value = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", value)
    value = re.sub(r"\s+", "_", value)
    return value or "unknown"


def parse_args(argv: list[str]) -> dict[str, str | None]:
    if len(argv) == 5:
        return {
            "source_language": argv[1],
            "language_arg": argv[2],
            "left_experiment": None,
            "left_model": argv[3],
            "right_experiment": None,
            "right_model": argv[4],
        }

    if len(argv) == 7:
        return {
            "source_language": argv[1],
            "language_arg": argv[2],
            "left_experiment": argv[3],
            "left_model": argv[4],
            "right_experiment": argv[5],
            "right_model": argv[6],
        }

    raise SystemExit("[ERROR] invalid arguments")


def get_output_dir(
    conn: sqlite3.Connection,
    *,
    source_language: str,
    language_arg: str,
    model: str,
    experiment_name: str | None,
) -> tuple[str, str, Path]:
    params: list[str] = [source_language, language_arg, model]
    experiment_filter = ""
    if experiment_name is not None:
        experiment_filter = "and experiment_name = ?"
        params.append(experiment_name)

    row = conn.execute(
        f"""
        select run_id, experiment_name, output_dir
        from transcribe_runs
        where source_language = ?
          and language_arg = ?
          and model = ?
          {experiment_filter}
          and coalesce(is_deleted, 0) = 0
          and coalesce(status, 'success') = 'success'
          and output_dir is not null
        order by id desc
        limit 1
        """,
        params,
    ).fetchone()

    if row is None:
        detail = (
            f"source_language={source_language}, language_arg={language_arg}, "
            f"model={model}"
        )
        if experiment_name is not None:
            detail += f", experiment_name={experiment_name}"
        raise SystemExit(f"[ERROR] output_dir not found for {detail}")

    return str(row[0]), str(row[1]), Path(str(row[2]))


def read_transcript(output_dir: Path) -> tuple[Path, list[str]]:
    transcript_path = output_dir / "transcript.txt"
    if not transcript_path.is_file():
        raise SystemExit(f"[ERROR] transcript not found: {transcript_path}")
    return transcript_path, transcript_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)


def main() -> int:
    args = parse_args(sys.argv)

    if not DB_PATH.exists():
        print(f"[ERROR] stats database not found: {DB_PATH}", file=sys.stderr)
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        left_run_id, left_experiment, left_dir = get_output_dir(
            conn,
            source_language=str(args["source_language"]),
            language_arg=str(args["language_arg"]),
            model=str(args["left_model"]),
            experiment_name=args["left_experiment"],
        )
        right_run_id, right_experiment, right_dir = get_output_dir(
            conn,
            source_language=str(args["source_language"]),
            language_arg=str(args["language_arg"]),
            model=str(args["right_model"]),
            experiment_name=args["right_experiment"],
        )

    left_file, left_lines = read_transcript(left_dir)
    right_file, right_lines = read_transcript(right_dir)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_language = str(args["source_language"])
    language_arg = str(args["language_arg"])
    left_model = str(args["left_model"])
    right_model = str(args["right_model"])

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = (
        f"model_{safe_filename(source_language)}_{safe_filename(language_arg)}_"
        f"{safe_filename(left_experiment)}_{safe_filename(left_model)}_vs_"
        f"{safe_filename(right_experiment)}_{safe_filename(right_model)}"
    )
    diff_path = OUT_DIR / f"{timestamp}_{out_name}.diff"

    diff_lines = list(
        difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile=f"{left_run_id}/{left_file.name}",
            tofile=f"{right_run_id}/{right_file.name}",
        )
    )
    diff_path.write_text("".join(diff_lines), encoding="utf-8")

    print("Left:")
    print(f"  experiment_name: {left_experiment}")
    print(f"  model          : {left_model}")
    print(f"  run_id         : {left_run_id}")
    print("Right:")
    print(f"  experiment_name: {right_experiment}")
    print(f"  model          : {right_model}")
    print(f"  run_id         : {right_run_id}")
    print(diff_path)

    if not diff_lines:
        print("[INFO] diff is empty")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
