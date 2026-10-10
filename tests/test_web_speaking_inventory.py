from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from english_master.schema_validation import load_json, validation_issues


SNAPSHOT_PATH = Path(__file__).parents[1] / "apps" / "web" / "src" / "content" / "generated" / "speaking-snapshot.json"


def test_web_speaking_inventory_is_schema_valid() -> None:
    snapshot = load_json(SNAPSHOT_PATH)

    assert validation_issues(snapshot, "web-speaking-inventory") == []
    assert len(snapshot["protocols"]) == 310
    assert {protocol["contentStatus"] for protocol in snapshot["protocols"]} == {"UNREVIEWED"}
    assert {
        value
        for protocol in snapshot["protocols"]
        for value in protocol["assessment"].values()
    } == {"NOT_ASSESSED"}


def test_web_speaking_inventory_rejects_assessment_and_source_leakage() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["protocols"][0]["assessment"]["fluency"] = "ASSESSED"
    assert validation_issues(snapshot, "web-speaking-inventory")

    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["protocols"][0]["target_ids"] = ["leaked_target"]
    assert validation_issues(snapshot, "web-speaking-inventory")
