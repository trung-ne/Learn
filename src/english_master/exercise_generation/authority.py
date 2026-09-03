"""Independently verified M6 development authority for M7."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.authority import VerifiedM5DevelopmentAuthority
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.lesson_generation.review import m7_eligibility_issues

from .models import ExerciseIssue, JsonObject


@dataclass(frozen=True)
class VerifiedM6DevelopmentAuthority:
    m5: VerifiedM5DevelopmentAuthority
    batch: Mapping[str, Any]
    candidate_root: Path
    lessons: Mapping[str, Mapping[str, Any]]
    audits: Mapping[str, Mapping[str, Any]]
    bindings: Mapping[str, Mapping[str, Any]]

    @classmethod
    def from_files(cls, structure_path: Path, snapshot_directory: Path, source_registry_path: Path, batch_path: Path, candidate_root: Path, *, graph_path: Path | None = None, coverage_path: Path | None = None, taxonomy_path: Path | None = None, observed_at: str | None = None) -> "VerifiedM6DevelopmentAuthority":
        m5 = VerifiedM5DevelopmentAuthority.from_files(structure_path, snapshot_directory, source_registry_path, graph_path=graph_path, coverage_path=coverage_path, taxonomy_path=taxonomy_path, observed_at=observed_at)
        batch = load_strict_document(batch_path.resolve())
        root = candidate_root.resolve()
        issues = m7_eligibility_issues(batch, m5, root)
        if issues:
            raise ValueError("; ".join(f"{issue.code}: {issue.message}" for issue in issues))
        if batch.get("approval_tier") != "DEVELOPMENT_APPROVED":
            raise ValueError("M6 batch is not DEVELOPMENT_APPROVED")
        lessons: dict[str, Mapping[str, Any]] = {}
        audits: dict[str, Mapping[str, Any]] = {}
        bindings: dict[str, Mapping[str, Any]] = {}
        for entry in batch["lessons"]:
            lesson_path = (root / entry["lesson_path"]).resolve()
            audit_path = (root / entry["audit_path"]).resolve()
            if root not in lesson_path.parents or root not in audit_path.parents:
                raise ValueError("M6 artifact path escapes candidate root")
            lessons[entry["lesson_id"]] = load_strict_document(lesson_path)
            audits[entry["lesson_id"]] = load_strict_document(audit_path)
            bindings[entry["lesson_id"]] = copy.deepcopy(entry)
        return cls(m5=m5, batch=copy.deepcopy(batch), candidate_root=root, lessons=lessons, audits=audits, bindings=bindings)

    def authorization(self, lesson_ids: tuple[str, ...] | list[str] | None = None) -> JsonObject:
        selected = tuple(lesson_ids) if lesson_ids is not None else tuple(self.bindings)
        if not selected or any(identifier not in self.bindings for identifier in selected):
            raise ValueError("authorization selects an unknown M6 development lesson")
        value: JsonObject = {"schema_version":"1.0","record_type":"exercise_generation_authorization","authorization_id":"PENDING","m6_batch_id":self.batch["batch_id"],"m6_batch_sha256":sha256_json(self.batch),"snapshot_binding":self.m5.snapshot_binding(),"lesson_bindings":[{key:self.bindings[identifier][key] for key in ("lesson_id","lesson_sha256","audit_sha256","lesson_path","audit_path")} for identifier in selected],"policy":{"external_stimuli":"FORBIDDEN","external_media":"FORBIDDEN","authored_inline_text":"REQUIRED","allow_m8_artifacts":False}}
        value["authorization_id"] = identity("m7auth", value, "authorization_id")
        return value

    def lesson(self, lesson_id: str) -> Mapping[str, Any]:
        try:
            return copy.deepcopy(dict(self.lessons[lesson_id]))
        except KeyError as error:
            raise ValueError(f"unknown authorized lesson {lesson_id!r}") from error

    def binding(self, lesson_id: str) -> JsonObject:
        return copy.deepcopy(dict(self.bindings[lesson_id]))
