from __future__ import annotations

import pytest

from english_master.revision_cycle.supersession import (
    build_supersession_index,
    validate_supersession_index,
)


def _entry(
    run: str,
    *,
    manifest_sha256: str = "a" * 64,
    state: str = "ACTIVE",
    supersedes: dict[str, str] | None = None,
    closure: dict[str, str] | None = None,
) -> dict[str, object]:
    value: dict[str, object] = {
        "run_id": run,
        "manifest_sha256": manifest_sha256,
        "state": state,
        "recorded_at": "2026-09-05T10:00:00Z",
    }
    if supersedes is not None:
        value["supersedes"] = supersedes
    if closure is not None:
        value["m9_closure"] = closure
    return value


def _parent(run_id: str, manifest_sha256: str) -> dict[str, str]:
    return {"run_id": run_id, "manifest_sha256": manifest_sha256, "reason": "Fresh immutable successor."}


def _closure() -> dict[str, str]:
    return {"path": "data/reviews/m9/fresh/development-batch.json", "sha256": "f" * 64}


def test_supersession_index_accepts_canonical_closed_linear_lineage() -> None:
    first = _entry("m10run_" + "1" * 64, manifest_sha256="a" * 64, state="SUPERSEDED")
    second = _entry(
        "m10run_" + "2" * 64,
        manifest_sha256="b" * 64,
        state="CLOSED_AFTER_FRESH_M9",
        supersedes=_parent(str(first["run_id"]), str(first["manifest_sha256"])),
        closure=_closure(),
    )
    index = build_supersession_index(entries=[second, first], updated_at="2026-09-05T11:00:00Z")
    assert not validate_supersession_index(index)
    assert [entry["run_id"] for entry in index["entries"]] == [first["run_id"], second["run_id"]]


def test_supersession_index_rejects_parent_manifest_hash_drift() -> None:
    first = _entry("m10run_" + "1" * 64, state="SUPERSEDED")
    second = _entry(
        "m10run_" + "2" * 64,
        state="CLOSED_AFTER_FRESH_M9",
        supersedes=_parent(str(first["run_id"]), "b" * 64),
        closure=_closure(),
    )
    with pytest.raises(ValueError, match="manifest hash mismatch"):
        build_supersession_index(entries=[first, second], updated_at="2026-09-05T11:00:00Z")


def test_supersession_index_rejects_forks() -> None:
    first = _entry("m10run_" + "1" * 64, state="SUPERSEDED")
    children = [
        _entry(
            "m10run_" + digit * 64,
            state="CLOSED_AFTER_FRESH_M9",
            supersedes=_parent(str(first["run_id"]), str(first["manifest_sha256"])),
            closure=_closure(),
        )
        for digit in ("2", "3")
    ]
    with pytest.raises(ValueError, match="fork"):
        build_supersession_index(entries=[first, *children], updated_at="2026-09-05T11:00:00Z")


def test_supersession_index_rejects_cycles() -> None:
    ids = ["m10run_" + digit * 64 for digit in ("1", "2", "3")]
    hashes = [digit * 64 for digit in ("a", "b", "c")]
    entries = [
        _entry(ids[0], manifest_sha256=hashes[0], state="SUPERSEDED", supersedes=_parent(ids[2], hashes[2])),
        _entry(ids[1], manifest_sha256=hashes[1], state="SUPERSEDED", supersedes=_parent(ids[0], hashes[0])),
        _entry(ids[2], manifest_sha256=hashes[2], state="SUPERSEDED", supersedes=_parent(ids[1], hashes[1])),
    ]
    with pytest.raises(ValueError, match="cycle"):
        build_supersession_index(entries=entries, updated_at="2026-09-05T11:00:00Z")


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (_entry("m10run_" + "1" * 64, state="CLOSED_AFTER_FRESH_M9"), "requires M9 closure"),
        (_entry("m10run_" + "1" * 64, closure=_closure()), "only CLOSED_AFTER_FRESH_M9"),
        (_entry("m10run_" + "1" * 64, state="SUPERSEDED"), "has no successor"),
    ],
)
def test_supersession_index_rejects_inconsistent_states(entry: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        build_supersession_index(entries=[entry], updated_at="2026-09-05T11:00:00Z")


def test_supersession_index_rejects_parent_not_marked_superseded() -> None:
    first = _entry("m10run_" + "1" * 64)
    second = _entry(
        "m10run_" + "2" * 64,
        state="CLOSED_AFTER_FRESH_M9",
        supersedes=_parent(str(first["run_id"]), str(first["manifest_sha256"])),
        closure=_closure(),
    )
    with pytest.raises(ValueError, match="not marked SUPERSEDED"):
        build_supersession_index(entries=[first, second], updated_at="2026-09-05T11:00:00Z")
