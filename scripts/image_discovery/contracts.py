"""Shared contracts for image discovery."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

ImageRole = Literal[
    "primary",
    "alternate",
    "detail",
    "display_or_scale_detail",
    "measuring_surface",
    "package",
    "included_accessories",
    "technical_diagram",
    "unknown",
]

IMAGE_ROLES: tuple[str, ...] = (
    "primary",
    "alternate",
    "detail",
    "display_or_scale_detail",
    "measuring_surface",
    "package",
    "included_accessories",
    "technical_diagram",
    "unknown",
)

Specificity = Literal["family", "singleton_unverified", "sku", "cross_brand_duplicate"]

MANIFEST_FIELDS: list[str] = [
    "candidate_id",
    "product_id",
    "product_key",
    "identity_basis",
    "source_candidate_key",
    "sku",
    "product_name",
    "brand",
    "source_adapter",
    "source_class",
    "image_role",
    "source_rank",
    "display_order_candidate",
    "source_image_index",
    "source_detail_url",
    "source_image_url",
    "final_image_url",
    "local_asset_path",
    "sha256",
    "mime_type",
    "extension",
    "byte_size",
    "width",
    "height",
    "foreground_occupancy_status",
    "presentation_note",
    "match_confidence",
    "sku_confirmed",
    "manufacturer_confirmed",
    "manufacturer_evidence",
    "sku_evidence",
    "page_subject_evidence",
    "image_specificity",
    "variant_specific",
    "shared_asset_group",
    "download_status",
    "review_status",
    "rights_status",
    "provenance_batch",
    "provenance_manifest",
    "provenance_source_adapter",
    "notes",
]

SEMANTIC_FIELDS: list[str] = [
    "candidate_id",
    "product_id",
    "product_key",
    "identity_basis",
    "source_candidate_key",
    "sku",
    "product_name",
    "brand",
    "source_adapter",
    "source_class",
    "image_role",
    "source_rank",
    "display_order_candidate",
    "source_image_index",
    "source_detail_url",
    "source_image_url",
    "final_image_url",
    "local_asset_path",
    "sha256",
    "mime_type",
    "extension",
    "byte_size",
    "width",
    "height",
    "foreground_occupancy_status",
    "presentation_note",
    "match_confidence",
    "sku_confirmed",
    "manufacturer_confirmed",
    "manufacturer_evidence",
    "sku_evidence",
    "page_subject_evidence",
    "image_specificity",
    "variant_specific",
    "shared_asset_group",
    "review_status",
    "rights_status",
    "provenance_batch",
    "provenance_manifest",
    "provenance_source_adapter",
]

REJECT_FIELDS: list[str] = [
    "candidate_id",
    "product_id",
    "product_key",
    "sku",
    "product_name",
    "brand",
    "stage",
    "reason_code",
    "reason_detail",
    "detail_url",
    "image_url",
    "http_status",
    "provenance_batch",
    "provenance_manifest",
    "provenance_source_adapter",
]

GROUP_FIELDS: list[str] = [
    "shared_asset_group",
    "sha256",
    "local_asset_path",
    "source_image_url",
    "sku_count",
    "skus",
    "brands",
    "image_specificity",
    "byte_size",
    "width",
    "height",
]

CONFLICT_FIELDS: list[str] = [
    "candidate_id",
    "reason_code",
    "batch_a",
    "batch_b",
    "manifest_a",
    "manifest_b",
    "source_adapter_a",
    "source_adapter_b",
    "semantic_sha_a",
    "semantic_sha_b",
    "detail",
]

CROSS_BRAND_FIELDS: list[str] = [
    "sha256",
    "brands",
    "skus",
    "candidate_ids",
    "shared_asset_group",
    "review_status",
    "notes",
]

PROVENANCE_OCCURRENCE_FIELDS: list[str] = [
    "candidate_id",
    "provenance_batch",
    "provenance_manifest",
    "provenance_source_adapter",
    "source_asset_path",
    "source_asset_sha256",
    "integrity_status",
]

HIGH_REUSE_FIELDS: list[str] = [
    "sha256",
    "brand",
    "product_key_count",
    "sku_count",
    "sku_prefix_count",
    "candidate_ids",
    "shared_asset_group",
    "review_status",
    "reason",
]

# Content fingerprint for duplicate/conflict decisions (excludes batch-local / derived / volatile).
CANDIDATE_CONTENT_FIELDS: list[str] = [
    "candidate_id",
    "product_id",
    "product_key",
    "identity_basis",
    "source_candidate_key",
    "sku",
    "product_name",
    "brand",
    "source_adapter",
    "source_class",
    "image_role",
    "source_rank",
    "display_order_candidate",
    "source_image_index",
    "source_detail_url",
    "source_image_url",
    "final_image_url",
    "sha256",
    "mime_type",
    "extension",
    "byte_size",
    "width",
    "height",
    "foreground_occupancy_status",
    "presentation_note",
    "match_confidence",
    "sku_confirmed",
    "manufacturer_confirmed",
    "manufacturer_evidence",
    "sku_evidence",
    "page_subject_evidence",
    "review_status",
    "rights_status",
]

# Default: same-brand SHA shared by more than this many distinct SKUs → high-reuse review signal.
HIGH_REUSE_SKU_THRESHOLD: int = 8


def normalize_identity_token(value: str) -> str:
    """NFKC + casefold + collapse whitespace for brand/SKU identity tokens."""
    text = unicodedata.normalize("NFKC", value or "")
    text = "".join(ch for ch in text if unicodedata.category(ch)[0] != "C")
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text


def build_product_identity(
    *,
    product_id: str = "",
    brand: str,
    sku: str,
) -> tuple[str, str, str]:
    """Return (product_id, product_key, identity_basis). Never treat bare SKU as global."""
    pid = (product_id or "").strip()
    if pid:
        return pid, f"product_id:{pid}", "product_id"
    nb = normalize_identity_token(brand)
    ns = normalize_identity_token(sku)
    return "", f"brand_sku:{nb}:{ns}", "brand_sku"


def derive_source_candidate_key(
    *,
    detail_url: str,
    image_url: str,
    source_image_index: int,
    extra: str = "",
) -> str:
    """Deterministic source identity (SHA-256 hex) — never Python hash()."""
    payload = "|".join(
        [
            (detail_url or "").strip(),
            (image_url or "").strip(),
            str(int(source_image_index)),
            (extra or "").strip(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def make_candidate_id(
    *,
    source_adapter: str,
    product_key: str,
    source_candidate_key: str,
    image_role: str,
) -> str:
    raw = "\0".join(
        [
            (source_adapter or "").strip(),
            (product_key or "").strip(),
            (source_candidate_key or "").strip(),
            (image_role or "").strip(),
        ]
    )
    return "cid:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


GOVERNED_IMAGE_ROLES: frozenset[str] = frozenset(IMAGE_ROLES)

REQUIRED_MANIFEST_FIELDS: tuple[str, ...] = (
    "candidate_id",
    "product_key",
    "identity_basis",
    "source_candidate_key",
    "sku",
    "brand",
    "source_adapter",
    "image_role",
    "source_detail_url",
    "source_image_url",
    "local_asset_path",
    "sha256",
    "review_status",
    "rights_status",
)

_CID_RE = re.compile(r"^cid:[0-9a-f]{64}$")
_SHA_RE = re.compile(r"^[0-9a-f]{64}$")


def normalize_sha256(value: str) -> str:
    return (value or "").strip().lower()


def validate_source_manifest_row(row: dict[str, Any]) -> str | None:
    """Return an integrity reason_code, or None when the row passes the source contract.

    Does not read assets — callers verify bytes separately against the declared SHA.
    """
    for req_field in REQUIRED_MANIFEST_FIELDS:
        val = row.get(req_field)
        if val is None or (isinstance(val, str) and not str(val).strip()):
            if req_field == "sha256":
                return "missing_manifest_sha256"
            if req_field == "candidate_id":
                return "missing_candidate_id"
            if req_field == "product_key":
                return "missing_product_key"
            if req_field == "source_candidate_key":
                return "missing_source_candidate_key"
            if req_field == "source_adapter":
                return "missing_source_adapter"
            return "missing_required_manifest_field"

    cid = str(row.get("candidate_id") or "").strip()
    if not _CID_RE.match(cid):
        return "invalid_candidate_id"

    sha = normalize_sha256(str(row.get("sha256") or ""))
    if not sha:
        return "missing_manifest_sha256"
    if not _SHA_RE.match(sha):
        return "invalid_manifest_sha256"

    role = str(row.get("image_role") or "").strip()
    if role not in GOVERNED_IMAGE_ROLES:
        return "invalid_image_role"

    expected = make_candidate_id(
        source_adapter=str(row.get("source_adapter") or ""),
        product_key=str(row.get("product_key") or ""),
        source_candidate_key=str(row.get("source_candidate_key") or ""),
        image_role=role,
    )
    if cid != expected:
        return "candidate_id_mismatch"

    return None


def row_semantic_fingerprint(row: dict[str, Any]) -> str:
    payload = {k: row.get(k) for k in SEMANTIC_FIELDS}
    blob = __import__("json").dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def candidate_content_fingerprint(row: dict[str, Any]) -> str:
    """Fingerprint for exact-duplicate vs conflict (excludes provenance / local path / derived)."""
    payload = {k: row.get(k) for k in CANDIDATE_CONTENT_FIELDS}
    blob = __import__("json").dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def fill_provenance(
    row: dict[str, Any],
    *,
    batch: str,
    manifest: str,
    adapter: str = "",
) -> dict[str, Any]:
    """Governed fallback: empty strings do not block filling."""
    out = dict(row)
    out["provenance_batch"] = (str(out.get("provenance_batch") or "").strip() or batch)
    out["provenance_manifest"] = (str(out.get("provenance_manifest") or "").strip() or manifest)
    out["provenance_source_adapter"] = (
        str(out.get("provenance_source_adapter") or "").strip()
        or str(out.get("source_adapter") or "").strip()
        or adapter
    )
    return out


@dataclass
class ImageCandidate:
    """One image candidate for a product (may be many per product)."""

    sku: str
    product_name: str
    brand: str
    detail_url: str
    image_url: str
    source_adapter: str
    source_class: str = "authorized_distributor_candidate"
    confidence: str = "very_high"
    image_role: str = "primary"
    source_rank: int = 1
    display_order_candidate: int = 1
    source_image_index: int = 0
    product_id: str = ""
    product_key: str = ""
    identity_basis: str = ""
    source_candidate_key: str = ""
    candidate_id: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def ensure_identity(self) -> str:
        pid, pkey, basis = build_product_identity(
            product_id=self.product_id, brand=self.brand, sku=self.sku
        )
        self.product_id = pid
        self.product_key = pkey
        self.identity_basis = basis
        if not self.source_candidate_key:
            self.source_candidate_key = derive_source_candidate_key(
                detail_url=self.detail_url,
                image_url=self.image_url,
                source_image_index=self.source_image_index,
                extra=str(self.extra.get("source_candidate_extra") or ""),
            )
        self.candidate_id = make_candidate_id(
            source_adapter=self.source_adapter,
            product_key=self.product_key,
            source_candidate_key=self.source_candidate_key,
            image_role=self.image_role,
        )
        return self.candidate_id

    def ensure_id(self) -> str:
        """Backward-compatible alias."""
        return self.ensure_identity()


@dataclass
class PageEvidence:
    manufacturer_confirmed: bool
    sku_confirmed: bool
    manufacturer_evidence: str
    sku_evidence: str
    page_subject_evidence: str
    reason_code: str = ""
    reason_detail: str = ""
    weak_review_only: bool = False


@dataclass
class RejectRecord:
    candidate_id: str
    sku: str
    product_name: str
    brand: str
    stage: str
    reason_code: str
    reason_detail: str
    detail_url: str
    image_url: str
    http_status: str | int = ""
    product_id: str = ""
    product_key: str = ""
    provenance_batch: str = ""
    provenance_manifest: str = ""
    provenance_source_adapter: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class DiscoveryError(Exception):
    def __init__(
        self,
        stage: str,
        reason_code: str,
        reason_detail: str,
        http_status: str | int = "",
    ) -> None:
        super().__init__(reason_detail)
        self.stage = stage
        self.reason_code = reason_code
        self.reason_detail = reason_detail
        self.http_status = http_status
