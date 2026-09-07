"""Fail-closed release-authority and content-inventory checks for M11."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from english_master.independent_review.release import validate_release_decision
from english_master.schema_validation import load_json, require_source_permission, validate_instance

from .canonical import canonical_json_bytes, identity, sha256_bytes, sha256_file


class ExportEligibilityError(ValueError):
    """Raised when release evidence or an export member is not eligible."""


@dataclass(frozen=True)
class EligibleExport:
    """An independently loaded and verified M11 input set."""

    authorization: dict[str, Any]
    authorization_path: Path
    repository_root: Path
    artifacts: tuple[tuple[dict[str, Any], dict[str, Any], Path], ...]
    evidence: tuple[tuple[str, dict[str, Any], Path], ...]


def _resolve(root: Path, relative: object, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ExportEligibilityError(f"{label}: path must be a nonempty repository-relative POSIX path")
    value = PurePosixPath(relative)
    if value.is_absolute() or ".." in value.parts or "\\" in relative:
        raise ExportEligibilityError(f"{label}: unsafe path {relative!r}")
    root_resolved = root.resolve()
    path = (root_resolved / Path(*value.parts)).resolve()
    try:
        path.relative_to(root_resolved)
    except ValueError as error:
        raise ExportEligibilityError(f"{label}: path escapes repository root") from error
    if not path.is_file():
        raise ExportEligibilityError(f"{label}: file does not exist: {relative}")
    return path


def _load_bound(root: Path, reference: Mapping[str, Any], *, label: str) -> tuple[dict[str, Any], Path]:
    path = _resolve(root, reference.get("path"), label=label)
    expected = reference.get("sha256")
    actual = sha256_file(path)
    if expected != actual:
        raise ExportEligibilityError(f"{label}: SHA-256 mismatch")
    try:
        return load_json(path), path
    except (OSError, ValueError) as error:
        raise ExportEligibilityError(f"{label}: invalid JSON object: {error}") from error


def _contains_forbidden_pilot(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "source_id" and item == "src_tatoeba_text":
                return True
            if _contains_forbidden_pilot(item):
                return True
    elif isinstance(value, list):
        return any(_contains_forbidden_pilot(item) for item in value)
    return False


def _forbidden_lineage(value: Any) -> str | None:
    if isinstance(value, Mapping):
        capture = value.get("capture_mode")
        if capture in {"TEST_ONLY", "REPLAY_ONLY", "MOCK", "UNSUPPORTED"}:
            return f"non-promotable capture mode {capture}"
        terminal = value.get("terminal_state") or value.get("outcome")
        if terminal in {"ESCALATED", "RETRY_EXHAUSTED", "OPERATIONAL_FAILURE", "REJECTED"}:
            return f"failed or unresolved M10 lineage {terminal}"
        if value.get("requires_fresh_m9_review") is True:
            return "lineage still requires fresh M9 review"
        for item in value.values():
            issue = _forbidden_lineage(item)
            if issue:
                return issue
    elif isinstance(value, list):
        for item in value:
            issue = _forbidden_lineage(item)
            if issue:
                return issue
    return None


def _source_ids(value: Any) -> set[str]:
    result: set[str] = set()
    if isinstance(value, Mapping):
        source_id = value.get("source_id")
        if isinstance(source_id, str):
            result.add(source_id)
        for item in value.values():
            result.update(_source_ids(item))
    elif isinstance(value, list):
        for item in value:
            result.update(_source_ids(item))
    return result


def _qa_statuses(value: Any) -> set[str]:
    statuses: set[str] = set()
    if isinstance(value, Mapping):
        lifecycle = value.get("content_lifecycle_status")
        if isinstance(lifecycle, str):
            statuses.add(lifecycle)
        metadata = value.get("generation_metadata")
        if isinstance(metadata, Mapping) and isinstance(metadata.get("qa_status"), str):
            statuses.add(str(metadata["qa_status"]))
        for item in value.values():
            statuses.update(_qa_statuses(item))
    elif isinstance(value, list):
        for item in value:
            statuses.update(_qa_statuses(item))
    return statuses


def assess_authorization(authorization_path: Path, repository_root: Path) -> EligibleExport:
    """Verify a complete release chain and inventory; never infer approval from development evidence."""

    try:
        authorization = load_json(authorization_path)
        validate_instance(authorization, "m11-export-authorization")
    except (OSError, ValueError) as error:
        raise ExportEligibilityError(f"authorization is invalid: {error}") from error

    if authorization.get("authorization_id") != identity("m11auth", authorization, "authorization_id"):
        raise ExportEligibilityError("authorization_id is not the canonical authorization identity")
    inventory_hash = sha256_bytes(canonical_json_bytes(authorization.get("artifacts")))
    if authorization.get("subject_inventory_sha256") != inventory_hash:
        raise ExportEligibilityError("subject_inventory_sha256 does not bind the exact artifact inventory")
    if authorization.get("tatoeba_pilot_included") is not False:
        raise ExportEligibilityError("Tatoeba pilot content is categorically excluded from M11")

    evidence_specs = (
        ("m9_development_batch", "m9-development-batch"),
        ("human_review_batch", "m9-human-review-batch"),
        ("release_decision", "m9-release-decision"),
        ("source_registry", "source-registry"),
    )
    loaded: dict[str, dict[str, Any]] = {}
    evidence: list[tuple[str, dict[str, Any], Path]] = []
    for field, schema_name in evidence_specs:
        record, path = _load_bound(repository_root, authorization[field], label=field)
        try:
            validate_instance(record, schema_name)
        except ValueError as error:
            raise ExportEligibilityError(f"{field}: {error}") from error
        loaded[field] = record
        evidence.append((field, record, path))

    development = loaded["m9_development_batch"]
    human = loaded["human_review_batch"]
    decision = loaded["release_decision"]
    human_ref = authorization["human_review_batch"]
    development_ref = authorization["m9_development_batch"]
    if human.get("development_batch_id") != development.get("batch_id") or human.get("development_batch_sha256") != development_ref["sha256"]:
        raise ExportEligibilityError("human review batch is not bound to the exact M9 development batch")
    if decision.get("human_review_batch_id") != human.get("batch_id") or decision.get("human_review_batch_sha256") != human_ref["sha256"]:
        raise ExportEligibilityError("release decision is not bound to the exact human review batch")
    release_issues = validate_release_decision(decision, human)
    if release_issues:
        raise ExportEligibilityError("release decision is not eligible: " + ", ".join(release_issues))
    authorized_at = datetime.fromisoformat(str(authorization["authorized_at"]).replace("Z", "+00:00"))
    released_at = datetime.fromisoformat(str(decision["released_at"]).replace("Z", "+00:00"))
    if authorized_at < released_at:
        raise ExportEligibilityError("authorization timestamp predates the release decision")

    artifacts: list[tuple[dict[str, Any], dict[str, Any], Path]] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    schema_by_type = {
        "LESSON": "lesson",
        "EXERCISE_SET": "exercise-set",
        "AI_PRACTICE_PROMPT": "ai-practice-prompt-artifact",
    }
    for index, member in enumerate(authorization["artifacts"]):
        label = f"artifacts[{index}]"
        path_text = member["path"]
        lowered = path_text.casefold()
        if "tatoeba" in lowered or "ingestion_pilot" in lowered or lowered.startswith(("data/raw/", "data/normalized/", "data/quarantine/")):
            raise ExportEligibilityError(f"{label}: ingestion/pilot paths are excluded")
        record, path = _load_bound(repository_root, member, label=label)
        schema_name = schema_by_type[member["content_type"]]
        try:
            validate_instance(record, schema_name)
        except ValueError as error:
            raise ExportEligibilityError(f"{label}: {error}") from error
        if member["content_id"] in seen_ids or path_text in seen_paths:
            raise ExportEligibilityError(f"{label}: duplicate content identity or path")
        seen_ids.add(member["content_id"])
        seen_paths.add(path_text)
        actual_id = record.get("id") or record.get("exercise_set_id") or record.get("prompt_artifact_id")
        if actual_id != member["content_id"]:
            raise ExportEligibilityError(f"{label}: content_id does not match the record")
        actual_lesson = record.get("lesson_id") or (record.get("id") if member["content_type"] == "LESSON" else None)
        if actual_lesson != member["lesson_id"]:
            raise ExportEligibilityError(f"{label}: lesson_id does not match the record")
        if _contains_forbidden_pilot(record):
            raise ExportEligibilityError(f"{label}: Tatoeba pilot provenance is excluded")
        lineage_issue = _forbidden_lineage(record)
        if lineage_issue:
            raise ExportEligibilityError(f"{label}: {lineage_issue}")
        statuses = _qa_statuses(record)
        if not statuses or statuses != {"APPROVED"}:
            raise ExportEligibilityError(f"{label}: every generated record must have qa_status APPROVED, found {sorted(statuses)!r}")
        for source_id in sorted(_source_ids(record)):
            try:
                require_source_permission(loaded["source_registry"], source_id, "redistribute_text")
            except ValueError as error:
                raise ExportEligibilityError(f"{label}: source {source_id!r} lacks redistribution authority: {error}") from error
        artifacts.append((dict(member), record, path))

    return EligibleExport(
        authorization=authorization,
        authorization_path=authorization_path.resolve(),
        repository_root=repository_root.resolve(),
        artifacts=tuple(artifacts),
        evidence=tuple(evidence),
    )
