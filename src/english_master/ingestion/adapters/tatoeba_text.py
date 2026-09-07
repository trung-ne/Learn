"""Bounded offline adapter for Tatoeba sentence-text export fixtures."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from typing import Any

from english_master.ingestion.base import (
    FetchOptions,
    ParseResult,
    RawPayload,
    RecordError,
    SourceAdapter,
)

EXPECTED_HEADER = (
    "sentence_id",
    "language",
    "text",
    "author",
    "license",
    "license_url",
)
MAX_FIXTURE_BYTES = 1_000_000
MAX_RECORDS = 100
MAX_PILOT_BYTES = 50_000_000
MIN_PILOT_RECORDS = 1_000
MAX_PILOT_RECORDS = 5_000


@dataclass(frozen=True)
class TatoebaTextRecord:
    """One original TSV row plus its parsed source fields."""

    sentence_id: str
    language: str
    text: str
    author: str
    license: str
    license_url: str
    raw_line: bytes


class TatoebaTextAdapter(SourceAdapter[TatoebaTextRecord]):
    """Read a tiny local TSV shaped like a documented Tatoeba text export.

    M3 intentionally provides no network mode. The whole fixture must fit both the
    byte cap and caller-supplied record cap, so no trailing records are ignored.
    """

    source_id = "src_tatoeba_text"
    adapter_id = "tatoeba_text_offline_tsv_v1"
    ingestion_version = "m3-tatoeba-text-v1"
    normalized_schema = "normalized-text"
    required_operations = (
        "fetch_source",
        "ingest_source",
        "store_source",
        "transform_source",
        "ingest_text",
        "store_text",
        "transform_text",
    )

    def fetch(self, options: FetchOptions) -> RawPayload:
        pilot = options.input_mode == "authorized_pilot"
        if options.input_mode not in {"offline_fixture", "authorized_pilot"}:
            raise ValueError(f"Unsupported Tatoeba input mode: {options.input_mode!r}")
        minimum, maximum = (
            (MIN_PILOT_RECORDS, MAX_PILOT_RECORDS) if pilot else (1, MAX_RECORDS)
        )
        max_bytes = MAX_PILOT_BYTES if pilot else MAX_FIXTURE_BYTES
        if not minimum <= options.max_records <= maximum:
            raise ValueError(f"max_records must be between {minimum} and {maximum}")
        path = options.input_path.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Bounded input does not exist: {path}")
        size = path.stat().st_size
        if size > max_bytes:
            raise ValueError(f"Bounded input exceeds {max_bytes} bytes: {size}")
        content = path.read_bytes()
        lines = content.splitlines()
        record_count = max(0, len(lines) - 1)
        if record_count > options.max_records:
            raise ValueError(
                f"Input contains {record_count} records, exceeding --max-records {options.max_records}"
            )
        if pilot and record_count != options.max_records:
            raise ValueError("Authorized pilot input must contain exactly --max-records records")
        return RawPayload(
            content=content,
            input_description={
                "mode": options.input_mode,
                "input_name": path.name,
                "input_sha256": hashlib.sha256(content).hexdigest(),
                "input_bytes": len(content),
                "record_count": record_count,
                "max_records": options.max_records,
            },
        )

    def parse(self, payload: RawPayload) -> ParseResult[TatoebaTextRecord]:
        try:
            lines = payload.content.splitlines()
            header_text = lines[0].decode("utf-8-sig") if lines else ""
        except UnicodeDecodeError as error:
            return ParseResult((), (RecordError("parse", "invalid_utf8", str(error)),))

        try:
            header = tuple(next(csv.reader([header_text], delimiter="\t", strict=True)))
        except (csv.Error, StopIteration) as error:
            return ParseResult((), (RecordError("parse", "malformed_header", str(error)),))
        if header != EXPECTED_HEADER:
            return ParseResult(
                (),
                (
                    RecordError(
                        "parse",
                        "invalid_header",
                        f"Expected tab-separated header {EXPECTED_HEADER!r}, received {header!r}",
                        raw_record=header_text,
                    ),
                ),
            )

        records: list[TatoebaTextRecord] = []
        errors: list[RecordError] = []
        seen_ids: set[str] = set()
        for index, raw_line in enumerate(lines[1:], start=1):
            try:
                line = raw_line.decode("utf-8")
                fields = next(csv.reader([line], delimiter="\t", strict=True))
            except (UnicodeDecodeError, csv.Error, StopIteration) as error:
                errors.append(
                    RecordError("parse", "malformed_tsv", str(error), index, raw_record=raw_line.hex())
                )
                continue
            if len(fields) != len(EXPECTED_HEADER):
                errors.append(
                    RecordError(
                        "parse",
                        "wrong_field_count",
                        f"Expected {len(EXPECTED_HEADER)} fields, received {len(fields)}",
                        index,
                        raw_record=line,
                    )
                )
                continue
            values = dict(zip(EXPECTED_HEADER, fields, strict=True))
            sentence_id = values["sentence_id"]
            if not all(values.values()):
                errors.append(
                    RecordError(
                        "parse",
                        "missing_required_field",
                        "Every source field must be nonempty",
                        index,
                        sentence_id or None,
                        line,
                    )
                )
                continue
            if not sentence_id.isascii() or not sentence_id.isdigit():
                errors.append(
                    RecordError(
                        "parse",
                        "invalid_source_record_id",
                        "sentence_id must contain ASCII digits only",
                        index,
                        sentence_id,
                        line,
                    )
                )
                continue
            if sentence_id in seen_ids:
                errors.append(
                    RecordError(
                        "parse",
                        "duplicate_source_record_id",
                        f"Duplicate sentence_id {sentence_id!r}",
                        index,
                        sentence_id,
                        line,
                    )
                )
                continue
            seen_ids.add(sentence_id)
            records.append(
                TatoebaTextRecord(
                    sentence_id=sentence_id,
                    language=values["language"],
                    text=values["text"],
                    author=values["author"],
                    license=values["license"],
                    license_url=values["license_url"],
                    raw_line=raw_line,
                )
            )
        return ParseResult(tuple(records), tuple(errors))

    def provenance(
        self,
        record: TatoebaTextRecord,
        source: dict[str, Any],
        options: FetchOptions,
    ) -> dict[str, Any]:
        if options.input_mode == "authorized_pilot" and record.language.lower() != "eng":
            raise ValueError(f"Pilot record {record.sentence_id} is not English")
        registered_license = source["license"]
        if record.license != registered_license["name"] or record.license_url != registered_license["url"]:
            raise ValueError(
                f"Record {record.sentence_id} license is not in this adapter's approved license lane"
            )
        attribution_template = source["attribution"]["format"]
        if not isinstance(attribution_template, str):
            raise ValueError("Registered attribution template is missing")
        attribution = attribution_template.format(
            source_record_id=record.sentence_id,
            author=record.author,
            license_url=record.license_url,
        )
        return {
            "source_id": source["source_id"],
            "source_name": source["source_name"],
            "source_url": f"https://tatoeba.org/en/sentences/show/{record.sentence_id}",
            "source_record_id": record.sentence_id,
            "retrieved_at": options.retrieved_at.isoformat().replace("+00:00", "Z"),
            "retrieved_by": self.adapter_id,
            "license": record.license,
            "license_url": record.license_url,
            "attribution": attribution,
            "content_hash": hashlib.sha256(record.raw_line).hexdigest(),
            "ingestion_version": self.ingestion_version,
        }

    def normalize(
        self,
        record: TatoebaTextRecord,
        provenance: dict[str, Any],
    ) -> dict[str, Any]:
        identity = f"{self.source_id}\0{record.sentence_id}".encode("utf-8")
        record_id = f"text_{self.source_id}_{hashlib.sha256(identity).hexdigest()[:16]}"
        return {
            "schema_version": "1.0",
            "record_type": "normalized_text",
            "id": record_id,
            "language": record.language.lower(),
            "text": record.text,
            "ingestion_version": self.ingestion_version,
            "provenance": provenance,
        }
