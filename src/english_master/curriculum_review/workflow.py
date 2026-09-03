"""Semantic workflow for M5-only independent review and approval snapshots."""

from __future__ import annotations

import copy
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from english_master.curriculum_validation.validator import CurriculumBundle, validate_bundle
from english_master.schema_validation import (
    SchemaValidationError,
    schema_directory,
    taxonomy_citation_issues,
    validate_instance,
)

from .canonical import content_identity, sha256_json
from .loading import load_strict_document
from .storage import publish_bundle

ARTIFACT_SPEC = (
    ("STRUCTURE", "curriculum-manifest", "structure", 0),
    ("GRAPH", "curriculum-graph", "graph", 1),
    ("COVERAGE", "curriculum-coverage-roadmap", "coverage", 2),
    ("TAXONOMY", "taxonomy", "taxonomy", 3),
)
REVIEW_ROLES = ("LINGUISTIC", "PEDAGOGICAL")
CHECKLIST_BY_ROLE = {
    "LINGUISTIC": (
        "CEFR_ALIGNMENT",
        "LINGUISTIC_ACCURACY",
        "DEPENDENCY_SOUNDNESS",
        "VOCABULARY_SENSE_INTEGRITY",
        "VIETNAMESE_LEARNER_RELEVANCE",
    ),
    "PEDAGOGICAL": (
        "PEDAGOGICAL_SEQUENCE",
        "OBJECTIVE_COHERENCE",
        "SKILL_BALANCE",
        "REVIEW_SPIRAL",
        "ASSESSMENT_ALIGNMENT",
        "SCOPE_AND_HOURS_CREDIBILITY",
    ),
}
VALIDATION_SCHEMA_ROOTS = (
    "source-registry.schema.json",
    "taxonomy.schema.json",
    "curriculum-manifest.schema.json",
    "curriculum-graph.schema.json",
    "curriculum-coverage-roadmap.schema.json",
    "curriculum-review-manifest.schema.json",
    "curriculum-independent-review-draft.schema.json",
    "curriculum-independent-review.schema.json",
    "curriculum-reviewer-registry.schema.json",
    "curriculum-approval-snapshot.schema.json",
    "curriculum-development-snapshot.schema.json",
)
REVIEW_VALIDATION_PROFILE = "M5_INDEPENDENT_REVIEW_V2"
SEMANTIC_VALIDATOR_VERSION = "2.0"
CANONICALIZATION_PROFILE = "SORTED_COMPACT_JSON_V1"
_ORDERABLE_TIMESTAMP = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-5][0-9])"
    r"(?P<fraction>\.[0-9]+)?(?P<offset>Z|[+-][0-9]{2}:[0-9]{2})$"
)
_EPOCH = datetime(1970, 1, 1)


@dataclass(frozen=True, order=True)
class ReviewIssue:
    """Stable semantic issue reported by the review workflow."""

    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


class ReviewValidationError(ValueError):
    """Raised when a manifest, review, or snapshot fails closed."""

    def __init__(self, issues: Iterable[ReviewIssue]) -> None:
        self.issues = tuple(sorted(set(issues)))
        super().__init__("; ".join(f"{issue.path} [{issue.code}]: {issue.message}" for issue in self.issues))


def _schema_issues(value: Mapping[str, Any], schema_name: str, path: str) -> list[ReviewIssue]:
    try:
        validate_instance(dict(value), schema_name)
    except SchemaValidationError as error:
        return [
            ReviewIssue(f"{path}{issue.instance_path[1:]}", "SCHEMA_INVALID", issue.message)
            for issue in error.issues
        ]
    return []


def _safe_hash(value: Any, *, path: str, issues: list[ReviewIssue]) -> str | None:
    try:
        return sha256_json(value)
    except (TypeError, ValueError) as error:
        issues.append(ReviewIssue(path, "CANONICALIZATION_FAILED", str(error)))
        return None


def _safe_identity(prefix: str, value: Mapping[str, Any], field: str, *, path: str, issues: list[ReviewIssue]) -> str | None:
    try:
        return content_identity(prefix, value, field)
    except (TypeError, ValueError) as error:
        issues.append(ReviewIssue(path, "CANONICALIZATION_FAILED", str(error)))
        return None


def normalize_reviewer_id(value: str) -> str:
    """Apply the canonical comparison form for externally assigned reviewer IDs."""

    return unicodedata.normalize("NFKC", value).strip().casefold()


def _logical_path(path: Path, structure_path: Path) -> str:
    """Represent the actual resolved input relative to the structure directory."""

    try:
        relative = os.path.relpath(path, start=structure_path.parent)
    except ValueError:
        return path.as_uri()
    return Path(relative).as_posix()


def validate_source_registry(
    registry: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    *,
    required_taxonomy_ids: Iterable[str] | None = None,
) -> tuple[ReviewIssue, ...]:
    """Validate source-registry shape and taxonomy citations in the approval scope."""

    issues = _schema_issues(registry, "source-registry", "$.source_registry")
    if not issues:
        for issue in taxonomy_citation_issues(
            dict(taxonomy),
            dict(registry),
            required_record_ids=required_taxonomy_ids,
        ):
            issues.append(
                ReviewIssue(
                    f"$.taxonomy{issue.instance_path[1:]}",
                    "TAXONOMY_SOURCE_INELIGIBLE",
                    issue.message,
                )
            )
    return tuple(sorted(set(issues)))


def _bundle_input_issues(bundle: CurriculumBundle) -> tuple[ReviewIssue, ...]:
    documents = (bundle.structure, bundle.graph, bundle.coverage, bundle.taxonomy)
    issues: list[ReviewIssue] = []
    for (role, _, _, _), document, path in zip(
        ARTIFACT_SPEC,
        documents,
        bundle.paths,
        strict=True,
    ):
        loaded = load_strict_document(path.resolve())
        if loaded != dict(document):
            issues.append(
                ReviewIssue(
                    f"$.artifacts.{role.lower()}",
                    "M5_ARTIFACT_INPUT_MISMATCH",
                    f"{role} value does not equal the independently loaded artifact path",
                )
            )
    return tuple(issues)


def _source_registry_input_issues(
    registry: Mapping[str, Any],
    registry_path: Path,
) -> tuple[ReviewIssue, ...]:
    """Ensure the claimed authority value is exactly the value loaded from its path."""

    loaded = load_strict_document(registry_path.resolve())
    if loaded == dict(registry):
        return ()
    return (
        ReviewIssue(
            "$.source_registry",
            "SOURCE_REGISTRY_INPUT_MISMATCH",
            "source registry value does not equal the independently loaded registry path",
        ),
    )


def _source_registry_binding(
    registry: Mapping[str, Any],
    registry_path: Path,
    structure_path: Path,
) -> dict[str, Any]:
    return {
        "logical_path": _logical_path(registry_path.resolve(), structure_path.resolve()),
        "schema_name": "source-registry",
        "schema_version": str(registry.get("schema_version", "")),
        "sha256": sha256_json(registry),
    }


def _is_blank(value: object) -> bool:
    return isinstance(value, str) and not value.strip()


def validate_reviewer_registry(registry: Mapping[str, Any]) -> tuple[ReviewIssue, ...]:
    """Validate the independently supplied trusted reviewer authority."""

    issues = _schema_issues(registry, "curriculum-reviewer-registry", "$.reviewer_registry")
    expected_id = _safe_identity("m5reviewers", registry, "registry_id", path="$.reviewer_registry.registry_id", issues=issues)
    if expected_id is not None and registry.get("registry_id") != expected_id:
        issues.append(ReviewIssue("$.reviewer_registry.registry_id", "REGISTRY_ID_MISMATCH", "registry_id is not its canonical content identity"))
    for field in ("issued_by",):
        if _is_blank(registry.get(field)):
            issues.append(ReviewIssue(f"$.reviewer_registry.{field}", "BLANK_VALUE", f"{field} cannot contain only whitespace"))
    records = registry.get("reviewers")
    reviewer_ids: list[str] = []
    evidence_ids: list[str] = []
    subject_keys: list[tuple[str, str]] = []
    if isinstance(records, list):
        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                continue
            reviewer_id = record.get("reviewer_id")
            if isinstance(reviewer_id, str):
                normalized = normalize_reviewer_id(reviewer_id)
                reviewer_ids.append(normalized)
                if reviewer_id != normalized:
                    issues.append(ReviewIssue(f"$.reviewer_registry.reviewers[{index}].reviewer_id", "NONCANONICAL_REVIEWER_ID", "trusted reviewer IDs must already be NFKC-normalized, trimmed, and case-folded"))
            for field in ("display_name",):
                if _is_blank(record.get(field)):
                    issues.append(ReviewIssue(f"$.reviewer_registry.reviewers[{index}].{field}", "BLANK_VALUE", f"{field} cannot contain only whitespace"))
            qualifications = record.get("qualifications")
            if isinstance(qualifications, list):
                for qualification_index, qualification in enumerate(qualifications):
                    if _is_blank(qualification):
                        issues.append(ReviewIssue(f"$.reviewer_registry.reviewers[{index}].qualifications[{qualification_index}]", "BLANK_VALUE", "qualification cannot contain only whitespace"))
            evidence = record.get("identity_evidence")
            if isinstance(evidence, Mapping):
                if isinstance(evidence.get("evidence_id"), str):
                    evidence_id = str(evidence["evidence_id"])
                    evidence_ids.append(evidence_id)
                    if evidence_id != normalize_reviewer_id(evidence_id):
                        issues.append(ReviewIssue(f"$.reviewer_registry.reviewers[{index}].identity_evidence.evidence_id", "NONCANONICAL_EVIDENCE_ID", "identity evidence IDs must already be NFKC-normalized, trimmed, and case-folded"))
                for field in ("issuer", "subject_id", "evidence_reference", "verified_by"):
                    if _is_blank(evidence.get(field)):
                        issues.append(ReviewIssue(f"$.reviewer_registry.reviewers[{index}].identity_evidence.{field}", "BLANK_VALUE", f"{field} cannot contain only whitespace"))
                subject_id = evidence.get("subject_id")
                issuer = evidence.get("issuer")
                if isinstance(subject_id, str) and isinstance(issuer, str):
                    subject_keys.append((normalize_reviewer_id(issuer), subject_id))
                issued_at = _parse_datetime(
                    registry.get("issued_at"),
                    path="$.reviewer_registry.issued_at",
                    issues=issues,
                )
                verified_at = _parse_datetime(
                    evidence.get("verified_at"),
                    path=f"$.reviewer_registry.reviewers[{index}].identity_evidence.verified_at",
                    issues=issues,
                )
                if issued_at is not None and verified_at is not None and verified_at > issued_at:
                    issues.append(ReviewIssue(f"$.reviewer_registry.reviewers[{index}].identity_evidence.verified_at", "EVIDENCE_AFTER_REGISTRY_ISSUANCE", "identity evidence must be verified no later than registry issuance"))
    if len(reviewer_ids) != len(set(reviewer_ids)):
        issues.append(ReviewIssue("$.reviewer_registry.reviewers", "DUPLICATE_REVIEWER_ID", "reviewer IDs must be unique after normalization"))
    if len(evidence_ids) != len(set(evidence_ids)):
        issues.append(ReviewIssue("$.reviewer_registry.reviewers", "DUPLICATE_IDENTITY_EVIDENCE", "identity evidence IDs must be unique"))
    if len(subject_keys) != len(set(subject_keys)):
        issues.append(ReviewIssue("$.reviewer_registry.reviewers", "DUPLICATE_IDENTITY_SUBJECT", "one exact provider subject under the same normalized issuer cannot authorize multiple reviewer records"))
    return tuple(sorted(set(issues)))


def _reviewer_index(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    records = registry.get("reviewers")
    if not isinstance(records, list):
        return {}
    return {
        normalize_reviewer_id(str(record["reviewer_id"])): record
        for record in records
        if isinstance(record, Mapping) and isinstance(record.get("reviewer_id"), str)
    }


def _taxonomy_indexes(taxonomy: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, str]]:
    records: dict[str, Mapping[str, Any]] = {}
    types: dict[str, str] = {}
    for collection, record_type in (("concepts", "TAXONOMY_CONCEPT"), ("vocabulary_senses", "VOCABULARY_SENSE")):
        values = taxonomy.get(collection, [])
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict) and isinstance(value.get("id"), str):
                    records[value["id"]] = value
                    types[value["id"]] = record_type
    return records, types


def _taxonomy_scope(bundle: CurriculumBundle) -> list[dict[str, Any]]:
    records, types = _taxonomy_indexes(bundle.taxonomy)
    selected: set[str] = set()
    for lesson in bundle.structure.get("lessons", []):
        if not isinstance(lesson, dict):
            continue
        for field in ("grammar", "functions", "pronunciation", "taxonomy_concepts", "vocabulary"):
            values = lesson.get(field, [])
            if isinstance(values, list):
                selected.update(value for value in values if isinstance(value, str))
    queue = list(selected)
    while queue:
        record = records.get(queue.pop())
        if record is None:
            continue
        for prerequisite in record.get("prerequisites", []):
            if isinstance(prerequisite, str) and prerequisite not in selected:
                selected.add(prerequisite)
                queue.append(prerequisite)
    return [
        {
            "id": record_id,
            "record_type": types[record_id],
            "source_status": records[record_id].get("status"),
            "sha256": sha256_json(records[record_id]),
        }
        for record_id in sorted(selected)
        if record_id in records
    ]


def _annotation_scope(bundle: CurriculumBundle) -> list[dict[str, Any]]:
    """Inventory reviewed Vietnamese annotations without granting generation authority."""

    values = bundle.taxonomy.get("vietnamese_learner_annotations", [])
    records = [
        value
        for value in values
        if isinstance(value, Mapping) and isinstance(value.get("id"), str)
    ] if isinstance(values, list) else []
    return [
        {
            "id": str(record["id"]),
            "target_id": record.get("target_id"),
            "annotation_kind": record.get("annotation_kind"),
            "source_status": record.get("status"),
            "sha256": sha256_json(record),
        }
        for record in sorted(records, key=lambda item: str(item["id"]))
    ]


def _schema_reference_targets(value: Any) -> set[str]:
    targets: set[str] = set()
    if isinstance(value, Mapping):
        reference = value.get("$ref")
        if isinstance(reference, str):
            document = reference.split("#", 1)[0]
            if document:
                path = urlsplit(document).path if "://" in document else document
                targets.add(Path(path).name)
        for child in value.values():
            targets.update(_schema_reference_targets(child))
    elif isinstance(value, list):
        for child in value:
            targets.update(_schema_reference_targets(child))
    return targets


def _validation_schema_bindings() -> list[dict[str, str]]:
    directory = schema_directory().resolve()
    pending = list(VALIDATION_SCHEMA_ROOTS)
    loaded: dict[str, dict[str, Any]] = {}
    while pending:
        filename = pending.pop()
        if filename in loaded:
            continue
        path = (directory / filename).resolve()
        if path.parent != directory or not filename.endswith(".schema.json"):
            raise ValueError(f"invalid local schema dependency: {filename!r}")
        schema = load_strict_document(path)
        loaded[filename] = schema
        pending.extend(_schema_reference_targets(schema) - loaded.keys())
    return [
        {
            "logical_path": f"schemas/{filename}",
            "sha256": sha256_json(schema),
        }
        for filename, schema in sorted(loaded.items())
    ]


def _validation_policy() -> dict[str, Any]:
    return {
        "profile": REVIEW_VALIDATION_PROFILE,
        "semantic_validator_version": SEMANTIC_VALIDATOR_VERSION,
        "canonicalization_profile": CANONICALIZATION_PROFILE,
        "required_checklists": {
            role: list(CHECKLIST_BY_ROLE[role])
            for role in REVIEW_ROLES
        },
        "schema_bindings": _validation_schema_bindings(),
    }


def _manifest_without_id(
    bundle: CurriculumBundle,
    source_registry: Mapping[str, Any],
    source_registry_path: Path,
) -> dict[str, Any]:
    documents = {
        "structure": bundle.structure,
        "graph": bundle.graph,
        "coverage": bundle.coverage,
        "taxonomy": bundle.taxonomy,
    }
    return {
        "schema_version": "2.0",
        "record_type": "curriculum_review_manifest",
        "curriculum_version": str(bundle.structure.get("curriculum_version", "")),
        "taxonomy_version": str(bundle.taxonomy.get("taxonomy_version", "")),
        "source_registry": _source_registry_binding(
            source_registry,
            source_registry_path,
            bundle.paths[0],
        ),
        "artifacts": [
            {
                "role": role,
                "logical_path": _logical_path(bundle.paths[path_index], bundle.paths[0]),
                "schema_name": schema_name,
                "sha256": sha256_json(documents[key]),
            }
            for role, schema_name, key, path_index in ARTIFACT_SPEC
        ],
        "taxonomy_scope": _taxonomy_scope(bundle),
        "annotation_scope": _annotation_scope(bundle),
        "required_review_roles": list(REVIEW_ROLES),
        "validation_policy": _validation_policy(),
        "source_bundle_policy": {
            "m5_records_remain_unchanged": True,
            "taxonomy_statuses_remain_draft": True,
            "lesson_outlines_remain_outline_only": True,
            "content_generation_permitted_by_manifest": False,
        },
    }


def build_manifest(
    bundle: CurriculumBundle,
    source_registry: Mapping[str, Any],
    *,
    source_registry_path: Path,
    _source_prevalidated: bool = False,
) -> dict[str, Any]:
    """Build a deterministic manifest after validating M5 and source governance."""

    curriculum_result = None if _source_prevalidated else validate_bundle(bundle)
    issues = [] if curriculum_result is None else [ReviewIssue(issue.path, f"M5_{issue.code}", issue.message) for issue in curriculum_result.issues]
    issues.extend(_bundle_input_issues(bundle))
    scope = _taxonomy_scope(bundle)
    annotation_scope = _annotation_scope(bundle)
    scope_ids = [record["id"] for record in scope]
    annotation_ids = [record["id"] for record in annotation_scope]
    reviewed_record_ids = [*scope_ids, *annotation_ids]
    issues.extend(_source_registry_input_issues(source_registry, source_registry_path))
    issues.extend(
        validate_source_registry(
            source_registry,
            bundle.taxonomy,
            required_taxonomy_ids=reviewed_record_ids,
        )
    )
    issues.extend(
        _source_chronology_issues(
            source_registry,
            bundle.taxonomy,
            reviewed_record_ids,
        )
    )
    non_draft: list[str] = []
    for collection in ("concepts", "vocabulary_senses", "vietnamese_learner_annotations"):
        records = bundle.taxonomy.get(collection, [])
        if isinstance(records, list):
            non_draft.extend(
                str(record.get("id", f"{collection}[{index}]"))
                for index, record in enumerate(records)
                if isinstance(record, dict) and record.get("status") != "DRAFT"
            )
    if non_draft:
        issues.append(ReviewIssue("$.taxonomy", "SOURCE_STATUS_CHANGED", f"M5 taxonomy records must remain DRAFT: {', '.join(sorted(non_draft))}"))
    if issues:
        raise ReviewValidationError(issues)
    payload = _manifest_without_id(bundle, source_registry, source_registry_path)
    if not payload["taxonomy_scope"]:
        raise ReviewValidationError([ReviewIssue("$.taxonomy_scope", "EMPTY_REVIEW_SCOPE", "the M5 bundle references no taxonomy records")])
    if not payload["annotation_scope"]:
        raise ReviewValidationError([ReviewIssue("$.annotation_scope", "EMPTY_ANNOTATION_SCOPE", "the M5 bundle contains no Vietnamese learner annotations")])
    payload["manifest_id"] = content_identity("m5manifest", payload, "manifest_id")
    validate_instance(payload, "curriculum-review-manifest")
    return payload


def validate_manifest(
    manifest: Mapping[str, Any],
    bundle: CurriculumBundle,
    source_registry: Mapping[str, Any],
    *,
    source_registry_path: Path,
    _source_prevalidated: bool = False,
) -> tuple[ReviewIssue, ...]:
    """Validate exact bindings to loaded M5 artifacts and source governance."""

    issues = _schema_issues(manifest, "curriculum-review-manifest", "$.manifest")
    try:
        expected = build_manifest(
            bundle,
            source_registry,
            source_registry_path=source_registry_path,
            _source_prevalidated=_source_prevalidated,
        )
    except ReviewValidationError as error:
        issues.extend(error.issues)
        try:
            expected = _manifest_without_id(
                bundle,
                source_registry,
                source_registry_path,
            )
            expected["manifest_id"] = content_identity(
                "m5manifest",
                expected,
                "manifest_id",
            )
        except (OSError, TypeError, ValueError):
            expected = None
    expected_identity = _safe_identity("m5manifest", manifest, "manifest_id", path="$.manifest.manifest_id", issues=issues)
    if expected_identity is not None and manifest.get("manifest_id") != expected_identity:
        issues.append(ReviewIssue("$.manifest.manifest_id", "MANIFEST_ID_MISMATCH", "manifest_id is not its canonical content identity"))
    if expected is not None and dict(manifest) != expected:
        issues.append(ReviewIssue("$.manifest", "STALE_MANIFEST", "manifest does not exactly match the loaded M5 source bundle and source registry"))
    return tuple(sorted(set(issues)))


def normalize_review_submission(review: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize external reviewer/evidence identifiers before finalization."""

    normalized = copy.deepcopy(dict(review))
    reviewer = normalized.get("reviewer")
    if isinstance(reviewer, dict):
        reviewer_id = reviewer.get("reviewer_id")
        if isinstance(reviewer_id, str):
            reviewer["reviewer_id"] = normalize_reviewer_id(reviewer_id)
        evidence_id = reviewer.get("identity_evidence_id")
        if isinstance(evidence_id, str):
            reviewer["identity_evidence_id"] = normalize_reviewer_id(evidence_id)
    return normalized


def finalize_review(review: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize a completed draft and inject or verify its canonical review ID."""

    finalized = normalize_review_submission(review)
    issues: list[ReviewIssue] = []
    expected_id = _safe_identity("m5review", finalized, "review_id", path="$.review_id", issues=issues)
    supplied = finalized.get("review_id")
    if expected_id is not None and supplied is not None and supplied != expected_id:
        issues.append(ReviewIssue("$.review_id", "REVIEW_ID_MISMATCH", "review_id is not its canonical content identity"))
    if issues:
        raise ReviewValidationError(issues)
    assert expected_id is not None
    finalized["review_id"] = expected_id
    return finalized


def validate_review(review: Mapping[str, Any], manifest: Mapping[str, Any], reviewer_registry: Mapping[str, Any], *, manifest_digest: str | None = None) -> tuple[ReviewIssue, ...]:
    """Validate a finalized human review against a manifest and trusted identity authority."""

    issues = list(validate_reviewer_registry(reviewer_registry))
    issues.extend(_schema_issues(review, "curriculum-independent-review", "$.review"))
    expected_id = _safe_identity("m5review", review, "review_id", path="$.review.review_id", issues=issues)
    if expected_id is not None and review.get("review_id") != expected_id:
        issues.append(ReviewIssue("$.review.review_id", "REVIEW_ID_MISMATCH", "review_id is not its canonical content identity"))
    if review.get("manifest_id") != manifest.get("manifest_id"):
        issues.append(ReviewIssue("$.review.manifest_id", "REVIEW_MANIFEST_MISMATCH", "review names a different manifest"))
    expected_manifest_hash = manifest_digest or _safe_hash(manifest, path="$.review.manifest_sha256", issues=issues)
    if expected_manifest_hash is not None and review.get("manifest_sha256") != expected_manifest_hash:
        issues.append(ReviewIssue("$.review.manifest_sha256", "REVIEW_MANIFEST_HASH_MISMATCH", "review is not hash-bound to this manifest"))
    expected_artifacts = [item[0] for item in ARTIFACT_SPEC]
    if review.get("artifact_scope") != expected_artifacts:
        issues.append(ReviewIssue("$.review.artifact_scope", "INCOMPLETE_ARTIFACT_SCOPE", "review must cover all four M5 artifacts in canonical order"))
    taxonomy_records = manifest.get("taxonomy_scope")
    expected_taxonomy = [record["id"] for record in taxonomy_records if isinstance(record, Mapping) and isinstance(record.get("id"), str)] if isinstance(taxonomy_records, list) else []
    if review.get("taxonomy_scope") != expected_taxonomy:
        issues.append(ReviewIssue("$.review.taxonomy_scope", "INCOMPLETE_TAXONOMY_SCOPE", "review must cover the exact manifest taxonomy scope in canonical order"))
    annotation_records = manifest.get("annotation_scope")
    expected_annotations = [record["id"] for record in annotation_records if isinstance(record, Mapping) and isinstance(record.get("id"), str)] if isinstance(annotation_records, list) else []
    if review.get("annotation_scope") != expected_annotations:
        issues.append(ReviewIssue("$.review.annotation_scope", "INCOMPLETE_ANNOTATION_SCOPE", "review must cover the exact manifest annotation scope in canonical order"))
    role = review.get("review_role")
    validation_policy = manifest.get("validation_policy")
    required_checklists = (
        validation_policy.get("required_checklists")
        if isinstance(validation_policy, Mapping)
        else None
    )
    role_checks = required_checklists.get(str(role)) if isinstance(required_checklists, Mapping) else None
    expected_checks = list(role_checks) if isinstance(role_checks, list) else []
    checks = review.get("checklist")
    actual_checks = [check.get("criterion") for check in checks if isinstance(check, Mapping)] if isinstance(checks, list) else []
    if actual_checks != expected_checks:
        issues.append(ReviewIssue("$.review.checklist", "CHECKLIST_MISMATCH", f"{role!r} review requires criteria {expected_checks!r} in order"))
    if isinstance(checks, list):
        for index, check in enumerate(checks):
            if isinstance(check, Mapping) and _is_blank(check.get("notes")):
                issues.append(ReviewIssue(f"$.review.checklist[{index}].notes", "BLANK_VALUE", "checklist notes cannot contain only whitespace"))
    findings = review.get("findings")
    finding_ids = [finding.get("finding_id") for finding in findings if isinstance(finding, Mapping) and isinstance(finding.get("finding_id"), str)] if isinstance(findings, list) else []
    if len(finding_ids) != len(set(finding_ids)):
        issues.append(ReviewIssue("$.review.findings", "DUPLICATE_FINDING_ID", "finding_id values must be unique"))
    if isinstance(findings, list):
        for index, finding in enumerate(findings):
            if not isinstance(finding, Mapping):
                continue
            for field in ("category", "location", "description", "required_action"):
                if _is_blank(finding.get(field)):
                    issues.append(ReviewIssue(f"$.review.findings[{index}].{field}", "BLANK_VALUE", f"{field} cannot contain only whitespace"))
    reviewer = review.get("reviewer")
    if isinstance(reviewer, Mapping):
        reviewer_id_value = reviewer.get("reviewer_id")
        normalized_id = normalize_reviewer_id(reviewer_id_value) if isinstance(reviewer_id_value, str) else None
        if normalized_id is not None and reviewer_id_value != normalized_id:
            issues.append(ReviewIssue("$.review.reviewer.reviewer_id", "NONCANONICAL_REVIEWER_ID", "finalized reviewer ID is not normalized"))
        authority = _reviewer_index(reviewer_registry).get(normalized_id) if normalized_id is not None else None
        if authority is None:
            issues.append(ReviewIssue("$.review.reviewer.reviewer_id", "UNTRUSTED_REVIEWER", "reviewer ID is absent from the independently loaded trusted registry"))
        else:
            if authority.get("status") != "VERIFIED":
                issues.append(ReviewIssue("$.review.reviewer.reviewer_id", "UNVERIFIED_REVIEWER", "reviewer registry status must be VERIFIED"))
            permitted_roles = authority.get("permitted_roles")
            if not isinstance(permitted_roles, list) or role not in permitted_roles:
                issues.append(ReviewIssue("$.review.review_role", "REVIEWER_ROLE_NOT_PERMITTED", "trusted registry does not permit this reviewer role"))
            for field in ("display_name", "qualifications"):
                if reviewer.get(field) != authority.get(field):
                    issues.append(ReviewIssue(f"$.review.reviewer.{field}", "REVIEWER_AUTHORITY_MISMATCH", f"{field} does not match the trusted reviewer registry"))
            evidence = authority.get("identity_evidence")
            expected_evidence_id = evidence.get("evidence_id") if isinstance(evidence, Mapping) else None
            if reviewer.get("identity_evidence_id") != expected_evidence_id:
                issues.append(ReviewIssue("$.review.reviewer.identity_evidence_id", "IDENTITY_EVIDENCE_MISMATCH", "identity evidence ID does not match the trusted reviewer registry"))
            reviewed_at = _parse_datetime(
                review.get("reviewed_at"),
                path="$.review.reviewed_at",
                issues=issues,
            )
            registry_issued_at = _parse_datetime(
                reviewer_registry.get("issued_at"),
                path="$.reviewer_registry.issued_at",
                issues=issues,
            )
            evidence_verified_at = (
                _parse_datetime(
                    evidence.get("verified_at"),
                    path="$.reviewer_registry.identity_evidence.verified_at",
                    issues=issues,
                )
                if isinstance(evidence, Mapping)
                else None
            )
            if reviewed_at is not None and registry_issued_at is not None and registry_issued_at > reviewed_at:
                issues.append(ReviewIssue("$.review.reviewed_at", "REVIEW_BEFORE_REGISTRY_ISSUANCE", "review cannot rely on a registry issued after the review"))
            if reviewed_at is not None and evidence_verified_at is not None and evidence_verified_at > reviewed_at:
                issues.append(ReviewIssue("$.review.reviewed_at", "REVIEW_BEFORE_IDENTITY_VERIFICATION", "review cannot rely on identity evidence verified after the review"))
        if _is_blank(reviewer.get("display_name")):
            issues.append(ReviewIssue("$.review.reviewer.display_name", "BLANK_VALUE", "display_name cannot contain only whitespace"))
        qualifications = reviewer.get("qualifications")
        if isinstance(qualifications, list):
            for index, qualification in enumerate(qualifications):
                if _is_blank(qualification):
                    issues.append(ReviewIssue(f"$.review.reviewer.qualifications[{index}]", "BLANK_VALUE", "qualification cannot contain only whitespace"))
        if _is_blank(reviewer.get("conflict_notes")):
            issues.append(ReviewIssue("$.review.reviewer.conflict_notes", "BLANK_VALUE", "conflict_notes cannot contain only whitespace"))
    return tuple(sorted(set(issues)))


def _parse_datetime(value: object, *, path: str, issues: list[ReviewIssue]) -> Decimal | None:
    if not isinstance(value, str):
        return None
    match = _ORDERABLE_TIMESTAMP.fullmatch(value)
    if match is None or value.endswith("-00:00"):
        issues.append(
            ReviewIssue(
                path,
                "UNORDERABLE_TIMESTAMP",
                "timestamp must be an orderable RFC 3339 value without leap seconds or the unknown '-00:00' offset",
            )
        )
        return None
    offset = "+00:00" if match.group("offset") == "Z" else match.group("offset")
    whole_second = (
        f"{match.group('date')}T{match.group('hour')}:"
        f"{match.group('minute')}:{match.group('second')}{offset}"
    )
    try:
        parsed = datetime.fromisoformat(whole_second)
        utc_value = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except (OverflowError, ValueError):
        issues.append(
            ReviewIssue(
                path,
                "UNORDERABLE_TIMESTAMP",
                "timestamp is valid input syntax but cannot be ordered by this implementation",
            )
        )
        return None
    delta = utc_value - _EPOCH
    whole_seconds = delta.days * 86_400 + delta.seconds
    return Decimal(whole_seconds) + Decimal(match.group("fraction") or "0")


def _taxonomy_source_ids(
    taxonomy: Mapping[str, Any],
    required_taxonomy_ids: Iterable[str],
) -> frozenset[str]:
    required_ids = frozenset(required_taxonomy_ids)
    source_ids: set[str] = set()
    for collection in ("concepts", "vocabulary_senses", "vietnamese_learner_annotations"):
        records = taxonomy.get(collection)
        if not isinstance(records, list):
            continue
        for record in records:
            if not isinstance(record, Mapping) or record.get("id") not in required_ids:
                continue
            evidence = record.get("evidence_or_reference")
            if not isinstance(evidence, list):
                continue
            for reference in evidence:
                if isinstance(reference, Mapping) and isinstance(reference.get("source_id"), str):
                    source_ids.add(reference["source_id"])
    return frozenset(source_ids)


def _source_chronology_issues(
    source_registry: Mapping[str, Any],
    taxonomy: Mapping[str, Any],
    required_taxonomy_ids: Iterable[str],
    *,
    reviews: Iterable[Mapping[str, Any]] = (),
    approved_at: object | None = None,
) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    required_source_ids = _taxonomy_source_ids(taxonomy, required_taxonomy_ids)
    sources = source_registry.get("sources")
    if not isinstance(sources, list):
        return issues
    authority_times: dict[str, Decimal] = {}
    for source_index, source in enumerate(sources):
        if not isinstance(source, Mapping) or source.get("source_id") not in required_source_ids:
            continue
        source_id = str(source["source_id"])
        base_path = f"$.source_registry.sources[{source_index}]"
        reviewed_at = _parse_datetime(
            source.get("reviewed_at"),
            path=f"{base_path}.reviewed_at",
            issues=issues,
        )
        dated_events = [
            (
                f"{base_path}.registered_at",
                _parse_datetime(
                    source.get("registered_at"),
                    path=f"{base_path}.registered_at",
                    issues=issues,
                ),
            ),
        ]
        license_record = source.get("license")
        if isinstance(license_record, Mapping):
            path = f"{base_path}.license.reviewed_at"
            dated_events.append(
                (
                    path,
                    _parse_datetime(
                        license_record.get("reviewed_at"),
                        path=path,
                        issues=issues,
                    ),
                )
            )
        evidence = source.get("evidence")
        if isinstance(evidence, list):
            for evidence_index, item in enumerate(evidence):
                if not isinstance(item, Mapping):
                    continue
                path = f"{base_path}.evidence[{evidence_index}].checked_at"
                dated_events.append(
                    (
                        path,
                        _parse_datetime(
                            item.get("checked_at"),
                            path=path,
                            issues=issues,
                        ),
                    )
                )
        event_times = [value for _, value in dated_events if value is not None]
        if reviewed_at is not None:
            authority_times[source_id] = max([reviewed_at, *event_times])
            for path, event_time in dated_events:
                if event_time is not None and event_time > reviewed_at:
                    issues.append(
                        ReviewIssue(
                            path,
                            "SOURCE_EVENT_AFTER_REVIEW",
                            "source registration, license review, and evidence checks must not follow source review",
                        )
                    )
    latest_authority = max(authority_times.values()) if authority_times else None
    if latest_authority is not None:
        for review_index, review in enumerate(reviews):
            reviewed_at = _parse_datetime(
                review.get("reviewed_at"),
                path=f"$.reviews[{review_index}].reviewed_at",
                issues=issues,
            )
            if reviewed_at is not None and reviewed_at < latest_authority:
                issues.append(
                    ReviewIssue(
                        f"$.reviews[{review_index}].reviewed_at",
                        "REVIEW_BEFORE_SOURCE_AUTHORITY",
                        "review cannot rely on source governance established later",
                    )
                )
        approval_time = _parse_datetime(
            approved_at,
            path="$.approved_at",
            issues=issues,
        )
        if approval_time is not None and approval_time < latest_authority:
            issues.append(
                ReviewIssue(
                    "$.approved_at",
                    "APPROVAL_BEFORE_SOURCE_AUTHORITY",
                    "approval cannot rely on source governance established later",
                )
            )
    return issues


def _approval_issues(
    reviews: list[Mapping[str, Any]],
    *,
    approved_at: object | None = None,
    observed_at: object | None = None,
) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    roles = [review.get("review_role") for review in reviews]
    if roles != list(REVIEW_ROLES):
        issues.append(ReviewIssue("$.reviews", "REQUIRED_REVIEW_ROLES", f"reviews must be ordered exactly as {list(REVIEW_ROLES)!r}"))
    reviewer_ids: list[str] = []
    for review in reviews:
        reviewer = review.get("reviewer")
        reviewer_id = reviewer.get("reviewer_id") if isinstance(reviewer, Mapping) else None
        if isinstance(reviewer_id, str):
            reviewer_ids.append(normalize_reviewer_id(reviewer_id))
    if len(reviewer_ids) != len(set(reviewer_ids)) or len(reviewer_ids) != len(reviews):
        issues.append(ReviewIssue("$.reviews", "REVIEWERS_NOT_INDEPENDENT", "linguistic and pedagogical reviews require two distinct normalized reviewer IDs"))
    for index, review in enumerate(reviews):
        if review.get("decision") != "APPROVE":
            issues.append(ReviewIssue(f"$.reviews[{index}].decision", "REVIEW_NOT_APPROVED", "every required review must explicitly APPROVE"))
        checks = review.get("checklist")
        if isinstance(checks, list):
            for check_index, check in enumerate(checks):
                if isinstance(check, Mapping) and check.get("result") != "PASS":
                    issues.append(ReviewIssue(f"$.reviews[{index}].checklist[{check_index}].result", "CHECK_FAILED", "approval requires every checklist item to pass"))
        findings = review.get("findings")
        if isinstance(findings, list):
            for finding_index, finding in enumerate(findings):
                if isinstance(finding, Mapping) and finding.get("severity") in {"MAJOR", "CRITICAL"}:
                    issues.append(ReviewIssue(f"$.reviews[{index}].findings[{finding_index}].severity", "BLOCKING_FINDING", "major and critical findings block publication"))
    approval_time = _parse_datetime(approved_at, path="$.approved_at", issues=issues)
    review_times = [
        _parse_datetime(
            review.get("reviewed_at"),
            path=f"$.reviews[{index}].reviewed_at",
            issues=issues,
        )
        for index, review in enumerate(reviews)
    ]
    if approval_time is not None and any(review_time is not None and review_time > approval_time for review_time in review_times):
        issues.append(ReviewIssue("$.approved_at", "APPROVAL_BEFORE_REVIEW", "approved_at cannot precede either human review"))
    observation_value = observed_at
    if observation_value is None:
        observation_value = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    observation_time = _parse_datetime(
        observation_value,
        path="$.observation_timestamp",
        issues=issues,
    )
    if approval_time is not None and observation_time is not None and approval_time > observation_time:
        issues.append(
            ReviewIssue(
                "$.approved_at",
                "FUTURE_APPROVAL",
                "approved_at cannot be later than the trusted publication or verification clock",
            )
        )
    return issues


def _registry_approval_issues(registry: Mapping[str, Any], approved_at: object) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    approval_time = _parse_datetime(approved_at, path="$.approved_at", issues=issues)
    registry_time = _parse_datetime(
        registry.get("issued_at"),
        path="$.reviewer_registry.issued_at",
        issues=issues,
    )
    if approval_time is not None and registry_time is not None and registry_time > approval_time:
        issues.append(ReviewIssue("$.approved_at", "APPROVAL_BEFORE_REGISTRY_ISSUANCE", "approval cannot rely on a reviewer registry issued later"))
    return issues


def build_snapshot(manifest: Mapping[str, Any], reviews: list[Mapping[str, Any]], reviewer_registry: Mapping[str, Any], *, approved_at: str, published_by: str, manifest_digest: str | None = None, registry_digest: str | None = None) -> dict[str, Any]:
    """Construct a deterministic approval overlay without mutating M5 records."""

    artifacts = {str(item["role"]).lower(): item["sha256"] for item in manifest["artifacts"]}
    authorities = _reviewer_index(reviewer_registry)
    snapshot: dict[str, Any] = {
        "schema_version": "2.0",
        "record_type": "curriculum_approval_snapshot",
        "status": "APPROVED",
        "approval_scope": "M5_ARCHITECTURE_REFERENCED_TAXONOMY_AND_REVIEWED_ANNOTATIONS",
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": manifest_digest or sha256_json(manifest),
        "reviewer_registry_id": reviewer_registry["registry_id"],
        "reviewer_registry_sha256": registry_digest or sha256_json(reviewer_registry),
        "curriculum_version": manifest["curriculum_version"],
        "taxonomy_version": manifest["taxonomy_version"],
        "source_registry": copy.deepcopy(manifest["source_registry"]),
        "artifact_hashes": artifacts,
        "approved_taxonomy_records": copy.deepcopy(manifest["taxonomy_scope"]),
        "reviewed_annotation_records": copy.deepcopy(manifest["annotation_scope"]),
        "reviews": [
            {
                "review_role": review["review_role"],
                "review_id": review["review_id"],
                "reviewer_id": review["reviewer"]["reviewer_id"],
                "identity_evidence_sha256": sha256_json(authorities[review["reviewer"]["reviewer_id"]]["identity_evidence"]),
                "sha256": sha256_json(review),
            }
            for review in reviews
        ],
        "approved_at": approved_at,
        "published_by": published_by,
        "source_bundle_policy": {
            "m5_records_remain_unchanged": True,
            "taxonomy_statuses_remain_draft": True,
            "lesson_outlines_remain_outline_only": True,
            "snapshot_contains_generated_lesson_content": False,
        },
    }
    snapshot["snapshot_id"] = content_identity("m5snapshot", snapshot, "snapshot_id")
    return snapshot


def _review_issue_at(issue: ReviewIssue, index: int) -> ReviewIssue:
    if issue.path == "$.review":
        path = f"$.reviews[{index}]"
    elif issue.path.startswith("$.review."):
        path = f"$.reviews[{index}]{issue.path[len('$.review'):]}"
    else:
        path = issue.path
    return ReviewIssue(path, issue.code, issue.message)


def publish_approval(
    destination: Path,
    bundle: CurriculumBundle,
    manifest: Mapping[str, Any],
    review_submissions: Iterable[Mapping[str, Any]],
    reviewer_registry: Mapping[str, Any],
    *,
    source_registry: Mapping[str, Any],
    source_registry_path: Path,
    approved_at: str,
    published_by: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Validate and atomically publish an immutable M5 approval bundle."""

    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable destination already exists: {destination}")
    issues = list(
        validate_manifest(
            manifest,
            bundle,
            source_registry,
            source_registry_path=source_registry_path,
        )
    )
    issues.extend(validate_reviewer_registry(reviewer_registry))
    if _is_blank(published_by):
        issues.append(ReviewIssue("$.published_by", "BLANK_VALUE", "published_by cannot contain only whitespace"))
    if issues:
        raise ReviewValidationError(issues)
    manifest_digest = sha256_json(manifest)
    registry_digest = sha256_json(reviewer_registry)
    reviews: list[dict[str, Any]] = []
    for index, submission in enumerate(review_submissions):
        if not isinstance(submission, Mapping):
            issues.append(ReviewIssue(f"$.reviews[{index}]", "SCHEMA_INVALID", "review submission must be an object"))
            continue
        normalized = normalize_review_submission(submission)
        input_schema = "curriculum-independent-review" if "review_id" in normalized else "curriculum-independent-review-draft"
        issues.extend(
            ReviewIssue(f"$.reviews[{index}]{issue.path[len('$.review'):]}", issue.code, issue.message)
            for issue in _schema_issues(normalized, input_schema, "$.review")
        )
        try:
            review = finalize_review(normalized)
        except ReviewValidationError as error:
            issues.extend(ReviewIssue(f"$.reviews[{index}]{issue.path[1:]}", issue.code, issue.message) for issue in error.issues)
            continue
        reviews.append(review)
        issues.extend(
            _review_issue_at(issue, index)
            for issue in validate_review(
                review,
                manifest,
                reviewer_registry,
                manifest_digest=manifest_digest,
            )
        )
    issues.extend(
        _approval_issues(
            reviews,
            approved_at=approved_at,
            observed_at=observed_at,
        )
    )
    issues.extend(_registry_approval_issues(reviewer_registry, approved_at))
    taxonomy_scope = manifest.get("taxonomy_scope")
    taxonomy_ids = [
        record["id"]
        for record in taxonomy_scope
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    ] if isinstance(taxonomy_scope, list) else []
    annotation_scope = manifest.get("annotation_scope")
    annotation_ids = [
        record["id"]
        for record in annotation_scope
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    ] if isinstance(annotation_scope, list) else []
    issues.extend(
        _source_chronology_issues(
            source_registry,
            bundle.taxonomy,
            [*taxonomy_ids, *annotation_ids],
            reviews=reviews,
            approved_at=approved_at,
        )
    )
    if issues:
        raise ReviewValidationError(issues)
    snapshot = build_snapshot(manifest, reviews, reviewer_registry, approved_at=approved_at, published_by=published_by, manifest_digest=manifest_digest, registry_digest=registry_digest)
    schema_issues = _schema_issues(snapshot, "curriculum-approval-snapshot", "$.snapshot")
    if schema_issues:
        raise ReviewValidationError(schema_issues)
    files = {
        "manifest.json": dict(manifest),
        "review-linguistic.json": reviews[0],
        "review-pedagogical.json": reviews[1],
        "reviewer-registry.json": dict(reviewer_registry),
        "source-registry.json": dict(source_registry),
        "snapshot.json": snapshot,
    }
    publish_bundle(destination, files)
    return snapshot


def verify_snapshot_bundle(
    directory: Path,
    bundle: CurriculumBundle,
    reviewer_registry: Mapping[str, Any],
    *,
    source_registry: Mapping[str, Any],
    source_registry_path: Path,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Verify a published directory against current M5 and independent authorities."""

    expected_names = {
        "manifest.json",
        "review-linguistic.json",
        "review-pedagogical.json",
        "reviewer-registry.json",
        "source-registry.json",
        "snapshot.json",
    }
    actual_names = {path.name for path in directory.iterdir()} if directory.is_dir() else set()
    issues: list[ReviewIssue] = []
    if actual_names != expected_names:
        issues.append(ReviewIssue("$.bundle", "BUNDLE_MEMBERS", f"expected exactly {sorted(expected_names)!r}, found {sorted(actual_names)!r}"))
        raise ReviewValidationError(issues)
    manifest = load_strict_document(directory / "manifest.json")
    reviews = [load_strict_document(directory / "review-linguistic.json"), load_strict_document(directory / "review-pedagogical.json")]
    retained_registry = load_strict_document(directory / "reviewer-registry.json")
    retained_source_registry = load_strict_document(directory / "source-registry.json")
    snapshot = load_strict_document(directory / "snapshot.json")
    approved_records = snapshot.get("approved_taxonomy_records")
    approved_ids = frozenset(
        record["id"]
        for record in approved_records
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    ) if isinstance(approved_records, list) else frozenset()
    reviewed_annotations = snapshot.get("reviewed_annotation_records")
    annotation_ids = frozenset(
        record["id"]
        for record in reviewed_annotations
        if isinstance(record, Mapping) and isinstance(record.get("id"), str)
    ) if isinstance(reviewed_annotations, list) else frozenset()
    reviewed_record_ids = approved_ids | annotation_ids
    strict_result = validate_bundle(bundle, require_approved_taxonomy=True, externally_approved_taxonomy_ids=approved_ids, required_taxonomy_ids=approved_ids)
    source_issues = tuple(issue for issue in strict_result.issues if issue.code != "APPROVED_TAXONOMY_REQUIRED")
    issues.extend(
        validate_manifest(
            manifest,
            bundle,
            source_registry,
            source_registry_path=source_registry_path,
            _source_prevalidated=not source_issues,
        )
    )
    issues.extend(ReviewIssue(issue.path, f"STRICT_M5_{issue.code}", issue.message) for issue in strict_result.issues)
    issues.extend(
        validate_source_registry(
            retained_source_registry,
            bundle.taxonomy,
            required_taxonomy_ids=reviewed_record_ids,
        )
    )
    issues.extend(validate_reviewer_registry(reviewer_registry))
    issues.extend(validate_reviewer_registry(retained_registry))
    manifest_digest = _safe_hash(manifest, path="$.manifest", issues=issues)
    registry_digest = _safe_hash(reviewer_registry, path="$.reviewer_registry", issues=issues)
    if retained_registry != reviewer_registry:
        issues.append(ReviewIssue("$.reviewer_registry", "REVIEWER_REGISTRY_MISMATCH", "retained registry does not equal the independently loaded trusted registry"))
    if retained_source_registry != source_registry:
        issues.append(ReviewIssue("$.source_registry", "SOURCE_REGISTRY_MISMATCH", "retained source registry does not equal the independently loaded current registry"))
    for index, review in enumerate(reviews):
        issues.extend(
            _review_issue_at(issue, index)
            for issue in validate_review(
                review,
                manifest,
                reviewer_registry,
                manifest_digest=manifest_digest,
            )
        )
    issues.extend(
        _approval_issues(
            reviews,
            approved_at=snapshot.get("approved_at"),
            observed_at=observed_at,
        )
    )
    issues.extend(_registry_approval_issues(reviewer_registry, snapshot.get("approved_at")))
    issues.extend(
        _source_chronology_issues(
            source_registry,
            bundle.taxonomy,
            reviewed_record_ids,
            reviews=reviews,
            approved_at=snapshot.get("approved_at"),
        )
    )
    issues.extend(_schema_issues(snapshot, "curriculum-approval-snapshot", "$.snapshot"))
    if _is_blank(snapshot.get("published_by")):
        issues.append(ReviewIssue("$.snapshot.published_by", "BLANK_VALUE", "published_by cannot contain only whitespace"))
    if issues:
        raise ReviewValidationError(issues)
    expected_snapshot = build_snapshot(
        manifest,
        reviews,
        reviewer_registry,
        approved_at=str(snapshot["approved_at"]),
        published_by=str(snapshot["published_by"]),
        manifest_digest=manifest_digest,
        registry_digest=registry_digest,
    )
    expected_snapshot_id = _safe_identity("m5snapshot", snapshot, "snapshot_id", path="$.snapshot.snapshot_id", issues=issues)
    if expected_snapshot_id is not None and snapshot.get("snapshot_id") != expected_snapshot_id:
        issues.append(ReviewIssue("$.snapshot.snapshot_id", "SNAPSHOT_ID_MISMATCH", "snapshot_id is not its canonical content identity"))
    if snapshot != expected_snapshot:
        issues.append(ReviewIssue("$.snapshot", "SNAPSHOT_BINDING_MISMATCH", "snapshot does not exactly bind the manifest, source registry, reviewer registry, and reviews"))
    if issues:
        raise ReviewValidationError(issues)
    return dict(snapshot)


# Development authority intentionally remains separate from the human/release snapshot.
DEVELOPMENT_SNAPSHOT_MEMBERS = ("manifest.json", "source-registry.json", "snapshot.json")


def build_development_snapshot(
    manifest: Mapping[str, Any],
    *,
    produced_at: str,
    tool_name: str = "english_master.curriculum_review",
    tool_version: str = "3.0",
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Build a hash-bound M5 development-only overlay without human claims."""

    artifacts = {str(item["role"]).lower(): item["sha256"] for item in manifest["artifacts"]}
    producing_tool: dict[str, Any] = {"name": tool_name, "version": tool_version}
    if git_commit is not None:
        producing_tool["git_commit"] = git_commit
    snapshot: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "curriculum_development_snapshot",
        "approval_tier": "DEVELOPMENT_APPROVED",
        "authority_scope": "M5_DEVELOPMENT_ONLY",
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": sha256_json(manifest),
        "curriculum_version": manifest["curriculum_version"],
        "taxonomy_version": manifest["taxonomy_version"],
        "source_registry": copy.deepcopy(manifest["source_registry"]),
        "artifact_hashes": artifacts,
        "approved_taxonomy_records": copy.deepcopy(manifest["taxonomy_scope"]),
        "reviewed_annotation_records": copy.deepcopy(manifest["annotation_scope"]),
        "produced_at": produced_at,
        "producing_tool": producing_tool,
        "source_bundle_policy": {
            "m5_records_remain_unchanged": True,
            "taxonomy_statuses_remain_draft": True,
            "lesson_outlines_remain_outline_only": True,
            "snapshot_contains_generated_lesson_content": False,
            "not_human_reviewed": True,
            "not_release_approved": True,
        },
    }
    snapshot["snapshot_id"] = content_identity("m5devsnapshot", snapshot, "snapshot_id")
    return snapshot


def publish_development_snapshot(
    destination: Path,
    bundle: CurriculumBundle,
    manifest: Mapping[str, Any],
    *,
    source_registry: Mapping[str, Any],
    source_registry_path: Path,
    produced_at: str,
    tool_name: str = "english_master.curriculum_review",
    tool_version: str = "3.0",
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Validate and atomically publish an M5 development-only snapshot."""

    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"immutable destination already exists: {destination}")
    issues = list(validate_manifest(manifest, bundle, source_registry, source_registry_path=source_registry_path))
    if issues:
        raise ReviewValidationError(issues)
    snapshot = build_development_snapshot(
        manifest, produced_at=produced_at, tool_name=tool_name, tool_version=tool_version, git_commit=git_commit,
    )
    issues = _schema_issues(snapshot, "curriculum-development-snapshot", "$.snapshot")
    if issues:
        raise ReviewValidationError(issues)
    publish_bundle(destination, {
        "manifest.json": dict(manifest),
        "source-registry.json": dict(source_registry),
        "snapshot.json": snapshot,
    })
    return snapshot


def verify_development_snapshot_bundle(
    directory: Path,
    bundle: CurriculumBundle,
    *,
    source_registry: Mapping[str, Any],
    source_registry_path: Path,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Reverify a development snapshot against current M5 inputs and registry."""

    actual_names = {path.name for path in directory.iterdir()} if directory.is_dir() else set()
    if actual_names != set(DEVELOPMENT_SNAPSHOT_MEMBERS):
        raise ReviewValidationError((ReviewIssue("$.bundle", "BUNDLE_MEMBERS", f"expected exactly {list(DEVELOPMENT_SNAPSHOT_MEMBERS)!r}, found {sorted(actual_names)!r}"),))
    manifest = load_strict_document(directory / "manifest.json")
    retained_source_registry = load_strict_document(directory / "source-registry.json")
    snapshot = load_strict_document(directory / "snapshot.json")
    issues = list(validate_manifest(manifest, bundle, source_registry, source_registry_path=source_registry_path))
    if retained_source_registry != source_registry:
        issues.append(ReviewIssue("$.source_registry", "SOURCE_REGISTRY_MISMATCH", "retained source registry does not equal independently loaded registry"))
    issues.extend(_schema_issues(snapshot, "curriculum-development-snapshot", "$.snapshot"))
    tool = snapshot.get("producing_tool")
    expected = build_development_snapshot(
        manifest,
        produced_at=str(snapshot.get("produced_at", "")),
        tool_name=str(tool.get("name", "")) if isinstance(tool, Mapping) else "",
        tool_version=str(tool.get("version", "")) if isinstance(tool, Mapping) else "",
        git_commit=tool.get("git_commit") if isinstance(tool, Mapping) and isinstance(tool.get("git_commit"), str) else None,
    )
    if snapshot != expected:
        issues.append(ReviewIssue("$.snapshot", "SNAPSHOT_BINDING_MISMATCH", "development snapshot does not exactly bind its manifest and policy"))
    produced = _parse_datetime(snapshot.get("produced_at"), path="$.snapshot.produced_at", issues=issues)
    observed = _parse_datetime(observed_at, path="$.observation_timestamp", issues=issues) if observed_at else None
    if produced is not None and observed is not None and produced > observed:
        issues.append(ReviewIssue("$.snapshot.produced_at", "FUTURE_APPROVAL", "produced_at cannot be later than verification clock"))
    if issues:
        raise ReviewValidationError(issues)
    return dict(snapshot)
