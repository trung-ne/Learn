"""Typed contracts for deterministic post-ingestion normalization."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any


class RecordDisposition(StrEnum):
    """Machine disposition before any semantic review decision."""

    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class DeduplicationReason(StrEnum):
    """Explainable reasons for an exact duplicate group."""

    RAW_HASH = "RAW_HASH"
    NORMALIZED_HASH = "NORMALIZED_HASH"


class ReviewDisposition(StrEnum):
    """Allowed explicit human decisions for a similarity candidate."""

    DUPLICATE = "DUPLICATE"
    NOT_DUPLICATE = "NOT_DUPLICATE"
    RELATED_NOT_DUPLICATE = "RELATED_NOT_DUPLICATE"


@dataclass(frozen=True)
class NormalizationPolicy:
    """Versioned, deterministic text-comparison policy."""

    version: str = "text-nfc-casefold-v1"
    unicode_form: str = "NFC"
    collapse_whitespace: bool = True
    casefold: bool = True
    punctuation: str = "space"

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "unicode_form": self.unicode_form,
            "collapse_whitespace": self.collapse_whitespace,
            "casefold": self.casefold,
            "punctuation": self.punctuation,
        }


@dataclass(frozen=True)
class NearDuplicatePolicy:
    """Bounded character n-gram candidate and scoring policy."""

    version: str = "char-ngram-jaccard-v1"
    ngram_size: int = 3
    threshold: float = 0.85
    minimum_characters: int = 12
    max_candidates_per_record: int = 50
    same_language_only: bool = True

    def validate(self) -> None:
        if not 2 <= self.ngram_size <= 8:
            raise ValueError("ngram_size must be between 2 and 8")
        if not 0.0 <= self.threshold <= 1.0:
            raise ValueError("near_threshold must be between 0 and 1")
        if self.minimum_characters < self.ngram_size:
            raise ValueError("minimum_characters must be at least ngram_size")
        if not 1 <= self.max_candidates_per_record <= 10_000:
            raise ValueError("max_candidates_per_record must be between 1 and 10000")

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "method": "character_ngram_jaccard",
            "ngram_size": self.ngram_size,
            "threshold": self.threshold,
            "minimum_characters": self.minimum_characters,
            "max_candidates_per_record": self.max_candidates_per_record,
            "same_language_only": self.same_language_only,
        }


@dataclass(frozen=True)
class InputRecord:
    """A validated M3 record and its immutable storage location."""

    document: dict[str, Any]
    location: Path


@dataclass(frozen=True)
class ProcessedRecord:
    """Internal processed-record view used between pipeline stages."""

    document: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.document["id"])

    @property
    def source_record_id(self) -> str:
        return str(self.document["source_record_id"])

    @property
    def language(self) -> str:
        return str(self.document["language"])

    @property
    def comparison_text(self) -> str:
        return str(self.document["comparison_text"])

    @property
    def raw_hash(self) -> str:
        return str(self.document["raw_hash"])

    @property
    def normalized_hash(self) -> str:
        return str(self.document["normalized_hash"])
