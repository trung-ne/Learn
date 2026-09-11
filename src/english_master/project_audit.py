"""Lightweight offline audit for active project documentation and repository facts.

This audit deliberately checks only concrete drift between active documentation,
local commands, and a small set of declared repository facts.  It does not
assess generated learning content or establish any approval status.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from english_master.schema_validation import load_document, repository_root


@dataclass(frozen=True)
class AuditIssue:
    """One actionable consistency problem."""

    path: str
    message: str


_ACTIVE_DOCUMENTS = {
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

_REQUIRED_PATHS = (
    "src/english_master/project_audit.py",
    "src/english_master/schema_validation.py",
    "docs/DEVELOPMENT_WORKFLOW.md",
    "curriculum/ai-practice/pilot-batches/20260911-v14-m10/batch-manifest.json",
)


def _issue_for_missing_path(root: Path, relative_path: str) -> AuditIssue | None:
    if not (root / relative_path).is_file():
        return AuditIssue(relative_path, "Required active-workflow path is missing.")
    return None


def _document_issues(root: Path) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for relative_path, required_text in sorted(_ACTIVE_DOCUMENTS.items()):
        path = root / relative_path
        if not path.is_file():
            issues.append(AuditIssue(relative_path, "Active workflow document is missing."))
            continue
        text = path.read_text(encoding="utf-8")
        if required_text not in text:
            issues.append(
                AuditIssue(
                    relative_path,
                    f"Active workflow marker is missing: {required_text!r}.",
                )
            )
    return issues


def _pilot_issues(root: Path) -> list[AuditIssue]:
    relative_path = "curriculum/ai-practice/pilot-batches/20260911-v14-m10/batch-manifest.json"
    path = root / relative_path
    if not path.is_file():
        return []
    try:
        manifest = load_document(path)
    except (OSError, ValueError) as error:
        return [AuditIssue(relative_path, f"Cannot load declared pilot manifest: {error}")]
    members = manifest.get("members")
    if not isinstance(members, list) or len(members) != 40:
        return [AuditIssue(relative_path, "Declared M8.2 pilot must contain exactly 40 members.")]
    return []


def audit_repository(root: Path | None = None) -> tuple[AuditIssue, ...]:
    """Return ordered active-workflow drift issues for a repository checkout."""

    audit_root = (root or repository_root()).resolve()
    issues = [
        issue
        for relative_path in _REQUIRED_PATHS
        if (issue := _issue_for_missing_path(audit_root, relative_path)) is not None
    ]
    issues.extend(_document_issues(audit_root))
    issues.extend(_pilot_issues(audit_root))
    return tuple(sorted(issues, key=lambda issue: (issue.path, issue.message)))


def build_report(root: Path | None = None) -> dict[str, Any]:
    """Build a stable machine-readable report without writing repository state."""

    issues = audit_repository(root)
    return {
        "audit": "project-consistency",
        "status": "PASS" if not issues else "FAIL",
        "checks": [
            "active workflow documents reference the local audit command",
            "active workflow paths exist",
            "declared M8.2 pilot inventory remains closed",
        ],
        "issues": [
            {"path": issue.path, "message": issue.message}
            for issue in issues
        ],
        "limitations": [
            "This audit checks repository consistency only.",
            "It does not establish content quality, approval, release, or runtime behavior.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check active documentation and local repository facts for drift."
    )
    parser.add_argument(
        "--repository-root",
        type=Path,
        default=repository_root(),
        help="Repository checkout to audit (default: this source checkout).",
    )
    arguments = parser.parse_args(argv)
    report = build_report(arguments.repository_root)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
