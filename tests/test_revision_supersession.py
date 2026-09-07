from __future__ import annotations

import pytest

from english_master.revision_cycle.supersession import (
    build_supersession_index,
    validate_supersession_index,
)


def _entry(run: str, state: str = "ACTIVE", supersedes: dict[str, str] | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "run_id": run,
        "manifest_sha256": "a" * 64,
        "state": state,
        "recorded_at": "2026-09-05T10:00:00Z",
    }
    if supersedes is not None:
        value["supersedes"] = supersedes
    return value


def test_supersession_index_is_canonical_and_append_only() -> None:
    first = _entry("m10run_" + "1" * 64)
    second = _entry(
        "m10run_" + "2" * 64,
        supersedes={"run_id": first["run_id"], "manifest_sha256": "a" * 64, "reason": "New failed M9 evidence."},
    )
    index = build_supersession_index(entries=[second, first], updated_at="2026-09-05T11:00:00Z")
    assert not validate_supersession_index(index)
    assert [entry["run_id"] for entry in index["entries"]] == [first["run_id"], second["run_id"]]


def test_supersession_index_rejects_cycles() -> None:
    first = _entry("m10run_" + "1" * 64, supersedes={"run_id": "m10run_" + "2" * 64, "manifest_sha256": "a" * 64, "reason": "bad"})
    second = _entry("m10run_" + "2" * 64, supersedes={"run_id": "m10run_" + "1" * 64, "manifest_sha256": "a" * 64, "reason": "bad"})
    with pytest.raises(ValueError, match="cycle"):
        build_supersession_index(entries=[first, second], updated_at="2026-09-05T11:00:00Z")
