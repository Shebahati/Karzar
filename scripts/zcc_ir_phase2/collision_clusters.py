"""Logical duplicate collision clusters (connected components)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LogicalCollisionCluster:
    cluster_id: str
    entry_indices: list[int]
    source_urls: list[str]
    reasons: list[str] = field(default_factory=list)

    @property
    def size(self) -> int:
        return len(self.entry_indices)


def _mfg_key(entry: dict[str, Any]) -> tuple[str, str] | None:
    identity = entry.get("source_identity") or {}
    brand = identity.get("brand")
    mfg = identity.get("manufacturer_code") or ""
    if brand and mfg:
        return str(brand), str(mfg)
    return None


def _sku_proposal(entry: dict[str, Any]) -> str | None:
    planned = entry.get("planned_fields") or {}
    sku = (planned.get("identity") or {}).get("sku_proposal")
    return str(sku) if sku else None


def _union_find_parent(parent: list[int], i: int) -> int:
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def _union(parent: list[int], a: int, b: int) -> None:
    ra, rb = _union_find_parent(parent, a), _union_find_parent(parent, b)
    if ra != rb:
        parent[rb] = ra


def build_logical_collision_clusters(entries: list[dict[str, Any]]) -> list[LogicalCollisionCluster]:
    """Connect entries sharing manufacturer identity OR proposed target SKU."""
    n = len(entries)
    parent = list(range(n))
    by_mfg: dict[tuple[str, str], list[int]] = {}
    by_sku: dict[str, list[int]] = {}

    for i, entry in enumerate(entries):
        key = _mfg_key(entry)
        if key:
            by_mfg.setdefault(key, []).append(i)
        sku = _sku_proposal(entry)
        if sku:
            by_sku.setdefault(sku, []).append(i)

    for indices in by_mfg.values():
        if len(indices) < 2:
            continue
        for j in range(1, len(indices)):
            _union(parent, indices[0], indices[j])

    for indices in by_sku.values():
        if len(indices) < 2:
            continue
        for j in range(1, len(indices)):
            _union(parent, indices[0], indices[j])

    buckets: dict[int, list[int]] = {}
    for i in range(n):
        root = _union_find_parent(parent, i)
        buckets.setdefault(root, []).append(i)

    clusters: list[LogicalCollisionCluster] = []
    cid = 0
    for indices in sorted(buckets.values(), key=lambda xs: min(xs)):
        if len(indices) < 2:
            continue
        cid += 1
        mfg_counts = Counter(_mfg_key(entries[i]) for i in indices)
        sku_counts = Counter(_sku_proposal(entries[i]) for i in indices)
        reasons: list[str] = []
        if any(count >= 2 for key, count in mfg_counts.items() if key):
            reasons.append("DUPLICATE_MANUFACTURER_IDENTITY")
        if any(count >= 2 for key, count in sku_counts.items() if key):
            reasons.append("DUPLICATE_TARGET_SKU")
        urls = [str(entries[i].get("source_url") or "") for i in indices]
        clusters.append(
            LogicalCollisionCluster(
                cluster_id=f"LOGICAL-{cid:04d}",
                entry_indices=sorted(indices),
                source_urls=sorted({u for u in urls if u}),
                reasons=reasons,
            )
        )
    return clusters


def index_to_cluster_id(clusters: list[LogicalCollisionCluster]) -> dict[int, str]:
    out: dict[int, str] = {}
    for cluster in clusters:
        for idx in cluster.entry_indices:
            out[idx] = cluster.cluster_id
    return out
