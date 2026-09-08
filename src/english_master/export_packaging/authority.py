"""Fail-closed AI-development authority and content-inventory checks for M11."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from english_master.independent_review.authority import VerifiedM9Authority
from english_master.independent_review.verification import verify_development_batch
from english_master.schema_validation import load_json, require_source_permission, validate_instance

from .canonical import canonical_json_bytes, identity, sha256_bytes, sha256_file


class ExportEligibilityError(ValueError):
    """Raised when development evidence or an export member is not eligible."""


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


def _current_m9_authority(root: Path, source_registry_path: Path) -> VerifiedM9Authority:
    """Reconstruct the current repository's complete M5-M8.2 authority."""
    return VerifiedM9Authority.from_files(
        structure_path=root / "curriculum" / "structure.json",
        snapshot_directory=root / "data" / "reviews" / "m5" / "development-20260903-062008",
        source_registry_path=source_registry_path,
        m6_batch_path=root / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        m6_root=root / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
        exercise_root=root / "curriculum" / "exercises",
        m7_batch_path=root / "curriculum" / "exercises" / "development-batches" / "20260903-v3" / "development-batch.json",
        pilot_directory=root / "curriculum" / "ai-practice" / "pilot-batches" / "20260905-v13",
    )


def _reject_unresolved_m10(root: Path) -> None:
    """Conservatively block M11 while any recorded M10 run is unresolved."""
    runs = root / "data" / "reviews" / "m10" / "runs"
    if not runs.is_dir():
        return
    for path in sorted(runs.rglob("*.json")):
        if path.is_symlink() or not path.is_file():
            raise ExportEligibilityError(f"M10 lineage contains an unsafe path: {path}")
        try:
            record = load_json(path)
        except (OSError, ValueError) as error:
            raise ExportEligibilityError(f"M10 lineage record is invalid: {path}: {error}") from error
        issue = _forbidden_lineage(record)
        if issue:
            raise ExportEligibilityError(f"M10 lineage is not closed: {path.relative_to(root).as_posix()}: {issue}")


def assess_authorization(authorization_path: Path, repository_root: Path) -> EligibleExport:
    """Verify AI-only development evidence and an approved-content inventory."""

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
        ("m9_development_batch", "m9-development-batch-v2"),
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
    development_ref = authorization["m9_development_batch"]
    if development.get("batch_id") != identity("m9devbatch", development, "batch_id"):
        raise ExportEligibilityError("M9 development batch identity is not canonical")
    if development.get("approval_tier") != "DEVELOPMENT_APPROVED":
        raise ExportEligibilityError("M9 evidence does not establish DEVELOPMENT_APPROVED")
    aggregate = development.get("aggregate_report")
    if not isinstance(aggregate, Mapping) or aggregate.get("blocking_finding_count") != 0:
        raise ExportEligibilityError("M9 development evidence has blocking findings")
    if (
        aggregate.get("selection_scope") != "FULL_POPULATION"
        or aggregate.get("selected_subject_count") != 60
        or aggregate.get("machine_pass_count") != 60
        or aggregate.get("ai_review_count") != 120
        or aggregate.get("unreviewed_outside_selection") is not False
    ):
        raise ExportEligibilityError("M9 evidence does not cover the complete current 60-subject population")
    authorized_at = datetime.fromisoformat(str(authorization["authorized_at"]).replace("Z", "+00:00"))
    developed_at = datetime.fromisoformat(str(development["created_at"]).replace("Z", "+00:00"))
    if authorized_at < developed_at:
        raise ExportEligibilityError("authorization timestamp predates the M9 development batch")
    if development_ref.get("sha256") != sha256_file(evidence[0][2]):
        raise ExportEligibilityError("authorization does not bind the exact M9 development batch")
    try:
        m9_authority = _current_m9_authority(repository_root.resolve(), evidence[1][2])
        verified_m9 = verify_development_batch(evidence[0][2].parent, m9_authority)
    except (OSError, TypeError, ValueError) as error:
        raise ExportEligibilityError(f"M9 development directory is not independently verifiable: {error}") from error
    if verified_m9.get("batch_id") != development.get("batch_id"):
        raise ExportEligibilityError("M9 verifier did not reconstruct the authorized batch")
    _reject_unresolved_m10(repository_root.resolve())

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
        if not statuses or statuses != {"UNREVIEWED"}:
            raise ExportEligibilityError(f"{label}: generated records must remain consistently UNREVIEWED, found {sorted(statuses)!r}")
        for source_id in sorted(_source_ids(record)):
            try:
                require_source_permission(loaded["source_registry"], source_id, "redistribute_text")
            except ValueError as error:
                raise ExportEligibilityError(f"{label}: source {source_id!r} lacks redistribution authority: {error}") from error
        artifacts.append((dict(member), record, path))

    counts = {
        content_type: sum(member[0]["content_type"] == content_type for member in artifacts)
        for content_type in schema_by_type
    }
    if counts != {"LESSON": 10, "EXERCISE_SET": 10, "AI_PRACTICE_PROMPT": 40}:
        raise ExportEligibilityError(f"artifact inventory must contain the complete 10/10/40 population, found {counts!r}")
    authorized_subjects = {
        (member[0]["content_type"], member[0]["lesson_id"], member[0]["path"], member[0]["sha256"])
        for member in artifacts
    }
    reviewed_subjects = {
        (subject.content_type, subject.lesson_id, subject.artifact_path, subject.artifact_sha256)
        for subject in m9_authority.subjects
    }
    if authorized_subjects != reviewed_subjects:
        raise ExportEligibilityError("artifact inventory is not an exact one-to-one projection of the verified M9 population")

    return EligibleExport(
        authorization=authorization,
        authorization_path=authorization_path.resolve(),
        repository_root=repository_root.resolve(),
        artifacts=tuple(artifacts),
        evidence=tuple(evidence),
    )
