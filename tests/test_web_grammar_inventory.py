from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from english_master.schema_validation import load_json, validation_issues


SNAPSHOT_PATH = Path(__file__).parents[1] / "apps" / "web" / "src" / "content" / "generated" / "grammar-snapshot.json"


def test_web_grammar_inventory_is_schema_valid() -> None:
    snapshot = load_json(SNAPSHOT_PATH)

    assert validation_issues(snapshot, "web-grammar-inventory") == []
    assert len(snapshot["targets"]) == 20
    assert {target["contentStatus"] for target in snapshot["targets"]} == {"UNREVIEWED"}


def test_web_grammar_inventory_rejects_source_mapping_leakage() -> None:
    snapshot = deepcopy(load_json(SNAPSHOT_PATH))
    snapshot["targets"][0]["sourceTargetId"] = "a1t_u01_personal_origin"

    assert validation_issues(snapshot, "web-grammar-inventory")
