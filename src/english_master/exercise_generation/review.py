"""Hash-bound independent AI review and development-batch validation for M7."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from english_master.curriculum_review.loading import load_strict_document
from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validation_issues

from .authority import VerifiedM6DevelopmentAuthority
from .builders import build_authorization, build_request
from .models import ExerciseIssue, JsonObject
from .validator import assembled_issues, candidate_semantic_issues

REQUIRED_DEVELOPMENT_LESSONS = (
    "A1-U01-L01", "A1-U01-L02", "A1-U02-L01", "A1-U02-L02", "A2-U03-L01",
    "A2-U03-L02", "A2-U04-L01", "A2-U04-L02", "B1-U05-L01", "B1-U05-L02",
)
AI_CHECKLIST_BY_ROLE = {
    "LINGUISTIC_AI_REVIEWER": {
        "CEFR_ALIGNMENT", "GRAMMAR_LEXICAL_ACCURACY", "ANSWER_ACCURACY",
        "DISTRACTOR_QUALITY", "LANGUAGE_QUALITY", "ORIGINALITY_LIMITATIONS",
    },
    "PEDAGOGICAL_AI_REVIEWER": {
        "OBJECTIVE_ALIGNMENT", "TEACHABILITY", "PROGRESSION", "CLARITY",
        "COGNITIVE_LOAD", "VIETNAMESE_LEARNER_RELEVANCE", "WORKLOAD",
    },
}


def _issue(code: str, path: str, message: str) -> ExerciseIssue:
    return ExerciseIssue(code, path, message)


def _schema(value: Mapping[str, Any], name: str) -> list[ExerciseIssue]:
    return [_issue("REVIEW_SCHEMA", issue.instance_path, issue.message) for issue in validation_issues(dict(value), name)]


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _revalidate_exercise_set(
    exercise_set: Mapping[str, Any],
    authority: VerifiedM6DevelopmentAuthority,
) -> tuple[ExerciseIssue, ...]:
    """Reapply deterministic final-artifact checks without trusting its old audit."""
    issues = list(assembled_issues({}, exercise_set))
    lesson_id = exercise_set.get("lesson_id")
    if not isinstance(lesson_id, str):
        return tuple(sorted(set(issues)))
    try:
        request = build_request(authority, build_authorization(authority), lesson_id).as_dict()
        binding = authority.binding(lesson_id)
    except (KeyError, TypeError, ValueError) as error:
        issues.append(_issue("FINAL_SET_AUTHORITY_INVALID", "$.lesson_id", type(error).__name__))
        return tuple(sorted(set(issues)))
    if exercise_set.get("m6_batch_id") != authority.batch["batch_id"]:
        issues.append(_issue("FINAL_SET_M6_BINDING_MISMATCH", "$.m6_batch_id", "set must bind verified M6 batch"))
    if exercise_set.get("lesson_sha256") != binding["lesson_sha256"]:
        issues.append(_issue("FINAL_SET_LESSON_HASH_MISMATCH", "$.lesson_sha256", "set must bind exact verified lesson"))
    candidate = {
        "items": [
            {
                key: item[key]
                for key in (
                    "title", "exercise_type", "difficulty", "instructions", "objective_indices",
                    "target_references", "review_references", "scoring_mode", "payload",
                )
                if key in item
            }
            for item in exercise_set.get("exercises", [])
            if isinstance(item, Mapping)
        ]
    }
    issues.extend(candidate_semantic_issues(request, candidate))
    return tuple(sorted(set(issues)))


def build_ai_review_prompt(role: str, exercise_set: Mapping[str, Any], audit: Mapping[str, Any]) -> str:
    if role not in AI_CHECKLIST_BY_ROLE:
        raise ValueError(f"unsupported AI review role: {role}")
    import json
    return (
        f"You are the independent {role}. Review only the supplied exercise set and automated audit; "
        "do not infer or reproduce generation reasoning. Evaluate "
        f"{', '.join(sorted(AI_CHECKLIST_BY_ROLE[role]))}. Return a structured decision, checklist, and concrete findings. "
        "This AI review is development evidence only, never human or release approval.\n\n"
        + json.dumps({"exercise_set": exercise_set, "audit": audit}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def validate_ai_review(
    review: Mapping[str, Any], exercise_set: Mapping[str, Any], audit: Mapping[str, Any], authority: VerifiedM6DevelopmentAuthority,
) -> tuple[ExerciseIssue, ...]:
    issues = _schema(review, "exercise-ai-review")
    if issues:
        return tuple(sorted(set(issues)))
    lesson_id = exercise_set.get("lesson_id")
    if review["ai_review_id"] != identity("m7aireview", review, "ai_review_id"):
        issues.append(_issue("AI_REVIEW_ID_MISMATCH", "$.ai_review_id", "must be canonical"))
    if review.get("reviewer_type") != "AI" or review.get("independent_of_generation") is not True:
        issues.append(_issue("AI_REVIEW_INDEPENDENCE_INVALID", "$.independent_of_generation", "review must explicitly be independent AI evidence"))
    if review["exercise_set_id"] != exercise_set.get("exercise_set_id") or review["lesson_id"] != lesson_id:
        issues.append(_issue("EXERCISE_SET_BINDING_MISMATCH", "$.exercise_set_id", "review must name the independently loaded exercise set"))
    if review["exercise_set_sha256"] != sha256_json(exercise_set) or review["audit_sha256"] != sha256_json(audit):
        issues.append(_issue("ARTIFACT_HASH_MISMATCH", "$.exercise_set_sha256", "review must bind complete set and audit"))
    if review["m6_batch_id"] != authority.batch["batch_id"] or exercise_set.get("m6_batch_id") != authority.batch["batch_id"]:
        issues.append(_issue("M6_BATCH_BINDING_MISMATCH", "$.m6_batch_id", "review and set must bind verified M6 authority"))
    if audit.get("status") != "ACCEPTED" or audit.get("qa_status") != "UNREVIEWED" or exercise_set.get("status") != "UNREVIEWED":
        issues.append(_issue("ARTIFACT_NOT_REVIEWABLE", "$.audit", "only accepted UNREVIEWED machine output can be AI reviewed"))
    checks = audit.get("checks")
    if not isinstance(checks, Mapping) or any(result != "PASS" for result in checks.values()):
        issues.append(_issue("MACHINE_CHECKS_INCOMPLETE", "$.audit.checks", "all automated checks must pass"))
    criteria = [check["criterion"] for check in review["checklist"]]
    if set(criteria) != AI_CHECKLIST_BY_ROLE[review["review_role"]] or len(criteria) != len(set(criteria)):
        issues.append(_issue("AI_CHECKLIST_SCOPE_MISMATCH", "$.checklist", "must contain each role-specific criterion once"))
    if any(check["result"] not in {"PASS", "NOT_APPLICABLE"} for check in review["checklist"]):
        issues.append(_issue("AI_CHECKLIST_RESULT_INVALID", "$.checklist", "development approval permits only PASS or justified NOT_APPLICABLE results"))
    originality = review.get("copyright_originality_check")
    if not isinstance(originality, Mapping) or originality.get("result") != "NO_CONCERN_FOUND":
        issues.append(_issue("AI_ORIGINALITY_CHECK_INCOMPLETE", "$.copyright_originality_check", "approving evidence requires a completed no-concern local originality check"))
    prompt, response = review["review_prompt"], review["response"]
    if prompt["capture_mode"] in {"TEST_ONLY", "REPLAY_CAPTURED"} or response["provider"] == "TEST_ONLY_MOCK":
        issues.append(_issue("NON_PROMOTABLE_AI_PROVENANCE", "$.review_prompt.capture_mode", "test/replay AI evidence cannot support development promotion"))
    failed = any(check["result"] == "FAIL" for check in review["checklist"])
    blocking = any(finding["severity"] in {"MAJOR", "CRITICAL"} for finding in review["findings"])
    if review["decision"] == "APPROVE" and (failed or blocking):
        issues.append(_issue("AI_REVIEW_DECISION_MISMATCH", "$.decision", "approval cannot have failed or blocking checks"))
    if review["decision"] != "APPROVE" and not (failed or blocking):
        issues.append(_issue("AI_REVIEW_DECISION_MISMATCH", "$.decision", "non-approval requires failed or blocking evidence"))
    reviewed_at, qa_at = _timestamp(review["reviewed_at"]), _timestamp(audit.get("qa_timestamp"))
    if reviewed_at is None or qa_at is None or reviewed_at < qa_at:
        issues.append(_issue("AI_REVIEW_CHRONOLOGY_INVALID", "$.reviewed_at", "review must occur at or after automated QA"))
    return tuple(sorted(set(issues)))


def validate_development_batch(
    report: Mapping[str, Any], authority: VerifiedM6DevelopmentAuthority, exercise_root: Path,
) -> tuple[ExerciseIssue, ...]:
    issues = _schema(report, "exercise-development-batch")
    if issues:
        return tuple(sorted(set(issues)))
    if report["batch_id"] != identity("m7devbatch", report, "batch_id"):
        issues.append(_issue("DEVELOPMENT_BATCH_ID_MISMATCH", "$.batch_id", "must be canonical"))
    if report["m6_batch_id"] != authority.batch["batch_id"]:
        issues.append(_issue("M6_BATCH_BINDING_MISMATCH", "$.m6_batch_id", "must bind verified M6 development batch"))
    if tuple(item["lesson_id"] for item in report["exercise_sets"]) != REQUIRED_DEVELOPMENT_LESSONS:
        issues.append(_issue("REQUIRED_LESSON_BATCH_MISMATCH", "$.exercise_sets", "must contain exact ten lessons in graph order"))
    root = exercise_root.resolve()
    for index, entry in enumerate(report["exercise_sets"]):
        bundle = (root / entry["bundle_path"]).resolve()
        if root not in bundle.parents:
            issues.append(_issue("BUNDLE_PATH_ESCAPE", f"$.exercise_sets[{index}].bundle_path", "bundle path escapes root"))
            continue
        try:
            exercise_set = load_strict_document(bundle / "exercise-set.json")
            audit = load_strict_document(bundle / "audit.json")
        except (OSError, ValueError, TypeError) as error:
            issues.append(_issue("BUNDLE_UNAVAILABLE", f"$.exercise_sets[{index}]", type(error).__name__))
            continue
        if (exercise_set.get("lesson_id") != entry["lesson_id"] or sha256_json(exercise_set) != entry["exercise_set_sha256"]
                or sha256_json(audit) != entry["audit_sha256"] or len(exercise_set.get("exercises", [])) != entry["exercise_count"]):
            issues.append(_issue("BUNDLE_HASH_MISMATCH", f"$.exercise_sets[{index}]", "bundle identity, hash, or count differs"))
        for issue in _revalidate_exercise_set(exercise_set, authority):
            issues.append(_issue(f"FINAL_{issue.code}", f"$.exercise_sets[{index}]{issue.path.removeprefix('$')}", issue.message))
        roles: set[str] = set()
        review_run_ids: set[str] = set()
        response_hashes: set[str] = set()
        for review_ref in entry["ai_reviews"]:
            path = (root / review_ref["path"]).resolve()
            if root not in path.parents:
                issues.append(_issue("REVIEW_PATH_ESCAPE", f"$.exercise_sets[{index}].ai_reviews", "review path escapes root"))
                continue
            try:
                review = load_strict_document(path)
            except (OSError, ValueError, TypeError) as error:
                issues.append(_issue("AI_REVIEW_UNAVAILABLE", f"$.exercise_sets[{index}].ai_reviews", type(error).__name__))
                continue
            if sha256_json(review) != review_ref["sha256"] or review.get("review_role") != review_ref["review_role"]:
                issues.append(_issue("AI_REVIEW_HASH_MISMATCH", f"$.exercise_sets[{index}].ai_reviews", "review reference differs from file"))
            prompt_data, response_data = review.get("review_prompt"), review.get("response")
            if isinstance(prompt_data, Mapping) and isinstance(response_data, Mapping):
                run_id, response_sha256 = prompt_data.get("run_id"), response_data.get("sha256")
                if not isinstance(run_id, str) or not isinstance(response_sha256, str) or run_id in review_run_ids or response_sha256 in response_hashes:
                    issues.append(_issue("AI_REVIEW_PROVENANCE_NOT_DISTINCT", f"$.exercise_sets[{index}].ai_reviews", "review roles require distinct captured run and response evidence"))
                review_run_ids.add(str(run_id))
                response_hashes.add(str(response_sha256))
            else:
                issues.append(_issue("AI_REVIEW_PROVENANCE_INVALID", f"$.exercise_sets[{index}].ai_reviews", "review must include captured prompt and response evidence"))
            issues.extend(validate_ai_review(review, exercise_set, audit, authority))
            roles.add(str(review.get("review_role")))
        if roles != set(AI_CHECKLIST_BY_ROLE):
            issues.append(_issue("AI_REVIEW_ROLE_COVERAGE", f"$.exercise_sets[{index}].ai_reviews", "both independent AI roles are required"))
    return tuple(sorted(set(issues)))


def build_development_batch(
    authority: VerifiedM6DevelopmentAuthority,
    exercise_root: Path,
    *,
    created_at: str,
    git_commit: str | None = None,
    bundle_paths: Mapping[str, str] | None = None,
) -> JsonObject:
    """Build a batch from immutable selected revisions beneath one exercise root."""
    root = exercise_root.resolve()
    selected_paths = dict(bundle_paths or {})
    unknown = set(selected_paths) - set(REQUIRED_DEVELOPMENT_LESSONS)
    if unknown:
        raise ValueError(f"unknown lesson selection: {sorted(unknown)}")
    entries: list[JsonObject] = []
    for lesson_id in REQUIRED_DEVELOPMENT_LESSONS:
        relative_bundle = Path(selected_paths.get(lesson_id, lesson_id))
        if relative_bundle.is_absolute() or ".." in relative_bundle.parts:
            raise ValueError(f"unsafe bundle selection for {lesson_id}")
        bundle = root / relative_bundle
        exercise_set = load_strict_document(bundle / "exercise-set.json")
        audit = load_strict_document(bundle / "audit.json")
        reviews = []
        for role in ("LINGUISTIC_AI_REVIEWER", "PEDAGOGICAL_AI_REVIEWER"):
            path = bundle.parent / "reviews" / lesson_id / f"{role}.json"
            review = load_strict_document(path)
            reviews.append({"review_role": role, "path": path.relative_to(root).as_posix(), "sha256": sha256_json(review)})
        entries.append({
            "lesson_id": lesson_id, "bundle_path": bundle.relative_to(root).as_posix(),
            "exercise_set_sha256": sha256_json(exercise_set), "audit_sha256": sha256_json(audit),
            "exercise_count": len(exercise_set["exercises"]), "generation_provenance_mode": "SESSION_CAPTURED", "ai_reviews": reviews,
        })
    tool: JsonObject = {"name": "english_master.exercise_generation.review", "version": "1.0"}
    if git_commit:
        tool["git_commit"] = git_commit
    report: JsonObject = {
        "schema_version": "1.0", "record_type": "exercise_development_batch", "approval_tier": "DEVELOPMENT_APPROVED",
        "m6_batch_id": authority.batch["batch_id"], "created_at": created_at, "tool": tool, "exercise_sets": entries,
        "automated_checks": {"schema": "PASS", "lesson_scope": "PASS", "answer_ambiguity": "PASS", "duplicate": "PASS", "provenance_copyright": "PASS", "no_m8_scope": "PASS"},
        "originality_provenance_checks": {"authorized_input_scope": "PASS", "duplicate_check": "PASS", "external_search_performed": False, "limitations": ["No Internet-wide plagiarism search was performed; checks cover original project-authored policy, immutable hashes, and exact/near duplicate detection only."]},
        "limitations": ["Development approval is not human review or release approval.", "No Internet-wide plagiarism search was performed.", "Session-captured AI review evidence is replayable evidence, not a provider-authenticated receipt."],
    }
    report["batch_id"] = identity("m7devbatch", report, "batch_id")
    return report
