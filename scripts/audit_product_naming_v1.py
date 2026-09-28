#!/usr/bin/env python3
"""Karzar Product Naming Standard v1 — READ-ONLY audit dry-run.

Never mutates catalog/DB. --apply is rejected (exit 2).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.product_naming import (  # noqa: E402
    NAMING_STANDARD_VERSION,
    build_product_name_v1,
    compare_product_name_v1,
    extract_manufacturer_code_candidates,
    lint_product_name_v1,
)
from app.utils.seo_descriptions import split_bilingual_label  # noqa: E402

BANNER = """
========================================================================
  KARZAR PRODUCT NAMING v1 AUDIT
  MODE: READ-ONLY / DRY-RUN
  APPLY: DISABLED (never writes catalog/DB)
  Engine: {version}
========================================================================
""".strip()

# Terminology lead patterns → (product_type_fa, profile, optional qualifier)
_TERM_RULES: list[tuple[re.Pattern[str], str, str, str | None]] = [
    (re.compile(r"کولیس\s*دیجیتال"), "کولیس دیجیتال", "metrology.caliper.v1", None),
    (re.compile(r"کولیس"), "کولیس", "metrology.caliper.v1", None),
    (re.compile(r"میکرومتر\s*خارج"), "میکرومتر خارج‌سنج", "metrology.micrometer.v1", None),
    (re.compile(r"میکرومتر"), "میکرومتر", "metrology.micrometer.v1", None),
    (re.compile(r"اینسرت\s*ترمیم\s*رزوه|هلی[\u200c ]?کویل"), "اینسرت ترمیم رزوه", "thread_repair.insert.v1", None),
    (re.compile(r"اینسرت\s*تراش|الماس\s*تراش|^الماس\b"), "اینسرت تراشکاری", "cutting.turning_insert.v1", None),
    (re.compile(r"انگشتی|اند\s*میل|end\s*mill", re.I), "انگشتی", "cutting.solid_tool.v1", None),
    (re.compile(r"سه[\u200c ]?نظام\s*(?:دریل|مته)|چاک\s*دریل|drill\s*chuck", re.I), "سه نظام دریل", "workholding.chuck.v1", None),
    (
        re.compile(r"سه[\u200c ]?نظام\s*(?:منظم|خودمرکز|آچاری)?|سه‌نظام"),
        "سه‌نظام منظم",
        "workholding.chuck.v1",
        None,
    ),
    (re.compile(r"میز\s*گردان|rotary\s*table", re.I), "میز گردان", "machines.equipment.v1", None),
    (re.compile(r"میز\s*تقسیم|indexing\s*table", re.I), "میز تقسیم", "machines.equipment.v1", None),
    (re.compile(r"هلدر|هولدر|holder", re.I), "هلدر تراش", "toolholding.holder.v1", None),
    (re.compile(r"روانکار|روغن\s*برش|سیال"), "روانکار", "fluids.lubricant.v1", None),
]

_INSIZE_SKU_RE = re.compile(r"^\d{3,5}-\d{2,5}[A-Za-z]*$")
_MITUTOYO_SKU_RE = re.compile(r"^\d{3,7}(?:-\d+)?$")
_ZCC_CODE_RE = re.compile(r"^[A-Z]{2,6}\d")
_RANGE_KEY_RE = re.compile(r"measuring_range|measurement_range|^range$|بازه", re.I)
_CAPACITY_RE = re.compile(r"(?:Ø|⌀)?\s*(\d+(?:\.\d+)?)\s*(?:mm|میلی)", re.I)


def _reject_apply(argv: list[str]) -> None:
    if any(a == "--apply" or a.startswith("--apply=") for a in argv):
        print("ERROR: --apply is rejected. This audit is READ-ONLY only.", file=sys.stderr)
        print("MODE: READ-ONLY / APPLY disabled", file=sys.stderr)
        sys.exit(2)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_brand_registry(path: Path) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                bid = int(row["brand_id"])
            except (KeyError, ValueError):
                continue
            out[bid] = row
    return out


def _load_insize_rebuild(path: Path) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                pid = int(row["product_id"])
            except (KeyError, ValueError):
                continue
            evidence: dict[str, Any] = {
                "official_model": (row.get("official_model") or "").strip(),
                "source": "insize_official_rebuild_plan",
            }
            specs_raw = row.get("proposed_specifications") or ""
            if specs_raw.strip().startswith("{"):
                try:
                    specs = json.loads(specs_raw)
                except json.JSONDecodeError:
                    specs = {}
                tech = specs.get("technical_specs") if isinstance(specs, dict) else None
                if isinstance(tech, dict):
                    for k, v in tech.items():
                        if _RANGE_KEY_RE.search(str(k)) and v:
                            evidence["measuring_range"] = v
                            evidence["range_key"] = k
                            break
            out[pid] = evidence
    return out


def _load_specialty(path: Path) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    if not path.is_file():
        return out
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                pid = int(row["product_id"])
            except (KeyError, ValueError):
                continue
            out[pid] = {
                "oem_model": (row.get("oem_model") or "").strip(),
                "product_type_hint": (row.get("product_type") or "").strip(),
                "range_min": row.get("range_min"),
                "range_max": row.get("range_max"),
                "source": "insize_phase8_ready_specialty",
            }
    return out


def _flatten_specs(specs: Any) -> dict[str, Any]:
    if not isinstance(specs, dict):
        return {}
    flat: dict[str, Any] = {}
    for k, v in specs.items():
        if k in {"technical_specs", "dimensions"} and isinstance(v, dict):
            for kk, vv in v.items():
                flat[str(kk)] = vv
        elif k == "technical_specs" and isinstance(v, list):
            for item in v:
                if isinstance(item, dict) and "key" in item:
                    flat[str(item["key"])] = item.get("value")
        else:
            flat[k] = v
    return flat


def _match_product_type(name: str) -> tuple[str | None, str, str | None, str]:
    """Return (product_type_fa, profile, qualifier, evidence)."""
    for rx, pt, profile, qual in _TERM_RULES:
        if rx.search(name or ""):
            return pt, profile, qual, f"terminology:{pt}"
    return None, "generic.v1", None, "unmatched_lead"


def _brand_native_sku(brand_en: str | None, sku: str | None) -> bool:
    if not sku:
        return False
    b = (brand_en or "").upper()
    if "INSIZE" in b:
        return bool(_INSIZE_SKU_RE.match(sku))
    if "MITUTOYO" in b:
        return bool(_MITUTOYO_SKU_RE.match(sku))
    if "ZCC" in b:
        return bool(_ZCC_CODE_RE.match(sku.replace("ZCC-", "")))
    if "DASQUA" in b:
        return bool(re.match(r"^\d{3,5}-\d{3,5}", sku))
    if "TERMA" in b:
        return bool(re.match(r"^[A-Z]{1,4}\d", sku, re.I)) or "-" in sku
    if "ASTPOWER" in b or "AST" in b:
        return sku.upper().startswith("AST")
    if "SAN OU" in b or "SANOU" in b.replace(" ", ""):
        return bool(re.match(r"^(SO-|K\d|00\d)", sku, re.I))
    return False


def _is_reversed_hyphen_pair(a: str, b: str) -> bool:
    ap = (a or "").split("-")
    bp = (b or "").split("-")
    return len(ap) == 2 and len(bp) == 2 and ap[0] == bp[1] and ap[1] == bp[0]


def _pick_manufacturer_code(
    *,
    name: str,
    sku: str | None,
    specs: dict[str, Any],
    brand_en: str | None,
    overlay: dict[str, Any] | None,
) -> tuple[str | None, str, str, list[str]]:
    """Return (code, evidence, confidence_hint, conflict_notes)."""
    notes: list[str] = []
    merged = dict(specs)
    if overlay:
        if overlay.get("official_model"):
            merged["official_model"] = overlay["official_model"]
        if overlay.get("oem_model"):
            merged["oem_model"] = overlay["oem_model"]

    cands = extract_manufacturer_code_candidates(name=name, sku=sku, specs=merged)
    # Prefer structured evidence over sku_as_candidate / sku
    priority = [
        "specs.manufacturer_code",
        "specs.official_model",
        "specs.oem_model",
        "specs.model",
        "specs.part_number",
        "name_label",
        "sku",
    ]

    def rank(ev: str) -> int:
        for i, p in enumerate(priority):
            if ev == p or ev.startswith(p):
                return i
        return 99

    cands_sorted = sorted(cands, key=lambda x: rank(x[1]))
    if not cands_sorted:
        return None, "none", "none", notes

    labeled = [(c, e) for c, e in cands_sorted if e == "name_label"]
    sku_cands = [(c, e) for c, e in cands_sorted if e == "sku"]
    if labeled and sku_cands and _is_reversed_hyphen_pair(labeled[0][0], sku_cands[0][0]):
        notes.append(f"reversed_model_vs_sku:{labeled[0][0]}!={sku_cands[0][0]}")
        # Prefer site SKU; force LOW confidence for human review.
        return sku_cands[0][0], "sku_over_reversed_title", "low", notes

    # Prefer full title designation over truncated specs.model (grade/chipbreaker).
    spec_model = next((c for c, e in cands_sorted if e == "specs.model"), None)
    if labeled and spec_model and labeled[0][0] != spec_model:
        if spec_model in labeled[0][0] or labeled[0][0].startswith(spec_model):
            notes.append("prefer_full_title_designation_over_specs_model")
            return labeled[0][0], "name_label", "medium", notes

    # Detect conflicts among high-priority non-sku evidences
    structured = [(c, e) for c, e in cands_sorted if e != "sku"]
    if len({c for c, _ in structured}) > 1:
        # Ignore conflict if one is a prefix/subset of another (designation vs truncated model)
        uniq = sorted({c for c, _ in structured}, key=len, reverse=True)
        if not any(uniq[0].startswith(u) or u in uniq[0] for u in uniq[1:]):
            notes.append("identity_conflict:" + "|".join(f"{c}@{e}" for c, e in structured[:4]))
            return None, "conflict", "hold", notes
        notes.append("resolved_superset_designation")
        return uniq[0], "name_label" if labeled and labeled[0][0] == uniq[0] else structured[0][1], "medium", notes

    code, evidence = cands_sorted[0]
    if evidence == "sku":
        if _brand_native_sku(brand_en, sku):
            # usable but low if title lacks code
            if not re.search(r"(?:مدل|کد)\s+", name or ""):
                return code, "sku_as_candidate", "low", notes + ["title_lacks_code_label"]
            return code, "sku_as_candidate", "medium", notes
        return None, "sku_rejected_non_native", "none", notes + ["sku_not_brand_native"]

    return code, evidence, "medium", notes


def _extract_facts(
    specs: dict[str, Any],
    overlay: dict[str, Any] | None,
    name: str,
    profile: str,
) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    # range from overlay specialty
    if overlay and overlay.get("range_min") not in (None, "") and overlay.get("range_max") not in (None, ""):
        try:
            facts["range_min_mm"] = float(overlay["range_min"])
            facts["range_max_mm"] = float(overlay["range_max"])
            facts["_range_evidence"] = overlay.get("source", "overlay")
        except (TypeError, ValueError):
            pass
    if overlay and overlay.get("measuring_range") and "range_min_mm" not in facts:
        facts["measuring_range"] = overlay["measuring_range"]
        facts["_range_evidence"] = overlay.get("source", "overlay")

    for k, v in specs.items():
        if v in (None, "", [], {}):
            continue
        if _RANGE_KEY_RE.search(str(k)) and "measuring_range" not in facts and "range_min_mm" not in facts:
            facts["measuring_range"] = v
            facts["_range_evidence"] = f"specs.{k}"
        if re.search(r"diameter|قطر|Ø", str(k), re.I) and "diameter_mm" not in facts:
            facts["diameter_mm"] = v
        if re.search(r"capacity|ظرفیت", str(k), re.I) and "capacity_mm" not in facts:
            facts["capacity_mm"] = v

    # Heuristic range from name: prefer سانت; only accept digit–digit when unit-marked
    # (do NOT treat OEM codes like 1108-150 as measuring ranges).
    if "range_min_mm" not in facts and "measuring_range" not in facts:
        m2 = re.search(r"(\d+)\s*سانت", name)
        if m2 and profile.startswith("metrology."):
            cm = int(m2.group(1))
            facts["range_min_mm"] = 0
            facts["range_max_mm"] = cm * 10
            facts["_range_evidence"] = "title_sant_heuristic"
        else:
            m = re.search(
                r"(?<![مدلکد\w])(\d+(?:\.\d+)?)\s*[-–~]\s*(\d+(?:\.\d+)?)\s*(?:mm|میلی[\u200c ]*متر)",
                name,
                re.I,
            )
            if not m:
                m = re.search(
                    r"(\d+(?:\.\d+)?)\s*[-–~]\s*(\d+(?:\.\d+)?)\s*(?:mm|میلی[\u200c ]*متر)",
                    name,
                    re.I,
                )
            if m:
                facts["range_min_mm"] = float(m.group(1))
                facts["range_max_mm"] = float(m.group(2))
                facts["_range_evidence"] = "title_range_heuristic"

    if profile == "workholding.chuck.v1" and "capacity_mm" not in facts:
        m = _CAPACITY_RE.search(name)
        if m:
            facts["capacity_mm"] = float(m.group(1))
            facts["_capacity_evidence"] = "title_capacity_heuristic"
        else:
            m2 = re.search(r"(\d{2,4})\s*میلی", name)
            if m2:
                facts["capacity_mm"] = float(m2.group(1))
                facts["_capacity_evidence"] = "title_mm_heuristic"

    return facts


def _csv_write(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_apply(argv)

    parser = argparse.ArgumentParser(description="READ-ONLY Product Naming v1 audit")
    parser.add_argument(
        "--snapshot-dir",
        default=str(ROOT / "audit/product-naming-v1/snapshots"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "audit/product-naming-v1"),
    )
    parser.add_argument(
        "--brand-registry",
        default=str(ROOT / "audit/product-naming-v1/BRAND_DISPLAY_REGISTRY.csv"),
    )
    parser.add_argument(
        "--insize-rebuild",
        default=str(ROOT / "data/catalog-target/insize_official_rebuild_plan.csv"),
    )
    parser.add_argument(
        "--specialty",
        default=str(ROOT / "audit/insize-phase8/READY_SPECIALTY_PRODUCTS.csv"),
    )
    # Accept but reject --apply early; still declare to avoid argparse noise if somehow passed after
    parser.add_argument("--apply", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.apply:
        print("ERROR: --apply is rejected. This audit is READ-ONLY only.", file=sys.stderr)
        sys.exit(2)

    print(BANNER.format(version=NAMING_STANDARD_VERSION))

    snapshot_dir = Path(args.snapshot_dir)
    output_dir = Path(args.output_dir)
    details_path = snapshot_dir / "products_details.json"
    if not details_path.is_file():
        print(f"Missing snapshot: {details_path}", file=sys.stderr)
        return 1

    details_raw = _load_json(details_path)
    if isinstance(details_raw, dict):
        products = list(details_raw.values())
    else:
        products = list(details_raw)

    brands_reg = _load_brand_registry(Path(args.brand_registry))
    rebuild = _load_insize_rebuild(Path(args.insize_rebuild))
    specialty = _load_specialty(Path(args.specialty))

    census: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    holds: list[dict[str, Any]] = []
    seo: list[dict[str, Any]] = []

    state_counts: Counter[str] = Counter()
    conf_counts: Counter[str] = Counter()
    brand_counts: Counter[str] = Counter()
    profile_counts: Counter[str] = Counter()
    len_current: list[int] = []
    len_proposed: list[int] = []

    proposed_name_index: dict[str, list[int]] = defaultdict(list)
    brand_code_index: dict[tuple[str, str], list[int]] = defaultdict(list)

    examples: dict[str, dict[str, Any]] = {}

    for p in products:
        pid = int(p["id"])
        name = p.get("name") or ""
        sku = p.get("sku") or ""
        brand_obj = p.get("brand") or {}
        brand_id = p.get("brand_id") or brand_obj.get("id")
        brand_raw = brand_obj.get("name") or ""
        brand_en, _brand_fa = split_bilingual_label(brand_raw)
        reg = brands_reg.get(int(brand_id)) if brand_id is not None else None
        specs = _flatten_specs(p.get("specifications"))
        overlay: dict[str, Any] = {}
        if pid in rebuild:
            overlay.update(rebuild[pid])
        if pid in specialty:
            overlay.update(specialty[pid])

        pt_fa, profile, qual, pt_evidence = _match_product_type(name)
        # specialty PT hints
        if not pt_fa and overlay.get("product_type_hint"):
            hint = str(overlay["product_type_hint"]).upper()
            if "CALIPER" in hint:
                pt_fa, profile, pt_evidence = "کولیس", "metrology.caliper.v1", f"specialty:{hint}"
            elif "MICROMETER" in hint:
                pt_fa, profile, pt_evidence = "میکرومتر", "metrology.micrometer.v1", f"specialty:{hint}"

        code, code_ev, code_conf, code_notes = _pick_manufacturer_code(
            name=name,
            sku=sku,
            specs=specs,
            brand_en=brand_en,
            overlay=overlay or None,
        )

        facts = _extract_facts(specs, overlay or None, name, profile)
        # strip internal evidence keys from engine facts
        engine_facts = {k: v for k, v in facts.items() if not str(k).startswith("_")}

        lint_now = lint_product_name_v1(name, brand_raw=brand_raw, manufacturer_code=code)

        hold_reason = ""
        result = None
        if code_ev == "conflict":
            state = "HOLD_IDENTITY_CONFLICT"
            hold_reason = ";".join(code_notes) or "manufacturer_code_conflict"
            confidence = "none"
            proposed = None
        elif not pt_fa:
            state = "HOLD_MISSING_PRODUCT_TYPE"
            hold_reason = "no_terminology_match_on_name_lead"
            confidence = "none"
            proposed = None
        else:
            result = build_product_name_v1(
                product_type=pt_fa,
                brand=brand_raw,
                manufacturer_code=code,
                facts=engine_facts,
                naming_profile=profile,
                identity_qualifiers=[qual] if qual else None,
                registry_brand=reg,
                current_name=name,
                product_type_governed=False,  # public snapshot has no product_type_id
            )
            state = result.state
            confidence = result.confidence
            proposed = result.name
            if state.startswith("HOLD"):
                hold_reason = ",".join(result.reason_codes)

            # Cap RENAME_SAFE at MEDIUM when PT not FK-governed (already medium)
            if state == "RENAME_SAFE" and confidence == "high":
                confidence = "medium"
            # Downgrade when only sku_as_candidate with low
            if state == "RENAME_SAFE" and code_conf == "low":
                confidence = "low"
                if result:
                    # keep proposal but flag
                    pass

        state_counts[state] += 1
        conf_counts[confidence] += 1
        brand_counts[brand_raw or "?"] += 1
        profile_counts[profile] += 1
        len_current.append(len(name))
        if proposed:
            len_proposed.append(len(proposed))
            proposed_name_index[proposed].append(pid)
        if code and brand_en:
            brand_code_index[(brand_en, code)].append(pid)

        cmp = compare_product_name_v1(name, proposed) if proposed else {
            "equal": False,
            "delta_len": 0,
            "proposed_len": 0,
            "current_len": len(name),
        }

        census_row = {
            "product_id": pid,
            "sku": sku,
            "brand_id": brand_id or "",
            "brand_raw": brand_raw,
            "current_name": name,
            "current_len": len(name),
            "meta_title": p.get("meta_title") or "",
            "meta_title_blank": "1" if not (p.get("meta_title") or "").strip() else "0",
            "state": state,
            "confidence": confidence,
            "profile": profile,
            "product_type_fa": pt_fa or "",
            "product_type_evidence": pt_evidence,
            "product_type_governed": "0",
            "manufacturer_code": code or "",
            "manufacturer_code_evidence": code_ev,
            "code_notes": ";".join(code_notes),
            "proposed_name": proposed or "",
            "proposed_len": len(proposed or ""),
            "delta_len": cmp.get("delta_len", 0),
            "lint_current": "|".join(lint_now),
            "overlay_sources": ",".join(
                filter(
                    None,
                    [
                        rebuild.get(pid, {}).get("source"),
                        specialty.get(pid, {}).get("source"),
                    ],
                )
            ),
            "range_evidence": facts.get("_range_evidence", ""),
            "naming_standard_version": NAMING_STANDARD_VERSION,
        }
        census.append(census_row)

        if state in {"RENAME_SAFE", "EXACT"} and proposed:
            proposals.append(
                {
                    **census_row,
                    "reason_codes": ",".join(result.reason_codes) if result else "",
                    "used_fields": ",".join(result.used_fields) if result else "",
                    "omitted_fields": ",".join(result.omitted_fields) if result else "",
                    "warnings": "|".join(result.warnings) if result else "",
                }
            )
        if state.startswith("HOLD") or state == "MANUAL_REVIEW":
            holds.append({**census_row, "hold_reason": hold_reason})

        seo.append(
            {
                "product_id": pid,
                "sku": sku,
                "current_name": name,
                "proposed_name": proposed or "",
                "meta_title": p.get("meta_title") or "",
                "meta_title_blank": census_row["meta_title_blank"],
                "serp_title_would_change": (
                    "1"
                    if (
                        census_row["meta_title_blank"] == "1"
                        and proposed
                        and not cmp.get("equal")
                    )
                    else "0"
                ),
                "state": state,
                "confidence": confidence,
            }
        )

        # Capture examples
        def _ex(key: str) -> None:
            if key not in examples:
                examples[key] = census_row

        if sku in {"1108-150", "1108-200", "1108-300"}:
            _ex(f"pilot_{sku}")
        if brand_en == "ZCC.CT" and profile == "cutting.turning_insert.v1":
            _ex("zcc_insert")
        if brand_en == "ZCC.CT" and profile == "toolholding.holder.v1":
            _ex("zcc_holder")
        if brand_en == "SAN OU" and ("نظام" in name or profile == "workholding.chuck.v1"):
            _ex("san_ou_chuck")
        if brand_en == "Mitutoyo":
            _ex("mitutoyo")
        if brand_en == "Dasqua":
            _ex("dasqua")
        if brand_en == "TERMA":
            _ex("terma")
        if brand_en == "ASTPOWER":
            _ex("astpower")
        if state == "HOLD_MISSING_PRODUCT_TYPE":
            _ex("missing_pt")
        if state == "HOLD_IDENTITY_CONFLICT":
            _ex("identity_conflict")
        if state == "MANUAL_REVIEW":
            _ex("manual_review")

    # Collisions
    dup_names = {n: ids for n, ids in proposed_name_index.items() if len(ids) > 1}
    dup_codes = {k: ids for k, ids in brand_code_index.items() if len(ids) > 1}

    _csv_write(
        output_dir / "PRODUCT_NAMING_CENSUS.csv",
        list(census[0].keys()) if census else ["product_id"],
        census,
    )
    prop_fields = list(proposals[0].keys()) if proposals else ["product_id"]
    _csv_write(output_dir / "PRODUCT_NAMING_PROPOSALS.csv", prop_fields, proposals)
    hold_fields = list(holds[0].keys()) if holds else ["product_id", "hold_reason"]
    _csv_write(output_dir / "PRODUCT_NAMING_HOLDS.csv", hold_fields, holds)
    seo_fields = list(seo[0].keys()) if seo else ["product_id"]
    _csv_write(output_dir / "SEO_IMPACT_REPORT.csv", seo_fields, seo)

    def _pct(n: int) -> str:
        return f"{(100.0 * n / max(len(products), 1)):.1f}%"

    def _stats(vals: list[int]) -> str:
        if not vals:
            return "n/a"
        vals_s = sorted(vals)
        mid = vals_s[len(vals_s) // 2]
        return f"n={len(vals_s)} min={vals_s[0]} median={mid} max={vals_s[-1]} avg={sum(vals_s)/len(vals_s):.1f}"

    serp_change = sum(1 for r in seo if r["serp_title_would_change"] == "1")
    meta_blank = sum(1 for r in seo if r["meta_title_blank"] == "1")

    lines: list[str] = []
    lines.append("# Product Naming v1 — Audit Summary")
    lines.append("")
    lines.append("**Mode:** READ-ONLY / APPLY disabled")
    lines.append(f"**Engine:** `{NAMING_STANDARD_VERSION}`")
    lines.append(f"**Snapshot products:** {len(products)}")
    lines.append(f"**product_type_governed:** always `False` (not in public API) → RENAME_SAFE confidence ≤ MEDIUM")
    lines.append("")
    lines.append("## State census")
    lines.append("")
    lines.append("| State | Count | Share |")
    lines.append("|-------|------:|------:|")
    for st, n in state_counts.most_common():
        lines.append(f"| `{st}` | {n} | {_pct(n)} |")
    lines.append("")
    lines.append("## Confidence (RENAME_SAFE / EXACT)")
    lines.append("")
    lines.append("| Confidence | Count |")
    lines.append("|------------|------:|")
    for c, n in conf_counts.most_common():
        lines.append(f"| `{c}` | {n} |")
    lines.append("")
    lines.append("## Length stats")
    lines.append("")
    lines.append(f"- Current names: {_stats(len_current)}")
    lines.append(f"- Proposed names: {_stats(len_proposed)}")
    lines.append("")
    lines.append("## SEO impact")
    lines.append("")
    lines.append(f"- `meta_title` blank: **{meta_blank}** ({_pct(meta_blank)})")
    lines.append(f"- SERP title would change on rename (blank meta + different proposed): **{serp_change}**")
    lines.append("")
    lines.append("## Brands in snapshot")
    lines.append("")
    for b, n in brand_counts.most_common():
        lines.append(f"- {b}: {n}")
    lines.append("")
    lines.append("## Profiles selected")
    lines.append("")
    for pr, n in profile_counts.most_common():
        lines.append(f"- `{pr}`: {n}")
    lines.append("")
    lines.append("## Collisions")
    lines.append("")
    lines.append(f"- Duplicate proposed_name groups: **{len(dup_names)}**")
    if dup_names:
        for n, ids in list(dup_names.items())[:15]:
            lines.append(f"  - `{n[:80]}` → ids {ids}")
    lines.append(f"- Same brand+manufacturer_code groups: **{len(dup_codes)}**")
    if dup_codes:
        for (br, code), ids in list(dup_codes.items())[:15]:
            lines.append(f"  - {br} / `{code}` → ids {ids}")
    lines.append("")
    lines.append("## Example proposals / holds")
    lines.append("")
    for key in [
        "pilot_1108-150",
        "pilot_1108-200",
        "pilot_1108-300",
        "zcc_insert",
        "zcc_holder",
        "san_ou_chuck",
        "mitutoyo",
        "dasqua",
        "terma",
        "astpower",
        "missing_pt",
        "identity_conflict",
        "manual_review",
    ]:
        row = examples.get(key)
        if not row:
            lines.append(f"### {key}")
            lines.append("_no example captured_")
            lines.append("")
            continue
        lines.append(f"### {key}")
        lines.append(f"- id/sku: `{row['product_id']}` / `{row['sku']}`")
        lines.append(f"- brand: {row['brand_raw']}")
        lines.append(f"- current: {row['current_name']}")
        lines.append(f"- proposed: {row['proposed_name'] or '—'}")
        lines.append(f"- state/confidence: `{row['state']}` / `{row['confidence']}`")
        lines.append(f"- profile / PT: `{row['profile']}` / {row['product_type_fa'] or '—'}")
        lines.append(
            f"- OEM code: `{row['manufacturer_code']}` (evidence: {row['manufacturer_code_evidence']})"
        )
        lines.append("")
    lines.append("## Blockers for APPLY")
    lines.append("")
    lines.append("1. `product_type_id` not exposed on public ProductDetail — all PT matches are provisional terminology.")
    lines.append("2. No first-class `products.manufacturer_code` column (see SCHEMA_IDENTITY_REVIEW.md).")
    lines.append("3. HOLD counts must be cleared or overridden before any rename wave.")
    lines.append("4. Brand display governance incomplete (ASTPOWER + non-live brands NEEDS_GOVERNANCE).")
    lines.append("5. This script never enables APPLY — Phase 0/1 audit only.")
    lines.append("")
    lines.append("## Artifact paths")
    lines.append("")
    for name in [
        "PRODUCT_NAMING_CENSUS.csv",
        "PRODUCT_NAMING_PROPOSALS.csv",
        "PRODUCT_NAMING_HOLDS.csv",
        "SEO_IMPACT_REPORT.csv",
        "PRODUCT_NAMING_SUMMARY.md",
        "BRAND_DISPLAY_REGISTRY.csv",
        "PRODUCT_TYPE_NAMING_PROFILES.csv",
        "NAMING_TERMINOLOGY_REGISTRY.csv",
        "PRODUCT_NAME_WRITERS.md",
        "SCHEMA_IDENTITY_REVIEW.md",
    ]:
        lines.append(f"- `audit/product-naming-v1/{name}`")

    summary_path = output_dir / "PRODUCT_NAMING_SUMMARY.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote census={len(census)} proposals={len(proposals)} holds={len(holds)} seo={len(seo)}")
    print(f"States: {dict(state_counts)}")
    print(f"Summary → {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
