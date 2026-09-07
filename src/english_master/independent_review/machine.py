"""Fresh deterministic M9 checks over immutable selected artifacts."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from english_master.ai_practice.generation import audit_artifact
from english_master.curriculum_review.loading import load_strict_document
from english_master.exercise_generation.review import _revalidate_exercise_set
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validation_issues

from .authority import ReviewSubject, VerifiedM9Authority

JsonObject = dict[str, Any]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _check(criterion: str, passed: bool, notes: str) -> JsonObject:
    return {"criterion": criterion, "result": "PASS" if passed else "FAIL", "notes": notes}


def build_machine_report(
    authority: VerifiedM9Authority,
    selection: Mapping[str, Any],
    subject: ReviewSubject,
    *,
    reviewed_at: str | None = None,
) -> JsonObject:
    """Reapply applicable static checks without trusting an old PASS alone."""
    checks: list[JsonObject] = []
    schema_name = {"LESSON": "lesson", "EXERCISE_SET": "exercise-set", "AI_PRACTICE_PROMPT": "ai-practice-prompt-artifact"}[subject.content_type]
    schema_errors = validation_issues(dict(subject.artifact), schema_name)
    checks.append(_check("SCHEMA", not schema_errors, "schema was independently validated"))
    checks.append(_check("IMMUTABLE_BINDING", sha256_json(subject.audit) == subject.audit_sha256, "stored source audit binding was rehashed"))
    if subject.content_type == "LESSON":
        audit_checks = subject.audit.get("checks", {})
        passed = subject.artifact.get("generation_metadata", {}).get("qa_status") == "UNREVIEWED" and subject.audit.get("status") == "ACCEPTED" and all(value == "PASS" for key, value in audit_checks.items() if key != "publication")
        checks.extend([
            _check("M6_MACHINE_AUDIT", passed, "M6 audit and lifecycle were independently inspected"),
            _check("CEFR_PREREQUISITE_SCOPE", subject.artifact.get("id") == subject.lesson_id, "lesson identity remains bound to graph-selected scope"),
            _check("PROVENANCE_STATUS", subject.artifact.get("generation_metadata", {}).get("qa_status") == "UNREVIEWED", "development evidence does not approve content"),
        ])
        scope = "STATIC_ARTIFACT"
        limitations = ["Static artifact checks only; no human, release, or Internet-wide originality claim is made."]
    elif subject.content_type == "EXERCISE_SET":
        issues = _revalidate_exercise_set(subject.artifact, authority.m7.m6)
        audit_checks = subject.audit.get("checks", {})
        checks.extend([
            _check("M7_SEMANTIC_REVALIDATION", not issues, "M7 final-set validators were rerun"),
            _check("ANSWER_CEFR_PREREQUISITE", all(value == "PASS" for value in audit_checks.values()), "stored audit is supplemental to fresh revalidation"),
            _check("PROVENANCE_STATUS", subject.artifact.get("status") == "UNREVIEWED", "exercise lifecycle remains unreviewed"),
        ])
        scope = "STATIC_ARTIFACT"
        limitations = ["Static exercise-set checks only; no human, release, or Internet-wide originality claim is made."]
    else:
        name = f"{subject.lesson_id.lower()}--{subject.modality.lower()}.json"
        request = load_strict_document(authority.pilot_directory / "requests" / name)
        authorization = load_strict_document(authority.pilot_directory / "authorization.json")
        audit = audit_artifact(subject.artifact, authority=authority.practice, request=request, authorization=authorization)
        passed = audit.get("result") == "PASS" and subject.artifact.get("content_lifecycle_status") == "UNREVIEWED"
        checks.extend([
            _check("M8_2_RECONSTRUCTION", passed, "prompt protocol and audit were reconstructed from verified M6 authority"),
            _check("MODALITY_CONTRACT", passed, f"{subject.modality} protocol remains statically conformant"),
            _check("PROVENANCE_STATUS", subject.artifact.get("provenance", {}).get("origin") == "PROJECT_AUTHORED", "prompt is project-authored and remains unreviewed"),
        ])
        scope = "STATIC_PROTOCOL"
        limitations = ["No live provider, audio, conversational turn handling, scoring behavior, or learner outcome was executed or observed."]
    result = "PASS" if all(item["result"] == "PASS" for item in checks) else "FAIL"
    report: JsonObject = {
        "schema_version": "1.0", "record_type": "m9_machine_qa_report", "report_id": "PENDING",
        "selection_id": selection["selection_id"], "subject_id": subject.subject_id, "content_type": subject.content_type,
        "artifact_sha256": subject.artifact_sha256, "machine_audit_sha256": subject.audit_sha256,
        "checks": checks, "result": result, "review_scope": scope, "limitations": limitations,
        "reviewed_at": reviewed_at or _now(), "human_reviewed": False, "release_approved": False, "provider_authenticated": False,
    }
    report["report_id"] = identity("m9machine", report, "report_id")
    return report
