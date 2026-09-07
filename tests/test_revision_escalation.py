from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from english_master.revision_cycle.escalation_storage import verify_escalated_run

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "data" / "reviews" / "m10" / "runs" / "20260907-a1-u01-l01-title-conflict"


def test_current_authority_conflict_run_verifies() -> None:
    result = verify_escalated_run(RUN)
    assert result["terminal_state"] == "ESCALATED"
    assert result["attempt_count"] == 0


def test_escalation_run_rejects_tampered_authority_record(tmp_path: Path) -> None:
    copied = tmp_path / "run"
    shutil.copytree(RUN, copied)
    path = copied / "authority-record.json"
    path.write_text(path.read_text(encoding="utf-8").replace("Foundational exchange", "Tampered title"), encoding="utf-8")
    with pytest.raises(ValueError, match="title"):
        verify_escalated_run(copied)


def test_escalation_run_rejects_extra_file(tmp_path: Path) -> None:
    copied = tmp_path / "run"
    shutil.copytree(RUN, copied)
    (copied / "unexpected.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="inventory"):
        verify_escalated_run(copied)
