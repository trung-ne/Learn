"""Independent authority reconstruction for the complete active M9 population."""
from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from english_master.ai_practice.authority import VerifiedM6PracticeAuthority
from english_master.ai_practice.verification import verify_pilot
from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.canonical import sha256_json
from english_master.qa_engine.authority import VerifiedM7QaAuthority

JsonObject = dict[str, Any]
MODALITIES = ("LISTENING", "SPEAKING", "PRONUNCIATION", "WRITING")
EXPECTED_LESSON_COUNT = 10
EXPECTED_EXERCISE_SET_COUNT = 10
EXPECTED_PROMPT_COUNT = 40
EXPECTED_SUBJECT_COUNT = 60


@dataclass(frozen=True)
class ReviewSubject:
    subject_id: str
    content_type: str
    lesson_id: str
    modality: str | None
    artifact_path: str
    artifact: Mapping[str, Any]
    audit_path: str
    audit: Mapping[str, Any]

    @property
    def artifact_sha256(self) -> str:
        return sha256_json(self.artifact)

    @property
    def audit_sha256(self) -> str:
        return sha256_json(self.audit)


@dataclass(frozen=True)
class VerifiedM9Authority:
    """Freshly reconstructed M5–M8.2 authority for M9 overlays only."""

    repository_root: Path
    m7: VerifiedM7QaAuthority
    practice: VerifiedM6PracticeAuthority
    m7_batch_path: Path
    pilot_directory: Path
    pilot_manifest: Mapping[str, Any]
    subjects: tuple[ReviewSubject, ...]

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
        pilot_directory: Path,
    ) -> "VerifiedM9Authority":
        m7 = VerifiedM7QaAuthority.from_files(
            structure_path=structure_path,
            snapshot_directory=snapshot_directory,
            source_registry_path=source_registry_path,
            m6_batch_path=m6_batch_path,
            m6_root=m6_root,
            exercise_root=exercise_root,
            m7_batch_path=m7_batch_path,
        )
        practice = VerifiedM6PracticeAuthority.from_files(
            structure_path=structure_path,
            snapshot_directory=snapshot_directory,
            source_registry_path=source_registry_path,
            m6_batch_path=m6_batch_path,
            m6_root=m6_root,
        )
        if sha256_json(m7.m6.batch) != sha256_json(practice.m6.batch):
            raise ValueError("M9 M6 authorities disagree")
        pilot = pilot_directory.resolve()
        verify_pilot(pilot, practice)
        manifest = load_strict_document(pilot / "batch-manifest.json")
        repository_root = structure_path.resolve().parent.parent
        subjects: list[ReviewSubject] = []
        from english_master.lesson_generation.canonical import identity

        def relative_path(path: Path, *, label: str) -> str:
            resolved = path.resolve()
            try:
                return resolved.relative_to(repository_root).as_posix()
            except ValueError as error:
                raise ValueError(f"M9 {label} path is outside the repository root: {resolved}") from error

        def add(
            content_type: str,
            lesson_id: str,
            artifact: Mapping[str, Any],
            audit: Mapping[str, Any],
            *,
            artifact_file: Path,
            audit_file: Path,
            modality: str | None = None,
        ) -> None:
            descriptor: JsonObject = {
                "content_type": content_type,
                "lesson_id": lesson_id,
                "modality": modality,
                "artifact_sha256": sha256_json(artifact),
                "machine_audit_sha256": sha256_json(audit),
            }
            subject_id = identity("m9sub", descriptor, "subject_id")
            subjects.append(ReviewSubject(
                subject_id=subject_id,
                content_type=content_type,
                lesson_id=lesson_id,
                modality=modality,
                artifact_path=relative_path(artifact_file, label="artifact"),
                artifact=copy.deepcopy(dict(artifact)),
                audit_path=relative_path(audit_file, label="machine audit"),
                audit=copy.deepcopy(dict(audit)),
            ))

        lesson_ids = tuple(practice.lesson_ids)
        if len(lesson_ids) != EXPECTED_LESSON_COUNT or len(set(lesson_ids)) != EXPECTED_LESSON_COUNT:
            raise ValueError("M9 requires exactly ten distinct graph-ordered lessons")
        if set(m7.entries) != set(lesson_ids):
            raise ValueError("M9 M7 exercise population does not exactly match the M6 lesson population")
        for lesson_id in lesson_ids:
            lesson_binding = m7.m6.binding(lesson_id)
            lesson_file = m7.m6.candidate_root / lesson_binding["lesson_path"]
            lesson_audit_file = m7.m6.candidate_root / lesson_binding["audit_path"]
            add(
                "LESSON", lesson_id, m7.m6.lesson(lesson_id), m7.m6.audits[lesson_id],
                artifact_file=lesson_file, audit_file=lesson_audit_file,
            )
            exercise_set, exercise_audit, _ = m7.artifacts(lesson_id)
            exercise_binding = m7.entries[lesson_id]
            exercise_bundle = m7.exercise_root / exercise_binding["bundle_path"]
            add(
                "EXERCISE_SET", lesson_id, exercise_set, exercise_audit,
                artifact_file=exercise_bundle / "exercise-set.json", audit_file=exercise_bundle / "audit.json",
            )
            for modality in MODALITIES:
                name = f"{lesson_id.lower()}--{modality.lower()}.json"
                prompt_file = pilot / "prompts" / name
                prompt_audit_file = pilot / "audits" / name
                prompt = load_strict_document(prompt_file)
                prompt_audit = load_strict_document(prompt_audit_file)
                if prompt.get("lesson_id") != lesson_id or prompt.get("modality") != modality:
                    raise ValueError("M9 pilot subject identity drift")
                add(
                    "AI_PRACTICE_PROMPT", lesson_id, prompt, prompt_audit,
                    artifact_file=prompt_file, audit_file=prompt_audit_file, modality=modality,
                )
        counts = {
            "LESSON": sum(item.content_type == "LESSON" for item in subjects),
            "EXERCISE_SET": sum(item.content_type == "EXERCISE_SET" for item in subjects),
            "AI_PRACTICE_PROMPT": sum(item.content_type == "AI_PRACTICE_PROMPT" for item in subjects),
        }
        if counts != {
            "LESSON": EXPECTED_LESSON_COUNT,
            "EXERCISE_SET": EXPECTED_EXERCISE_SET_COUNT,
            "AI_PRACTICE_PROMPT": EXPECTED_PROMPT_COUNT,
        } or len(subjects) != EXPECTED_SUBJECT_COUNT or len({item.subject_id for item in subjects}) != EXPECTED_SUBJECT_COUNT:
            raise ValueError("M9 requires the complete distinct 10-lesson, 10-exercise-set, 40-prompt population")
        return cls(
            repository_root=repository_root,
            m7=m7,
            practice=practice,
            m7_batch_path=m7_batch_path.resolve(),
            pilot_directory=pilot,
            pilot_manifest=copy.deepcopy(manifest),
            subjects=tuple(subjects),
        )

    def reload(self) -> "VerifiedM9Authority":
        return type(self).from_files(
            structure_path=self.practice.structure_path,
            snapshot_directory=self.practice.snapshot_directory,
            source_registry_path=self.practice.source_registry_path,
            m6_batch_path=self.practice.m6_batch_path,
            m6_root=self.practice.m6_root,
            exercise_root=self.m7.exercise_root,
            m7_batch_path=self.m7_batch_path,
            pilot_directory=self.pilot_directory,
        )
