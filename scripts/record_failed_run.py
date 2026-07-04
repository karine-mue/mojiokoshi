from __future__ import annotations

import re
import sqlite3
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path

from transcribe_m4a import init_db, insert_run_stat, resolve_audio_path, resolve_project_path, safe_stem


def read_config(project_root: Path, config_arg: str) -> tuple[Path, dict]:
    config_path = Path(config_arg).expanduser()
    if not config_path.is_absolute():
        config_path = project_root / config_path

    with config_path.open("rb") as f:
        return config_path, tomllib.load(f)


def find_latest_log(log_dir: Path, run_label: str, audio_stem: str) -> Path | None:
    suffix = f"_{safe_stem(run_label)}_{safe_stem(audio_stem)}.log"
    candidates = [p for p in log_dir.glob(f"*{suffix}") if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def extract_log_started_at(log_text: str) -> str:
    match = re.search(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", log_text, re.MULTILINE)
    if not match:
        return datetime.now().isoformat(timespec="seconds")
    return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").isoformat(timespec="seconds")


def make_error_message(log_text: str, exit_code: str) -> str:
    marker = "Traceback (most recent call last):"
    idx = log_text.rfind(marker)
    if idx >= 0:
        message = log_text[idx:]
    else:
        message = log_text

    message = message.strip()
    if not message:
        message = f"process exited with code {exit_code}"
    else:
        message = f"exit_code={exit_code}\n{message}"

    if len(message) > 2000:
        return message[-2000:]
    return message


def run_already_recorded(db_path: Path, run_id: str) -> bool:
    if not db_path.exists():
        return False

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "select 1 from transcribe_runs where run_id = ? limit 1",
            (run_id,),
        ).fetchone()
    return row is not None


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python scripts/record_failed_run.py CONFIG_PATH EXIT_CODE", file=sys.stderr)
        return 2

    config_arg = sys.argv[1]
    exit_code = sys.argv[2]

    project_root = Path(__file__).resolve().parent.parent
    config_path, config = read_config(project_root, config_arg)

    data_dir = resolve_project_path(project_root, config.get("data_dir", "data"))
    output_dir = resolve_project_path(project_root, config.get("output_dir", "output"))
    log_dir = resolve_project_path(project_root, config.get("log_dir", "log"))
    stats_dir = resolve_project_path(project_root, config.get("stats_dir", "stats"))

    audio_path = resolve_audio_path(config.get("audio_file", ""), data_dir)

    run_label = str(config.get("run_label", ""))
    source_language = str(config.get("source_language", "unknown"))
    experiment_name = str(config.get("experiment_name", ""))

    log_path = find_latest_log(log_dir, run_label, audio_path.stem)
    if log_path is None:
        print("[WARN] failed run log not found; skip sqlite error record", file=sys.stderr)
        return 0

    run_id = log_path.stem
    run_output_dir = output_dir / run_id
    config_snapshot_path = run_output_dir / "config_snapshot.toml"

    db_file = str(config.get("db_file", "transcribe_runs.sqlite3"))
    db_path = stats_dir / db_file
    init_db(db_path)

    if run_already_recorded(db_path, run_id):
        print(f"[INFO] run already recorded: {run_id}")
        return 0

    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    run_started_at = extract_log_started_at(log_text)
    run_finished_at = datetime.now().isoformat(timespec="seconds")
    error_message = make_error_message(log_text, exit_code)

    model_size = str(config.get("model", ""))
    device = str(config.get("device", ""))
    compute_type_value = config.get("compute_type", "")
    if compute_type_value is None or str(compute_type_value).strip() == "":
        compute_type = "float16" if device == "cuda" else "int8"
    else:
        compute_type = str(compute_type_value)

    language_arg = str(config.get("language", ""))
    vad_filter = bool(config.get("vad_filter", True))
    beam_size = int(config.get("beam_size", 0) or 0)

    started_dt = datetime.fromisoformat(run_started_at)
    finished_dt = datetime.fromisoformat(run_finished_at)
    elapsed_sec = max(0.0, (finished_dt - started_dt).total_seconds())

    insert_run_stat(
        db_path=db_path,
        run_id=run_id,
        run_user="",
        run_host="",
        run_started_at=run_started_at,
        run_finished_at=run_finished_at,
        elapsed_sec=elapsed_sec,
        experiment_name=experiment_name,
        run_label=run_label,
        config_path=config_path,
        config_snapshot=config_snapshot_path if config_snapshot_path.exists() else None,
        audio_path=audio_path,
        source_language=source_language,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        language_arg=language_arg,
        detected_language=None,
        language_probability=None,
        duration_sec=None,
        segment_count=None,
        transcript_chars=None,
        vad_filter=vad_filter,
        beam_size=beam_size,
        run_output_dir=run_output_dir if run_output_dir.exists() else None,
        txt_path=None,
        srt_path=None,
        json_path=None,
        log_path=log_path,
        status="error",
        error_message=error_message,
    )

    print(f"[INFO] sqlite error stat inserted: {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
