"""Objective scoring and atomic caller-managed local concept state."""

from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import sha256_json
from english_master.schema_validation import load_document, validate_instance

from .service import TIER_ORDER


def _normal(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError("seen_at must be an explicit UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("seen_at must be a valid ISO 8601 UTC timestamp") from error
    if parsed.tzinfo != timezone.utc:
        raise ValueError("seen_at must use UTC")
    return parsed


def _utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _state_document(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, item in pairs:
            if key in value:
                raise ValueError(f"duplicate learner-state key {key!r}")
            value[key] = item
        return value

    with path.open("r", encoding="utf-8") as file:
        state = json.load(file, object_pairs_hook=unique_object)
    validate_instance(state, "learner-concept-state-v1")
    concept_ids = [row["concept_id"] for row in state]
    if concept_ids != sorted(concept_ids) or len(concept_ids) != len(set(concept_ids)):
        raise ValueError("learner concept state must contain unique records sorted by concept_id")
    for row in state:
        if row["attempts"] != row["correct"] + row["incorrect"]:
            raise ValueError(f"learner concept state counter mismatch for {row['concept_id']}")
        if row["mastery"] != round(row["correct"] / row["attempts"], 4):
            raise ValueError(f"learner concept state mastery mismatch for {row['concept_id']}")
        _parse_utc(row["last_seen"])
        _parse_utc(row["next_review"])
    return state


def _response_correct(item: Mapping[str, Any], response: Any) -> bool:
    contract = item["answer_contract"]
    if "correct_answer" in contract:
        return isinstance(response, str) and _normal(response) == _normal(contract["correct_answer"])
    if "acceptable_answers" in contract:
        return isinstance(response, str) and _normal(response) in {_normal(value) for value in contract["acceptable_answers"]}
    if "correct_order" in contract:
        return isinstance(response, list) and all(isinstance(value, str) for value in response) and [_normal(value) for value in response] == [_normal(value) for value in contract["correct_order"]]
    if "pairs" in contract:
        if not isinstance(response, list) or not all(isinstance(pair, dict) and set(pair) == {"left", "right"} and isinstance(pair["left"], str) and isinstance(pair["right"], str) for pair in response):
            return False
        actual = sorted((_normal(pair["left"]), _normal(pair["right"])) for pair in response)
        expected = sorted((_normal(pair["left"]), _normal(pair["right"])) for pair in contract["pairs"])
        return actual == expected
    raise ValueError(f"item {item['item_id']} has no supported answer contract")


def _next_review(*, correct: bool, mastery: float, attempts: int, seen: datetime) -> str:
    if not correct:
        delay = 0
    elif mastery < 0.8:
        delay = 1
    elif attempts < 3:
        delay = 3
    elif attempts <= 5:
        delay = 7
    else:
        delay = 30
    return _utc(seen + timedelta(days=delay))


def _atomic_write_state(path: Path, state: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(list(state), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def score_submission(*, package_path: Path, submission_path: Path, state_path: Path) -> dict[str, Any]:
    """Validate completely, score objectively, then atomically replace local state."""
    package = load_document(package_path)
    validate_instance(package, "assessment-package-v1")
    if package["package_sha256"] != sha256_json({key: value for key, value in package.items() if key != "package_sha256"}):
        raise ValueError("assessment package hash mismatch")
    item_ids = [item["item_id"] for item in package["items"]]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("assessment package contains duplicate item IDs")
    for item in package["items"]:
        if item["item_sha256"] != sha256_json({key: value for key, value in item.items() if key != "item_sha256"}):
            raise ValueError(f"assessment item hash mismatch: {item['item_id']}")
    submission = load_document(submission_path)
    validate_instance(submission, "assessment-submission-v1")
    if submission["submission_sha256"] != sha256_json({key: value for key, value in submission.items() if key != "submission_sha256"}):
        raise ValueError("assessment submission hash mismatch")
    if submission["assessment_id"] != package["assessment_id"] or submission["package_sha256"] != package["package_sha256"]:
        raise ValueError("assessment submission package binding mismatch")
    seen = _parse_utc(submission["seen_at"])
    item_by_id = {item["item_id"]: item for item in package["items"]}
    responses = submission["responses"]
    response_ids = [row["item_id"] for row in responses]
    if len(response_ids) != len(set(response_ids)):
        raise ValueError("assessment submission contains duplicate item responses")
    if set(response_ids) != set(item_by_id):
        missing = sorted(set(item_by_id) - set(response_ids))
        extra = sorted(set(response_ids) - set(item_by_id))
        raise ValueError(f"assessment submission must be complete; missing={missing!r}, extra={extra!r}")

    results = []
    concept_outcomes: dict[str, list[bool]] = {}
    tier_scores = {tier: {"correct": 0, "total": 0} for tier in TIER_ORDER}
    for response_row in responses:
        item = item_by_id[response_row["item_id"]]
        correct = _response_correct(item, response_row["answer"])
        results.append({"item_id": item["item_id"], "correct": correct})
        tier_score = tier_scores[item["source"]["tier"]]
        tier_score["total"] += 1
        tier_score["correct"] += int(correct)
        for concept_id in set(item["concept_ids"]):
            concept_outcomes.setdefault(concept_id, []).append(correct)

    existing = _state_document(state_path)
    by_concept = {row["concept_id"]: dict(row) for row in existing}
    changed = []
    for concept_id, outcomes in sorted(concept_outcomes.items()):
        row = by_concept.get(concept_id, {
            "concept_id": concept_id, "attempts": 0, "correct": 0, "incorrect": 0,
            "mastery": 0.0, "last_seen": submission["seen_at"], "next_review": submission["seen_at"],
        })
        if concept_id in by_concept and _parse_utc(row["last_seen"]) > seen:
            raise ValueError(f"seen_at precedes existing last_seen for concept {concept_id}")
        row["attempts"] += len(outcomes)
        row["correct"] += sum(outcomes)
        row["incorrect"] += len(outcomes) - sum(outcomes)
        row["mastery"] = round(row["correct"] / row["attempts"], 4)
        row["last_seen"] = submission["seen_at"]
        row["next_review"] = _next_review(correct=all(outcomes), mastery=row["mastery"], attempts=row["attempts"], seen=seen)
        by_concept[concept_id] = row
        changed.append(dict(row))
    new_state = [by_concept[key] for key in sorted(by_concept)]
    validate_instance(new_state, "learner-concept-state-v1")
    _atomic_write_state(state_path, new_state)

    correct_count = sum(result["correct"] for result in results)
    output: dict[str, Any] = {
        "assessment_id": package["assessment_id"], "correct": correct_count,
        "incorrect": len(results) - correct_count, "total": len(results),
        "score": round(correct_count / len(results), 4), "item_results": results,
        "changed_concept_states": changed,
    }
    if package["assessment_type"] == "PLACEMENT":
        per_tier = []
        suggested = "C2.2"
        found = False
        for tier in TIER_ORDER:
            score = tier_scores[tier]
            met = score == {"correct": 2, "total": 2}
            per_tier.append({"tier": tier, **score, "met_threshold": met})
            if not met and not found:
                suggested = tier
                found = True
        output["tier_scores"] = per_tier
        output["suggested_start_tier"] = suggested
        output["placement_limitation"] = "Offline fixed 2/2 heuristic only; not a validated diagnostic, CEFR certification, or learner-proficiency claim."
    return output
