"""Typed contracts and shared records for source-specific ingestion adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, TypeVar

RawRecordT = TypeVar("RawRecordT")


@dataclass(frozen=True)
class FetchOptions:
    """Explicit, bounded inputs for an offline source fetch."""

    input_path: Path
    max_records: int
    retrieved_at: datetime


@dataclass(frozen=True)
class RawPayload:
    """The exact bounded bytes returned by an adapter fetch."""

    content: bytes
    input_description: dict[str, Any]


@dataclass(frozen=True)
class RecordError:
    """A structured record-level failure that can be quarantined."""

    stage: str
    code: str
    message: str
    record_index: int | None = None
    source_record_id: str | None = None
    raw_record: str | None = None

    def as_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
        }
        if self.record_index is not None:
            value["record_index"] = self.record_index
        if self.source_record_id is not None:
            value["source_record_id"] = self.source_record_id
        if self.raw_record is not None:
            value["raw_record"] = self.raw_record
        return value


@dataclass(frozen=True)
class ParseResult(Generic[RawRecordT]):
    """All parsed records and all failures; adapters may not drop failures."""

    records: tuple[RawRecordT, ...]
    errors: tuple[RecordError, ...]


class SourceAdapter(ABC, Generic[RawRecordT]):
    """Contract isolating source fetch, parse, provenance, and normalization.

    ``fetch`` must accept only bounded explicit inputs and preserve fetched bytes.
    ``parse`` must retain source identity and report every malformed record.
    ``provenance`` hashes the documented original record representation.
    ``normalize`` maps only permitted fields and never performs CEFR classification.
    """

    source_id: str
    adapter_id: str
    ingestion_version: str
    normalized_schema: str
    required_operations: tuple[str, ...]

    @abstractmethod
    def fetch(self, options: FetchOptions) -> RawPayload:
        """Fetch a bounded payload without rewriting source data."""

    @abstractmethod
    def parse(self, payload: RawPayload) -> ParseResult[RawRecordT]:
        """Split the payload into raw records and report malformed records."""

    @abstractmethod
    def provenance(
        self,
        record: RawRecordT,
        source: dict[str, Any],
        options: FetchOptions,
    ) -> dict[str, Any]:
        """Build complete policy provenance for one original raw record."""

    @abstractmethod
    def normalize(
        self,
        record: RawRecordT,
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        """Produce one canonical record without CEFR fields."""
