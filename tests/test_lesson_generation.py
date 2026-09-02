from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from english_master.lesson_generate import main as lesson_generate_main
from english_master.lesson_generation import (
    LessonGenerationAuthority,
    LessonGenerationRequest,
    LessonGenerator,
    MockLessonBackend,
    authorization_id,
    request_id,
)
from english_master.lesson_generation import storage
from english_master.schema_validation import load_document, load_json, validate_instance

ROOT = Path(__file__).parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "m6"


def fixture_request() -> dict:
    return load_json(FIXTURES / "approved-request.json")


def fixture_candidate() -> dict:
    return load_json(FIXTURES / "approved-mock-lesson.json")


def fixture_authorization() -> dict:
    return load_json(FIXTURES / "approved-authorization.json")


def fixture_registry() -> dict:
    return load_document(ROOT / "sources" / "registry.yaml")


def authority(authorization: dict | None = None, registry: dict | None = None) -> LessonGenerationAuthority:
    loaded = LessonGenerationAuthority.from_files(
        ROOT / "curriculum" / "structure.json",
        FIXTURES / "approved-authorization.json",
        ROOT / "sources" / "registry.yaml",
    )
    return LessonGenerationAuthority(loaded.bundle, authorization or loaded.authorization, registry or loaded.source_registry)


def resign_request(value: dict) -> dict:
    value["request_id"] = request_id(value)
    return value


def bind_authority(value: dict, authorization: dict, registry: dict | None = None) -> tuple[dict, LessonGenerationAuthority]:
    candidate_authority = authority(authorization, registry)
    authorization["artifact_hashes"] = candidate_authority.artifact_hashes()
    authorization["authorization_id"] = authorization_id(authorization)
    candidate_authority = authority(authorization, registry)
    value["artifact_hashes"] = candidate_authority.artifact_hashes()
    value["authorization_id"] = authorization["authorization_id"]
    resign_request(value)
    return value, candidate_authority


def run(value: dict, candidate: object | None = None, *, auth: LessonGenerationAuthority | None = None, **kwargs):
    response = fixture_candidate() if candidate is None else candidate

    class TestBackend:
        def __init__(self, payload: object) -> None:
            self.payload = payload
            self.calls = 0
            self.last_prompt: str | None = None

        def generate(self, prompt, *, parameters, seed):
            self.calls += 1
            self.last_prompt = prompt
            return copy.deepcopy(self.payload)

    backend = TestBackend(response)
    result = LessonGenerator(backend, auth or authority()).generate(LessonGenerationRequest.from_dict(value), **kwargs)
    return backend, result


def codes(result) -> set[str]:
    return {item["code"] for item in result.audit["unresolved_issues"]}


def test_valid_generation_uses_authority_and_injects_trusted_fields() -> None:
    first_backend, first = run(fixture_request())
    _, second = run(fixture_request())
    assert first.accepted and first_backend.calls == 1
    assert first.lesson == second.lesson and first.audit == second.audit
    assert set(fixture_candidate()) == {"content_sections"}
    assert first.lesson["id"] == "A1-U01-L01"
    assert first.lesson["generation_metadata"] == {
        "generator": "english_master.lesson_generation",
        "generator_version": "1.1",
        "model": "authored-fixture-v2",
        "prompt_version": "M6_LESSON_GENERATOR_v2",
        "generated_at": "2026-09-02T10:00:00Z",
        "curriculum_version": "20260902",
        "qa_status": "UNREVIEWED",
        "qa_notes": "Automated M6 structural checks passed; independent review remains required.",
    }
    assert first.audit["qa_outcome"] == "AUTOMATED_CHECKS_PASSED_PENDING_INDEPENDENT_REVIEW"
    assert first.audit["outstanding_independent_reviews"] == ["CEFR", "GRAMMAR_LEXICAL", "LANGUAGE_QUALITY", "PEDAGOGICAL"]
    assert all(value == "PASS" for key, value in first.audit["checks"].items() if key != "publication")
    assert first.audit["checks"]["publication"] == "NOT_RUN"
    validate_instance(first.lesson, "lesson")
    validate_instance(first.audit, "lesson-generation-audit")


def test_current_m5_draft_gate_fails_before_backend() -> None:
    authorization = fixture_authorization()
    authorization["status"] = "DRAFT"
    request, denied_authority = bind_authority(fixture_request(), authorization)
    backend, result = run(request, auth=denied_authority)
    assert backend.calls == 0 and not result.accepted
    assert {"AUTHORIZATION_SCHEMA", "M5_CONTENT_GENERATION_BLOCKED"} <= codes(result)
    assert result.audit["checks"]["m5_authority"] == "FAIL"
    assert result.audit["checks"]["backend_contract"] == "NOT_RUN"


def test_resigned_request_cannot_forge_authoritative_m5_lesson() -> None:
    request = fixture_request()
    request["lesson_spec"]["title"] = "Forged title"
    resign_request(request)
    backend, result = run(request)
    assert backend.calls == 0
    assert "M5_LESSON_MISMATCH" in codes(result)


@pytest.mark.parametrize("field", ["lesson_order", "prerequisite_edges", "introduction_edges", "review_edges", "resolved_prerequisite_closure"])
def test_graph_declarations_must_equal_authoritative_derivation(field: str) -> None:
    request = fixture_request()
    if field == "lesson_order":
        request["graph"][field] = list(reversed(request["graph"][field]))
    elif field == "resolved_prerequisite_closure":
        request["graph"][field] = ["concept_past_simple"]
    elif field == "review_edges":
        request["graph"][field] = [{"from": "A1-U01-L01", "to": "A1-U01-L02"}]
    else:
        request["graph"][field] = [] if request["graph"][field] else [{"from": "A1-U01-L01", "to": "concept_past_simple"}]
    resign_request(request)
    backend, result = run(request)
    assert backend.calls == 0 and "AUTHORITATIVE_GRAPH_MISMATCH" in codes(result)


def test_authorized_record_must_match_pinned_taxonomy_and_closure() -> None:
    authorization = fixture_authorization()
    authorization["records"][0]["definition"] = "Rewritten caller assertion"
    request, changed_authority = bind_authority(fixture_request(), authorization)
    backend, result = run(request, auth=changed_authority)
    assert backend.calls == 0
    assert {"AUTHORIZED_RECORD_MISMATCH", "M5_CONTENT_GENERATION_BLOCKED"} <= codes(result)


def test_authorization_includes_all_m5_supporting_taxonomy_concepts() -> None:
    authorization = fixture_authorization()
    expected = {
        "concept_listening", "concept_speaking", "concept_reading", "concept_writing",
        "concept_topic_personal_information",
    }
    supporting = {record["id"] for record in authorization["records"] if record["record_type"] == "SUPPORTING_CONCEPT"}
    assert expected == supporting

    authorization["records"] = [record for record in authorization["records"] if record["id"] != "concept_listening"]
    request, changed_authority = bind_authority(fixture_request(), authorization)
    backend, result = run(request, auth=changed_authority)
    assert backend.calls == 0
    assert {"UNRESOLVED_REFERENCE", "M5_CONTENT_GENERATION_BLOCKED"} <= codes(result)


def externalize(record: dict, source: dict) -> None:
    source_content = "Authorized fixture source text."
    record["content_origin"] = "EXTERNAL_APPROVED"
    record["source_content_type"] = "text"
    record["source_content"] = source_content
    record["provenance"] = {
        "source_id": source["source_id"],
        "source_name": source["source_name"],
        "source_url": source["source_url"],
        "source_record_id": "fixture_record_1",
        "retrieved_at": "2026-09-02T08:00:00Z",
        "retrieved_by": "m6_fixture_builder",
        "license": source["license"]["name"],
        "license_url": source["license"]["url"],
        "attribution": f"Record fixture_record_1, {source['license']['url']}",
        "content_hash": hashlib.sha256(source_content.encode("utf-8")).hexdigest(),
        "ingestion_version": "fixture-v1",
    }


def test_external_record_is_denied_by_registry_status_and_permissions() -> None:
    registry = fixture_registry()
    source = next(item for item in registry["sources"] if item["status"] == "REFERENCE_ONLY")
    authorization = fixture_authorization()
    externalize(authorization["records"][0], source)
    request, changed_authority = bind_authority(fixture_request(), authorization, registry)
    backend, result = run(request, auth=changed_authority)
    assert backend.calls == 0
    assert {"SOURCE_NOT_APPROVED", "SOURCE_PERMISSION_DENIED"} <= codes(result)
    assert result.audit["checks"]["provenance_copyright"] == "FAIL"


def test_external_provenance_must_match_approved_registry_record() -> None:
    registry = fixture_registry()
    source = next(item for item in registry["sources"] if item["source_id"] == "src_tatoeba_text")
    authorization = fixture_authorization()
    externalize(authorization["records"][0], source)
    authorization["records"][0]["provenance"]["license"] = "invented-license"
    request, changed_authority = bind_authority(fixture_request(), authorization, registry)
    backend, result = run(request, auth=changed_authority)
    assert backend.calls == 0 and "PROVENANCE_REGISTRY_MISMATCH" in codes(result)


def test_external_source_content_hash_and_attribution_are_verified() -> None:
    registry = fixture_registry()
    source = next(item for item in registry["sources"] if item["source_id"] == "src_tatoeba_text")
    authorization = fixture_authorization()
    externalize(authorization["records"][0], source)
    authorization["records"][0]["source_content"] = "Tampered after hashing."
    authorization["records"][0]["provenance"]["attribution"] = "Incomplete"
    request, changed_authority = bind_authority(fixture_request(), authorization, registry)
    backend, result = run(request, auth=changed_authority)
    assert backend.calls == 0
    assert {"PROVENANCE_CONTENT_HASH_MISMATCH", "ATTRIBUTION_INCOMPLETE", "M5_CONTENT_GENERATION_BLOCKED"} <= codes(result)


def test_shared_id_and_identity_contracts_reject_cross_family_and_mismatch() -> None:
    cross_family = fixture_request()
    cross_family["constraints"]["allowed_vocabulary"] = ["concept_present_simple"]
    resign_request(cross_family)
    backend, result = run(cross_family)
    assert backend.calls == 0 and "REQUEST_SCHEMA" in codes(result)

    inconsistent = fixture_request()
    inconsistent["lesson_spec"]["lesson_number"] = 2
    resign_request(inconsistent)
    backend, result = run(inconsistent)
    assert backend.calls == 0
    assert {"IDENTITY_CONTRACT_MISMATCH", "M5_LESSON_MISMATCH"} <= codes(result)


def test_lesson_schema_accepts_taxonomy_communicative_function_ids() -> None:
    _, result = run(fixture_request())
    lesson = copy.deepcopy(result.lesson)
    lesson["communicative_functions"] = ["concept_function_request_help"]
    lesson["functions_introduced"] = ["concept_function_request_help"]
    validate_instance(lesson, "lesson")


def test_section_titles_obey_forbidden_term_and_size_constraints() -> None:
    candidate = fixture_candidate()
    candidate["content_sections"][0]["title"] = "Forbidden title marker"
    request = fixture_request()
    request["constraints"]["forbidden_terms"] = ["forbidden title"]
    resign_request(request)
    backend, result = run(request, candidate)
    assert backend.calls == 1 and "FORBIDDEN_TERM" in codes(result)
    assert any(issue["path"].endswith(".title") for issue in result.audit["unresolved_issues"] if issue["code"] == "FORBIDDEN_TERM")


def test_reproducibility_claim_comes_from_backend_capability() -> None:
    _, ordinary = run(fixture_request())
    assert ordinary.audit["reproducibility"]["byte_identical_claimed"] is False
    result = LessonGenerator(MockLessonBackend(fixture_candidate()), authority()).generate(
        LessonGenerationRequest.from_dict(fixture_request())
    )
    assert result.audit["reproducibility"]["byte_identical_claimed"] is True


def test_invalid_generated_at_is_a_controlled_preflight_rejection() -> None:
    request = fixture_request()
    request["generation"]["generated_at"] = "not-a-date"
    resign_request(request)
    backend, result = run(request)
    assert backend.calls == 0
    assert {"REQUEST_SCHEMA", "M5_CONTENT_GENERATION_BLOCKED"} <= codes(result)
    validate_instance(result.audit, "lesson-generation-audit")


def test_hostile_backend_cannot_supply_metadata_or_later_scope() -> None:
    candidate = fixture_candidate()
    candidate["generation_metadata"] = {"qa_status": "APPROVED"}
    backend, result = run(fixture_request(), candidate)
    assert backend.calls == 1 and not result.accepted
    assert "BACKEND_SCOPE_VIOLATION" in codes(result)
    assert result.rejection["stage"] == "PROVIDER"


@pytest.mark.parametrize("candidate", [[], {"content_sections": float("nan")}, {"content_sections": object()}])
def test_malformed_backend_values_are_controlled_rejections(candidate: object) -> None:
    backend, result = run(fixture_request(), candidate)
    assert backend.calls == 1 and not result.accepted
    assert "BACKEND_RESPONSE_INVALID" in codes(result)
    assert result.audit["checks"]["backend_contract"] == "FAIL"
    assert result.audit["checks"]["lesson_schema"] == "NOT_RUN"


def test_provider_exception_is_sanitized_and_deterministic() -> None:
    class BrokenBackend:
        def generate(self, prompt, *, parameters, seed):
            raise RuntimeError("secret provider details")

    generator = LessonGenerator(BrokenBackend(), authority())
    result = generator.generate(LessonGenerationRequest.from_dict(fixture_request()))
    assert not result.accepted
    assert result.audit["unresolved_issues"][0]["message"] == "backend raised RuntimeError"
    assert "secret" not in json.dumps(result.rejection)


def test_rejection_persists_audit_and_rejection_atomically(tmp_path: Path) -> None:
    candidate = fixture_candidate()
    candidate["answer_key"] = {"forbidden": True}
    output = tmp_path / "accepted"
    rejected = tmp_path / "rejected"
    _, result = run(fixture_request(), candidate, output_directory=output, rejection_directory=rejected)
    assert not result.accepted and not output.exists()
    assert sorted(path.name for path in rejected.iterdir()) == ["audit.json", "rejection.json"]
    validate_instance(load_json(rejected / "audit.json"), "lesson-generation-audit")
    validate_instance(load_json(rejected / "rejection.json"), "lesson-generation-rejection")


def test_accepted_publication_is_atomic_and_no_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "published"
    _, accepted = run(fixture_request(), output_directory=output)
    assert accepted.accepted
    assert sorted(path.name for path in output.iterdir()) == ["audit.json", "lesson.json"]
    assert load_json(output / "audit.json")["checks"]["publication"] == "PASS"
    _, duplicate = run(fixture_request(), output_directory=output)
    assert not duplicate.accepted and "PUBLICATION_FAILURE" in codes(duplicate)
    assert load_json(output / "lesson.json") == accepted.lesson


def test_post_commit_parent_fsync_failure_does_not_report_rejection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original = storage._fsync_directory
    calls = 0

    def fail_parent_after_commit(path: Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated parent fsync failure")
        original(path)

    monkeypatch.setattr(storage, "_fsync_directory", fail_parent_after_commit)
    output = tmp_path / "published"
    _, result = run(fixture_request(), output_directory=output)
    assert result.accepted
    assert sorted(path.name for path in output.iterdir()) == ["audit.json", "lesson.json"]


def test_concurrent_destination_creation_is_not_overwritten(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    original = storage._rename_directory_noreplace
    output = tmp_path / "race"

    def race(source: Path, destination: Path) -> None:
        destination.mkdir()
        (destination / "owner.txt").write_text("other writer", encoding="utf-8")
        original(source, destination)

    monkeypatch.setattr(storage, "_rename_directory_noreplace", race)
    _, result = run(fixture_request(), output_directory=output)
    assert not result.accepted and "PUBLICATION_FAILURE" in codes(result)
    assert (output / "owner.txt").read_text(encoding="utf-8") == "other writer"
    assert not (output / "lesson.json").exists()
    assert not list(tmp_path.glob(".race.*"))


def test_rejection_storage_failure_is_reported_without_masking_validation(tmp_path: Path) -> None:
    rejection = tmp_path / "existing"
    rejection.mkdir()
    request = fixture_request()
    request["lesson_spec"]["title"] = "forged"
    resign_request(request)
    _, result = run(request, rejection_directory=rejection)
    assert {"M5_LESSON_MISMATCH", "REJECTION_PERSISTENCE_FAILURE"} <= codes(result)
    assert result.rejection["stage"] == "PUBLICATION"
    assert result.audit["checks"]["publication"] == "FAIL"


def test_offline_cli_success_rejection_and_no_overwrite(tmp_path: Path) -> None:
    common = [
        "--request", str(FIXTURES / "approved-request.json"),
        "--authorization", str(FIXTURES / "approved-authorization.json"),
        "--mock-response", str(FIXTURES / "approved-mock-lesson.json"),
    ]
    success = tmp_path / "success"
    assert lesson_generate_main([*common, "--output-dir", str(success)]) == 0
    assert lesson_generate_main([*common, "--output-dir", str(success)]) == 2

    hostile = fixture_candidate()
    hostile["generation_metadata"] = {"qa_status": "APPROVED"}
    hostile_path = tmp_path / "hostile.json"
    hostile_path.write_text(json.dumps(hostile), encoding="utf-8")
    rejected = tmp_path / "rejected"
    failed = tmp_path / "failed"
    args = [
        "--request", str(FIXTURES / "approved-request.json"),
        "--authorization", str(FIXTURES / "approved-authorization.json"),
        "--mock-response", str(hostile_path),
        "--output-dir", str(failed),
        "--rejection-dir", str(rejected),
    ]
    assert lesson_generate_main(args) == 1
    assert not failed.exists() and (rejected / "audit.json").is_file()
