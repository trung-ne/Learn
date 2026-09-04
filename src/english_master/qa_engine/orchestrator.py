"""Ordered, fail-closed M8 QA orchestration with immutable retry lineage."""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from english_master.exercise_generation.builders import build_authorization, build_request
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

from .authority import VerifiedM7QaAuthority
from .evidence import (
    build_candidate_bound_review,
    build_invocation,
    build_regeneration_prompt,
    build_review_prompt,
    assemble_regenerated_candidate,
)
from .models import (
    JsonObject,
    ModelBackend,
    QaEngineResult,
    QaIssue,
    ReviewEvidence,
    STAGE_CONTRACT,
)
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

_EXPECTED_ERRORS = (Exception,)


class _InvocationFailure(ValueError):
    def __init__(
        self,
        message: str,
        invocation: Mapping[str, Any],
        operation: str = "CANDIDATE_ASSEMBLY",
    ) -> None:
        super().__init__(message)
        self.invocation = copy.deepcopy(dict(invocation))
        self.operation = operation


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


class QaEngine:
    def __init__(
        self,
        authority: VerifiedM7QaAuthority,
        request: Mapping[str, Any],
        regeneration_backend: ModelBackend | None = None,
        review_backend: ModelBackend | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.authority = authority
        self.request = copy.deepcopy(dict(request))
        self.regeneration_backend = regeneration_backend
        self.review_backend = review_backend
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._last_timestamp: str | None = None

    def _timestamp(self) -> str:
        value = self._clock()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("clock must be timezone-aware")
        timestamp = value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if self._last_timestamp is not None:
            ensure_not_after(
                self._last_timestamp,
                timestamp,
                "clock moved backwards during M8 orchestration",
            )
        self._last_timestamp = timestamp
        return timestamp

    def _operational_timestamp(self) -> tuple[str, str]:
        """Return an honest orderable boundary when record construction is failing."""
        try:
            return self._timestamp(), "OBSERVED_CLOCK"
        except _EXPECTED_ERRORS:
            if self._last_timestamp is not None:
                return self._last_timestamp, "LAST_KNOWN_SAFE_TIMESTAMP"
            return self.request["created_at"], "REQUEST_CREATED_AT"

    def _attempt(
        self,
        candidate: Mapping[str, Any],
        *,
        number: int,
        parent_rejection_sha256: str | None,
        provenance: Mapping[str, Any],
    ) -> JsonObject:
        created_at = self._timestamp()
        ensure_not_after(
            provenance["observed_at"],
            created_at,
            "candidate observation must not follow attempt creation",
        )
        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "qa_engine_candidate_attempt",
            "candidate_attempt_id": "PENDING",
            "engine_run_id": self.request["engine_run_id"],
            "attempt_number": number,
            "status": "CANDIDATE",
            "candidate": copy.deepcopy(dict(candidate)),
            "candidate_sha256": sha256_json(candidate),
            "parent_rejection_sha256": parent_rejection_sha256,
            "generation_provenance": copy.deepcopy(dict(provenance)),
            "created_at": created_at,
        }
        value["candidate_attempt_id"] = identity(
            "qaeattempt", value, "candidate_attempt_id"
        )
        validate_instance(value, "qa-engine-candidate-attempt")
        return value

    def _initial_attempt(self) -> JsonObject:
        candidate, _, _ = self.authority.artifacts(self.request["lesson_id"])
        if sha256_json(candidate) != self.request["exercise_set_sha256"]:
            raise ValueError("verified M7 source candidate hash drifted")
        observed_at = candidate.get("generation_metadata", {}).get("generated_at")
        orderable_timestamp(observed_at)
        now = self._timestamp()
        ensure_not_after(
            observed_at,
            self.request["created_at"],
            "M7 source generation must not follow the M8 request",
        )
        ensure_not_after(
            self.request["created_at"], now, "M8 request cannot be future-dated"
        )
        return self._attempt(
            candidate,
            number=1,
            parent_rejection_sha256=None,
            provenance={
                "origin": "M7_AUTHORITY",
                "source_sha256": sha256_json(candidate),
                "invocation_id": None,
                "invocation_sha256": None,
                "capture_mode": "M7_AUTHORITY",
                "observed_at": observed_at,
                "qa_request_sha256": sha256_json(self.request),
                "repair_constraints_sha256": sha256_json([]),
                "provider_authenticated": False,
            },
        )

    def _regenerated_attempt(
        self,
        *,
        number: int,
        prior_attempt: Mapping[str, Any],
        parent_rejection: Mapping[str, Any],
    ) -> tuple[JsonObject, JsonObject]:
        if self.regeneration_backend is None:
            raise ValueError("no regeneration backend is configured")
        generation_request = build_request(
            self.authority.m6,
            build_authorization(self.authority.m6),
            self.request["lesson_id"],
        ).as_dict()
        constraints = parent_rejection["repair_constraints"]
        prompt = build_regeneration_prompt(
            self.request, prior_attempt["candidate"], parent_rejection, generation_request
        )
        config = generation_request["generation_config"]
        capture = self.regeneration_backend.generate(
            prompt,
            parameters=config["parameters"],
            seed=config["seed"],
        )
        observed_at = self._timestamp()
        ensure_not_after(
            parent_rejection["rejected_at"],
            observed_at,
            "regeneration must occur after its parent rejection",
        )
        invocation = build_invocation(
            request=self.request,
            purpose="REGENERATION",
            attempt_number=number,
            candidate_attempt_id=None,
            parent_rejection_sha256=sha256_json(parent_rejection),
            repair_constraints=constraints,
            prompt=prompt,
            capture=capture,
            parameters=config["parameters"],
            seed=config["seed"],
            observed_at=observed_at,
        )
        try:
            candidate = assemble_regenerated_candidate(
                self.authority,
                self.request["lesson_id"],
                invocation["response"],
                invocation,
            )
        except _EXPECTED_ERRORS as error:
            raise _InvocationFailure(str(error), invocation) from error
        try:
            attempt = self._attempt(
                candidate,
                number=number,
                parent_rejection_sha256=sha256_json(parent_rejection),
                provenance={
                    "origin": "M8_REGENERATION",
                    "source_sha256": invocation["response_sha256"],
                    "invocation_id": invocation["invocation_id"],
                    "invocation_sha256": sha256_json(invocation),
                    "capture_mode": invocation["capture_mode"],
                    "observed_at": invocation["observed_at"],
                    "qa_request_sha256": sha256_json(self.request),
                    "repair_constraints_sha256": parent_rejection[
                        "repair_constraints_sha256"
                    ],
                    "provider_authenticated": False,
                },
            )
        except _EXPECTED_ERRORS as error:
            raise _InvocationFailure(
                str(error), invocation, "RECORD_CONSTRUCTION"
            ) from error
        return attempt, invocation

    def _receipt(
        self,
        attempt: Mapping[str, Any],
        stage: str,
        sequence: int,
        result: str,
        issues: Sequence[QaIssue],
        *,
        review_reference: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        expected = STAGE_CONTRACT[sequence - 1]
        if expected[:2] != (stage, sequence):
            raise ValueError("stage and sequence differ from the fixed M8 contract")
        validator_version = (
            f"1.0;projection={PROJECTION_VERSION};near={NEAR_POLICY_VERSION}"
            if stage == "DUPLICATE"
            else "1.0"
        )
        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "qa_engine_stage_receipt",
            "receipt_id": "PENDING",
            "engine_run_id": self.request["engine_run_id"],
            "candidate_attempt_id": attempt["candidate_attempt_id"],
            "candidate_sha256": attempt["candidate_sha256"],
            "stage": stage,
            "sequence": sequence,
            "result": result,
            "validator": {
                "name": "english_master.qa_engine",
                "version": validator_version,
            },
            "reviewer_type": expected[2],
            "input_sha256": sha256_json(attempt["candidate"]),
            "checked_at": self._timestamp(),
            "issues": [item.as_dict() for item in issues],
            "review_reference": (
                copy.deepcopy(dict(review_reference))
                if review_reference is not None
                else None
            ),
            "limitations": [
                "M8 development QA evidence is not human review or release approval."
            ],
        }
        value["receipt_id"] = identity("qaereceipt", value, "receipt_id")
        validate_instance(value, "qa-engine-stage-receipt")
        return value

    def _not_run(
        self, attempt: Mapping[str, Any], stage: str, sequence: int
    ) -> JsonObject:
        return self._receipt(
            attempt,
            stage,
            sequence,
            "NOT_RUN",
            (
                QaIssue(
                    "EARLIER_STAGE_FAILED",
                    "$",
                    "not run because an earlier QA stage failed",
                    "INFO",
                ),
            ),
        )

    @staticmethod
    def _repair_constraints(
        receipts: Sequence[Mapping[str, Any]],
    ) -> list[JsonObject]:
        constraints: list[JsonObject] = []
        seen: set[tuple[str, str, str, str]] = set()
        for receipt in receipts:
            for issue in receipt["issues"]:
                if issue["severity"] not in {"MAJOR", "CRITICAL"}:
                    continue
                key = (
                    receipt["stage"],
                    issue["code"],
                    issue["path"],
                    issue["message"],
                )
                if key in seen:
                    continue
                seen.add(key)
                constraints.append(
                    {
                        "stage": key[0],
                        "code": key[1],
                        "path": key[2],
                        "message": key[3],
                    }
                )
        if not constraints:
            constraints.append(
                {
                    "stage": "LANGUAGE",
                    "code": "RESOLVE_FAILED_QA",
                    "path": "$",
                    "message": "Resolve all failed QA findings while preserving trusted scope.",
                }
            )
        return constraints

    def _rejection(
        self,
        attempt: Mapping[str, Any],
        receipts: Sequence[Mapping[str, Any]],
        reason: str,
    ) -> JsonObject:
        constraints = self._repair_constraints(receipts)
        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "qa_engine_rejection",
            "rejection_id": "PENDING",
            "engine_run_id": self.request["engine_run_id"],
            "candidate_attempt_id": attempt["candidate_attempt_id"],
            "candidate_sha256": attempt["candidate_sha256"],
            "attempt_number": attempt["attempt_number"],
            "reason": reason,
            "receipt_sha256s": [sha256_json(item) for item in receipts],
            "repair_constraints": constraints,
            "repair_constraints_sha256": sha256_json(constraints),
            "rejected_at": self._timestamp(),
        }
        ensure_not_after(
            receipts[-1]["checked_at"],
            value["rejected_at"],
            "rejection must not precede its final receipt",
        )
        value["rejection_id"] = identity("qaereject", value, "rejection_id")
        validate_instance(value, "qa-engine-rejection")
        return value

    def _operational_failure(
        self,
        *,
        number: int,
        operation: str,
        error: Exception,
        candidate_attempt_id: str | None,
        parent_rejection_sha256: str | None,
        receipts: Sequence[Mapping[str, Any]] = (),
        invocation: Mapping[str, Any] | None = None,
        ai_review: Mapping[str, Any] | None = None,
    ) -> JsonObject:
        message = str(error).strip()[:4000] or "Exception raised without a message."
        occurred_at, occurred_at_source = self._operational_timestamp()
        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "qa_engine_operational_failure",
            "operational_failure_id": "PENDING",
            "engine_run_id": self.request["engine_run_id"],
            "attempt_number": number,
            "candidate_attempt_id": candidate_attempt_id,
            "parent_rejection_sha256": parent_rejection_sha256,
            "invocation_id": invocation["invocation_id"] if invocation is not None else None,
            "invocation_sha256": sha256_json(invocation) if invocation is not None else None,
            "ai_review_id": ai_review["ai_review_id"] if ai_review is not None else None,
            "ai_review_sha256": sha256_json(ai_review) if ai_review is not None else None,
            "operation": operation,
            "error_type": type(error).__name__,
            "message": message,
            "related_receipt_sha256s": [sha256_json(item) for item in receipts],
            "occurred_at": occurred_at,
            "occurred_at_source": occurred_at_source,
        }
        value["operational_failure_id"] = identity(
            "qaeopfail", value, "operational_failure_id"
        )
        validate_instance(value, "qa-engine-operational-failure")
        return value

    def _candidate_review(
        self,
        attempt: Mapping[str, Any],
        machine_receipts: Sequence[Mapping[str, Any]],
        parent_rejection: Mapping[str, Any] | None,
        generation_invocation: Mapping[str, Any] | None,
    ) -> ReviewEvidence:
        if (
            parent_rejection is not None
            and self.review_backend is self.regeneration_backend
        ):
            raise ValueError(
                "a regenerated candidate requires a distinct semantic-review backend"
            )
        if self.review_backend is None:
            bound_at = self._timestamp()
            ensure_not_after(
                machine_receipts[-1]["checked_at"],
                bound_at,
                "legacy M7 review binding must follow the five machine receipts",
            )
            return BoundM7LanguageReviewer(
                self.authority, self.request["lesson_id"]
            ).review(
                self.request,
                attempt,
                machine_receipts,
                bound_at=bound_at,
            )
        prompt = build_review_prompt(self.request, attempt, machine_receipts)
        parameters = {"temperature": 0, "response_format": "json"}
        capture = self.review_backend.generate(prompt, parameters=parameters, seed=None)
        observed_at = self._timestamp()
        ensure_not_after(
            machine_receipts[-1]["checked_at"],
            observed_at,
            "AI review invocation must follow the five machine receipts",
        )
        invocation = build_invocation(
            request=self.request,
            purpose="SEMANTIC_REVIEW",
            attempt_number=attempt["attempt_number"],
            candidate_attempt_id=attempt["candidate_attempt_id"],
            parent_rejection_sha256=(
                sha256_json(parent_rejection) if parent_rejection is not None else None
            ),
            repair_constraints=(
                parent_rejection["repair_constraints"]
                if parent_rejection is not None
                else []
            ),
            prompt=prompt,
            capture=capture,
            parameters=parameters,
            seed=None,
            observed_at=observed_at,
        )
        try:
            return build_candidate_bound_review(
                request=self.request,
                attempt=attempt,
                machine_receipts=machine_receipts,
                invocation=invocation,
                generation_invocation=generation_invocation,
            )
        except _EXPECTED_ERRORS as error:
            raise _InvocationFailure(str(error), invocation) from error

    def _decision(
        self,
        attempt: Mapping[str, Any],
        receipts: Sequence[Mapping[str, Any]],
        review: Mapping[str, Any],
        attempts: Sequence[Mapping[str, Any]],
        receipt_groups: Sequence[Sequence[Mapping[str, Any]]],
        rejections: Sequence[Mapping[str, Any]],
        invocations: Sequence[Mapping[str, Any]],
        ai_reviews: Sequence[Mapping[str, Any]],
    ) -> JsonObject:
        value: JsonObject = {
            "schema_version": "1.0",
            "record_type": "qa_engine_decision",
            "decision_id": "PENDING",
            "engine_run_id": self.request["engine_run_id"],
            "m7_batch_id": self.request["m7_batch_id"],
            "candidate_attempt_id": attempt["candidate_attempt_id"],
            "candidate_sha256": attempt["candidate_sha256"],
            "ai_review_id": review["ai_review_id"],
            "ai_review_sha256": sha256_json(review),
            "terminal_result": "DEVELOPMENT_APPROVED",
            "content_lifecycle_status": "UNREVIEWED",
            "receipt_sha256s": [sha256_json(item) for item in receipts],
            "run_evidence_sha256": sha256_json(
                {
                    "request": self.request,
                    "attempts": list(attempts),
                    "receipts": [list(group) for group in receipt_groups],
                    "rejections": list(rejections),
                    "invocations": list(invocations),
                    "ai_reviews": list(ai_reviews),
                    "operational_failures": [],
                }
            ),
            "decided_at": self._timestamp(),
            "human_reviewed": False,
            "release_approved": False,
            "limitations": [
                "AI and machine evidence establishes development approval only; content remains UNREVIEWED.",
                "No human review, release approval, provider authentication, or Internet-wide search is claimed.",
            ],
        }
        ensure_not_after(
            receipts[-1]["checked_at"],
            value["decided_at"],
            "decision must not precede its final receipt",
        )
        value["decision_id"] = identity("qaedecision", value, "decision_id")
        validate_instance(value, "qa-engine-decision")
        return value

    def _result(
        self,
        *,
        approved: bool,
        decision: JsonObject | None,
        attempts: Sequence[JsonObject],
        receipts: Sequence[tuple[JsonObject, ...]],
        rejections: Sequence[JsonObject],
        invocations: Sequence[JsonObject],
        ai_reviews: Sequence[JsonObject],
        operational_failures: Sequence[JsonObject],
    ) -> QaEngineResult:
        return QaEngineResult(
            approved,
            copy.deepcopy(decision),
            tuple(copy.deepcopy(item) for item in rejections),
            tuple(copy.deepcopy(item) for item in attempts),
            tuple(tuple(copy.deepcopy(item) for item in group) for group in receipts),
            tuple(copy.deepcopy(item) for item in invocations),
            tuple(copy.deepcopy(item) for item in ai_reviews),
            tuple(copy.deepcopy(item) for item in operational_failures),
        )

    def run(self) -> QaEngineResult:
        validate_instance(self.request, "qa-engine-request")
        expected_request = self.authority.request(
            self.request["lesson_id"],
            created_at=self.request["created_at"],
            maximum_attempts=self.request["maximum_attempts"],
        )
        if self.request != expected_request:
            raise ValueError("QA request differs from verified M7 authority")
        orderable_timestamp(self.request["created_at"])
        ensure_not_after(
            self.authority.authority_available_at(),
            self.request["created_at"],
            "M8 request must not predate the verified M7 development batch",
        )

        attempts: list[JsonObject] = []
        receipt_groups: list[tuple[JsonObject, ...]] = []
        rejections: list[JsonObject] = []
        invocations: list[JsonObject] = []
        ai_reviews: list[JsonObject] = []
        operational_failures: list[JsonObject] = []

        def record_construction_failure(
            number: int,
            parent: Mapping[str, Any] | None,
            error: Exception,
            invocation: Mapping[str, Any] | None = None,
        ) -> QaEngineResult:
            operational_failures.append(
                self._operational_failure(
                    number=number,
                    operation="RECORD_CONSTRUCTION",
                    error=error,
                    candidate_attempt_id=None,
                    parent_rejection_sha256=(
                        sha256_json(parent) if parent is not None else None
                    ),
                    invocation=invocation,
                )
            )
            return self._result(
                approved=False,
                decision=None,
                attempts=attempts,
                receipts=receipt_groups,
                rejections=rejections,
                invocations=invocations,
                ai_reviews=ai_reviews,
                operational_failures=operational_failures,
            )

        for number in range(1, self.request["maximum_attempts"] + 1):
            parent = rejections[-1] if rejections else None
            try:
                if number == 1:
                    attempt = self._initial_attempt()
                else:
                    attempt, invocation = self._regenerated_attempt(
                        number=number,
                        prior_attempt=attempts[-1],
                        parent_rejection=parent,
                    )
                    invocations.append(invocation)
            except _EXPECTED_ERRORS as error:
                failed_invocation = (
                    error.invocation if isinstance(error, _InvocationFailure) else None
                )
                if failed_invocation is not None:
                    invocations.append(copy.deepcopy(dict(failed_invocation)))
                operational_failures.append(
                    self._operational_failure(
                        number=number,
                        operation=(
                            "INITIAL_MATERIALIZATION"
                            if number == 1
                            else (
                                error.operation
                                if isinstance(error, _InvocationFailure)
                                else "CANDIDATE_GENERATION"
                            )
                        ),
                        error=error,
                        candidate_attempt_id=None,
                        parent_rejection_sha256=(
                            sha256_json(parent) if parent is not None else None
                        ),
                        invocation=failed_invocation,
                    )
                )
                return self._result(
                    approved=False,
                    decision=None,
                    attempts=attempts,
                    receipts=receipt_groups,
                    rejections=rejections,
                    invocations=invocations,
                    ai_reviews=ai_reviews,
                    operational_failures=operational_failures,
                )

            candidate = attempt["candidate"]
            stage_functions = (
                lambda: schema_issues(candidate, self.authority, self.request["lesson_id"]),
                lambda: answer_issues(candidate, self.authority, self.request["lesson_id"]),
                lambda: cefr_issues(candidate, self.authority, self.request["lesson_id"]),
                lambda: prerequisite_issues(candidate, self.authority, self.request["lesson_id"]),
                lambda: duplicate_issues(
                    candidate,
                    self.authority,
                    self.request["lesson_id"],
                    [item["candidate"] for item in attempts],
                ),
            )
            receipts: list[JsonObject] = []
            failed = False
            stage_error: Exception | None = None
            for stage, sequence, _ in STAGE_CONTRACT[:5]:
                if failed:
                    try:
                        receipts.append(self._not_run(attempt, stage, sequence))
                    except _EXPECTED_ERRORS as error:
                        return record_construction_failure(
                            number,
                            parent,
                            error,
                            invocation if number > 1 else None,
                        )
                    continue
                try:
                    issues = tuple(stage_functions[sequence - 1]())
                    if stage == "SCHEMA" and number > 1:
                        issues += regeneration_evidence_issues(invocation)
                    result = "FAIL" if issues else "PASS"
                except _EXPECTED_ERRORS as error:
                    stage_error = error
                    issues = (
                        QaIssue(
                            "QA_STAGE_ERROR",
                            "$",
                            f"{stage} QA could not complete: {error}",
                            "CRITICAL",
                        ),
                    )
                    result = "ERROR"
                try:
                    receipts.append(
                        self._receipt(attempt, stage, sequence, result, issues)
                    )
                except _EXPECTED_ERRORS as error:
                    return record_construction_failure(
                        number,
                        parent,
                        error,
                        invocation if number > 1 else None,
                    )
                failed = result != "PASS"

            if failed:
                try:
                    receipts.append(self._not_run(attempt, "LANGUAGE", 6))
                except _EXPECTED_ERRORS as error:
                    return record_construction_failure(
                        number,
                        parent,
                        error,
                        invocation if number > 1 else None,
                    )
                attempts.append(attempt)
                receipt_tuple = tuple(receipts)
                receipt_groups.append(receipt_tuple)
                if stage_error is not None:
                    operational_failures.append(
                        self._operational_failure(
                            number=number,
                            operation="QA_STAGE",
                            error=stage_error,
                            candidate_attempt_id=attempt["candidate_attempt_id"],
                            parent_rejection_sha256=(
                                sha256_json(parent) if parent is not None else None
                            ),
                            receipts=receipt_tuple,
                        )
                    )
                    return self._result(
                        approved=False,
                        decision=None,
                        attempts=attempts,
                        receipts=receipt_groups,
                        rejections=rejections,
                        invocations=invocations,
                        ai_reviews=ai_reviews,
                        operational_failures=operational_failures,
                    )
            else:
                review_invocation: Mapping[str, Any] | None = None
                review: JsonObject | None = None
                try:
                    evidence = self._candidate_review(
                        attempt,
                        tuple(receipts),
                        parent,
                        invocation if number > 1 else None,
                    )
                    if evidence.invocation is not None:
                        review_invocation = copy.deepcopy(dict(evidence.invocation))
                        invocations.append(review_invocation)
                    if evidence.review is None:
                        raise ValueError("AI review response could not form candidate-bound evidence")
                    review = copy.deepcopy(dict(evidence.review))
                    ai_reviews.append(review)
                    result = "PASS" if evidence.passed else "FAIL"
                    receipts.append(
                        self._receipt(
                            attempt,
                            "LANGUAGE",
                            6,
                            result,
                            evidence.issues,
                            review_reference=evidence.reference(),
                        )
                    )
                    failed = result != "PASS"
                except _EXPECTED_ERRORS as error:
                    if isinstance(error, _InvocationFailure):
                        review_invocation = error.invocation
                        invocations.append(copy.deepcopy(dict(review_invocation)))
                    try:
                        receipts.append(
                            self._receipt(
                                attempt,
                                "LANGUAGE",
                                6,
                                "ERROR",
                                (
                                    QaIssue(
                                        "AI_REVIEW_ERROR",
                                        "$",
                                        f"AI review could not complete: {error}",
                                        "CRITICAL",
                                    ),
                                ),
                            )
                        )
                    except _EXPECTED_ERRORS as record_error:
                        return record_construction_failure(
                            number, parent, record_error, review_invocation
                        )
                    attempts.append(attempt)
                    receipt_tuple = tuple(receipts)
                    receipt_groups.append(receipt_tuple)
                    operational_failures.append(
                        self._operational_failure(
                            number=number,
                            operation=(
                                "RECORD_CONSTRUCTION"
                                if review is not None
                                else "AI_REVIEW"
                                if review_invocation is not None
                                else "AI_REVIEW_CAPTURE"
                            ),
                            error=error,
                            candidate_attempt_id=attempt["candidate_attempt_id"],
                            parent_rejection_sha256=(
                                sha256_json(parent) if parent is not None else None
                            ),
                            receipts=receipt_tuple,
                            invocation=review_invocation,
                            ai_review=review,
                        )
                    )
                    return self._result(
                        approved=False,
                        decision=None,
                        attempts=attempts,
                        receipts=receipt_groups,
                        rejections=rejections,
                        invocations=invocations,
                        ai_reviews=ai_reviews,
                        operational_failures=operational_failures,
                    )
                attempts.append(attempt)
                receipt_tuple = tuple(receipts)
                receipt_groups.append(receipt_tuple)

            if not failed:
                try:
                    decision = self._decision(
                        attempt,
                        receipt_tuple,
                        ai_reviews[-1],
                        attempts,
                        receipt_groups,
                        rejections,
                        invocations,
                        ai_reviews,
                    )
                except _EXPECTED_ERRORS as error:
                    operational_failures.append(
                        self._operational_failure(
                            number=number,
                            operation="RECORD_CONSTRUCTION",
                            error=error,
                            candidate_attempt_id=attempt["candidate_attempt_id"],
                            parent_rejection_sha256=(
                                sha256_json(parent) if parent is not None else None
                            ),
                            receipts=receipt_tuple,
                        )
                    )
                    return self._result(
                        approved=False,
                        decision=None,
                        attempts=attempts,
                        receipts=receipt_groups,
                        rejections=rejections,
                        invocations=invocations,
                        ai_reviews=ai_reviews,
                        operational_failures=operational_failures,
                    )
                return self._result(
                    approved=True,
                    decision=decision,
                    attempts=attempts,
                    receipts=receipt_groups,
                    rejections=rejections,
                    invocations=invocations,
                    ai_reviews=ai_reviews,
                    operational_failures=operational_failures,
                )

            non_repairable = any(
                issue["code"] in _NON_REPAIRABLE_CODES
                for receipt in receipt_tuple
                for issue in receipt["issues"]
            )
            reason = (
                "NON_REPAIRABLE_AUTHORITY_FAILURE"
                if non_repairable
                else "RETRY_LIMIT_EXHAUSTED"
                if number == self.request["maximum_attempts"]
                else "CONTENT_QA_FAILED"
            )
            try:
                rejection = self._rejection(attempt, receipt_tuple, reason)
            except _EXPECTED_ERRORS as error:
                operational_failures.append(
                    self._operational_failure(
                        number=number,
                        operation="RECORD_CONSTRUCTION",
                        error=error,
                        candidate_attempt_id=attempt["candidate_attempt_id"],
                        parent_rejection_sha256=(
                            sha256_json(parent) if parent is not None else None
                        ),
                        receipts=receipt_tuple,
                    )
                )
                return self._result(
                    approved=False,
                    decision=None,
                    attempts=attempts,
                    receipts=receipt_groups,
                    rejections=rejections,
                    invocations=invocations,
                    ai_reviews=ai_reviews,
                    operational_failures=operational_failures,
                )
            rejections.append(rejection)
            if non_repairable or number == self.request["maximum_attempts"]:
                return self._result(
                    approved=False,
                    decision=None,
                    attempts=attempts,
                    receipts=receipt_groups,
                    rejections=rejections,
                    invocations=invocations,
                    ai_reviews=ai_reviews,
                    operational_failures=operational_failures,
                )

        raise AssertionError("bounded QA loop terminated without a terminal result")
