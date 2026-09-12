"""Command line interface for the development-only Full A1 pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import audit_full_a1, build_full_a1, sample_full_a1, verify_full_a1


def _source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--population", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--allocation", required=True, type=Path)
    parser.add_argument("--content-manifest", required=True, type=Path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build, verify, audit, and sample the complete 50-lesson A1 development set.")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build an immutable 50-packet Full A1 run")
    _source_arguments(build)
    build.add_argument("--output-root", required=True, type=Path)
    build.add_argument("--built-at", required=True)
    verify = commands.add_parser("verify", help="verify a closed Full A1 run")
    verify.add_argument("run_dir", type=Path)
    _source_arguments(verify)
    audit = commands.add_parser("audit", help="write a bounded full-population consistency report")
    audit.add_argument("run_dir", type=Path)
    _source_arguments(audit)
    audit.add_argument("--output", required=True, type=Path)
    sample = commands.add_parser("sample", help="write a deterministic hash-ranked unit-stratified sample")
    sample.add_argument("run_dir", type=Path)
    _source_arguments(sample)
    sample.add_argument("--audit-report", required=True, type=Path)
    sample.add_argument("--seed", required=True)
    sample.add_argument("--size", default=12, type=int)
    sample.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    sources = {"population_path": args.population, "blueprint_path": args.blueprint, "allocation_path": args.allocation, "content_manifest_path": args.content_manifest}
    if args.command == "build":
        print(build_full_a1(**sources, output_root=args.output_root, built_at=args.built_at))
    elif args.command == "verify":
        verify_full_a1(args.run_dir, **sources)
        print("Full A1 verification passed")
    elif args.command == "audit":
        report = audit_full_a1(run_dir=args.run_dir, output_path=args.output, **sources)
        print(f"Full A1 lightweight audit: {report['result']}")
    else:
        sample_manifest = sample_full_a1(run_dir=args.run_dir, audit_report_path=args.audit_report, seed=args.seed, sample_size=args.size, output_path=args.output, **sources)
        print(f"Full A1 deterministic sample contains {len(sample_manifest['selected_lesson_ids'])} lessons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
