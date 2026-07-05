from __future__ import annotations

import getpass
import re
import socket
import sys
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from stats_db import (  # noqa: E402
    AUDIO_EXTENSIONS,
    init_db,
    insert_error_stat,
    make_run_id,
    resolve_project_path,
    run_already_recorded,
    run_label_part,
    safe_stem,
)

ERROR_MESSAGE_LIMIT = 2000
TRUNCATED_MARKER = "...(trimmed)..."


def read_config(project_root: Path, config_arg: str) -> tuple[Path, dict[str, Any]]:
    config_path = Path(config_arg).expanduser()
    if not config_path.is_absolute():
        config_path = project_root / config_path

    with config_path.open("rb") as f:
        return config_path, tomllib.load(f)


def find_latest_audio(data_dir: Path) -> Path | None:
    if not data_dir.exists():
        return None

    files = [
        p
        for p in data_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    if not files:
        return None

    return max(files, key=lambda p: p.stat().st_mtime).resolve()


def resolve_audio_path_for_record(
    input_name: str | None,
    data_dir: Path,
) -> tuple[Path, bool]:
    """
    失敗run記録用のaudio pathを返す。

    本体の `resolve_audio_path()` と違い、音声が存在しなくても例外を投げない。
    音声欠損そのものをDBへ記録するため、存在しない候補Pathを返す。
    """
    if input_name is None or input_name.strip() == "":
        latest = find_latest_audio(data_dir)
        if latest is not None:
            return latest, True
        return data_dir / "unknown_audio", False

    raw = Path(input_name).expanduser()

    if raw.is_absolute():
        return raw, raw.exists()

    if raw.exists():
        return raw.resolve(), True

    candidate = data_dir / input_name
    if candidate.exists():
        return candidate.resolve(), True

    return candidate, False


def find_latest_log(
    log_dir: Path,
    run_label: str,
    audio_stem: str,
    started_epoch: float | None,
) -> Path | None:
    suffix = f"_{run_label_part(run_label)}_{safe_stem(audio_stem)}.log"
    candidates = [p for p in log_dir.glob(f"*{suffix}") if p.is_file()]

    if started_epoch is not None:
        threshold = started_epoch - 2.0
        candidates = [p for p in candidates if p.stat().st_mtime >= threshold]

    if not candidates:
        return None

    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_started_epoch(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_exit_code(value: str | None) -> int | None:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def started_at_from_epoch(started_epoch: float | None) -> str:
    if started_epoch is None:
        return datetime.now().isoformat(timespec="seconds")
    return datetime.fromtimestamp(started_epoch).isoformat(timespec="seconds")


def extract_log_started_at(log_text: str, fallback_epoch: float | None) -> str:
    match = re.search(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", log_text, re.MULTILINE)
    if not match:
        return started_at_from_epoch(fallback_epoch)
    return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S").isoformat(timespec="seconds")


def trim_body_preserving_header(header_text: str, body: str) -> str:
    if not body:
        body = "no log text found"

    message = header_text + "\n" + body
    if len(message) <= ERROR_MESSAGE_LIMIT:
        return message

    prefix = header_text + "\n" + TRUNCATED_MARKER + "\n"
    body_limit = ERROR_MESSAGE_LIMIT - len(prefix)
    if body_limit <= 0:
        return header_text[:ERROR_MESSAGE_LIMIT]

    return prefix + body[-body_limit:]


def make_error_message(
    *,
    log_text: str,
    exit_code: str,
    failure_stage: str,
    audio_exists: bool,
    audio_path: Path,
) -> str:
    marker = "Traceback (most recent call last):"
    idx = log_text.rfind(marker)
    if idx >= 0:
        body = log_text[idx:].strip()
    else:
        body = log_text.strip()

    header = [
        f"exit_code={exit_code}",
        f"failure_stage={failure_stage}",
        f"audio_exists={audio_exists}",
        f"audio_path={audio_path}",
    ]

    return trim_body_preserving_header("\n".join(header), body)


def main() -> int:
    if len(sys.argv) not in {3, 4, 5}:
        print(
            "usage: python scripts/record_failed_run.py CONFIG_PATH EXIT_CODE [STARTED_EPOCH] [FAILURE_STAGE]",
            file=sys.stderr,
        )
        return 2

    config_arg = sys.argv[1]
    exit_code_arg = sys.argv[2]
    exit_code = parse_exit_code(exit_code_arg)
    started_epoch = parse_started_epoch(sys.argv[3] if len(sys.argv) >= 4 else None)
    failure_stage = sys.argv[4] if len(sys.argv) >= 5 else "transcribe"

    config_path, config = read_config(PROJECT_ROOT, config_arg)

    data_dir = resolve_project_path(PROJECT_ROOT, config.get("data_dir", "data"))
    output_dir = resolve_project_path(PROJECT_ROOT, config.get("output_dir", "output"))
    log_dir = resolve_project_path(PROJECT_ROOT, config.get("log_dir", "log"))
    stats_dir = resolve_project_path(PROJECT_ROOT, config.get("stats_dir", "stats"))

    audio_path, audio_exists = resolve_audio_path_for_record(config.get("audio_file", ""), data_dir)
    audio_stem = audio_path.stem or "unknown_audio"

    run_label = str(config.get("run_label", ""))
    source_language = str(config.get("source_language", "unknown"))
    experiment_name = str(config.get("experiment_name", ""))

    log_path = find_latest_log(log_dir, run_label, audio_stem, started_epoch)
    log_text = ""
    if log_path is not None:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")

    run_started_at = extract_log_started_at(log_text, started_epoch)
    run_finished_at = datetime.now().isoformat(timespec="seconds")

    if log_path is not None:
        run_id = log_path.stem
    else:
        run_id = make_run_id(run_started_at, run_label, audio_stem)

    run_output_dir = output_dir / run_id
    config_snapshot_path = run_output_dir / "config_snapshot.toml"

    db_file = str(config.get("db_file", "transcribe_runs.sqlite3"))
    db_path = stats_dir / db_file
    init_db(db_path)

    if run_already_recorded(db_path, run_id):
        print(f"[INFO] run already recorded: {run_id}")
        return 0

    error_message = make_error_message(
        log_text=log_text,
        exit_code=exit_code_arg,
        failure_stage=failure_stage,
        audio_exists=audio_exists,
        audio_path=audio_path,
    )

    model_size = str(config.get("model", ""))
    device = str(config.get("device", ""))
    compute_type_value = config.get("compute_type", "")
    if compute_type_value is None or str(compute_type_value).strip() == "":
        compute_type = "float16" if device == "cuda" else "int8"
    else:
        compute_type = str(compute_type_value)

    language_arg = str(config.get("language", ""))
    vad_filter = bool(config.get("vad_filter", True))
    beam_size_value = config.get("beam_size", 5)
    beam_size = int(beam_size_value if beam_size_value is not None else 5)

    started_dt = datetime.fromisoformat(run_started_at)
    finished_dt = datetime.fromisoformat(run_finished_at)
    elapsed_sec = max(0.0, (finished_dt - started_dt).total_seconds())

    insert_error_stat(
        db_path=db_path,
        run_id=run_id,
        run_user=getpass.getuser(),
        run_host=socket.gethostname(),
        run_started_at=run_started_at,
        run_finished_at=run_finished_at,
        elapsed_sec=elapsed_sec,
        experiment_name=experiment_name,
        run_label=run_label,
        config_path=config_path,
        config_snapshot=config_snapshot_path if config_snapshot_path.exists() else None,
        audio_path=audio_path,
        audio_exists=audio_exists,
        source_language=source_language,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        language_arg=language_arg,
        vad_filter=vad_filter,
        beam_size=beam_size,
        run_output_dir=run_output_dir if run_output_dir.exists() else None,
        log_path=log_path,
        error_message=error_message,
        failure_stage=failure_stage,
        exit_code=exit_code,
    )

    print(f"[INFO] sqlite error stat inserted: {run_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
