"""Fail-closed authority loading for QA-engine candidates."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_document
from english_master.exercise_generation.authority import VerifiedM6DevelopmentAuthority
from english_master.exercise_generation.review import validate_development_batch
from english_master.lesson_generation.canonical import sha256_json

from .models import JsonObject


@dataclass(frozen=True)
class VerifiedM7QaAuthority:
    m6: VerifiedM6DevelopmentAuthority
    batch: Mapping[str, Any]
    exercise_root: Path
    entries: Mapping[str, Mapping[str, Any]]

    @classmethod
    def from_files(
        cls,
        *,
        structure_path: Path,
        snapshot_directory: Path,
        source_registry_path: Path,
        m6_batch_path: Path,
        m6_root: Path,
        exercise_root: Path,
        m7_batch_path: Path,
    ) -> "VerifiedM7QaAuthority":
        m6 = VerifiedM6DevelopmentAuthority.from_files(
            structure_path, snapshot_directory, source_registry_path, m6_batch_path, m6_root,
        )
        root = exercise_root.resolve()
        batch = load_strict_document(m7_batch_path.resolve())
        issues = validate_development_batch(batch, m6, root)
        if issues:
            raise ValueError("; ".join(f"{issue.code}: {issue.message}" for issue in issues))
        if batch.get("approval_tier") != "DEVELOPMENT_APPROVED":
            raise ValueError("M7 batch is not DEVELOPMENT_APPROVED")
        entries = {entry["lesson_id"]: copy.deepcopy(entry) for entry in batch["exercise_sets"]}
        return cls(m6=m6, batch=copy.deepcopy(batch), exercise_root=root, entries=entries)

    def artifacts(self, lesson_id: str) -> tuple[JsonObject, JsonObject, tuple[JsonObject, ...]]:
        try:
            entry = self.entries[lesson_id]
        except KeyError as error:
            raise ValueError(f"lesson is not in the verified M7 batch: {lesson_id}") from error
        bundle = (self.exercise_root / entry["bundle_path"]).resolve()
        if self.exercise_root not in bundle.parents:
            raise ValueError("M7 bundle path escapes exercise root")
        exercise_set = load_strict_document(bundle / "exercise-set.json")
        audit = load_strict_document(bundle / "audit.json")
        if sha256_json(exercise_set) != entry["exercise_set_sha256"] or sha256_json(audit) != entry["audit_sha256"]:
            raise ValueError("M7 artifact hash drift")
        reviews: list[JsonObject] = []
        for reference in entry["ai_reviews"]:
            path = (self.exercise_root / reference["path"]).resolve()
            if self.exercise_root not in path.parents:
                raise ValueError("M7 review path escapes exercise root")
            review = load_strict_document(path)
            if sha256_json(review) != reference["sha256"]:
                raise ValueError("M7 review hash drift")
            reviews.append(review)
        return copy.deepcopy(exercise_set), copy.deepcopy(audit), tuple(copy.deepcopy(item) for item in reviews)

    def authority_available_at(self) -> str:
        """Return the latest batch-level authority timestamp for M8 requests."""
        from .time import orderable_timestamp

        value = self.batch.get("created_at")
        orderable_timestamp(value)
        return str(value)

    def request(self, lesson_id: str, *, created_at: str, maximum_attempts: int = 3) -> JsonObject:
        exercise_set, audit, _ = self.artifacts(lesson_id)
        value: JsonObject = {
            "schema_version": "1.0", "record_type": "qa_engine_request", "engine_run_id": "PENDING",
            "m7_batch_id": self.batch["batch_id"], "exercise_set_id": exercise_set["exercise_set_id"],
            "exercise_set_sha256": sha256_json(exercise_set), "audit_sha256": sha256_json(audit),
            "lesson_id": lesson_id, "maximum_attempts": maximum_attempts,
            "stages": ["SCHEMA", "ANSWER", "CEFR", "PREREQUISITE", "DUPLICATE", "LANGUAGE"],
            "policy_version": "QA_ENGINE_DEVELOPMENT_v1", "created_at": created_at,
        }
        from english_master.lesson_generation.canonical import identity
        value["engine_run_id"] = identity("qaerun", value, "engine_run_id")
        return value
