#!/usr/bin/env python3
"""Phase 2C Discovery — full-catalog manufacturer identity audit (READ-ONLY).

Never mutates Product / taxonomy / synonyms. ``--apply`` is rejected (exit 2).

Inputs (one required):
  --products-csv PATH   Export of non-deleted products (authoritative live dump)
  --status-master PATH  Historical product-status master (STALE — labeled PARTIAL)

Outputs under audit/product-naming-phase2c-discovery/.

BACKFILL_EXACT requires Tier 1–3 evidence registry linkage. SKU/title alone
never yields BACKFILL_EXACT.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.product_naming import (  # noqa: E402
    extract_manufacturer_code_candidates,
    resolve_naming_profile_v1,
)

DEFAULT_OUT = ROOT / "audit" / "product-naming-phase2c-discovery"
PRIMARY_STATES = (
    "BACKFILL_EXACT",
    "MANUAL_REVIEW",
    "HOLD_WEAK_EVIDENCE",
    "HOLD_IDENTITY_CONFLICT",
    "HOLD_MISSING",
    "HOLD_BRAND_AMBIGUOUS",
    "HOLD_DUPLICATE_IDENTITY",
    "REVIEW_EXISTING_CANONICAL",
)

_CODE_LABEL_RE = re.compile(r"(?:^|[\s،,])کد\s+", re.UNICODE)
_MODEL_LABEL_RE = re.compile(r"(?:^|[\s،,])مدل\s+", re.UNICODE)


def _reject_apply(argv: list[str]) -> None:
    if any(a == "--apply" or a.startswith("--apply=") for a in argv):
        print("ERROR: --apply is rejected. Phase 2C Discovery is READ-ONLY.", file=sys.stderr)
        raise SystemExit(2)


def _norm_brand(name: str | None) -> str:
    if not name:
        return ""
    return name.split("|", 1)[0].strip().upper()


def _title_token(name: str | None) -> str | None:
    if not name:
        return None
    for rx in (_CODE_LABEL_RE, _MODEL_LABEL_RE):
        m = rx.search(name)
        if not m:
            continue
        tail = name[m.end() :].strip()
        token = re.split(r"[،,]", tail, maxsplit=1)[0].strip()
        token = re.split(r"\s+برای\s+", token, maxsplit=1)[0].strip()
        token = re.sub(r"\s{2,}", " ", token)
        if token:
            return token
    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_evidence_registry(path: Path | None) -> dict[str, dict[str, Any]]:
    """Map brand_norm|candidate_code → Tier 1–3 evidence row."""
    if path is None or not path.exists():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            brand = _norm_brand(row.get("brand") or row.get("brand_name"))
            code = (row.get("manufacturer_code") or row.get("candidate_manufacturer_code") or "").strip()
            tier = int(row.get("authority_tier") or "0" or 0)
            if not brand or not code or tier < 1 or tier > 3:
                continue
            out[f"{brand}|{code}"] = row
    return out


def classify_row(
    row: dict[str, Any],
    *,
    evidence: dict[str, dict[str, Any]],
    collision_codes: set[str],
) -> dict[str, Any]:
    """Primary classification for one product. Never promotes SKU/title to EXACT."""
    brand_name = row.get("brand_name") or row.get("brand") or ""
    brand = _norm_brand(brand_name)
    sku = (row.get("sku") or "").strip()
    name = row.get("name") or ""
    canonical = row.get("manufacturer_code")
    if isinstance(canonical, str):
        canonical = canonical.strip() or None
    else:
        canonical = None

    specs = row.get("specifications") or {}
    if isinstance(specs, str) and specs.strip().startswith("{"):
        try:
            specs = json.loads(specs)
        except json.JSONDecodeError:
            specs = {}
    if not isinstance(specs, dict):
        specs = {}

    title = _title_token(name)
    cands = extract_manufacturer_code_candidates(name=name, sku=sku, specs=specs)
    cand_codes = [c[0] for c in cands]

    pt_code = (row.get("product_type_code") or row.get("product_type") or "").strip() or None
    pt_id = row.get("product_type_id")
    if pt_id in ("", None):
        pt_id = None
    profile, profile_res = resolve_naming_profile_v1(pt_code)

    out: dict[str, Any] = {
        "product_id": row.get("product_id") or row.get("id"),
        "sku": sku,
        "name": name,
        "slug": row.get("slug") or "",
        "brand_id": row.get("brand_id") or "",
        "brand_name": brand_name,
        "product_type_id": pt_id or "",
        "product_type_code": pt_code or "",
        "manufacturer_code": canonical or "",
        "title_candidate": title or "",
        "sku_candidate": sku,
        "parser_candidates": "|".join(cand_codes[:5]),
        "naming_profile": profile,
        "profile_resolution": profile_res,
        "authority_tier": "",
        "source_type": "",
        "source_path_or_url": "",
        "evidence_notes": "",
        "source_sha256": "",
        "candidate_manufacturer_code": "",
        "classification": "HOLD_MISSING",
        "conflict_status": "",
    }

    if not brand:
        out["classification"] = "HOLD_BRAND_AMBIGUOUS"
        out["evidence_notes"] = "brandless_product"
        return out

    if canonical:
        key = f"{brand}|{canonical}"
        if key in evidence:
            out["classification"] = "BACKFILL_EXACT"
            out["candidate_manufacturer_code"] = canonical
            ev = evidence[key]
            out["authority_tier"] = ev.get("authority_tier", "")
            out["source_type"] = ev.get("source_type", "existing_canonical_verified")
            out["source_path_or_url"] = ev.get("source_path_or_url", "")
            out["evidence_notes"] = "existing_manufacturer_code_matches_tier1_3_registry"
        else:
            out["classification"] = "REVIEW_EXISTING_CANONICAL"
            out["candidate_manufacturer_code"] = canonical
            out["evidence_notes"] = "non_null_manufacturer_code_without_tier1_3_provenance"
            out["conflict_status"] = "unverified_existing"
        if key in collision_codes:
            out["classification"] = "HOLD_DUPLICATE_IDENTITY"
            out["conflict_status"] = "brand_oem_collision"
        return out

    # No canonical column value — candidates are audit-only.
    title_c = title
    sku_c = sku if sku else None
    conflict = False
    if title_c and sku_c and title_c.replace(" ", "") != sku_c.replace(" ", ""):
        # Distinct code-like signals → conflict / review, never exact from heuristics.
        if re.search(r"\d", title_c) and re.search(r"\d", sku_c):
            conflict = True

    # Tier 1–3 registry hit on a candidate
    for code in cand_codes + ([title_c] if title_c else []) + ([sku_c] if sku_c else []):
        if not code:
            continue
        key = f"{brand}|{code}"
        if key in evidence:
            if key in collision_codes:
                out["classification"] = "HOLD_DUPLICATE_IDENTITY"
                out["candidate_manufacturer_code"] = code
                out["conflict_status"] = "brand_oem_collision"
                return out
            out["classification"] = "BACKFILL_EXACT"
            out["candidate_manufacturer_code"] = code
            ev = evidence[key]
            out["authority_tier"] = ev.get("authority_tier", "")
            out["source_type"] = ev.get("source_type", "")
            out["source_path_or_url"] = ev.get("source_path_or_url") or ev.get("source_path", "")
            out["evidence_notes"] = "tier1_3_registry_match"
            if ev.get("sha256"):
                out["source_sha256"] = ev.get("sha256", "")
            return out

    if conflict:
        cand = title_c or sku_c or ""
        key = f"{brand}|{cand}" if cand else ""
        if key and key in collision_codes:
            out["classification"] = "HOLD_DUPLICATE_IDENTITY"
            out["candidate_manufacturer_code"] = cand
            out["conflict_status"] = "title_vs_sku+brand_oem_collision"
            out["authority_tier"] = "4"
            out["source_type"] = "title+sku_heuristic"
            out["evidence_notes"] = f"title={title_c}|sku={sku_c}"
            return out
        out["classification"] = "HOLD_IDENTITY_CONFLICT"
        out["candidate_manufacturer_code"] = cand
        out["conflict_status"] = "title_vs_sku"
        out["authority_tier"] = "4"
        out["source_type"] = "title+sku_heuristic"
        out["evidence_notes"] = f"title={title_c}|sku={sku_c}"
        return out

    if title_c or sku_c or cand_codes:
        cand = title_c or sku_c or (cand_codes[0] if cand_codes else "")
        key = f"{brand}|{cand}" if cand else ""
        if key and key in collision_codes:
            out["classification"] = "HOLD_DUPLICATE_IDENTITY"
            out["candidate_manufacturer_code"] = cand
            out["conflict_status"] = "brand_oem_collision"
            out["authority_tier"] = "4"
            out["source_type"] = "sku_or_title_or_specs_heuristic"
            out["evidence_notes"] = "tier4_candidate_collides_across_products"
            return out
        out["classification"] = "HOLD_WEAK_EVIDENCE"
        out["candidate_manufacturer_code"] = cand
        out["authority_tier"] = "4"
        out["source_type"] = "sku_or_title_or_specs_heuristic"
        out["evidence_notes"] = "tier4_only_cannot_be_backfill_exact"
        return out

    out["classification"] = "HOLD_MISSING"
    out["evidence_notes"] = "no_plausible_oem_candidate"
    return out


def load_products_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def filter_non_deleted(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep rows with empty/absent deleted_at. Does not invent soft-delete state."""
    out: list[dict[str, Any]] = []
    for r in rows:
        deleted = r.get("deleted_at")
        if deleted is None:
            out.append(r)
            continue
        if isinstance(deleted, str) and deleted.strip() == "":
            out.append(r)
            continue
        # Non-empty deleted_at → excluded from Phase 2C population.
    return out


def rename_readiness_row(classified: dict[str, Any]) -> dict[str, Any]:
    """Future rename readiness flags — OEM identity ≠ rename-ready."""
    cls = classified.get("classification")
    mfg_ready = cls == "BACKFILL_EXACT"
    pt_id = str(classified.get("product_type_id") or "").strip()
    pt_code = str(classified.get("product_type_code") or "").strip()
    profile = classified.get("naming_profile")
    profile_res = classified.get("profile_resolution") or ""
    pt_ready = bool(pt_id and pt_code)
    profile_ready = bool(profile) and profile_res in {"governed", "exact", "mapped"}
    brand_ready = bool(_norm_brand(classified.get("brand_name")))
    return {
        "product_id": classified.get("product_id"),
        "sku": classified.get("sku"),
        "classification": cls,
        "manufacturer_identity_ready": mfg_ready,
        "product_type_ready": pt_ready,
        "brand_display_ready": brand_ready,  # registry governance audited separately
        "profile_ready": profile_ready,
        "variant_fact_ready_if_required": "",  # not scored in discovery without KB dump
        "oem_exact_plus_pt_governed": mfg_ready and pt_ready and profile_ready,
        "oem_exact_plus_pt_missing": mfg_ready and not pt_ready,
        "oem_exact_plus_profile_missing": mfg_ready and pt_ready and not profile_ready,
    }


def brand_census(rows: list[dict[str, Any]], classified: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_brand: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r, c in zip(rows, classified, strict=True):
        key = (str(r.get("brand_id") or ""), r.get("brand_name") or r.get("brand") or "")
        by_brand[f"{key[0]}|{key[1]}"].append({**r, **c})
    out = []
    for key, items in sorted(by_brand.items(), key=lambda kv: -len(kv[1])):
        bid, bname = key.split("|", 1)
        counts = Counter(i["classification"] for i in items)
        oem_pop = sum(1 for i in items if (i.get("manufacturer_code") or "").strip())
        pt_pop = sum(1 for i in items if str(i.get("product_type_id") or "").strip())
        out.append(
            {
                "brand_id": bid,
                "brand_name": bname,
                "products": len(items),
                "manufacturer_code_populated": oem_pop,
                "manufacturer_code_null": len(items) - oem_pop,
                "product_type_populated": pt_pop,
                **{s: counts.get(s, 0) for s in PRIMARY_STATES},
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = fieldnames or list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def reconcile(classified: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(r["classification"] for r in classified)
    total = len(classified)
    summed = sum(counts[s] for s in PRIMARY_STATES)
    unknown = total - summed
    return {
        "non_deleted_total": total,
        "by_state": {s: counts.get(s, 0) for s in PRIMARY_STATES},
        "sum_primary_states": summed,
        "unknown_state_rows": unknown,
        "reconciles": summed == total and unknown == 0,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_apply(argv)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--products-csv", type=Path, help="Live/authoritative non-deleted product export")
    p.add_argument(
        "--status-master",
        type=Path,
        help="Historical status master CSV (STALE/PARTIAL coverage label)",
    )
    p.add_argument(
        "--evidence-registry",
        type=Path,
        default=None,
        help="CSV of Tier 1–3 evidence rows (brand, manufacturer_code, authority_tier, ...)",
    )
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--live-authoritative",
        action="store_true",
        help="Emit *_LIVE artifacts + PHASE2C_AUTHORITATIVE_DISCOVERY.* (preserve stale partial files)",
    )
    args = p.parse_args(argv)

    if not args.products_csv and not args.status_master:
        print("ERROR: provide --products-csv (preferred) or --status-master", file=sys.stderr)
        return 2

    coverage = "FULL_LIVE_EXPORT"
    src_path: Path
    if args.products_csv:
        src_path = args.products_csv
        rows = load_products_csv(src_path)
        if not args.live_authoritative:
            rows = filter_non_deleted(rows)
        else:
            rows = filter_non_deleted(rows)
    else:
        src_path = args.status_master
        rows = filter_non_deleted(load_products_csv(src_path))
        coverage = "STALE_STATUS_MASTER_PARTIAL"

    if args.live_authoritative:
        coverage = "LIVE_DB_AUTHORITATIVE"

    evidence = load_evidence_registry(args.evidence_registry)

    # Collision detection on candidate keys (brand|code) among non-deleted rows.
    key_to_pids: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        brand = _norm_brand(r.get("brand_name") or r.get("brand"))
        codes = set()
        mc = (r.get("manufacturer_code") or "").strip()
        if mc:
            codes.add(mc)
        title = _title_token(r.get("name"))
        if title:
            codes.add(title)
        sku = (r.get("sku") or "").strip()
        if sku:
            codes.add(sku)
        for code in codes:
            key_to_pids[f"{brand}|{code}"].append(str(r.get("product_id") or r.get("id")))
    collision_codes = {k for k, pids in key_to_pids.items() if len(set(pids)) > 1 and k.split("|", 1)[0]}

    classified = [
        classify_row(r, evidence=evidence, collision_codes=collision_codes) for r in rows
    ]
    rec = reconcile(classified)
    brands = brand_census(rows, classified)

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    suffix = "_LIVE" if args.live_authoritative else ""
    census_name = f"FULL_CATALOG_IDENTITY_CENSUS{suffix}.csv"
    brand_ready_name = f"BRAND_IDENTITY_READINESS{suffix}.csv"
    rename_name = f"RENAME_READINESS{suffix}.csv"
    collisions_name = f"IDENTITY_COLLISIONS{suffix}.csv"
    reversed_name = f"REVERSED_CODE_CONFLICTS{suffix}.csv"

    write_csv(out_dir / census_name, classified)
    if not args.live_authoritative:
        write_csv(out_dir / "FULL_CATALOG_IDENTITY_CENSUS.csv", classified)
    write_csv(out_dir / brand_ready_name, brands)
    if not args.live_authoritative:
        write_csv(out_dir / "BRAND_IDENTITY_READINESS.csv", brands)
    for state in PRIMARY_STATES:
        state_rows = [r for r in classified if r["classification"] == state]
        write_csv(out_dir / f"{state}{suffix}.csv", state_rows)
        if not args.live_authoritative:
            write_csv(out_dir / f"{state}.csv", state_rows)

    collisions = []
    for key, pids in sorted(key_to_pids.items()):
        uniq = sorted(set(pids))
        if len(uniq) > 1:
            brand, code = key.split("|", 1)
            collisions.append(
                {
                    "brand": brand,
                    "manufacturer_code_candidate": code,
                    "product_ids": "|".join(uniq),
                    "n": len(uniq),
                }
            )
    write_csv(out_dir / collisions_name, collisions)
    if not args.live_authoritative:
        write_csv(out_dir / "IDENTITY_COLLISIONS.csv", collisions)
    reversed_rows = [r for r in classified if r.get("conflict_status") == "title_vs_sku"]
    write_csv(out_dir / reversed_name, reversed_rows)
    if not args.live_authoritative:
        write_csv(out_dir / "REVERSED_CODE_CONFLICTS.csv", reversed_rows)
    readiness = [rename_readiness_row(c) for c in classified]
    write_csv(out_dir / rename_name, readiness)
    if not args.live_authoritative:
        write_csv(out_dir / "RENAME_READINESS.csv", readiness)

    existing_canonical_audit = []
    for r in classified:
        mc = (r.get("manufacturer_code") or "").strip()
        if not mc:
            continue
        cls = r.get("classification")
        if cls == "BACKFILL_EXACT":
            audit_cls = "VERIFIED_EXISTING_CANONICAL"
        elif cls == "REVIEW_EXISTING_CANONICAL":
            audit_cls = "REVIEW_EXISTING_CANONICAL"
        elif cls == "HOLD_DUPLICATE_IDENTITY":
            audit_cls = "CONFLICTING_EXISTING_CANONICAL"
        else:
            audit_cls = "REVIEW_EXISTING_CANONICAL"
        existing_canonical_audit.append(
            {
                "product_id": r.get("product_id"),
                "brand": r.get("brand_name"),
                "name": r.get("name"),
                "sku": r.get("sku"),
                "current_manufacturer_code": mc,
                "classification": audit_cls,
                "reason": r.get("evidence_notes") or r.get("conflict_status") or "",
            }
        )
    write_csv(out_dir / f"REVIEW_EXISTING_CANONICAL{suffix}.csv", existing_canonical_audit)

    # Empty registry template when no Tier 1–3 evidence supplied (honest zero EXACT).
    registry_path = out_dir / "SOURCE_AUTHORITY_REGISTRY.csv"
    if args.evidence_registry and Path(args.evidence_registry).exists():
        registry_path.write_bytes(Path(args.evidence_registry).read_bytes())
    elif not registry_path.exists():
        write_csv(
            registry_path,
            [],
            fieldnames=[
                "brand",
                "manufacturer_code",
                "authority_tier",
                "source_type",
                "source_path_or_url",
                "source_page_or_row",
                "source_quote_or_field",
                "sha256",
                "notes",
            ],
        )

    git_sha = ""
    try:
        import subprocess

        git_sha = (
            subprocess.run(
                ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            ).stdout.strip()
        )
    except OSError:
        pass

    summary = {
        "phase": "2C-discovery",
        "generated_at": datetime.now(UTC).isoformat(),
        "coverage": coverage,
        "script_git_sha": git_sha,
        "source_path": str(src_path),
        "source_sha256": _sha256_file(src_path) if src_path.exists() else "",
        "evidence_registry": str(args.evidence_registry) if args.evidence_registry else "",
        "reconciliation": rec,
        "collision_groups": len(collisions),
        "reversed_code_conflicts": sum(
            1 for r in classified if r.get("conflict_status") == "title_vs_sku"
        ),
        "rename_readiness": {
            "manufacturer_identity_ready": sum(
                1 for r in readiness if r["manufacturer_identity_ready"]
            ),
            "oem_exact_plus_pt_governed": sum(
                1 for r in readiness if r["oem_exact_plus_pt_governed"]
            ),
            "oem_exact_plus_pt_missing": sum(
                1 for r in readiness if r["oem_exact_plus_pt_missing"]
            ),
            "oem_exact_plus_profile_missing": sum(
                1 for r in readiness if r["oem_exact_plus_profile_missing"]
            ),
        },
        "note": (
            "BACKFILL_EXACT requires Tier 1–3 evidence registry linkage. "
            "SKU/title alone never yields BACKFILL_EXACT. No Product writes performed."
        ),
    }
    (out_dir / "PHASE2C_DISCOVERY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    md = [
        "# Phase 2C Discovery Summary",
        "",
        f"- Coverage: `{coverage}`",
        f"- Source: `{src_path}`",
        f"- Rows: **{rec['non_deleted_total']}**",
        f"- Reconciliation: **{'PASS' if rec['reconciles'] else 'FAIL'}**",
        "",
        "## Primary classification",
        "",
    ]
    for s in PRIMARY_STATES:
        md.append(f"- {s}: {rec['by_state'].get(s, 0)}")
    md.extend(
        [
            "",
            "## Safety",
            "",
            "- manufacturer_code writes: **0**",
            "- Product.name writes: **0**",
            "- `--apply`: rejected",
            "",
        ]
    )
    (out_dir / "PHASE2C_DISCOVERY_SUMMARY.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    if args.live_authoritative:
        auth_md = [
            "# Phase 2C Authoritative Discovery Summary",
            "",
            "> **Coverage: LIVE_DB_AUTHORITATIVE** — live read-only SQL export.",
            "> Historical `STALE_STATUS_MASTER_PARTIAL` artifacts remain for provenance only.",
            "",
            f"- Export SHA256: `{summary['source_sha256']}`",
            f"- Rows: **{rec['non_deleted_total']}**",
            f"- Reconciliation: **{'PASS' if rec['reconciles'] else 'FAIL'}**",
            f"- BACKFILL_EXACT: **{rec['by_state'].get('BACKFILL_EXACT', 0)}** (Tier 1–3 registry only)",
            "",
            "## Primary classification",
            "",
        ]
        for s in PRIMARY_STATES:
            auth_md.append(f"- {s}: {rec['by_state'].get(s, 0)}")
        auth_md.extend(
            [
                "",
                "## Safety",
                "",
                "- DISCOVERY ONLY — no APPLY",
                "- manufacturer_code writes: **0**",
                "- `--apply`: rejected",
                "",
            ]
        )
        (out_dir / "PHASE2C_AUTHORITATIVE_DISCOVERY_SUMMARY.md").write_text(
            "\n".join(auth_md) + "\n", encoding="utf-8"
        )
        auth = {**summary, "phase": "2C-authoritative-discovery", "artifact_suffix": "_LIVE"}
        (out_dir / "PHASE2C_AUTHORITATIVE_DISCOVERY.json").write_text(
            json.dumps(auth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if rec["reconciles"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
