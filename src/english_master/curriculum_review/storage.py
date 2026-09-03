"""Atomic immutable directory publication for M5 review artifacts."""

from __future__ import annotations

import ctypes
import errno
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping


class AtomicPublishError(OSError):
    """Raised when atomic no-replace publication is unavailable."""


class PostCommitDurabilityError(AtomicPublishError):
    """Raised when publication is visible but parent-directory fsync fails."""

    def __init__(self, destination: Path, cause: OSError) -> None:
        self.destination = destination
        self.cause = cause
        super().__init__(f"bundle is visible at {destination}, but parent-directory fsync failed: {cause}")


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_directory_noreplace(source: Path, destination: Path) -> None:
    if os.name == "nt":
        os.rename(source, destination)
        return
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform.startswith("linux"):
        function = getattr(libc, "renameat2", None)
        if function is None:
            raise AtomicPublishError("renameat2 is required for atomic no-overwrite publication")
        function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(-100, source_bytes, -100, destination_bytes, 1)
    elif sys.platform == "darwin":
        function = getattr(libc, "renamex_np", None)
        if function is None:
            raise AtomicPublishError("renamex_np is required for atomic no-overwrite publication")
        function.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        function.restype = ctypes.c_int
        result = function(source_bytes, destination_bytes, 0x00000004)
    else:
        raise AtomicPublishError(f"atomic no-overwrite publication is unsupported on {sys.platform}")
    if result:
        number = ctypes.get_errno()
        if number in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(number, os.strerror(number), destination)
        raise OSError(number, os.strerror(number), destination)


def publish_bundle(destination: Path, files: Mapping[str, Mapping[str, Any]]) -> tuple[Path, ...]:
    """Publish all JSON documents together, refusing overwrite."""

    if not files or any(Path(name).name != name or not name.endswith(".json") for name in files):
        raise ValueError("bundle members must be nonempty, flat .json filenames")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        for name in sorted(files):
            _write_json(staging / name, files[name])
        _fsync_directory(staging)
        _rename_directory_noreplace(staging, destination)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    try:
        _fsync_directory(destination.parent)
    except OSError as error:
        raise PostCommitDurabilityError(destination, error) from error
    return tuple(destination / name for name in sorted(files))
