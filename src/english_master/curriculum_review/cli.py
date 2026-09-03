"""Offline CLI for M5 independent review and approval snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from english_master.curriculum_review.loading import load_strict_bundle, load_strict_document
from english_master.curriculum_review.storage import AtomicPublishError, PostCommitDurabilityError, publish_bundle
from english_master.curriculum_review.workflow import (
    ReviewValidationError,
    build_manifest,
    publish_approval,
    publish_development_snapshot,
    verify_development_snapshot_bundle,
    verify_snapshot_bundle,
)
from english_master.schema_validation import SchemaValidationError


def _bundle_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("structure", type=Path, help="M5 curriculum/structure.json")
    parser.add_argument("--graph", type=Path, help="Override graph path")
    parser.add_argument("--coverage", type=Path, help="Override coverage path")
    parser.add_argument("--taxonomy", type=Path, help="Override taxonomy path")
    parser.add_argument(
        "--source-registry",
        type=Path,
        required=True,
        help="Independently loaded current source registry",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the prepare/publish/verify command parser."""

    parser = argparse.ArgumentParser(description="Prepare, publish, and verify M5 independent human-review snapshots offline.")
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Create an immutable hash manifest for human review")
    _bundle_arguments(prepare)
    prepare.add_argument("--output", type=Path, required=True, help="New immutable manifest directory")
    publish = commands.add_parser("publish", help="Validate two human reviews and publish an approval snapshot")
    _bundle_arguments(publish)
    publish.add_argument("--manifest", type=Path, required=True)
    publish.add_argument("--linguistic-review", type=Path, required=True)
    publish.add_argument("--pedagogical-review", type=Path, required=True)
    publish.add_argument("--reviewer-registry", type=Path, required=True, help="Independently managed trusted reviewer identity registry")
    publish.add_argument("--approved-at", required=True, help="Trusted ISO 8601 publication timestamp")
    publish.add_argument("--published-by", required=True, help="Administrative publisher identity")
    publish.add_argument("--output", type=Path, required=True, help="New immutable approval directory")
    verify = commands.add_parser("verify", help="Verify a published snapshot against current M5 files")
    _bundle_arguments(verify)
    verify.add_argument("--snapshot", type=Path, required=True, help="Published approval bundle directory")
    verify.add_argument("--reviewer-registry", type=Path, required=True, help="Independently loaded trusted reviewer identity registry")
    develop_publish = commands.add_parser("develop-publish", help="Publish a deterministic M5 development-only snapshot")
    _bundle_arguments(develop_publish)
    develop_publish.add_argument("--manifest", type=Path, required=True)
    develop_publish.add_argument("--produced-at", required=True, help="Trusted ISO 8601 tool execution timestamp")
    develop_publish.add_argument("--tool-version", default="3.0")
    develop_publish.add_argument("--git-commit", help="Optional current Git commit hash")
    develop_publish.add_argument("--output", type=Path, required=True, help="New immutable development snapshot directory")
    develop_verify = commands.add_parser("develop-verify", help="Verify an M5 development-only snapshot")
    _bundle_arguments(develop_verify)
    develop_verify.add_argument("--snapshot", type=Path, required=True)
    return parser


def _load_bundle(arguments: argparse.Namespace):
    return load_strict_bundle(arguments.structure, graph_path=arguments.graph, coverage_path=arguments.coverage, taxonomy_path=arguments.taxonomy)


def _load_source_registry(arguments: argparse.Namespace) -> tuple[dict[str, object], Path]:
    path = arguments.source_registry.resolve()
    return load_strict_document(path), path


def _print_review_error(error: ReviewValidationError) -> None:
    for issue in error.issues:
        print(f"{issue.path}: {issue.code}: {issue.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    """Execute one review workflow operation."""

    arguments = build_parser().parse_args(argv)
    try:
        bundle = _load_bundle(arguments)
        source_registry, source_registry_path = _load_source_registry(arguments)
        if arguments.command == "prepare":
            manifest = build_manifest(
                bundle,
                source_registry,
                source_registry_path=source_registry_path,
            )
            publish_bundle(arguments.output, {"manifest.json": manifest})
            print(f"Prepared M5 review manifest {manifest['manifest_id']}: {arguments.output}")
            return 0
        if arguments.command == "publish":
            manifest = load_strict_document(arguments.manifest)
            reviews = [load_strict_document(arguments.linguistic_review), load_strict_document(arguments.pedagogical_review)]
            reviewer_registry = load_strict_document(arguments.reviewer_registry)
            snapshot = publish_approval(
                arguments.output,
                bundle,
                manifest,
                reviews,
                reviewer_registry,
                source_registry=source_registry,
                source_registry_path=source_registry_path,
                approved_at=arguments.approved_at,
                published_by=arguments.published_by,
            )
            print(f"Published M5 approval snapshot {snapshot['snapshot_id']}: {arguments.output}")
            return 0
        if arguments.command == "develop-publish":
            manifest = load_strict_document(arguments.manifest)
            snapshot = publish_development_snapshot(
                arguments.output, bundle, manifest, source_registry=source_registry,
                source_registry_path=source_registry_path, produced_at=arguments.produced_at,
                tool_version=arguments.tool_version, git_commit=arguments.git_commit,
            )
            print(f"Published M5 development snapshot {snapshot['snapshot_id']}: {arguments.output}")
            return 0
        if arguments.command == "develop-verify":
            snapshot = verify_development_snapshot_bundle(
                arguments.snapshot, bundle, source_registry=source_registry, source_registry_path=source_registry_path,
            )
            print(f"Verified M5 development snapshot {snapshot['snapshot_id']}: {arguments.snapshot}")
            return 0
        reviewer_registry = load_strict_document(arguments.reviewer_registry)
        snapshot = verify_snapshot_bundle(
            arguments.snapshot,
            bundle,
            reviewer_registry,
            source_registry=source_registry,
            source_registry_path=source_registry_path,
        )
        print(f"Verified M5 approval snapshot {snapshot['snapshot_id']}: {arguments.snapshot}")
        return 0
    except ReviewValidationError as error:
        _print_review_error(error)
        return 1
    except PostCommitDurabilityError as error:
        print(f"Publication is visible but durability confirmation failed: {error}", file=sys.stderr)
        return 2
    except (FileExistsError, AtomicPublishError) as error:
        print(f"Publication failed: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, yaml.YAMLError, SchemaValidationError) as error:
        print(f"M5 review workflow failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
