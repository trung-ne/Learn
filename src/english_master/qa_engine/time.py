"""Exact, orderable RFC 3339 timestamps for M8 evidence."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal

_ORDERABLE_TIMESTAMP = re.compile(
    r"(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-5][0-9])"
    r"(?P<fraction>\.[0-9]+)?(?P<offset>Z|[+-][0-9]{2}:[0-9]{2})"
)
_EPOCH = datetime(1970, 1, 1)


def orderable_timestamp(value: object) -> Decimal:
    """Return an exact UTC second value or reject an unorderable timestamp."""

    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    match = _ORDERABLE_TIMESTAMP.fullmatch(value)
    if match is None or value.endswith("-00:00"):
        raise ValueError(
            "timestamp must be orderable RFC 3339 without leap seconds or -00:00"
        )
    offset = "+00:00" if match.group("offset") == "Z" else match.group("offset")
    whole = (
        f"{match.group('date')}T{match.group('hour')}:"
        f"{match.group('minute')}:{match.group('second')}{offset}"
    )
    try:
        parsed = datetime.fromisoformat(whole)
        utc_value = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except (OverflowError, ValueError) as error:
        raise ValueError("timestamp cannot be ordered by this implementation") from error
    delta = utc_value - _EPOCH
    return Decimal(delta.days * 86_400 + delta.seconds) + Decimal(
        match.group("fraction") or "0"
    )


def ensure_not_after(left: object, right: object, message: str) -> None:
    if orderable_timestamp(left) > orderable_timestamp(right):
        raise ValueError(message)
