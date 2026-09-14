"""Language-bound objective scoring for future multilingual course packages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

from .learner_state import _atomic_write_state, _next_review, _parse_utc, _response_correct


def _require_language_concept_ids(package: dict[str, Any], language_code: str) -> None:
    prefix = f"kg_{language_code}_"
    for item in package["items"]:
        for concept_id in item["concept_ids"]:
            if not concept_id.startswith(prefix):
                raise ValueError(
                    f"assessment item {item['item_id']} has concept {concept_id!r} outside language {language_code!r}"
                )


def _load_state(path: Path, language_code: str) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema_version": "2.0",
            "record_type": "learner_concept_state",
            "language_code": language_code,
            "concepts": [],
        }
    state = load_document(path)
    validate_instance(state, "learner-concept-state-v2")
    if state["language_code"] != language_code:
        raise ValueError("learner state language does not match assessment language")
    concepts = state["concepts"]
    concept_ids = [row["concept_id"] for row in concepts]
    if concept_ids != sorted(concept_ids) or len(concept_ids) != len(set(concept_ids)):
        raise ValueError("learner concept state must contain unique records sorted by concept_id")
    prefix = f"kg_{language_code}_"
    for row in concepts:
        if not row["concept_id"].startswith(prefix):
            raise ValueError("learner state contains a concept outside its declared language")
        if row["attempts"] != row["correct"] + row["incorrect"]:
            raise ValueError(f"learner concept state counter mismatch for {row['concept_id']}")
        if row["mastery"] != round(row["correct"] / row["attempts"], 4):
            raise ValueError(f"learner concept state mastery mismatch for {row['concept_id']}")
        _parse_utc(row["last_seen"])
        _parse_utc(row["next_review"])
    return state


def score_multilingual_submission(*, package_path: Path, submission_path: Path, state_path: Path) -> dict[str, Any]:
    """Score one language-bound wrapper and atomically update only its state file."""

    package_wrapper = load_document(package_path)
    submission_wrapper = load_document(submission_path)
    validate_instance(package_wrapper, "multilingual-assessment-package-v1")
    validate_instance(submission_wrapper, "multilingual-assessment-submission-v1")
    language_code = package_wrapper["language_code"]
    if submission_wrapper["language_code"] != language_code:
        raise ValueError("assessment package and submission languages do not match")

    package = package_wrapper["assessment"]
    submission = submission_wrapper["submission"]
    if package["package_sha256"] != sha256_json({key: value for key, value in package.items() if key != "package_sha256"}):
        raise ValueError("assessment package hash mismatch")
    if submission["submission_sha256"] != sha256_json({key: value for key, value in submission.items() if key != "submission_sha256"}):
        raise ValueError("assessment submission hash mismatch")
    if submission["assessment_id"] != package["assessment_id"] or submission["package_sha256"] != package["package_sha256"]:
        raise ValueError("assessment submission package binding mismatch")
    _require_language_concept_ids(package, language_code)

    item_by_id = {item["item_id"]: item for item in package["items"]}
    responses = submission["responses"]
    response_ids = [row["item_id"] for row in responses]
    if len(response_ids) != len(set(response_ids)) or set(response_ids) != set(item_by_id):
        raise ValueError("assessment submission must contain one response for every assessment item")

    seen = _parse_utc(submission["seen_at"])
    outcomes: dict[str, list[bool]] = {}
    results: list[dict[str, Any]] = []
    for response in responses:
        item = item_by_id[response["item_id"]]
        correct = _response_correct(item, response["answer"])
        results.append({"item_id": item["item_id"], "correct": correct})
        for concept_id in set(item["concept_ids"]):
            outcomes.setdefault(concept_id, []).append(correct)

    state = _load_state(state_path, language_code)
    by_concept = {row["concept_id"]: dict(row) for row in state["concepts"]}
    changed = []
    for concept_id, values in sorted(outcomes.items()):
        row = by_concept.get(concept_id, {
            "concept_id": concept_id, "attempts": 0, "correct": 0, "incorrect": 0,
            "mastery": 0.0, "last_seen": submission["seen_at"], "next_review": submission["seen_at"],
        })
        if concept_id in by_concept and _parse_utc(row["last_seen"]) > seen:
            raise ValueError(f"seen_at precedes existing last_seen for concept {concept_id}")
        row["attempts"] += len(values)
        row["correct"] += sum(values)
        row["incorrect"] += len(values) - sum(values)
        row["mastery"] = round(row["correct"] / row["attempts"], 4)
        row["last_seen"] = submission["seen_at"]
        row["next_review"] = _next_review(correct=all(values), mastery=row["mastery"], attempts=row["attempts"], seen=seen)
        by_concept[concept_id] = row
        changed.append(dict(row))

    next_state = {
        "schema_version": "2.0",
        "record_type": "learner_concept_state",
        "language_code": language_code,
        "concepts": [by_concept[key] for key in sorted(by_concept)],
    }
    validate_instance(next_state, "learner-concept-state-v2")
    _atomic_write_state(state_path, next_state)
    correct_count = sum(result["correct"] for result in results)
    return {
        "language_code": language_code,
        "assessment_id": package["assessment_id"],
        "correct": correct_count,
        "incorrect": len(results) - correct_count,
        "total": len(results),
        "score": round(correct_count / len(results), 4),
        "item_results": results,
        "changed_concept_states": changed,
    }
