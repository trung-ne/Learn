"""Host-built prompts, invocation evidence, candidates, and M8 AI reviews."""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from english_master.exercise_generation.builders import build_authorization, build_request
from english_master.exercise_generation.validator import backend_candidate_issues
from english_master.lesson_generation.canonical import (
    canonical_json,
    identity,
    sha256_json,
    sha256_text,
)
from english_master.schema_validation import validate_instance

from .authority import VerifiedM7QaAuthority
from .models import ModelCapture, QaIssue, REVIEW_CRITERIA, ReviewEvidence

REGENERATION_PROMPT_VERSION = "M8_REGENERATION_v1"
REVIEW_PROMPT_VERSION = "M8_COMPREHENSIVE_AI_REVIEW_v1"


def build_regeneration_prompt(
    request: Mapping[str, Any],
    prior_candidate: Mapping[str, Any],
    rejection: Mapping[str, Any],
    generation_request: Mapping[str, Any],
) -> str:
    payload = {
        "qa_request": request,
        "prior_candidate": prior_candidate,
        "rejection": rejection,
        "generation_authority": generation_request,
    }
    return (
        "Return exactly one JSON object containing only an items array. Create a new "
        "immutable exercise-set revision that resolves every repair constraint. Preserve "
        "the trusted scope and do not emit IDs, provenance, statuses, media, approvals, "
        "AI tutors, or evaluator behavior. INPUT=" + canonical_json(payload)
    )


def build_review_prompt(
    request: Mapping[str, Any],
    attempt: Mapping[str, Any],
    machine_receipts: Sequence[Mapping[str, Any]],
) -> str:
    payload = {
        "qa_request": request,
        "candidate_attempt": attempt,
        "machine_receipts": list(machine_receipts),
        "required_criteria": list(REVIEW_CRITERIA),
    }
    return (
        "Independently review the candidate for development QA. Return exactly one JSON "
        "object with decision, criteria, findings, and limitations. Criteria must appear "
        "once in the supplied order and use PASS or FAIL with a rationale. Findings use "
        "code, path, message, and INFO|MINOR|MAJOR|CRITICAL severity. Do not claim human "
        "review, release approval, provider authentication, CEFR certification, or an "
        "Internet-wide originality search. INPUT=" + canonical_json(payload)
    )


def build_invocation(
    *,
    request: Mapping[str, Any],
    purpose: str,
    attempt_number: int,
    candidate_attempt_id: str | None,
    parent_rejection_sha256: str | None,
    repair_constraints: Sequence[Mapping[str, Any]],
    prompt: str,
    capture: ModelCapture,
    parameters: Mapping[str, Any],
    seed: int | None,
    observed_at: str,
) -> dict[str, Any]:
    if not isinstance(capture, ModelCapture):
        raise ValueError("backend must return ModelCapture")
    reported_capture_mode = (
        capture.capture_mode
        if isinstance(capture.capture_mode, str) and capture.capture_mode
        else "INVALID"
    )
    capture_mode = (
        reported_capture_mode
        if reported_capture_mode
        in {
            "SESSION_CAPTURED",
            "PROVIDER_CAPTURED",
            "REPLAY_CAPTURED",
            "TEST_ONLY",
        }
        else "UNSUPPORTED"
    )
    captured_parameters = (
        copy.deepcopy(dict(capture.parameters))
        if isinstance(capture.parameters, Mapping)
        else None
    )
    parameters_match = (
        captured_parameters is not None and captured_parameters == dict(parameters)
    )
    seed_match = capture.seed_observed and capture.seed == seed
    provider = capture.provider if isinstance(capture.provider, str) and capture.provider else "UNKNOWN"
    model = capture.model if isinstance(capture.model, str) and capture.model else "UNKNOWN"
    provider_run_id = (
        capture.provider_run_id
        if isinstance(capture.provider_run_id, str) and capture.provider_run_id
        else "UNKNOWN"
    )
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "qa_engine_model_invocation",
        "invocation_id": "PENDING",
        "engine_run_id": request["engine_run_id"],
        "purpose": purpose,
        "attempt_number": attempt_number,
        "candidate_attempt_id": candidate_attempt_id,
        "parent_rejection_sha256": parent_rejection_sha256,
        "qa_request_sha256": sha256_json(request),
        "repair_constraints_sha256": sha256_json(list(repair_constraints)),
        "capture_mode": capture_mode,
        "reported_capture_mode": reported_capture_mode,
        "prompt": prompt,
        "prompt_sha256": sha256_text(prompt),
        "response": copy.deepcopy(dict(capture.content)),
        "response_sha256": sha256_json(capture.content),
        "provider": provider,
        "model": model,
        "provider_run_id": provider_run_id,
        "parameters": copy.deepcopy(dict(parameters)),
        "captured_parameters": captured_parameters,
        "parameters_match": parameters_match,
        "seed": seed,
        "captured_seed": capture.seed,
        "seed_observed": capture.seed_observed,
        "seed_match": seed_match,
        "observed_at": observed_at,
        "reported_provider_authenticated": bool(capture.provider_authenticated),
        "provider_authenticated": False,
    }
    value["invocation_id"] = identity("qaeinvoke", value, "invocation_id")
    validate_instance(value, "qa-engine-model-invocation")
    return value


def _generation_metadata(
    generation_request: Mapping[str, Any],
    invocation: Mapping[str, Any],
) -> dict[str, Any]:
    config = generation_request["generation_config"]
    value: dict[str, Any] = {
        "generator": "english_master.qa_engine.regenerator",
        "generator_version": "1.0",
        "prompt_version": REGENERATION_PROMPT_VERSION,
        "generated_at": invocation["observed_at"],
        "curriculum_version": config["curriculum_version"],
        "qa_status": "UNREVIEWED",
        "qa_notes": "M8 regeneration; ordered QA and independent AI review remain required.",
    }
    if invocation["model"] != "UNKNOWN":
        value["model"] = invocation["model"]
    return value


def assemble_regenerated_candidate(
    authority: VerifiedM7QaAuthority,
    lesson_id: str,
    response: Mapping[str, Any],
    invocation: Mapping[str, Any],
) -> dict[str, Any]:
    issues = backend_candidate_issues(response)
    if issues:
        raise ValueError(
            "; ".join(f"{item.code}: {item.message}" for item in issues)
        )
    generation_request = build_request(
        authority.m6, build_authorization(authority.m6), lesson_id
    ).as_dict()
    binding = generation_request["lesson_binding"]
    spec = generation_request["lesson_spec"]
    metadata = _generation_metadata(generation_request, invocation)
    exercises: list[dict[str, Any]] = []
    for sequence, item in enumerate(response["items"], 1):
        exercises.append(
            {
                "id": f"ex_{lesson_id}_{sequence:03d}",
                "sequence": sequence,
                "title": item["title"],
                "exercise_type": item["exercise_type"],
                "cefr_level": spec["cefr_level"],
                "difficulty": item["difficulty"],
                "instructions": item["instructions"],
                "objective_indices": copy.deepcopy(item["objective_indices"]),
                "target_references": sorted(item["target_references"]),
                "review_references": sorted(item["review_references"]),
                "scoring_mode": item["scoring_mode"],
                "payload": copy.deepcopy(item["payload"]),
                "generation_metadata": copy.deepcopy(metadata),
            }
        )
    source_set, _, _ = authority.artifacts(lesson_id)
    value: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "exercise_set",
        "exercise_set_id": "PENDING",
        "request_id": source_set["request_id"],
        "lesson_id": lesson_id,
        "lesson_sha256": binding["lesson_sha256"],
        "m6_batch_id": generation_request["m6_batch_id"],
        "status": "UNREVIEWED",
        "exercises": exercises,
        "output_sha256": "PENDING",
        "provenance": {
            "origin": "PROJECT_AUTHORED",
            "external_payload_used": False,
            "media_used": False,
            "notes": "Regenerated from trusted M8 constraints without external payloads.",
        },
        "generation_metadata": copy.deepcopy(metadata),
    }
    identity_base = copy.deepcopy(value)
    identity_base.pop("exercise_set_id")
    identity_base.pop("output_sha256")
    digest = sha256_json(identity_base)
    value["output_sha256"] = digest
    value["exercise_set_id"] = f"m7set_{digest}"
    return value


def _review_response_issues(response: Mapping[str, Any]) -> tuple[QaIssue, ...]:
    issues: list[QaIssue] = []
    if set(response) != {"decision", "criteria", "findings", "limitations"}:
        issues.append(
            QaIssue(
                "AI_REVIEW_RESPONSE_INVALID",
                "$",
                "review response must contain only decision, criteria, findings, and limitations",
                "CRITICAL",
            )
        )
        return tuple(issues)
    criteria = response.get("criteria")
    if not isinstance(criteria, list) or len(criteria) != len(REVIEW_CRITERIA):
        issues.append(
            QaIssue(
                "AI_REVIEW_CRITERIA_INVALID",
                "$.criteria",
                "review must contain all required criteria exactly once in order",
                "CRITICAL",
            )
        )
    else:
        for index, (item, expected) in enumerate(zip(criteria, REVIEW_CRITERIA)):
            if not isinstance(item, Mapping) or set(item) != {
                "criterion",
                "result",
                "rationale",
            }:
                issues.append(
                    QaIssue(
                        "AI_REVIEW_CRITERION_INVALID",
                        f"$.criteria[{index}]",
                        "criterion must contain criterion, result, and rationale only",
                        "CRITICAL",
                    )
                )
                continue
            if item.get("criterion") != expected or item.get("result") not in {
                "PASS",
                "FAIL",
            } or not isinstance(item.get("rationale"), str) or not item["rationale"]:
                issues.append(
                    QaIssue(
                        "AI_REVIEW_CRITERION_INVALID",
                        f"$.criteria[{index}]",
                        f"criterion must be {expected} with a result and rationale",
                        "CRITICAL",
                    )
                )
    findings = response.get("findings")
    if not isinstance(findings, list):
        issues.append(QaIssue("AI_REVIEW_FINDINGS_INVALID", "$.findings", "findings must be an array", "CRITICAL"))
    else:
        for index, finding in enumerate(findings):
            if not isinstance(finding, Mapping) or set(finding) != {
                "code",
                "path",
                "message",
                "severity",
            } or finding.get("severity") not in {"INFO", "MINOR", "MAJOR", "CRITICAL"}:
                issues.append(QaIssue("AI_REVIEW_FINDING_INVALID", f"$.findings[{index}]", "finding shape or severity is invalid", "CRITICAL"))
    limitations = response.get("limitations")
    if not isinstance(limitations, list) or not limitations or any(
        not isinstance(item, str) or not item for item in limitations
    ):
        issues.append(QaIssue("AI_REVIEW_LIMITATIONS_INVALID", "$.limitations", "limitations must contain nonempty strings", "CRITICAL"))
    if response.get("decision") not in {"APPROVE", "REQUEST_REVISION"}:
        issues.append(QaIssue("AI_REVIEW_DECISION_INVALID", "$.decision", "decision must be APPROVE or REQUEST_REVISION", "CRITICAL"))
    return tuple(issues)


def build_candidate_bound_review(
    *,
    request: Mapping[str, Any],
    attempt: Mapping[str, Any],
    machine_receipts: Sequence[Mapping[str, Any]],
    invocation: Mapping[str, Any],
    generation_invocation: Mapping[str, Any] | None,
) -> ReviewEvidence:
    response = invocation["response"]
    issues = list(_review_response_issues(response))
    findings = response.get("findings", []) if isinstance(response, Mapping) else []
    if isinstance(findings, list):
        for item in findings:
            if isinstance(item, Mapping) and set(item) >= {"code", "path", "message", "severity"}:
                issues.append(QaIssue(str(item["code"]), str(item["path"]), str(item["message"]), str(item["severity"])))
    criteria = response.get("criteria", []) if isinstance(response, Mapping) else []
    if isinstance(criteria, list):
        for index, item in enumerate(criteria):
            if isinstance(item, Mapping) and item.get("result") == "FAIL":
                issues.append(
                    QaIssue(
                        "AI_REVIEW_CRITERION_FAILED",
                        f"$.criteria[{index}]",
                        str(item.get("rationale", "semantic review criterion failed")),
                    )
                )
    criteria_pass = isinstance(criteria, list) and len(criteria) == 4 and all(
        isinstance(item, Mapping) and item.get("result") == "PASS"
        for item in criteria
    )
    blocking = any(item.severity in {"MAJOR", "CRITICAL"} for item in issues)
    promotable_capture = (
        invocation["capture_mode"] in {"SESSION_CAPTURED", "PROVIDER_CAPTURED"}
        and invocation["provider"] != "TEST_ONLY_MOCK"
        and invocation["parameters_match"]
        and invocation["seed_match"]
        and not invocation["reported_provider_authenticated"]
    )
    if not promotable_capture:
        issues.append(
            QaIssue(
                "NON_PROMOTABLE_AI_REVIEW_EVIDENCE",
                "$.invocation",
                "replay, test, unsupported, parameter-mismatched, or provider-authentication-asserting AI review evidence cannot support development promotion",
                "CRITICAL",
            )
        )
        blocking = True
    independent_execution = (
        generation_invocation is not None
        and generation_invocation.get("provider_run_id") not in {None, "", "UNKNOWN"}
        and invocation.get("provider_run_id") not in {None, "", "UNKNOWN"}
        and generation_invocation.get("provider_run_id") != invocation.get("provider_run_id")
    )
    if not independent_execution:
        issues.append(
            QaIssue(
                "INDEPENDENCE_NOT_ESTABLISHED",
                "$.invocation.provider_run_id",
                "distinct factual generation and review execution identities are required before AI independence can be asserted",
                "CRITICAL",
            )
        )
        blocking = True
    passed = (
        not _review_response_issues(response)
        and response.get("decision") == "APPROVE"
        and criteria_pass
        and not blocking
        and promotable_capture
        and independent_execution
    )
    review: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "qa_engine_ai_review",
        "ai_review_id": "PENDING",
        "engine_run_id": request["engine_run_id"],
        "candidate_attempt_id": attempt["candidate_attempt_id"],
        "candidate_sha256": attempt["candidate_sha256"],
        "qa_request_sha256": sha256_json(request),
        "m7_batch_id": request["m7_batch_id"],
        "machine_receipt_sha256s": [sha256_json(item) for item in machine_receipts],
        "evidence_kind": "M8_CANDIDATE_BOUND",
        "invocation_id": invocation["invocation_id"],
        "invocation_sha256": sha256_json(invocation),
        "source_review_sha256s": [],
        "source_reviewed_ats": [],
        "reviewer_type": "AI",
        "review_role": "COMPREHENSIVE_AI_REVIEWER",
        "independent_of_generation": independent_execution,
        "criteria": copy.deepcopy(criteria) if isinstance(criteria, list) else [],
        "findings": copy.deepcopy(findings) if isinstance(findings, list) else [],
        "decision": response.get("decision", "REQUEST_REVISION"),
        "reviewed_at": invocation["observed_at"],
        "approval_tier": "AI_REVIEWED",
        "content_lifecycle_status": "UNREVIEWED",
        "human_reviewed": False,
        "release_approved": False,
        "limitations": list(dict.fromkeys(
            (response.get("limitations", []) if isinstance(response.get("limitations"), list) else [])
            + [
                "This is AI-only development evidence, not human review or release approval.",
                "Session hashes do not cryptographically authenticate a provider or model.",
            ]
        )),
    }
    # A malformed response is retained in its invocation but cannot form a schema-valid review.
    if _review_response_issues(response):
        return ReviewEvidence(False, tuple(issues), "UNBOUND", "qaeaireview_" + "0" * 64, "0" * 64, None, invocation)
    review["ai_review_id"] = identity("qaeaireview", review, "ai_review_id")
    validate_instance(review, "qa-engine-ai-review")
    return ReviewEvidence(
        passed,
        tuple(issues),
        "M8_CANDIDATE_BOUND",
        review["ai_review_id"],
        sha256_json(review),
        review,
        invocation,
    )
