"""Command line interface for the development-only Full C2 pipeline."""
from __future__ import annotations
import argparse
from pathlib import Path
from .service import audit_full_c2, build_full_c2, sample_full_c2, verify_full_c2

def _source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--population", required=True, type=Path)
    parser.add_argument("--blueprint", required=True, type=Path)
    parser.add_argument("--allocation", required=True, type=Path)
    parser.add_argument("--content-manifest", required=True, type=Path)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build, verify, audit, and sample the complete 50-lesson C2 development set.")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("build", "verify", "audit", "sample"):
        sub = commands.add_parser(command)
        if command != "build": sub.add_argument("run_dir", type=Path)
        _source_arguments(sub)
        if command == "build": sub.add_argument("--output-root", required=True, type=Path); sub.add_argument("--built-at", required=True)
        if command == "audit": sub.add_argument("--output", required=True, type=Path)
        if command == "sample": sub.add_argument("--audit-report", required=True, type=Path); sub.add_argument("--seed", required=True); sub.add_argument("--size", default=12, type=int); sub.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    sources = {"population_path": args.population, "blueprint_path": args.blueprint, "allocation_path": args.allocation, "content_manifest_path": args.content_manifest}
    if args.command == "build": print(build_full_c2(**sources, output_root=args.output_root, built_at=args.built_at))
    elif args.command == "verify": verify_full_c2(args.run_dir, **sources); print("Full C2 verification passed")
    elif args.command == "audit": print(f"Full C2 lightweight audit: {audit_full_c2(run_dir=args.run_dir, output_path=args.output, **sources)['result']}")
    else: print(f"Full C2 deterministic sample contains {len(sample_full_c2(run_dir=args.run_dir, audit_report_path=args.audit_report, seed=args.seed, sample_size=args.size, output_path=args.output, **sources)['selected_lesson_ids'])} lessons")
    return 0
if __name__ == "__main__": raise SystemExit(main())
