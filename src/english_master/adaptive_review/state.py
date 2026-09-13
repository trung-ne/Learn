"""Adaptive state loading and atomic persistence."""
from __future__ import annotations
import json, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from english_master.schema_validation import validate_instance

INTERVALS = (1, 3, 7, 14, 30, 60)

def parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be explicit UTC ending in Z")
    try: value_dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc: raise ValueError("invalid UTC timestamp") from exc
    if value_dt.tzinfo != timezone.utc: raise ValueError("timestamp must use UTC")
    return value_dt

def utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def load_state(path: Path) -> list[dict[str, Any]]:
    if not path.exists(): return []
    with path.open(encoding="utf-8") as fh: state = json.load(fh)
    validate_instance(state, "adaptive-review-state-v1")
    ids = [row["concept_id"] for row in state]
    if ids != sorted(ids) or len(ids) != len(set(ids)): raise ValueError("adaptive state must be sorted and unique")
    for row in state:
        parse_utc(row["last_reviewed_at"]); parse_utc(row["next_review"])
        if row["last_mistake_at"] is not None: parse_utc(row["last_mistake_at"])
    return [dict(row) for row in state]

def atomic_write(path: Path, state: Sequence[Mapping[str, Any]]) -> None:
    validate_instance(list(state), "adaptive-review-state-v1")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(list(state), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True); raise
