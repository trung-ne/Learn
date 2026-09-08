from __future__ import annotations

import json
from pathlib import Path

from english_master.independent_review.authority import VerifiedM9Authority
from english_master.independent_review.machine import build_machine_report
from english_master.independent_review.review import CHECKLISTS
from english_master.independent_review.selection import build_selection
from english_master.revision_cycle.cli import import_findings
from english_master.revision_cycle.verification import verify_finding_batch

ROOT = Path(__file__).resolve().parents[1]


def _authority() -> VerifiedM9Authority:
    return VerifiedM9Authority.from_files(
        structure_path=ROOT / "curriculum" / "structure.json",
        snapshot_directory=ROOT / "data" / "reviews" / "m5" / "development-20260903-062008",
        source_registry_path=ROOT / "sources" / "registry.yaml",
        m6_batch_path=ROOT / "data" / "generated" / "m6" / "development-batches" / "20260903-v6" / "development-batch.json",
        m6_root=ROOT / "data" / "generated" / "m6" / "development-candidates" / "20260903-v6-selected",
        exercise_root=ROOT / "curriculum" / "exercises",
        m7_batch_path=ROOT / "curriculum" / "exercises" / "development-batches" / "20260903-v3" / "development-batch.json",
        pilot_directory=ROOT / "curriculum" / "ai-practice" / "pilot-batches" / "20260905-v13",
    )


def test_import_findings_requires_complete_capture_inventory_and_publishes_nonapproval_inputs(tmp_path: Path) -> None:
    authority = _authority()
    prepared = tmp_path / "prepared"
    captures = tmp_path / "captures"
    (prepared / "machine").mkdir(parents=True)
    captures.mkdir()
    selection = build_selection(authority, created_at="2026-09-08T08:36:00Z")
    (prepared / "selection.json").write_text(json.dumps(selection), encoding="utf-8")
    for index, subject in enumerate(authority.subjects):
        report = build_machine_report(authority, selection, subject, reviewed_at="2026-09-08T08:36:00Z")
        (prepared / "machine" / f"{subject.subject_id}.json").write_text(json.dumps(report), encoding="utf-8")
        for role, criteria in CHECKLISTS.items():
            failed = index == 0 and role == "LINGUISTIC_AI_REVIEWER"
            raw_response = {
                "decision": "NEEDS_REVISION" if failed else "APPROVE",
                "checklist": [
                    {"criterion": criterion, "result": "FAIL" if failed and criterion == criteria[0] else "PASS", "notes": "Fixture review."}
                    for criterion in criteria
                ],
                "findings": ([{"severity": "MAJOR", "category": "FIXTURE", "description": "Repair fixture defect.", "recommendation": "Repair it."}] if failed else []),
                "limitations": ["Fixture capture only."],
            }
            capture = {
                "capture": {
                    "capture_mode": "SESSION_CAPTURED",
                    "provider": "UNKNOWN",
                    "model": "UNKNOWN",
                    "execution_id": f"fixture-{index}-{role}",
                    "provider_authenticated": False,
                    "observed_at": "2026-09-08T08:37:00Z",
                },
                "raw_response": raw_response,
                "reviewed_at": "2026-09-08T08:38:00Z",
            }
            (captures / f"{subject.subject_id}--{role.lower()}.json").write_text(json.dumps(capture), encoding="utf-8")
    output = import_findings(
        authority=authority,
        prepared_directory=prepared,
        capture_directory=captures,
        output_directory=tmp_path / "m10-findings",
        imported_at="2026-09-08T08:39:00Z",
    )
    result = verify_finding_batch(output, selection=selection, subjects={subject.subject_id: subject for subject in authority.subjects})
    assert len(result["review_inputs"]) == 1
    assert result["promotion_status"] == "NON_PROMOTABLE"
