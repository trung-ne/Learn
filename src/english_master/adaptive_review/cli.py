"""CLI for offline adaptive review."""
from __future__ import annotations
import argparse
from pathlib import Path
from .service import build_review_plan, observe_submission

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Build deterministic local adaptive-review plans.")
    sub=parser.add_subparsers(dest="command",required=True)
    obs=sub.add_parser("observe"); obs.add_argument("--package",required=True,type=Path); obs.add_argument("--submission",required=True,type=Path); obs.add_argument("--adaptive-state",required=True,type=Path); obs.add_argument("--output",required=True,type=Path)
    plan=sub.add_parser("plan"); plan.add_argument("--assessment-run",required=True,type=Path); plan.add_argument("--state",required=True,type=Path); plan.add_argument("--adaptive-state",required=True,type=Path); plan.add_argument("--lesson-id",required=True); plan.add_argument("--as-of",required=True); plan.add_argument("--limit",type=int,default=10); plan.add_argument("--output",required=True,type=Path)
    args=parser.parse_args(argv)
    if args.command=="observe":
        result=observe_submission(package_path=args.package,submission_path=args.submission,adaptive_state_path=args.adaptive_state,output_path=args.output)
        print(f"Adaptive observation: {result['observation_sha256']}")
    else:
        result=build_review_plan(assessment_run=args.assessment_run,state_path=args.state,adaptive_state_path=args.adaptive_state,lesson_id=args.lesson_id,as_of=args.as_of,output_path=args.output,limit=args.limit)
        print(f"Adaptive review plan: {result['plan_sha256']} ({len(result['entries'])} items)")
    return 0
