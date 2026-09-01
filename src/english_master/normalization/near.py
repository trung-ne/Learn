"""Bounded, explainable character n-gram near-duplicate detection."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from english_master.normalization.hashes import canonical_json_bytes, sha256_bytes
from english_master.normalization.models import NearDuplicatePolicy, ProcessedRecord
from english_master.normalization.text import character_ngrams, comparison_characters


def jaccard_similarity(left: frozenset[str], right: frozenset[str]) -> tuple[float, int, int]:
    """Return score, intersection size, and union size for two sets."""

    union = left | right
    intersection_size = len(left & right)
    return ((intersection_size / len(union)) if union else 1.0, intersection_size, len(union))


def find_near_duplicate_candidates(
    records: Iterable[ProcessedRecord], policy: NearDuplicatePolicy | None = None
) -> tuple[dict[str, object], ...]:
    """Score only bounded candidates obtained from an n-gram inverted index."""

    selected = policy or NearDuplicatePolicy()
    selected.validate()
    ordered = sorted(records, key=lambda record: record.id)
    grams_by_id: dict[str, frozenset[str]] = {}
    eligible: list[ProcessedRecord] = []
    for record in ordered:
        compact = comparison_characters(record.comparison_text)
        if len(compact) < selected.minimum_characters:
            continue
        grams = character_ngrams(record.comparison_text, selected.ngram_size)
        if grams:
            grams_by_id[record.id] = grams
            eligible.append(record)

    by_id = {record.id: record for record in eligible}
    inverted: dict[tuple[str, str], list[str]] = defaultdict(list)
    for record in eligible:
        language_scope = record.language if selected.same_language_only else "*"
        for gram in sorted(grams_by_id[record.id]):
            inverted[(language_scope, gram)].append(record.id)

    emitted_pairs: set[tuple[str, str]] = set()
    candidates: list[dict[str, object]] = []
    for record in eligible:
        overlap_counts: dict[str, int] = defaultdict(int)
        language_scope = record.language if selected.same_language_only else "*"
        for gram in grams_by_id[record.id]:
            for other_id in inverted[(language_scope, gram)]:
                if other_id > record.id:
                    overlap_counts[other_id] += 1
        bounded = sorted(overlap_counts, key=lambda item: (-overlap_counts[item], item))[
            : selected.max_candidates_per_record
        ]
        for other_id in bounded:
            pair = (record.id, other_id)
            if pair in emitted_pairs:
                continue
            emitted_pairs.add(pair)
            other = by_id[other_id]
            if record.normalized_hash == other.normalized_hash:
                continue
            left = grams_by_id[record.id]
            right = grams_by_id[other.id]
            score, intersection_size, union_size = jaccard_similarity(left, right)
            if score < selected.threshold:
                continue
            matched = sorted(left & right)
            material = {"left_record_id": record.id, "right_record_id": other.id, "policy": selected.as_dict()}
            candidate_id = f"sim_{sha256_bytes(canonical_json_bytes(material))[:20]}"
            candidates.append(
                {
                    "schema_version": "1.0",
                    "record_type": "similarity_candidate",
                    "id": candidate_id,
                    "left_record_id": record.id,
                    "right_record_id": other.id,
                    "language": record.language if record.language == other.language else None,
                    "method": "character_ngram_jaccard",
                    "score": round(score, 12),
                    "threshold": selected.threshold,
                    "evidence": {
                        "ngram_size": selected.ngram_size,
                        "intersection_count": intersection_size,
                        "union_count": union_size,
                        "matched_ngram_sample": matched[:10],
                        "short_text_safeguard_passed": True,
                    },
                    "policy_version": selected.version,
                    "disposition": "REVIEW_REQUIRED",
                }
            )
    return tuple(sorted(candidates, key=lambda candidate: str(candidate["id"])))
