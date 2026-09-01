"""Hash-based exact duplicate grouping with retained provenance."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from english_master.normalization.hashes import canonical_json_bytes, sha256_bytes
from english_master.normalization.models import DeduplicationReason, ProcessedRecord


class ExactDeduplicationError(ValueError):
    """Raised for inconsistent identity/hash metadata."""


def _group_document(
    reason: DeduplicationReason,
    digest: str,
    members: list[ProcessedRecord],
    policy_version: str,
) -> dict[str, object]:
    ordered = sorted(members, key=lambda record: (record.id, record.document["original_raw_location"]))
    member_ids = [record.id for record in ordered]
    group_material = {"reason": reason.value, "hash": digest, "member_ids": member_ids}
    group_id = f"dup_{sha256_bytes(canonical_json_bytes(group_material))[:20]}"
    canonical_record_id = member_ids[0]
    return {
        "schema_version": "1.0",
        "record_type": "duplicate_group",
        "id": group_id,
        "canonical_record_id": canonical_record_id,
        "member_record_ids": member_ids,
        "source_ids": sorted({str(record.document["source_id"]) for record in ordered}),
        "source_record_ids": sorted({record.source_record_id for record in ordered}),
        "raw_hashes": sorted({record.raw_hash for record in ordered}),
        "normalized_hashes": sorted({record.normalized_hash for record in ordered}),
        "member_locations": [
            {
                "record_id": record.id,
                "location": str(record.document["original_raw_location"]),
                "first_seen": index == 0,
            }
            for index, record in enumerate(ordered)
        ],
        "deduplication_reason": reason.value,
        "deduplication_policy_version": policy_version,
        "disposition": "DUPLICATE",
    }


def build_exact_groups(
    records: Iterable[ProcessedRecord], policy_version: str = "hash-exact-v1"
) -> tuple[dict[str, object], ...]:
    """Return deterministic raw and normalized duplicate groups.

    A stable M3 record identity with different raw content is rejected rather
    than interpreted as a hash collision or silently replaced.
    """

    ordered = sorted(records, key=lambda record: (record.source_record_id, record.id))
    identity_hashes: dict[tuple[str, str], str] = {}
    raw_index: dict[str, list[ProcessedRecord]] = defaultdict(list)
    normalized_index: dict[str, list[ProcessedRecord]] = defaultdict(list)
    for record in ordered:
        identity = (str(record.document["source_id"]), record.source_record_id)
        existing = identity_hashes.setdefault(identity, record.raw_hash)
        if existing != record.raw_hash:
            raise ExactDeduplicationError(
                f"Inconsistent raw content for source identity {identity[0]!r}/{identity[1]!r}"
            )
        raw_index[record.raw_hash].append(record)
        normalized_index[record.normalized_hash].append(record)

    groups: list[dict[str, object]] = []
    raw_member_sets: set[frozenset[str]] = set()
    for digest, members in sorted(raw_index.items()):
        if len(members) > 1:
            groups.append(_group_document(DeduplicationReason.RAW_HASH, digest, members, policy_version))
            raw_member_sets.add(frozenset(member.id for member in members))
    for digest, members in sorted(normalized_index.items()):
        member_set = frozenset(member.id for member in members)
        if len(members) > 1 and member_set not in raw_member_sets:
            groups.append(
                _group_document(DeduplicationReason.NORMALIZED_HASH, digest, members, policy_version)
            )
    return tuple(sorted(groups, key=lambda group: str(group["id"])))
