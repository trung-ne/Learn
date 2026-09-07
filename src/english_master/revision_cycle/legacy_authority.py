"""Read-only M6/M7/M8.2 predecessor revalidation for M10 authority binding."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .models import RevisionIssue


@dataclass(frozen=True)
class LegacyAuthorityPaths:
    structure: Path
    m5_snapshot: Path
    source_registry: Path
    m6_batch: Path
    m6_root: Path
    exercise_root: Path
    m7_batch: Path
    m8_pilot: Path


def revalidate_predecessor(request: Mapping[str, Any], paths: LegacyAuthorityPaths) -> tuple[RevisionIssue, ...]:
    """Reconstruct legacy authority without writing or relabelling old artifacts."""
    try:
        from english_master.lesson_generation.authority import VerifiedM5DevelopmentAuthority
        m5 = VerifiedM5DevelopmentAuthority.from_files(paths.structure, paths.m5_snapshot, paths.source_registry)
        target = request.get("target_milestone")
        if target == "M6":
            return ()
        from english_master.exercise_generation.authority import VerifiedM6DevelopmentAuthority
        m6 = VerifiedM6DevelopmentAuthority.from_files(paths.structure, paths.m5_snapshot, paths.source_registry, paths.m6_batch, paths.m6_root)
        if target == "M7":
            from english_master.curriculum_review.loading import load_strict_document
            from english_master.exercise_generation.review import validate_development_batch
            report = load_strict_document(paths.m7_batch)
            if not isinstance(report, dict):
                raise ValueError("M7 development batch must be an object")
            issues = validate_development_batch(report, m6, paths.exercise_root)
            if issues:
                raise ValueError("M7 development batch validation failed: " + "; ".join(issue.code for issue in issues))
            return ()
        if target == "M8_2":
            from english_master.ai_practice.authority import VerifiedM6PracticeAuthority
            from english_master.ai_practice.verification import verify_pilot
            practice = VerifiedM6PracticeAuthority.from_files(structure_path=paths.structure, snapshot_directory=paths.m5_snapshot, source_registry_path=paths.source_registry, m6_batch_path=paths.m6_batch, m6_root=paths.m6_root)
            verify_pilot(paths.m8_pilot, practice)
            if not m5 or not m6 or not practice:
                raise ValueError("legacy authority reconstruction returned no authority")
            return ()
        return (RevisionIssue("REQUEST_BINDING", "/target_milestone", "Unsupported M10 target milestone."),)
    except (OSError, ValueError, KeyError) as error:
        return (RevisionIssue("AUTHORITY_DRIFT", "/authority", str(error), "CRITICAL"),)
