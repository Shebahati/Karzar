"""Operation-aware collision semantics (forensic vs mutation-blocking)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

from zcc_ir_phase2.collision_clusters import (
    LogicalCollisionCluster,
    build_logical_collision_clusters,
)

MUTATION_BEARING_OPERATIONS = frozenset({"CREATE_PLAN", "UPDATE_CONTENT_PLAN"})
FORENSIC_OPERATIONS = frozenset({"NOOP", "HOLD"})


def canonical_source_url(url: str) -> str:
    """Normalize URL path (decode percent-encoding, trailing slash) for alias detection."""
    parsed = urlparse(url.strip())
    netloc = (parsed.netloc or "").lower()
    path = unquote(parsed.path or "/")
    if not path.endswith("/"):
        path = path + "/"
    scheme = (parsed.scheme or "https").lower()
    return f"{scheme}://{netloc}{path}"


def cluster_has_encoding_alias_urls(cluster: LogicalCollisionCluster, entries: list[dict[str, Any]]) -> bool:
    """True when multiple distinct raw URLs collapse to one canonical URL representation."""
    raw_urls = [
        str(entries[i].get("source_url") or "")
        for i in cluster.entry_indices
        if entries[i].get("source_url")
    ]
    unique_raw = set(raw_urls)
    if len(unique_raw) < 2:
        return False
    canonical = {canonical_source_url(u) for u in unique_raw}
    return len(canonical) == 1


def cluster_is_mutation_blocking(cluster: LogicalCollisionCluster, entries: list[dict[str, Any]]) -> bool:
    for idx in cluster.entry_indices:
        if entries[idx].get("operation") in MUTATION_BEARING_OPERATIONS:
            return True
    return False


def classify_collision_kind(
    entry: dict[str, Any],
    cluster: LogicalCollisionCluster,
    entries: list[dict[str, Any]],
) -> str:
    if cluster_has_encoding_alias_urls(cluster, entries):
        return "ENCODING_DUPLICATE"
    flags = entry.get("blocking_flags") or []
    if "ambiguous_match" in flags:
        return "TRUE_IDENTITY_CONFLICT"
    op = entry.get("operation")
    target = entry.get("target_identity") or {}
    karzar_id = entry.get("karzar_product_id") or target.get("karzar_id")
    if karzar_id and op in FORENSIC_OPERATIONS and cluster_is_mutation_blocking(cluster, entries):
        return "KARZAR_EXISTING_DUPLICATE"
    if karzar_id and op in FORENSIC_OPERATIONS:
        return "NOOP_EXISTING_MATCH"
    if op in MUTATION_BEARING_OPERATIONS:
        return "MUTATION_IDENTITY_COLLISION"
    return "SOURCE_QUALITY_FORENSIC"


@dataclass
class CollisionImpactSummary:
    all_logical_clusters: list[LogicalCollisionCluster]
    mutation_blocking_clusters: list[LogicalCollisionCluster]

    @property
    def ALL_MANIFEST_LOGICAL_COLLISION_GROUPS(self) -> int:
        return len(self.all_logical_clusters)

    @property
    def ALL_MANIFEST_COLLISION_AFFECTED_ROWS(self) -> int:
        urls: set[str] = set()
        for cluster in self.all_logical_clusters:
            urls.update(cluster.source_urls)
        return len(urls)

    @property
    def MUTATION_BLOCKING_COLLISION_GROUPS(self) -> int:
        return len(self.mutation_blocking_clusters)

    @property
    def MUTATION_BLOCKING_AFFECTED_ROWS(self) -> int:
        urls: set[str] = set()
        for cluster in self.mutation_blocking_clusters:
            urls.update(cluster.source_urls)
        return len(urls)

    def create_blocking_urls(self, entries: list[dict[str, Any]]) -> set[str]:
        blocked: set[str] = set()
        for cluster in self.mutation_blocking_clusters:
            for idx in cluster.entry_indices:
                if entries[idx].get("operation") == "CREATE_PLAN":
                    url = entries[idx].get("source_url")
                    if url:
                        blocked.add(str(url))
        return blocked

    def update_blocking_urls(self, entries: list[dict[str, Any]]) -> set[str]:
        blocked: set[str] = set()
        for cluster in self.mutation_blocking_clusters:
            for idx in cluster.entry_indices:
                if entries[idx].get("operation") == "UPDATE_CONTENT_PLAN":
                    url = entries[idx].get("source_url")
                    if url:
                        blocked.add(str(url))
        return blocked

    @property
    def CONTENT_SOURCE_QUALITY_VALID(self) -> bool:
        return self.ALL_MANIFEST_LOGICAL_COLLISION_GROUPS == 0

    @property
    def CONTENT_MUTATION_PLAN_VALID(self) -> bool:
        return self.MUTATION_BLOCKING_COLLISION_GROUPS == 0

    def as_dict(self, entries: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "ALL_MANIFEST_LOGICAL_COLLISION_GROUPS": self.ALL_MANIFEST_LOGICAL_COLLISION_GROUPS,
            "ALL_MANIFEST_COLLISION_AFFECTED_ROWS": self.ALL_MANIFEST_COLLISION_AFFECTED_ROWS,
            "MUTATION_BLOCKING_COLLISION_GROUPS": self.MUTATION_BLOCKING_COLLISION_GROUPS,
            "MUTATION_BLOCKING_AFFECTED_ROWS": self.MUTATION_BLOCKING_AFFECTED_ROWS,
            "CREATE_BLOCKING_COLLISION_ROWS": len(self.create_blocking_urls(entries)),
            "UPDATE_BLOCKING_COLLISION_ROWS": len(self.update_blocking_urls(entries)),
            "CONTENT_SOURCE_QUALITY_VALID": self.CONTENT_SOURCE_QUALITY_VALID,
            "CONTENT_MUTATION_PLAN_VALID": self.CONTENT_MUTATION_PLAN_VALID,
            "forensic_only_cluster_count": (
                self.ALL_MANIFEST_LOGICAL_COLLISION_GROUPS - self.MUTATION_BLOCKING_COLLISION_GROUPS
            ),
        }


def summarize_collision_impact(entries: list[dict[str, Any]]) -> CollisionImpactSummary:
    all_clusters = build_logical_collision_clusters(entries)
    mutation_blocking = [c for c in all_clusters if cluster_is_mutation_blocking(c, entries)]
    return CollisionImpactSummary(
        all_logical_clusters=all_clusters,
        mutation_blocking_clusters=mutation_blocking,
    )
