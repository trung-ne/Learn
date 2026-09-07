"""Independent read-only verification for immutable M11 export bundles."""
from __future__ import annotations

import csv
import io
import json
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from xml.etree import ElementTree as ET

from english_master.schema_validation import load_json, validate_instance

from .authority import assess_authorization
from .canonical import identity, sha256_bytes, sha256_file
from .models import build_export_model
from .renderers import common_cartridge_bytes


class ExportVerificationError(ValueError):
    """Raised when a published export is incomplete, changed, or malformed."""


class _StrictHTMLParser(HTMLParser):
    def error(self, message: str) -> None:  # pragma: no cover - compatibility hook
        raise ExportVerificationError(message)


def _safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def _validate_cartridge(path: Path, expected_bytes: bytes) -> None:
    if path.read_bytes() != expected_bytes:
        raise ExportVerificationError("IMS Common Cartridge bytes are not deterministic for the verified model")
    try:
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or any(not _safe_member(name) for name in names):
                raise ExportVerificationError("IMS archive has duplicate or unsafe members")
            if "imsmanifest.xml" not in names:
                raise ExportVerificationError("IMS archive has no imsmanifest.xml")
            for info in archive.infolist():
                if info.date_time != (1980, 1, 1, 0, 0, 0):
                    raise ExportVerificationError("IMS archive metadata is not fixed")
            manifest = ET.fromstring(archive.read("imsmanifest.xml"))
            hrefs = {
                node.attrib["href"]
                for node in manifest.iter()
                if node.tag.endswith("resource") and node.attrib.get("href")
            }
            files = {
                node.attrib["href"]
                for node in manifest.iter()
                if node.tag.endswith("file") and node.attrib.get("href")
            }
            expected_members = {"imsmanifest.xml", *hrefs}
            if hrefs != files or set(names) != expected_members:
                raise ExportVerificationError("IMS manifest/resource/archive closure mismatch")
            for href in sorted(hrefs):
                ET.fromstring(archive.read(href))
    except (OSError, zipfile.BadZipFile, ET.ParseError) as error:
        raise ExportVerificationError(f"invalid IMS Common Cartridge: {error}") from error


def _validate_payload_files(bundle: Path, manifest: Mapping[str, Any]) -> None:
    for item in manifest["files"]:
        path = bundle / Path(*PurePosixPath(item["path"]).parts)
        if not path.is_file():
            raise ExportVerificationError(f"missing inventoried file: {item['path']}")
        if path.stat().st_size != item["bytes"] or sha256_file(path) != item["sha256"]:
            raise ExportVerificationError(f"changed inventoried file: {item['path']}")
        suffix = path.suffix.lower()
        try:
            if suffix == ".json":
                json.loads(path.read_text(encoding="utf-8"))
            elif suffix == ".csv":
                data = path.read_bytes()
                if b"\n" in data.replace(b"\r\n", b""):
                    raise ExportVerificationError(f"CSV does not use RFC-4180 CRLF records: {item['path']}")
                list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))
            elif suffix == ".html":
                parser = _StrictHTMLParser(convert_charrefs=True)
                parser.feed(path.read_text(encoding="utf-8"))
                parser.close()
        except (UnicodeError, json.JSONDecodeError, csv.Error) as error:
            raise ExportVerificationError(f"cannot parse {item['path']}: {error}") from error


def build_verification(bundle: Path, repository_root: Path, *, require_receipt: bool) -> dict[str, Any]:
    """Reconstruct authority/model and verify the complete export directory."""

    try:
        manifest = load_json(bundle / "manifest.json")
        validate_instance(manifest, "m11-export-manifest")
    except (OSError, ValueError) as error:
        raise ExportVerificationError(f"invalid manifest: {error}") from error
    if manifest.get("export_id") != identity("m11export", manifest, "export_id"):
        raise ExportVerificationError("manifest export_id is not canonical")

    eligible = assess_authorization(bundle / "authorization.json", repository_root)
    if manifest["authorization_id"] != eligible.authorization["authorization_id"] or manifest["authorization_sha256"] != sha256_file(bundle / "authorization.json"):
        raise ExportVerificationError("manifest authorization binding mismatch")
    if manifest["exported_at"] < eligible.authorization["authorized_at"]:
        raise ExportVerificationError("export timestamp predates authorization")
    model = build_export_model(eligible.authorization, eligible.artifacts, exported_at=manifest["exported_at"])

    expected = {item["path"] for item in manifest["files"]} | {"manifest.json", "verification.json"}
    actual = {
        path.relative_to(bundle).as_posix()
        for path in bundle.rglob("*")
        if path.is_file()
    }
    if require_receipt:
        if actual != expected:
            raise ExportVerificationError(f"bundle inventory mismatch; missing={sorted(expected-actual)!r}, unexpected={sorted(actual-expected)!r}")
    else:
        if actual != expected - {"verification.json"}:
            raise ExportVerificationError("staged bundle inventory is not closed")
    _validate_payload_files(bundle, manifest)

    learner = (bundle / "print" / "learner.html").read_text(encoding="utf-8")
    instructor = (bundle / "print" / "instructor-answer-key.html").read_text(encoding="utf-8")
    if "Answer material:" in learner or "Answer material:" not in instructor:
        raise ExportVerificationError("learner/instructor answer-material separation failed")
    _validate_cartridge(bundle / "lms" / "english-master.imscc", common_cartridge_bytes(model))

    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "record_type": "m11_export_verification",
        "verification_id": "PENDING",
        "export_id": manifest["export_id"],
        "manifest_sha256": sha256_file(bundle / "manifest.json"),
        "authorization_sha256": sha256_file(bundle / "authorization.json"),
        "verified_at": manifest["exported_at"],
        "checks": ["ANSWER_SEPARATION", "ARCHIVE_CLOSURE", "AUTHORITY", "CLOSED_INVENTORY", "CSV", "DETERMINISTIC_ARCHIVE", "FILE_HASHES", "HTML", "JSON", "TATOEBA_EXCLUSION", "XML"],
        "verified_file_count": len(manifest["files"]),
        "result": "PASS",
        "approval_tier": "RELEASE_APPROVED",
        "human_reviewed": True,
        "release_approved": True,
    }
    receipt["verification_id"] = identity("m11verify", receipt, "verification_id")
    validate_instance(receipt, "m11-export-verification")
    if require_receipt:
        stored = load_json(bundle / "verification.json")
        validate_instance(stored, "m11-export-verification")
        if stored != receipt:
            raise ExportVerificationError("stored verification receipt does not match independent verification")
    return receipt


def verify_export(bundle: Path, repository_root: Path) -> dict[str, Any]:
    return build_verification(bundle.resolve(), repository_root.resolve(), require_receipt=True)
