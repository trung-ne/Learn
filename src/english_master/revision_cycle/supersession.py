"""Append-only M10 archival and supersession index construction."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]


def build_supersession_index(*, entries: Iterable[Mapping[str, Any]], updated_at: str) -> JsonObject:
    """Build a canonical, fork-free index with explicit terminal closure."""
    ordered = [dict(entry) for entry in entries]
    ids = [str(entry.get("run_id")) for entry in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("M10 supersession index contains duplicate run IDs")
    by_id = {str(entry["run_id"]): entry for entry in ordered}
    child_by_parent: dict[str, str] = {}
    for entry in ordered:
        state = entry.get("state")
        closure = entry.get("m9_closure")
        if state == "CLOSED_AFTER_FRESH_M9" and closure is None:
            raise ValueError("CLOSED_AFTER_FRESH_M9 entry requires M9 closure evidence")
        if state != "CLOSED_AFTER_FRESH_M9" and closure is not None:
            raise ValueError("only CLOSED_AFTER_FRESH_M9 entries may contain M9 closure evidence")
        parent = entry.get("supersedes")
        if parent is not None:
            if not isinstance(parent, Mapping) or parent.get("run_id") not in by_id:
                raise ValueError("M10 supersession target is absent from index")
            parent_id = str(parent["run_id"])
            if parent_id == entry.get("run_id"):
                raise ValueError("M10 run cannot supersede itself")
            if parent.get("manifest_sha256") != by_id[parent_id].get("manifest_sha256"):
                raise ValueError("M10 supersession target manifest hash mismatch")
            if parent_id in child_by_parent:
                raise ValueError("M10 supersession fork")
            child_by_parent[parent_id] = str(entry["run_id"])
    for parent_id, child_id in child_by_parent.items():
        if by_id[parent_id].get("state") != "SUPERSEDED":
            raise ValueError(f"M10 superseded parent {parent_id} is not marked SUPERSEDED")
        if by_id[child_id].get("state") == "SUPERSEDED" and child_id not in child_by_parent:
            raise ValueError(f"M10 SUPERSEDED entry {child_id} has no successor")
    for entry in ordered:
        run_id = str(entry["run_id"])
        if entry.get("state") == "SUPERSEDED" and run_id not in child_by_parent:
            raise ValueError(f"M10 SUPERSEDED entry {run_id} has no successor")
        if entry.get("state") == "CLOSED_AFTER_FRESH_M9" and run_id in child_by_parent:
            raise ValueError("closed M10 entry cannot be superseded")
    for start in ids:
        seen: set[str] = set()
        current = start
        while current in by_id:
            if current in seen:
                raise ValueError("M10 supersession cycle")
            seen.add(current)
            parent = by_id[current].get("supersedes")
            current = str(parent["run_id"]) if isinstance(parent, Mapping) else ""
    value: JsonObject = {"schema_version": "1.0", "record_type": "m10_supersession_index", "index_id": "PENDING", "entries": sorted(ordered, key=lambda entry: str(entry["run_id"])), "updated_at": updated_at}
    value["index_id"] = identity("m10index", value, "index_id")
    validate_instance(value, "m10-supersession-index")
    return value


def validate_supersession_index(value: Mapping[str, Any]) -> tuple[str, ...]:
    try:
        rebuilt = build_supersession_index(entries=value.get("entries", []), updated_at=str(value.get("updated_at", "")))
    except (TypeError, ValueError) as error:
        return (str(error),)
    if dict(value) != rebuilt:
        return ("M10 supersession index does not reconstruct canonically",)
    return ()
