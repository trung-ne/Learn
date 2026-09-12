"""Command line interface for the bounded A2 pilot."""
from __future__ import annotations
import argparse
from pathlib import Path
from .service import build_pilot, verify_pilot, audit_pilot, sample_pilot

def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Build and validate the bounded A2 pilot.")
    commands=parser.add_subparsers(dest="command", required=True)
    b=commands.add_parser("build"); b.add_argument("--population",required=True,type=Path); b.add_argument("--blueprint",required=True,type=Path); b.add_argument("--content",required=True,type=Path); b.add_argument("--output-root",required=True,type=Path); b.add_argument("--built-at",required=True)
    v=commands.add_parser("verify"); v.add_argument("pilot_dir",type=Path); v.add_argument("--population",required=True,type=Path); v.add_argument("--blueprint",required=True,type=Path)
    a=commands.add_parser("audit"); a.add_argument("pilot_dir",type=Path); a.add_argument("--population",required=True,type=Path); a.add_argument("--blueprint",required=True,type=Path); a.add_argument("--output",required=True,type=Path)
    s=commands.add_parser("sample"); s.add_argument("pilot_dir",type=Path); s.add_argument("--population",required=True,type=Path); s.add_argument("--blueprint",required=True,type=Path); s.add_argument("--audit-report",required=True,type=Path); s.add_argument("--seed",required=True); s.add_argument("--size",type=int,default=5); s.add_argument("--output",required=True,type=Path)
    args=parser.parse_args(argv)
    if args.command=="build": print(build_pilot(population_path=args.population,blueprint_path=args.blueprint,content_path=args.content,output_root=args.output_root,built_at=args.built_at))
    elif args.command=="verify": verify_pilot(args.pilot_dir,args.population,args.blueprint); print("A2 pilot verification passed")
    elif args.command=="audit": print(audit_pilot(pilot_dir=args.pilot_dir,population_path=args.population,blueprint_path=args.blueprint,output_path=args.output))
    else: print(sample_pilot(pilot_dir=args.pilot_dir,population_path=args.population,blueprint_path=args.blueprint,audit_report_path=args.audit_report,seed=args.seed,sample_size=args.size,output_path=args.output))
    return 0
if __name__=="__main__": raise SystemExit(main())
