from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable
from faster_whisper import WhisperModel


AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".opus"}


def safe_stem(name: str) -> str:
    """
    Windows/WSLでファイル名にしにくい文字を軽く置換する。
    日本語はそのまま残す。
    """
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name or "audio"


def format_timestamp_srt(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    hours = millis // 3_600_000
    millis %= 3_600_000
    minutes = millis // 60_000
    millis %= 60_000
    secs = millis // 1000
    millis %= 1000
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def find_latest_audio(data_dir: Path) -> Path:
    files = [
        p for p in data_dir.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS
    ]
    if not files:
        raise FileNotFoundError(f"音声ファイルが見つかりません: {data_dir}")
    return max(files, key=lambda p: p.stat().st_mtime)


def resolve_audio_path(input_name: str | None, data_dir: Path) -> Path:
    if not input_name:
        return find_latest_audio(data_dir)

    raw = Path(input_name).expanduser()

    if raw.is_absolute() and raw.exists():
        return raw.resolve()

    # まずカレントから見て存在する場合
    if raw.exists():
        return raw.resolve()

    # 次に data/ 配下として見る
    candidate = data_dir / input_name
    if candidate.exists():
        return candidate.resolve()

    raise FileNotFoundError(
        f"音声ファイルが見つかりません: {input_name}\n"
        f"確認先: {raw.resolve()} / {candidate.resolve()}"
    )


def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("transcribe")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

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


def write_outputs(
    *,
    segments: Iterable,
    info,
    audio_path: Path,
    output_prefix: Path,
    model_size: str,
    device: str,
    compute_type: str,
    logger: logging.Logger,
) -> None:
    txt_path = output_prefix.with_suffix(".txt")
    srt_path = output_prefix.with_suffix(".srt")
    json_path = output_prefix.with_suffix(".json")

    all_segments: list[dict] = []

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
        "audio": str(audio_path),
        "model": model_size,
        "device": device,
        "compute_type": compute_type,
        "language": info.language,
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


def main() -> None:
    logger: logging.Logger | None = None

    try:
        parser = argparse.ArgumentParser(
            description="Transcribe audio files under data/ using faster-whisper."
        )

        parser.add_argument(
            "audio",
            nargs="?",
            help="音声ファイル名。省略時は data/ の最新音声ファイルを使う。",
        )
        parser.add_argument(
            "--model",
            default="medium",
            help="Whisper model size. examples: small, medium, large-v3",
        )
        parser.add_argument(
            "--device",
            default="cuda",
            choices=["cpu", "cuda"],
            help="cpu or cuda",
        )
        parser.add_argument(
            "--compute-type",
            default=None,
            help="cpuなら int8、cudaなら float16 など。省略時は自動。",
        )
        parser.add_argument(
            "--beam-size",
            type=int,
            default=5,
        )
        parser.add_argument(
            "--no-vad",
            action="store_true",
            help="VAD filterを使わない。",
        )

        args = parser.parse_args()

        project_root = Path(__file__).resolve().parent
        data_dir = project_root / "data"
        output_dir = project_root / "output"
        log_dir = project_root / "log"

        data_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)
        log_dir.mkdir(exist_ok=True)

        audio_path = resolve_audio_path(args.audio, data_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = safe_stem(audio_path.stem)
        output_prefix = output_dir / f"{timestamp}_{base}"
        log_path = log_dir / f"{timestamp}_{base}.log"

        logger = setup_logger(log_path)

        compute_type = args.compute_type
        if compute_type is None:
            compute_type = "float16" if args.device == "cuda" else "int8"

        logger.info("project_root: %s", project_root)
        logger.info("audio       : %s", audio_path)
        logger.info("model       : %s", args.model)
        logger.info("device      : %s", args.device)
        logger.info("compute_type: %s", compute_type)
        logger.info("beam_size   : %s", args.beam_size)
        logger.info("vad_filter  : %s", not args.no_vad)
        logger.info("output_base : %s", output_prefix)
        logger.info("log         : %s", log_path)

        logger.info("loading model...")
        model = WhisperModel(
            args.model,
            device=args.device,
            compute_type=compute_type,
        )

        logger.info("transcribing...")
        segments, info = model.transcribe(
            str(audio_path),
            language="ja",
            task="transcribe",
            vad_filter=not args.no_vad,
            beam_size=args.beam_size,
        )

        logger.info(
            "detected language: %s probability=%.4f duration=%.2f sec",
            info.language,
            info.language_probability,
            info.duration,
        )

        write_outputs(
            segments=segments,
            info=info,
            audio_path=audio_path,
            output_prefix=output_prefix,
            model_size=args.model,
            device=args.device,
            compute_type=compute_type,
            logger=logger,
        )

    except Exception:
        if logger is not None:
            logger.exception("fatal error")
        else:
            logging.exception("fatal error before logger setup")
        raise


if __name__ == "__main__":
    main()