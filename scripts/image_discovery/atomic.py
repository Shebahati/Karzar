"""Atomic file writes and corrupt-state guards."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .contracts import DiscoveryError


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    atomic_write_bytes(path, text.encode(encoding))


def refuse_overwrite_if_corrupt_json(path: Path, *, code: str) -> None:
    """If path exists and is invalid JSON, do not overwrite — operator must archive."""
    if not path.exists():
        return
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DiscoveryError(
            "state",
            code,
            f"refusing to overwrite corrupt file: {path}",
        ) from e


def load_json_object(path: Path, *, missing_ok: bool, corrupt_code: str) -> Any:
    if not path.exists():
        if missing_ok:
            return None
        raise DiscoveryError("state", corrupt_code, f"missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DiscoveryError("state", corrupt_code, f"invalid JSON: {path}") from e
