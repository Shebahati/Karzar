"""Governed OEM heading → Product Type + canonical title policy (Phase 2D exact gate)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

POLICY_CSV = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "architecture"
    / "specs"
    / "product-naming-v1"
    / "OEM_CANONICAL_IDENTITY_POLICY.csv"
)


@dataclass(frozen=True)
class OemCanonicalPolicyRow:
    oem_heading_or_family: str
    match_type: str
    allowed_product_type_code: str
    canonical_title_fa: str
    required_title_qualifier: str
    semantic_scope: str
    policy_status: str
    policy_basis: str


def normalize_oem_heading(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().upper())


def load_oem_canonical_policy(path: Path | None = None) -> dict[str, OemCanonicalPolicyRow]:
    src = path or POLICY_CSV
    out: dict[str, OemCanonicalPolicyRow] = {}
    if not src.is_file():
        return out
    with src.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            key = normalize_oem_heading(row.get("OEM_heading_or_family") or "")
            if not key:
                continue
            out[key] = OemCanonicalPolicyRow(
                oem_heading_or_family=key,
                match_type=(row.get("match_type") or "").strip(),
                allowed_product_type_code=(row.get("allowed_product_type_code") or "").strip(),
                canonical_title_fa=(row.get("canonical_title_fa") or "").strip(),
                required_title_qualifier=(row.get("required_title_qualifier") or "").strip(),
                semantic_scope=(row.get("semantic_scope") or "").strip(),
                policy_status=(row.get("policy_status") or "").strip(),
                policy_basis=(row.get("policy_basis") or "").strip(),
            )
    return out


@lru_cache(maxsize=1)
def default_oem_canonical_policy() -> dict[str, OemCanonicalPolicyRow]:
    return load_oem_canonical_policy()


def _heading_lookup_keys(oem_heading: str) -> list[str]:
    key = normalize_oem_heading(oem_heading)
    alt = key.replace(" AND SLOPE METER", " AND SLOPE METERS")
    keys = [key]
    if alt != key:
        keys.append(alt)
    if key.endswith("S") and key[:-1] in keys:
        keys.append(key[:-1])
    return keys


def lookup_policy(
    oem_heading: str,
    policies: dict[str, OemCanonicalPolicyRow] | None = None,
) -> OemCanonicalPolicyRow | None:
    pol = policies if policies is not None else default_oem_canonical_policy()
    for key in _heading_lookup_keys(oem_heading):
        row = pol.get(key)
        if row and row.policy_status == "APPROVED":
            return row
    return None
