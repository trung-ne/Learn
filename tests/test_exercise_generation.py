from __future__ import annotations

import copy
from datetime import datetime, timezone
from pathlib import Path

from english_master.exercise_generation.authority import VerifiedM6DevelopmentAuthority
from english_master.exercise_generation.backend import MockExerciseBackend
from english_master.exercise_generation.builders import build_authorization, build_request
from english_master.exercise_generation.generator import ExerciseGenerator
from english_master.exercise_generation.models import ExerciseGenerationRequest
from english_master.exercise_generation.review import _revalidate_exercise_set, validate_ai_review, validate_development_batch
from english_master.exercise_generation.validator import candidate_semantic_issues
from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_json

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "tests" / "fixtures" / "exercise_generation" / "a1-u01-l01-capture.json"
DEVELOPMENT_CAPTURES = ROOT / "curriculum" / "exercises" / "captures" / "20260903-development-v1"
DEVELOPMENT_LESSONS = (
    "A1-U01-L01", "A1-U01-L02", "A1-U02-L01", "A1-U02-L02", "A2-U03-L01",
    "A2-U03-L02", "A2-U04-L01", "A2-U04-L02", "B1-U05-L01", "B1-U05-L02",
)
SUPPORTED_TYPES = {
    "multiple_choice", "fill_blank", "matching", "ordering", "error_correction",
    "sentence_construction", "translation", "reading", "listening", "speaking", "writing",
}
FIXED_NOW = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)


def authority() -> VerifiedM6DevelopmentAuthority:
    return VerifiedM6DevelopmentAuthority.from_files(
        ROOT / "curriculum" / "structure.json", ROOT / "data" / "reviews" / "m5" / "development-20260903-062008",
        ROOT / "sources" / "registry.yaml", ROOT / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        ROOT / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
    )


def candidate() -> dict:
    return load_json(CAPTURE)["content"]


def run(value: dict | None = None):
    verified = authority(); authorization = build_authorization(verified); request = build_request(verified, authorization, "A1-U01-L01")
    backend = MockExerciseBackend(candidate() if value is None else value)
    result = ExerciseGenerator(backend, verified, clock=lambda: FIXED_NOW).generate(request)
    return backend, result, request


def test_generation_uses_verified_m6_authority_and_injects_trusted_fields() -> None:
    backend, result, _ = run()
    assert backend.calls == 1 and result.accepted
    assert result.exercise_set is not None
    assert result.exercise_set["status"] == "UNREVIEWED"
    assert all(item["generation_metadata"]["qa_status"] == "UNREVIEWED" for item in result.exercise_set["exercises"])
    assert result.audit["provenance_copyright"]["external_payload_used"] is False


def test_preflight_rejects_request_drift_before_backend() -> None:
    verified = authority(); authorization = build_authorization(verified); payload = build_request(verified, authorization, "A1-U01-L01").as_dict()
    payload["lesson_spec"]["cefr_level"] = "C2.2"
    backend = MockExerciseBackend(candidate())
    result = ExerciseGenerator(backend, verified, clock=lambda: FIXED_NOW).generate(ExerciseGenerationRequest(payload))
    assert not result.accepted and backend.calls == 0
    assert {item["code"] for item in result.audit["qa_issues_found"]} == {"REQUEST_DERIVATION_MISMATCH"}


def test_multiple_choice_multiple_primary_or_duplicate_option_is_rejected() -> None:
    value = candidate(); value["items"][0]["payload"]["options"][1]["text"] = value["items"][0]["payload"]["options"][0]["text"]
    _, result, _ = run(value)
    assert not result.accepted
    assert "MCQ_DISTRACTOR_INVALID" in {item["code"] for item in result.audit["qa_issues_found"]}


def test_unsupported_media_and_later_milestone_scope_leakage_are_rejected() -> None:
    value = candidate(); value["items"][0]["instructions"] = "Ask an AI tutor to evaluate pronunciation."
    _, result, _ = run(value)
    assert not result.accepted
    assert "LATER_MILESTONE_SCOPE_LEAKAGE" in {item["code"] for item in result.audit["qa_issues_found"]}


def test_all_supported_types_are_accepted_in_development_captures() -> None:
    verified = authority()
    observed_types: set[str] = set()
    for lesson_id in DEVELOPMENT_LESSONS:
        capture = load_json(DEVELOPMENT_CAPTURES / f"{lesson_id}.json")["content"]
        authorization = build_authorization(verified)
        request = build_request(verified, authorization, lesson_id)
        result = ExerciseGenerator(MockExerciseBackend(capture), verified, clock=lambda: FIXED_NOW).generate(request)
        assert result.accepted, lesson_id
        assert result.exercise_set is not None
        observed_types.update(item["exercise_type"] for item in result.exercise_set["exercises"])
    assert observed_types == SUPPORTED_TYPES


def test_duplicate_matching_labels_are_rejected() -> None:
    value = candidate()
    value["items"][2]["payload"]["left"][1]["id"] = value["items"][2]["payload"]["left"][0]["id"]
    _, result, _ = run(value)
    assert not result.accepted
    assert "MATCHING_MAPPING_INVALID" in {item["code"] for item in result.audit["qa_issues_found"]}


def test_duplicate_matching_text_is_rejected() -> None:
    value = candidate()
    value["items"][2]["payload"]["right"][1]["text"] = value["items"][2]["payload"]["right"][0]["text"]
    _, result, _ = run(value)
    assert not result.accepted
    assert "MATCHING_MAPPING_INVALID" in {item["code"] for item in result.audit["qa_issues_found"]}


def test_duplicate_ordering_segment_ids_are_rejected() -> None:
    value = candidate()
    value["items"][3]["payload"]["segments"][1]["id"] = value["items"][3]["payload"]["segments"][0]["id"]
    _, result, _ = run(value)
    assert not result.accepted
    assert "ORDERING_INVALID" in {item["code"] for item in result.audit["qa_issues_found"]}


def test_rejection_is_atomic_and_separate(tmp_path: Path) -> None:
    value = candidate(); value["items"][1]["payload"].pop("primary_answer")
    _, result, _ = run(value)
    assert not result.accepted
    assert result.exercise_set is None


def test_final_mixed_revision_development_batch_and_ai_reviews_validate() -> None:
    verified = authority()
    exercise_root = ROOT / "curriculum" / "exercises"
    report = load_strict_document(
        exercise_root / "development-batches" / "20260903-v3" / "development-batch.json"
    )
    assert validate_development_batch(report, verified, exercise_root) == ()
    final_entry = next(entry for entry in report["exercise_sets"] if entry["lesson_id"] == "B1-U05-L02")
    bundle = exercise_root / final_entry["bundle_path"]
    exercise_set = load_strict_document(bundle / "exercise-set.json")
    audit = load_strict_document(bundle / "audit.json")
    for reference in final_entry["ai_reviews"]:
        review = load_strict_document(exercise_root / reference["path"])
        assert validate_ai_review(review, exercise_set, audit, verified) == ()


def test_final_set_revalidation_does_not_trust_a_passing_audit() -> None:
    verified = authority()
    bundle = ROOT / "curriculum" / "exercises" / "development-20260903-v3" / "B1-U05-L02"
    exercise_set = copy.deepcopy(load_strict_document(bundle / "exercise-set.json"))
    exercise_set["exercises"][0]["target_references"] = ["vocab_en_outside_scope_001"]
    base = dict(exercise_set)
    base.pop("exercise_set_id")
    base.pop("output_sha256")
    exercise_set["output_sha256"] = sha256_json(base)
    exercise_set["exercise_set_id"] = f"m7set_{exercise_set['output_sha256']}"
    assert "REFERENCE_SCOPE_MISMATCH" in {issue.code for issue in _revalidate_exercise_set(exercise_set, verified)}


def test_comprehension_questions_require_exact_answer_mapping() -> None:
    verified = authority()
    lesson_id = "B1-U05-L02"
    captured = load_json(
        DEVELOPMENT_CAPTURES / f"{lesson_id}.json"
    )["content"]
    reading = next(
        item for item in captured["items"] if item["exercise_type"] == "reading"
    )
    reading["payload"]["answers"][0]["question_id"] = "unrelated"
    request = build_request(
        verified, build_authorization(verified), lesson_id
    ).as_dict()
    assert "COMPREHENSION_ANSWER_MAPPING_INVALID" in {
        issue.code for issue in candidate_semantic_issues(request, captured)
    }


def test_subjective_rubric_rejects_duplicate_or_empty_dimensions() -> None:
    verified = authority()
    lesson_id = "A1-U01-L02"
    captured = load_json(ROOT / "curriculum" / "exercises" / "captures" / "20260903-development-v2" / f"{lesson_id}.json")["content"]
    subjective = next(item for item in captured["items"] if item["exercise_type"] == "speaking")
    subjective["payload"]["rubric"] = [
        {"dimension": "meaning", "criterion": ""},
        {"dimension": "meaning", "criterion": "Repeated dimension."},
    ]
    request = build_request(verified, build_authorization(verified), lesson_id).as_dict()
    assert "SUBJECTIVE_RUBRIC_REQUIRED" in {issue.code for issue in candidate_semantic_issues(request, captured)}
