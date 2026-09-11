from __future__ import annotations
import argparse
from pathlib import Path
from .service import run, validate_population
from english_master.schema_validation import load_document

def main() -> int:
    parser=argparse.ArgumentParser(description="Build or validate the deterministic M15 knowledge graph")
    sub=parser.add_subparsers(dest="command",required=True)
    p=sub.add_parser("build"); p.add_argument("output",type=Path)
    v=sub.add_parser("validate"); v.add_argument("population",type=Path)
    args=parser.parse_args()
    if args.command=="build": run(args.output); return 0
    validate_population(load_document(args.population)); return 0
if __name__=="__main__": raise SystemExit(main())
