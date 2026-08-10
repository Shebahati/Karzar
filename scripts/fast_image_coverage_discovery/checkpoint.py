"""Checkpoint persistence for resumable discovery runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import (
    DiscoveryCandidate,
    DiscoveryRunState,
    MaterializedAsset,
    ProductTerminalState,
)


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


def _restore_candidate(data: dict[str, Any] | None) -> DiscoveryCandidate | None:
    if not data:
        return None
    asset = None
    raw_asset = data.get("asset")
    if isinstance(raw_asset, dict) and raw_asset.get("sha256"):
        asset = MaterializedAsset(
            sha256=str(raw_asset["sha256"]),
            relative_path=str(raw_asset.get("relative_path") or ""),
            width=int(raw_asset.get("width") or 0),
            height=int(raw_asset.get("height") or 0),
            format=str(raw_asset.get("format") or ""),
            byte_size=int(raw_asset.get("byte_size") or 0),
            mime_type=str(raw_asset.get("mime_type") or ""),
            source_url=str(raw_asset.get("source_url") or ""),
        )
    return DiscoveryCandidate(
        product_id=int(data["product_id"]),
        sku=str(data.get("sku") or ""),
        brand_key=str(data.get("brand_key") or ""),
        product_name=str(data.get("product_name") or ""),
        category=str(data.get("category") or ""),
        source_id=str(data.get("source_id") or ""),
        source_domain=str(data.get("source_domain") or ""),
        source_country=str(data.get("source_country") or ""),
        source_class=str(data.get("source_class") or ""),
        lane=str(data.get("lane") or ""),
        source_page_url=str(data.get("source_page_url") or ""),
        source_image_url=str(data.get("source_image_url") or ""),
        match_type=str(data.get("match_type") or ""),
        brand_evidence=str(data.get("brand_evidence") or ""),
        sku_model_evidence=str(data.get("sku_model_evidence") or ""),
        page_identity_evidence=str(data.get("page_identity_evidence") or ""),
        gallery_identity_evidence=str(data.get("gallery_identity_evidence") or ""),
        owner_usage_policy=data.get("owner_usage_policy") or "non_iranian_not_precleared",  # type: ignore[arg-type]
        discovery_status=data.get("discovery_status") or "unresolved",  # type: ignore[arg-type]
        temporary_primary_eligible=bool(data.get("temporary_primary_eligible")),
        asset=asset,
        reason_code=str(data.get("reason_code") or ""),
        missing_evidence=str(data.get("missing_evidence") or ""),
        best_known_evidence=str(data.get("best_known_evidence") or ""),
        recommended_action=str(data.get("recommended_action") or ""),
        discovery_timestamp=str(data.get("discovery_timestamp") or ""),
        stop_search=bool(data.get("stop_search")),
    )


def apply_checkpoint(state: DiscoveryRunState, data: dict) -> None:
    for pid_s, row in (data.get("terminals") or {}).items():
        pid = int(pid_s)
        attempts_raw = row.get("attempts") or []
        state.products[pid] = ProductTerminalState(
            product_id=pid,
            final_status=row.get("final_status", "unresolved"),
            stop_search=bool(row.get("stop_search")),
            green=_restore_candidate(row.get("green")),
            best_yellow=_restore_candidate(row.get("best_yellow")),
            attempts=[c for c in (_restore_candidate(a) for a in attempts_raw) if c is not None],
        )
    state.url_cache.update(data.get("url_cache") or {})
    state.sha_assets.update(data.get("sha_assets") or {})
