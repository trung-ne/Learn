from __future__ import annotations

import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from english_master.lesson_generation.canonical import sha256_json
from english_master.qa_engine.authority import VerifiedM7QaAuthority
from english_master.qa_engine.backend import ReplayModelBackend, SessionModelBackend
from english_master.qa_engine.cli import main as cli_main
from english_master.qa_engine.models import ModelCapture, REVIEW_CRITERIA
from english_master.qa_engine.orchestrator import QaEngine
from english_master.qa_engine.storage import publish_run
from english_master.qa_engine.verification import verify_run
from english_master.qa_engine.validators import answer_issues

ROOT = Path(__file__).resolve().parents[1]
FIXED_NOW = datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc)
LESSON_ID = "A1-U01-L01"


@pytest.fixture(scope="module")
def qa_authority() -> VerifiedM7QaAuthority:
    return VerifiedM7QaAuthority.from_files(
        structure_path=ROOT / "curriculum" / "structure.json",
        snapshot_directory=ROOT / "data" / "reviews" / "m5" / "development-20260903-062008",
        source_registry_path=ROOT / "sources" / "registry.yaml",
        m6_batch_path=ROOT / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        m6_root=ROOT / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
        exercise_root=ROOT / "curriculum" / "exercises",
        m7_batch_path=ROOT / "curriculum" / "exercises" / "development-batches" / "20260903-v3" / "development-batch.json",
    )


def request(authority: VerifiedM7QaAuthority, maximum_attempts: int = 3) -> dict:
    return authority.request(
        LESSON_ID,
        created_at="2026-09-04T06:00:00Z",
        maximum_attempts=maximum_attempts,
    )


def engine(
    authority: VerifiedM7QaAuthority,
    qa_request: dict,
    regeneration_backend=None,
    review_backend=None,
) -> QaEngine:
    return QaEngine(
        authority,
        qa_request,
        regeneration_backend,
        review_backend,
        clock=lambda: FIXED_NOW,
    )


def observed_backend(callback, provider_run_id: str):
    class ObservedBackend:
        def generate(self, prompt, *, parameters, seed) -> ModelCapture:
            return ModelCapture(
                callback(prompt, parameters, seed),
                "SESSION_CAPTURED",
                "UNKNOWN",
                "UNKNOWN",
                provider_run_id,
                parameters,
                seed,
                True,
            )

    return ObservedBackend()


def review_response(*, approve: bool, major_finding: bool = False) -> dict:
    return {
        "decision": "APPROVE" if approve else "REQUEST_REVISION",
        "criteria": [
            {
                "criterion": criterion,
                "result": "FAIL" if not approve and index == 3 else "PASS",
                "rationale": "Checked independently." if approve else "Clarify the learner-facing explanation.",
            }
            for index, criterion in enumerate(REVIEW_CRITERIA)
        ],
        "findings": (
            [
                {
                    "code": "LANGUAGE_CLARITY",
                    "path": "$.exercises[0].payload.explanation",
                    "message": "Clarify the learner-facing explanation.",
                    "severity": "MAJOR" if major_finding else "MINOR",
                }
            ]
            if not approve
            else []
        ),
        "limitations": ["AI-only development review; not human review."],
    }


def regeneration_items() -> dict:
    capture = json.loads(
        (ROOT / "curriculum" / "exercises" / "captures" / "20260903-development-v2" / f"{LESSON_ID}.json").read_text(encoding="utf-8")
    )
    response = copy.deepcopy(capture["content"])
    response["items"][0]["payload"]["explanation"] = (
        "With a singular third-person subject such as Hoa, use walks."
    )
    return response


def publish(
    tmp_path: Path,
    authority: VerifiedM7QaAuthority,
    qa_request: dict,
    result,
) -> Path:
    directory = tmp_path / "run"
    publish_run(
        directory,
        authority=authority,
        request=qa_request,
        attempts=result.attempts,
        receipts=result.receipts,
        rejections=result.rejections,
        decision=result.decision,
        invocations=result.invocations,
        ai_reviews=result.ai_reviews,
        operational_failures=result.operational_failures,
    )
    return directory


def test_exact_m7_attempt_passes_all_stages_and_publishes_verified_bundle(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority)
    result = engine(qa_authority, qa_request).run()

    assert result.approved
    assert result.decision is not None
    assert result.decision["terminal_result"] == "DEVELOPMENT_APPROVED"
    assert result.decision["content_lifecycle_status"] == "UNREVIEWED"
    assert len(result.attempts) == 1
    assert result.attempts[0]["generation_provenance"]["origin"] == "M7_AUTHORITY"
    assert [item["stage"] for item in result.receipts[0]] == [
        "SCHEMA", "ANSWER", "CEFR", "PREREQUISITE", "DUPLICATE", "LANGUAGE"
    ]
    assert [item["result"] for item in result.receipts[0]] == ["PASS"] * 6
    assert result.decision["human_reviewed"] is False
    assert result.decision["release_approved"] is False

    directory = publish(tmp_path, qa_authority, qa_request, result)
    verified = verify_run(directory, qa_authority)
    assert verified["terminal_state"] == "DEVELOPMENT_APPROVED"
    assert verified["content_lifecycle_status"] == "UNREVIEWED"
    with pytest.raises(ValueError, match="future-dated"):
        verify_run(
            directory,
            qa_authority,
            verified_at="2026-09-04T05:59:59Z",
        )


def test_answer_qa_detects_an_ambiguous_option(qa_authority: VerifiedM7QaAuthority) -> None:
    candidate, _, _ = qa_authority.artifacts(LESSON_ID)
    candidate = copy.deepcopy(candidate)
    options = candidate["exercises"][0]["payload"]["options"]
    options[1]["text"] = options[0]["text"]

    assert "MCQ_DISTRACTOR_INVALID" in {
        item.code for item in answer_issues(candidate, qa_authority, LESSON_ID)
    }


def test_replay_review_rejects_and_short_circuits_no_later_stage(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority, maximum_attempts=1)
    result = engine(
        qa_authority,
        qa_request,
        review_backend=ReplayModelBackend([{"response": review_response(approve=True)}]),
    ).run()

    assert not result.approved
    assert len(result.rejections) == 1
    language = result.receipts[0][-1]
    assert language["result"] == "FAIL"
    assert "NON_PROMOTABLE_AI_REVIEW_EVIDENCE" in {
        item["code"] for item in language["issues"]
    }
    assert publish(tmp_path, qa_authority, qa_request, result).is_dir()
    assert verify_run(tmp_path / "run", qa_authority)["terminal_state"] == "REJECTED"


def test_failed_fresh_review_regenerates_immutable_candidate_then_passes(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority, maximum_attempts=2)
    # A stateful callback gives the first candidate a repair request and the retry a pass.
    calls = {"count": 0}

    def review_callback(*_args):
        calls["count"] += 1
        return review_response(approve=calls["count"] == 2, major_finding=True)

    review_backend = observed_backend(review_callback, "review-session-001")
    regeneration_backend = observed_backend(
        lambda *_: regeneration_items(), "generation-session-001"
    )
    result = engine(qa_authority, qa_request, regeneration_backend, review_backend).run()

    assert result.approved
    assert len(result.attempts) == 2
    assert len(result.rejections) == 1
    assert result.attempts[0]["candidate_sha256"] != result.attempts[1]["candidate_sha256"]
    assert result.attempts[1]["parent_rejection_sha256"] == sha256_json(result.rejections[0])
    assert result.attempts[1]["generation_provenance"]["origin"] == "M8_REGENERATION"
    assert len(result.invocations) == 3
    assert len(result.ai_reviews) == 2
    assert verify_run(publish(tmp_path, qa_authority, qa_request, result), qa_authority)["terminal_state"] == "DEVELOPMENT_APPROVED"


def test_retry_capture_policy_failure_publishes_and_verifies(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    class ParameterMismatchedBackend:
        def generate(self, *_args, **_kwargs) -> ModelCapture:
            return ModelCapture(
                regeneration_items(),
                "SESSION_CAPTURED",
                "UNKNOWN",
                "UNKNOWN",
                "generation-session-parameter-mismatch",
                {"temperature": 1},
            )

    qa_request = request(qa_authority, maximum_attempts=2)
    result = engine(
        qa_authority,
        qa_request,
        ParameterMismatchedBackend(),
        SessionModelBackend(lambda *_: review_response(approve=False, major_finding=True)),
    ).run()

    assert not result.approved
    assert "CAPTURE_PARAMETERS_MISMATCH" in {
        issue["code"] for issue in result.receipts[1][0]["issues"]
    }
    assert result.rejections[-1]["reason"] == "NON_REPAIRABLE_AUTHORITY_FAILURE"
    assert verify_run(
        publish(tmp_path, qa_authority, qa_request, result), qa_authority
    )["terminal_state"] == "REJECTED"


def test_malformed_regeneration_is_operational_evidence_with_retained_invocation(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority, maximum_attempts=2)
    result = engine(
        qa_authority,
        qa_request,
        SessionModelBackend(lambda *_: {"wrong": []}),
        SessionModelBackend(lambda *_: review_response(approve=False, major_finding=True)),
    ).run()

    assert not result.approved
    assert len(result.rejections) == 1
    assert len(result.operational_failures) == 1
    failure = result.operational_failures[0]
    assert failure["operation"] == "CANDIDATE_ASSEMBLY"
    assert failure["invocation_id"] is not None
    assert len(result.invocations) == 2
    assert verify_run(publish(tmp_path, qa_authority, qa_request, result), qa_authority)["terminal_state"] == "OPERATIONAL_FAILURE"


def test_verifier_rejects_orphan_and_tampered_manifest_records(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority)
    directory = publish(tmp_path, qa_authority, qa_request, engine(qa_authority, qa_request).run())
    (directory / "extra.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        verify_run(directory, qa_authority)


def test_publication_rejects_duplicate_receipt_stages(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority)
    result = engine(qa_authority, qa_request).run()
    with pytest.raises(ValueError, match="stages and sequences"):
        publish_run(
            tmp_path / "bad",
            authority=qa_authority,
            request=qa_request,
            attempts=result.attempts,
            receipts=(tuple([result.receipts[0][0]] * 6),),
            rejections=result.rejections,
            decision=result.decision,
            invocations=result.invocations,
            ai_reviews=result.ai_reviews,
            operational_failures=result.operational_failures,
        )




def test_receipt_construction_failure_retains_retry_invocation(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority, monkeypatch: pytest.MonkeyPatch
) -> None:
    qa_request = request(qa_authority, maximum_attempts=2)
    qa_engine = engine(
        qa_authority,
        qa_request,
        SessionModelBackend(
            lambda *_: regeneration_items(), provider_run_id="generation-001"
        ),
        SessionModelBackend(
            lambda *_: review_response(approve=False, major_finding=True),
            provider_run_id="review-001",
        ),
    )
    original_receipt = qa_engine._receipt

    def fail_retry_schema(attempt, stage, sequence, *args, **kwargs):
        if attempt["attempt_number"] == 2 and stage == "SCHEMA":
            raise ValueError("receipt construction failed")
        return original_receipt(attempt, stage, sequence, *args, **kwargs)

    monkeypatch.setattr(qa_engine, "_receipt", fail_retry_schema)
    result = qa_engine.run()

    assert result.operational_failures[0]["operation"] == "RECORD_CONSTRUCTION"
    assert result.operational_failures[0]["invocation_id"] == result.invocations[-1]["invocation_id"]
    assert verify_run(
        publish(tmp_path, qa_authority, qa_request, result), qa_authority
    )["terminal_state"] == "OPERATIONAL_FAILURE"


def test_record_construction_failure_is_terminal_operational_evidence(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority, monkeypatch: pytest.MonkeyPatch
) -> None:
    qa_request = request(qa_authority)
    qa_engine = engine(qa_authority, qa_request)

    def fail_decision(*_args, **_kwargs):
        raise ValueError("decision construction failed")

    monkeypatch.setattr(qa_engine, "_decision", fail_decision)
    result = qa_engine.run()

    assert not result.approved
    assert result.operational_failures[0]["operation"] == "RECORD_CONSTRUCTION"
    assert result.operational_failures[0]["candidate_attempt_id"] == result.attempts[0]["candidate_attempt_id"]
    assert verify_run(
        publish(tmp_path, qa_authority, qa_request, result), qa_authority
    )["terminal_state"] == "OPERATIONAL_FAILURE"


def test_record_construction_retains_last_known_safe_timestamp(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority)
    moments = iter(
        [
            datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 4, 6, 0, tzinfo=timezone.utc),
            datetime(2026, 9, 4, 5, 59, tzinfo=timezone.utc),
        ]
    )
    qa_engine = QaEngine(
        qa_authority, qa_request, clock=lambda: next(moments)
    )
    result = qa_engine.run()

    assert result.operational_failures[0]["operation"] == "RECORD_CONSTRUCTION"
    assert result.operational_failures[0]["occurred_at_source"] == "LAST_KNOWN_SAFE_TIMESTAMP"
    assert verify_run(
        publish(tmp_path, qa_authority, qa_request, result), qa_authority
    )["terminal_state"] == "OPERATIONAL_FAILURE"


def test_cli_verifies_run_directory_and_detects_tampering(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority)
    directory = publish(tmp_path, qa_authority, qa_request, engine(qa_authority, qa_request).run())
    assert cli_main(["verify", "--run-dir", str(directory)]) == 0
    receipt = directory / "attempt-001-receipt-06-language.json"
    receipt.write_text("{}\n", encoding="utf-8")
    assert cli_main(["verify", "--run-dir", str(directory)]) == 2



def test_answer_qa_rejects_incomplete_comprehension_mapping(
    qa_authority: VerifiedM7QaAuthority,
) -> None:
    candidate, _, _ = qa_authority.artifacts("B1-U05-L02")
    candidate = copy.deepcopy(candidate)
    reading = next(
        item for item in candidate["exercises"] if item["exercise_type"] == "reading"
    )
    reading["payload"]["answers"][0]["question_id"] = "missing-question"

    assert "COMPREHENSION_ANSWER_MAPPING_INVALID" in {
        item.code for item in answer_issues(candidate, qa_authority, "B1-U05-L02")
    }


def test_request_must_follow_the_verified_m7_batch(
    qa_authority: VerifiedM7QaAuthority,
) -> None:
    qa_request = qa_authority.request(
        LESSON_ID,
        created_at="2026-09-03T10:14:59Z",
    )

    with pytest.raises(ValueError, match="predate"):
        engine(qa_authority, qa_request).run()


def test_pre_capture_review_failure_is_publishable_operational_evidence(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    class FailingReviewBackend:
        def generate(self, *_args, **_kwargs) -> ModelCapture:
            raise TimeoutError("review service timed out before a response was captured")

    qa_request = request(qa_authority)
    result = engine(
        qa_authority, qa_request, review_backend=FailingReviewBackend()
    ).run()

    assert result.operational_failures[0]["operation"] == "AI_REVIEW_CAPTURE"
    assert result.operational_failures[0]["invocation_id"] is None
    assert verify_run(
        publish(tmp_path, qa_authority, qa_request, result), qa_authority
    )["terminal_state"] == "OPERATIONAL_FAILURE"


def test_session_callback_without_effective_configuration_is_non_promotable(
    qa_authority: VerifiedM7QaAuthority,
) -> None:
    qa_request = request(qa_authority, maximum_attempts=1)
    result = engine(
        qa_authority,
        qa_request,
        review_backend=SessionModelBackend(lambda *_: review_response(approve=True)),
    ).run()

    assert not result.approved
    assert "NON_PROMOTABLE_AI_REVIEW_EVIDENCE" in {
        issue["code"] for issue in result.receipts[0][-1]["issues"]
    }


def test_retry_attempt_construction_failure_retains_invocation(
    tmp_path: Path,
    qa_authority: VerifiedM7QaAuthority,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    qa_request = request(qa_authority, maximum_attempts=2)
    qa_engine = engine(
        qa_authority,
        qa_request,
        observed_backend(lambda *_: regeneration_items(), "generation-001"),
        observed_backend(
            lambda *_: review_response(approve=False, major_finding=True), "review-001"
        ),
    )
    original_attempt = qa_engine._attempt

    def fail_retry_attempt(candidate, *, number, **kwargs):
        if number == 2:
            raise ValueError("attempt record construction failed")
        return original_attempt(candidate, number=number, **kwargs)

    monkeypatch.setattr(qa_engine, "_attempt", fail_retry_attempt)
    result = qa_engine.run()

    failure = result.operational_failures[0]
    assert failure["operation"] == "RECORD_CONSTRUCTION"
    assert failure["invocation_id"] == result.invocations[-1]["invocation_id"]
    assert verify_run(
        publish(tmp_path, qa_authority, qa_request, result), qa_authority
    )["terminal_state"] == "OPERATIONAL_FAILURE"


def test_language_receipt_failure_retains_completed_review_as_record_failure(
    tmp_path: Path,
    qa_authority: VerifiedM7QaAuthority,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    qa_request = request(qa_authority)
    qa_engine = engine(
        qa_authority,
        qa_request,
        review_backend=observed_backend(
            lambda *_: review_response(approve=True), "review-001"
        ),
    )
    original_receipt = qa_engine._receipt
    calls = {"language": 0}

    def fail_first_language_receipt(attempt, stage, sequence, *args, **kwargs):
        if stage == "LANGUAGE":
            calls["language"] += 1
            if calls["language"] == 1:
                raise ValueError("language receipt construction failed")
        return original_receipt(attempt, stage, sequence, *args, **kwargs)

    monkeypatch.setattr(qa_engine, "_receipt", fail_first_language_receipt)
    result = qa_engine.run()

    assert result.operational_failures[0]["operation"] == "RECORD_CONSTRUCTION"
    assert result.operational_failures[0]["ai_review_id"] == result.ai_reviews[0]["ai_review_id"]
    assert verify_run(
        publish(tmp_path, qa_authority, qa_request, result), qa_authority
    )["terminal_state"] == "OPERATIONAL_FAILURE"


def test_verifier_rejects_a_root_directory_symlink(
    tmp_path: Path, qa_authority: VerifiedM7QaAuthority
) -> None:
    qa_request = request(qa_authority)
    directory = publish(tmp_path, qa_authority, qa_request, engine(qa_authority, qa_request).run())
    link = tmp_path / "run-link"
    try:
        link.symlink_to(directory, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable in this environment")

    with pytest.raises(ValueError, match="symlink"):
        verify_run(link, qa_authority)
