from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from english_master.schema_validation import load_json, validation_issues


SNAPSHOT_PATH = Path(__file__).parents[1] / "apps" / "web" / "src" / "content" / "generated" / "pronunciation-snapshot.json"


def test_web_pronunciation_inventory_is_schema_valid() -> None:
    snapshot = load_json(SNAPSHOT_PATH)

    assert validation_issues(snapshot, "web-pronunciation-inventory") == []
    assert len(snapshot["protocols"]) == 310
    assert {protocol["assessmentAvailability"] for protocol in snapshot["protocols"]} == {"NOT_ASSESSED"}
    assert {protocol["contentStatus"] for protocol in snapshot["protocols"]} == {"UNREVIEWED"}


def test_web_pronunciation_inventory_rejects_assessment_and_source_leakage() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["protocols"][0]["assessmentAvailability"] = "ASSESSED"
    assert validation_issues(snapshot, "web-pronunciation-inventory")

    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["protocols"][0]["packet_sha256"] = "0" * 64
    assert validation_issues(snapshot, "web-pronunciation-inventory")
