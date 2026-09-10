"""Local-path, hashing, loading, and immutable-storage helpers for M13."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path, PurePath, PurePosixPath
from typing import Any, Mapping

from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import SchemaValidationError, load_document, validate_instance

from .models import JsonObject, TranscriptionError


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_bytes(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def require_regular_file(path: Path, label: str) -> Path:
    if "://" in str(path):
        raise TranscriptionError(f"{label} must be a local path, not a URL")
    absolute = path.absolute()
    if is_link(path) or not path.is_file():
        raise TranscriptionError(f"{label} must be a regular local file: {path}")
    if any(is_link(parent) for parent in absolute.parents if parent.exists()):
        raise TranscriptionError(f"{label} path has a link-like ancestor")
    return absolute


def require_real_directory(path: Path, label: str) -> Path:
    if "://" in str(path):
        raise TranscriptionError(f"{label} must be a local path, not a URL")
    absolute = path.absolute()
    if is_link(path) or not path.is_dir():
        raise TranscriptionError(f"{label} must be a real local directory: {path}")
    if any(is_link(parent) for parent in absolute.parents if parent.exists()):
        raise TranscriptionError(f"{label} path has a link-like ancestor")
    return absolute


def load_record(path: Path, schema: str) -> JsonObject:
    require_regular_file(path, schema)
    try:
        value = load_document(path)
        validate_instance(value, schema)
    except (OSError, UnicodeError, json.JSONDecodeError, SchemaValidationError, ValueError) as error:
        raise TranscriptionError(f"invalid {schema}: {error}") from error
    return value


def local_path_matches(declared: str, actual: Path, label: str) -> None:
    declared_path = PurePosixPath(declared.replace("\\", "/"))
    actual_path = PurePosixPath(actual.absolute().as_posix())
    if (
        declared_path.is_absolute()
        or not declared_path.parts
        or ".." in declared_path.parts
        or "://" in declared
        or len(actual_path.parts) < len(declared_path.parts)
        or tuple(actual_path.parts[-len(declared_path.parts):]) != declared_path.parts
    ):
        raise TranscriptionError(f"{label} differs from the pinned local path")


def safe_output_root(data_root: Path) -> Path:
    if "://" in str(data_root):
        raise TranscriptionError("data root must be local")
    root = data_root.absolute()
    lowered = {part.lower() for part in root.parts}
    if lowered.intersection({"approved", "curriculum", "exports", "media"}):
        raise TranscriptionError("transcription data root cannot be inside approved, curriculum, export, or media storage")
    if any(is_link(parent) for parent in (root, *root.parents) if parent.exists()):
        raise TranscriptionError("transcription data root has a link-like ancestor")
    return root / "transcription" / "runs"


def inventory(stage: Path, paths: list[tuple[str, str]]) -> list[JsonObject]:
    result: list[JsonObject] = []
    for relative, role in sorted(paths):
        safe = PurePosixPath(relative)
        if safe.is_absolute() or ".." in safe.parts or "\\" in relative:
            raise TranscriptionError("unsafe inventory path")
        path = stage.joinpath(*safe.parts)
        result.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path), "role": role})
    return result


def atomic_publish(stage_parent: Path, destination: Path, populate: Any) -> None:
    if destination.exists() or is_link(destination):
        raise FileExistsError(f"immutable transcription run already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if any(is_link(parent) for parent in destination.parents if parent.exists()):
        raise TranscriptionError("transcription destination has a link-like ancestor")
    stage = stage_parent / f".transcription-staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False)
        populate(stage)
        _fsync_directory(stage)
        _rename_directory_noreplace(stage, destination)
        _fsync_directory(destination.parent)
    except BaseException:
        if stage.exists() or is_link(stage):
            shutil.rmtree(stage, ignore_errors=True)
        raise


def write_once(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or is_link(path):
        raise FileExistsError(f"refusing to overwrite immutable output: {path}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
