"""Discover approved Target Catalog sources under a configurable root.

Never treats repository legacy extracts (PDF parses, shopmill crawls, PR #266
pilot allowlists) as product-scope authority. Missing files are reported, not
guessed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from catalog_target.core import (
    SourceFile,
    TargetSku,
    canonicalize_brand,
    detect_markup_percent,
    normalize_sku,
)
from catalog_target.xlsx import iter_xlsx_rows

REGISTRY_PATH = Path(__file__).with_name("source_registry.json")
TABULAR_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xlsm"}

# Legacy repo artifacts that must never become Target membership authority.
LEGACY_NON_AUTHORITY = (
    "data/imports/insize_products.csv",
    "data/imports/dasqua_products.csv",
    "data/imports/all_products.csv",
    "scripts/fixtures/insize_pilot_manifest_synthetic.json",
)


def load_registry(path: Path | None = None) -> dict[str, Any]:
    target = path or REGISTRY_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def resolve_source_root(
    cli_root: str | Path | None = None,
    *,
    env: dict[str, str] | None = None,
) -> Path | None:
    environ = env if env is not None else os.environ
    raw = str(cli_root).strip() if cli_root else environ.get("KARZAR_TARGET_SOURCE_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    if not path.is_dir():
        return None
    return path.resolve()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _glob_files(root: Path, patterns: Iterable[str]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for match in root.glob(pattern):
            if not match.is_file():
                continue
            resolved = match.resolve()
            if resolved.suffix.lower() not in TABULAR_SUFFIXES and resolved.suffix.lower() not in {
                ".json",
                ".jsonl",
            }:
                if resolved.suffix.lower() not in {".csv", ".tsv", ".xlsx", ".xlsm"}:
                    continue
            if resolved not in seen:
                seen.add(resolved)
                found.append(resolved)
    return sorted(found)


def read_tabular(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return iter_xlsx_rows(path)
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            return [row for row in payload["rows"] if isinstance(row, dict)]
        return []
    if suffix == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        return rows
    dialect_delim = "\t" if suffix == ".tsv" else ","
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=dialect_delim)
        return [{k: v for k, v in row.items() if k is not None} for row in reader]


def pick_header(row: dict[str, Any], candidates: Iterable[str]) -> str | None:
    lowered = {str(k).strip().lower(): k for k in row if k}
    for name in candidates:
        if name in row and row[name] not in (None, ""):
            return name
        key = lowered.get(name.lower())
        if key is not None and row.get(key) not in (None, ""):
            return key
    return None


def extract_sku(row: dict[str, Any], sku_headers: list[str]) -> str:
    header = pick_header(row, sku_headers)
    if header is None:
        return ""
    return str(row.get(header) or "").strip()


class SourceDiscovery:
    def __init__(
        self,
        *,
        source_root: Path | None,
        registry: dict[str, Any] | None = None,
    ) -> None:
        self.source_root = source_root
        self.registry = registry or load_registry()
        self.files: list[SourceFile] = []
        self.parse_failures: list[dict[str, str]] = []
        self.unavailable: list[dict[str, str]] = []

    def discover(self) -> None:
        scopes: list[dict[str, Any]] = list(self.registry.get("approved_scopes") or [])
        if self.source_root is None:
            self.unavailable.append(
                {
                    "source": "KARZAR_TARGET_SOURCE_DIR",
                    "reason": "source_root_unset_or_missing",
                }
            )
            for scope in scopes:
                self.unavailable.append(
                    {
                        "source": f"{scope.get('brand')}/{scope.get('product_family')}",
                        "reason": "source_root_unavailable",
                    }
                )
            self._record_insize_unavailable()
            return

        self._discover_insize()
        seen_non_insize: set[Path] = set()
        for scope in scopes:
            brand = str(scope.get("brand") or "")
            family = str(scope.get("product_family") or "")
            if brand == "INSIZE":
                continue
            hints = [brand, *(scope.get("aliases") or []), *(scope.get("folder_hints") or [])]
            matches = self._files_for_hints(hints)
            if not matches:
                self.unavailable.append(
                    {
                        "source": f"{brand}/{family}",
                        "reason": "authoritative_source_file_unavailable",
                    }
                )
                continue
            for path in matches:
                if path in seen_non_insize:
                    continue
                roles = self._roles_for_path(path)
                if "product_scope" in roles and ("price" in roles or "inventory" in roles):
                    self.parse_failures.append(
                        {
                            "path": str(path),
                            "reason": "conflicting_authoritative_roles",
                        }
                    )
                    continue
                if "product_scope" in roles:
                    role = "product_scope"
                elif "price" in roles and "inventory" in roles:
                    role = "price_inventory"
                elif "price" in roles:
                    role = "price"
                elif "inventory" in roles:
                    role = "inventory"
                elif "catalog" in roles:
                    role = "catalog"
                elif "media" in roles:
                    role = "media"
                else:
                    continue
                seen_non_insize.add(path)
                self.files.append(
                    SourceFile(
                        path=str(path),
                        brand_key=canonicalize_brand(brand),
                        role=role,
                        available=True,
                        sha256=file_sha256(path),
                        markup_percent=detect_markup_percent(path.name),
                    )
                )

    def _record_insize_unavailable(self) -> None:
        self.unavailable.extend(
            [
                {
                    "source": "INSIZE/product_scope",
                    "reason": "authoritative_source_file_unavailable",
                },
                {
                    "source": "INSIZE/distributor_price_inventory",
                    "reason": "authoritative_source_file_unavailable",
                },
            ]
        )

    def _roles_for_path(self, path: Path) -> set[str]:
        assert self.source_root is not None
        rel = path.relative_to(self.source_root).as_posix().lower()
        name = path.name.lower()
        roles: set[str] = set()
        for role, patterns in (self.registry.get("role_globs") or {}).items():
            for pattern in patterns:
                tokens = [t for t in pattern.lower().replace("**/", "").split("*") if t]
                if tokens and all(t in rel or t in name for t in tokens):
                    roles.add(role)
                    break
        return roles

    def _files_for_hints(self, hints: list[str]) -> list[Path]:
        assert self.source_root is not None
        found: list[Path] = []
        for hint in hints:
            needle = str(hint).strip().lower()
            if not needle:
                continue
            for path in self.source_root.rglob("*"):
                if not path.is_file() or path.suffix.lower() not in TABULAR_SUFFIXES | {".json", ".jsonl"}:
                    continue
                blob = str(path.relative_to(self.source_root)).lower()
                if needle.lower() in blob:
                    found.append(path)
        return sorted(set(found))

    def _discover_insize(self) -> None:
        assert self.source_root is not None
        cfg = self.registry.get("insize") or {}
        product_files = _glob_files(self.source_root, cfg.get("product_scope_globs") or [])
        distributor_files = _glob_files(self.source_root, cfg.get("distributor_globs") or [])
        overlap = set(product_files) & set(distributor_files)
        if overlap:
            for path in sorted(overlap):
                self.parse_failures.append(
                    {
                        "path": str(path),
                        "reason": "insize_product_scope_overlaps_distributor",
                    }
                )
            product_files = [p for p in product_files if p not in overlap]

        if not product_files:
            self.unavailable.append(
                {
                    "source": "INSIZE/product_scope",
                    "reason": "authoritative_source_file_unavailable",
                }
            )
        for path in product_files:
            self.files.append(
                SourceFile(
                    path=str(path),
                    brand_key="INSIZE",
                    role="product_scope",
                    available=True,
                    sha256=file_sha256(path),
                    markup_percent=detect_markup_percent(path.name),
                )
            )
        if not distributor_files:
            self.unavailable.append(
                {
                    "source": "INSIZE/distributor_price_inventory",
                    "reason": "authoritative_source_file_unavailable",
                }
            )
        for path in distributor_files:
            role = "price_inventory"
            self.files.append(
                SourceFile(
                    path=str(path),
                    brand_key="INSIZE",
                    role=role,
                    available=True,
                    sha256=file_sha256(path),
                    markup_percent=detect_markup_percent(path.name),
                )
            )

    def load_product_scope_targets(self) -> list[TargetSku]:
        """Membership comes only from product_scope files, never price/inventory."""
        targets: list[TargetSku] = []
        sku_headers = list(
            (self.registry.get("insize") or {}).get("sku_headers")
            or self.registry.get("sku_headers")
            or ["sku", "CODE"]
        )
        family_headers = list(self.registry.get("family_headers") or ["product_family"])
        brand_headers = list(self.registry.get("brand_headers") or ["brand"])
        for source in self.files:
            if source.role != "product_scope":
                continue
            path = Path(source.path)
            posix = path.as_posix()
            if any(posix.endswith(rel) or f"/{rel}" in posix for rel in LEGACY_NON_AUTHORITY):
                self.parse_failures.append(
                    {
                        "path": str(path),
                        "reason": "legacy_repo_artifact_not_product_scope_authority",
                    }
                )
                continue
            try:
                rows = read_tabular(path)
            except Exception as exc:  # noqa: BLE001 — record parser failure, do not guess
                self.parse_failures.append({"path": str(path), "reason": f"parse_failure:{exc}"})
                continue
            source.row_count = len(rows)
            for row in rows:
                sku = extract_sku(row, sku_headers)
                if not sku:
                    self.parse_failures.append(
                        {"path": str(path), "reason": "malformed_source_missing_sku"}
                    )
                    continue
                brand_header = pick_header(row, brand_headers)
                brand_raw = str(row.get(brand_header) or source.brand_key or "")
                brand_key = canonicalize_brand(brand_raw) or source.brand_key or ""
                family_header = pick_header(row, family_headers)
                family = str(row.get(family_header) or "unspecified")
                targets.append(
                    TargetSku(
                        brand=brand_raw or brand_key,
                        brand_key=brand_key,
                        sku=sku,
                        normalized_sku=normalize_sku(sku),
                        product_family=family,
                        source_scope=source.role,
                        source_product=str(path),
                        provenance=source.sha256,
                    )
                )
        return targets

    def load_role_rows(self, role: str) -> list[tuple[SourceFile, dict[str, Any]]]:
        out: list[tuple[SourceFile, dict[str, Any]]] = []
        for source in self.files:
            if source.role != role and not (
                role in {"price", "inventory"} and source.role == "price_inventory"
            ):
                continue
            path = Path(source.path)
            try:
                rows = read_tabular(path)
            except Exception as exc:  # noqa: BLE001
                self.parse_failures.append({"path": str(path), "reason": f"parse_failure:{exc}"})
                continue
            source.row_count = len(rows)
            for row in rows:
                out.append((source, row))
        return out
