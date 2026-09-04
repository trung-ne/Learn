"""Independent reconstruction and verification of an M8 terminal run directory."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_document
from english_master.exercise_generation.builders import build_authorization, build_request
from english_master.lesson_generation.canonical import identity, sha256_json, sha256_text
from english_master.schema_validation import validate_instance

from .authority import VerifiedM7QaAuthority
from .evidence import (
    assemble_regenerated_candidate,
    build_candidate_bound_review,
    build_regeneration_prompt,
    build_review_prompt,
)
from .models import QaIssue, STAGE_CONTRACT
from .projection import NEAR_POLICY_VERSION, PROJECTION_VERSION
from .reviewers import BoundM7LanguageReviewer
from .time import ensure_not_after, orderable_timestamp
from .validators import (
    answer_issues,
    cefr_issues,
    duplicate_issues,
    prerequisite_issues,
    regeneration_evidence_issues,
    schema_issues,
)
_NON_REPAIRABLE_CODES = {
    "AUTHORITY_INVALID",
    "CONTENT_STATUS_INVALID",
    "EXERCISE_ID_INVALID",
    "EXERCISE_STATUS_INVALID",
    "LESSON_BINDING_MISMATCH",
    "M6_BATCH_BINDING_MISMATCH",
    "M7_REQUEST_BINDING_MISMATCH",
    "SET_GENERATION_STATUS_INVALID",
    "REGENERATION_EVIDENCE_NOT_PROMOTABLE",
    "CAPTURE_PARAMETERS_MISMATCH",
    "UNVERIFIED_PROVIDER_AUTHENTICATION_CLAIM",
}


def _expected_rejection_reason(
    receipts: list[Mapping[str, Any]], attempt_number: int, maximum_attempts: int
) -> str:
    if any(
        issue["code"] in _NON_REPAIRABLE_CODES
        for receipt in receipts
        for issue in receipt["issues"]
    ):
        return "NON_REPAIRABLE_AUTHORITY_FAILURE"
    if attempt_number >= maximum_attempts:
        return "RETRY_LIMIT_EXHAUSTED"
    return "CONTENT_QA_FAILED"


def _load_inventory(directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("run directory must be a real directory, not a symlink")
    manifest_path = directory / "run-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("run manifest is missing or unsafe")
    manifest = load_strict_document(manifest_path)
    validate_instance(manifest, "qa-engine-run-manifest")
    if manifest["run_manifest_id"] != identity(
        "qaemanifest", manifest, "run_manifest_id"
    ):
        raise ValueError("run manifest identity is not canonical")
    references = manifest["files"]
    paths = [item["path"] for item in references]
    if len(paths) != len(set(paths)):
        raise ValueError("run manifest contains duplicate paths")
    expected_names = set(paths) | {"run-manifest.json"}
    actual_names: set[str] = set()
    for path in directory.iterdir():
        if path.is_symlink() or not path.is_file():
            raise ValueError("run directory contains an unsafe or non-file entry")
        actual_names.add(path.name)
    if actual_names != expected_names:
        raise ValueError("run directory inventory differs from its manifest")
    loaded: dict[str, Any] = {}
    for reference in references:
        path = directory / reference["path"]
        if path.parent != directory or path.is_symlink():
            raise ValueError("manifest path is unsafe")
        value = load_strict_document(path)
        if sha256_json(value) != reference["sha256"]:
            raise ValueError(f"manifest hash mismatch: {path.name}")
        loaded[path.name] = value
    return manifest, loaded


def _canonical(value: Mapping[str, Any], schema: str, prefix: str, field: str) -> None:
    validate_instance(value, schema)
    if value[field] != identity(prefix, value, field):
        raise ValueError(f"{schema} identity is not canonical")


def _verify_invocation(
    invocation: Mapping[str, Any],
    *,
    request: Mapping[str, Any],
    purpose: str,
    attempt_number: int,
    candidate_attempt_id: str | None,
    parent_rejection_sha256: str | None,
    repair_constraints_sha256: str,
    parameters: Mapping[str, Any],
    seed: int | None,
) -> None:
    reported_mode = invocation["reported_capture_mode"]
    expected_mode = (
        reported_mode
        if reported_mode in {"SESSION_CAPTURED", "PROVIDER_CAPTURED", "REPLAY_CAPTURED", "TEST_ONLY"}
        else "UNSUPPORTED"
    )
    if invocation["capture_mode"] != expected_mode:
        raise ValueError("invocation capture mode is not the canonical reported-mode projection")
    captured_parameters = invocation["captured_parameters"]
    if invocation["parameters_match"] != (
        isinstance(captured_parameters, Mapping)
        and captured_parameters == invocation["parameters"]
    ):
        raise ValueError("invocation parameter-match assertion is not reconstructable")
    if invocation["seed_match"] != (
        invocation["seed_observed"] is True
        and invocation["captured_seed"] == invocation["seed"]
    ):
        raise ValueError("invocation seed-match assertion is not reconstructable")
    if (
        invocation["engine_run_id"] != request["engine_run_id"]
        or invocation["qa_request_sha256"] != sha256_json(request)
        or invocation["purpose"] != purpose
        or invocation["attempt_number"] != attempt_number
        or invocation["candidate_attempt_id"] != candidate_attempt_id
        or invocation["parent_rejection_sha256"] != parent_rejection_sha256
        or invocation["repair_constraints_sha256"] != repair_constraints_sha256
        or invocation["parameters"] != dict(parameters)
        or invocation["seed"] != seed
        or invocation["provider_authenticated"] is not False
    ):
        raise ValueError("invocation scope or trusted configuration is invalid")


def _expected_machine_issues(
    stage: str,
    attempt: Mapping[str, Any],
    authority: VerifiedM7QaAuthority,
    request: Mapping[str, Any],
    prior_attempts: list[Mapping[str, Any]],
) -> tuple[QaIssue, ...]:
    candidate = attempt["candidate"]
    functions = {
        "SCHEMA": lambda: schema_issues(candidate, authority, request["lesson_id"]),
        "ANSWER": lambda: answer_issues(candidate, authority, request["lesson_id"]),
        "CEFR": lambda: cefr_issues(candidate, authority, request["lesson_id"]),
        "PREREQUISITE": lambda: prerequisite_issues(candidate, authority, request["lesson_id"]),
        "DUPLICATE": lambda: duplicate_issues(
            candidate,
            authority,
            request["lesson_id"],
            [item["candidate"] for item in prior_attempts],
        ),
    }
    issues = tuple(functions[stage]())
    return issues


def _validate_timestamp(value: object, verification_at: str, path: str) -> None:
    if isinstance(value, str):
        ensure_not_after(value, verification_at, f"future-dated evidence at {path}")


def _validate_recorded_times(
    value: object,
    verification_at: str,
    *,
    path: str = "$",
) -> None:
    """Check only contract-defined audit timestamps, never authored free text."""
    if not isinstance(value, Mapping):
        return
    record_type = value.get("record_type")
    fields = {
        "qa_engine_run_manifest": ("terminal_at",),
        "qa_engine_request": ("created_at",),
        "qa_engine_candidate_attempt": ("created_at",),
        "qa_engine_stage_receipt": ("checked_at",),
        "qa_engine_model_invocation": ("observed_at",),
        "qa_engine_ai_review": ("reviewed_at",),
        "qa_engine_rejection": ("rejected_at",),
        "qa_engine_operational_failure": ("occurred_at",),
        "qa_engine_decision": ("decided_at",),
    }.get(record_type, ())
    for field in fields:
        _validate_timestamp(value.get(field), verification_at, f"{path}.{field}")
    if record_type == "qa_engine_candidate_attempt":
        provenance = value.get("generation_provenance")
        if isinstance(provenance, Mapping):
            _validate_timestamp(
                provenance.get("observed_at"),
                verification_at,
                f"{path}.generation_provenance.observed_at",
            )
        candidate = value.get("candidate")
        if isinstance(candidate, Mapping):
            metadata = candidate.get("generation_metadata")
            if isinstance(metadata, Mapping):
                _validate_timestamp(
                    metadata.get("generated_at"),
                    verification_at,
                    f"{path}.candidate.generation_metadata.generated_at",
                )
            exercises = candidate.get("exercises")
            if isinstance(exercises, list):
                for index, exercise in enumerate(exercises):
                    if isinstance(exercise, Mapping) and isinstance(
                        exercise.get("generation_metadata"), Mapping
                    ):
                        _validate_timestamp(
                            exercise["generation_metadata"].get("generated_at"),
                            verification_at,
                            f"{path}.candidate.exercises[{index}].generation_metadata.generated_at",
                        )
    elif record_type == "qa_engine_ai_review":
        source_reviewed_ats = value.get("source_reviewed_ats")
        if isinstance(source_reviewed_ats, list):
            for index, timestamp in enumerate(source_reviewed_ats):
                _validate_timestamp(
                    timestamp,
                    verification_at,
                    f"{path}.source_reviewed_ats[{index}]",
                )


def verify_run(
    directory: Path,
    authority: VerifiedM7QaAuthority,
    *,
    verified_at: str | None = None,
) -> dict[str, Any]:
    if directory.is_symlink():
        raise ValueError("run directory must be a real directory, not a symlink")
    directory = directory.resolve()
    manifest, files = _load_inventory(directory)
    verification_at = verified_at or datetime.now(timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
    orderable_timestamp(verification_at)
    _validate_recorded_times(manifest, verification_at, path="$.run_manifest")
    for name, value in files.items():
        _validate_recorded_times(value, verification_at, path=f"$.files[{name!r}]")
    request = files.get("request.json")
    if not isinstance(request, Mapping):
        raise ValueError("published request is missing")
    _canonical(request, "qa-engine-request", "qaerun", "engine_run_id")
    expected_request = authority.request(
        request["lesson_id"],
        created_at=request["created_at"],
        maximum_attempts=request["maximum_attempts"],
    )
    if request != expected_request:
        raise ValueError("published request differs from verified M7 authority")
    if manifest["engine_run_id"] != request["engine_run_id"] or manifest[
        "request_sha256"
    ] != sha256_json(request):
        raise ValueError("manifest does not bind its request")
    orderable_timestamp(request["created_at"])
    ensure_not_after(
        authority.authority_available_at(),
        request["created_at"],
        "M8 request predates the verified M7 development batch",
    )

    attempts = [
        files[name]
        for name in sorted(files)
        if name.endswith("-candidate-attempt.json")
    ]
    receipts_by_attempt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    invocations: dict[str, dict[str, Any]] = {}
    reviews: dict[str, dict[str, Any]] = {}
    rejections = [
        value
        for name, value in files.items()
        if name.startswith("rejection-")
    ]
    operational = [
        value
        for name, value in files.items()
        if name.startswith("operational-failure-")
    ]
    decision = files.get("decision.json")

    for name, value in files.items():
        if "-receipt-" in name:
            _canonical(value, "qa-engine-stage-receipt", "qaereceipt", "receipt_id")
            receipts_by_attempt[value["candidate_attempt_id"]].append(value)
        elif name.startswith("invocation-"):
            _canonical(value, "qa-engine-model-invocation", "qaeinvoke", "invocation_id")
            if name != f"invocation-{value['invocation_id']}.json":
                raise ValueError("invocation filename differs from its identity")
            invocations[value["invocation_id"]] = value
        elif name.startswith("ai-review-"):
            _canonical(value, "qa-engine-ai-review", "qaeaireview", "ai_review_id")
            if name != f"ai-review-{value['ai_review_id']}.json":
                raise ValueError("AI review filename differs from its identity")
            reviews[value["ai_review_id"]] = value
        elif name.startswith("operational-failure-"):
            _canonical(
                value,
                "qa-engine-operational-failure",
                "qaeopfail",
                "operational_failure_id",
            )
            if name != f"operational-failure-{value['operational_failure_id']}.json":
                raise ValueError("operational-failure filename differs from its identity")
        elif name.startswith("rejection-"):
            _canonical(value, "qa-engine-rejection", "qaereject", "rejection_id")
        elif name == "decision.json":
            _canonical(value, "qa-engine-decision", "qaedecision", "decision_id")
        elif name != "request.json" and not name.endswith("-candidate-attempt.json"):
            raise ValueError(f"unrecognized run file: {name}")

    rejections.sort(key=lambda item: item["attempt_number"])

    for attempt in attempts:
        _canonical(attempt, "qa-engine-candidate-attempt", "qaeattempt", "candidate_attempt_id")
    if len(attempts) > request["maximum_attempts"]:
        raise ValueError("run exceeds its maximum attempt limit")
    attempt_ids = {item["candidate_attempt_id"] for item in attempts}
    if set(receipts_by_attempt) - attempt_ids:
        raise ValueError("run contains receipts for an unknown candidate attempt")
    source_set, _, _ = authority.artifacts(request["lesson_id"])
    used_invocations: set[str] = set()
    used_reviews: set[str] = set()
    previous_terminal_time = request["created_at"]
    for index, attempt in enumerate(attempts, 1):
        _canonical(attempt, "qa-engine-candidate-attempt", "qaeattempt", "candidate_attempt_id")
        expected_attempt_name = f"attempt-{index:03d}-candidate-attempt.json"
        if files.get(expected_attempt_name) != attempt:
            raise ValueError("candidate-attempt filename or order is invalid")
        if attempt["attempt_number"] != index or attempt["engine_run_id"] != request["engine_run_id"]:
            raise ValueError("candidate-attempt order or run binding is invalid")
        if sha256_json(attempt["candidate"]) != attempt["candidate_sha256"]:
            raise ValueError("candidate hash differs from its payload")
        provenance = attempt["generation_provenance"]
        retry_invocation: Mapping[str, Any] | None = None
        if provenance["qa_request_sha256"] != sha256_json(request):
            raise ValueError("candidate provenance does not bind the request")
        ensure_not_after(previous_terminal_time, attempt["created_at"], "attempt predates its request or parent rejection")
        ensure_not_after(provenance["observed_at"], attempt["created_at"], "attempt predates its source observation")
        if index == 1:
            if attempt["candidate"] != source_set or attempt["candidate_sha256"] != request["exercise_set_sha256"]:
                raise ValueError("first attempt is not the exact verified M7 candidate")
            expected_provenance = {
                "origin": "M7_AUTHORITY",
                "source_sha256": sha256_json(source_set),
                "invocation_id": None,
                "invocation_sha256": None,
                "capture_mode": "M7_AUTHORITY",
                "observed_at": source_set["generation_metadata"]["generated_at"],
                "qa_request_sha256": sha256_json(request),
                "repair_constraints_sha256": sha256_json([]),
                "provider_authenticated": False,
            }
            if provenance != expected_provenance or attempt["parent_rejection_sha256"] is not None:
                raise ValueError("first attempt provenance is not authority-derived")
            ensure_not_after(provenance["observed_at"], request["created_at"], "M7 source postdates its M8 request")
        else:
            if len(rejections) < index - 1:
                raise ValueError("retry is missing its parent rejection")
            parent = rejections[index - 2]
            if attempt["parent_rejection_sha256"] != sha256_json(parent):
                raise ValueError("retry does not bind its parent rejection")
            invocation = invocations.get(provenance["invocation_id"])
            if invocation is None:
                raise ValueError("retry generation invocation is missing")
            retry_invocation = invocation
            used_invocations.add(invocation["invocation_id"])
            if provenance["invocation_sha256"] != sha256_json(invocation):
                raise ValueError("retry invocation hash is invalid")
            if invocation["purpose"] != "REGENERATION" or invocation["attempt_number"] != index:
                raise ValueError("retry invocation purpose or attempt number is invalid")
            if invocation["parent_rejection_sha256"] != sha256_json(parent):
                raise ValueError("retry invocation does not bind the parent rejection")
            if invocation["repair_constraints_sha256"] != parent["repair_constraints_sha256"] or provenance["repair_constraints_sha256"] != parent["repair_constraints_sha256"]:
                raise ValueError("retry does not bind exact repair constraints")
            ensure_not_after(parent["rejected_at"], invocation["observed_at"], "retry invocation predates rejection")
            generation_request = build_request(
                authority.m6,
                build_authorization(authority.m6),
                request["lesson_id"],
            ).as_dict()
            _verify_invocation(
                invocation,
                request=request,
                purpose="REGENERATION",
                attempt_number=index,
                candidate_attempt_id=None,
                parent_rejection_sha256=sha256_json(parent),
                repair_constraints_sha256=parent["repair_constraints_sha256"],
                parameters=generation_request["generation_config"]["parameters"],
                seed=generation_request["generation_config"]["seed"],
            )
            expected_prompt = build_regeneration_prompt(
                request, attempts[index - 2]["candidate"], parent, generation_request
            )
            if invocation["prompt"] != expected_prompt or invocation["prompt_sha256"] != sha256_text(expected_prompt):
                raise ValueError("retry prompt is not reconstructable")
            if invocation["response_sha256"] != sha256_json(invocation["response"]):
                raise ValueError("retry response hash is invalid")
            reconstructed = assemble_regenerated_candidate(
                authority, request["lesson_id"], invocation["response"], invocation
            )
            if attempt["candidate"] != reconstructed:
                raise ValueError("retry candidate is not reconstructable from raw response")
            expected_provenance = {
                "origin": "M8_REGENERATION",
                "source_sha256": invocation["response_sha256"],
                "invocation_id": invocation["invocation_id"],
                "invocation_sha256": sha256_json(invocation),
                "capture_mode": invocation["capture_mode"],
                "observed_at": invocation["observed_at"],
                "qa_request_sha256": sha256_json(request),
                "repair_constraints_sha256": parent["repair_constraints_sha256"],
                "provider_authenticated": False,
            }
            if provenance != expected_provenance:
                raise ValueError("retry provenance differs from reconstructed evidence")

        group = sorted(receipts_by_attempt.get(attempt["candidate_attempt_id"], []), key=lambda item: item["sequence"])
        if len(group) != 6:
            raise ValueError("each attempt requires exactly six receipts")
        failed = False
        receipt_time = attempt["created_at"]
        for stage, sequence, reviewer_type in STAGE_CONTRACT:
            receipt = group[sequence - 1]
            expected_name = f"attempt-{index:03d}-receipt-{sequence:02d}-{stage.lower()}.json"
            if files.get(expected_name) != receipt:
                raise ValueError("receipt filename differs from its stage and attempt")
            if (receipt["stage"], receipt["sequence"], receipt["reviewer_type"]) != (stage, sequence, reviewer_type):
                raise ValueError("receipt stage, sequence, or reviewer type is invalid")
            if receipt["engine_run_id"] != request["engine_run_id"] or receipt["candidate_attempt_id"] != attempt["candidate_attempt_id"] or receipt["candidate_sha256"] != attempt["candidate_sha256"] or receipt["input_sha256"] != sha256_json(attempt["candidate"]):
                raise ValueError("receipt cross-record binding is invalid")
            if receipt["validator"] != {
                "name": "english_master.qa_engine",
                "version": (
                    f"1.0;projection={PROJECTION_VERSION};near={NEAR_POLICY_VERSION}"
                    if stage == "DUPLICATE"
                    else "1.0"
                ),
            } or receipt["limitations"] != [
                "M8 development QA evidence is not human review or release approval."
            ]:
                raise ValueError("receipt validator metadata or limitations are invalid")
            ensure_not_after(receipt_time, receipt["checked_at"], "receipt chronology is invalid")
            receipt_time = receipt["checked_at"]
            if failed:
                expected_not_run_issues = [
                    QaIssue(
                        "EARLIER_STAGE_FAILED",
                        "$",
                        "not run because an earlier QA stage failed",
                        "INFO",
                    ).as_dict()
                ]
                if (
                    receipt["result"] != "NOT_RUN"
                    or receipt["review_reference"] is not None
                    or receipt["issues"] != expected_not_run_issues
                ):
                    raise ValueError("stage ran after an earlier failure")
                continue
            if receipt["result"] == "NOT_RUN":
                raise ValueError("stage is NOT_RUN without an earlier failure")
            blocking = any(item["severity"] in {"MAJOR", "CRITICAL"} for item in receipt["issues"])
            if receipt["result"] == "PASS" and blocking:
                raise ValueError("passing receipt contains a blocking finding")
            if receipt["result"] in {"FAIL", "ERROR"} and not receipt["issues"]:
                raise ValueError("failed receipt has no findings")
            if stage != "LANGUAGE" and receipt["result"] != "ERROR":
                expected_issues = list(
                    item.as_dict()
                    for item in _expected_machine_issues(
                        stage, attempt, authority, request, attempts[: index - 1]
                    )
                )
                if stage == "SCHEMA" and retry_invocation is not None:
                    expected_issues.extend(
                        item.as_dict()
                        for item in regeneration_evidence_issues(retry_invocation)
                    )
                if receipt["issues"] != expected_issues:
                    raise ValueError(f"{stage} receipt differs from deterministic revalidation")
                expected_result = "FAIL" if expected_issues else "PASS"
                if receipt["result"] != expected_result:
                    raise ValueError(f"{stage} receipt result is invalid")
            if receipt["result"] in {"FAIL", "ERROR"}:
                failed = True

        language = group[-1]
        if language["result"] in {"PASS", "FAIL"}:
            reference = language["review_reference"]
            if not isinstance(reference, Mapping):
                raise ValueError("executed LANGUAGE stage lacks a review reference")
            review = reviews.get(reference["review_id"])
            if review is None or reference["review_sha256"] != sha256_json(review):
                raise ValueError("LANGUAGE review reference is missing or invalid")
            used_reviews.add(review["ai_review_id"])
            if review["engine_run_id"] != request["engine_run_id"] or review["candidate_attempt_id"] != attempt["candidate_attempt_id"] or review["candidate_sha256"] != attempt["candidate_sha256"] or review["qa_request_sha256"] != sha256_json(request) or review["machine_receipt_sha256s"] != [sha256_json(item) for item in group[:5]]:
                raise ValueError("AI review bindings are invalid")
            if reference["evidence_kind"] != review["evidence_kind"]:
                raise ValueError("LANGUAGE evidence kind differs from its review")
            ensure_not_after(
                group[4]["checked_at"],
                review["reviewed_at"],
                "AI review predates machine QA",
            )
            if review["evidence_kind"] == "M8_CANDIDATE_BOUND":
                invocation = invocations.get(review["invocation_id"])
                if invocation is None or review["invocation_sha256"] != sha256_json(invocation):
                    raise ValueError("candidate-bound review invocation is missing or invalid")
                used_invocations.add(invocation["invocation_id"])
                _verify_invocation(
                    invocation,
                    request=request,
                    purpose="SEMANTIC_REVIEW",
                    attempt_number=index,
                    candidate_attempt_id=attempt["candidate_attempt_id"],
                    parent_rejection_sha256=(
                        sha256_json(rejections[index - 2]) if index > 1 else None
                    ),
                    repair_constraints_sha256=(
                        rejections[index - 2]["repair_constraints_sha256"]
                        if index > 1
                        else sha256_json([])
                    ),
                    parameters={"temperature": 0, "response_format": "json"},
                    seed=None,
                )
                expected_prompt = build_review_prompt(request, attempt, group[:5])
                if invocation["prompt"] != expected_prompt or invocation["prompt_sha256"] != sha256_text(expected_prompt) or invocation["response_sha256"] != sha256_json(invocation["response"]):
                    raise ValueError("AI review prompt or response is not reconstructable")
                ensure_not_after(group[4]["checked_at"], invocation["observed_at"], "AI review predates machine QA")
                expected_evidence = build_candidate_bound_review(
                    request=request,
                    attempt=attempt,
                    machine_receipts=group[:5],
                    invocation=invocation,
                    generation_invocation=retry_invocation,
                )
            else:
                expected_evidence = BoundM7LanguageReviewer(
                    authority, request["lesson_id"]
                ).review(
                    request,
                    attempt,
                    group[:5],
                    bound_at=review["reviewed_at"],
                )
            if expected_evidence.review != review or expected_evidence.review_sha256 != sha256_json(review):
                raise ValueError("AI review differs from independently reconstructed evidence")
            expected_language_result = "PASS" if expected_evidence.passed else "FAIL"
            if language["result"] != expected_language_result or language["issues"] != [item.as_dict() for item in expected_evidence.issues]:
                raise ValueError("LANGUAGE receipt differs from reconstructed AI review")
            ensure_not_after(review["reviewed_at"], language["checked_at"], "LANGUAGE receipt predates its review")

        if index <= len(rejections):
            rejection = rejections[index - 1]
            if rejection["attempt_number"] != index or rejection["engine_run_id"] != request["engine_run_id"] or rejection["candidate_attempt_id"] != attempt["candidate_attempt_id"] or rejection["candidate_sha256"] != attempt["candidate_sha256"]:
                raise ValueError("rejection binding is invalid")
            if rejection["receipt_sha256s"] != [sha256_json(item) for item in group]:
                raise ValueError("rejection receipt hashes are invalid")
            expected_constraints = []
            seen = set()
            for receipt in group:
                for issue in receipt["issues"]:
                    if issue["severity"] not in {"MAJOR", "CRITICAL"}:
                        continue
                    key = (receipt["stage"], issue["code"], issue["path"], issue["message"])
                    if key not in seen:
                        seen.add(key)
                        expected_constraints.append({"stage": key[0], "code": key[1], "path": key[2], "message": key[3]})
            if not expected_constraints:
                expected_constraints = [{"stage": "LANGUAGE", "code": "RESOLVE_FAILED_QA", "path": "$", "message": "Resolve all failed QA findings while preserving trusted scope."}]
            expected_reason = _expected_rejection_reason(
                group, index, request["maximum_attempts"]
            )
            if rejection["reason"] != expected_reason:
                raise ValueError("rejection reason is not derivable from receipt state")
            if rejection["repair_constraints"] != expected_constraints or rejection["repair_constraints_sha256"] != sha256_json(expected_constraints):
                raise ValueError("rejection repair constraints are not derivable")
            if not failed:
                raise ValueError("passing attempt must not have rejection evidence")
            ensure_not_after(group[-1]["checked_at"], rejection["rejected_at"], "rejection predates receipts")
            previous_terminal_time = rejection["rejected_at"]
        else:
            previous_terminal_time = group[-1]["checked_at"]

    for failure in operational:
        if failure["engine_run_id"] != request["engine_run_id"]:
            raise ValueError("operational failure run binding is invalid")
        if failure["attempt_number"] > request["maximum_attempts"]:
            raise ValueError("operational failure exceeds the request attempt limit")
        number = failure["attempt_number"]
        if number == 1:
            expected_parent_sha256 = None
        else:
            if len(rejections) < number - 1:
                raise ValueError("operational failure retry is missing its parent rejection")
            expected_parent_sha256 = sha256_json(rejections[number - 2])
        if failure["parent_rejection_sha256"] != expected_parent_sha256:
            raise ValueError("operational failure parent rejection is invalid")
        ensure_not_after(
            request["created_at"],
            failure["occurred_at"],
            "operational failure predates its request",
        )
        if number > 1:
            ensure_not_after(
                rejections[number - 2]["rejected_at"],
                failure["occurred_at"],
                "operational retry failure predates its parent rejection",
            )
        if failure["occurred_at_source"] not in {
            "OBSERVED_CLOCK",
            "LAST_KNOWN_SAFE_TIMESTAMP",
            "REQUEST_CREATED_AT",
        }:
            raise ValueError("operational failure timestamp source is invalid")
        if (
            failure["occurred_at_source"] == "REQUEST_CREATED_AT"
            and failure["occurred_at"] != request["created_at"]
        ):
            raise ValueError("request-timestamp fallback must retain the request time")
        has_attempt = failure["candidate_attempt_id"] is not None
        if failure["operation"] != "RECORD_CONSTRUCTION":
            expected_attempt_operation = failure["operation"] in {
                "QA_STAGE", "AI_REVIEW_CAPTURE", "AI_REVIEW"
            }
            if has_attempt != expected_attempt_operation:
                raise ValueError("operational failure operation and candidate binding are inconsistent")
        requires_invocation = failure["operation"] in {"CANDIDATE_ASSEMBLY", "AI_REVIEW"}
        if requires_invocation and failure["invocation_id"] is None:
            raise ValueError("operational failure operation requires an invocation")
        if (
            failure["operation"] not in {"CANDIDATE_ASSEMBLY", "AI_REVIEW", "RECORD_CONSTRUCTION"}
            and failure["invocation_id"] is not None
        ):
            raise ValueError("operational failure operation cannot bind an invocation")
        orderable_timestamp(failure["occurred_at"])
        matching = next(
            (
                item
                for item in attempts
                if item["candidate_attempt_id"] == failure["candidate_attempt_id"]
            ),
            None,
        )
        if failure["candidate_attempt_id"] is not None and (
            matching is None or matching["attempt_number"] != failure["attempt_number"]
        ):
            raise ValueError("operational failure references a missing or wrong attempt")
        if failure["invocation_id"] is not None:
            invocation = invocations.get(failure["invocation_id"])
            if invocation is None or failure["invocation_sha256"] != sha256_json(invocation):
                raise ValueError("operational failure invocation binding is invalid")
            if invocation["engine_run_id"] != request["engine_run_id"] or invocation["attempt_number"] != failure["attempt_number"]:
                raise ValueError("operational failure invocation scope is invalid")
            used_invocations.add(invocation["invocation_id"])
            ensure_not_after(invocation["observed_at"], failure["occurred_at"], "operational failure predates its invocation")
            if invocation["purpose"] == "REGENERATION":
                if failure["operation"] not in {"CANDIDATE_ASSEMBLY", "RECORD_CONSTRUCTION"} or number < 2:
                    raise ValueError("operational regeneration invocation has invalid topology")
                generation_request = build_request(
                    authority.m6,
                    build_authorization(authority.m6),
                    request["lesson_id"],
                ).as_dict()
                parent = rejections[number - 2]
                _verify_invocation(
                    invocation,
                    request=request,
                    purpose="REGENERATION",
                    attempt_number=number,
                    candidate_attempt_id=None,
                    parent_rejection_sha256=sha256_json(parent),
                    repair_constraints_sha256=parent["repair_constraints_sha256"],
                    parameters=generation_request["generation_config"]["parameters"],
                    seed=generation_request["generation_config"]["seed"],
                )
                expected_prompt = build_regeneration_prompt(
                    request, attempts[number - 2]["candidate"], parent, generation_request
                )
                if (
                    invocation["prompt"] != expected_prompt
                    or invocation["prompt_sha256"] != sha256_text(expected_prompt)
                    or invocation["response_sha256"] != sha256_json(invocation["response"])
                ):
                    raise ValueError("operational regeneration invocation is not reconstructable")
            elif invocation["purpose"] == "SEMANTIC_REVIEW":
                if failure["operation"] not in {"AI_REVIEW", "RECORD_CONSTRUCTION"} or matching is None:
                    raise ValueError("operational semantic-review invocation has invalid topology")
                group = sorted(
                    receipts_by_attempt[matching["candidate_attempt_id"]],
                    key=lambda item: item["sequence"],
                )
                _verify_invocation(
                    invocation,
                    request=request,
                    purpose="SEMANTIC_REVIEW",
                    attempt_number=number,
                    candidate_attempt_id=matching["candidate_attempt_id"],
                    parent_rejection_sha256=expected_parent_sha256,
                    repair_constraints_sha256=(
                        rejections[number - 2]["repair_constraints_sha256"]
                        if number > 1
                        else sha256_json([])
                    ),
                    parameters={"temperature": 0, "response_format": "json"},
                    seed=None,
                )
                expected_prompt = build_review_prompt(request, matching, group[:5])
                if (
                    invocation["prompt"] != expected_prompt
                    or invocation["prompt_sha256"] != sha256_text(expected_prompt)
                    or invocation["response_sha256"] != sha256_json(invocation["response"])
                ):
                    raise ValueError("operational semantic-review invocation is not reconstructable")
            else:
                raise ValueError("operational invocation purpose is invalid")
        elif failure["invocation_sha256"] is not None:
            raise ValueError("operational failure has an invocation hash without an invocation")
        if failure["ai_review_id"] is not None:
            if failure["operation"] != "RECORD_CONSTRUCTION" or matching is None:
                raise ValueError("operational AI review has invalid topology")
            review = reviews.get(failure["ai_review_id"])
            if review is None or failure["ai_review_sha256"] != sha256_json(review):
                raise ValueError("operational AI review binding is invalid")
            if failure["invocation_id"] is None or review["invocation_id"] != failure["invocation_id"]:
                raise ValueError("operational AI review does not bind its invocation")
            group = sorted(
                receipts_by_attempt[matching["candidate_attempt_id"]],
                key=lambda item: item["sequence"],
            )
            if len(group) != 6 or group[-1]["result"] != "ERROR":
                raise ValueError("operational post-review failure lacks an ERROR LANGUAGE receipt")
            if review["engine_run_id"] != request["engine_run_id"] or review["candidate_attempt_id"] != matching["candidate_attempt_id"] or review["candidate_sha256"] != matching["candidate_sha256"] or review["qa_request_sha256"] != sha256_json(request) or review["machine_receipt_sha256s"] != [sha256_json(item) for item in group[:5]]:
                raise ValueError("operational AI review bindings are invalid")
            invocation = invocations[failure["invocation_id"]]
            expected_evidence = build_candidate_bound_review(
                request=request,
                attempt=matching,
                machine_receipts=group[:5],
                invocation=invocation,
                generation_invocation=(
                    invocations.get(matching["generation_provenance"]["invocation_id"])
                    if number > 1
                    else None
                ),
            )
            if expected_evidence.review != review:
                raise ValueError("operational AI review is not reconstructable")
            used_reviews.add(review["ai_review_id"])
        elif failure["ai_review_sha256"] is not None:
            raise ValueError("operational failure has an AI review hash without a review")
        if failure["candidate_attempt_id"] is not None:
            assert matching is not None
            group = sorted(receipts_by_attempt[matching["candidate_attempt_id"]], key=lambda item: item["sequence"])
            if failure["related_receipt_sha256s"] != [sha256_json(item) for item in group]:
                raise ValueError("operational failure receipt hashes are invalid")
            ensure_not_after(group[-1]["checked_at"], failure["occurred_at"], "operational failure predates its receipts")
        elif failure["related_receipt_sha256s"]:
            raise ValueError("pre-attempt operational failure cannot reference receipts")

    if set(invocations) != used_invocations:
        raise ValueError("run contains orphan model invocations")
    if set(reviews) != used_reviews:
        raise ValueError("run contains orphan AI reviews")

    terminal_state = manifest["terminal_state"]
    if terminal_state == "DEVELOPMENT_APPROVED":
        if not isinstance(decision, Mapping) or operational:
            raise ValueError("approved manifest lacks a sole development decision")
        if len(rejections) != len(attempts) - 1 or not attempts:
            raise ValueError("approved retry lineage is incomplete")
        final = attempts[-1]
        group = sorted(receipts_by_attempt[final["candidate_attempt_id"]], key=lambda item: item["sequence"])
        if any(item["result"] != "PASS" for item in group):
            raise ValueError("approved decision requires six passing receipts")
        reference = group[-1]["review_reference"]
        review = reviews[reference["review_id"]]
        if decision["engine_run_id"] != request["engine_run_id"] or decision["m7_batch_id"] != request["m7_batch_id"] or decision["candidate_attempt_id"] != final["candidate_attempt_id"] or decision["candidate_sha256"] != final["candidate_sha256"] or decision["ai_review_id"] != review["ai_review_id"] or decision["ai_review_sha256"] != sha256_json(review) or decision["receipt_sha256s"] != [sha256_json(item) for item in group]:
            raise ValueError("decision bindings are invalid")
        expected_evidence_hash = sha256_json({
            "request": request,
            "attempts": attempts,
            "receipts": [sorted(receipts_by_attempt[item["candidate_attempt_id"]], key=lambda value: value["sequence"]) for item in attempts],
            "rejections": rejections,
            "invocations": sorted(invocations.values(), key=lambda item: (item["attempt_number"], item["purpose"])),
            "ai_reviews": [reviews[item["review_reference"]["review_id"]] for item in [sorted(receipts_by_attempt[attempt["candidate_attempt_id"]], key=lambda value: value["sequence"])[-1] for attempt in attempts] if isinstance(item["review_reference"], Mapping)],
            "operational_failures": [],
        })
        if decision["run_evidence_sha256"] != expected_evidence_hash:
            raise ValueError("decision does not bind complete run evidence")
        ensure_not_after(group[-1]["checked_at"], decision["decided_at"], "decision predates final receipt")
        if manifest["terminal_at"] != decision["decided_at"]:
            raise ValueError("manifest terminal time differs from decision")
    elif terminal_state == "REJECTED":
        if decision is not None or operational or not attempts or len(rejections) != len(attempts):
            raise ValueError("rejected manifest has inconsistent terminal evidence")
        if rejections[-1]["reason"] == "CONTENT_QA_FAILED":
            raise ValueError("repairable content rejection must continue to a retry")
        if manifest["terminal_at"] != rejections[-1]["rejected_at"]:
            raise ValueError("manifest terminal time differs from rejection")
    else:
        if decision is not None or len(operational) != 1:
            raise ValueError("operational manifest has inconsistent terminal evidence")
        if manifest["terminal_at"] != operational[0]["occurred_at"]:
            raise ValueError("manifest terminal time differs from operational failure")
        if len(rejections) not in {len(attempts), max(0, len(attempts) - 1)}:
            raise ValueError("operational run lineage is incomplete")

    return {
        "run_manifest_id": manifest["run_manifest_id"],
        "engine_run_id": request["engine_run_id"],
        "terminal_state": terminal_state,
        "content_lifecycle_status": "UNREVIEWED",
        "internally_consistent": True,
        "provider_authenticated": False,
    }
