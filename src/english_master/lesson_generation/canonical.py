"""Canonical JSON and deterministic identities for M6."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    """Hash the exact UTF-8 text passed to a provider boundary."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def identity(prefix: str, value: Mapping[str, Any], identity_field: str) -> str:
    payload = dict(value)
    payload.pop(identity_field, None)
    return f"{prefix}_{sha256_json(payload)}"


def request_id(value: Mapping[str, Any]) -> str:
    return identity("req", value, "request_id")


def authorization_id(value: Mapping[str, Any]) -> str:
    return identity("auth", value, "authorization_id")
