"""Append-only M10 archival and supersession index construction."""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from english_master.lesson_generation.canonical import identity, sha256_json
from english_master.schema_validation import validate_instance

JsonObject = dict[str, Any]


def build_supersession_index(*, entries: Iterable[Mapping[str, Any]], updated_at: str) -> JsonObject:
    """Build a canonical index; each run appears once and supersession is acyclic."""
    ordered = [dict(entry) for entry in entries]
    ids = [str(entry.get("run_id")) for entry in ordered]
    if len(ids) != len(set(ids)):
        raise ValueError("M10 supersession index contains duplicate run IDs")
    by_id = {str(entry["run_id"]): entry for entry in ordered}
    for entry in ordered:
        parent = entry.get("supersedes")
        if parent is not None:
            if not isinstance(parent, Mapping) or parent.get("run_id") not in by_id:
                raise ValueError("M10 supersession target is absent from index")
            if parent.get("run_id") == entry.get("run_id"):
                raise ValueError("M10 run cannot supersede itself")
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
