from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path

import pytest

from english_master.curriculum_review import storage
from english_master.curriculum_review.canonical import canonical_json, content_identity, sha256_json
from english_master.curriculum_review.cli import main
from english_master.curriculum_review.loading import DuplicateMappingKeyError, load_strict_document
from english_master.curriculum_review.storage import PostCommitDurabilityError
from english_master.curriculum_review.workflow import (
    CHECKLIST_BY_ROLE,
    ReviewValidationError,
    build_manifest,
    finalize_review,
    publish_approval,
    validate_manifest,
    validate_review,
    validate_reviewer_registry,
    validate_source_registry,
    verify_snapshot_bundle,
)
from english_master.curriculum_validation.validator import CurriculumBundle, load_bundle
from english_master.schema_validation import SchemaValidationError, validate_instance

ROOT = Path(__file__).resolve().parents[1]
STRUCTURE = ROOT / "curriculum" / "structure.json"
SOURCE_REGISTRY_PATH = ROOT / "sources" / "registry.yaml"
SOURCE_REGISTRY = load_strict_document(SOURCE_REGISTRY_PATH)


@pytest.fixture(scope="module")
def bundle() -> CurriculumBundle:
    return load_bundle(STRUCTURE)


def build_bound_manifest(
    bundle: CurriculumBundle,
    source_registry: Mapping[str, object] = SOURCE_REGISTRY,
    *,
    source_registry_path: Path = SOURCE_REGISTRY_PATH,
) -> dict[str, object]:
    return build_manifest(
        bundle,
        source_registry,
        source_registry_path=source_registry_path,
    )


def validate_bound_manifest(
    manifest: Mapping[str, object],
    bundle: CurriculumBundle,
    source_registry: Mapping[str, object] = SOURCE_REGISTRY,
    *,
    source_registry_path: Path = SOURCE_REGISTRY_PATH,
):
    return validate_manifest(
        manifest,
        bundle,
        source_registry,
        source_registry_path=source_registry_path,
    )


def publish_bound_approval(
    destination: Path,
    bundle: CurriculumBundle,
    manifest: Mapping[str, object],
    review_submissions: Iterable[Mapping[str, object]],
    reviewer_registry: Mapping[str, object],
    *,
    source_registry: Mapping[str, object] = SOURCE_REGISTRY,
    source_registry_path: Path = SOURCE_REGISTRY_PATH,
    approved_at: str,
    published_by: str,
) -> dict[str, object]:
    return publish_approval(
        destination,
        bundle,
        manifest,
        review_submissions,
        reviewer_registry,
        source_registry=source_registry,
        source_registry_path=source_registry_path,
        approved_at=approved_at,
        published_by=published_by,
    )


def verify_bound_snapshot(
    directory: Path,
    bundle: CurriculumBundle,
    reviewer_registry: Mapping[str, object],
    *,
    source_registry: Mapping[str, object] = SOURCE_REGISTRY,
    source_registry_path: Path = SOURCE_REGISTRY_PATH,
) -> dict[str, object]:
    return verify_snapshot_bundle(
        directory,
        bundle,
        reviewer_registry,
        source_registry=source_registry,
        source_registry_path=source_registry_path,
    )


def reviewer_registry(*reviewer_ids: str) -> dict[str, object]:
    registry: dict[str, object] = {
        "schema_version": "1.0",
        "record_type": "curriculum_reviewer_registry",
        "issued_at": "2026-09-02T17:48:49Z",
        "issued_by": "synthetic-test-authority",
        "trust_policy": "EXTERNALLY_VERIFIED_IDENTITIES_V1",
        "reviewers": [
            {
                "reviewer_id": reviewer_id,
                "display_name": f"Test reviewer {reviewer_id}",
                "qualifications": ["Synthetic test fixture qualification"],
                "permitted_roles": ["LINGUISTIC", "PEDAGOGICAL"],
                "status": "VERIFIED",
                "identity_evidence": {
                    "evidence_id": f"evidence-{reviewer_id}",
                    "method": "MANUAL_ID_CHECK",
                    "issuer": "synthetic-test-authority",
                    "subject_id": reviewer_id,
                    "evidence_reference": f"test-only:{reviewer_id}",
                    "verified_at": "2026-09-02T17:48:48Z",
                    "verified_by": "synthetic-test-verifier",
                },
            }
            for reviewer_id in reviewer_ids
        ],
    }
    registry["registry_id"] = content_identity("m5reviewers", registry, "registry_id")
    return registry


def review_submission(manifest: dict[str, object], role: str, reviewer_id: str) -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "record_type": "curriculum_independent_review",
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": sha256_json(manifest),
        "review_role": role,
        "reviewer": {
            "reviewer_id": reviewer_id,
            "display_name": f"Test reviewer {reviewer_id}",
            "qualifications": ["Synthetic test fixture qualification"],
            "identity_evidence_id": f"evidence-{reviewer_id}",
            "independent_of_authorship": True,
            "conflicts_disclosed": False,
        },
        "reviewed_at": "2026-09-02T17:48:50Z",
        "decision": "APPROVE",
        "artifact_scope": ["STRUCTURE", "GRAPH", "COVERAGE", "TAXONOMY"],
        "taxonomy_scope": [record["id"] for record in manifest["taxonomy_scope"]],
        "annotation_scope": [record["id"] for record in manifest["annotation_scope"]],
        "checklist": [
            {"criterion": criterion, "result": "PASS", "notes": "Synthetic passing test fixture."}
            for criterion in CHECKLIST_BY_ROLE[role]
        ],
        "findings": [],
        "attestation": {
            "method": "HUMAN_REVIEW",
            "reviewed_exact_hash_bound_manifest_and_artifacts": True,
            "source_records_not_edited": True,
            "no_lesson_content_approved": True,
        },
    }


def changed_bundle(bundle: CurriculumBundle, *, structure=None) -> CurriculumBundle:
    return CurriculumBundle(
        structure=structure if structure is not None else copy.deepcopy(bundle.structure),
        graph=copy.deepcopy(bundle.graph),
        coverage=copy.deepcopy(bundle.coverage),
        taxonomy=copy.deepcopy(bundle.taxonomy),
        paths=bundle.paths,
    )


def test_streaming_hash_matches_canonical_json_bytes() -> None:
    value = {"unicode": "Tiếng Việt", "nested": [3, {"a": True}], "number": 1.25}
    assert sha256_json(value) == hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def test_strict_loader_rejects_duplicate_json_and_yaml_keys(tmp_path: Path) -> None:
    duplicate_json = tmp_path / "duplicate.json"
    duplicate_json.write_text('{"decision":"APPROVE","nested":{"decision":"REJECT","decision":"APPROVE"}}', encoding="utf-8")
    with pytest.raises(DuplicateMappingKeyError, match="duplicate JSON mapping key"):
        load_strict_document(duplicate_json)

    duplicate_yaml = tmp_path / "duplicate.yaml"
    duplicate_yaml.write_text("decision: APPROVE\nnested:\n  decision: REJECT\n  decision: APPROVE\n", encoding="utf-8")
    with pytest.raises(DuplicateMappingKeyError, match="duplicate YAML mapping key"):
        load_strict_document(duplicate_yaml)


def test_cli_rejects_duplicate_keys_in_m5_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    structure = tmp_path / "structure.json"
    structure.write_text('{"artifacts":{},"artifacts":{}}', encoding="utf-8")
    assert main(["prepare", str(structure), "--source-registry", str(SOURCE_REGISTRY_PATH), "--output", str(tmp_path / "packet")]) == 2
    assert "duplicate JSON mapping key" in capsys.readouterr().err
    assert not (tmp_path / "packet").exists()


def test_cli_rejects_duplicate_keys_in_source_registry(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text('schema_version: "1.0"\nschema_version: "2.0"\nsources: []\n', encoding="utf-8")
    assert main([
        "prepare", str(STRUCTURE), "--source-registry", str(registry),
        "--output", str(tmp_path / "packet"),
    ]) == 2
    assert "duplicate YAML mapping key" in capsys.readouterr().err
    assert not (tmp_path / "packet").exists()


def test_manifest_is_deterministic_strict_and_does_not_mutate_m5(bundle: CurriculumBundle) -> None:
    before = copy.deepcopy(bundle)
    first = build_bound_manifest(bundle)
    second = build_bound_manifest(bundle)
    assert first == second
    assert first["manifest_id"].startswith("m5manifest_")
    assert first["source_registry"] == {
        "logical_path": "../sources/registry.yaml",
        "schema_name": "source-registry",
        "schema_version": SOURCE_REGISTRY["schema_version"],
        "sha256": sha256_json(SOURCE_REGISTRY),
    }
    assert [item["role"] for item in first["artifacts"]] == ["STRUCTURE", "GRAPH", "COVERAGE", "TAXONOMY"]
    assert first["schema_version"] == "2.0"
    assert first["taxonomy_scope"] == sorted(first["taxonomy_scope"], key=lambda record: record["id"])
    assert {record["source_status"] for record in first["taxonomy_scope"]} == {"DRAFT"}
    assert first["annotation_scope"] == sorted(first["annotation_scope"], key=lambda record: record["id"])
    assert {record["source_status"] for record in first["annotation_scope"]} == {"DRAFT"}
    assert [record["id"] for record in first["annotation_scope"]] == sorted(
        annotation["id"]
        for annotation in bundle.taxonomy["vietnamese_learner_annotations"]
    )
    annotations_by_id = {
        annotation["id"]: annotation
        for annotation in bundle.taxonomy["vietnamese_learner_annotations"]
    }
    assert all(
        record["sha256"] == sha256_json(annotations_by_id[record["id"]])
        for record in first["annotation_scope"]
    )
    assert {
        record["id"] for record in first["taxonomy_scope"]
    }.isdisjoint(record["id"] for record in first["annotation_scope"])
    assert first["validation_policy"]["profile"] == "M5_INDEPENDENT_REVIEW_V2"
    assert first["validation_policy"]["required_checklists"] == {
        "LINGUISTIC": [
            "CEFR_ALIGNMENT",
            "LINGUISTIC_ACCURACY",
            "DEPENDENCY_SOUNDNESS",
            "VOCABULARY_SENSE_INTEGRITY",
            "VIETNAMESE_LEARNER_RELEVANCE",
        ],
        "PEDAGOGICAL": [
            "PEDAGOGICAL_SEQUENCE",
            "OBJECTIVE_COHERENCE",
            "SKILL_BALANCE",
            "REVIEW_SPIRAL",
            "ASSESSMENT_ALIGNMENT",
            "SCOPE_AND_HOURS_CREDIBILITY",
        ],
    }
    schema_paths = {
        binding["logical_path"]
        for binding in first["validation_policy"]["schema_bindings"]
    }
    assert {
        "schemas/common.schema.json",
        "schemas/source.schema.json",
        "schemas/curriculum-review-manifest.schema.json",
        "schemas/curriculum-independent-review.schema.json",
    } <= schema_paths
    assert first["source_bundle_policy"]["content_generation_permitted_by_manifest"] is False
    validate_instance(first, "curriculum-review-manifest")
    assert bundle == before


def test_manifest_schema_enforces_canonical_artifact_roles(
    bundle: CurriculumBundle,
) -> None:
    manifest = build_bound_manifest(bundle)
    malformed = copy.deepcopy(manifest)
    malformed["artifacts"][1] = copy.deepcopy(malformed["artifacts"][0])
    malformed["manifest_id"] = content_identity(
        "m5manifest",
        malformed,
        "manifest_id",
    )
    with pytest.raises(SchemaValidationError):
        validate_instance(malformed, "curriculum-review-manifest")


def test_manifest_paths_bind_actual_override_inputs(tmp_path: Path, bundle: CurriculumBundle) -> None:
    overridden = CurriculumBundle(
        structure=copy.deepcopy(bundle.structure),
        graph=copy.deepcopy(bundle.graph),
        coverage=copy.deepcopy(bundle.coverage),
        taxonomy=copy.deepcopy(bundle.taxonomy),
        paths=(
            tmp_path / "custom-structure.json",
            tmp_path / "overrides" / "custom-graph.json",
            tmp_path / "custom-coverage.json",
            tmp_path.parent / "external" / "custom-taxonomy.json",
        ),
    )
    for path, document in zip(
        overridden.paths,
        (
            overridden.structure,
            overridden.graph,
            overridden.coverage,
            overridden.taxonomy,
        ),
        strict=True,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document), encoding="utf-8")
    manifest = build_bound_manifest(overridden)
    assert [artifact["logical_path"] for artifact in manifest["artifacts"]] == [
        "custom-structure.json",
        "overrides/custom-graph.json",
        "custom-coverage.json",
        "../external/custom-taxonomy.json",
    ]
    assert manifest != build_bound_manifest(bundle)


def test_manifest_detects_semantic_artifact_drift(bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    structure = copy.deepcopy(bundle.structure)
    structure["scale_plan"]["estimated_total_hours"]["maximum"] += 1
    issues = validate_bound_manifest(manifest, changed_bundle(bundle, structure=structure))
    assert "STALE_MANIFEST" in {issue.code for issue in issues}


def test_manifest_binds_actual_source_registry_path(bundle: CurriculumBundle, tmp_path: Path) -> None:
    registry_path = tmp_path / "governance" / "registry.yaml"
    registry_path.parent.mkdir()
    registry_path.write_text(json.dumps(SOURCE_REGISTRY), encoding="utf-8")
    manifest = build_bound_manifest(
        bundle,
        source_registry_path=registry_path,
    )
    assert manifest["source_registry"]["logical_path"] == Path(
        os.path.relpath(registry_path.resolve(), start=bundle.paths[0].parent)
    ).as_posix()
    assert manifest != build_bound_manifest(bundle)


def test_manifest_rejects_missing_or_mislabeled_external_taxonomy_citations(
    bundle: CurriculumBundle,
) -> None:
    missing_source = changed_bundle(bundle)
    mediation = next(
        record
        for record in missing_source.taxonomy["concepts"]
        if record["id"] == "concept_mediation"
    )
    mediation["evidence_or_reference"][0].pop("source_id")
    with pytest.raises(ReviewValidationError) as captured:
        build_bound_manifest(missing_source)
    assert "TAXONOMY_SOURCE_INELIGIBLE" in {
        issue.code for issue in captured.value.issues
    }
    assert any("source_id" in issue.path for issue in captured.value.issues)

    mislabeled = changed_bundle(bundle)
    mislabeled.taxonomy["concepts"][0]["evidence_or_reference"][0][
        "citation_url"
    ] = "https://example.invalid/unregistered-reference"
    with pytest.raises(ReviewValidationError) as captured:
        build_bound_manifest(mislabeled)
    assert "TAXONOMY_SOURCE_INELIGIBLE" in {
        issue.code for issue in captured.value.issues
    }
    assert any("citation_url" in issue.path for issue in captured.value.issues)


def test_manifest_rejects_source_registry_value_path_mismatch(
    bundle: CurriculumBundle,
    tmp_path: Path,
) -> None:
    claimed_path = tmp_path / "different-registry.json"
    changed_registry = copy.deepcopy(SOURCE_REGISTRY)
    changed_registry["sources"][0]["review_notes"] += " Different authority."
    claimed_path.write_text(json.dumps(changed_registry), encoding="utf-8")
    with pytest.raises(ReviewValidationError) as captured:
        build_bound_manifest(
            bundle,
            SOURCE_REGISTRY,
            source_registry_path=claimed_path,
        )
    assert "SOURCE_REGISTRY_INPUT_MISMATCH" in {
        issue.code for issue in captured.value.issues
    }


@pytest.mark.parametrize("source_id", ["src_missing_source", "src_english_profile_evp"])
def test_manifest_rejects_unknown_or_quarantined_taxonomy_citations(
    bundle: CurriculumBundle,
    source_id: str,
) -> None:
    changed = changed_bundle(bundle)
    changed.taxonomy["concepts"][0]["evidence_or_reference"][0]["source_id"] = source_id
    with pytest.raises(ReviewValidationError) as captured:
        build_bound_manifest(changed)
    assert "TAXONOMY_SOURCE_INELIGIBLE" in {issue.code for issue in captured.value.issues}


def test_manifest_rejects_rejected_or_reference_denied_sources(bundle: CurriculumBundle) -> None:
    for mutation in ("REJECTED", "REFERENCE_DENIED"):
        registry = copy.deepcopy(SOURCE_REGISTRY)
        source = next(record for record in registry["sources"] if record["source_id"] == "src_cefr_companion_volume")
        if mutation == "REJECTED":
            source["status"] = "REJECTED"
        else:
            source["permissions"]["reference_allowed"] = False
        issues = validate_source_registry(registry, bundle.taxonomy)
        assert "TAXONOMY_SOURCE_INELIGIBLE" in {issue.code for issue in issues}
        with pytest.raises(ReviewValidationError) as captured:
            build_bound_manifest(bundle, registry)
        assert "TAXONOMY_SOURCE_INELIGIBLE" in {issue.code for issue in captured.value.issues}


@pytest.mark.parametrize(
    "citation_url",
    [
        "https://eric.ed.gov/?id=EJ000000",
        "https://eric.ed.gov/unregistered-path?id=EJ527841",
    ],
)
def test_manifest_enforces_record_specific_citation_query_scope(
    bundle: CurriculumBundle,
    citation_url: str,
) -> None:
    changed = changed_bundle(bundle)
    annotation = next(
        record
        for record in changed.taxonomy["vietnamese_learner_annotations"]
        if record["annotation_kind"] == "RESEARCH_CLAIM"
    )
    annotation["evidence_or_reference"][0]["citation_url"] = citation_url

    with pytest.raises(ReviewValidationError) as captured:
        build_bound_manifest(changed)

    assert "TAXONOMY_SOURCE_INELIGIBLE" in {
        issue.code for issue in captured.value.issues
    }
    assert any(
        "vietnamese_learner_annotations" in issue.path
        and "citation_url" in issue.path
        for issue in captured.value.issues
    )


def test_publish_rechecks_source_registry_binding_and_eligibility(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    reviews = [
        review_submission(manifest, "LINGUISTIC", "reviewer-l"),
        review_submission(manifest, "PEDAGOGICAL", "reviewer-p"),
    ]
    registry = copy.deepcopy(SOURCE_REGISTRY)
    source = next(record for record in registry["sources"] if record["source_id"] == "src_cefr_companion_volume")
    source["status"] = "REJECTED"
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(
            tmp_path / "blocked-source",
            bundle,
            manifest,
            reviews,
            authority,
            source_registry=registry,
            approved_at="2026-09-02T17:48:51Z",
            published_by="test-publisher",
        )
    assert "TAXONOMY_SOURCE_INELIGIBLE" in {
        issue.code for issue in captured.value.issues
    }
    assert not (tmp_path / "blocked-source").exists()

    drifted_registry = copy.deepcopy(SOURCE_REGISTRY)
    drifted_registry["sources"][0]["review_notes"] += " Synthetic prepublication drift."
    drifted_registry_path = tmp_path / "drifted-source-registry.json"
    drifted_registry_path.write_text(json.dumps(drifted_registry), encoding="utf-8")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(
            tmp_path / "blocked-drift",
            bundle,
            manifest,
            reviews,
            authority,
            source_registry=drifted_registry,
            source_registry_path=drifted_registry_path,
            approved_at="2026-09-02T17:48:51Z",
            published_by="test-publisher",
        )
    assert "STALE_MANIFEST" in {issue.code for issue in captured.value.issues}
    assert not (tmp_path / "blocked-drift").exists()


def test_manifest_rejects_status_mutation_anywhere_in_taxonomy(bundle: CurriculumBundle) -> None:
    changed = changed_bundle(bundle)
    changed.taxonomy["vietnamese_learner_annotations"][-1]["status"] = "APPROVED"
    with pytest.raises(ReviewValidationError) as captured:
        build_bound_manifest(changed)
    assert "SOURCE_STATUS_CHANGED" in {issue.code for issue in captured.value.issues}


def test_review_requires_exact_hash_scope_and_role_checklist(bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l")
    submission = review_submission(manifest, "LINGUISTIC", "reviewer-l")
    validate_instance(submission, "curriculum-independent-review-draft")
    review = finalize_review(submission)
    assert validate_review(review, manifest, authority) == ()
    assert validate_reviewer_registry(authority) == ()
    validate_instance(review, "curriculum-independent-review")

    stale = copy.deepcopy(review)
    stale["manifest_sha256"] = "0" * 64
    stale = finalize_review({key: value for key, value in stale.items() if key != "review_id"})
    assert "REVIEW_MANIFEST_HASH_MISMATCH" in {issue.code for issue in validate_review(stale, manifest, authority)}

    incomplete = copy.deepcopy(review)
    incomplete["checklist"] = incomplete["checklist"][:-1]
    incomplete = finalize_review({key: value for key, value in incomplete.items() if key != "review_id"})
    assert "CHECKLIST_MISMATCH" in {issue.code for issue in validate_review(incomplete, manifest, authority)}

    incomplete_annotations = copy.deepcopy(review)
    incomplete_annotations["annotation_scope"] = incomplete_annotations["annotation_scope"][:-1]
    incomplete_annotations = finalize_review({
        key: value
        for key, value in incomplete_annotations.items()
        if key != "review_id"
    })
    assert "INCOMPLETE_ANNOTATION_SCOPE" in {
        issue.code
        for issue in validate_review(incomplete_annotations, manifest, authority)
    }

    reordered_annotations = copy.deepcopy(review)
    reordered_annotations["annotation_scope"] = list(
        reversed(reordered_annotations["annotation_scope"])
    )
    reordered_annotations = finalize_review({
        key: value
        for key, value in reordered_annotations.items()
        if key != "review_id"
    })
    assert "INCOMPLETE_ANNOTATION_SCOPE" in {
        issue.code
        for issue in validate_review(reordered_annotations, manifest, authority)
    }


def test_review_ids_are_normalized_and_bound_to_external_identity(bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l")
    submission = review_submission(manifest, "LINGUISTIC", "reviewer-l")
    submission["reviewer"]["reviewer_id"] = "  REVIEWER-L  "
    submission["reviewer"]["identity_evidence_id"] = "  EVIDENCE-REVIEWER-L  "
    finalized = finalize_review(submission)
    assert finalized["reviewer"]["reviewer_id"] == "reviewer-l"
    assert finalized["reviewer"]["identity_evidence_id"] == "evidence-reviewer-l"
    assert validate_review(finalized, manifest, authority) == ()

    untrusted = reviewer_registry("reviewer-p")
    assert "UNTRUSTED_REVIEWER" in {issue.code for issue in validate_review(finalized, manifest, untrusted)}


def test_registry_rejects_duplicate_external_identity_subjects(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    authority["reviewers"][1]["identity_evidence"]["subject_id"] = "reviewer-l"
    authority["registry_id"] = content_identity("m5reviewers", authority, "registry_id")
    assert "DUPLICATE_IDENTITY_SUBJECT" in {issue.code for issue in validate_reviewer_registry(authority)}
    direct_review = finalize_review(
        review_submission(manifest, "LINGUISTIC", "reviewer-l")
    )
    assert "DUPLICATE_IDENTITY_SUBJECT" in {
        issue.code for issue in validate_review(direct_review, manifest, authority)
    }
    reviews = [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")]
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "duplicate-subject", bundle, manifest, reviews, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    assert "DUPLICATE_IDENTITY_SUBJECT" in {issue.code for issue in captured.value.issues}

    authority["reviewers"][1]["identity_evidence"]["issuer"] = "Other Test Authority"
    authority["registry_id"] = content_identity("m5reviewers", authority, "registry_id")
    assert "DUPLICATE_IDENTITY_SUBJECT" not in {issue.code for issue in validate_reviewer_registry(authority)}
    authority["reviewers"][1]["identity_evidence"]["issuer"] = "synthetic-test-authority"
    authority["reviewers"][1]["identity_evidence"]["subject_id"] = "Reviewer-L"
    authority["registry_id"] = content_identity("m5reviewers", authority, "registry_id")
    assert "DUPLICATE_IDENTITY_SUBJECT" not in {issue.code for issue in validate_reviewer_registry(authority)}


def test_review_and_approval_require_prior_identity_authority(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    authority["issued_at"] = "2026-09-02T17:48:50.5Z"
    authority["reviewers"][0]["identity_evidence"]["verified_at"] = "2026-09-02T17:48:50.25Z"
    authority["registry_id"] = content_identity("m5reviewers", authority, "registry_id")
    reviews = [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")]
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "late-authority", bundle, manifest, reviews, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    codes = {issue.code for issue in captured.value.issues}
    assert {"REVIEW_BEFORE_REGISTRY_ISSUANCE", "REVIEW_BEFORE_IDENTITY_VERIFICATION"} <= codes
    assert not any("]er_registry" in issue.path for issue in captured.value.issues)
    assert any(
        issue.code == "REVIEW_BEFORE_IDENTITY_VERIFICATION"
        and issue.path == "$.reviews[0].reviewed_at"
        for issue in captured.value.issues
    )

    authority["issued_at"] = "2026-09-02T17:48:52Z"
    authority["reviewers"][0]["identity_evidence"]["verified_at"] = "2026-09-02T17:48:48Z"
    authority["registry_id"] = content_identity("m5reviewers", authority, "registry_id")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "future-authority", bundle, manifest, reviews, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    assert "APPROVAL_BEFORE_REGISTRY_ISSUANCE" in {issue.code for issue in captured.value.issues}


@pytest.mark.parametrize(
    "unorderable_timestamp",
    ["2026-12-31T23:59:60Z", "2026-09-02T12:00:00-00:00"],
)
def test_rfc3339_timestamps_unsupported_for_chronology_fail_closed(
    tmp_path: Path,
    bundle: CurriculumBundle,
    unorderable_timestamp: str,
) -> None:
    manifest = build_bound_manifest(bundle)

    authority = reviewer_registry("reviewer-l", "reviewer-p")
    authority["issued_at"] = unorderable_timestamp
    authority["reviewers"][0]["identity_evidence"]["verified_at"] = unorderable_timestamp
    authority["registry_id"] = content_identity("m5reviewers", authority, "registry_id")
    registry_issues = validate_reviewer_registry(authority)
    assert {
        "$.reviewer_registry.issued_at",
        "$.reviewer_registry.reviewers[0].identity_evidence.verified_at",
    } <= {issue.path for issue in registry_issues if issue.code == "UNORDERABLE_TIMESTAMP"}

    authority = reviewer_registry("reviewer-l", "reviewer-p")
    linguistic = review_submission(manifest, "LINGUISTIC", "reviewer-l")
    linguistic["reviewed_at"] = unorderable_timestamp
    finalized = finalize_review(linguistic)
    review_issues = validate_review(finalized, manifest, authority)
    assert any(issue.code == "UNORDERABLE_TIMESTAMP" and issue.path == "$.review.reviewed_at" for issue in review_issues)

    reviews = [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")]
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "unorderable-approval", bundle, manifest, reviews, authority, approved_at=unorderable_timestamp, published_by="test-publisher")
    assert any(issue.code == "UNORDERABLE_TIMESTAMP" and issue.path == "$.approved_at" for issue in captured.value.issues)
    assert not (tmp_path / "unorderable-approval").exists()


def test_publish_and_verify_atomic_immutable_snapshot(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    submissions = [
        review_submission(manifest, "LINGUISTIC", "reviewer-l"),
        review_submission(manifest, "PEDAGOGICAL", "reviewer-p"),
    ]
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    output = tmp_path / "approved"
    snapshot = publish_bound_approval(output, bundle, manifest, submissions, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    assert sorted(path.name for path in output.iterdir()) == [
        "manifest.json",
        "review-linguistic.json",
        "review-pedagogical.json",
        "reviewer-registry.json",
        "snapshot.json",
        "source-registry.json",
    ]
    assert snapshot["source_bundle_policy"]["taxonomy_statuses_remain_draft"] is True
    assert snapshot["source_bundle_policy"]["snapshot_contains_generated_lesson_content"] is False
    approved_ids = {
        record["id"] for record in snapshot["approved_taxonomy_records"]
    }
    reviewed_annotation_ids = {
        record["id"] for record in snapshot["reviewed_annotation_records"]
    }
    assert reviewed_annotation_ids == {
        annotation["id"]
        for annotation in bundle.taxonomy["vietnamese_learner_annotations"]
    }
    assert approved_ids.isdisjoint(reviewed_annotation_ids)
    assert verify_bound_snapshot(output, bundle, authority) == snapshot
    original = (output / "snapshot.json").read_bytes()
    with pytest.raises(FileExistsError):
        publish_bound_approval(output, bundle, manifest, submissions, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    assert (output / "snapshot.json").read_bytes() == original
    assert not list(tmp_path.glob(".approved.*"))


def test_publication_rejects_same_reviewer_failed_check_and_blocking_finding(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    linguistic = review_submission(manifest, "LINGUISTIC", "same-reviewer")
    pedagogical = review_submission(manifest, "PEDAGOGICAL", "same-reviewer")
    pedagogical["checklist"][0]["result"] = "FAIL"
    pedagogical["decision"] = "REQUEST_CHANGES"
    pedagogical["findings"] = [{
        "finding_id": "finding_001",
        "severity": "MAJOR",
        "category": "sequence",
        "location": "$.lessons[0]",
        "description": "Synthetic blocking test finding.",
        "required_action": "Revise and obtain a new review.",
    }]
    authority = reviewer_registry("same-reviewer")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "blocked", bundle, manifest, [linguistic, pedagogical], authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    codes = {issue.code for issue in captured.value.issues}
    assert {"REVIEWERS_NOT_INDEPENDENT", "REVIEW_NOT_APPROVED", "CHECK_FAILED", "BLOCKING_FINDING"} <= codes
    assert not (tmp_path / "blocked").exists()


def test_whitespace_only_governance_fields_fail_semantically(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    authority["issued_by"] = "   "
    authority["registry_id"] = content_identity("m5reviewers", authority, "registry_id")
    assert "BLANK_VALUE" in {issue.code for issue in validate_reviewer_registry(authority)}

    authority = reviewer_registry("reviewer-l", "reviewer-p")
    linguistic = review_submission(manifest, "LINGUISTIC", "reviewer-l")
    linguistic["checklist"][0]["notes"] = "   "
    finalized = finalize_review(linguistic)
    assert "BLANK_VALUE" in {issue.code for issue in validate_review(finalized, manifest, authority)}
    pedagogical = review_submission(manifest, "PEDAGOGICAL", "reviewer-p")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "blank-publisher", bundle, manifest, [review_submission(manifest, "LINGUISTIC", "reviewer-l"), pedagogical], authority, approved_at="2026-09-02T17:48:51Z", published_by="   ")
    assert "BLANK_VALUE" in {issue.code for issue in captured.value.issues}


def test_malformed_checklists_and_finding_ids_collect_issues(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    linguistic = review_submission(manifest, "LINGUISTIC", "reviewer-l")
    linguistic["checklist"] = 42
    linguistic["findings"] = [{
        "finding_id": [],
        "severity": "INFO",
        "category": "test",
        "location": "$.test",
        "description": "Synthetic malformed identifier test.",
        "required_action": "None.",
    }]
    pedagogical = review_submission(manifest, "PEDAGOGICAL", "reviewer-p")
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "malformed", bundle, manifest, [linguistic, pedagogical], authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    codes = {issue.code for issue in captured.value.issues}
    assert {"SCHEMA_INVALID", "CHECKLIST_MISMATCH"} <= codes
    assert not (tmp_path / "malformed").exists()


def test_publication_rejects_approval_before_reviews(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    reviews = [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")]
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(tmp_path / "blocked-time", bundle, manifest, reviews, authority, approved_at="2026-09-02T17:48:49.5Z", published_by="test-publisher")
    assert "APPROVAL_BEFORE_REVIEW" in {issue.code for issue in captured.value.issues}
    assert not (tmp_path / "blocked-time").exists()


def test_fractional_second_chronology_is_exact(
    tmp_path: Path,
    bundle: CurriculumBundle,
) -> None:
    manifest = build_bound_manifest(bundle)
    reviews = [
        review_submission(manifest, "LINGUISTIC", "reviewer-l"),
        review_submission(manifest, "PEDAGOGICAL", "reviewer-p"),
    ]
    for review in reviews:
        review["reviewed_at"] = "2026-09-02T17:48:50.0000009Z"
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(
            tmp_path / "submicrosecond-ordering",
            bundle,
            manifest,
            reviews,
            authority,
            approved_at="2026-09-02T17:48:50.0000001Z",
            published_by="test-publisher",
        )
    assert "APPROVAL_BEFORE_REVIEW" in {
        issue.code for issue in captured.value.issues
    }


def test_future_approval_fails_closed(
    tmp_path: Path,
    bundle: CurriculumBundle,
) -> None:
    manifest = build_bound_manifest(bundle)
    reviews = [
        review_submission(manifest, "LINGUISTIC", "reviewer-l"),
        review_submission(manifest, "PEDAGOGICAL", "reviewer-p"),
    ]
    for review in reviews:
        review["reviewed_at"] = "2099-01-01T12:00:00Z"
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    authority["issued_at"] = "2099-01-01T10:00:00Z"
    for reviewer in authority["reviewers"]:
        reviewer["identity_evidence"]["verified_at"] = "2099-01-01T09:00:00Z"
    authority["registry_id"] = content_identity(
        "m5reviewers",
        authority,
        "registry_id",
    )
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(
            tmp_path / "future-approval",
            bundle,
            manifest,
            reviews,
            authority,
            approved_at="2099-01-01T13:00:00Z",
            published_by="test-publisher",
        )
    assert "FUTURE_APPROVAL" in {issue.code for issue in captured.value.issues}


def test_reviews_cannot_precede_cited_source_authority(
    tmp_path: Path,
    bundle: CurriculumBundle,
) -> None:
    source_registry = copy.deepcopy(SOURCE_REGISTRY)
    source = next(
        record
        for record in source_registry["sources"]
        if record["source_id"] == "src_cefr_companion_volume"
    )
    source["reviewed_at"] = "2026-09-02T17:48:50.5Z"
    registry_path = tmp_path / "source-registry.json"
    registry_path.write_text(json.dumps(source_registry), encoding="utf-8")
    manifest = build_bound_manifest(
        bundle,
        source_registry,
        source_registry_path=registry_path,
    )
    reviews = [
        review_submission(manifest, "LINGUISTIC", "reviewer-l"),
        review_submission(manifest, "PEDAGOGICAL", "reviewer-p"),
    ]
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    with pytest.raises(ReviewValidationError) as captured:
        publish_bound_approval(
            tmp_path / "late-source-authority",
            bundle,
            manifest,
            reviews,
            authority,
            source_registry=source_registry,
            source_registry_path=registry_path,
            approved_at="2026-09-02T17:48:51Z",
            published_by="test-publisher",
        )
    assert "REVIEW_BEFORE_SOURCE_AUTHORITY" in {
        issue.code for issue in captured.value.issues
    }


def test_verify_detects_tampered_review(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    submissions = [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")]
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    output = tmp_path / "approved"
    publish_bound_approval(output, bundle, manifest, submissions, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    path = output / "review-linguistic.json"
    review = json.loads(path.read_text(encoding="utf-8"))
    review["reviewer"]["display_name"] = "Tampered"
    path.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(ReviewValidationError) as captured:
        verify_bound_snapshot(output, bundle, authority)
    assert {"REVIEW_ID_MISMATCH", "REVIEWER_AUTHORITY_MISMATCH"} <= {issue.code for issue in captured.value.issues}


def test_verify_malformed_snapshot_returns_validation_issues(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    submissions = [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")]
    output = tmp_path / "approved"
    publish_bound_approval(output, bundle, manifest, submissions, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    snapshot_path = output / "snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot.pop("reviewer_registry_id")
    snapshot["approved_taxonomy_records"] = 7
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    with pytest.raises(ReviewValidationError) as captured:
        verify_bound_snapshot(output, bundle, authority)
    assert "SCHEMA_INVALID" in {issue.code for issue in captured.value.issues}


def test_verify_rejects_rehashed_annotation_scope_tampering(
    tmp_path: Path,
    bundle: CurriculumBundle,
) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    submissions = [
        review_submission(manifest, "LINGUISTIC", "reviewer-l"),
        review_submission(manifest, "PEDAGOGICAL", "reviewer-p"),
    ]
    output = tmp_path / "approved"
    publish_bound_approval(
        output,
        bundle,
        manifest,
        submissions,
        authority,
        approved_at="2026-09-02T17:48:51Z",
        published_by="test-publisher",
    )
    snapshot_path = output / "snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot["reviewed_annotation_records"][0]["sha256"] = "0" * 64
    snapshot["snapshot_id"] = content_identity(
        "m5snapshot",
        snapshot,
        "snapshot_id",
    )
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")

    with pytest.raises(ReviewValidationError) as captured:
        verify_bound_snapshot(output, bundle, authority)

    assert "SNAPSHOT_BINDING_MISMATCH" in {
        issue.code for issue in captured.value.issues
    }


def test_verify_requires_same_independent_reviewer_registry(tmp_path: Path, bundle: CurriculumBundle) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    submissions = [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")]
    output = tmp_path / "approved"
    publish_bound_approval(output, bundle, manifest, submissions, authority, approved_at="2026-09-02T17:48:51Z", published_by="test-publisher")
    changed_authority = copy.deepcopy(authority)
    changed_authority["issued_by"] = "different-trusted-authority"
    changed_authority["registry_id"] = content_identity("m5reviewers", changed_authority, "registry_id")
    with pytest.raises(ReviewValidationError) as captured:
        verify_bound_snapshot(output, bundle, changed_authority)
    assert "REVIEWER_REGISTRY_MISMATCH" in {issue.code for issue in captured.value.issues}


def test_verify_rejects_current_source_registry_drift_and_retained_tampering(
    tmp_path: Path,
    bundle: CurriculumBundle,
) -> None:
    manifest = build_bound_manifest(bundle)
    authority = reviewer_registry("reviewer-l", "reviewer-p")
    submissions = [
        review_submission(manifest, "LINGUISTIC", "reviewer-l"),
        review_submission(manifest, "PEDAGOGICAL", "reviewer-p"),
    ]
    output = tmp_path / "approved"
    snapshot = publish_bound_approval(
        output,
        bundle,
        manifest,
        submissions,
        authority,
        approved_at="2026-09-02T17:48:51Z",
        published_by="test-publisher",
    )
    assert snapshot["source_registry"] == manifest["source_registry"]

    changed_registry = copy.deepcopy(SOURCE_REGISTRY)
    changed_registry["sources"][0]["review_notes"] += " Synthetic drift."
    changed_registry_path = tmp_path / "changed-source-registry.json"
    changed_registry_path.write_text(json.dumps(changed_registry), encoding="utf-8")
    with pytest.raises(ReviewValidationError) as captured:
        verify_bound_snapshot(
            output,
            bundle,
            authority,
            source_registry=changed_registry,
            source_registry_path=changed_registry_path,
        )
    assert {"SOURCE_REGISTRY_MISMATCH", "STALE_MANIFEST"} <= {
        issue.code for issue in captured.value.issues
    }

    retained_path = output / "source-registry.json"
    retained = json.loads(retained_path.read_text(encoding="utf-8"))
    retained["sources"][0]["review_notes"] += " Synthetic retained tampering."
    retained_path.write_text(json.dumps(retained), encoding="utf-8")
    with pytest.raises(ReviewValidationError) as captured:
        verify_bound_snapshot(output, bundle, authority)
    assert "SOURCE_REGISTRY_MISMATCH" in {issue.code for issue in captured.value.issues}


def test_storage_checks_existing_destination_before_staging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output = tmp_path / "exists"
    output.mkdir()

    def unexpected_staging(*args: object, **kwargs: object) -> str:
        raise AssertionError("staging must not be created for an existing destination")

    monkeypatch.setattr(storage.tempfile, "mkdtemp", unexpected_staging)
    with pytest.raises(FileExistsError):
        storage.publish_bundle(output, {"value.json": {"value": 1}})


def test_storage_reports_parent_fsync_failure_after_commit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def failing_parent_fsync(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic parent fsync failure")

    monkeypatch.setattr(storage, "_fsync_directory", failing_parent_fsync)
    output = tmp_path / "published"
    with pytest.raises(PostCommitDurabilityError) as captured:
        storage.publish_bundle(output, {"value.json": {"value": 1}})
    assert captured.value.destination == output
    assert (output / "value.json").is_file()


def test_prepare_and_verify_cli_offline(tmp_path: Path, bundle: CurriculumBundle, capsys: pytest.CaptureFixture[str]) -> None:
    prepared = tmp_path / "prepared"
    assert main(["prepare", str(STRUCTURE), "--source-registry", str(SOURCE_REGISTRY_PATH), "--output", str(prepared)]) == 0
    assert "Prepared M5 review manifest" in capsys.readouterr().out
    assert main(["prepare", str(STRUCTURE), "--source-registry", str(SOURCE_REGISTRY_PATH), "--output", str(prepared)]) == 2
    assert "Publication failed" in capsys.readouterr().err

    manifest = json.loads((prepared / "manifest.json").read_text(encoding="utf-8"))
    linguistic = tmp_path / "linguistic.json"
    pedagogical = tmp_path / "pedagogical.json"
    linguistic.write_text(json.dumps(review_submission(manifest, "LINGUISTIC", "reviewer-l")), encoding="utf-8")
    pedagogical.write_text(json.dumps(review_submission(manifest, "PEDAGOGICAL", "reviewer-p")), encoding="utf-8")
    registry_path = tmp_path / "reviewer-registry.json"
    registry_path.write_text(json.dumps(reviewer_registry("reviewer-l", "reviewer-p")), encoding="utf-8")
    approved = tmp_path / "approved"
    assert main([
        "publish", str(STRUCTURE), "--manifest", str(prepared / "manifest.json"),
        "--linguistic-review", str(linguistic), "--pedagogical-review", str(pedagogical),
        "--reviewer-registry", str(registry_path),
        "--source-registry", str(SOURCE_REGISTRY_PATH),
        "--approved-at", "2026-09-02T17:48:51Z", "--published-by", "test-publisher", "--output", str(approved),
    ]) == 0
    assert main([
        "verify", str(STRUCTURE), "--snapshot", str(approved),
        "--reviewer-registry", str(registry_path),
        "--source-registry", str(SOURCE_REGISTRY_PATH),
    ]) == 0


def test_module_cli_prepare_runs_offline(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable, "-m", "english_master.curriculum_review", "prepare", str(STRUCTURE),
            "--source-registry", str(SOURCE_REGISTRY_PATH),
            "--output", str(tmp_path / "packet"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "Prepared M5 review manifest" in result.stdout
