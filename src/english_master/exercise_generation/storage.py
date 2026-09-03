"""Atomic no-overwrite storage for M7 bundles."""
from pathlib import Path
from typing import Any, Mapping
from english_master.lesson_generation.storage import _publish_bundle

def publish(output_directory: Path, exercise_set: Mapping[str, Any], audit: Mapping[str, Any]) -> tuple[Path, ...]:
    return _publish_bundle(output_directory, {"audit.json": audit, "exercise-set.json": exercise_set})

def publish_rejection(output_directory: Path, rejection: Mapping[str, Any], audit: Mapping[str, Any]) -> tuple[Path, ...]:
    return _publish_bundle(output_directory, {"audit.json": audit, "rejection.json": rejection})
