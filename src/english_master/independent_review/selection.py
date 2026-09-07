"""Deterministic M9 representative-sample selection."""
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
    """Bind the full current population and the fixed three-band sample."""
    subjects: list[JsonObject] = []
    for subject in authority.subjects:
        value: JsonObject = {
            "subject_id": subject.subject_id, "content_type": subject.content_type,
            "lesson_id": subject.lesson_id, "artifact_path": subject.artifact_path,
            "artifact_sha256": subject.artifact_sha256, "machine_audit_path": subject.audit_path,
            "machine_audit_sha256": subject.audit_sha256,
        }
        if subject.modality is not None:
            value["modality"] = subject.modality
        subjects.append(value)
    manifest: JsonObject = {
        "schema_version": "1.0", "record_type": "m9_selection_manifest", "selection_id": "PENDING",
        "selection_policy": "M9_REPRESENTATIVE_STRATIFIED_V1", "selection_scope": "REPRESENTATIVE_SAMPLE",
        "rationale": "Three graph-ordered lesson clusters cover the available A1, A2, and B1 bands; each cluster includes its lesson, exercise set, and all four M8.2 modalities.",
        "upstream": {
            "m5_snapshot_binding": authority.m7.m6.m5.snapshot_binding(),
            "m6_batch_id": authority.m7.m6.batch["batch_id"], "m6_batch_sha256": sha256_json(authority.m7.m6.batch),
            "m7_batch_id": authority.m7.batch["batch_id"], "m7_batch_sha256": sha256_json(authority.m7.batch),
            "m8_2_pilot_id": authority.pilot_manifest["batch_id"], "m8_2_pilot_sha256": sha256_json(authority.pilot_manifest),
            "m8_1_terminal_run_consumed": False,
        },
        "population": {"lesson_count": 10, "exercise_set_count": 10, "prompt_count": 40, "total_subject_count": 60, "selected_subject_count": 18, "unreviewed_outside_sample": True},
        "subjects": subjects, "created_at": created_at or _now(), "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False, "release_approved": False, "provider_authenticated": False,
    }
    manifest["selection_id"] = identity("m9select", manifest, "selection_id")
    validate_instance(manifest, "m9-selection-manifest")
    return manifest
