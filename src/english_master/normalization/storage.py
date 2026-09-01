"""Failure-safe persistence helpers for normalization runs."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class NormalizationStorageError(RuntimeError):
    """Raised when an output cannot be safely published."""


def pretty_json_bytes(value: Any) -> bytes:
    """Serialize human-readable JSON deterministically with one final LF."""

    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def write_once(path: Path, content: bytes) -> bool:
    """Atomically create a file, allowing only byte-identical replay."""

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_file() and path.read_bytes() == content:
            return False
        raise NormalizationStorageError(f"Refusing to overwrite different existing output: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_file() and path.read_bytes() == content:
                return False
            raise NormalizationStorageError(f"Concurrent output conflict: {path}") from None
    finally:
        temporary.unlink(missing_ok=True)
    return True
