"""Atomic, no-overwrite publication for accepted M6 output."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Mapping, Any


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def publish(output_directory: Path, lesson: Mapping[str, Any], audit: Mapping[str, Any]) -> tuple[Path, ...]:
    """Atomically publish one immutable lesson directory or raise."""

    if output_directory.exists():
        raise FileExistsError(f"Refusing to overwrite output directory: {output_directory}")
    output_directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_directory.name}.", dir=output_directory.parent))
    try:
        lesson_path = staging / "lesson.json"
        audit_path = staging / "audit.json"
        _write_json(lesson_path, lesson)
        _write_json(audit_path, audit)
        staging.replace(output_directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return output_directory / "lesson.json", output_directory / "audit.json"


def write_rejection(path: Path, rejection: Mapping[str, Any]) -> Path:
    """Write an auditable rejection without ever overwriting an existing record."""

    if path.exists():
        raise FileExistsError(f"Refusing to overwrite rejection record: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_name(f".{path.name}.tmp")
    if staging.exists():
        raise FileExistsError(f"Incomplete rejection staging file exists: {staging}")
    try:
        _write_json(staging, rejection)
        staging.replace(path)
    except BaseException:
        staging.unlink(missing_ok=True)
        raise
    return path
