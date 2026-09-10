"""CLI for fixture-only M14 listening-difficulty analysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .service import ListeningDifficultyError, project_m13, run, verify


def _local_path(value: str) -> Path:
    if "://" in value:
        raise argparse.ArgumentTypeError("URLs are prohibited; provide a local path")
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic offline fixture-only listening-difficulty analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True)
    execute = subparsers.add_parser("run", help="publish from one independently verified M13 fixture run")
    execute.add_argument("--transcription-run-directory", required=True, type=_local_path)
    execute.add_argument("--acoustic-sidecar", type=_local_path)
    execute.add_argument("--output-root", required=True, type=_local_path)
    checked = subparsers.add_parser("verify", help="read-only verify one immutable M14 run")
    checked.add_argument("--run-directory", required=True, type=_local_path)
    projected = subparsers.add_parser("project-m13", help="project one verified M13 run for internal analysis or sidecar authoring")
    projected.add_argument("--transcription-run-directory", required=True, type=_local_path)
    projected.add_argument("--output", required=True, type=_local_path)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command == "run":
            directory = run(
                transcription_run_directory=arguments.transcription_run_directory,
                acoustic_sidecar_path=arguments.acoustic_sidecar,
                output_root=arguments.output_root,
            )
            result = {"run_directory": str(directory)}
        elif arguments.command == "project-m13":
            if arguments.output.exists():
                raise FileExistsError(f"refusing to overwrite projection: {arguments.output}")
            fixture = project_m13(arguments.transcription_run_directory)
            arguments.output.parent.mkdir(parents=True, exist_ok=True)
            arguments.output.write_text(json.dumps(fixture, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
            result = {"fixture_path": str(arguments.output), "publishable": False}
        else:
            result = verify(run_directory=arguments.run_directory)
    except (ListeningDifficultyError, OSError, ValueError) as error:
        print(f"listening-difficulty analysis failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
