"""Authority-bound legacy review adapter for the exact M7 candidate."""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

from .authority import VerifiedM7QaAuthority
from .models import QaIssue, REVIEW_CRITERIA, ReviewEvidence
from .time import ensure_not_after, orderable_timestamp


class BoundM7LanguageReviewer:
    """Bind both verified M7 AI roles to the unchanged authority candidate.

    This preserves legacy development evidence without pretending its provider facts
    were authenticated or that it reviewed a regenerated M8 candidate.
    """

    def __init__(self, authority: VerifiedM7QaAuthority, lesson_id: str) -> None:
        self.authority = authority
        self.lesson_id = lesson_id

    def review(
        self,
        request: Mapping[str, Any],
        attempt: Mapping[str, Any],
        machine_receipts: Sequence[Mapping[str, Any]],
        *,
        bound_at: str,
    ) -> ReviewEvidence:
        exercise_set, _, reviews = self.authority.artifacts(self.lesson_id)
        if sha256_json(attempt["candidate"]) != sha256_json(exercise_set):
            return ReviewEvidence(
                False,
                (
                    QaIssue(
                        "AI_REVIEW_REQUIRED",
                        "$.candidate",
                        "a regenerated candidate requires a fresh candidate-bound M8 AI review",
                    ),
                ),
                "UNBOUND",
                "qaeaireview_" + "0" * 64,
                "0" * 64,
            )
        by_role = {
            item.get("review_role"): item
            for item in reviews
            if isinstance(item, Mapping)
        }
        linguistic = by_role.get("LINGUISTIC_AI_REVIEWER")
        pedagogical = by_role.get("PEDAGOGICAL_AI_REVIEWER")
        if not isinstance(linguistic, Mapping) or not isinstance(pedagogical, Mapping):
            return ReviewEvidence(
                False,
                (QaIssue("M7_AI_REVIEWS_MISSING", "$", "both verified M7 AI review roles are required"),),
                "UNBOUND",
                "qaeaireview_" + "0" * 64,
                "0" * 64,
            )

        def checks(review: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
            return {
                str(item.get("criterion")): item
                for item in review.get("checklist", [])
                if isinstance(item, Mapping)
            }

        linguistic_checks = checks(linguistic)
        pedagogical_checks = checks(pedagogical)
        required = (
            ("ANSWER_ACCURACY_AND_AMBIGUITY", linguistic_checks, ("ANSWER_ACCURACY", "DISTRACTOR_QUALITY")),
            ("CEFR_SEMANTIC_ALIGNMENT", linguistic_checks, ("CEFR_ALIGNMENT",)),
            ("PREREQUISITE_OBJECTIVE_ALIGNMENT", pedagogical_checks, ("OBJECTIVE_ALIGNMENT", "TEACHABILITY")),
            ("LANGUAGE_QUALITY", linguistic_checks, ("GRAMMAR_LEXICAL_ACCURACY", "LANGUAGE_QUALITY")),
        )
        criteria: list[dict[str, Any]] = []
        issues: list[QaIssue] = []
        for output_name, source, names in required:
            passed = all(source.get(name, {}).get("result") == "PASS" for name in names)
            notes = [str(source.get(name, {}).get("notes", "missing M7 criterion")) for name in names]
            criteria.append(
                {
                    "criterion": output_name,
                    "result": "PASS" if passed else "FAIL",
                    "rationale": " ".join(notes),
                }
            )
            if not passed:
                issues.append(
                    QaIssue(
                        "M7_AI_REVIEW_CRITERION_FAILED",
                        f"$.criteria[{len(criteria) - 1}]",
                        " ".join(notes),
                    )
                )
        findings: list[dict[str, Any]] = []
        for source_review in (linguistic, pedagogical):
            for finding in source_review.get("findings", []):
                if not isinstance(finding, Mapping):
                    continue
                issue = QaIssue(
                    "M7_AI_REVIEW_FINDING",
                    "$.candidate",
                    str(finding.get("description", "M7 AI review finding")),
                    str(finding.get("severity", "MAJOR")),
                )
                issues.append(issue)
                findings.append(issue.as_dict())
        approved = (
            linguistic.get("decision") == "APPROVE"
            and pedagogical.get("decision") == "APPROVE"
            and all(item["result"] == "PASS" for item in criteria)
            and not any(item.severity in {"MAJOR", "CRITICAL"} for item in issues)
        )
        source_reviewed_ats = sorted(
            (str(linguistic["reviewed_at"]), str(pedagogical["reviewed_at"])),
            key=orderable_timestamp,
        )
        orderable_timestamp(bound_at)
        ensure_not_after(
            source_reviewed_ats[-1],
            bound_at,
            "M7 source reviews must not postdate their M8 binding record",
        )
        source_hashes = sorted((sha256_json(linguistic), sha256_json(pedagogical)))
        value: dict[str, Any] = {
            "schema_version": "1.0",
            "record_type": "qa_engine_ai_review",
            "ai_review_id": "PENDING",
            "engine_run_id": request["engine_run_id"],
            "candidate_attempt_id": attempt["candidate_attempt_id"],
            "candidate_sha256": attempt["candidate_sha256"],
            "qa_request_sha256": sha256_json(request),
            "m7_batch_id": request["m7_batch_id"],
            "machine_receipt_sha256s": [sha256_json(item) for item in machine_receipts],
            "evidence_kind": "M7_BOUND_LEGACY",
            "invocation_id": None,
            "invocation_sha256": None,
            "source_review_sha256s": source_hashes,
            "source_reviewed_ats": source_reviewed_ats,
            "reviewer_type": "AI",
            "review_role": "COMPREHENSIVE_AI_REVIEWER",
            "independent_of_generation": True,
            "criteria": criteria,
            "findings": findings,
            "decision": "APPROVE" if approved else "REQUEST_REVISION",
            "reviewed_at": bound_at,
            "approval_tier": "AI_REVIEWED",
            "content_lifecycle_status": "UNREVIEWED",
            "human_reviewed": False,
            "release_approved": False,
            "limitations": [
                "This binds two verified M7 AI development reviews; it is not a fresh M8 provider invocation.",
                "The source review hashes do not cryptographically authenticate their provider or model.",
                "This is not human review, CEFR certification, content approval, or release approval.",
                "No Internet-wide copyright or plagiarism search is implied.",
            ],
        }
        value["ai_review_id"] = identity("qaeaireview", value, "ai_review_id")
        validate_instance(value, "qa-engine-ai-review")
        return ReviewEvidence(
            approved,
            tuple(issues),
            "M7_BOUND_LEGACY",
            value["ai_review_id"],
            sha256_json(value),
            copy.deepcopy(value),
        )
