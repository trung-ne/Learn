from __future__ import annotations

from copy import deepcopy

import pytest

from english_master.independent_review.authority import ReviewSubject
from english_master.independent_review.review import CHECKLISTS
from english_master.lesson_generation.canonical import sha256_json
from english_master.revision_cycle.evidence import build_review_input
from english_master.revision_cycle.planning import build_revision_requests
from english_master.schema_validation import load_schema, validate_instance


def _subject(content_type: str, *, index: int, modality: str | None = None) -> ReviewSubject:
    return ReviewSubject(
        subject_id=f"m9sub_{index:064x}",
        content_type=content_type,
        lesson_id="A1-U01-L01",
        modality=modality,
        artifact_path=f"artifact-{index}.json",
        artifact={"kind": content_type, "index": index},
        audit_path=f"audit-{index}.json",
        audit={"result": "PASS", "index": index},
    )


def _review_input(subject: ReviewSubject, role: str, description: str, *, execution: str) -> dict[str, object]:
    selection = {"selection_id": f"m9select_{9:064x}"}
    report = {"reviewed_at": "2026-09-05T10:00:00Z", "subject_id": subject.subject_id}
    response = {
        "decision": "NEEDS_REVISION",
        "checklist": [
            {
                "criterion": criterion,
                "result": "FAIL" if position == 0 else "PASS",
                "notes": "Captured M9 finding evidence.",
            }
            for position, criterion in enumerate(CHECKLISTS[role])
        ],
        "findings": [
            {
                "severity": "MAJOR",
                "category": "LANGUAGE_ACCURACY",
                "description": description,
                "recommendation": "Replace the inaccurate sentence and recheck its target use.",
            }
        ],
        "limitations": ["This non-promotable review evidence is revision input only."],
    }
    return build_review_input(
        selection=selection,
        subject=subject,
        machine_report=report,
        role=role,
        capture={
            "capture_mode": "SESSION_CAPTURED",
            "provider": "UNVERIFIED_CAPTURE",
            "model": "UNKNOWN",
            "execution_id": execution,
            "provider_authenticated": False,
            "observed_at": "2026-09-05T10:01:00Z",
        },
        raw_response=response,
        observed_at="2026-09-05T10:01:00Z",
        imported_at="2026-09-05T10:02:00Z",
    )


def test_groups_verbatim_findings_and_builds_canonical_lesson_request() -> None:
    subject = _subject("LESSON", index=1)
    first = _review_input(subject, "LINGUISTIC_AI_REVIEWER", "The example uses the wrong verb form.", execution="capture-1")
    second = _review_input(subject, "PEDAGOGICAL_AI_REVIEWER", "The explanation precedes required context.", execution="capture-2")
    inputs = {str(second["input_id"]): second, str(first["input_id"]): first}

    actual = build_revision_requests(review_inputs=inputs, subjects={subject.subject_id: subject})
    repeated = build_revision_requests(review_inputs=dict(reversed(list(inputs.items()))), subjects=[subject])

    assert actual == repeated
    assert len(actual) == 1
    request = actual[0]
    validate_instance(request, "m10-revision-request")
    assert request["target_milestone"] == "M6"
    assert request["revision_number"] == 2
    assert request["predecessor"] == {
        "artifact_path": subject.artifact_path,
        "artifact_sha256": subject.artifact_sha256,
        "audit_path": subject.audit_path,
        "audit_sha256": subject.audit_sha256,
    }
    assert [item["input_id"] for item in request["source_inputs"]] == sorted(inputs)
    assert {item["input_sha256"] for item in request["source_inputs"]} == {sha256_json(first), sha256_json(second)}
    expected_findings = {
        (str(first["input_id"]), first["findings"][0]["description"]),
        (str(second["input_id"]), second["findings"][0]["description"]),
    }
    assert {(item["source_input_id"], item["finding"]["description"]) for item in request["findings"]} == expected_findings
    assert request["rebuild_closure"] == [
        {"target_milestone": "M7", "artifact_kind": "EXERCISE_SET", "scope": "SUBJECT_LESSON", "lesson_id": "A1-U01-L01"},
        {"target_milestone": "M8_2", "artifact_kind": "AI_PRACTICE_PILOT", "scope": "FULL_CLOSED_PILOT"},
    ]
    assert request["planning_only"] is True
    for boundary in ("successor_created", "lifecycle_transition_authorized", "approval_claim_authorized", "development_approved"):
        assert request[boundary] is False
    assert "human_reviewed" not in request
    assert "release_approved" not in request


def test_target_and_rebuild_closure_follow_subject_type() -> None:
    exercise = _subject("EXERCISE_SET", index=2)
    prompt = _subject("AI_PRACTICE_PROMPT", index=3, modality="LISTENING")
    exercise_input = _review_input(exercise, "LINGUISTIC_AI_REVIEWER", "One distractor is also correct.", execution="capture-3")
    prompt_input = _review_input(prompt, "PEDAGOGICAL_AI_REVIEWER", "The transcript is disclosed before the attempt.", execution="capture-4")

    requests = build_revision_requests(
        review_inputs=[prompt_input, exercise_input],
        subjects=[exercise, prompt],
    )
    by_type = {request["content_type"]: request for request in requests}
    assert by_type["EXERCISE_SET"]["target_milestone"] == "M7"
    assert by_type["EXERCISE_SET"]["rebuild_closure"] == [
        {"target_milestone": "M7", "artifact_kind": "EXERCISE_SET", "scope": "SUBJECT_LESSON", "lesson_id": "A1-U01-L01"}
    ]
    assert by_type["AI_PRACTICE_PROMPT"]["target_milestone"] == "M8_2"
    assert by_type["AI_PRACTICE_PROMPT"]["modality"] == "LISTENING"
    assert by_type["AI_PRACTICE_PROMPT"]["rebuild_closure"] == [
        {"target_milestone": "M8_2", "artifact_kind": "AI_PRACTICE_PILOT", "scope": "FULL_CLOSED_PILOT"}
    ]


def test_rejects_input_drift_and_finding_free_input() -> None:
    subject = _subject("LESSON", index=4)
    source = _review_input(subject, "LINGUISTIC_AI_REVIEWER", "The target form is inaccurate.", execution="capture-5")
    drifted = deepcopy(source)
    drifted["artifact_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="identity drift"):
        build_revision_requests(review_inputs=[drifted], subjects=[subject])

    finding_free = deepcopy(source)
    finding_free["findings"] = []
    finding_free["raw_response"]["findings"] = []
    from english_master.lesson_generation.canonical import identity, sha256_json

    finding_free["raw_response_sha256"] = sha256_json(finding_free["raw_response"])
    finding_free["input_id"] = identity("m10input", finding_free, "input_id")
    with pytest.raises(ValueError, match="at least one verbatim finding"):
        build_revision_requests(review_inputs=[finding_free], subjects=[subject])


def test_revision_request_schema_is_registered() -> None:
    assert load_schema("m10-revision-request")["$id"].endswith("m10-revision-request.schema.json")
