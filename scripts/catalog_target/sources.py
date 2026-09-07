"""Discover approved Target Catalog sources under KARZAR_TARGET_SOURCE_DIR.

Authority is the explicit registry, not generic filename guessing.
Price lists do not become membership unless the registry assigns product_scope.
INSIZE distributor workbooks never define the product universe.
AST family folders do not make every PDF a product_scope source.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from catalog_target.core import (
    SourceFile,
    TargetSku,
    canonicalize_brand,
    detect_markup_percent,
    fold_token,
    normalize_sku,
    parse_decimal,
)
from catalog_target.pdf import extract_pdf_row_parse, extract_pdf_text
from catalog_target.xlsx import iter_xlsx_rows, read_xlsx_cell

REGISTRY_PATH = Path(__file__).with_name("source_registry.json")
TABULAR_SUFFIXES = {".csv", ".tsv", ".xlsx", ".xlsm"}
PDF_SUFFIXES = {".pdf"}
JSON_SUFFIXES = {".json", ".jsonl"}
MEDIA_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}
SKIP_FILE_NAMES = {"thumbs.db", "desktop.ini", ".ds_store"}

LEGACY_NON_AUTHORITY = (
    "data/imports/insize_products.csv",
    "data/imports/dasqua_products.csv",
    "data/imports/all_products.csv",
    "scripts/fixtures/insize_pilot_manifest_synthetic.json",
)


def load_registry(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or REGISTRY_PATH).read_text(encoding="utf-8"))


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


def describe_source_root(cli_root: str | Path | None = None, *, env: dict[str, str] | None = None) -> dict[str, str]:
    environ = env if env is not None else os.environ
    raw = str(cli_root).strip() if cli_root else environ.get("KARZAR_TARGET_SOURCE_DIR", "").strip()
    if not raw:
        return {
            "raw": "",
            "resolved": "",
            "exists": "false",
            "status": "BLOCKED_SOURCE_NOT_MOUNTED",
        }
    path = Path(raw).expanduser()
    exists = path.is_dir()
    return {
        "raw": raw,
        "resolved": str(path.resolve()) if exists or path.exists() else str(path.resolve()),
        "exists": "true" if exists else "false",
        "status": "ok" if exists else "BLOCKED_SOURCE_NOT_MOUNTED",
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pick_header(row: dict[str, Any], candidates: list[str]) -> str | None:
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
    delim = "\t" if suffix == ".tsv" else ","
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delim)
        return [{k: v for k, v in row.items() if k is not None} for row in reader]


def _path_parts(root: Path, path: Path) -> tuple[str, ...]:
    try:
        return path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return path.parts


def in_duplicate_tree(root: Path, path: Path, markers: list[str]) -> bool:
    folded_markers = {fold_token(m) for m in markers}
    return any(fold_token(part) in folded_markers for part in _path_parts(root, path))


def _folder_in_path(parts: tuple[str, ...], wanted: str | None) -> bool:
    if not wanted:
        return True
    needle = fold_token(wanted)
    return any(fold_token(p) == needle for p in parts)


def _ast_family_match(parts: tuple[str, ...], names: list[str]) -> str | None:
    folded_parts = [fold_token(p) for p in parts]
    if any(p in names for p in folded_parts):
        return "exact"
    if any(n and any(n in p for p in folded_parts) for n in names if n):
        return "contains"
    return None


def _ast_family_score(parts: tuple[str, ...], names: list[str]) -> tuple[int, int] | None:
    kind = _ast_family_match(parts, names)
    if not kind:
        return None
    folded_parts = [fold_token(p) for p in parts]
    namelen = 0
    for n in names:
        if not n:
            continue
        if n in folded_parts:
            namelen = max(namelen, len(n))
        elif any(n in p for p in folded_parts):
            namelen = max(namelen, len(n))
    return (1 if kind == "exact" else 0, namelen)


def _filename_contains_any(name: str, needles: list[str]) -> bool:
    folded = fold_token(name)
    return any(fold_token(item) and fold_token(item) in folded for item in needles)


def _filename_matches(name: str, spec: dict[str, Any]) -> bool:
    equals = spec.get("filename_equals") or []
    contains = spec.get("filename_contains") or []
    if not equals and not contains:
        return True
    folded = fold_token(name)
    for item in equals:
        if folded == fold_token(item):
            return True
    for item in contains:
        if fold_token(item) and fold_token(item) in folded:
            return True
    return False


def spec_matches_path(root: Path, path: Path, spec: dict[str, Any]) -> bool:
    parts = _path_parts(root, path)
    if not _folder_in_path(parts, spec.get("parent_folder")):
        return False
    if not _folder_in_path(parts, spec.get("ancestor_folder")):
        return False
    return _filename_matches(path.name, spec)


def source_has_role(source: SourceFile, role: str) -> bool:
    roles = source.roles or ([source.role] if source.role else [])
    if role in roles:
        return True
    if role in {"price", "inventory"} and "price_inventory" in roles:
        return True
    if role in {"price", "inventory"} and source.role == "price_inventory":
        return True
    return False


def ast_roles_for_file(path: Path, registry: dict[str, Any]) -> tuple[list[str], str, str]:
    """Fail closed: family folder is not enough. Enumerators are explicit."""
    suffix = path.suffix.lower()
    rules = registry.get("ast_enumerators") or {}
    enumerators = list(rules.get("product_scope_price_filename_contains") or [])
    catalogs = list(rules.get("catalog_filename_contains") or [])
    if suffix in MEDIA_SUFFIXES:
        return ["media"], "none", "ok"
    if _filename_contains_any(path.name, enumerators):
        if suffix in PDF_SUFFIXES:
            return ["product_scope", "price"], "pdf_sku_price", "ok"
        if suffix in TABULAR_SUFFIXES | JSON_SUFFIXES:
            return ["product_scope", "price"], "tabular", "ok"
        return ["unclassified"], "none", "unclassified"
    if suffix in PDF_SUFFIXES and _filename_contains_any(path.name, catalogs):
        return ["catalog"], "none", "ok"
    if suffix in PDF_SUFFIXES:
        return ["unclassified"], "none", "unclassified"
    if suffix in TABULAR_SUFFIXES | JSON_SUFFIXES:
        return ["unclassified"], "none", "unclassified"
    return ["catalog"], "none", "ok"


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
        self.unparsed: list[dict[str, str]] = []
        self.discovered: list[dict[str, str]] = []
        self.skipped_duplicates: list[str] = []
        self.hash_conflicts: list[dict[str, str]] = []
        self.duplicate_scope_skus: list[str] = []
        self.rejected_examples: dict[str, list[str]] = {}
        self.brand_parse: dict[str, dict[str, Any]] = {}
        self._row_cache: dict[str, list[dict[str, Any]]] = {}

    def discover(self) -> None:
        if self.source_root is None:
            self.unavailable.append(
                {"source": "KARZAR_TARGET_SOURCE_DIR", "reason": "source_root_unset_or_missing"}
            )
            for spec in self.registry.get("sources") or []:
                self.unavailable.append(
                    {"source": spec.get("id", ""), "reason": "source_root_unavailable"}
                )
            for family in self.registry.get("ast_families") or []:
                self.unavailable.append(
                    {
                        "source": f"ASTPOWER/{family.get('product_family')}",
                        "reason": "source_root_unavailable",
                    }
                )
            return

        skip_names = {fold_token(n) for n in SKIP_FILE_NAMES}
        files = [
            p
            for p in self.source_root.rglob("*")
            if p.is_file() and fold_token(p.name) not in skip_names
        ]
        dup_markers = list(self.registry.get("duplicate_trees") or [])
        claimed: set[Path] = set()

        for spec in self.registry.get("sources") or []:
            matches = [p for p in files if spec_matches_path(self.source_root, p, spec.get("match") or {})]
            if not matches:
                if spec.get("product_scope_status"):
                    self.unavailable.append(
                        {
                            "source": spec.get("id", ""),
                            "reason": spec.get("product_scope_status", "authoritative_source_file_unavailable"),
                        }
                    )
                else:
                    self.unavailable.append(
                        {
                            "source": spec.get("id", ""),
                            "reason": "authoritative_source_file_unavailable",
                        }
                    )
                continue
            chosen = self._prefer_originals(matches, dup_markers)
            if spec.get("id") == "insize.distributor" and len(chosen) > 1:
                chosen = self._prefer_single_workbook(chosen)
            for path in chosen:
                self._register_file(path, spec)
                claimed.add(path.resolve())
            roles = list(spec.get("roles") or [])
            if spec.get("product_scope_status") and "product_scope" not in roles:
                self.unavailable.append(
                    {
                        "source": spec.get("id", ""),
                        "reason": str(spec.get("product_scope_status")),
                    }
                )

        self._discover_ast_families(files, claimed, dup_markers)

    def _prefer_originals(self, matches: list[Path], dup_markers: list[str]) -> list[Path]:
        originals = [p for p in matches if not in_duplicate_tree(self.source_root, p, dup_markers)]
        copies = [p for p in matches if in_duplicate_tree(self.source_root, p, dup_markers)]
        chosen = list(originals)
        original_by_name: dict[str, Path] = {fold_token(p.name): p for p in originals}
        seen_names = set(original_by_name)
        for path in copies:
            key = fold_token(path.name)
            if key in original_by_name:
                original = original_by_name[key]
                try:
                    copy_hash = file_sha256(path)
                    orig_hash = file_sha256(original)
                except OSError as exc:
                    self.hash_conflicts.append(
                        {
                            "name": path.name,
                            "original": str(original),
                            "copy": str(path),
                            "reason": f"hash_unreadable:{exc}",
                        }
                    )
                    continue
                if copy_hash == orig_hash:
                    self.skipped_duplicates.append(str(path))
                    continue
                self.hash_conflicts.append(
                    {
                        "name": path.name,
                        "original": str(original),
                        "copy": str(path),
                        "original_sha256": orig_hash,
                        "copy_sha256": copy_hash,
                        "reason": "same_name_different_hash",
                    }
                )
                continue
            if key in seen_names:
                self.skipped_duplicates.append(str(path))
                continue
            chosen.append(path)
            seen_names.add(key)
        return chosen

    def _prefer_single_workbook(self, matches: list[Path]) -> list[Path]:
        """One INSIZE distributor workbook is join authority; extra copies must not duplicate-match."""
        preferred = [p for p in matches if "sheet1" in fold_token(p.name)]
        pick = preferred[0] if preferred else sorted(matches, key=lambda p: p.name)[0]
        pick_hash = file_sha256(pick)
        for other in matches:
            if other.resolve() == pick.resolve():
                continue
            try:
                other_hash = file_sha256(other)
            except OSError as exc:
                self.hash_conflicts.append(
                    {
                        "name": other.name,
                        "original": str(pick),
                        "copy": str(other),
                        "reason": f"hash_unreadable:{exc}",
                    }
                )
                continue
            if other_hash == pick_hash:
                self.skipped_duplicates.append(str(other))
            else:
                self.hash_conflicts.append(
                    {
                        "name": other.name,
                        "original": str(pick),
                        "copy": str(other),
                        "original_sha256": pick_hash,
                        "copy_sha256": other_hash,
                        "reason": "same_logical_source_different_hash",
                    }
                )
                self.skipped_duplicates.append(str(other))
        return [pick]

    def _register_file(self, path: Path, spec: dict[str, Any]) -> None:
        roles = list(spec.get("roles") or [])
        if spec.get("never_product_scope"):
            roles = [r for r in roles if r != "product_scope"]
        primary = roles[0] if roles else "catalog"
        markup = detect_markup_percent(path.name, spec.get("id"))
        if spec.get("markup_already_present") and markup is None:
            markup = detect_markup_percent(path.name)
        source = SourceFile(
            path=str(path),
            brand_key=canonicalize_brand(str(spec.get("brand") or "")),
            role=primary,
            available=True,
            sha256=file_sha256(path),
            markup_percent=markup,
            roles=roles,
            source_id=str(spec.get("id") or ""),
            product_family=str(spec.get("product_family") or ""),
            currency=spec.get("source_currency"),
            membership_mode=str(spec.get("membership_mode") or "authoritative"),
            parse_status=str(spec.get("parse_status") or "ok"),
        )
        parser = spec.get("parser")
        if parser in {"pdf_sku", "pdf_sku_price", "pdf_or_media"} and path.suffix.lower() == ".pdf":
            extracted = extract_pdf_text(path)
            if not extracted.ok:
                source.parse_status = extracted.status
                source.available = extracted.status == "ok"
                self.unparsed.append(
                    {
                        "path": str(path),
                        "source_id": source.source_id,
                        "reason": extracted.error or extracted.status,
                    }
                )
                if "product_scope" in roles:
                    self.parse_failures.append(
                        {
                            "path": str(path),
                            "reason": f"pdf_{extracted.status}:{extracted.error or 'no_text'}",
                        }
                    )
        self.files.append(source)
        self.discovered.append(
            {
                "path": str(path),
                "source_id": source.source_id,
                "roles": ",".join(roles),
                "parse_status": source.parse_status,
            }
        )

    def _discover_ast_families(
        self,
        files: list[Path],
        claimed: set[Path],
        dup_markers: list[str],
    ) -> None:
        assert self.source_root is not None
        families = list(self.registry.get("ast_families") or [])
        buckets: dict[str, list[Path]] = {str(f.get("id") or f.get("product_family")): [] for f in families}
        for path in files:
            if path.resolve() in claimed:
                continue
            parts = _path_parts(self.source_root, path)
            if not _folder_in_path(parts, "آذرصنعت"):
                continue
            best_family = None
            best_score = (-1, -1)
            for family in families:
                names = [fold_token(n) for n in (family.get("folder_names") or [])]
                score = _ast_family_score(parts, names)
                if score is None:
                    continue
                if score > best_score:
                    best_score = score
                    best_family = family
            if best_family is None:
                continue
            fid = str(best_family.get("id") or best_family.get("product_family"))
            buckets[fid].append(path)
        for family in families:
            fid = str(family.get("id") or family.get("product_family"))
            matched = buckets.get(fid) or []
            if not matched:
                names = [fold_token(n) for n in (family.get("folder_names") or [])]
                present = any(
                    _folder_in_path(_path_parts(self.source_root, path), "آذرصنعت")
                    and _ast_family_match(_path_parts(self.source_root, path), names)
                    for path in files
                )
                self.unavailable.append(
                    {
                        "source": f"ASTPOWER/{family.get('product_family')}",
                        "reason": (
                            "ast_family_present_but_no_approved_enumerator"
                            if present
                            else "authoritative_source_file_unavailable"
                        ),
                    }
                )
                continue
            saw_enumerator = False
            for path in self._prefer_originals(matched, dup_markers):
                roles, parser, parse_status = ast_roles_for_file(path, self.registry)
                if "product_scope" in roles:
                    saw_enumerator = True
                spec = {
                    "id": fid,
                    "brand": "ASTPOWER",
                    "product_family": family.get("product_family"),
                    "roles": roles,
                    "parser": parser,
                    "parse_status": parse_status,
                    "source_currency": "rial",
                    "sku_kind": "generic",
                    "membership_mode": "review_if_weak" if parse_status == "unclassified" else "authoritative",
                }
                self._register_file(path, spec)
                claimed.add(path.resolve())
            if not saw_enumerator:
                self.unavailable.append(
                    {
                        "source": f"ASTPOWER/{family.get('product_family')}",
                        "reason": "ast_family_present_but_no_approved_enumerator",
                    }
                )

    def rows_for(self, source: SourceFile) -> list[dict[str, Any]]:
        if source.path in self._row_cache:
            return self._row_cache[source.path]
        path = Path(source.path)
        posix = path.as_posix()
        if any(posix.endswith(rel) or f"/{rel}" in posix for rel in LEGACY_NON_AUTHORITY):
            self.parse_failures.append(
                {"path": str(path), "reason": "legacy_repo_artifact_not_product_scope_authority"}
            )
            self._row_cache[source.path] = []
            return []
        if source.parse_status not in {"ok", ""}:
            self._row_cache[source.path] = []
            return []
        spec = self._spec_for(source)
        try:
            rows = self._parse_path(path, source, spec)
        except Exception as exc:  # noqa: BLE001
            self.parse_failures.append({"path": str(path), "reason": f"parse_failure:{exc}"})
            rows = []
        source.row_count = len(rows)
        self._row_cache[source.path] = rows
        return rows

    def _spec_for(self, source: SourceFile) -> dict[str, Any]:
        for spec in self.registry.get("sources") or []:
            if spec.get("id") == source.source_id:
                return spec
        for family in self.registry.get("ast_families") or []:
            if family.get("id") == source.source_id:
                parser = "none"
                if Path(source.path).suffix.lower() == ".pdf" and source_has_role(source, "product_scope"):
                    parser = "pdf_sku_price"
                elif source_has_role(source, "product_scope"):
                    parser = "tabular"
                return {
                    "parser": parser,
                    "sku_kind": "generic",
                    "source_currency": source.currency,
                }
        return {}

    def _parse_path(
        self,
        path: Path,
        source: SourceFile,
        spec: dict[str, Any],
    ) -> list[dict[str, Any]]:
        parser = spec.get("parser") or ""
        suffix = path.suffix.lower()
        if parser == "none":
            return []
        if parser == "insize_distributor_xlsx" or (
            source.brand_key == "INSIZE" and "price" in (source.roles or []) and suffix in {".xlsx", ".xlsm"}
        ):
            return self._parse_insize_distributor(path)
        if suffix in PDF_SUFFIXES:
            extracted = extract_pdf_text(path)
            if not extracted.ok:
                source.parse_status = extracted.status
                self.unparsed.append(
                    {
                        "path": str(path),
                        "source_id": source.source_id,
                        "reason": extracted.error or extracted.status,
                    }
                )
                self.parse_failures.append(
                    {"path": str(path), "reason": f"pdf_{extracted.status}:{extracted.error or 'no_text'}"}
                )
                return []
            kind = str(spec.get("sku_kind") or ("insize" if source.brand_key == "INSIZE" else "generic"))
            currency = source.currency or spec.get("source_currency")
            parsed = extract_pdf_row_parse(extracted.text, sku_kind=kind, default_currency=currency)
            source.parser_confidence = parsed.confidence
            brand = source.brand_key or "UNKNOWN"
            stats = self.brand_parse.setdefault(
                brand,
                {
                    "extracted_rows": 0,
                    "rejected_rows": 0,
                    "confidence": parsed.confidence,
                    "rejected_examples": [],
                },
            )
            stats["extracted_rows"] = int(stats["extracted_rows"]) + len(parsed.rows)
            stats["rejected_rows"] = int(stats["rejected_rows"]) + len(parsed.rejected)
            if parsed.confidence == "low":
                stats["confidence"] = "low"
            examples = stats["rejected_examples"]
            for item in parsed.rejected[:8]:
                if len(examples) < 8:
                    examples.append(item.get("text") or item.get("reason") or "")
            if parsed.rejected:
                self.rejected_examples.setdefault(source.source_id, [])
                for item in parsed.rejected[:5]:
                    self.rejected_examples[source.source_id].append(item.get("text") or "")
            if not parsed.rows and source_has_role(source, "product_scope"):
                source.parse_status = "unparsed_empty"
                reason = "pdf_text_extracted_but_no_skus"
                self.unparsed.append(
                    {"path": str(path), "source_id": source.source_id, "reason": reason}
                )
                self.parse_failures.append({"path": str(path), "reason": reason})
            if parsed.confidence == "low" and source.membership_mode == "authoritative":
                source.membership_mode = "review_if_weak"
            return parsed.rows
        if suffix in TABULAR_SUFFIXES | JSON_SUFFIXES:
            return read_tabular(path)
        return []

    def _parse_insize_distributor(self, path: Path) -> list[dict[str, Any]]:
        rows = iter_xlsx_rows(path)
        rate = parse_decimal(read_xlsx_cell(path, "K6"))
        out: list[dict[str, Any]] = []
        for row in rows:
            code = extract_sku(
                row,
                list((self.registry.get("insize") or {}).get("sku_headers") or ["CODE"]),
            )
            if not code:
                continue
            usd_header = pick_header(row, ["قیمت دلاری", "usd", "USD"])
            toman_header = pick_header(row, ["TOMAN", "toman", "تومان"])
            status_header = pick_header(row, list(self.registry.get("status_headers") or ["وضعیت"]))
            item: dict[str, Any] = {
                "CODE": code,
                "sku": code,
                "وضعیت": row.get(status_header) if status_header else "",
                "status": row.get(status_header) if status_header else "",
                "__source_row": row.get("__source_row"),
            }
            if toman_header and row.get(toman_header) not in (None, ""):
                item["price"] = row.get(toman_header)
                item["currency"] = "toman"
            elif usd_header and row.get(usd_header) not in (None, "") and rate is not None and rate > 0:
                usd = parse_decimal(row.get(usd_header))
                if usd is not None:
                    from decimal import ROUND_HALF_UP, Decimal as D

                    rial = (usd * rate).quantize(D("1"), rounding=ROUND_HALF_UP)
                    item["price"] = str(rial)
                    item["currency"] = "rial"
                    item["__usd"] = str(usd)
                    item["__rate"] = str(rate)
            elif usd_header and row.get(usd_header) not in (None, ""):
                item["price"] = row.get(usd_header)
                item["currency"] = "usd"
            out.append(item)
        return out

    def load_product_scope_targets(self) -> list[TargetSku]:
        """Membership only from files whose registry roles include product_scope."""
        collected: list[TargetSku] = []
        sku_headers = list(
            (self.registry.get("insize") or {}).get("sku_headers")
            or self.registry.get("sku_headers")
            or ["sku", "CODE"]
        )
        family_headers = list(self.registry.get("family_headers") or ["product_family"])
        brand_headers = list(self.registry.get("brand_headers") or ["brand"])
        occurrence: dict[tuple[str, str], int] = {}
        for source in self.files:
            if not source_has_role(source, "product_scope"):
                continue
            if source.source_id == "insize.distributor" or source.role == "unclassified":
                continue
            rows = self.rows_for(source)
            if source.parse_status not in {"ok", ""} and not rows:
                continue
            weak = source.membership_mode == "review_if_weak" and (
                source.parser_confidence == "low" or len(rows) < 20
            )
            for row in rows:
                sku = extract_sku(row, sku_headers)
                if not sku:
                    continue
                brand_header = pick_header(row, brand_headers)
                brand_raw = str(row.get(brand_header) or source.brand_key or "")
                brand_key = canonicalize_brand(brand_raw) or source.brand_key or ""
                family_header = pick_header(row, family_headers)
                family = str(row.get(family_header) or source.product_family or "unspecified")
                nsku = normalize_sku(sku)
                idk = (brand_key, nsku)
                occurrence[idk] = occurrence.get(idk, 0) + 1
                collected.append(
                    TargetSku(
                        brand=brand_raw or brand_key,
                        brand_key=brand_key,
                        sku=sku,
                        normalized_sku=nsku,
                        product_family=family,
                        source_scope="product_scope",
                        source_product=source.path,
                        provenance=source.sha256,
                        membership_mode="review_if_weak" if weak else source.membership_mode,
                        parse_status=source.parse_status,
                        parser_confidence=source.parser_confidence,
                    )
                )
        targets: list[TargetSku] = []
        seen: set[tuple[str, str]] = set()
        for item in collected:
            idk = (item.brand_key, item.normalized_sku)
            if idk in seen:
                continue
            seen.add(idk)
            if occurrence.get(idk, 0) > 1:
                item.duplicate_in_source = True
                self.duplicate_scope_skus.append(item.sku)
            targets.append(item)
        return targets

    def load_role_rows(self, role: str) -> list[tuple[SourceFile, dict[str, Any]]]:
        out: list[tuple[SourceFile, dict[str, Any]]] = []
        for source in self.files:
            if not source_has_role(source, role):
                continue
            if role == "product_scope":
                continue
            for row in self.rows_for(source):
                out.append((source, row))
        return out
