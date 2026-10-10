from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from english_master.schema_validation import load_json, validation_issues


INVENTORY_PATH = Path(__file__).parents[1] / "curriculum" / "web-vocabulary" / "v1" / "en-a1-unit-01.json"


def test_web_vocabulary_inventory_is_schema_valid() -> None:
    inventory = load_json(INVENTORY_PATH)

    assert validation_issues(inventory, "web-vocabulary-inventory") == []
    assert len(inventory["records"]) == 20
    assert {record["content_status"] for record in inventory["records"]} == {"UNREVIEWED"}


def test_web_vocabulary_inventory_rejects_bad_source_target_identifier() -> None:
    inventory = deepcopy(load_json(INVENTORY_PATH))
    inventory["records"][0]["exercise_bindings"][0]["source_target_id"] = "bad-target-id"

    assert validation_issues(inventory, "web-vocabulary-inventory")
