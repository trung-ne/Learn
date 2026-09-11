from __future__ import annotations

import json
from pathlib import Path

from english_master.project_audit import audit_repository, build_report, main


_ACTIVE_DOCUMENT_MARKERS = {
    "PROJECT_RULES.md": "Routine development validation is intentionally lightweight.",
    "README.md": "python -m english_master.project_audit",
    "docs/DEVELOPMENT_WORKFLOW.md": "Routine work uses a small local consistency check",
    "docs/MILESTONES.md": "**Status**: Active free QA workflow.",
    "docs/PROJECT_STATUS.md": "Routine development dùng **lightweight consistency audit**",
    "docs/PROJECT_SPEC.md": "## Current Active Development Workflow",
    "docs/QA_SPEC.md": "## Active Lightweight Workflow",
    "docs/M9_INDEPENDENT_REVIEW.md": "M9 is the active free development check.",
    "docs/M10_REVISION_CYCLE.md": "M10 is a small revision loop:",
    "docs/M11.md": "Build one explicitly declared local batch",
    "docs/EXPORT_PACKAGING.md": "The active export path accepts one hash-bound local batch",
    "prompts/M12_MEDIA_INGESTION.md": "`english_master.m12_local_pilot` validates a manifest",
    "docs/M13_TRANSCRIPTION.md": "`english_master.m13_local_pilot`",
    "docs/M14_LISTENING_DIFFICULTY.md": "`english_master.listening_difficulty.local_metrics`",
}


def _write_checkout(root: Path) -> None:
    for relative_path, marker in _ACTIVE_DOCUMENT_MARKERS.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(marker, encoding="utf-8")
    for relative_path in (
        "src/english_master/project_audit.py",
        "src/english_master/schema_validation.py",
    ):
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n", encoding="utf-8")
    manifest = root / "curriculum/ai-practice/pilot-batches/20260911-v14-m10/batch-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"members": [{} for _ in range(40)]}), encoding="utf-8")


def test_audit_passes_for_consistent_fixture(tmp_path: Path) -> None:
    _write_checkout(tmp_path)

    assert audit_repository(tmp_path) == ()
    assert build_report(tmp_path)["status"] == "PASS"


def test_audit_reports_missing_workflow_marker(tmp_path: Path) -> None:
    _write_checkout(tmp_path)
    (tmp_path / "README.md").write_text("No command here.\n", encoding="utf-8")

    report = build_report(tmp_path)

    assert report["status"] == "FAIL"
    assert report["issues"] == [
        {
            "path": "README.md",
            "message": "Active workflow marker is missing: 'python -m english_master.project_audit'.",
        }
    ]


def test_audit_rejects_obsolete_historical_only_m9_marker(tmp_path: Path) -> None:
    _write_checkout(tmp_path)
    path = tmp_path / "docs/M9_INDEPENDENT_REVIEW.md"
    path.write_text("It is not an active future gate.", encoding="utf-8")

    report = build_report(tmp_path)

    assert report["issues"] == [
        {
            "path": "docs/M9_INDEPENDENT_REVIEW.md",
            "message": "Active workflow marker is missing: 'M9 is the active free development check.'.",
        }
    ]


def test_audit_reports_drifted_pilot_inventory(tmp_path: Path) -> None:
    _write_checkout(tmp_path)
    manifest = tmp_path / "curriculum/ai-practice/pilot-batches/20260911-v14-m10/batch-manifest.json"
    manifest.write_text(json.dumps({"members": []}), encoding="utf-8")

    issues = audit_repository(tmp_path)

    assert [(issue.path, issue.message) for issue in issues] == [
        (
            "curriculum/ai-practice/pilot-batches/20260911-v14-m10/batch-manifest.json",
            "Declared M8.2 pilot must contain exactly 40 members.",
        )
    ]


def test_cli_returns_nonzero_for_audit_failure(tmp_path: Path, capsys) -> None:
    _write_checkout(tmp_path)
    (tmp_path / "docs/PROJECT_STATUS.md").unlink()

    assert main(["--repository-root", str(tmp_path)]) == 1
    assert '"status": "FAIL"' in capsys.readouterr().out
