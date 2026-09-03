"""Canonical JSON identities for M5 review artifacts."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_json(value: Any) -> str:
    """Serialize a JSON value canonically for local deterministic hashing."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_json(value: Any) -> str:
    """Return the SHA-256 hash of canonical JSON without buffering one full copy."""

    digest = hashlib.sha256()
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    for chunk in encoder.iterencode(value):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def content_identity(prefix: str, value: Mapping[str, Any], field: str) -> str:
    """Derive a stable identity after removing the identity field itself."""

    payload = dict(value)
    payload.pop(field, None)
    return f"{prefix}_{sha256_json(payload)}"
