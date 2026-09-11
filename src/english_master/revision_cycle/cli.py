"""Offline M10 intake and planning commands."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from english_master.curriculum_review.loading import load_strict_document
from english_master.independent_review.authority import VerifiedM9Authority
from english_master.independent_review.review import CHECKLISTS

from .evidence import build_review_input
from .execution import execute_supplied_successor
from .planning import build_revision_requests
from .storage import publish_finding_batch
from .verification import verify_finding_batch


def _emit(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False))


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
    return VerifiedM9Authority.from_files(
        structure_path=args.structure,
        snapshot_directory=args.snapshot_dir,
        source_registry_path=args.source_registry,
        m6_batch_path=args.m6_batch,
        m6_root=args.m6_root,
        exercise_root=args.exercise_root,
        m7_batch_path=args.m7_batch,
        pilot_directory=args.pilot_dir,
    )


def _capture_path(directory: Path, subject_id: str, role: str) -> Path:
    return directory / f"{subject_id}--{role.lower()}.json"


def import_findings(
    *,
    authority: VerifiedM9Authority,
    prepared_directory: Path,
    capture_directory: Path,
    output_directory: Path,
    imported_at: str,
) -> Path:
    """Import every failed, factual M9 capture as immutable M10 input evidence.

    The command requires a complete capture inventory so omission cannot conceal a
    failed role review. Approval captures are inspected for a decision only and are
    deliberately excluded from the non-promotable finding batch.
    """
    selection = load_strict_document(prepared_directory / "selection.json")
    reports: dict[str, Mapping[str, Any]] = {
        subject.subject_id: load_strict_document(prepared_directory / "machine" / f"{subject.subject_id}.json")
        for subject in authority.subjects
    }
    inputs: dict[str, Mapping[str, Any]] = {}
    for subject in authority.subjects:
        for role in CHECKLISTS:
            capture_path = _capture_path(capture_directory, subject.subject_id, role)
            capture_document = load_strict_document(capture_path)
            capture = capture_document.get("capture")
            raw_response = capture_document.get("raw_response")
            reviewed_at = capture_document.get("reviewed_at")
            if not isinstance(capture, Mapping) or not isinstance(raw_response, Mapping) or not isinstance(reviewed_at, str):
                raise ValueError(f"invalid M9 capture wrapper: {capture_path}")
            decision = raw_response.get("decision")
            if decision == "APPROVE":
                continue
            value = build_review_input(
                selection=selection,
                subject=subject,
                machine_report=reports[subject.subject_id],
                role=role,
                capture=capture,
                raw_response=raw_response,
                observed_at=str(capture.get("observed_at")),
                imported_at=imported_at,
            )
            if reviewed_at < str(capture.get("observed_at")):
                raise ValueError(f"M9 review timestamp precedes capture: {capture_path}")
            inputs[str(value["input_id"])] = value
    if not inputs:
        raise ValueError("M10 import requires at least one non-approval M9 capture")
    return publish_finding_batch(
        output_directory,
        selection=selection,
        subjects={subject.subject_id: subject for subject in authority.subjects},
        machine_reports=reports,
        inputs=inputs,
        imported_at=imported_at,
    )


def plan_findings(*, authority: VerifiedM9Authority, finding_batch_directory: Path) -> tuple[dict[str, Any], ...]:
    """Read and validate immutable M10 inputs, then derive planning-only requests."""
    selection = load_strict_document(finding_batch_directory / "selection.json")
    if not isinstance(selection, dict):
        raise ValueError("M10 finding batch selection must be an object")
    subjects = {subject.subject_id: subject for subject in authority.subjects}
    batch = verify_finding_batch(finding_batch_directory, selection=selection, subjects=subjects)
    inputs: dict[str, Mapping[str, Any]] = {}
    for reference in batch["review_inputs"]:
        value = load_strict_document(finding_batch_directory / str(reference["path"]))
        if not isinstance(value, Mapping):
            raise ValueError("M10 review input must be an object")
        inputs[str(value["input_id"])] = value
    return build_revision_requests(review_inputs=inputs, subjects=subjects)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    intake = commands.add_parser("import-findings", help="import a complete M9 capture inventory as non-promotable M10 evidence")
    _common(intake)
    intake.add_argument("--prepared-dir", type=Path, required=True)
    intake.add_argument("--capture-dir", type=Path, required=True)
    intake.add_argument("--output-dir", type=Path, required=True)
    intake.add_argument("--imported-at", required=True)
    planning = commands.add_parser("plan-findings", help="derive read-only M10 revision requests from an immutable finding batch")
    _common(planning)
    planning.add_argument("--finding-batch-dir", type=Path, required=True)
    execution = commands.add_parser("execute-successor", help="freeze and validate one externally captured M10 successor")
    execution.add_argument("--finding-batch", type=Path, required=True)
    execution.add_argument("--revision-request", type=Path, required=True)
    execution.add_argument("--prompt", type=Path, required=True)
    execution.add_argument("--capture", type=Path, help="closed factual capture metadata; omit to record CAPTURE_NOT_CONFIGURED")
    execution.add_argument("--successor", type=Path, help="externally supplied successor response; required with --capture")
    execution.add_argument("--repository-root", type=Path, default=Path("."), help="root that safely contains immutable successor evidence")
    execution.add_argument("--output-dir", type=Path, required=True)
    execution.add_argument("--maximum-attempts", type=int, default=1)
    execution.add_argument("--policy-version", default="m10-successor-execution-v1")
    execution.add_argument("--created-at", required=True)
    execution.add_argument("--reviewed-at", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "execute-successor":
            finding_batch = load_strict_document(args.finding_batch)
            request = load_strict_document(args.revision_request)
            if not isinstance(finding_batch, Mapping) or not isinstance(request, Mapping):
                raise ValueError("M10 finding batch and revision request must be objects")
            if (args.capture is None) != (args.successor is None):
                raise ValueError("M10 --capture and --successor must be supplied together")
            capture = load_strict_document(args.capture) if args.capture is not None else None
            successor = load_strict_document(args.successor) if args.successor is not None else None
            if capture is not None and not isinstance(capture, Mapping):
                raise ValueError("M10 supplied capture must be an object")
            if successor is not None and not isinstance(successor, Mapping):
                raise ValueError("M10 supplied successor must be an object")
            result = execute_supplied_successor(
                finding_batch=finding_batch,
                request=request,
                prompt=args.prompt.read_text(encoding="utf-8"),
                successor=successor,
                capture_facts=capture,
                output_directory=args.output_dir,
                maximum_attempts=args.maximum_attempts,
                policy_version=args.policy_version,
                created_at=args.created_at,
                reviewed_at=args.reviewed_at,
                repository_root=args.repository_root,
            )
            _emit(result)
            return 0
        authority = _authority(args)
        if args.command == "import-findings":
            directory = import_findings(
                authority=authority,
                prepared_directory=args.prepared_dir,
                capture_directory=args.capture_dir,
                output_directory=args.output_dir,
                imported_at=args.imported_at,
            )
            result = verify_finding_batch(
                directory,
                selection=load_strict_document(args.prepared_dir / "selection.json"),
                subjects={subject.subject_id: subject for subject in authority.subjects},
            )
            _emit({"output": str(directory), **result})
            return 0
        if args.command == "plan-findings":
            requests = plan_findings(authority=authority, finding_batch_directory=args.finding_batch_dir)
            _emit({
                "finding_batch": str(args.finding_batch_dir),
                "request_count": len(requests),
                "requests": requests,
                "planning_only": True,
                "successor_created": False,
            })
            return 0
        raise AssertionError("unreachable")
    except (KeyError, OSError, TypeError, ValueError, yaml.YAMLError) as error:
        print(f"{type(error).__name__}: {error}".encode("ascii", "backslashreplace").decode("ascii"))
        return 2
