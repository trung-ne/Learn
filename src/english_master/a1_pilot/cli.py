"""Command line interface for the development-only A1 pilot."""

from __future__ import annotations

import argparse
from pathlib import Path

from .service import build_pilot, build_review_template, summarize_review, verify_pilot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build, verify, and review the bounded A1 pilot.")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="build an immutable ten-lesson A1.1 pilot")
    build.add_argument("--population", required=True, type=Path)
    build.add_argument("--blueprint", required=True, type=Path)
    build.add_argument("--content", required=True, type=Path)
    build.add_argument("--output-root", required=True, type=Path)
    build.add_argument("--built-at", required=True)

    verify = commands.add_parser("verify", help="verify a closed A1 pilot")
    verify.add_argument("pilot_dir", type=Path)
    verify.add_argument("--population", required=True, type=Path)
    verify.add_argument("--blueprint", required=True, type=Path)

    template = commands.add_parser("review-template", help="write an incomplete review template for a verified pilot")
    template.add_argument("pilot_dir", type=Path)
    template.add_argument("--population", required=True, type=Path)
    template.add_argument("--blueprint", required=True, type=Path)
    template.add_argument("--output", required=True, type=Path)

    review = commands.add_parser("summarize-review", help="summarize a completed user/AI development review")
    review.add_argument("pilot_dir", type=Path)
    review.add_argument("--population", required=True, type=Path)
    review.add_argument("--blueprint", required=True, type=Path)
    review.add_argument("--review", required=True, type=Path)
    review.add_argument("--output", required=True, type=Path)

    args = parser.parse_args(argv)
    if args.command == "build":
        print(build_pilot(population_path=args.population, blueprint_path=args.blueprint, content_path=args.content, output_root=args.output_root, built_at=args.built_at))
    elif args.command == "verify":
        verify_pilot(args.pilot_dir, args.population, args.blueprint)
        print("A1 pilot verification passed")
    elif args.command == "review-template":
        print(build_review_template(pilot_dir=args.pilot_dir, population_path=args.population, blueprint_path=args.blueprint, output_path=args.output))
    else:
        print(summarize_review(pilot_dir=args.pilot_dir, population_path=args.population, blueprint_path=args.blueprint, review_path=args.review, output_path=args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
