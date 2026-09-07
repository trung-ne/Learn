from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from english_master.schema_validation import SCHEMA_FILENAMES, load_schemas, schema_directory, schema_registry


@pytest.fixture(scope="module")
def schemas() -> dict[str, dict[str, object]]:
    return load_schemas()


def test_all_schema_files_are_loaded_and_metaschema_valid(schemas: dict[str, dict[str, object]]) -> None:
    files = sorted(path.name for path in schema_directory().glob("*.schema.json"))
    assert files == [
        "ai-practice-audit.schema.json",
        "ai-practice-authorization.schema.json",
        "ai-practice-pilot-manifest.schema.json",
        "ai-practice-prompt-artifact.schema.json",
        "ai-practice-prompt.schema.json",
        "ai-practice-request.schema.json",
        "common.schema.json",
        "concept.schema.json",
        "coverage-matrix.schema.json",
        "curriculum-approval-snapshot.schema.json",
        "curriculum-common.schema.json",
        "curriculum-coverage-roadmap.schema.json",
        "curriculum-development-snapshot.schema.json",
        "curriculum-graph.schema.json",
        "curriculum-independent-review-draft.schema.json",
        "curriculum-independent-review.schema.json",
        "curriculum-lesson-outline.schema.json",
        "curriculum-level-tier.schema.json",
        "curriculum-manifest.schema.json",
        "curriculum-review-manifest.schema.json",
        "curriculum-review-node.schema.json",
        "curriculum-reviewer-registry.schema.json",
        "curriculum-unit.schema.json",
        "curriculum-validation-report.schema.json",
        "duplicate-group.schema.json",
        "exercise-ai-review.schema.json",
        "exercise-backend-candidate.schema.json",
        "exercise-development-batch.schema.json",
        "exercise-generation-audit.schema.json",
        "exercise-generation-authorization.schema.json",
        "exercise-generation-rejection.schema.json",
        "exercise-generation-request.schema.json",
        "exercise-set.schema.json",
        "exercise.schema.json",
        "ingestion-pilot-authorization.schema.json",
        "ingestion-pilot-preparation-report.schema.json",
        "ingestion-pilot-receipt.schema.json",
        "lesson-ai-review.schema.json",
        "lesson-batch-qa-report.schema.json",
        "lesson-development-batch.schema.json",
        "lesson-generation-audit.schema.json",
        "lesson-generation-authorization.schema.json",
        "lesson-generation-rejection.schema.json",
        "lesson-generation-request.schema.json",
        "lesson-independent-review.schema.json",
        "lesson.schema.json",
        "m10-candidate-attempt.schema.json",
        "m10-escalation.schema.json",
        "m10-finding-batch.schema.json",
        "m10-governance-run.schema.json",
        "m10-operational-failure.schema.json",
        "m10-regeneration-capture.schema.json",
        "m10-rejection.schema.json",
        "m10-review-input.schema.json",
        "m10-revision-manifest.schema.json",
        "m10-revision-request.schema.json",
        "m10-supersession-index.schema.json",
        "m10-verification-receipt.schema.json",
        "m11-export-authorization.schema.json",
        "m11-export-manifest.schema.json",
        "m11-export-verification.schema.json",
        "m9-ai-review.schema.json",
        "m9-development-batch.schema.json",
        "m9-human-review-batch.schema.json",
        "m9-human-review.schema.json",
        "m9-machine-qa-report.schema.json",
        "m9-release-decision.schema.json",
        "m9-selection-manifest.schema.json",
        "normalization-record.schema.json",
        "normalization-report.schema.json",
        "normalized-text.schema.json",
        "qa-engine-ai-review.schema.json",
        "qa-engine-candidate-attempt.schema.json",
        "qa-engine-decision.schema.json",
        "qa-engine-model-invocation.schema.json",
        "qa-engine-operational-failure.schema.json",
        "qa-engine-rejection.schema.json",
        "qa-engine-request.schema.json",
        "qa-engine-run-manifest.schema.json",
        "qa-engine-stage-receipt.schema.json",
        "semantic-review-queue.schema.json",
        "semantic-review.schema.json",
        "similarity-candidate.schema.json",
        "source-registry.schema.json",
        "source.schema.json",
        "taxonomy-concept.schema.json",
        "taxonomy-vocabulary-sense.schema.json",
        "taxonomy.schema.json",
        "vietnamese-learner-annotation.schema.json",
        "vocabulary-sense.schema.json",
    ]
    assert len(schemas) == len(files)
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)


def test_core_schemas_resolve_the_common_schema(schemas: dict[str, dict[str, object]]) -> None:
    registry = schema_registry(schemas)
    common_id = "https://english-master.local/schemas/common.schema.json"
    assert registry.contents(common_id) == schemas[common_id]
    for name, filename in SCHEMA_FILENAMES.items():
        schema = json.loads((schema_directory() / filename).read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, registry=registry)
        assert validator.schema["title"].startswith("English Master"), name


def test_source_status_model_is_exact() -> None:
    common = json.loads((schema_directory() / "common.schema.json").read_text(encoding="utf-8"))
    assert common["$defs"]["sourceStatus"]["enum"] == [
        "APPROVED",
        "REFERENCE_ONLY",
        "QUARANTINED",
        "REJECTED",
    ]
