"""Atomic no-overwrite publication for M9 development overlays."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Mapping

from english_master.lesson_generation.canonical import sha256_json
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace
from english_master.schema_validation import validate_instance

from .authority import VerifiedM9Authority
from .development import build_development_batch
from .review import ai_review_schema_for_selection
from .verification import _linklike, verify_development_batch


def _write(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def publish_development_batch(
    directory: Path,
    authority: VerifiedM9Authority,
    selection: Mapping[str, object],
    reports: Mapping[str, Mapping[str, object]],
    reviews: Mapping[tuple[str, str], Mapping[str, object]],
    *,
    created_at: str,
) -> Path:
    """Stage, independently reverify, then atomically publish an M9 overlay."""
    review_schema, _ = ai_review_schema_for_selection(selection)
    for review in reviews.values():
        validate_instance(dict(review), review_schema)
    destination = directory.absolute()
    for ancestor in (destination, *destination.parents):
        if _linklike(ancestor):
            raise ValueError(f"M9 publication destination has a link-like ancestor: {ancestor}")
        if ancestor != destination and (ancestor / "development-batch.json").is_file():
            raise ValueError(f"M9 publication destination is nested in immutable evidence: {ancestor}")
    if destination.exists():
        raise FileExistsError(f"immutable M9 development directory already exists: {destination}")
    stage = destination.parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False)
        _write(stage / "selection.json", selection)
        for subject_id, report in reports.items():
            token = subject_id.split("_", 1)[1]
            _write(stage / "machine" / f"{token}.json", report)
        for (subject_id, role), review in reviews.items():
            token = subject_id.split("_", 1)[1]
            _write(stage / "reviews" / f"{token}--{role.lower()}.json", review)
        inventory = [
            {"path": path.relative_to(stage).as_posix(), "sha256": sha256_json(json.loads(path.read_text(encoding="utf-8")))}
            for path in sorted(stage.rglob("*.json"))
        ]
        batch = build_development_batch(authority, selection, reports, reviews, created_at=created_at, inventory=inventory)
        _write(stage / "development-batch.json", batch)
        verify_development_batch(stage, authority.reload())
        for child in (stage / "machine", stage / "reviews", stage):
            _fsync_directory(child)
        _rename_directory_noreplace(stage, destination)
        try:
            _fsync_directory(destination.parent)
        except OSError:
            pass
        return destination
    except BaseException:
        if stage.exists() or stage.is_symlink():
            shutil.rmtree(stage, ignore_errors=True)
        raise
