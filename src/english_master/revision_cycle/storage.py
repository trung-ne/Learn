"""Atomic no-overwrite storage for M10 finding batches."""
from __future__ import annotations

import json
import os
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from english_master.independent_review.authority import ReviewSubject
from english_master.independent_review.storage import _write
from english_master.lesson_generation.canonical import sha256_json
from english_master.lesson_generation.storage import _fsync_directory, _rename_directory_noreplace

from .verification import build_finding_batch, verify_finding_batch


def publish_finding_batch(
    directory: Path,
    *,
    selection: Mapping[str, Any],
    subjects: Mapping[str, ReviewSubject],
    machine_reports: Mapping[str, Mapping[str, Any]],
    inputs: Mapping[str, Mapping[str, Any]],
    imported_at: str,
) -> Path:
    """Stage, reverify, then atomically publish non-promotable M10 inputs."""
    destination = directory.absolute()
    if destination.exists():
        raise FileExistsError(f"immutable M10 finding directory already exists: {destination}")
    for ancestor in (destination, *destination.parents):
        if ancestor.is_symlink():
            raise ValueError(f"M10 finding destination has a link-like ancestor: {ancestor}")
        if ancestor != destination and (ancestor / "finding-batch.json").is_file():
            raise ValueError(f"M10 finding destination is nested in immutable evidence: {ancestor}")
    stage = destination.parent / f".{destination.name}.staging-{uuid.uuid4().hex}"
    try:
        stage.mkdir(parents=True, exist_ok=False)
        _write(stage / "selection.json", selection)
        for subject_id, report in sorted(machine_reports.items()):
            _write(stage / "machine" / f"{subject_id.split('_', 1)[-1][:16]}.json", report)
        for input_id, input_value in sorted(inputs.items()):
            _write(stage / "inputs" / f"{input_id.split('_', 1)[-1][:16]}.json", input_value)
        inventory = [
            {"path": path.relative_to(stage).as_posix(), "sha256": sha256_json(json.loads(path.read_text(encoding="utf-8")))}
            for path in sorted(stage.rglob("*.json"))
        ]
        batch = build_finding_batch(selection=selection, subjects=subjects, machine_reports=machine_reports, inputs=inputs, imported_at=imported_at, inventory=inventory)
        _write(stage / "finding-batch.json", batch)
        verify_finding_batch(stage, selection=selection, subjects=subjects)
        for child in (stage / "machine", stage / "inputs", stage):
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
