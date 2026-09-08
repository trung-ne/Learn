"""Deterministic active M9 full-population selection."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

from .authority import VerifiedM9Authority

JsonObject = dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_selection(authority: VerifiedM9Authority, *, created_at: str | None = None) -> JsonObject:
    """Bind every subject in the complete current verified population."""
    subjects: list[JsonObject] = []
    counts = {"LESSON": 0, "EXERCISE_SET": 0, "AI_PRACTICE_PROMPT": 0}
    for subject in authority.subjects:
        counts[subject.content_type] += 1
        value: JsonObject = {
            "subject_id": subject.subject_id, "content_type": subject.content_type,
            "lesson_id": subject.lesson_id, "artifact_path": subject.artifact_path,
            "artifact_sha256": subject.artifact_sha256, "machine_audit_path": subject.audit_path,
            "machine_audit_sha256": subject.audit_sha256,
        }
        if subject.modality is not None:
            value["modality"] = subject.modality
        subjects.append(value)
    total = len(subjects)
    manifest: JsonObject = {
        "schema_version": "2.0", "record_type": "m9_selection_manifest", "selection_id": "PENDING",
        "selection_policy": "M9_FULL_POPULATION_V2", "selection_scope": "FULL_POPULATION",
        "rationale": "Every lesson, exercise set, and lesson-specific AI-practice prompt in the independently verified current M6, M7, and M8.2 authority is selected in graph and modality order.",
        "upstream": {
            "m5_snapshot_binding": authority.m7.m6.m5.snapshot_binding(),
            "m6_batch_id": authority.m7.m6.batch["batch_id"], "m6_batch_sha256": sha256_json(authority.m7.m6.batch),
            "m7_batch_id": authority.m7.batch["batch_id"], "m7_batch_sha256": sha256_json(authority.m7.batch),
            "m8_2_pilot_id": authority.pilot_manifest["batch_id"], "m8_2_pilot_sha256": sha256_json(authority.pilot_manifest),
            "m8_1_terminal_run_consumed": False,
        },
        "population": {
            "lesson_count": counts["LESSON"],
            "exercise_set_count": counts["EXERCISE_SET"],
            "prompt_count": counts["AI_PRACTICE_PROMPT"],
            "total_subject_count": total,
            "selected_subject_count": total,
            "unreviewed_outside_selection": False,
        },
        "subjects": subjects, "created_at": created_at or _now(), "content_lifecycle_status": "UNREVIEWED",
    }
    manifest["selection_id"] = identity("m9select", manifest, "selection_id")
    validate_instance(manifest, "m9-selection-manifest-v2")
    return manifest
