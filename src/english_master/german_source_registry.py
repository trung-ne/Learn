"""Language-scoped, no-download German source registry for 12.5C."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from english_master.multilingual_validation import validate_multilingual_source_registry

_REVIEWED_AT = "2026-09-14T00:00:00Z"


def _media() -> dict[str, dict[str, bool]]:
    return {
        "text": {
            "ingest_allowed": True, "store_allowed": True, "redistribute_allowed": True,
            "transform_allowed": True, "transcript_allowed": False, "exercise_allowed": True,
            "derived_redistribution_allowed": True,
        },
        "audio": {
            "download_allowed": False, "store_allowed": False, "clip_allowed": False,
            "transform_allowed": False, "transcript_allowed": False, "timestamp_allowed": False,
            "exercise_allowed": False, "redistribute_allowed": False,
            "derived_redistribution_allowed": False,
        },
        "video": {
            "download_allowed": False, "store_allowed": False, "clip_allowed": False,
            "audio_extraction_allowed": False, "transcript_allowed": False,
            "timestamp_allowed": False, "exercise_allowed": False, "redistribute_allowed": False,
            "derived_redistribution_allowed": False,
        },
    }


def _source(
    source_id: str,
    name: str,
    owner: str,
    url: str,
    license_name: str,
    license_url: str,
    status: str,
    *,
    source_type: str = "dump",
    reference_allowed: bool = True,
    ingest_allowed: bool = True,
    download_allowed: bool = True,
    notes: str,
) -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "source_id": source_id,
        "source_name": name,
        "owner": owner,
        "source_type": source_type,
        "source_url": url,
        "taxonomy_reference_url_prefixes": [url],
        "description": f"German-language {name}; this registration is a source-governance record only.",
        "content_types": ["text", "metadata"],
        "access": {
            "preferred_method": "official_dump" if source_type == "dump" else "manual_reference",
            "api_url": None,
            "dataset_url": url,
            "crawl_allowed": False,
            "download_allowed": download_allowed,
        },
        "license": {"name": license_name, "url": license_url, "reviewed_at": _REVIEWED_AT, "notes": notes},
        "permissions": {
            "reference_allowed": reference_allowed,
            "ingest_allowed": ingest_allowed,
            "store_allowed": ingest_allowed,
            "modify_allowed": ingest_allowed,
            "redistribute_allowed": ingest_allowed,
            "commercial_use_allowed": ingest_allowed,
        },
        "media_permissions": _media(),
        "attribution": {
            "required": license_name != "CC0-1.0",
            "format": f"{name}, {{source_url}}, {{license_url}}" if license_name != "CC0-1.0" else None,
            "requirements": "Retain source identity, URL, license, retrieval facts, and any required attribution.",
        },
        "technical": {
            "robots_notes": "Do not crawl pages; use only the explicitly registered official route.",
            "rate_limit_notes": "No network operation is performed by this milestone; respect source limits in any future authorized run.",
            "official_api_available": False,
            "official_dump_available": source_type == "dump",
        },
        "status": status,
        "evidence": [{"url": url, "description": "Official source or terms locator recorded for later verification.", "checked_at": _REVIEWED_AT}],
        "registered_at": _REVIEWED_AT,
        "registered_by": "12.5C German source-registry preparation",
        "reviewed_at": _REVIEWED_AT,
        "review_notes": notes,
    }


def build_registry() -> dict[str, Any]:
    sources = [
        _source(
            "src_de_wiktionary_dump", "German Wiktionary official text dumps", "Wikimedia Foundation",
            "https://dumps.wikimedia.org/dewiktionary/", "CC-BY-SA-4.0",
            "https://creativecommons.org/licenses/by-sa/4.0/", "APPROVED",
            notes="Text dump lane only; preserve attribution and share-alike obligations. No webpage crawl.",
        ),
        _source(
            "src_de_wikibooks_dump", "German Wikibooks official text dumps", "Wikimedia Foundation",
            "https://dumps.wikimedia.org/dewikibooks/", "CC-BY-SA-4.0",
            "https://creativecommons.org/licenses/by-sa/4.0/", "APPROVED",
            notes="Text dump lane only; preserve attribution and share-alike obligations. No webpage crawl.",
        ),
        _source(
            "src_de_wikidata_lexemes", "Wikidata German lexeme metadata", "Wikimedia Foundation",
            "https://www.wikidata.org/wiki/Wikidata:Data_access", "CC0-1.0",
            "https://creativecommons.org/publicdomain/zero/1.0/", "APPROVED",
            source_type="api", notes="Structured metadata reference/API lane; query limits and exact record provenance remain required.",
        ),
        _source(
            "src_de_goethe_reference", "Goethe-Institut German learning resources", "Goethe-Institut",
            "https://www.goethe.de/", "PROVIDER_TERMS_UNVERIFIED", "https://www.goethe.de/", "REFERENCE_ONLY",
            source_type="other", reference_allowed=True, ingest_allowed=False, download_allowed=False,
            notes="Reference and taxonomy study only until affirmative reuse permission is documented; no copying or ingestion.",
        ),
        _source(
            "src_de_deutsche_welle_reference", "Deutsche Welle German learning resources", "Deutsche Welle",
            "https://www.dw.com/", "PROVIDER_TERMS_UNVERIFIED", "https://www.dw.com/", "REFERENCE_ONLY",
            source_type="other", reference_allowed=True, ingest_allowed=False, download_allowed=False,
            notes="Reference and taxonomy study only until affirmative reuse permission is documented; no copying or ingestion.",
        ),
    ]
    return {
        "schema_version": "1.0",
        "record_type": "multilingual_source_registry",
        "registry": {"schema_version": "1.0", "sources": sources},
        "language_scopes": [{"source_id": source["source_id"], "language_codes": ["de"]} for source in sources],
    }


def validate_registry(value: dict[str, Any]) -> dict[str, Any]:
    validate_multilingual_source_registry(value)
    for source in value["registry"]["sources"]:
        if source["source_id"] not in {scope["source_id"] for scope in value["language_scopes"]}:
            raise ValueError(f"missing German language scope: {source['source_id']}")
        if source["status"] == "REFERENCE_ONLY" and source["permissions"]["ingest_allowed"]:
            raise ValueError(f"reference-only source cannot permit ingestion: {source['source_id']}")
        if source["status"] != "APPROVED" and source["permissions"]["redistribute_allowed"]:
            raise ValueError(f"non-approved source cannot permit redistribution: {source['source_id']}")
    return value


def write_registry(output: Path) -> Path:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite immutable registry artifact: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    value = validate_registry(build_registry())
    output.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return output
