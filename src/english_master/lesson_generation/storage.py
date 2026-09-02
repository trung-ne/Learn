"""Atomic, immutable storage for accepted and rejected M6 artifacts."""

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
    """Raised when the platform cannot provide atomic no-replace publication."""


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
    """Atomically rename a directory while refusing an existing destination."""

    if os.name == "nt":
        # MoveFile semantics used by os.rename do not replace an existing path.
        os.rename(source, destination)
        return
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform.startswith("linux"):
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise AtomicPublishError("renameat2 is required for atomic no-overwrite publication")
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        result = renameat2(-100, source_bytes, -100, destination_bytes, 1)  # AT_FDCWD, RENAME_NOREPLACE
    elif sys.platform == "darwin":
        renamex_np = getattr(libc, "renamex_np", None)
        if renamex_np is None:
            raise AtomicPublishError("renamex_np is required for atomic no-overwrite publication")
        renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        renamex_np.restype = ctypes.c_int
        result = renamex_np(source_bytes, destination_bytes, 0x00000004)  # RENAME_EXCL
    else:
        raise AtomicPublishError(f"atomic no-overwrite directory publication is unsupported on {sys.platform}")
    if result != 0:
        error_number = ctypes.get_errno()
        if error_number in (errno.EEXIST, errno.ENOTEMPTY):
            raise FileExistsError(error_number, os.strerror(error_number), destination)
        raise OSError(error_number, os.strerror(error_number), destination)


def _publish_bundle(destination: Path, files: Mapping[str, Mapping[str, Any]]) -> tuple[Path, ...]:
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
    # The exclusive rename is the publication commit point. A parent-directory
    # fsync improves crash durability on POSIX, but failure cannot truthfully be
    # reported as rejection because the complete bundle is already visible.
    try:
        _fsync_directory(destination.parent)
    except OSError:
        pass
    return tuple(destination / name for name in sorted(files))


def publish(output_directory: Path, lesson: Mapping[str, Any], audit: Mapping[str, Any]) -> tuple[Path, ...]:
    """Atomically publish one immutable accepted lesson bundle."""

    return _publish_bundle(output_directory, {"audit.json": audit, "lesson.json": lesson})


def publish_rejection(output_directory: Path, rejection: Mapping[str, Any], audit: Mapping[str, Any]) -> tuple[Path, ...]:
    """Atomically publish one immutable rejected-attempt bundle."""

    return _publish_bundle(output_directory, {"audit.json": audit, "rejection.json": rejection})
