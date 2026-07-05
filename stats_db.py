from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path


AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".opus"}

COLUMN_DEFINITIONS: dict[str, str] = {
    "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
    "run_id": "TEXT",
    "run_user": "TEXT",
    "run_host": "TEXT",
    "run_started_at": "TEXT",
    "run_finished_at": "TEXT",
    "elapsed_sec": "REAL",
    "experiment_name": "TEXT",
    "run_label": "TEXT",
    "config_path": "TEXT",
    "config_snapshot": "TEXT",
    "audio_path": "TEXT",
    "audio_file": "TEXT",
    "audio_stem": "TEXT",
    "audio_size_bytes": "INTEGER",
    "audio_mtime": "TEXT",
    "source_language": "TEXT",
    "model": "TEXT",
    "device": "TEXT",
    "compute_type": "TEXT",
    "language_arg": "TEXT",
    "detected_language": "TEXT",
    "language_probability": "REAL",
    "duration_sec": "REAL",
    "segment_count": "INTEGER",
    "transcript_chars": "INTEGER",
    "vad_filter": "INTEGER",
    "beam_size": "INTEGER",
    "output_dir": "TEXT",
    "output_txt": "TEXT",
    "output_srt": "TEXT",
    "output_json": "TEXT",
    "log_path": "TEXT",
    "status": "TEXT",
    "error_message": "TEXT",
    "is_deleted": "INTEGER NOT NULL DEFAULT 0",
    "deleted_at": "TEXT",
    "delete_reason": "TEXT",
}

RUN_STAT_COLUMNS = [
    column
    for column in COLUMN_DEFINITIONS
    if column not in {"id", "is_deleted", "deleted_at", "delete_reason"}
]

INDEX_SQL = [
    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_transcribe_runs_run_id
    ON transcribe_runs (run_id)
    WHERE run_id IS NOT NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transcribe_runs_experiment
    ON transcribe_runs (experiment_name, run_label)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transcribe_runs_audio_language
    ON transcribe_runs (audio_file, source_language, language_arg)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transcribe_runs_user_host
    ON transcribe_runs (run_user, run_host)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_transcribe_runs_deleted
    ON transcribe_runs (is_deleted)
    """,
]


def safe_stem(name: str) -> str:
    """
    Windows/WSLでファイル名にしにくい文字を軽く置換する。
    日本語はそのまま残す。
    """
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name or "unknown"


def run_label_part(run_label: str) -> str:
    return safe_stem(run_label) if run_label.strip() else "run"


def run_timestamp_part(timestamp: str) -> str:
    value = timestamp.strip()
    try:
        return datetime.fromisoformat(value).strftime("%Y%m%d_%H%M%S")
    except ValueError:
        return safe_stem(value)


def make_run_id(timestamp: str, run_label: str, audio_stem: str) -> str:
    return f"{run_timestamp_part(timestamp)}_{run_label_part(run_label)}_{safe_stem(audio_stem)}"


def resolve_project_path(project_root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return project_root / path


def init_db(db_path: Path) -> None:
    """
    stats用SQLiteを初期化する。
    既存DBに列が足りない場合は追加する。
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    columns_sql = ",\n                ".join(
        f"{column_name} {column_type}"
        for column_name, column_type in COLUMN_DEFINITIONS.items()
    )

    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS transcribe_runs (
                    {columns_sql}
                )
                """
            )

            existing_columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(transcribe_runs)").fetchall()
            }

            for column_name, column_type in COLUMN_DEFINITIONS.items():
                if column_name == "id":
                    continue
                if column_name not in existing_columns:
                    conn.execute(
                        f"ALTER TABLE transcribe_runs ADD COLUMN {column_name} {column_type}"
                    )

            for index_sql in INDEX_SQL:
                conn.execute(index_sql)


def run_already_recorded(db_path: Path, run_id: str) -> bool:
    if not db_path.exists():
        return False

    with closing(sqlite3.connect(db_path)) as conn:
        row = conn.execute(
            "select 1 from transcribe_runs where run_id = ? limit 1",
            (run_id,),
        ).fetchone()
    return row is not None


def _path_or_none(path: Path | None) -> str | None:
    return str(path) if path else None


def _audio_metadata(audio_path: Path, audio_exists: bool) -> tuple[int | None, str | None]:
    stat = audio_path.stat() if audio_exists and audio_path.exists() else None
    audio_size_bytes = stat.st_size if stat else None
    audio_mtime = (
        datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds")
        if stat
        else None
    )
    return audio_size_bytes, audio_mtime


def _insert_stat_params(db_path: Path, params: dict[str, object]) -> None:
    columns_sql = ",\n                ".join(RUN_STAT_COLUMNS)
    values_sql = ",\n                ".join(f":{column}" for column in RUN_STAT_COLUMNS)
    missing = [column for column in RUN_STAT_COLUMNS if column not in params]
    if missing:
        raise KeyError(f"missing run stat columns: {missing}")

    with closing(sqlite3.connect(db_path)) as conn:
        with conn:
            conn.execute(
                f"""
                INSERT INTO transcribe_runs (
                    {columns_sql}
                )
                VALUES (
                    {values_sql}
                )
                """,
                params,
            )


def insert_run_stat(
    *,
    db_path: Path,
    run_id: str,
    run_user: str,
    run_host: str,
    run_started_at: str,
    run_finished_at: str,
    elapsed_sec: float,
    experiment_name: str,
    run_label: str,
    config_path: Path,
    config_snapshot: Path | None,
    audio_path: Path,
    source_language: str,
    model_size: str,
    device: str,
    compute_type: str,
    language_arg: str,
    detected_language: str | None,
    language_probability: float | None,
    duration_sec: float | None,
    segment_count: int | None,
    transcript_chars: int | None,
    vad_filter: bool,
    beam_size: int,
    run_output_dir: Path | None,
    txt_path: Path | None,
    srt_path: Path | None,
    json_path: Path | None,
    log_path: Path | None,
    status: str,
    error_message: str | None,
) -> None:
    audio_size_bytes, audio_mtime = _audio_metadata(audio_path, audio_path.exists())

    params = {
        "run_id": run_id,
        "run_user": run_user,
        "run_host": run_host,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "elapsed_sec": elapsed_sec,
        "experiment_name": experiment_name,
        "run_label": run_label,
        "config_path": str(config_path),
        "config_snapshot": _path_or_none(config_snapshot),
        "audio_path": str(audio_path),
        "audio_file": audio_path.name,
        "audio_stem": audio_path.stem,
        "audio_size_bytes": audio_size_bytes,
        "audio_mtime": audio_mtime,
        "source_language": source_language,
        "model": model_size,
        "device": device,
        "compute_type": compute_type,
        "language_arg": language_arg,
        "detected_language": detected_language,
        "language_probability": language_probability,
        "duration_sec": duration_sec,
        "segment_count": segment_count,
        "transcript_chars": transcript_chars,
        "vad_filter": int(vad_filter),
        "beam_size": beam_size,
        "output_dir": _path_or_none(run_output_dir),
        "output_txt": _path_or_none(txt_path),
        "output_srt": _path_or_none(srt_path),
        "output_json": _path_or_none(json_path),
        "log_path": _path_or_none(log_path),
        "status": status,
        "error_message": error_message,
    }

    _insert_stat_params(db_path, params)


def insert_error_stat(
    *,
    db_path: Path,
    run_id: str,
    run_user: str,
    run_host: str,
    run_started_at: str,
    run_finished_at: str,
    elapsed_sec: float,
    experiment_name: str,
    run_label: str,
    config_path: Path,
    config_snapshot: Path | None,
    audio_path: Path,
    audio_exists: bool,
    source_language: str,
    model_size: str,
    device: str,
    compute_type: str,
    language_arg: str,
    vad_filter: bool,
    beam_size: int,
    run_output_dir: Path | None,
    log_path: Path | None,
    error_message: str,
) -> None:
    audio_size_bytes, audio_mtime = _audio_metadata(audio_path, audio_exists)

    params = {
        "run_id": run_id,
        "run_user": run_user,
        "run_host": run_host,
        "run_started_at": run_started_at,
        "run_finished_at": run_finished_at,
        "elapsed_sec": elapsed_sec,
        "experiment_name": experiment_name,
        "run_label": run_label,
        "config_path": str(config_path),
        "config_snapshot": _path_or_none(config_snapshot),
        "audio_path": str(audio_path),
        "audio_file": audio_path.name,
        "audio_stem": audio_path.stem,
        "audio_size_bytes": audio_size_bytes,
        "audio_mtime": audio_mtime,
        "source_language": source_language,
        "model": model_size,
        "device": device,
        "compute_type": compute_type,
        "language_arg": language_arg,
        "detected_language": None,
        "language_probability": None,
        "duration_sec": None,
        "segment_count": None,
        "transcript_chars": None,
        "vad_filter": int(vad_filter),
        "beam_size": beam_size,
        "output_dir": _path_or_none(run_output_dir),
        "output_txt": None,
        "output_srt": None,
        "output_json": None,
        "log_path": _path_or_none(log_path),
        "status": "error",
        "error_message": error_message,
    }

    _insert_stat_params(db_path, params)
