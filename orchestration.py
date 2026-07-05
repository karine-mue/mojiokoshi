from __future__ import annotations

import os
import signal
import site
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from typing import Mapping

NVIDIA_LIBRARY_SUBDIRS = [
    "nvidia/cuda_runtime/lib",
    "nvidia/cublas/lib",
    "nvidia/cudnn/lib",
]
INTERRUPTED_EXIT_CODE = 130


def resolve_config_path(project_root: Path, config_arg: str | Path) -> Path:
    config_path = Path(config_arg).expanduser()
    if not config_path.is_absolute():
        config_path = project_root / config_path
    return config_path


def read_config(project_root: Path, config_arg: str | Path) -> dict:
    config_path = resolve_config_path(project_root, config_arg)
    with config_path.open("rb") as f:
        return tomllib.load(f)


def get_config_device(project_root: Path, config_arg: str | Path) -> str:
    config = read_config(project_root, config_arg)
    return str(config.get("device", "")).strip()


def prepend_env_path(env: dict[str, str], key: str, paths: list[Path]) -> None:
    existing = env.get(key, "")
    existing_parts = [part for part in existing.split(os.pathsep) if part]
    prepend_parts = [str(path) for path in reversed(paths) if path.is_dir()]

    merged: list[str] = []
    for part in prepend_parts + existing_parts:
        if part not in merged:
            merged.append(part)

    if merged:
        env[key] = os.pathsep.join(merged)


def find_nvidia_library_dirs() -> list[Path]:
    dirs: list[Path] = []
    for site_packages in site.getsitepackages():
        base = Path(site_packages)
        for subdir in NVIDIA_LIBRARY_SUBDIRS:
            candidate = base / subdir
            if candidate.is_dir():
                dirs.append(candidate)
    return dirs


def prepare_runtime_env(device: str) -> dict[str, str]:
    env = os.environ.copy()
    if device != "cuda":
        return env

    prepend_env_path(env, "LD_LIBRARY_PATH", find_nvidia_library_dirs())
    return env


def check_cuda_runtime(*, python_bin: str, env: Mapping[str, str], project_root: Path) -> int:
    completed = subprocess.run(
        [python_bin, "scripts/check_cuda_runtime.py"],
        cwd=project_root,
        env=dict(env),
        shell=False,
    )
    return completed.returncode


def run_transcribe(*, python_bin: str, config_arg: str, env: Mapping[str, str], project_root: Path) -> int:
    completed = subprocess.run(
        [python_bin, "transcribe_m4a.py", "--config", config_arg],
        cwd=project_root,
        env=dict(env),
        shell=False,
    )
    return completed.returncode


def record_failed_run(*, python_bin: str, config_arg: str, exit_code: int, started_epoch: float, failure_stage: str, project_root: Path) -> int:
    completed = subprocess.run(
        [python_bin, "scripts/record_failed_run.py", config_arg, str(exit_code), str(started_epoch), failure_stage],
        cwd=project_root,
        shell=False,
    )
    return completed.returncode


def record_interrupted_run(*, python_bin: str, config_arg: str, started_epoch: float, project_root: Path) -> int:
    print("[WARN] interrupted by user; recording failed run", file=sys.stderr)
    record_failed_run(
        python_bin=python_bin,
        config_arg=config_arg,
        exit_code=INTERRUPTED_EXIT_CODE,
        started_epoch=started_epoch,
        failure_stage="interrupted",
        project_root=project_root,
    )
    return INTERRUPTED_EXIT_CODE


def run_one(config_arg: str, *, python_bin: str | None = None, project_root: Path | None = None) -> int:
    project_root = project_root or Path(__file__).resolve().parent
    python_bin = python_bin or sys.executable
    started_epoch = time.time()

    config_path = resolve_config_path(project_root, config_arg)
    if not config_path.is_file():
        print(f"[ERROR] config not found: {config_arg}", file=sys.stderr)
        return 1

    device = get_config_device(project_root, config_arg)
    env = prepare_runtime_env(device)

    if device == "cuda":
        print("[INFO] device=cuda; loading CUDA environment")
        try:
            status = check_cuda_runtime(
                python_bin=python_bin,
                env=env,
                project_root=project_root,
            )
        except KeyboardInterrupt:
            return record_interrupted_run(
                python_bin=python_bin,
                config_arg=config_arg,
                started_epoch=started_epoch,
                project_root=project_root,
            )
        if status != 0:
            record_failed_run(
                python_bin=python_bin,
                config_arg=config_arg,
                exit_code=status,
                started_epoch=started_epoch,
                failure_stage="cuda_env",
                project_root=project_root,
            )
            return status
    elif device == "cpu":
        print("[INFO] device=cpu; skipping CUDA environment")
    else:
        print(f"[WARN] device is not set to cpu/cuda in {config_arg}; running without CUDA environment")

    try:
        status = run_transcribe(python_bin=python_bin, config_arg=config_arg, env=env, project_root=project_root)
    except KeyboardInterrupt:
        return record_interrupted_run(
            python_bin=python_bin,
            config_arg=config_arg,
            started_epoch=started_epoch,
            project_root=project_root,
        )

    if status in {INTERRUPTED_EXIT_CODE, -signal.SIGINT}:
        return record_interrupted_run(
            python_bin=python_bin,
            config_arg=config_arg,
            started_epoch=started_epoch,
            project_root=project_root,
        )

    if status != 0:
        record_failed_run(
            python_bin=python_bin,
            config_arg=config_arg,
            exit_code=status,
            started_epoch=started_epoch,
            failure_stage="transcribe",
            project_root=project_root,
        )
    return status
