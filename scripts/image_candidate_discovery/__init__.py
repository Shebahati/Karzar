"""Governed brand image candidate discovery (IMG-02B-02..04)."""

from __future__ import annotations

SCHEMA_VERSION = 1
TASK_ID = "IMG-02B"

CANDIDATE_FIELDS: list[str] = [
    "schema_version",
    "task_id",
    "lane_id",
    "product_id",
    "product_key",
    "sku",
    "product_name",
    "brand_key",
    "work_type",
    "work_reasons",
    "priority",
    "source_adapter",
    "source_class",
    "source_detail_url",
    "source_image_url",
    "source_image_index",
    "candidate_discovery_method",
    "candidate_match_basis",
    "manufacturer_evidence",
    "sku_evidence",
    "confidence",
    "rights_status",
    "apply_status",
    "discovery_status",
    "notes",
]

LANE_SPECS: dict[str, dict[str, str]] = {
    "dasqua": {
        "lane_id": "IMG-02B-02",
        "adapter": "dasqua_official",
        "brand_key": "dasqua",
        "source_class": "official_manufacturer",
        "worklist": "worklist-dasqua.csv",
    },
    "insize": {
        "lane_id": "IMG-02B-03",
        "adapter": "insize_tosag",
        "brand_key": "insize",
        "source_class": "authorized_distributor_candidate",
        "worklist": "worklist-insize.csv",
    },
    "san_ou": {
        "lane_id": "IMG-02B-04",
        "adapter": "sanou_official",
        "brand_key": "san_ou",
        "source_class": "official_manufacturer",
        "worklist": "worklist-san-ou.csv",
    },
}

# Dasqua product HTML lives on dasquatools.com; official product images are
# served from GlobalSo CDNs referenced by those pages (legacy importer evidence:
# scripts/import_dasqua_images_from_official.py extract_image).
_DASQUA_CDN_HOSTS = frozenset(
    {"cdn.globalso.com", *[f"ecdn{i}.globalso.com" for i in range(1, 16)]}
)

ALLOWED_HOSTS: dict[str, frozenset[str]] = {
    "dasqua": frozenset({"www.dasquatools.com", "dasquatools.com"}) | _DASQUA_CDN_HOSTS,
    "insize": frozenset({"www.tosag.ch", "tosag.ch"}),
    "san_ou": frozenset({"www.sanouchuck.com", "sanouchuck.com", "en.sanouchuck.com"}),
}


class CandidateDiscoveryError(Exception):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(f"{stage}: {message}")
        self.stage = stage
        self.message = message
