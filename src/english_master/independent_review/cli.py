"""Offline M9 independent-review commands."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from english_master.curriculum_review.loading import load_strict_document

from .authority import VerifiedM9Authority
from .machine import build_machine_report
from .review import CHECKLISTS, build_ai_review, build_review_prompt
from .selection import build_selection
from .storage import publish_development_batch
from .verification import verify_development_batch


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--structure", type=Path, default=Path("curriculum/structure.json"))
    parser.add_argument("--snapshot-dir", type=Path, default=Path("data/reviews/m5/development-20260903-062008"))
    parser.add_argument("--source-registry", type=Path, default=Path("sources/registry.yaml"))
    parser.add_argument("--m6-batch", type=Path, default=Path("data/generated/m6/development-batches/20260903-v6/development-batch.json"))
    parser.add_argument("--m6-root", type=Path, default=Path("data/generated/m6/development-candidates/20260903-v6-selected"))
    parser.add_argument("--exercise-root", type=Path, default=Path("curriculum/exercises"))
    parser.add_argument("--m7-batch", type=Path, default=Path("curriculum/exercises/development-batches/20260903-v3/development-batch.json"))
    parser.add_argument("--pilot-dir", type=Path, default=Path("curriculum/ai-practice/pilot-batches/20260905-v13"))


def _authority(args: argparse.Namespace) -> VerifiedM9Authority:
    return VerifiedM9Authority.from_files(structure_path=args.structure, snapshot_directory=args.snapshot_dir, source_registry_path=args.source_registry, m6_batch_path=args.m6_batch, m6_root=args.m6_root, exercise_root=args.exercise_root, m7_batch_path=args.m7_batch, pilot_directory=args.pilot_dir)


def _emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-development", help="write a non-promotable M9 selection and fresh machine reports")
    _common(prepare); prepare.add_argument("--output-dir", type=Path, required=True); prepare.add_argument("--created-at")
    publish = commands.add_parser("publish-development", help="publish complete M9 evidence from real AI captures")
    _common(publish); publish.add_argument("--prepared-dir", type=Path, required=True); publish.add_argument("--capture-dir", type=Path, required=True); publish.add_argument("--output-dir", type=Path, required=True); publish.add_argument("--created-at", default=None)
    verify = commands.add_parser("verify-development", help="read-only verify an immutable M9 development batch")
    _common(verify); verify.add_argument("--batch-dir", type=Path, required=True)
    return parser


def _prepare(authority: VerifiedM9Authority, directory: Path, created_at: str) -> Path:
    if directory.exists():
        raise FileExistsError(f"M9 prepared directory already exists: {directory}")
    selection = build_selection(authority, created_at=created_at)
    directory.mkdir(parents=True)
    (directory / "machine").mkdir()
    (directory / "prompts").mkdir()
    (directory / "selection.json").write_text(json.dumps(selection, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    for subject in authority.subjects:
        report = build_machine_report(authority, selection, subject, reviewed_at=created_at)
        (directory / "machine" / f"{subject.subject_id}.json").write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        for role in CHECKLISTS:
            prompt_path = directory / "prompts" / f"{subject.subject_id}--{role.lower()}.txt"
            prompt_path.write_text(build_review_prompt(role, subject, report) + "\n", encoding="utf-8")
    return directory


def _publish(authority: VerifiedM9Authority, prepared: Path, captures: Path, output: Path, created_at: str) -> Path:
    selection = load_strict_document(prepared / "selection.json")
    reports = {subject.subject_id: load_strict_document(prepared / "machine" / f"{subject.subject_id}.json") for subject in authority.subjects}
    reviews: dict[tuple[str, str], dict[str, Any]] = {}
    for subject in authority.subjects:
        for role in CHECKLISTS:
            capture = load_strict_document(captures / f"{subject.subject_id}--{role.lower()}.json")
            reviews[(subject.subject_id, role)] = build_ai_review(selection=selection, subject=subject, machine_report=reports[subject.subject_id], role=role, capture=capture["capture"], raw_response=capture["raw_response"], reviewed_at=capture["reviewed_at"])
    return publish_development_batch(output, authority, selection, reports, reviews, created_at=created_at)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        authority = _authority(args)
        if args.command == "prepare-development":
            path = _prepare(authority, args.output_dir, args.created_at or _now())
            _emit({"prepared": str(path), "selected_subject_count": len(authority.subjects), "review_prompt_count": len(authority.subjects) * len(CHECKLISTS), "approval_tier": "NOT_PUBLISHED"})
            return 0
        if args.command == "publish-development":
            path = _publish(authority, args.prepared_dir, args.capture_dir, args.output_dir, args.created_at or _now())
            _emit({"output": str(path), **verify_development_batch(path, authority)})
            return 0
        _emit(verify_development_batch(args.batch_dir, authority))
        return 0
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print(f"{type(error).__name__}: {error}".encode("ascii", "backslashreplace").decode("ascii"))
        return 2
