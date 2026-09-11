from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from english_master.m12_local_pilot import (
    LocalPilotValidationError,
    main,
    validate_local_pilot_manifest,
)
from english_master.schema_validation import SchemaValidationError, validate_instance


def _manifest(input_root: Path, count: int = 10) -> dict[str, object]:
    records: list[dict[str, object]] = []
    for index in range(count):
        content = f"fake-media-{index}".encode()
        relative_path = f"media/record-{index:02d}.bin"
        path = input_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        records.append(
            {
                "id": f"local-media-{index:02d}",
                "path": relative_path,
                "sha256": hashlib.sha256(content).hexdigest(),
                "duration_seconds": 10.0,
                "source_url": f"https://example.test/media/{index}",
                "license": "CC0-1.0",
                "attribution": f"Fake test record {index}",
                "permissions": {
                    "storage": True,
                    "transcript": index % 2 == 0,
                    "timestamp": False,
                },
            }
        )
    return {
        "schema_version": "1.0",
        "record_type": "m12_operational_local_pilot_manifest",
        "records": records,
    }


def _write_manifest(tmp_path: Path, manifest: dict[str, object]) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_validates_ten_local_fake_files_read_only(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    manifest = _manifest(input_root)
    manifest_path = _write_manifest(tmp_path, manifest)

    result = validate_local_pilot_manifest(
        manifest_path=manifest_path, input_root=input_root
    )

    assert result == {
        "result": "VALID",
        "record_count": 10,
        "hashes_verified": 10,
        "network_accessed": False,
        "media_processed": False,
    }
    assert sorted(path.relative_to(input_root).as_posix() for path in input_root.rglob("*")) == [
        "media",
        *[f"media/record-{index:02d}.bin" for index in range(10)],
    ]


def test_cli_validate_reports_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    input_root = tmp_path / "input"
    manifest_path = _write_manifest(tmp_path, _manifest(input_root))

    assert main(["validate", "--manifest", str(manifest_path), "--input-root", str(input_root)]) == 0
    assert json.loads(capsys.readouterr().out)["record_count"] == 10


def test_rejects_wrong_hash(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    manifest = _manifest(input_root)
    manifest["records"][3]["sha256"] = "0" * 64  # type: ignore[index]

    with pytest.raises(LocalPilotValidationError, match="SHA-256 mismatch"):
        validate_local_pilot_manifest(
            manifest_path=_write_manifest(tmp_path, manifest), input_root=input_root
        )


def test_rejects_duplicate_record_ids(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    manifest = _manifest(input_root)
    manifest["records"][1]["id"] = manifest["records"][0]["id"]  # type: ignore[index]

    with pytest.raises(LocalPilotValidationError, match="duplicate record id"):
        validate_local_pilot_manifest(
            manifest_path=_write_manifest(tmp_path, manifest), input_root=input_root
        )


def test_schema_rejects_unsafe_path_and_out_of_bounds_count(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    manifest = _manifest(input_root)
    manifest["records"][0]["path"] = "../outside.bin"  # type: ignore[index]
    with pytest.raises(SchemaValidationError):
        validate_instance(manifest, "m12-local-pilot-manifest")

    too_small = _manifest(tmp_path / "other-input", count=9)
    with pytest.raises(SchemaValidationError):
        validate_instance(too_small, "m12-local-pilot-manifest")


def test_rejects_symlinked_file_when_supported(tmp_path: Path) -> None:
    input_root = tmp_path / "input"
    manifest = _manifest(input_root)
    target = input_root / "media" / "record-00.bin"
    link = input_root / "media" / "linked.bin"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable")
    manifest["records"][0]["path"] = "media/linked.bin"  # type: ignore[index]

    with pytest.raises(LocalPilotValidationError, match="symlinks"):
        validate_local_pilot_manifest(
            manifest_path=_write_manifest(tmp_path, manifest), input_root=input_root
        )
