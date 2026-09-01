"""Canonical UTF-8 serialization and SHA-256 contracts for M4."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

_HASH = re.compile(r"^[a-f0-9]{64}$")


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize JSON with sorted keys, compact separators, UTF-8, and one LF."""

    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 hexadecimal digest."""

    return hashlib.sha256(value).hexdigest()


def raw_record_hash(record: dict[str, Any]) -> str:
    """Hash the complete canonical M3 JSON record, never normalized text alone."""

    return sha256_bytes(canonical_json_bytes(record))


def normalized_comparison_hash(language: str, comparison_text: str) -> str:
    """Hash a language-scoped canonical comparison representation."""

    return sha256_bytes(
        canonical_json_bytes({"language": language.casefold(), "comparison_text": comparison_text})
    )


def is_sha256(value: object) -> bool:
    """Return whether *value* is a canonical lowercase SHA-256 digest."""

    return isinstance(value, str) and _HASH.fullmatch(value) is not None
