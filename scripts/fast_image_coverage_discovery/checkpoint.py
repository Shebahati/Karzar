"""Checkpoint persistence for resumable discovery runs."""

from __future__ import annotations

import json
from pathlib import Path

from .contracts import DiscoveryRunState, ProductTerminalState


def checkpoint_path(package_dir: Path) -> Path:
    return package_dir / "checkpoint.json"


def save_checkpoint(state: DiscoveryRunState, package_dir: Path) -> None:
    package_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path(package_dir).write_text(
        json.dumps(state.to_checkpoint(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_checkpoint(package_dir: Path) -> dict | None:
    p = checkpoint_path(package_dir)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def apply_checkpoint(state: DiscoveryRunState, data: dict) -> None:
    for pid_s, row in (data.get("terminals") or {}).items():
        pid = int(pid_s)
        state.products[pid] = ProductTerminalState(
            product_id=pid,
            final_status=row.get("final_status", "unresolved"),
            stop_search=bool(row.get("stop_search")),
        )
    state.url_cache.update(data.get("url_cache") or {})
    state.sha_assets.update(data.get("sha_assets") or {})
