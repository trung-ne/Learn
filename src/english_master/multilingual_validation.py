"""Semantic checks for additive language-bound core contracts."""

from __future__ import annotations

from typing import Any

from english_master.schema_validation import SchemaValidationError, ValidationIssue, taxonomy_citation_issues, validate_instance


def validate_multilingual_source_registry(instance: dict[str, Any]) -> None:
    """Validate source scopes against the immutable legacy registry they wrap."""

    validate_instance(instance, "multilingual-source-registry-v1")
    registered = {source["source_id"] for source in instance["registry"]["sources"]}
    seen: set[str] = set()
    issues: list[ValidationIssue] = []
    for index, scope in enumerate(instance["language_scopes"]):
        source_id = scope["source_id"]
        if source_id not in registered:
            issues.append(ValidationIssue(f"$.language_scopes[{index}].source_id", "source scope references an unregistered source"))
        if source_id in seen:
            issues.append(ValidationIssue(f"$.language_scopes[{index}].source_id", "source language scope must be unique"))
        seen.add(source_id)
    if issues:
        raise SchemaValidationError(issues)


def validate_multilingual_taxonomy(
    instance: dict[str, Any], source_registry: dict[str, Any] | None = None
) -> None:
    """Validate taxonomy target-language coherence and optional citation scope."""

    validate_instance(instance, "multilingual-taxonomy-v1")
    target_language = instance["target_language_code"]
    taxonomy = instance["taxonomy"]
    issues: list[ValidationIssue] = []
    for index, sense in enumerate(taxonomy["vocabulary_senses"]):
        if sense["language"] != target_language:
            issues.append(ValidationIssue(f"$.taxonomy.vocabulary_senses[{index}].language", "vocabulary language must match taxonomy target language"))
    if source_registry is not None:
        validate_multilingual_source_registry(source_registry)
        scope_by_source = {entry["source_id"]: set(entry["language_codes"]) for entry in source_registry["language_scopes"]}
        for issue in taxonomy_citation_issues(taxonomy, source_registry["registry"]):
            issues.append(ValidationIssue(f"$.taxonomy{issue.instance_path.removeprefix('$')}", issue.message))
        for collection in ("concepts", "vocabulary_senses", "vietnamese_learner_annotations"):
            for record_index, record in enumerate(taxonomy.get(collection, [])):
                for evidence_index, evidence in enumerate(record.get("evidence_or_reference", [])):
                    source_id = evidence.get("source_id")
                    if source_id is not None and target_language not in scope_by_source.get(source_id, set()):
                        issues.append(
                            ValidationIssue(
                                f"$.taxonomy.{collection}[{record_index}].evidence_or_reference[{evidence_index}].source_id",
                                f"source {source_id!r} does not support taxonomy language {target_language!r}",
                            )
                        )
    if issues:
        raise SchemaValidationError(issues)
