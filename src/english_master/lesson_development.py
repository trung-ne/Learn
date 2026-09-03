"""Build and publish the fixed M6 development approval batch."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from english_master.lesson_generation.authority import VerifiedM5DevelopmentAuthority
from english_master.lesson_generation.development import build_development_batch, publish_development_batch


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    root = _root()
    parser = argparse.ArgumentParser(description="Publish only a validated M6 DEVELOPMENT_APPROVED batch; never human or release approval")
    parser.add_argument("--snapshot-dir", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--git-commit")
    parser.add_argument("--structure", type=Path, default=root / "curriculum" / "structure.json")
    parser.add_argument("--source-registry", type=Path, default=root / "sources" / "registry.yaml")
    args = parser.parse_args(argv)
    try:
        m5 = VerifiedM5DevelopmentAuthority.from_files(args.structure, args.snapshot_dir, args.source_registry)
        report = build_development_batch(m5, args.bundle_root, created_at=args.created_at, git_commit=args.git_commit)
        published = publish_development_batch(args.output, report, m5, args.bundle_root)
    except Exception as error:
        print(f"M6 development promotion failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(f"M6 DEVELOPMENT_APPROVED batch {published['batch_id']}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
