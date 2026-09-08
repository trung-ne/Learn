from __future__ import annotations

from pathlib import Path

import pytest

from english_master.revision_cycle.escalation_storage import verify_escalated_run
from english_master.schema_validation import SchemaValidationError, load_schema

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data" / "reviews" / "m10" / "runs" / "20260907-a1-u01-l01-title-conflict"


def test_historical_authority_conflict_run_is_not_active_m10_authority() -> None:
    with pytest.raises(
        SchemaValidationError,
        match="Additional properties are not allowed.*human_reviewed.*release_approved",
    ):
        verify_escalated_run(RUN)


def test_active_escalation_contract_omits_human_reviewed() -> None:
    schema = load_schema("m10-escalation")
    assert "human_reviewed" not in schema["required"]
    assert "human_reviewed" not in schema["properties"]


def test_active_escalation_contract_omits_release_approved() -> None:
    schema = load_schema("m10-escalation")
    assert "release_approved" not in schema["required"]
    assert "release_approved" not in schema["properties"]
