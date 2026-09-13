"""Offline validation and source-governance gates for English Master JSON/YAML records."""

from __future__ import annotations

import argparse
import json
import re
import sys
import sysconfig
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from yaml.nodes import MappingNode

SCHEMA_FILENAMES: dict[str, str] = {
    "source": "source.schema.json",
    "source-registry": "source-registry.schema.json",
    "concept": "concept.schema.json",
    "vocabulary-sense": "vocabulary-sense.schema.json",
    "lesson": "lesson.schema.json",
    "exercise": "exercise.schema.json",
    "ai-practice-prompt": "ai-practice-prompt.schema.json",
    "ai-practice-authorization": "ai-practice-authorization.schema.json",
    "ai-practice-request": "ai-practice-request.schema.json",
    "ai-practice-prompt-artifact": "ai-practice-prompt-artifact.schema.json",
    "ai-practice-pilot-manifest": "ai-practice-pilot-manifest.schema.json",
    "ai-practice-audit": "ai-practice-audit.schema.json",
    "m15-knowledge-graph-node": "m15-knowledge-graph-node.schema.json",
    "m15-knowledge-graph-population": "m15-knowledge-graph-population.schema.json",
    "m15-knowledge-graph-run-manifest": "m15-knowledge-graph-run-manifest.schema.json",
    "m16-a1-curriculum-blueprint": "m16-a1-curriculum-blueprint.schema.json",
    "m16-a2-curriculum-blueprint": "m16-a2-curriculum-blueprint.schema.json",
    "m16-b1-curriculum-blueprint": "m16-b1-curriculum-blueprint.schema.json",
    "m16-b2-curriculum-blueprint": "m16-b2-curriculum-blueprint.schema.json",
    "m16-c1-curriculum-blueprint": "m16-c1-curriculum-blueprint.schema.json",
    "m16-c2-curriculum-blueprint": "m16-c2-curriculum-blueprint.schema.json",
    "b2-pilot-content-input": "b2-pilot-content-input.schema.json",
    "b2-pilot-lesson-packet": "b2-pilot-lesson-packet.schema.json",
    "b2-pilot-manifest": "b2-pilot-manifest.schema.json",
    "c1-pilot-content-input": "c1-pilot-content-input.schema.json",
    "c1-pilot-lesson-packet": "c1-pilot-lesson-packet.schema.json",
    "c1-pilot-manifest": "c1-pilot-manifest.schema.json",
    "c2-pilot-content-input": "c2-pilot-content-input.schema.json",
    "c2-pilot-lesson-packet": "c2-pilot-lesson-packet.schema.json",
    "c2-pilot-manifest": "c2-pilot-manifest.schema.json",
    "c2-full-allocation-v1": "c2-full-allocation-v1.schema.json",
    "c2-full-content-manifest-v1": "c2-full-content-manifest-v1.schema.json",
    "c2-full-content-unit-v1": "c2-full-content-unit-v1.schema.json",
    "c2-full-packet-v1": "c2-full-packet-v1.schema.json",
    "c2-full-run-manifest-v1": "c2-full-run-manifest-v1.schema.json",
    "c2-full-audit-report-v1": "c2-full-audit-report-v1.schema.json",
    "c2-full-sample-manifest-v1": "c2-full-sample-manifest-v1.schema.json",
    "cross-level-qa-request": "cross-level-qa-request.schema.json",
    "cross-level-qa-request-v2": "cross-level-qa-request-v2.schema.json",
    "cross-level-qa-report": "cross-level-qa-report.schema.json",
    "cross-level-qa-report-v2": "cross-level-qa-report-v2.schema.json",
    "cross-level-qa-sample": "cross-level-qa-sample.schema.json",
    "cross-level-qa-sample-v2": "cross-level-qa-sample-v2.schema.json",
    "assessment-build-request-v1": "assessment-build-request-v1.schema.json",
    "assessment-package-v1": "assessment-package-v1.schema.json",
    "assessment-run-manifest-v1": "assessment-run-manifest-v1.schema.json",
    "assessment-submission-v1": "assessment-submission-v1.schema.json",
    "learner-concept-state-v1": "learner-concept-state-v1.schema.json",
    "adaptive-review-state-v1": "adaptive-review-state-v1.schema.json",
    "adaptive-review-observation-v1": "adaptive-review-observation-v1.schema.json",
    "adaptive-review-plan-v1": "adaptive-review-plan-v1.schema.json",
    "m16-a1-unit": "m16-a1-unit.schema.json",
    "m16-a1-lesson": "m16-a1-lesson.schema.json",
    "m16-a1-review": "m16-a1-review.schema.json",
    "m16-a1-assessment-blueprint": "m16-a1-assessment-blueprint.schema.json",
    "m16-a1-blueprint-manifest": "m16-a1-blueprint-manifest.schema.json",
    "m16-a1-blueprint-validation": "m16-a1-blueprint-validation.schema.json",
    "m9-selection-manifest": "m9-selection-manifest.schema.json",
    "m9-selection-manifest-v2": "m9-selection-manifest-v2.schema.json",
    "m9-machine-qa-report": "m9-machine-qa-report.schema.json",
    "m9-ai-review": "m9-ai-review.schema.json",
    "m9-ai-review-v2": "m9-ai-review-v2.schema.json",
    "m9-ai-runner-request": "m9-ai-runner-request.schema.json",
    "m9-ai-runner-response": "m9-ai-runner-response.schema.json",
    "m9-ai-capture-wrapper": "m9-ai-capture-wrapper.schema.json",
    "m9-ai-capture-manifest": "m9-ai-capture-manifest.schema.json",
    "m9-development-batch": "m9-development-batch.schema.json",
    "m9-development-batch-v2": "m9-development-batch-v2.schema.json",
    "m9-human-review": "m9-human-review.schema.json",
    "m9-human-review-batch": "m9-human-review-batch.schema.json",
    "m9-release-decision": "m9-release-decision.schema.json",
    "m10-review-input": "m10-review-input.schema.json",
    "m10-finding-batch": "m10-finding-batch.schema.json",
    "m10-revision-request": "m10-revision-request.schema.json",
    "m10-governance-run": "m10-governance-run.schema.json",
    "m10-regeneration-capture": "m10-regeneration-capture.schema.json",
    "m10-candidate-attempt": "m10-candidate-attempt.schema.json",
    "m10-verification-receipt": "m10-verification-receipt.schema.json",
    "m10-rejection": "m10-rejection.schema.json",
    "m10-operational-failure": "m10-operational-failure.schema.json",
    "m10-supersession-index": "m10-supersession-index.schema.json",
    "m10-escalation": "m10-escalation.schema.json",
    "m10-revision-manifest": "m10-revision-manifest.schema.json",
    "m11-export-authorization": "m11-export-authorization.schema.json",
    "m11-export-manifest": "m11-export-manifest.schema.json",
    "m11-export-verification": "m11-export-verification.schema.json",
    "m11-export-batch-input": "m11-export-batch-input.schema.json",
    "m11-export-batch-manifest": "m11-export-batch-manifest.schema.json",
    "m11-export-batch-verification": "m11-export-batch-verification.schema.json",
    "m12-local-pilot-manifest": "m12-local-pilot-manifest.schema.json",
    "m13-local-pilot-transcript-batch": "m13-local-pilot-transcript-batch.schema.json",
    "media-source-authorization": "media-source-authorization.schema.json",
    "media-source-authorization-v2": "media-source-authorization-v2.schema.json",
    "media-evidence-external-capture": "media-evidence-external-capture.schema.json",
    "media-evidence-assessment": "media-evidence-assessment.schema.json",
    "media-acquisition-receipt": "media-acquisition-receipt.schema.json",
    "media-acquisition-receipt-v2": "media-acquisition-receipt-v2.schema.json",
    "media-asset-metadata": "media-asset-metadata.schema.json",
    "media-derivative-receipt": "media-derivative-receipt.schema.json",
    "media-quarantine-record": "media-quarantine-record.schema.json",
    "media-run-report": "media-run-report.schema.json",
    "media-run-report-v2": "media-run-report-v2.schema.json",
    "media-verification-report": "media-verification-report.schema.json",
    "media-verification-report-v2": "media-verification-report-v2.schema.json",
    "listening-transcription-fixture": "listening-transcription-fixture.schema.json",
    "listening-acoustic-fixture-sidecar": "listening-acoustic-fixture-sidecar.schema.json",
    "listening-difficulty-profile": "listening-difficulty-profile.schema.json",
    "listening-difficulty-run-manifest": "listening-difficulty-run-manifest.schema.json",
    "listening-difficulty-verification": "listening-difficulty-verification.schema.json",
    "m14-local-pilot-metrics": "m14-local-pilot-metrics.schema.json",
    "a1-pilot-content-input": "a1-pilot-content-input.schema.json",
    "a2-pilot-content-input": "a2-pilot-content-input.schema.json",
    "a2-pilot-lesson-packet": "a2-pilot-lesson-packet.schema.json",
    "a2-pilot-manifest": "a2-pilot-manifest.schema.json",
    "b1-pilot-content-input": "b1-pilot-content-input.schema.json",
    "b1-pilot-lesson-packet": "b1-pilot-lesson-packet.schema.json",
    "b1-pilot-manifest": "b1-pilot-manifest.schema.json",
    "a1-pilot-lesson-packet": "a1-pilot-lesson-packet.schema.json",
    "a1-pilot-manifest": "a1-pilot-manifest.schema.json",
    "a1-pilot-review": "a1-pilot-review.schema.json",
    "a1-pilot-review-summary": "a1-pilot-review-summary.schema.json",
    "a1-full-allocation-v2": "a1-full-allocation-v2.schema.json",
    "a1-full-content-unit-v2": "a1-full-content-unit-v2.schema.json",
    "a1-full-content-manifest-v2": "a1-full-content-manifest-v2.schema.json",
    "a1-full-packet-v2": "a1-full-packet-v2.schema.json",
    "a1-full-run-manifest-v2": "a1-full-run-manifest-v2.schema.json",
    "a1-full-audit-report-v2": "a1-full-audit-report-v2.schema.json",
    "a1-full-sample-manifest-v2": "a1-full-sample-manifest-v2.schema.json",
    "a2-full-allocation-v1": "a2-full-allocation-v1.schema.json",
    "a2-full-content-unit-v1": "a2-full-content-unit-v1.schema.json",
    "a2-full-content-manifest-v1": "a2-full-content-manifest-v1.schema.json",
    "a2-full-packet-v1": "a2-full-packet-v1.schema.json",
    "a2-full-run-manifest-v1": "a2-full-run-manifest-v1.schema.json",
    "a2-full-audit-report-v1": "a2-full-audit-report-v1.schema.json",
    "a2-full-sample-manifest-v1": "a2-full-sample-manifest-v1.schema.json",
    "b1-full-allocation-v1": "b1-full-allocation-v1.schema.json",
    "b1-full-content-unit-v1": "b1-full-content-unit-v1.schema.json",
    "b1-full-content-manifest-v1": "b1-full-content-manifest-v1.schema.json",
    "b1-full-packet-v1": "b1-full-packet-v1.schema.json",
    "b1-full-run-manifest-v1": "b1-full-run-manifest-v1.schema.json",
    "b1-full-audit-report-v1": "b1-full-audit-report-v1.schema.json",
    "b1-full-sample-manifest-v1": "b1-full-sample-manifest-v1.schema.json",
    "b2-full-allocation-v1": "b2-full-allocation-v1.schema.json",
    "b2-full-content-unit-v1": "b2-full-content-unit-v1.schema.json",
    "b2-full-content-manifest-v1": "b2-full-content-manifest-v1.schema.json",
    "b2-full-packet-v1": "b2-full-packet-v1.schema.json",
    "b2-full-run-manifest-v1": "b2-full-run-manifest-v1.schema.json",
    "b2-full-audit-report-v1": "b2-full-audit-report-v1.schema.json",
    "b2-full-sample-manifest-v1": "b2-full-sample-manifest-v1.schema.json",
    "c1-full-allocation-v1": "c1-full-allocation-v1.schema.json",
    "c1-full-content-unit-v1": "c1-full-content-unit-v1.schema.json",
    "c1-full-content-manifest-v1": "c1-full-content-manifest-v1.schema.json",
    "c1-full-packet-v1": "c1-full-packet-v1.schema.json",
    "c1-full-run-manifest-v1": "c1-full-run-manifest-v1.schema.json",
    "c1-full-audit-report-v1": "c1-full-audit-report-v1.schema.json",
    "c1-full-sample-manifest-v1": "c1-full-sample-manifest-v1.schema.json",
    "transcription-authorization": "transcription-authorization.schema.json",
    "transcription-authorization-v2": "transcription-authorization-v2.schema.json",
    "transcription-request": "transcription-request.schema.json",
    "transcription-request-v2": "transcription-request-v2.schema.json",
    "transcription-processing-plan-v2": "transcription-processing-plan-v2.schema.json",
    "transcript-artifact": "transcript-artifact.schema.json",
    "transcript-artifact-v2": "transcript-artifact-v2.schema.json",
    "transcription-stage-receipt": "transcription-stage-receipt.schema.json",
    "transcription-stage-receipt-v2": "transcription-stage-receipt-v2.schema.json",
    "transcription-run-manifest": "transcription-run-manifest.schema.json",
    "transcription-run-manifest-v2": "transcription-run-manifest-v2.schema.json",
    "transcription-verification": "transcription-verification.schema.json",
    "transcription-verification-v2": "transcription-verification-v2.schema.json",
    "taxonomy-concept": "taxonomy-concept.schema.json",
    "taxonomy-vocabulary-sense": "taxonomy-vocabulary-sense.schema.json",
    "vietnamese-learner-annotation": "vietnamese-learner-annotation.schema.json",
    "taxonomy": "taxonomy.schema.json",
    "coverage-matrix": "coverage-matrix.schema.json",
    "normalized-text": "normalized-text.schema.json",
    "ingestion-pilot-authorization": "ingestion-pilot-authorization.schema.json",
    "ingestion-pilot-receipt": "ingestion-pilot-receipt.schema.json",
    "ingestion-pilot-preparation-report": "ingestion-pilot-preparation-report.schema.json",
    "normalization-record": "normalization-record.schema.json",
    "duplicate-group": "duplicate-group.schema.json",
    "similarity-candidate": "similarity-candidate.schema.json",
    "semantic-review": "semantic-review.schema.json",
    "semantic-review-queue": "semantic-review-queue.schema.json",
    "normalization-report": "normalization-report.schema.json",
    "curriculum-manifest": "curriculum-manifest.schema.json",
    "curriculum-level-tier": "curriculum-level-tier.schema.json",
    "curriculum-unit": "curriculum-unit.schema.json",
    "curriculum-lesson-outline": "curriculum-lesson-outline.schema.json",
    "curriculum-review-node": "curriculum-review-node.schema.json",
    "curriculum-graph": "curriculum-graph.schema.json",
    "curriculum-coverage-roadmap": "curriculum-coverage-roadmap.schema.json",
    "curriculum-validation-report": "curriculum-validation-report.schema.json",
    "curriculum-review-manifest": "curriculum-review-manifest.schema.json",
    "curriculum-independent-review-draft": "curriculum-independent-review-draft.schema.json",
    "curriculum-independent-review": "curriculum-independent-review.schema.json",
    "curriculum-reviewer-registry": "curriculum-reviewer-registry.schema.json",
    "curriculum-approval-snapshot": "curriculum-approval-snapshot.schema.json",
    "curriculum-development-snapshot": "curriculum-development-snapshot.schema.json",
    "lesson-generation-authorization": "lesson-generation-authorization.schema.json",
    "lesson-generation-request": "lesson-generation-request.schema.json",
    "lesson-generation-audit": "lesson-generation-audit.schema.json",
    "lesson-generation-rejection": "lesson-generation-rejection.schema.json",
    "lesson-independent-review": "lesson-independent-review.schema.json",
    "lesson-batch-qa-report": "lesson-batch-qa-report.schema.json",
    "lesson-ai-review": "lesson-ai-review.schema.json",
    "lesson-development-batch": "lesson-development-batch.schema.json",
    "exercise-generation-authorization": "exercise-generation-authorization.schema.json",
    "exercise-generation-request": "exercise-generation-request.schema.json",
    "exercise-backend-candidate": "exercise-backend-candidate.schema.json",
    "exercise-set": "exercise-set.schema.json",
    "exercise-generation-audit": "exercise-generation-audit.schema.json",
    "exercise-generation-rejection": "exercise-generation-rejection.schema.json",
    "exercise-ai-review": "exercise-ai-review.schema.json",
    "exercise-development-batch": "exercise-development-batch.schema.json",
    "qa-engine-request": "qa-engine-request.schema.json",
    "qa-engine-model-invocation": "qa-engine-model-invocation.schema.json",
    "qa-engine-candidate-attempt": "qa-engine-candidate-attempt.schema.json",
    "qa-engine-stage-receipt": "qa-engine-stage-receipt.schema.json",
    "qa-engine-ai-review": "qa-engine-ai-review.schema.json",
    "qa-engine-rejection": "qa-engine-rejection.schema.json",
    "qa-engine-decision": "qa-engine-decision.schema.json",
    "qa-engine-operational-failure": "qa-engine-operational-failure.schema.json",
    "qa-engine-run-manifest": "qa-engine-run-manifest.schema.json",
}

SOURCE_PERMISSION_PATHS: dict[str, tuple[str, ...]] = {
    "fetch_source": ("access", "download_allowed"),
    "ingest_source": ("permissions", "ingest_allowed"),
    "store_source": ("permissions", "store_allowed"),
    "transform_source": ("permissions", "modify_allowed"),
    "redistribute_source": ("permissions", "redistribute_allowed"),
    "ingest_text": ("media_permissions", "text", "ingest_allowed"),
    "store_text": ("media_permissions", "text", "store_allowed"),
    "store_audio": ("media_permissions", "audio", "store_allowed"),
    "store_video": ("media_permissions", "video", "store_allowed"),
    "transform_text": ("media_permissions", "text", "transform_allowed"),
    "transform_audio": ("media_permissions", "audio", "transform_allowed"),
    "download_audio": ("media_permissions", "audio", "download_allowed"),
    "download_video": ("media_permissions", "video", "download_allowed"),
    "extract_audio": ("media_permissions", "video", "audio_extraction_allowed"),
    "generate_audio_transcript": ("media_permissions", "audio", "transcript_allowed"),
    "generate_video_transcript": ("media_permissions", "video", "transcript_allowed"),
    "generate_audio_timestamps": ("media_permissions", "audio", "timestamp_allowed"),
    "generate_video_timestamps": ("media_permissions", "video", "timestamp_allowed"),
    "create_audio_clip": ("media_permissions", "audio", "clip_allowed"),
    "create_video_clip": ("media_permissions", "video", "clip_allowed"),
    "redistribute_text": ("media_permissions", "text", "redistribute_allowed"),
    "redistribute_audio": ("media_permissions", "audio", "redistribute_allowed"),
    "redistribute_video": ("media_permissions", "video", "redistribute_allowed"),
    "redistribute_derived_text": ("media_permissions", "text", "derived_redistribution_allowed"),
    "redistribute_derived_audio": ("media_permissions", "audio", "derived_redistribution_allowed"),
    "redistribute_derived_video": ("media_permissions", "video", "derived_redistribution_allowed"),
    "use_text_for_exercises": ("media_permissions", "text", "exercise_allowed"),
    "use_audio_for_exercises": ("media_permissions", "audio", "exercise_allowed"),
    "use_video_for_exercises": ("media_permissions", "video", "exercise_allowed"),
}


@dataclass(frozen=True)
class ValidationIssue:
    """A stable, user-readable schema validation failure."""

    instance_path: str
    message: str


class SchemaValidationError(ValueError):
    """Raised when a record does not conform to its schema."""

    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__("; ".join(f"{issue.instance_path}: {issue.message}" for issue in self.issues))


class SourcePermissionError(ValueError):
    """Raised when a registered source cannot perform a requested operation."""


class DuplicateMappingKeyError(ValueError):
    """Raised when JSON or YAML contains an ambiguous duplicate mapping key."""


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateMappingKeyError(f"duplicate JSON mapping key: {key!r}")
        value[key] = item
    return value


class _UniqueKeySafeLoader(yaml.SafeLoader):
    """SafeLoader variant that rejects duplicate keys at every depth."""


def _construct_unique_yaml_mapping(
    loader: _UniqueKeySafeLoader,
    node: MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    value: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in value
        except TypeError as error:
            raise DuplicateMappingKeyError(
                f"unhashable YAML mapping key at line {key_node.start_mark.line + 1}"
            ) from error
        if duplicate:
            raise DuplicateMappingKeyError(
                f"duplicate YAML mapping key {key!r} at line {key_node.start_mark.line + 1}"
            )
        value[key] = loader.construct_object(value_node, deep=deep)
    return value


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_yaml_mapping,
)


def repository_root() -> Path:
    """Return the source-checkout root for repository-bound defaults."""

    source_root = Path(__file__).resolve().parents[2]
    if not (source_root / "schemas").is_dir():
        raise FileNotFoundError(
            "Repository root is unavailable outside a source checkout; "
            "pass repository-bound input paths explicitly"
        )
    return source_root


def schema_directory() -> Path:
    """Return authoritative checkout schemas or their installed wheel copies."""

    checkout_directory = Path(__file__).resolve().parents[2] / "schemas"
    if checkout_directory.is_dir():
        return checkout_directory
    installed_directory = (
        Path(sysconfig.get_path("data"))
        / "share"
        / "english-master"
        / "schemas"
    )
    if installed_directory.is_dir():
        return installed_directory
    raise FileNotFoundError(
        "Schema directory not found in the source checkout or installed package data: "
        f"{checkout_directory}; {installed_directory}"
    )


def _require_object(value: Any, path: Path) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Document must be an object: {path}")
    return value


def load_json(path: Path) -> dict[str, Any]:
    """Strictly load a JSON object and reject duplicate mapping keys."""

    with path.open("r", encoding="utf-8") as file:
        return _require_object(json.load(file, object_pairs_hook=_unique_json_object), path)


def load_document(path: Path) -> dict[str, Any]:
    """Strictly load a JSON or YAML object, selected by the filename suffix."""

    if path.suffix.lower() in {".yaml", ".yml"}:
        with path.open("r", encoding="utf-8") as file:
            return _require_object(yaml.load(file, Loader=_UniqueKeySafeLoader), path)
    return load_json(path)


def load_schemas() -> dict[str, dict[str, Any]]:
    """Load and metaschema-check every local JSON Schema."""

    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_directory().glob("*.schema.json")):
        schema = load_json(path)
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if not isinstance(schema_id, str) or not schema_id:
            raise ValueError(f"Schema has no nonempty $id: {path}")
        schemas[schema_id] = schema
    if not schemas:
        raise FileNotFoundError(f"No schemas found in {schema_directory()}")
    return schemas


@lru_cache(maxsize=1)
def _validation_schema_catalog() -> dict[str, dict[str, Any]]:
    """Cache the immutable in-process schema catalog used by validators."""

    return load_schemas()


def schema_registry(schemas: dict[str, dict[str, Any]] | None = None) -> Registry:
    """Build a registry that resolves only schemas loaded from this repository."""

    loaded_schemas = schemas if schemas is not None else load_schemas()
    return Registry().with_resources(
        (schema_id, Resource.from_contents(schema, default_specification=DRAFT202012))
        for schema_id, schema in loaded_schemas.items()
    )


def load_schema(schema_name: str) -> dict[str, Any]:
    """Load one supported core schema by its stable logical name."""

    try:
        filename = SCHEMA_FILENAMES[schema_name]
    except KeyError as error:
        supported = ", ".join(sorted(SCHEMA_FILENAMES))
        raise ValueError(f"Unknown schema {schema_name!r}. Supported schemas: {supported}") from error

    schema = load_json(schema_directory() / filename)
    Draft202012Validator.check_schema(schema)
    return schema


def _json_path(error: ValidationError) -> str:
    path = "$"
    for segment in error.absolute_path:
        if isinstance(segment, int):
            path += f"[{segment}]"
        else:
            path += f".{segment}"
    return path


def _registry_duplicate_id_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    sources = instance.get("sources")
    if not isinstance(sources, list):
        return []

    first_index_by_id: dict[str, int] = {}
    issues: list[ValidationIssue] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        if not isinstance(source_id, str):
            continue
        if source_id in first_index_by_id:
            first_index = first_index_by_id[source_id]
            issues.append(
                ValidationIssue(
                    instance_path=f"$.sources[{index}].source_id",
                    message=f"duplicate source_id {source_id!r}; first declared at $.sources[{first_index}].source_id",
                )
            )
        else:
            first_index_by_id[source_id] = index
    return issues


def _duplicate_id_issues(
    records: Any, collection_path: str, id_field: str = "id"
) -> list[ValidationIssue]:
    if not isinstance(records, list):
        return []

    first_index_by_id: dict[str, int] = {}
    issues: list[ValidationIssue] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        record_id = record.get(id_field)
        if not isinstance(record_id, str):
            continue
        if record_id in first_index_by_id:
            first_index = first_index_by_id[record_id]
            issues.append(
                ValidationIssue(
                    instance_path=f"{collection_path}[{index}].{id_field}",
                    message=(
                        f"duplicate {id_field} {record_id!r}; first declared at "
                        f"{collection_path}[{first_index}].{id_field}"
                    ),
                )
            )
        else:
            first_index_by_id[record_id] = index
    return issues


def _word_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")


def _concept_graph_issues(concepts: Any) -> list[ValidationIssue]:
    if not isinstance(concepts, list):
        return []

    index_by_id = {
        concept["id"]: index
        for index, concept in enumerate(concepts)
        if isinstance(concept, dict) and isinstance(concept.get("id"), str)
    }
    issues: list[ValidationIssue] = []
    graph: dict[str, list[str]] = {concept_id: [] for concept_id in index_by_id}

    for index, concept in enumerate(concepts):
        if not isinstance(concept, dict):
            continue
        concept_id = concept.get("id")
        prerequisites = concept.get("prerequisites")
        if isinstance(prerequisites, list) and isinstance(concept_id, str):
            for reference_index, target_id in enumerate(prerequisites):
                if not isinstance(target_id, str):
                    continue
                if target_id not in index_by_id:
                    issues.append(
                        ValidationIssue(
                            f"$.concepts[{index}].prerequisites[{reference_index}]",
                            f"unknown concept prerequisite {target_id!r}",
                        )
                    )
                else:
                    graph.setdefault(concept_id, []).append(target_id)

        relationships = concept.get("related_concepts")
        if isinstance(relationships, list):
            for relationship_index, relationship in enumerate(relationships):
                if not isinstance(relationship, dict):
                    continue
                target_id = relationship.get("target_id")
                if isinstance(target_id, str) and target_id not in index_by_id:
                    issues.append(
                        ValidationIssue(
                            f"$.concepts[{index}].related_concepts[{relationship_index}].target_id",
                            f"unknown related concept {target_id!r}",
                        )
                    )
                elif target_id == concept_id:
                    issues.append(
                        ValidationIssue(
                            f"$.concepts[{index}].related_concepts[{relationship_index}].target_id",
                            "a concept relationship cannot target itself",
                        )
                    )

    state: dict[str, int] = {}
    stack: list[str] = []
    reported_cycles: set[tuple[str, ...]] = set()

    def visit(concept_id: str) -> None:
        state[concept_id] = 1
        stack.append(concept_id)
        for prerequisite_id in graph.get(concept_id, []):
            if state.get(prerequisite_id, 0) == 0:
                visit(prerequisite_id)
            elif state.get(prerequisite_id) == 1:
                start = stack.index(prerequisite_id)
                cycle = tuple(stack[start:] + [prerequisite_id])
                if cycle not in reported_cycles:
                    reported_cycles.add(cycle)
                    issues.append(
                        ValidationIssue(
                            f"$.concepts[{index_by_id[concept_id]}].prerequisites",
                            f"prerequisite cycle detected: {' -> '.join(cycle)}",
                        )
                    )
        stack.pop()
        state[concept_id] = 2

    for concept_id in index_by_id:
        if state.get(concept_id, 0) == 0:
            visit(concept_id)
    return issues


def _vocabulary_sense_issues(
    senses: Any, concept_ids: set[str]
) -> list[ValidationIssue]:
    if not isinstance(senses, list):
        return []

    issues = _duplicate_id_issues(senses, "$.vocabulary_senses")
    sense_ids = {
        sense["id"]
        for sense in senses
        if isinstance(sense, dict) and isinstance(sense.get("id"), str)
    }
    first_by_identity: dict[tuple[str, str, str, int], int] = {}
    for index, sense in enumerate(senses):
        if not isinstance(sense, dict):
            continue
        language = sense.get("language")
        lemma = sense.get("lemma")
        part_of_speech = sense.get("part_of_speech")
        sense_number = sense.get("sense_number")
        sense_id = sense.get("id")
        if (
            isinstance(language, str)
            and isinstance(lemma, str)
            and isinstance(part_of_speech, str)
            and isinstance(sense_number, int)
        ):
            identity = (language, lemma.casefold(), part_of_speech, sense_number)
            if identity in first_by_identity:
                issues.append(
                    ValidationIssue(
                        f"$.vocabulary_senses[{index}].sense_number",
                        "duplicate language/lemma/part_of_speech/sense_number identity; "
                        f"first declared at $.vocabulary_senses[{first_by_identity[identity]}]",
                    )
                )
            else:
                first_by_identity[identity] = index
            expected_id = f"vocab_{language}_{_word_slug(lemma)}_{sense_number:03d}"
            if isinstance(sense_id, str) and sense_id != expected_id:
                issues.append(
                    ValidationIssue(
                        f"$.vocabulary_senses[{index}].id",
                        f"sense ID must be {expected_id!r} for its language, lemma, and sense_number",
                    )
                )

        prerequisites = sense.get("prerequisites")
        if isinstance(prerequisites, list):
            for reference_index, target_id in enumerate(prerequisites):
                if isinstance(target_id, str) and target_id not in concept_ids:
                    issues.append(
                        ValidationIssue(
                            f"$.vocabulary_senses[{index}].prerequisites[{reference_index}]",
                            f"unknown concept prerequisite {target_id!r}",
                        )
                    )
        relationships = sense.get("relationships")
        if isinstance(relationships, list):
            for relationship_index, relationship in enumerate(relationships):
                if not isinstance(relationship, dict):
                    continue
                target_id = relationship.get("target_id")
                if isinstance(target_id, str) and target_id not in sense_ids:
                    issues.append(
                        ValidationIssue(
                            f"$.vocabulary_senses[{index}].relationships[{relationship_index}].target_id",
                            f"unknown vocabulary sense {target_id!r}",
                        )
                    )
                elif target_id == sense_id:
                    issues.append(
                        ValidationIssue(
                            f"$.vocabulary_senses[{index}].relationships[{relationship_index}].target_id",
                            "a vocabulary-sense relationship cannot target itself",
                        )
                    )
    return issues


def taxonomy_collection_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    """Return semantic graph and identity issues for one M2 taxonomy collection."""

    concepts = instance.get("concepts")
    concept_ids = {
        concept["id"]
        for concept in (concepts if isinstance(concepts, list) else [])
        if isinstance(concept, dict) and isinstance(concept.get("id"), str)
    }
    issues = _duplicate_id_issues(concepts, "$.concepts")
    issues.extend(_concept_graph_issues(concepts))
    issues.extend(_vocabulary_sense_issues(instance.get("vocabulary_senses"), concept_ids))

    annotations = instance.get("vietnamese_learner_annotations")
    issues.extend(_duplicate_id_issues(annotations, "$.vietnamese_learner_annotations"))
    vocabulary_ids = {
        sense["id"]
        for sense in (instance.get("vocabulary_senses") if isinstance(instance.get("vocabulary_senses"), list) else [])
        if isinstance(sense, dict) and isinstance(sense.get("id"), str)
    }
    if isinstance(annotations, list):
        for index, annotation in enumerate(annotations):
            if not isinstance(annotation, dict):
                continue
            target_type = annotation.get("target_type")
            target_id = annotation.get("target_id")
            expected_ids = concept_ids if target_type == "concept" else vocabulary_ids
            if isinstance(target_id, str) and target_id not in expected_ids:
                issues.append(
                    ValidationIssue(
                        f"$.vietnamese_learner_annotations[{index}].target_id",
                        f"unknown {target_type or 'annotation'} target {target_id!r}",
                    )
                )
    return sorted(issues, key=lambda issue: (issue.instance_path, issue.message))


def coverage_matrix_collection_issues(instance: dict[str, Any]) -> list[ValidationIssue]:
    """Return uniqueness and completeness issues for the six broad CEFR ranges."""

    rows = instance.get("rows")
    if not isinstance(rows, list):
        return []
    expected_ranges = [
        "A1.1-A1.2",
        "A2.1-A2.2",
        "B1.1-B1.2",
        "B2.1-B2.2",
        "C1.1-C1.2",
        "C2.1-C2.2",
    ]
    first_index_by_range: dict[str, int] = {}
    issues: list[ValidationIssue] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get("cefr_range"), str):
            continue
        cefr_range = row["cefr_range"]
        if cefr_range in first_index_by_range:
            issues.append(
                ValidationIssue(
                    f"$.rows[{index}].cefr_range",
                    f"duplicate cefr_range {cefr_range!r}; first declared at $.rows[{first_index_by_range[cefr_range]}].cefr_range",
                )
            )
        else:
            first_index_by_range[cefr_range] = index
    missing = [cefr_range for cefr_range in expected_ranges if cefr_range not in first_index_by_range]
    if missing:
        issues.append(ValidationIssue("$.rows", f"missing CEFR coverage ranges: {', '.join(missing)}"))
    return sorted(issues, key=lambda issue: (issue.instance_path, issue.message))


def _eligible_taxonomy_sources(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    validate_instance(registry, "source-registry")
    return {
        source["source_id"]: source
        for source in registry["sources"]
        if source["status"] in {"APPROVED", "REFERENCE_ONLY"}
        and source["permissions"]["reference_allowed"] is True
    }


def can_cite_for_taxonomy(registry: dict[str, Any], source_id: str) -> bool:
    """Return whether a registered source may be cited without authorizing ingestion."""

    try:
        return source_id in _eligible_taxonomy_sources(registry)
    except (SchemaValidationError, KeyError, TypeError, ValueError):
        return False


def _url_origin_path_and_query(value: str) -> tuple[str, str, int | None, str, str] | None:
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
        if not parsed.scheme or hostname is None:
            return None
        ascii_hostname = hostname.encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError):
        return None
    effective_port = port
    if effective_port is None:
        effective_port = {"http": 80, "https": 443}.get(parsed.scheme.lower())
    return parsed.scheme.lower(), ascii_hostname, effective_port, parsed.path or "/", parsed.query


def _url_matches_registered_prefix(url: str, prefix: str) -> bool:
    candidate = _url_origin_path_and_query(url)
    authority = _url_origin_path_and_query(prefix)
    if candidate is None or authority is None or candidate[:3] != authority[:3]:
        return False
    candidate_path = candidate[3]
    authority_path = authority[3]
    authority_query = authority[4]
    if authority_query:
        return candidate_path == authority_path and candidate[4] == authority_query
    authority_path = authority_path.rstrip("/")
    return (
        not authority_path
        or candidate_path == authority_path
        or candidate_path.startswith(f"{authority_path}/")
    )


def taxonomy_citation_issues(
    instance: dict[str, Any],
    registry: dict[str, Any],
    *,
    required_record_ids: Iterable[str] | None = None,
) -> list[ValidationIssue]:
    """Return source-identity, permission, and locator issues for taxonomy citations."""

    issues: list[ValidationIssue] = []
    try:
        eligible_sources = _eligible_taxonomy_sources(registry)
    except (SchemaValidationError, KeyError, TypeError, ValueError):
        eligible_sources = {}
    required_ids = frozenset(required_record_ids) if required_record_ids is not None else None
    for collection in ("concepts", "vocabulary_senses", "vietnamese_learner_annotations"):
        records = instance.get(collection)
        if not isinstance(records, list):
            continue
        for record_index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            record_id = record.get("id")
            if required_ids is not None and record_id not in required_ids:
                continue
            evidence = record.get("evidence_or_reference")
            if not isinstance(evidence, list):
                continue
            for evidence_index, reference in enumerate(evidence):
                if not isinstance(reference, dict):
                    continue
                path = f"$.{collection}[{record_index}].evidence_or_reference[{evidence_index}]"
                source_id = reference.get("source_id")
                if source_id is None:
                    if reference.get("kind") != "AUTHORED_PROTOTYPE":
                        issues.append(
                            ValidationIssue(
                                f"{path}.source_id",
                                "externally grounded taxonomy evidence must name a registered source",
                            )
                        )
                    continue
                source = eligible_sources.get(source_id) if isinstance(source_id, str) else None
                if source is None:
                    issues.append(
                        ValidationIssue(
                            f"{path}.source_id",
                            f"source {source_id!r} is not eligible for taxonomy citation",
                        )
                    )
                    continue
                citation_url = reference.get("citation_url")
                prefixes = source.get("taxonomy_reference_url_prefixes")
                if not isinstance(prefixes, list):
                    prefixes = [source.get("source_url")]
                if not isinstance(citation_url, str) or not any(
                    isinstance(prefix, str) and _url_matches_registered_prefix(citation_url, prefix)
                    for prefix in prefixes
                ):
                    issues.append(
                        ValidationIssue(
                            f"{path}.citation_url",
                            f"citation URL is outside the registered locator scope for source {source_id!r}",
                        )
                    )
    return issues



def validate_taxonomy_collection(
    instance: dict[str, Any], registry: dict[str, Any] | None = None
) -> None:
    """Schema-validate and semantically validate a complete M2 taxonomy."""

    validate_instance(instance, "taxonomy")
    if registry is not None:
        issues = taxonomy_citation_issues(instance, registry)
        if issues:
            raise SchemaValidationError(issues)


def validate_coverage_matrix_collection(instance: dict[str, Any]) -> None:
    """Schema-validate and semantically validate a complete M2 coverage matrix."""

    validate_instance(instance, "coverage-matrix")


@lru_cache(maxsize=None)
def _schema_validator(schema_name: str) -> Draft202012Validator:
    """Build each immutable local-schema validator once per process."""

    schemas = _validation_schema_catalog()
    return Draft202012Validator(
        load_schema(schema_name),
        registry=schema_registry(schemas),
        format_checker=FormatChecker(),
    )


def validation_issues(instance: dict[str, Any], schema_name: str) -> list[ValidationIssue]:
    """Return deterministically ordered issues for an instance and core schema."""

    validator = _schema_validator(schema_name)
    issues = [
        ValidationIssue(instance_path=_json_path(error), message=error.message)
        for error in validator.iter_errors(instance)
    ]
    if schema_name == "source-registry":
        issues.extend(_registry_duplicate_id_issues(instance))
    elif schema_name == "taxonomy":
        issues.extend(taxonomy_collection_issues(instance))
    elif schema_name == "coverage-matrix":
        issues.extend(coverage_matrix_collection_issues(instance))
    return sorted(issues, key=lambda issue: (issue.instance_path, issue.message))


def validate_instance(instance: dict[str, Any], schema_name: str) -> None:
    """Raise SchemaValidationError when an instance fails local schema validation."""

    issues = validation_issues(instance, schema_name)
    if issues:
        raise SchemaValidationError(issues)


def validate_file(path: Path, schema_name: str) -> None:
    """Load and validate one JSON or YAML file using a supported core schema."""

    validate_instance(load_document(path), schema_name)


def load_source_registry(path: Path) -> dict[str, Any]:
    """Load a valid source registry from its JSON or YAML representation."""

    registry = load_document(path)
    validate_instance(registry, "source-registry")
    return registry


def require_source_permission(
    registry: dict[str, Any], source_id: str, operation: str
) -> dict[str, Any]:
    """Return a source only when it is approved and grants *operation*."""

    if operation not in SOURCE_PERMISSION_PATHS:
        supported = ", ".join(sorted(SOURCE_PERMISSION_PATHS))
        raise ValueError(f"Unknown source operation {operation!r}. Supported operations: {supported}")

    validate_instance(registry, "source-registry")
    sources = registry["sources"]
    source = next((candidate for candidate in sources if candidate["source_id"] == source_id), None)
    if source is None:
        raise SourcePermissionError(f"Source {source_id!r} is not registered")
    if source["status"] != "APPROVED":
        raise SourcePermissionError(
            f"Source {source_id!r} has status {source['status']!r}; APPROVED is required for {operation}"
        )

    value: Any = source
    for key in SOURCE_PERMISSION_PATHS[operation]:
        value = value[key]
    if value is not True:
        raise SourcePermissionError(f"Source {source_id!r} does not permit {operation}")
    return source


def source_permission_allowed(registry: dict[str, Any], source_id: str, operation: str) -> bool:
    """Return whether an operation is permitted without exposing a permissive default."""

    try:
        require_source_permission(registry, source_id, operation)
    except (SchemaValidationError, SourcePermissionError, ValueError):
        return False
    return True


def can_ingest_text(registry: dict[str, Any], source_id: str) -> bool:
    """Return whether text ingestion is permitted for a source."""

    return source_permission_allowed(registry, source_id, "ingest_text")


def can_download_audio(registry: dict[str, Any], source_id: str) -> bool:
    """Return whether audio download is permitted for a source."""

    return source_permission_allowed(registry, source_id, "download_audio")


def can_download_video(registry: dict[str, Any], source_id: str) -> bool:
    """Return whether video download is permitted for a source."""

    return source_permission_allowed(registry, source_id, "download_video")


def can_extract_audio(registry: dict[str, Any], source_id: str) -> bool:
    """Return whether audio extraction from video is permitted for a source."""

    return source_permission_allowed(registry, source_id, "extract_audio")


def can_generate_transcript(registry: dict[str, Any], source_id: str, media_type: str) -> bool:
    """Return whether transcript generation is permitted for audio or video."""

    operation = {"audio": "generate_audio_transcript", "video": "generate_video_transcript"}.get(media_type)
    return operation is not None and source_permission_allowed(registry, source_id, operation)


def can_create_clip(registry: dict[str, Any], source_id: str, media_type: str) -> bool:
    """Return whether clip creation is permitted for audio or video."""

    operation = {"audio": "create_audio_clip", "video": "create_video_clip"}.get(media_type)
    return operation is not None and source_permission_allowed(registry, source_id, operation)


def can_redistribute_media(registry: dict[str, Any], source_id: str, media_type: str) -> bool:
    """Return whether original audio or video redistribution is permitted."""

    operation = {"audio": "redistribute_audio", "video": "redistribute_video"}.get(media_type)
    return operation is not None and source_permission_allowed(registry, source_id, operation)


def can_redistribute_derived_media(registry: dict[str, Any], source_id: str, media_type: str) -> bool:
    """Return whether derivatives of the named medium may be redistributed."""

    operation = {
        "text": "redistribute_derived_text",
        "audio": "redistribute_derived_audio",
        "video": "redistribute_derived_video",
    }.get(media_type)
    return operation is not None and source_permission_allowed(registry, source_id, operation)


def can_generate_timestamps(registry: dict[str, Any], source_id: str, media_type: str) -> bool:
    """Return whether timestamps may be generated for audio or video."""

    operation = {"audio": "generate_audio_timestamps", "video": "generate_video_timestamps"}.get(media_type)
    return operation is not None and source_permission_allowed(registry, source_id, operation)


def can_use_for_generated_exercises(registry: dict[str, Any], source_id: str, media_type: str) -> bool:
    """Return whether the named medium may support generated exercises."""

    operation = {
        "text": "use_text_for_exercises",
        "audio": "use_audio_for_exercises",
        "video": "use_video_for_exercises",
    }.get(media_type)
    return operation is not None and source_permission_allowed(registry, source_id, operation)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(description="Validate English Master JSON/YAML records offline.")
    parser.add_argument("--schema", required=True, choices=sorted(SCHEMA_FILENAMES))
    parser.add_argument(
        "--require-source-permission",
        nargs=2,
        metavar=("SOURCE_ID", "OPERATION"),
        help="Require an APPROVED source registry entry to grant an operation.",
    )
    parser.add_argument(
        "--source-registry",
        type=Path,
        help="Source registry used to verify taxonomy citation eligibility.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="JSON or YAML record files to validate")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the validation CLI and return a process exit status."""

    parser = build_parser()
    arguments = parser.parse_args(argv)
    if arguments.require_source_permission and arguments.schema != "source-registry":
        parser.error("--require-source-permission requires --schema source-registry")
    if arguments.source_registry and arguments.schema != "taxonomy":
        parser.error("--source-registry requires --schema taxonomy")

    source_registry = load_source_registry(arguments.source_registry) if arguments.source_registry else None
    failed = False
    for path in arguments.paths:
        try:
            instance = load_document(path)
            validate_instance(instance, arguments.schema)
            if arguments.schema == "taxonomy" and source_registry is not None:
                citation_issues = taxonomy_citation_issues(instance, source_registry)
                if citation_issues:
                    raise SchemaValidationError(citation_issues)
            if arguments.require_source_permission:
                source_id, operation = arguments.require_source_permission
                require_source_permission(instance, source_id, operation)
        except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError, SchemaValidationError, SourcePermissionError) as error:
            failed = True
            print(f"{path}: INVALID", file=sys.stderr)
            if isinstance(error, SchemaValidationError):
                for issue in error.issues:
                    print(f"  {issue.instance_path}: {issue.message}", file=sys.stderr)
            else:
                print(f"  {error}", file=sys.stderr)
        else:
            print(f"{path}: VALID")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
