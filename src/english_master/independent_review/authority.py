"""Independent authority reconstruction for the bounded M9 review sample."""
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
SAMPLE_LESSONS = ("A1-U01-L01", "A2-U03-L01", "B1-U05-L01")
MODALITIES = ("LISTENING", "SPEAKING", "PRONUNCIATION", "WRITING")


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
        subjects: list[ReviewSubject] = []
        from english_master.lesson_generation.canonical import identity

        def add(content_type: str, lesson_id: str, artifact: Mapping[str, Any], audit: Mapping[str, Any], *, modality: str | None = None) -> None:
            descriptor: JsonObject = {
                "content_type": content_type,
                "lesson_id": lesson_id,
                "modality": modality,
                "artifact_sha256": sha256_json(artifact),
                "machine_audit_sha256": sha256_json(audit),
            }
            subject_id = identity("m9sub", descriptor, "subject_id")
            suffix = f":{modality}" if modality else ""
            subjects.append(ReviewSubject(
                subject_id=subject_id,
                content_type=content_type,
                lesson_id=lesson_id,
                modality=modality,
                artifact_path=f"{content_type}:{lesson_id}{suffix}",
                artifact=copy.deepcopy(dict(artifact)),
                audit_path=f"MACHINE_AUDIT:{content_type}:{lesson_id}{suffix}",
                audit=copy.deepcopy(dict(audit)),
            ))

        for lesson_id in SAMPLE_LESSONS:
            if lesson_id not in m7.entries or lesson_id not in practice.lesson_ids:
                raise ValueError(f"M9 sample lesson is absent from verified authority: {lesson_id}")
            lesson = m7.m6.lesson(lesson_id)
            lesson_audit = copy.deepcopy(dict(m7.m6.audits[lesson_id]))
            add("LESSON", lesson_id, lesson, lesson_audit)
            exercise_set, exercise_audit, _ = m7.artifacts(lesson_id)
            add("EXERCISE_SET", lesson_id, exercise_set, exercise_audit)
            for modality in MODALITIES:
                name = f"{lesson_id.lower()}--{modality.lower()}.json"
                prompt = load_strict_document(pilot / "prompts" / name)
                prompt_audit = load_strict_document(pilot / "audits" / name)
                if prompt.get("lesson_id") != lesson_id or prompt.get("modality") != modality:
                    raise ValueError("M9 pilot subject identity drift")
                add("AI_PRACTICE_PROMPT", lesson_id, prompt, prompt_audit, modality=modality)
        if len(subjects) != 18 or len({item.subject_id for item in subjects}) != 18:
            raise ValueError("M9 requires exactly eighteen distinct selected subjects")
        return cls(m7=m7, practice=practice, m7_batch_path=m7_batch_path.resolve(), pilot_directory=pilot, pilot_manifest=copy.deepcopy(manifest), subjects=tuple(subjects))

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
