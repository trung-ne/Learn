from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from english_master.lesson_generate import main as lesson_generate_main
from english_master.lesson_generation import (
    LessonGenerationRequest,
    LessonGenerator,
    MockLessonBackend,
    authorization_id,
    request_id,
)
from english_master.schema_validation import load_json, validate_instance

FIXTURES = Path(__file__).parent / "fixtures" / "m6"


def fixture_request() -> dict:
    return load_json(FIXTURES / "approved-request.json")


def fixture_lesson() -> dict:
    return load_json(FIXTURES / "approved-mock-lesson.json")


def resign(value: dict) -> dict:
    value["authorization"]["authorization_id"] = authorization_id(value["authorization"])
    value["request_id"] = request_id(value)
    return value


def run(value: dict, lesson: dict | None = None, **kwargs):
    backend = MockLessonBackend(lesson or fixture_lesson())
    result = LessonGenerator(backend).generate(LessonGenerationRequest.from_dict(value), **kwargs)
    return backend, result


def codes(result) -> set[str]:
    return {item["code"] for item in result.audit["unresolved_issues"]}


def test_valid_constrained_generation_is_schema_valid_and_deterministic() -> None:
    request = fixture_request()
    first_backend, first = run(request)
    second_backend, second = run(request)
    assert first.accepted and first.lesson == fixture_lesson()
    assert first_backend.calls == second_backend.calls == 1
    assert first.audit == second.audit
    assert first.audit["qa_status"] == "UNREVIEWED"
    assert first.audit["checks"] == {key: True for key in first.audit["checks"]}
    validate_instance(first.lesson, "lesson")
    validate_instance(first.audit, "lesson-generation-audit")
    assert "Do not add scope" in first_backend.last_prompt


def test_current_m5_outline_bundle_fails_before_backend() -> None:
    root = Path(__file__).parents[1]
    backend, result = run(load_json(root / "curriculum" / "structure.json"))
    assert not result.accepted
    assert backend.calls == 0
    assert "REQUEST_SCHEMA" in codes(result)


@pytest.mark.parametrize(
    ("field", "value"),
    [("id", "A1-U01-L02"), ("unit_id", "A1.1-U02"), ("cefr_level", "A1.2")],
)
def test_output_identity_tier_and_parent_mismatches_are_rejected(field: str, value: object) -> None:
    lesson = fixture_lesson(); lesson[field] = value
    backend, result = run(fixture_request(), lesson)
    assert not result.accepted and backend.calls == 1
    assert "LESSON_SPEC_MISMATCH" in codes(result)


def test_missing_wrong_type_and_unapproved_authorization_fail_preflight() -> None:
    unknown = fixture_request()
    unknown["constraints"]["allowed_grammar"] = ["concept_missing"]
    unknown["lesson_spec"]["grammar_introduced"] = ["concept_missing"]
    backend, result = run(resign(unknown))
    assert backend.calls == 0 and "UNRESOLVED_REFERENCE" in codes(result)

    wrong = fixture_request()
    wrong["authorization"]["records"][0]["record_type"] = "PRONUNCIATION"
    backend, result = run(resign(wrong))
    assert backend.calls == 0 and "WRONG_REFERENCE_TYPE" in codes(result)

    draft = fixture_request()
    draft["authorization"]["records"][0]["status"] = "DRAFT"
    backend, result = run(resign(draft))
    assert backend.calls == 0 and "REQUEST_SCHEMA" in codes(result)


def test_unknown_unintroduced_and_over_limit_vocabulary_fail_preflight() -> None:
    unintroduced = fixture_request()
    unintroduced["lesson_spec"]["vocabulary_introduced"] = []
    backend, result = run(resign(unintroduced))
    assert backend.calls == 0 and "ALLOWED_SCOPE_MISMATCH" in codes(result)

    over = fixture_request(); over["constraints"]["max_target_vocabulary"] = 1
    backend, result = run(resign(over))
    assert backend.calls == 0 and "TARGET_VOCABULARY_LIMIT" in codes(result)


def test_forbidden_overlap_and_advanced_record_fail_preflight() -> None:
    overlap = fixture_request()
    overlap["constraints"]["forbidden_ids"].append("concept_subject_pronouns")
    backend, result = run(resign(overlap))
    assert backend.calls == 0 and "ALLOWED_FORBIDDEN_OVERLAP" in codes(result)

    advanced = fixture_request()
    advanced["authorization"]["records"][0]["cefr"] = "B1.1"
    backend, result = run(resign(advanced))
    assert backend.calls == 0 and "ABOVE_TARGET_CEFR" in codes(result)


def test_prerequisite_and_review_ordering_fail_preflight() -> None:
    request = fixture_request()
    request["lesson_spec"]["prerequisites"] = ["A1-U01-L02"]
    request["graph"]["lesson_order"].append("A1-U01-L02")
    request["graph"]["prerequisite_edges"] = [{"from": "A1-U01-L02", "to": "A1-U01-L01"}]
    request["previous_knowledge"]["completed_lessons"] = ["A1-U01-L02"]
    request["lesson_spec"]["grammar_introduced"] = []
    request["lesson_spec"]["grammar_reviewed"] = ["concept_subject_pronouns"]
    backend, result = run(resign(request))
    assert backend.calls == 0
    assert {"PREREQUISITE_NOT_EARLIER", "REVIEW_NOT_PREVIOUSLY_INTRODUCED"} <= codes(result)


def test_out_of_scope_references_and_forbidden_text_are_rejected() -> None:
    lesson = fixture_lesson()
    lesson["grammar_introduced"].append("concept_b1_hypothetical_conditionals")
    lesson["content_sections"][0]["body_text"] += " Notwithstanding this rule."
    backend, result = run(fixture_request(), lesson)
    assert backend.calls == 1 and not result.accepted
    assert {"REFERENCE_SCOPE_MISMATCH", "FORBIDDEN_REFERENCE", "FORBIDDEN_TERM"} <= codes(result)


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda lesson: lesson.pop("title"), "LESSON_SCHEMA"),
        (lambda lesson: lesson.pop("generation_metadata"), "GENERATION_METADATA_MISSING"),
        (lambda lesson: lesson["generation_metadata"].update(qa_status="APPROVED"), "GENERATION_METADATA_MISMATCH"),
        (lambda lesson: lesson["exercises"].append("ex_A1-U01-L01_001"), "M7_LEAKAGE"),
        (lambda lesson: lesson.update(assessment={"id": "forbidden"}), "LATER_MILESTONE_LEAKAGE"),
    ],
)
def test_invalid_model_outputs_are_rejected(mutator, expected: str) -> None:
    lesson = fixture_lesson(); mutator(lesson)
    _, result = run(fixture_request(), lesson)
    assert not result.accepted and expected in codes(result)


def test_rejected_generation_has_auditable_record_and_no_partial_publication(tmp_path: Path) -> None:
    lesson = fixture_lesson(); lesson["generation_metadata"]["qa_status"] = "APPROVED"
    output = tmp_path / "published"; rejection_path = tmp_path / "rejected.json"
    _, result = run(fixture_request(), lesson, output_directory=output, rejection_path=rejection_path)
    assert not result.accepted and not output.exists()
    assert rejection_path.is_file() and result.rejection["published"] is False
    validate_instance(load_json(rejection_path), "lesson-generation-rejection")


def test_accepted_publication_is_atomic_and_no_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "published"
    _, result = run(fixture_request(), output_directory=output)
    assert result.accepted
    assert sorted(path.name for path in output.iterdir()) == ["audit.json", "lesson.json"]
    with pytest.raises(FileExistsError):
        run(fixture_request(), output_directory=output)


def test_offline_cli_success_and_nonzero_rejection(tmp_path: Path) -> None:
    success = tmp_path / "success"
    assert lesson_generate_main(["--request", str(FIXTURES / "approved-request.json"), "--mock-response", str(FIXTURES / "approved-mock-lesson.json"), "--output-dir", str(success)]) == 0
    bad = fixture_lesson(); bad["generation_metadata"]["qa_status"] = "APPROVED"
    bad_path = tmp_path / "bad.json"; bad_path.write_text(json.dumps(bad), encoding="utf-8")
    failed = tmp_path / "failed"; rejected = tmp_path / "rejected.json"
    assert lesson_generate_main(["--request", str(FIXTURES / "approved-request.json"), "--mock-response", str(bad_path), "--output-dir", str(failed), "--rejection", str(rejected)]) == 1
    assert not failed.exists() and rejected.is_file()
