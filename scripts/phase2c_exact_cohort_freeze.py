#!/usr/bin/env python3
"""Phase 2C exact cohort freeze — evidence traceability + replay gate (READ-ONLY)."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.domain.phase2c_evidence import (  # noqa: E402
    BACKFILL_EXACT_COLUMNS,
    CONFLICT_HEURISTIC_UNRESOLVED,
    CONFLICT_NO,
    CONFLICT_RESOLVED_T1,
    CONFLICT_RESOLVED_T2,
    CONFLICT_RESOLVED_T3,
    CONFLICT_STRONG,
    REGISTRY_FIELDNAMES,
    evidence_completeness_ok,
    has_stable_locator,
    load_evidence_registry_multimap,
)
from scripts.audit_manufacturer_identity_phase2c_discovery import (  # noqa: E402
    classify_row,
    filter_non_deleted,
    load_products_csv,
    write_csv,
)

DEFAULT_OUT = ROOT / "audit" / "product-naming-phase2c-discovery"
PROVISIONAL_SHA = "38fbeee64bdb8f4b14a38dfe80937bf46f247b28344b2608889cc08e5efdf64d"
PROVISIONAL_ROWS = 1737


def _reject_apply(argv: list[str]) -> None:
    if any(a == "--apply" or a.startswith("--apply=") for a in argv):
        print("ERROR: --apply is rejected.", file=sys.stderr)
        raise SystemExit(2)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_head() -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except OSError:
        return ""


def build_exact_row(product: dict[str, Any], classified: dict[str, Any]) -> dict[str, str]:
    row: dict[str, str] = {
        "product_id": str(product.get("product_id") or product.get("id") or ""),
        "brand_id": str(product.get("brand_id") or ""),
        "brand_name": product.get("brand_name") or product.get("brand") or "",
        "current_name": product.get("name") or "",
        "sku": product.get("sku") or "",
        "current_manufacturer_code": str(product.get("manufacturer_code") or ""),
    }
    for key in BACKFILL_EXACT_COLUMNS:
        if key in row:
            continue
        row[key] = str(classified.get(key) or "")
    return row


def classify_catalog(
    products: list[dict[str, Any]],
    registry_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, set[str]]]:
    evidence = load_evidence_registry_multimap(registry_path)
    key_to_pids: dict[str, list[str]] = defaultdict(list)
    from app.domain.phase2c_evidence import normalized_match_key as nmk  # noqa: E402
    from scripts.audit_manufacturer_identity_phase2c_discovery import (  # noqa: E402
        _norm_brand,
        _title_token,
    )

    for r in products:
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
            key = f"{brand}|{nmk(code)}"
            key_to_pids.setdefault(key, []).append(str(r.get("product_id") or r.get("id")))
    collision_codes = {k for k, pids in key_to_pids.items() if len(set(pids)) > 1 and k.split("|", 1)[0]}

    classified = [
        classify_row(r, evidence=evidence, collision_codes=collision_codes) for r in products
    ]
    return classified, products, collision_codes


def evidence_completeness_report(registry_path: Path) -> dict[str, Any]:
    rows = list(csv.DictReader(registry_path.open(encoding="utf-8")))
    with_locator = 0
    without_locator = 0
    with_raw = 0
    with_desc = 0
    with_sha = 0
    complete_exact = 0
    for row in rows:
        if has_stable_locator(row):
            with_locator += 1
        else:
            without_locator += 1
        if (row.get("raw_source_code") or "").strip():
            with_raw += 1
        if (row.get("source_item_description") or "").strip():
            with_desc += 1
        if (row.get("source_sha256") or row.get("sha256") or "").strip():
            with_sha += 1
        ok, _ = evidence_completeness_ok(row)
        if ok:
            complete_exact += 1
    return {
        "registry_rows": len(rows),
        "with_stable_source_locator": with_locator,
        "without_stable_source_locator": without_locator,
        "with_raw_source_code": with_raw,
        "with_source_description": with_desc,
        "with_source_sha256": with_sha,
        "rows_passing_exact_completeness_gate": complete_exact,
    }


def conflict_resolution_report(classified: list[dict[str, Any]]) -> dict[str, Any]:
    heuristic = sum(
        1
        for r in classified
        if r.get("classification_reason") == "title_vs_sku"
        or (r.get("title_candidate") and r.get("sku_candidate")
            and r.get("title_candidate").replace(" ", "") != r.get("sku_candidate", "").replace(" ", ""))
    )
    resolved_t1 = sum(1 for r in classified if r.get("conflict_status") == CONFLICT_RESOLVED_T1)
    resolved_t2 = sum(1 for r in classified if r.get("conflict_status") == CONFLICT_RESOLVED_T2)
    resolved_t3 = sum(1 for r in classified if r.get("conflict_status") == CONFLICT_RESOLVED_T3)
    unresolved = sum(1 for r in classified if r.get("conflict_status") == CONFLICT_HEURISTIC_UNRESOLVED)
    strong = sum(1 for r in classified if r.get("conflict_status") == CONFLICT_STRONG)
    dup = sum(1 for r in classified if r.get("classification") == "HOLD_DUPLICATE_IDENTITY")
    return {
        "heuristic_conflicts_total": heuristic,
        "resolved_by_tier_1": resolved_t1,
        "resolved_by_tier_2": resolved_t2,
        "resolved_by_tier_3": resolved_t3,
        "unresolved_conflicts": unresolved,
        "strong_evidence_conflicts": strong,
        "duplicate_identity_holds": dup,
    }


def deterministic_sample(
    exact_rows: list[dict[str, str]],
    *,
    brand: str,
    n: int,
    seed_key: str,
) -> list[dict[str, str]]:
    subset = [r for r in exact_rows if (r.get("brand_name") or "").upper().startswith(brand)]
    subset.sort(key=lambda r: (r.get("product_id", ""), r.get("candidate_manufacturer_code", "")))
    h = int(hashlib.sha256(seed_key.encode()).hexdigest()[:8], 16)
    if len(subset) <= n:
        return subset
    step = max(1, len(subset) // n)
    start = h % len(subset)
    picked: list[dict[str, str]] = []
    i = start
    while len(picked) < n and len(picked) < len(subset):
        picked.append(subset[i % len(subset)])
        i += step
    return picked[:n]


def rejected_sample(classified: list[dict[str, Any]], products: list[dict[str, Any]], n: int) -> list[dict[str, str]]:
    holds = ("HOLD_WEAK_EVIDENCE", "HOLD_IDENTITY_CONFLICT", "HOLD_DUPLICATE_IDENTITY")
    rows: list[dict[str, str]] = []
    for p, c in zip(products, classified, strict=True):
        if c.get("classification") not in holds:
            continue
        rows.append(
            {
                "product_id": str(p.get("product_id") or ""),
                "brand_name": p.get("brand_name") or "",
                "sku": p.get("sku") or "",
                "current_name": p.get("name") or "",
                "classification": c.get("classification") or "",
                "conflict_status": c.get("conflict_status") or "",
                "classification_reason": c.get("classification_reason") or "",
                "candidate_manufacturer_code": c.get("candidate_manufacturer_code") or "",
                "evidence_notes": c.get("evidence_notes") or "",
            }
        )
    rows.sort(key=lambda r: (r["classification"], r["product_id"]))
    h = int(hashlib.sha256(b"rejected-sample-v1").hexdigest()[:8], 16)
    if len(rows) <= n:
        return rows
    step = max(1, len(rows) // n)
    start = h % len(rows)
    picked: list[dict[str, str]] = []
    i = start
    while len(picked) < n:
        picked.append(rows[i % len(rows)])
        i += step
    return picked[:n]


def run_freeze_pass(
    products: list[dict[str, Any]],
    registry_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    classified, _, _ = classify_catalog(products, registry_path)
    exact: list[dict[str, str]] = []
    for p, c in zip(products, classified, strict=True):
        if c.get("classification") != "BACKFILL_EXACT":
            continue
        exact.append(build_exact_row(p, c))
    exact.sort(key=lambda r: (r.get("product_id", ""), r.get("candidate_manufacturer_code", "")))
    return exact, classified


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    _reject_apply(argv)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--products-csv", type=Path, required=True)
    p.add_argument("--registry", type=Path, default=DEFAULT_OUT / "SOURCE_AUTHORITY_REGISTRY.csv")
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--skip-registry-build", action="store_true")
    args = p.parse_args(argv)

    if not args.skip_registry_build:
        rc = subprocess.call(
            [sys.executable, str(ROOT / "scripts/build_phase2c_source_authority_registry.py")],
        )
        if rc != 0:
            return rc

    products = filter_non_deleted(load_products_csv(args.products_csv))
    exact1, classified1 = run_freeze_pass(products, args.registry)
    exact2, _ = run_freeze_pass(products, args.registry)

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    live_path = out_dir / "BACKFILL_EXACT_LIVE.csv"
    frozen_path = out_dir / "BACKFILL_EXACT_FROZEN.csv"
    write_csv(live_path, exact1, fieldnames=BACKFILL_EXACT_COLUMNS)
    write_csv(frozen_path, exact1, fieldnames=BACKFILL_EXACT_COLUMNS)

    sha1 = _sha256_file(frozen_path)
    write_csv(frozen_path, exact2, fieldnames=BACKFILL_EXACT_COLUMNS)
    sha2 = _sha256_file(frozen_path)
    write_csv(frozen_path, exact1, fieldnames=BACKFILL_EXACT_COLUMNS)

    tier_counts = Counter(int(r.get("authority_tier") or 0) for r in exact1)
    brand_counts = Counter((r.get("brand_name") or "").split("|", 1)[0].strip().upper() for r in exact1)

    sample_rows: list[dict[str, str]] = []
    sample_rows.extend(deterministic_sample(exact1, brand="INSIZE", n=20, seed_key="insize-v1"))
    sample_rows.extend(deterministic_sample(exact1, brand="DASQUA", n=20, seed_key="dasqua-v1"))
    sample_rows.extend(deterministic_sample(exact1, brand="TERMA", n=15, seed_key="terma-v1"))
    ast_rows = [r for r in exact1 if "AST" in (r.get("brand_name") or "").upper()]
    sample_rows.extend(ast_rows if len(ast_rows) <= 50 else ast_rows[:50])
    write_csv(out_dir / "BACKFILL_EXACT_REVIEW_SAMPLE.csv", sample_rows, fieldnames=BACKFILL_EXACT_COLUMNS)

    rejected = rejected_sample(classified1, products, 30)
    write_csv(out_dir / "BACKFILL_REJECTED_REVIEW_SAMPLE.csv", rejected)

    ev_report = evidence_completeness_report(args.registry)
    (out_dir / "EVIDENCE_COMPLETENESS_REPORT.json").write_text(
        json.dumps(ev_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    conflict_report = conflict_resolution_report(classified1)
    (out_dir / "CONFLICT_RESOLUTION_REPORT.json").write_text(
        json.dumps(conflict_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest_path = out_dir / "SOURCE_HASH_MANIFEST.json"
    source_manifest_sha = _sha256_file(manifest_path) if manifest_path.exists() else ""
    registry_sha = _sha256_file(args.registry)

    fingerprints_path = out_dir / "LIVE_RUNTIME_IDENTITY.json"
    db_fps = {}
    if fingerprints_path.exists():
        db_fps = json.loads(fingerprints_path.read_text(encoding="utf-8"))

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_live_export_sha256": _sha256_file(args.products_csv),
        "source_live_export_rows": len(products),
        "source_authority_registry_sha256": registry_sha,
        "source_hash_manifest_sha256": source_manifest_sha,
        "classification_script_git_sha": _git_head(),
        "frozen_row_count": len(exact1),
        "frozen_csv_sha256": sha1,
        "tier_1_count": tier_counts.get(1, 0),
        "tier_2_count": tier_counts.get(2, 0),
        "tier_3_count": tier_counts.get(3, 0),
        "brand_counts": dict(brand_counts),
        "resolved_conflict_count": (
            conflict_report["resolved_by_tier_1"]
            + conflict_report["resolved_by_tier_2"]
            + conflict_report["resolved_by_tier_3"]
        ),
        "unresolved_conflict_count": conflict_report["unresolved_conflicts"],
        "provisional_cohort_sha256": PROVISIONAL_SHA,
        "provisional_cohort_rows": PROVISIONAL_ROWS,
        "provisional_status": "SUPERSEDED" if sha1 != PROVISIONAL_SHA or len(exact1) != PROVISIONAL_ROWS else "UNCHANGED",
        "replay_1_sha256": sha1,
        "replay_2_sha256": sha2,
        "replay_identical": sha1 == sha2,
        "db_identity_fingerprints_at_discovery": db_fps,
        "discovery_fingerprint_not_apply_preflight": (
            "Fingerprints captured at discovery are provenance only. "
            "Future Phase 2C APPLY must collect fresh fingerprints immediately before rehearsal."
        ),
        "status": "READY_FOR_OWNER_FREEZE_REVIEW" if sha1 == sha2 else "BLOCKED_REPLAY_MISMATCH",
    }
    (out_dir / "BACKFILL_EXACT_FREEZE_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    auth = {
        "phase": "2C-authoritative-discovery-freeze",
        "generated_at": manifest["generated_at"],
        "coverage": "LIVE_DB_AUTHORITATIVE",
        "backfill_exact_frozen_rows": len(exact1),
        "backfill_exact_frozen_sha256": sha1,
        "provisional_backfill_exact_rows": PROVISIONAL_ROWS,
        "provisional_backfill_exact_sha256": PROVISIONAL_SHA,
        "evidence_completeness": ev_report,
        "conflict_resolution": conflict_report,
        "replay_identical": sha1 == sha2,
        "ready_for_owner_freeze_review": sha1 == sha2,
    }
    (out_dir / "PHASE2C_AUTHORITATIVE_DISCOVERY.json").write_text(
        json.dumps(auth, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary_lines = [
        "# Phase 2C Authoritative Discovery Summary",
        "",
        "> LIVE_DB_AUTHORITATIVE — provisional 1737-row cohort superseded by evidence-traceable freeze.",
        "> **NO APPLY** — discovery fingerprints ≠ future APPLY preflight.",
        "",
        f"- Frozen BACKFILL_EXACT rows: **{len(exact1)}**",
        f"- Frozen SHA256: `{sha1}`",
        f"- Provisional SHA256 (historical): `{PROVISIONAL_SHA}`",
        f"- Replay identical: **{'YES' if sha1 == sha2 else 'NO'}**",
        "",
    ]
    (out_dir / "PHASE2C_AUTHORITATIVE_DISCOVERY_SUMMARY.md").write_text(
        "\n".join(summary_lines) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if sha1 == sha2 else 1


if __name__ == "__main__":
    raise SystemExit(main())
