from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from english_master.schema_validation import load_json, validation_issues


SNAPSHOT_PATH = Path(__file__).parents[1] / "apps" / "web" / "src" / "content" / "generated" / "listening-snapshot.json"


def test_web_listening_inventory_accepts_the_no_authorized_media_sentinel() -> None:
    snapshot = load_json(SNAPSHOT_PATH)

    assert validation_issues(snapshot, "web-listening-inventory") == []
    assert snapshot["availability"] == "NO_AUTHORIZED_MEDIA"
    assert snapshot["sessions"] == []


def test_web_listening_inventory_rejects_sessions_in_the_no_media_state() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["sessions"] = [{"id": "unpermitted"}]

    assert validation_issues(snapshot, "web-listening-inventory")


def test_web_listening_inventory_rejects_authority_leakage() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["sourceUrl"] = "https://example.invalid/asset"

    assert validation_issues(snapshot, "web-listening-inventory")
