"""Stable learner-facing projections for M8 duplicate QA."""
from __future__ import annotations

import copy
from typing import Any, Mapping, Sequence

from english_master.lesson_generation.canonical import canonical_json, sha256_json
from english_master.normalization.near import jaccard_similarity
from english_master.normalization.text import character_ngrams, normalize_comparison_text

PROJECTION_VERSION = "M8_LEARNER_FACING_EXERCISE_v1"
NEAR_POLICY_VERSION = "M8_CHARACTER_5GRAM_JACCARD_0.999_v1"

_EXERCISE_FIELDS = (
    "title",
    "exercise_type",
    "cefr_level",
    "difficulty",
    "instructions",
    "objective_indices",
    "target_references",
    "review_references",
    "scoring_mode",
    "payload",
)


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_comparison_text(value)
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, Mapping):
        return {key: _normalize(value[key]) for key in sorted(value)}
    return copy.deepcopy(value)


def exercise_projection(exercise: Mapping[str, Any]) -> dict[str, Any]:
    """Exclude volatile identity/provenance while retaining substantive content."""

    return {
        key: _normalize(exercise[key])
        for key in _EXERCISE_FIELDS
        if key in exercise
    }


def set_projection(candidate: Mapping[str, Any]) -> list[dict[str, Any]]:
    exercises = candidate.get("exercises", [])
    if not isinstance(exercises, list):
        return []
    return [
        exercise_projection(item)
        for item in exercises
        if isinstance(item, Mapping)
    ]


def projection_hash(candidate: Mapping[str, Any]) -> str:
    return sha256_json(set_projection(candidate))


def projection_text(candidate: Mapping[str, Any]) -> str:
    return normalize_comparison_text(canonical_json(set_projection(candidate)))


def is_near_duplicate(candidate: Mapping[str, Any], prior: Mapping[str, Any]) -> bool:
    left = character_ngrams(projection_text(candidate), 5)
    right = character_ngrams(projection_text(prior), 5)
    if not left or not right:
        return projection_hash(candidate) == projection_hash(prior)
    score, _, _ = jaccard_similarity(left, right)
    return score >= 0.999


def prior_projection_hashes(candidates: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    return tuple(projection_hash(item) for item in candidates)
