"""Dereference and validate immutable M10 successor evidence."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

from english_master.ai_practice.authority import VerifiedM6PracticeAuthority
from english_master.ai_practice.verification import verify_pilot
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import validate_instance

from .models import RevisionIssue

JsonObject = dict[str, Any]


def _safe_path(repository_root: Path, declared_path: object, *, directory: bool = False) -> Path:
    """Resolve one repository-relative evidence path without following links."""
    if not isinstance(declared_path, str) or not declared_path or "\\" in declared_path:
        raise ValueError("M10 successor evidence path must be a non-empty POSIX relative path")
    relative = PurePosixPath(declared_path)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise ValueError("M10 successor evidence path escapes its repository root")
    root = repository_root.resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise ValueError("M10 repository root must be a real directory")
    candidate = root.joinpath(*relative.parts)
    for item in (candidate, *candidate.parents):
        if item.is_symlink():
            raise ValueError("M10 successor evidence contains a link-like path")
        if item == root:
            break
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError("M10 successor evidence path escapes its repository root") from error
    if directory:
        if not resolved.is_dir():
            raise ValueError("M10 successor pilot evidence must be a directory")
    elif not resolved.is_file():
        raise ValueError("M10 successor evidence must be a regular file")
    return resolved


def _document(repository_root: Path, path: object, expected_hash: object) -> JsonObject:
    from english_master.curriculum_review.loading import load_strict_document

    if not isinstance(expected_hash, str):
        raise ValueError("M10 successor evidence hash must be a string")
    value = load_strict_document(_safe_path(repository_root, path))
    if not isinstance(value, dict) or sha256_json(value) != expected_hash:
        raise ValueError("M10 successor evidence hash or document shape drift")
    return value


def _m8_authority(repository_root: Path) -> VerifiedM6PracticeAuthority:
    return VerifiedM6PracticeAuthority.from_files(
        structure_path=repository_root / "curriculum/structure.json",
        snapshot_directory=repository_root / "data/reviews/m5/development-20260903-062008",
        source_registry_path=repository_root / "sources/registry.yaml",
        m6_batch_path=repository_root / "data/generated/m6/development-batches/20260903-v6/development-batch.json",
        m6_root=repository_root / "data/generated/m6/development-candidates/20260903-v6-selected",
    )


def _expected_kinds(target_milestone: str) -> set[str]:
    return {
        "M6": {"M6_SUCCESSOR_BATCH", "M7_SUCCESSOR_BATCH", "M8_2_SUCCESSOR_PILOT"},
        "M7": {"M7_SUCCESSOR_BATCH"},
        "M8_2": {"M8_2_SUCCESSOR_PILOT"},
    }[target_milestone]


def verify_successor_evidence(
    *, request: Mapping[str, Any], successor: Mapping[str, Any], repository_root: Path
) -> tuple[RevisionIssue, ...]:
    """Prove supplied M7/M8.2 records are the immutable files they cite."""
    evidence = successor.get("successor_evidence")
    if not isinstance(evidence, list):
        return (RevisionIssue("SUCCESSOR_SCHEMA", "/successor_evidence", "Missing successor evidence."),)
    target = str(request.get("target_milestone"))
    if {item.get("kind") for item in evidence if isinstance(item, Mapping)} != _expected_kinds(target):
        return (RevisionIssue("SUCCESSOR_SCHEMA", "/successor_evidence", "Successor evidence kinds do not exactly cover the target rebuild boundary."),)
    if len(evidence) != len(_expected_kinds(target)):
        return (RevisionIssue("SUCCESSOR_SCHEMA", "/successor_evidence", "Successor evidence inventory is not closed."),)
    issues: list[RevisionIssue] = []
    try:
        for item in evidence:
            if not isinstance(item, Mapping):
                raise ValueError("M10 successor evidence item must be an object")
            kind = item["kind"]
            if kind == "M7_SUCCESSOR_BATCH":
                required = {"kind", "exercise_set_path", "exercise_set_sha256", "audit_path", "audit_sha256"}
                if set(item) != required:
                    raise ValueError("M7 successor evidence fields are not closed")
                artifact = _document(repository_root, item["exercise_set_path"], item["exercise_set_sha256"])
                audit = _document(repository_root, item["audit_path"], item["audit_sha256"])
                validate_instance(artifact, "exercise-set")
                validate_instance(audit, "exercise-generation-audit")
                if artifact != successor.get("artifact") or audit != successor.get("audit"):
                    raise ValueError("M7 successor envelope differs from dereferenced evidence")
                if artifact.get("lesson_id") != request.get("lesson_id") or audit.get("lesson_id") != request.get("lesson_id"):
                    raise ValueError("M7 successor evidence lesson binding drift")
                if audit.get("status") != "ACCEPTED" or audit.get("qa_issues_found") != []:
                    raise ValueError("M7 successor audit is not an accepted clean result")
                if audit.get("output_hash") != str(artifact.get("exercise_set_id", "")).removeprefix("m7set_"):
                    raise ValueError("M7 successor exercise-set identity does not bind its audit output")
            elif kind == "M8_2_SUCCESSOR_PILOT":
                required = {
                    "kind", "pilot_directory", "batch_manifest_path", "batch_manifest_sha256",
                    "artifact_path", "artifact_sha256", "audit_path", "audit_sha256",
                }
                if set(item) != required:
                    raise ValueError("M8.2 successor evidence fields are not closed")
                pilot = _safe_path(repository_root, item["pilot_directory"], directory=True)
                manifest = _document(repository_root, item["batch_manifest_path"], item["batch_manifest_sha256"])
                artifact = _document(repository_root, item["artifact_path"], item["artifact_sha256"])
                audit = _document(repository_root, item["audit_path"], item["audit_sha256"])
                if not (str(item["batch_manifest_path"]).startswith(str(item["pilot_directory"]).rstrip("/") + "/") and str(item["artifact_path"]).startswith(str(item["pilot_directory"]).rstrip("/") + "/") and str(item["audit_path"]).startswith(str(item["pilot_directory"]).rstrip("/") + "/")):
                    raise ValueError("M8.2 successor evidence member escapes its pilot")
                result = verify_pilot(pilot, _m8_authority(repository_root))
                if result.get("artifact_count") != 40 or result.get("lesson_count") != 10:
                    raise ValueError("M8.2 successor pilot inventory is incomplete")
                if not isinstance(manifest.get("members"), list) or len(manifest["members"]) != 40:
                    raise ValueError("M8.2 successor manifest inventory is incomplete")
                if artifact != successor.get("artifact") or audit != successor.get("audit"):
                    raise ValueError("M8.2 successor envelope differs from dereferenced evidence")
                if artifact.get("lesson_id") != request.get("lesson_id") or artifact.get("modality") != request.get("modality"):
                    raise ValueError("M8.2 successor artifact does not match the frozen request")
                if audit.get("artifact_sha256") != artifact.get("artifact_sha256") or audit.get("prompt_artifact_id") != artifact.get("prompt_artifact_id"):
                    raise ValueError("M8.2 successor audit does not bind its selected artifact")
            else:
                raise ValueError("unsupported M10 successor evidence kind")
    except (KeyError, OSError, TypeError, ValueError) as error:
        issues.append(RevisionIssue("SUCCESSOR_EVIDENCE", "/successor_evidence", str(error)))
    return tuple(issues)
