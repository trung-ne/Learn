from __future__ import annotations

from datetime import UTC, datetime

import pytest

from english_master.normalization.exact import ExactDeduplicationError, build_exact_groups
from english_master.normalization.hashes import canonical_json_bytes, normalized_comparison_hash, raw_record_hash
from english_master.normalization.models import NearDuplicatePolicy, ProcessedRecord, ReviewDisposition
from english_master.normalization.near import find_near_duplicate_candidates, jaccard_similarity
from english_master.normalization.semantic import create_review_decision, validate_review_decisions
from english_master.normalization.text import character_ngrams, normalize_comparison_text, normalize_display_text
from english_master.schema_validation import validate_instance


def processed(identifier: str, raw_hash: str, normalized_hash: str, text: str = "example text long") -> ProcessedRecord:
    return ProcessedRecord({"id": identifier, "source_id": "src_tatoeba_text", "source_record_id": identifier, "language": "en", "comparison_text": text, "raw_hash": raw_hash, "normalized_hash": normalized_hash, "original_raw_location": f"{identifier}.json"})


def test_text_normalization_is_idempotent_unicode_safe_and_comparison_only() -> None:
    source = "  CAFÉ\r\n—  We'll…  Việt Nam!  "
    display = normalize_display_text(source)
    comparison = normalize_comparison_text(source)
    assert display == "CAFÉ — We'll… Việt Nam!"
    assert comparison == "café we'll việt nam"
    assert normalize_display_text(display) == display
    assert normalize_comparison_text(comparison) == comparison
    assert source.startswith("  ")


def test_hash_contracts_are_deterministic_and_language_scoped() -> None:
    first = {"text": "Hello", "id": "one"}
    second = {"text": "Hello ", "id": "one"}
    assert canonical_json_bytes({"é": 1, "a": 2}) == b'{"a":2,"\xc3\xa9":1}\n'
    assert raw_record_hash(first) == raw_record_hash(first)
    assert raw_record_hash(first) != raw_record_hash(second)
    assert normalized_comparison_hash("en", "hello") != normalized_comparison_hash("vi", "hello")


def test_exact_groups_and_inconsistent_identity_detection() -> None:
    records = (processed("norm_" + "1" * 20, "a" * 64, "b" * 64), processed("norm_" + "2" * 20, "a" * 64, "b" * 64))
    groups = build_exact_groups(records)
    assert len(groups) == 1
    assert groups[0]["deduplication_reason"] == "RAW_HASH"
    conflicting = ProcessedRecord({**records[1].document, "source_record_id": records[0].source_record_id, "raw_hash": "c" * 64})
    with pytest.raises(ExactDeduplicationError, match="Inconsistent raw content"):
        build_exact_groups((records[0], conflicting))


def test_ngram_similarity_is_explainable_bounded_and_language_safe() -> None:
    assert jaccard_similarity(frozenset({"a", "b"}), frozenset({"b", "c"})) == (1 / 3, 1, 3)
    left = processed("norm_" + "1" * 20, "1" * 64, "a" * 64, "the quick brown fox jumps")
    right = processed("norm_" + "2" * 20, "2" * 64, "b" * 64, "the quick brown fox jump")
    vietnamese = ProcessedRecord({**right.document, "id": "norm_" + "3" * 20, "language": "vi"})
    short = processed("norm_" + "4" * 20, "4" * 64, "d" * 64, "hi")
    candidates = find_near_duplicate_candidates((left, right, vietnamese, short), NearDuplicatePolicy(threshold=0.7, max_candidates_per_record=1))
    assert len(candidates) == 1
    assert candidates[0]["evidence"]["intersection_count"] > 0
    assert character_ngrams("abcd", 3) == frozenset({"abc", "bcd"})


def test_semantic_review_requires_human_supported_decision() -> None:
    decision = create_review_decision(candidate_id="sim_" + "a" * 20, disposition=ReviewDisposition.RELATED_NOT_DUPLICATE, relationship="TRANSLATION", reviewer="reviewer-1", reviewed_at=datetime(2026, 8, 31, tzinfo=UTC), reason="Preserve both records.", evidence=["manual bilingual review"])
    validate_instance(decision, "semantic-review")
    validate_review_decisions([decision], {"sim_" + "a" * 20})
    with pytest.raises(ValueError, match="unknown candidate"):
        validate_review_decisions([decision], set())
    with pytest.raises(ValueError, match="automatic merge states"):
        create_review_decision(candidate_id="sim_" + "a" * 20, disposition="AUTO_MERGE", relationship="OTHER", reviewer="robot", reviewed_at=datetime(2026, 8, 31, tzinfo=UTC), reason="score", evidence=["ngram"])
