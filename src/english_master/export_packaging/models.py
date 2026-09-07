"""Single normalized, immutable model consumed by every M11 renderer."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ExportArtifact:
    content_type: str
    content_id: str
    lesson_id: str
    sha256: str
    source_path: str
    content: Mapping[str, Any]


@dataclass(frozen=True)
class ExportModel:
    schema_version: str
    package_version: str
    exported_at: str
    answer_materials: str
    formats: tuple[str, ...]
    artifacts: tuple[ExportArtifact, ...]

    @property
    def lessons(self) -> tuple[ExportArtifact, ...]:
        return tuple(item for item in self.artifacts if item.content_type == "LESSON")

    @property
    def exercise_sets(self) -> tuple[ExportArtifact, ...]:
        return tuple(item for item in self.artifacts if item.content_type == "EXERCISE_SET")

    @property
    def prompts(self) -> tuple[ExportArtifact, ...]:
        return tuple(item for item in self.artifacts if item.content_type == "AI_PRACTICE_PROMPT")


def build_export_model(
    authorization: Mapping[str, Any],
    artifacts: Sequence[tuple[Mapping[str, Any], Mapping[str, Any], Path]],
    *,
    exported_at: str,
) -> ExportModel:
    """Normalize verified records into deterministic renderer input."""

    normalized = tuple(
        sorted(
            (
                ExportArtifact(
                    content_type=str(member["content_type"]),
                    content_id=str(member["content_id"]),
                    lesson_id=str(member["lesson_id"]),
                    sha256=str(member["sha256"]),
                    source_path=str(member["path"]),
                    content=record,
                )
                for member, record, _ in artifacts
            ),
            key=lambda item: (item.lesson_id, item.content_type, item.content_id),
        )
    )
    lesson_ids = {item.content_id for item in normalized if item.content_type == "LESSON"}
    referenced = {item.lesson_id for item in normalized}
    missing = sorted(referenced - lesson_ids)
    if missing:
        raise ValueError("export inventory references missing lessons: " + ", ".join(missing))
    return ExportModel(
        schema_version="1.0",
        package_version=str(authorization["package_version"]),
        exported_at=exported_at,
        answer_materials=str(authorization["answer_materials"]),
        formats=tuple(sorted(str(item) for item in authorization["formats"])),
        artifacts=normalized,
    )
