"""Read-only validation for a bounded M12 operational local-media pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from .schema_validation import SchemaValidationError, load_document, validate_instance


class LocalPilotValidationError(ValueError):
    """Raised when a local pilot manifest or listed file fails validation."""


def _safe_local_file(input_root: Path, relative_path: str) -> Path:
    """Resolve a manifest path beneath *input_root* without following file symlinks."""

    portable = relative_path.replace("\\", "/")
    raw_parts = portable.split("/")
    posix_path = PurePosixPath(portable)
    windows_path = PureWindowsPath(relative_path)
    if (
        posix_path.is_absolute()
        or windows_path.is_absolute()
        or windows_path.drive
        or not raw_parts
        or any(part in {"", ".", ".."} for part in raw_parts)
    ):
        raise LocalPilotValidationError(f"unsafe relative path: {relative_path!r}")

    candidate = input_root.joinpath(*posix_path.parts)
    current = input_root
    for part in posix_path.parts:
        current = current / part
        if current.is_symlink():
            raise LocalPilotValidationError(
                f"path must not contain symlinks: {relative_path!r}"
            )

    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(input_root)
    except (FileNotFoundError, OSError, ValueError) as error:
        raise LocalPilotValidationError(
            f"path is missing or outside the input root: {relative_path!r}"
        ) from error

    try:
        mode = resolved.stat().st_mode
    except OSError as error:
        raise LocalPilotValidationError(
            f"cannot inspect listed file: {relative_path!r}"
        ) from error
    if not stat.S_ISREG(mode):
        raise LocalPilotValidationError(
            f"path is not a regular file: {relative_path!r}"
        )
    return resolved


def _observed_sha256(path: Path, display_path: str) -> str:
    """Hash a regular local file and reject concurrent observable changes."""

    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise LocalPilotValidationError(
            f"file changed while being hashed: {display_path!r}"
        )
    return digest.hexdigest()


def validate_local_pilot_manifest(
    *, manifest_path: Path, input_root: Path
) -> dict[str, Any]:
    """Validate manifest shape, identities, paths, and observed file hashes."""

    try:
        resolved_root = input_root.resolve(strict=True)
    except (FileNotFoundError, OSError) as error:
        raise LocalPilotValidationError(f"input root does not exist: {input_root}") from error
    if not resolved_root.is_dir():
        raise LocalPilotValidationError(f"input root is not a directory: {input_root}")

    manifest = load_document(manifest_path)
    validate_instance(manifest, "m12-local-pilot-manifest")

    seen_ids: dict[str, int] = {}
    records = manifest["records"]
    for index, record in enumerate(records):
        record_id = record["id"]
        if record_id in seen_ids:
            raise LocalPilotValidationError(
                f"duplicate record id {record_id!r} at records[{index}]; "
                f"first declared at records[{seen_ids[record_id]}]"
            )
        seen_ids[record_id] = index

        listed_path = record["path"]
        local_file = _safe_local_file(resolved_root, listed_path)
        observed = _observed_sha256(local_file, listed_path)
        if observed != record["sha256"]:
            raise LocalPilotValidationError(
                f"SHA-256 mismatch for records[{index}] {record_id!r}: "
                f"declared {record['sha256']}, observed {observed}"
            )

    return {
        "result": "VALID",
        "record_count": len(records),
        "hashes_verified": len(records),
        "network_accessed": False,
        "media_processed": False,
    }


def _local_path(value: str) -> Path:
    if "://" in value:
        raise argparse.ArgumentTypeError("URLs are prohibited; provide a local path")
    return Path(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only validation of an M12 operational local pilot manifest"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate listed local files")
    validate.add_argument("--manifest", required=True, type=_local_path)
    validate.add_argument("--input-root", required=True, type=_local_path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = validate_local_pilot_manifest(
            manifest_path=args.manifest,
            input_root=args.input_root,
        )
    except (
        LocalPilotValidationError,
        SchemaValidationError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as error:
        print(f"M12 local pilot manifest INVALID: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
