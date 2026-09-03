from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from english_master.curriculum_review.canonical import content_identity, sha256_json
from english_master.curriculum_review.loading import load_strict_document
from english_master.curriculum_review.workflow import CHECKLIST_BY_ROLE, build_manifest, publish_approval
from english_master.curriculum_validation.validator import load_bundle
from english_master.lesson_generation import (
    CapturedLessonResponse,
    LessonGenerationAuthority,
    LessonGenerationRequest,
    LessonGenerator,
    MockLessonBackend,
    VerifiedM5Authority,
    build_authorization,
    build_request,
    sha256_text,
)
from english_master.lesson_generation import storage
from english_master.schema_validation import load_json, validate_instance

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "m6"
SOURCE_REGISTRY_PATH = ROOT / "sources" / "registry.yaml"
FIXED_NOW = datetime(2026, 9, 3, tzinfo=timezone.utc)


def fixture_candidate() -> dict:
    return load_json(FIXTURES / "approved-mock-lesson.json")


def reviewer_registry() -> dict:
    value: dict = {
        "schema_version": "1.0", "record_type": "curriculum_reviewer_registry",
        "issued_at": "2026-09-02T17:48:49Z", "issued_by": "synthetic-test-authority",
        "trust_policy": "EXTERNALLY_VERIFIED_IDENTITIES_V1",
        "reviewers": [],
    }
    for reviewer_id, role in (("reviewer-l", "LINGUISTIC"), ("reviewer-p", "PEDAGOGICAL")):
        value["reviewers"].append({
            "reviewer_id": reviewer_id, "display_name": f"Test reviewer {reviewer_id}",
            "qualifications": ["Synthetic test fixture qualification"], "permitted_roles": [role], "status": "VERIFIED",
            "identity_evidence": {"evidence_id": f"evidence-{reviewer_id}", "method": "MANUAL_ID_CHECK", "issuer": "synthetic-test-authority", "subject_id": reviewer_id, "evidence_reference": f"test-only:{reviewer_id}", "verified_at": "2026-09-02T17:48:48Z", "verified_by": "synthetic-test-verifier"},
        })
    value["registry_id"] = content_identity("m5reviewers", value, "registry_id")
    return value


def review_submission(manifest: dict, role: str, reviewer_id: str) -> dict:
    return {
        "schema_version": "2.0", "record_type": "curriculum_independent_review", "manifest_id": manifest["manifest_id"],
        "manifest_sha256": sha256_json(manifest), "review_role": role,
        "reviewer": {"reviewer_id": reviewer_id, "display_name": f"Test reviewer {reviewer_id}", "qualifications": ["Synthetic test fixture qualification"], "identity_evidence_id": f"evidence-{reviewer_id}", "independent_of_authorship": True, "conflicts_disclosed": False},
        "reviewed_at": "2026-09-02T17:48:50Z", "decision": "APPROVE", "artifact_scope": ["STRUCTURE", "GRAPH", "COVERAGE", "TAXONOMY"],
        "taxonomy_scope": [record["id"] for record in manifest["taxonomy_scope"]], "annotation_scope": [record["id"] for record in manifest["annotation_scope"]],
        "checklist": [{"criterion": criterion, "result": "PASS", "notes": "Synthetic passing test fixture."} for criterion in CHECKLIST_BY_ROLE[role]],
        "findings": [], "attestation": {"method": "HUMAN_REVIEW", "reviewed_exact_hash_bound_manifest_and_artifacts": True, "source_records_not_edited": True, "no_lesson_content_approved": True},
    }


@pytest.fixture()
def verified_m5(tmp_path: Path) -> VerifiedM5Authority:
    """Create a synthetic snapshot only to test the fail-closed verifier path."""
    bundle = load_bundle(ROOT / "curriculum" / "structure.json")
    source_registry = load_strict_document(SOURCE_REGISTRY_PATH)
    registry = reviewer_registry()
    manifest = build_manifest(bundle, source_registry, source_registry_path=SOURCE_REGISTRY_PATH)
    snapshot_dir = tmp_path / "snapshot"
    publish_approval(
        snapshot_dir, bundle, manifest,
        [review_submission(manifest, "LINGUISTIC", "reviewer-l"), review_submission(manifest, "PEDAGOGICAL", "reviewer-p")],
        registry, source_registry=source_registry, source_registry_path=SOURCE_REGISTRY_PATH,
        approved_at="2026-09-02T17:48:51Z", published_by="synthetic-test-publisher",
    )
    reviewer_path = tmp_path / "reviewer-authority.json"
    reviewer_path.write_text(json.dumps(registry), encoding="utf-8")
    return VerifiedM5Authority.from_files(ROOT / "curriculum" / "structure.json", snapshot_dir, SOURCE_REGISTRY_PATH, reviewer_path)


def authority_and_request(m5: VerifiedM5Authority, lesson_id: str = "A1-U01-L01") -> tuple[LessonGenerationAuthority, dict]:
    authorization = build_authorization(m5, [lesson_id])
    return LessonGenerationAuthority(m5=m5, authorization=authorization), build_request(m5, authorization, lesson_id)


def run(m5: VerifiedM5Authority, request: dict | None = None, candidate: dict | None = None, *, authority: LessonGenerationAuthority | None = None, **kwargs):
    selected_authority, default_request = authority_and_request(m5)
    backend = MockLessonBackend(fixture_candidate() if candidate is None else candidate, observed_at="2026-09-03T00:00:00Z")
    result = LessonGenerator(backend, authority or selected_authority, clock=lambda: FIXED_NOW).generate(LessonGenerationRequest.from_dict(request or default_request), **kwargs)
    return backend, result


def codes(result) -> set[str]:
    return {item["code"] for item in result.audit["unresolved_issues"]}


def test_snapshot_derived_generation_injects_runtime_provenance(verified_m5: VerifiedM5Authority) -> None:
    backend, result = run(verified_m5)
    assert result.accepted and backend.calls == 1
    assert result.lesson["id"] == "A1-U01-L01"
    assert result.lesson["generation_metadata"] == {
        "generator": "english_master.lesson_generation", "generator_version": "2.0", "prompt_version": "M6_LESSON_GENERATOR_v3",
        "generated_at": "2026-09-03T00:00:00Z", "curriculum_version": "20260903", "qa_status": "UNREVIEWED",
        "qa_notes": "Automated M6 structural checks passed; independent review remains required.",
    }
    assert result.audit["response_provenance"]["provider"] == "TEST_ONLY_MOCK"
    assert result.audit["response_provenance"]["prompt_sha256"] == sha256_text(backend.last_prompt)
    assert result.audit["checks"]["publication"] == "NOT_RUN"
    assert all(value == "PASS" for key, value in result.audit["checks"].items() if key != "publication")
    validate_instance(result.lesson, "lesson")
    validate_instance(result.audit, "lesson-generation-audit")


def test_rehashed_self_authorization_exploit_fails_before_backend(verified_m5: VerifiedM5Authority) -> None:
    authority, request = authority_and_request(verified_m5)
    forged = copy.deepcopy(authority.authorization)
    forged["records"] = forged["records"][:-1]
    from english_master.lesson_generation import authorization_id, request_id
    forged["authorization_id"] = authorization_id(forged)
    request["authorization_id"] = forged["authorization_id"]
    request["authorization_sha256"] = sha256_json(forged)
    request["request_id"] = request_id(request)
    backend, result = run(verified_m5, request, authority=LessonGenerationAuthority(m5=verified_m5, authorization=forged))
    assert backend.calls == 0 and not result.accepted
    assert "AUTHORIZATION_BINDING_MISMATCH" in codes(result)


@pytest.mark.parametrize("path,value", [
    (("lesson_spec", "title"), "Forged title"),
    (("constraints", "forbidden_ids"), []),
    (("teaching_payload", "payload_sha256"), "0" * 64),
])
def test_rehashed_request_drift_fails_before_backend(verified_m5: VerifiedM5Authority, path: tuple[str, str], value: object) -> None:
    _, request = authority_and_request(verified_m5)
    request[path[0]][path[1]] = value
    from english_master.lesson_generation import request_id
    request["request_id"] = request_id(request)
    backend, result = run(verified_m5, request)
    assert backend.calls == 0 and "REQUEST_DERIVATION_MISMATCH" in codes(result)


def test_vocabulary_bearing_a1_2_request_uses_m2_lemma_and_cefr(verified_m5: VerifiedM5Authority) -> None:
    authority, request = authority_and_request(verified_m5, "A1-U02-L02")
    vocabulary = [record for record in request["teaching_payload"]["records"] if record["id"] == "vocab_en_run_001"]
    assert vocabulary and vocabulary[0]["lemma"] == "run" and vocabulary[0]["cefr"] == "A1.2"
    assert authority.authorization["records"]


def test_capture_mismatch_is_rejected_after_preflight(verified_m5: VerifiedM5Authority) -> None:
    authority, request = authority_and_request(verified_m5)
    class MismatchedBackend:
        byte_identical_output = False
        calls = 0
        def generate(self, prompt, *, parameters, seed):
            self.calls += 1
            content = fixture_candidate()
            return CapturedLessonResponse(content, "0" * 64, sha256_json(content), "capture", "model", parameters, seed, "2026-09-03T00:00:00Z", False, True)
    backend = MismatchedBackend()
    result = LessonGenerator(backend, authority, clock=lambda: FIXED_NOW).generate(LessonGenerationRequest.from_dict(request))
    assert backend.calls == 1 and not result.accepted
    assert "CAPTURE_MISMATCH" in codes(result)


def test_supporting_scope_and_later_milestone_leakage_are_checked(verified_m5: VerifiedM5Authority) -> None:
    candidate = fixture_candidate()
    candidate["content_sections"][0]["embedded_examples"].append("concept_listening")
    backend, result = run(verified_m5, candidate=candidate)
    assert backend.calls == 1 and result.accepted
    hostile = fixture_candidate()
    hostile["answer_key"] = {"forbidden": True}
    backend, result = run(verified_m5, candidate=hostile)
    assert backend.calls == 1 and "BACKEND_SCOPE_VIOLATION" in codes(result)


def test_accepted_and_rejected_publication_are_immutable(verified_m5: VerifiedM5Authority, tmp_path: Path) -> None:
    output = tmp_path / "published"
    _, accepted = run(verified_m5, output_directory=output)
    assert accepted.accepted and sorted(path.name for path in output.iterdir()) == ["audit.json", "lesson.json"]
    _, duplicate = run(verified_m5, output_directory=output)
    assert not duplicate.accepted and "PUBLICATION_FAILURE" in codes(duplicate)
    rejected = tmp_path / "rejected"
    hostile = fixture_candidate()
    hostile["answer_key"] = {"forbidden": True}
    _, failed = run(verified_m5, candidate=hostile, rejection_directory=rejected)
    assert not failed.accepted and sorted(path.name for path in rejected.iterdir()) == ["audit.json", "rejection.json"]
    validate_instance(load_json(rejected / "audit.json"), "lesson-generation-audit")
    validate_instance(load_json(rejected / "rejection.json"), "lesson-generation-rejection")




def test_snapshot_member_tampering_blocks_authority_load(verified_m5: VerifiedM5Authority, tmp_path: Path) -> None:
    snapshot_dir = tmp_path / "snapshot"
    review_path = snapshot_dir / "review-linguistic.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["decision"] = "REJECT"
    review_path.write_text(json.dumps(review), encoding="utf-8")
    with pytest.raises(Exception):
        VerifiedM5Authority.from_files(ROOT / "curriculum" / "structure.json", snapshot_dir, SOURCE_REGISTRY_PATH, tmp_path / "reviewer-authority.json")


def independent_review(lesson: dict, audit: dict, m5: VerifiedM5Authority, *, decision: str = "APPROVE") -> dict:
    from english_master.lesson_generation.canonical import identity
    role = "LINGUISTIC"
    review = {
        "schema_version": "1.0", "record_type": "lesson_independent_review", "lesson_id": lesson["id"],
        "lesson_sha256": sha256_json(lesson), "audit_sha256": sha256_json(audit), "snapshot_binding": m5.snapshot_binding(),
        "review_role": role, "reviewer": {"reviewer_id": "reviewer-l", "display_name": "Test reviewer reviewer-l", "qualifications": ["Synthetic test fixture qualification"], "identity_evidence_id": "evidence-reviewer-l", "independent_of_generation": True, "conflicts_disclosed": False},
        "reviewed_at": "2026-09-03T00:00:01Z", "decision": decision,
        "checklist": [{"criterion": criterion, "result": "PASS", "notes": "Synthetic test-only review."} for criterion in sorted({"CEFR_ALIGNMENT", "GRAMMAR_LEXICAL_ACCURACY", "LANGUAGE_QUALITY", "PREREQUISITE_SCOPE", "COPYRIGHT_SPOT_CHECK"})],
        "findings": [], "copyright_spot_check": {"method": "Synthetic test search", "scope_limitations": "This is a synthetic test only.", "result": "NO_CONCERN_FOUND", "notes": "No external content was checked."},
        "attestation": {"reviewed_exact_lesson_and_audit": True, "independent_review_performed": True, "does_not_approve_content": True},
    }
    review["lesson_review_id"] = identity("m6review", review, "lesson_review_id")
    return review


def test_independent_review_is_hash_bound_but_does_not_approve_lesson(verified_m5: VerifiedM5Authority) -> None:
    from english_master.lesson_generation.review import validate_lesson_review
    _, generated = run(verified_m5)
    review = independent_review(generated.lesson, generated.audit, verified_m5)
    assert validate_lesson_review(review, generated.lesson, generated.audit, verified_m5) == ()
    assert generated.lesson["generation_metadata"]["qa_status"] == "UNREVIEWED"
    validate_instance(review, "lesson-independent-review")


def test_rehashed_independent_review_tampering_is_rejected(verified_m5: VerifiedM5Authority) -> None:
    from english_master.lesson_generation.canonical import identity
    from english_master.lesson_generation.review import validate_lesson_review
    _, generated = run(verified_m5)
    review = independent_review(generated.lesson, generated.audit, verified_m5)
    review["lesson_sha256"] = "0" * 64
    review["lesson_review_id"] = identity("m6review", review, "lesson_review_id")
    assert "LESSON_HASH_MISMATCH" in {issue.code for issue in validate_lesson_review(review, generated.lesson, generated.audit, verified_m5)}
