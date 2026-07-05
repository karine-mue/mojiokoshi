from __future__ import annotations

import argparse
import getpass
import json
import logging
import shutil
import socket
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from stats_db import (
    AUDIO_EXTENSIONS,
    init_db,
    insert_run_stat,
    make_run_id,
    resolve_project_path,
)


def format_timestamp_srt(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours = millis // 3_600_000
    millis %= 3_600_000
    minutes = millis // 60_000
    millis %= 60_000
    secs = millis // 1000
    millis %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(
            f"config file not found: {config_path}\n"
            f"create config.toml first."
        )

    with config_path.open("rb") as f:
        return tomllib.load(f)


def find_latest_audio(data_dir: Path) -> Path:
    if not data_dir.exists():
        raise FileNotFoundError(f"data_dir does not exist: {data_dir}")

    files = [
        p
        for p in data_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]

    if not files:
        raise FileNotFoundError(f"audio file not found under: {data_dir}")

    return max(files, key=lambda p: p.stat().st_mtime).resolve()


def resolve_audio_path(input_name: str | None, data_dir: Path) -> Path:
    """
    input_name が空なら data_dir の最新音声。
    input_name があれば、
      1. 絶対パス
      2. カレント相対
      3. data_dir 配下
    の順で探す。
    """
    if input_name is None or input_name.strip() == "":
        return find_latest_audio(data_dir)

    raw = Path(input_name).expanduser()

    if raw.is_absolute() and raw.exists():
        return raw.resolve()

    if raw.exists():
        return raw.resolve()

    candidate = data_dir / input_name
    if candidate.exists():
        return candidate.resolve()

    raise FileNotFoundError(
        f"audio file not found: {input_name}\n"
        f"checked: {raw.resolve()} / {candidate.resolve()}"
    )


def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("transcribe")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def validate_config(config: dict[str, Any]) -> None:
    device = config.get("device", "cpu")
    if device not in {"cpu", "cuda"}:
        raise ValueError(f"device must be cpu or cuda: {device}")

    language = config.get("language", "auto")
    if language not in {"auto", "ja", "en"}:
        raise ValueError(f"language must be auto, ja, or en: {language}")

    source_language = config.get("source_language", "unknown")
    if source_language not in {"ja", "en", "unknown"}:
        raise ValueError(f"source_language must be ja, en, or unknown: {source_language}")

    beam_size = config.get("beam_size", 5)
    if isinstance(beam_size, bool) or not isinstance(beam_size, int) or beam_size < 1:
        raise ValueError(f"beam_size must be positive integer: {beam_size}")

    vad_filter = config.get("vad_filter", True)
    if not isinstance(vad_filter, bool):
        raise ValueError(f"vad_filter must be true or false: {vad_filter}")


def write_outputs(
    *,
    run_id: str,
    segments: Iterable,
    info: Any,
    audio_path: Path,
    run_output_dir: Path,
    model_size: str,
    device: str,
    compute_type: str,
    language_arg: str,
    source_language: str,
    logger: logging.Logger,
) -> dict[str, Any]:
    txt_path = run_output_dir / "transcript.txt"
    srt_path = run_output_dir / "transcript.srt"
    json_path = run_output_dir / "result.json"

    all_segments: list[dict[str, Any]] = []

    logger.info("writing txt: %s", txt_path)
    logger.info("writing srt: %s", srt_path)

    with txt_path.open("w", encoding="utf-8") as txt, srt_path.open("w", encoding="utf-8") as srt:
        for i, seg in enumerate(segments, start=1):
            text = seg.text.strip()

            row = {
                "index": i,
                "start": seg.start,
                "end": seg.end,
                "text": text,
            }
            all_segments.append(row)

            txt.write(f"[{seg.start:8.2f} - {seg.end:8.2f}] {text}\n")

            srt.write(f"{i}\n")
            srt.write(f"{format_timestamp_srt(seg.start)} --> {format_timestamp_srt(seg.end)}\n")
            srt.write(f"{text}\n\n")

            if i % 20 == 0:
                logger.info("processed segments: %d", i)

    meta = {
        "run_id": run_id,
        "audio": str(audio_path),
        "audio_file": audio_path.name,
        "audio_stem": audio_path.stem,
        "model": model_size,
        "device": device,
        "compute_type": compute_type,
        "source_language": source_language,
        "language_arg": language_arg,
        "detected_language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": all_segments,
    }

    logger.info("writing json: %s", json_path)
    json_path.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("segments total: %d", len(all_segments))
    logger.info("done")
    logger.info("txt : %s", txt_path)
    logger.info("srt : %s", srt_path)
    logger.info("json: %s", json_path)

    return {
        "txt_path": txt_path,
        "srt_path": srt_path,
        "json_path": json_path,
        "segment_count": len(all_segments),
        "transcript_chars": sum(len(seg["text"]) for seg in all_segments),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using faster-whisper."
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="config file path. default: config.toml",
    )

    args = parser.parse_args()

    logger: logging.Logger | None = None

    try:
        started_monotonic = time.monotonic()
        run_started_at = datetime.now().isoformat(timespec="seconds")

        project_root = Path(__file__).resolve().parent

        config_path = Path(args.config).expanduser()
        if not config_path.is_absolute():
            config_path = project_root / config_path

        config = load_config(config_path)
        validate_config(config)

        data_dir = resolve_project_path(project_root, config.get("data_dir", "data"))
        output_dir = resolve_project_path(project_root, config.get("output_dir", "output"))
        log_dir = resolve_project_path(project_root, config.get("log_dir", "log"))
        stats_dir = resolve_project_path(project_root, config.get("stats_dir", "stats"))

        data_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        stats_dir.mkdir(parents=True, exist_ok=True)

        audio_name = config.get("audio_file", "")
        audio_path = resolve_audio_path(audio_name, data_dir)

        experiment_name = str(config.get("experiment_name", ""))
        run_label = str(config.get("run_label", ""))
        source_language = str(config.get("source_language", "unknown"))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_id = make_run_id(timestamp, run_label, audio_path.stem)

        run_user = getpass.getuser()
        run_host = socket.gethostname()

        run_output_dir = output_dir / run_id
        run_output_dir.mkdir(parents=True, exist_ok=False)

        log_path = log_dir / f"{run_id}.log"
        logger = setup_logger(log_path)

        config_snapshot_path = run_output_dir / "config_snapshot.toml"
        shutil.copyfile(config_path, config_snapshot_path)

        db_file = str(config.get("db_file", "transcribe_runs.sqlite3"))
        db_path = stats_dir / db_file
        init_db(db_path)

        model_size = str(config.get("model", "medium"))
        device = str(config.get("device", "cpu"))

        compute_type_value = config.get("compute_type", "")
        if compute_type_value is None or str(compute_type_value).strip() == "":
            compute_type = "float16" if device == "cuda" else "int8"
        else:
            compute_type = str(compute_type_value)

        language_arg = str(config.get("language", "auto"))
        language = None if language_arg == "auto" else language_arg

        beam_size = int(config.get("beam_size", 5))
        vad_filter = bool(config.get("vad_filter", True))

        logger.info("run_id      : %s", run_id)
        logger.info("run_user    : %s", run_user)
        logger.info("run_host    : %s", run_host)
        logger.info("config      : %s", config_path)
        logger.info("config_snap : %s", config_snapshot_path)
        logger.info("project_root: %s", project_root)
        logger.info("experiment : %s", experiment_name)
        logger.info("run_label  : %s", run_label)
        logger.info("source_lang: %s", source_language)
        logger.info("audio       : %s", audio_path)
        logger.info("model       : %s", model_size)
        logger.info("device      : %s", device)
        logger.info("compute_type: %s", compute_type)
        logger.info("language_arg: %s", language_arg)
        logger.info("language    : %s", language if language is not None else "auto")
        logger.info("beam_size   : %s", beam_size)
        logger.info("vad_filter  : %s", vad_filter)
        logger.info("output_dir  : %s", run_output_dir)
        logger.info("log         : %s", log_path)
        logger.info("stats_db    : %s", db_path)

        logger.info("loading model...")
        from faster_whisper import WhisperModel

        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )

        logger.info("transcribing...")
        segments, info = model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe",
            vad_filter=vad_filter,
            beam_size=beam_size,
        )

        logger.info(
            "detected language: %s probability=%.4f duration=%.2f sec",
            info.language,
            info.language_probability,
            info.duration,
        )

        if info.language_probability < 0.80:
            logger.warning(
                "language detection confidence is low: language=%s probability=%.4f",
                info.language,
                info.language_probability,
            )

        output_result = write_outputs(
            run_id=run_id,
            segments=segments,
            info=info,
            audio_path=audio_path,
            run_output_dir=run_output_dir,
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            language_arg=language_arg,
            source_language=source_language,
            logger=logger,
        )

        run_finished_at = datetime.now().isoformat(timespec="seconds")
        elapsed_sec = time.monotonic() - started_monotonic

        insert_run_stat(
            db_path=db_path,
            run_id=run_id,
            run_user=run_user,
            run_host=run_host,
            run_started_at=run_started_at,
            run_finished_at=run_finished_at,
            elapsed_sec=elapsed_sec,
            experiment_name=experiment_name,
            run_label=run_label,
            config_path=config_path,
            config_snapshot=config_snapshot_path,
            audio_path=audio_path,
            source_language=source_language,
            model_size=model_size,
            device=device,
            compute_type=compute_type,
            language_arg=language_arg,
            detected_language=info.language,
            language_probability=info.language_probability,
            duration_sec=info.duration,
            segment_count=output_result["segment_count"],
            transcript_chars=output_result["transcript_chars"],
            vad_filter=vad_filter,
            beam_size=beam_size,
            run_output_dir=run_output_dir,
            txt_path=output_result["txt_path"],
            srt_path=output_result["srt_path"],
            json_path=output_result["json_path"],
            log_path=log_path,
            status="success",
            error_message=None,
        )

        logger.info("elapsed_sec : %.2f", elapsed_sec)
        logger.info("sqlite stat inserted: %s", db_path)

    except Exception:
        if logger is not None:
            logger.exception("fatal error")
        else:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s [%(levelname)s] %(message)s",
            )
            logging.exception("fatal error before logger setup")
        raise


if __name__ == "__main__":
    main()
