#!/usr/bin/env python3
"""INSIZE sales activation reconciler + guarded pilot apply.

Dry-run / reconcile is the default.

Guarded production apply requires ALL of:
  --apply
  --sku-manifest PATH
  --expected-sku-count N
  --expected-workbook-sha256 HEX
  --expected-rate RATE
  --confirm-production-write

Apply updates ONLY ``base_price`` and ``is_available`` inside one DB transaction.

This script never prints database credentials or connection strings.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from insize_sales_activation_lib import (  # noqa: E402
    CONTROL_SKU,
    ALLOWED_APPLY_FIELDS,
    FORBIDDEN_APPLY_FIELDS,
    PilotGateError,
    PilotManifest,
    PilotSkuPlan,
    WorkbookCatalog,
    apply_pilot_plans,
    assert_expected_rate,
    assert_expected_workbook_sha,
    content_ready,
    duplicate_workbook_codes,
    image_ready,
    load_pilot_manifest,
    load_workbook_catalog,
    match_exact,
    normalize_sku,
    normalize_status,
    supplier_available,
    valid_workbook_price,
    verify_control_sku,
    verify_pilot_state,
    workbook_sha256,
)

DEFAULT_OUT = _ROOT / "data" / "imports" / "insize" / "sales_activation"
DEFAULT_MANIFEST = _ROOT / "scripts" / "fixtures" / "insize_pilot_manifest_v1.json"
STOREFRONT_PRODUCT_PREFIX = "/product/"


def _load_karzar_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "t", "true", "yes", "y"}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def reconcile(
    *,
    catalog: WorkbookCatalog,
    products: list[dict[str, Any]],
) -> dict[str, Any]:
    by_code = catalog.by_code
    dup_codes = duplicate_workbook_codes(catalog.rows)

    karzar_total = len(products)
    active = sum(1 for p in products if _truthy(p.get("is_active")))
    unavailable = sum(1 for p in products if not _truthy(p.get("is_available")))
    missing_price = 0
    missing_image = 0
    missing_content = 0
    for p in products:
        try:
            bp = Decimal(str(p.get("base_price") or "0"))
        except Exception:
            bp = Decimal("0")
        if bp <= 0:
            missing_price += 1
        if not image_ready(p.get("image_count"), p.get("primary_image_url")):
            missing_image += 1
        if not content_ready(
            name=p.get("name"),
            short_description=p.get("short_description"),
            description=p.get("description"),
            specifications=p.get("specifications"),
        ):
            missing_content += 1

    wb_rows = len(catalog.rows)
    unique_codes = len(by_code)
    malformed = sum(1 for r in catalog.rows if not normalize_sku(r.code))
    status_available = sum(1 for r in catalog.rows if supplier_available(r.status))
    status_unavailable = sum(
        1 for r in catalog.rows if normalize_status(r.status) == "نا موجود"
    )
    other_status = wb_rows - status_available - status_unavailable
    valid_usd = sum(
        1 for r in catalog.rows if r.usd_price is not None and r.usd_price > 0
    )
    invalid_usd = wb_rows - valid_usd

    matched_rows: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    unmatched_karzar: list[str] = []
    methods = Counter()

    karzar_keys = {normalize_sku(p.get("sku")) for p in products}
    for p in products:
        sku = p.get("sku") or ""
        m = match_exact(sku, by_code)
        methods[m.method] += 1
        if m.method != "exact" or not m.workbook_code:
            unmatched_karzar.append(sku)
            continue
        wb = by_code[normalize_sku(m.workbook_code)]
        if normalize_sku(wb.code) in dup_codes:
            ambiguous.append(
                {
                    "sku": sku,
                    "workbook_code": wb.code,
                    "reason": "duplicate_workbook_code",
                    "dup_count": dup_codes[normalize_sku(wb.code)],
                }
            )
            methods["ambiguous"] += 1
            methods["exact"] -= 1
            continue

        price_class, rial, toman = valid_workbook_price(wb.usd_price, catalog.rate)
        try:
            current_price = Decimal(str(p.get("base_price") or "0"))
        except Exception:
            current_price = Decimal("0")
        img_ok = image_ready(p.get("image_count"), p.get("primary_image_url"))
        content_ok = content_ready(
            name=p.get("name"),
            short_description=p.get("short_description"),
            description=p.get("description"),
            specifications=p.get("specifications"),
        )
        avail = supplier_available(wb.status)
        product_active = _truthy(p.get("is_active"))
        ready = (
            avail
            and price_class == "VALID_WORKBOOK_PRICE"
            and toman is not None
            and toman > 0
            and img_ok
            and content_ok
            and product_active
            and bool(p.get("category_id"))
            and bool((p.get("slug") or "").strip())
        )
        delta = None if toman is None else toman - current_price
        matched_rows.append(
            {
                "product_id": p.get("id"),
                "karzar_sku": sku,
                "slug": p.get("slug"),
                "title": p.get("name"),
                "category_id": p.get("category_id"),
                "category_name": p.get("category_name"),
                "category_slug": p.get("category_slug"),
                "workbook_code": wb.code,
                "workbook_row": wb.source_row,
                "workbook_description": wb.description,
                "usd_price": str(wb.usd_price) if wb.usd_price is not None else None,
                "rate": str(catalog.rate),
                "rial_price": str(rial) if rial is not None else None,
                "karzar_price_toman": str(toman) if toman is not None else None,
                "current_karzar_price": str(current_price),
                "price_delta": str(delta) if delta is not None else None,
                "workbook_total_inventory": str(wb.total_inventory)
                if wb.total_inventory is not None
                else None,
                "workbook_status": wb.status,
                "supplier_available": avail,
                "current_is_available": _truthy(p.get("is_available")),
                "is_active": product_active,
                "image_ready": img_ok,
                "content_ready": content_ok,
                "image_count": p.get("image_count"),
                "primary_image_url": p.get("primary_image_url"),
                "updated_at": p.get("updated_at"),
                "price_class": price_class,
                "ready_for_sales_activation": ready,
            }
        )

    unmatched_workbook = sorted(
        code
        for code in by_code
        if code not in karzar_keys and supplier_available(by_code[code].status)
    )
    unmatched_workbook_all = sorted(code for code in by_code if code not in karzar_keys)

    available_matches = [r for r in matched_rows if r["supplier_available"]]
    valid_price_matches = [
        r for r in available_matches if r["price_class"] == "VALID_WORKBOOK_PRICE"
    ]
    valid_karzar_unit = [
        r
        for r in valid_price_matches
        if r["karzar_price_toman"] and Decimal(r["karzar_price_toman"]) > 0
    ]
    image_ready_n = [r for r in valid_karzar_unit if r["image_ready"]]
    content_ready_n = [r for r in valid_karzar_unit if r["content_ready"]]
    ready = [r for r in valid_karzar_unit if r["ready_for_sales_activation"]]
    only_image = [
        r
        for r in valid_karzar_unit
        if (not r["image_ready"]) and r["content_ready"] and r["is_active"]
    ]
    only_content = [
        r
        for r in valid_karzar_unit
        if r["image_ready"] and (not r["content_ready"]) and r["is_active"]
    ]
    both_missing = [
        r
        for r in valid_karzar_unit
        if (not r["image_ready"]) and (not r["content_ready"]) and r["is_active"]
    ]
    inactive_block = [r for r in valid_karzar_unit if not r["is_active"]]
    invalid_price = [
        r for r in available_matches if r["price_class"] != "VALID_WORKBOOK_PRICE"
    ]

    buckets = {
        "READY_FOR_SALES_ACTIVATION": ready,
        "MISSING_IMAGE": only_image,
        "MISSING_CONTENT": only_content,
        "MISSING_IMAGE_AND_CONTENT": both_missing,
        "SUPPLIER_UNAVAILABLE": [r for r in matched_rows if not r["supplier_available"]],
        "INVALID_WORKBOOK_PRICE": invalid_price,
        "AMBIGUOUS_SKU": ambiguous,
        "UNMATCHED_KARZAR": unmatched_karzar,
        "UNMATCHED_WORKBOOK_AVAILABLE": unmatched_workbook,
        "INACTIVE": inactive_block,
    }
    control = next(
        (
            r
            for r in matched_rows
            if normalize_sku(r["karzar_sku"]) == normalize_sku(CONTROL_SKU)
        ),
        None,
    )
    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "workbook": {
            "rows": wb_rows,
            "unique_codes": unique_codes,
            "duplicate_codes": len(dup_codes),
            "malformed_codes": malformed,
            "status_available": status_available,
            "status_unavailable": status_unavailable,
            "status_other": other_status,
            "valid_usd": valid_usd,
            "invalid_usd": invalid_usd,
            "rate": str(catalog.rate),
            "rate_cell": catalog.rate_cell,
        },
        "karzar_insize": {
            "total": karzar_total,
            "active": active,
            "unavailable": unavailable,
            "missing_price": missing_price,
            "missing_image": missing_image,
            "missing_content": missing_content,
            "brand_ids": sorted({str(p.get("brand_id")) for p in products}),
        },
        "matching": {
            "exact_matches": methods.get("exact", 0),
            "ambiguous": len(ambiguous),
            "unmatched_karzar": len(unmatched_karzar),
            "unmatched_workbook_all": len(unmatched_workbook_all),
            "unmatched_workbook_available": len(unmatched_workbook),
        },
        "funnel": {
            "safe_match": methods.get("exact", 0),
            "supplier_available": len(available_matches),
            "valid_workbook_rial_price": len(valid_price_matches),
            "valid_karzar_unit_price": len(valid_karzar_unit),
            "image_ready_among_valid_available": len(image_ready_n),
            "content_ready_among_valid_available": len(content_ready_n),
            "READY_FOR_SALES_ACTIVATION": len(ready),
            "require_only_image": len(only_image),
            "require_only_content": len(only_content),
            "require_image_and_content": len(both_missing),
            "blocked_ambiguous_or_data": len(ambiguous),
            "invalid_workbook_price_among_available": len(invalid_price),
            "inactive_among_valid_available": len(inactive_block),
        },
        "control_sku_row": control,
        "samples": {
            "ready_for_sales": ready[:15],
            "missing_image": only_image[:10],
            "missing_content": only_content[:10],
            "ambiguous": ambiguous[:10],
        },
        "bucket_counts": {k: len(v) for k, v in buckets.items()},
        "allowed_apply_fields": sorted(ALLOWED_APPLY_FIELDS),
        "forbidden_apply_fields": sorted(FORBIDDEN_APPLY_FIELDS),
    }
    return {
        "summary": summary,
        "matched_rows": matched_rows,
        "buckets": buckets,
        "control_checksum": verify_control_sku(catalog),
    }


def _review_flags(row: dict[str, Any], ready_prices: list[Decimal]) -> list[str]:
    flags: list[str] = []
    cur = Decimal(str(row.get("current_karzar_price") or "0"))
    new = Decimal(str(row["karzar_price_toman"]))
    if cur <= 0:
        flags.append("zero_or_null_current_price")
    else:
        pct = float((new - cur) / cur * 100)
        if abs(pct) > 30:
            flags.append("pct_gt_30")
    if ready_prices:
        lo, hi = ready_prices[0], ready_prices[-1]
        if new < lo or new > hi:
            flags.append("outside_ready_price_distribution")
    if not (row.get("slug") or "").strip():
        flags.append("not_publicly_reachable_missing_slug")
    if not row.get("category_id"):
        flags.append("missing_category")
    return flags


def select_pilot_plans(
    *,
    ready_rows: list[dict[str, Any]],
    catalog: WorkbookCatalog,
    workbook_sha: str,
    count: int = 10,
) -> PilotManifest:
    """Select exactly ``count`` unflagged READY products with price/category mix."""
    prices = sorted(Decimal(r["karzar_price_toman"]) for r in ready_rows)
    enriched: list[dict[str, Any]] = []
    for r in ready_rows:
        flags = _review_flags(r, prices)
        enriched.append({**r, "review_flags": flags})
    clean = [r for r in enriched if not r["review_flags"]]
    if len(clean) < count:
        raise PilotGateError(
            f"not enough unflagged READY products: have {len(clean)}, need {count}"
        )

    clean_sorted = sorted(clean, key=lambda r: Decimal(r["karzar_price_toman"]))
    n = len(clean_sorted)
    terciles = [
        clean_sorted[: n // 3],
        clean_sorted[n // 3 : 2 * n // 3],
        clean_sorted[2 * n // 3 :],
    ]
    selected: list[dict[str, Any]] = []
    used: set[str] = set()
    cats: set[str] = set()

    def add_from(pool: list[dict[str, Any]], need: int) -> None:
        added = 0
        for prefer_new_cat in (True, False):
            for r in pool:
                if added >= need:
                    return
                sku = r["karzar_sku"]
                if sku in used:
                    continue
                cat = r.get("category_name") or ""
                if prefer_new_cat and cat in cats:
                    if any(
                        (x.get("category_name") or "") not in cats
                        and x["karzar_sku"] not in used
                        for x in pool
                    ):
                        continue
                selected.append(r)
                used.add(sku)
                cats.add(cat)
                added += 1

    add_from(terciles[0], 4)
    add_from(terciles[1], 3)
    add_from(terciles[2], 3)
    if len(selected) != count:
        raise PilotGateError(f"pilot selection produced {len(selected)} != {count}")

    selected = sorted(selected, key=lambda r: Decimal(r["karzar_price_toman"]))
    checkout = selected[0]
    plans: list[PilotSkuPlan] = []
    for r in selected:
        cur = Decimal(str(r.get("current_karzar_price") or "0"))
        new = Decimal(str(r["karzar_price_toman"]))
        abs_delta = new - cur
        pct = None if cur <= 0 else float((new - cur) / cur * 100)
        slug = str(r["slug"])
        plans.append(
            PilotSkuPlan(
                product_id=int(r["product_id"]),
                sku=str(r["karzar_sku"]),
                title=str(r.get("title") or r.get("name") or ""),
                category_id=int(r["category_id"]),
                category_name=str(r.get("category_name") or ""),
                slug=slug,
                public_path=f"{STOREFRONT_PRODUCT_PREFIX}{slug}",
                workbook_code=str(r["workbook_code"]),
                workbook_row=int(r["workbook_row"]),
                workbook_description=r.get("workbook_description"),
                usd_price=Decimal(str(r["usd_price"])),
                rate=catalog.rate,
                rial_price=Decimal(str(r["rial_price"])),
                toman_price=new,
                current_base_price=cur,
                new_base_price=new,
                absolute_delta=abs_delta,
                percentage_delta=pct,
                current_is_available=bool(r["current_is_available"]),
                target_is_available=True,
                is_active=bool(r["is_active"]),
                image_ready=bool(r["image_ready"]),
                content_ready=bool(r["content_ready"]),
                eligibility_reason=(
                    "exact_match && وضعیت==موجود && VALID_WORKBOOK_PRICE && "
                    "image_ready && content_ready && active && category && slug && "
                    "unflagged_delta"
                ),
                expected_updated_at=str(r.get("updated_at") or "") or None,
                review_flags=[],
            )
        )

    return PilotManifest(
        version=1,
        workbook_sha256=workbook_sha,
        expected_rate=str(catalog.rate),
        expected_sku_count=count,
        selected_skus=[p.sku for p in plans],
        checkout_test_sku=checkout["karzar_sku"],
        plans=plans,
        generated_at_utc=datetime.now(UTC).isoformat(),
    )


def _open_db_session():
    """Open a SQLAlchemy session from env without echoing credentials."""
    # Prefer DATABASE_URL; never print it.
    url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not url:
        raise PilotGateError(
            "DATABASE_URL / SQLALCHEMY_DATABASE_URI is not set for apply/verify"
        )
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(url)
    return sessionmaker(bind=engine)(), engine


def _run_apply(
    *,
    manifest: PilotManifest,
    catalog: WorkbookCatalog,
    live_products: list[dict[str, Any]],
    expected_count: int,
    expected_sha: str,
    expected_rate: Decimal,
    xlsx: Path,
) -> dict[str, Any]:
    assert_expected_workbook_sha(xlsx, expected_sha)
    assert_expected_rate(catalog, expected_rate)
    if manifest.expected_sku_count != expected_count:
        raise PilotGateError("exact expected SKU count mismatch (manifest)")
    if len(manifest.plans) != expected_count:
        raise PilotGateError("exact expected SKU count mismatch (plans)")
    if len(manifest.selected_skus) != expected_count:
        raise PilotGateError("exact expected SKU count mismatch (selected_skus)")
    if set(manifest.selected_skus) != {p.sku for p in manifest.plans}:
        raise PilotGateError("manifest selected_skus/plans divergence")

    live_by_sku = {normalize_sku(p.get("sku")): p for p in live_products}
    # Ensure allowlist exclusivity vs live READY set is revalidated per plan
    session, engine = _open_db_session()
    try:
        from sqlalchemy import select

        from app.db.models.product import Product

        ids = [p.product_id for p in manifest.plans]
        with session.begin():
            rows = (
                session.execute(
                    select(Product).where(Product.id.in_(ids)).with_for_update()
                )
                .scalars()
                .all()
            )
            products_by_id = {int(p.id): p for p in rows}
            if len(products_by_id) != expected_count:
                raise PilotGateError(
                    f"DB returned {len(products_by_id)} products, expected {expected_count}"
                )
            before = {
                pid: {
                    field: getattr(prod, field, None)
                    for field in FORBIDDEN_APPLY_FIELDS
                }
                for pid, prod in products_by_id.items()
            }
            result = apply_pilot_plans(
                products_by_id=products_by_id,
                plans=manifest.plans,
                workbook_by_code=catalog.by_code,
                catalog=catalog,
                live_product_rows=live_by_sku,
            )
            verify_pilot_state(
                plans=manifest.plans,
                products_by_id=products_by_id,
                snapshots_before=before,
            )
        # Second pass idempotency check (no-op)
        with session.begin():
            rows2 = (
                session.execute(select(Product).where(Product.id.in_(ids)))
                .scalars()
                .all()
            )
            products_by_id2 = {int(p.id): p for p in rows2}
            second = apply_pilot_plans(
                products_by_id=products_by_id2,
                plans=manifest.plans,
                workbook_by_code=catalog.by_code,
                catalog=catalog,
                live_product_rows=live_by_sku,
            )
            if second.updated:
                raise PilotGateError(
                    "idempotent second run expected no updates, got "
                    + str([u["sku"] for u in second.updated])
                )
        return {
            "updated": result.updated,
            "skipped_idempotent": result.skipped_idempotent,
            "audit": result.audit,
            "second_run_noop": True,
        }
    finally:
        session.close()
        engine.dispose()


def _run_verify_only(
    *,
    manifest: PilotManifest,
) -> dict[str, Any]:
    session, engine = _open_db_session()
    try:
        from sqlalchemy import select

        from app.db.models.product import Product

        ids = [p.product_id for p in manifest.plans]
        rows = (
            session.execute(select(Product).where(Product.id.in_(ids))).scalars().all()
        )
        products_by_id = {int(p.id): p for p in rows}
        return verify_pilot_state(plans=manifest.plans, products_by_id=products_by_id)
    finally:
        session.close()
        engine.dispose()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--xlsx", required=True, type=Path)
    ap.add_argument("--karzar-csv", required=True, type=Path)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--write-pilot-manifest", type=Path, default=None)
    ap.add_argument("--pilot-count", type=int, default=10)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--sku-manifest", type=Path)
    ap.add_argument("--expected-sku-count", type=int)
    ap.add_argument("--expected-workbook-sha256", type=str)
    ap.add_argument("--expected-rate", type=str)
    ap.add_argument("--confirm-production-write", action="store_true")
    ap.add_argument("--verify-after-apply", action="store_true")
    args = ap.parse_args(argv)

    catalog = load_workbook_catalog(args.xlsx)
    checksum = verify_control_sku(catalog)
    print("[checksum]", json.dumps(checksum, ensure_ascii=False))
    if not checksum.get("ok"):
        print("FATAL: PRICE_CALCULATION_MISMATCH on control SKU — stop.", file=sys.stderr)
        return 3

    wb_sha = workbook_sha256(args.xlsx)
    print(f"[workbook_sha256] {wb_sha}")

    products = _load_karzar_csv(args.karzar_csv)
    result = reconcile(catalog=catalog, products=products)
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "reconciliation_summary.json", result["summary"])
    _write_json(out / "control_checksum.json", result["control_checksum"])
    _write_csv(out / "matched_rows.csv", result["matched_rows"])
    for name, rows in result["buckets"].items():
        payload = rows if isinstance(rows, list) else []
        if payload and isinstance(payload[0], str):
            _write_csv(out / f"bucket_{name}.csv", [{"sku_or_code": x} for x in payload])
        else:
            _write_csv(out / f"bucket_{name}.csv", payload)

    funnel = result["summary"]["funnel"]
    print("=== INSIZE RECONCILE FUNNEL ===")
    for k, v in funnel.items():
        print(f"{k}: {v}")

    manifest_path = args.write_pilot_manifest
    if manifest_path is None and not args.apply:
        # Always refresh the tracked fixture when reconciling for pilot prep.
        manifest_path = DEFAULT_MANIFEST

    if manifest_path is not None and not args.apply:
        ready = result["buckets"]["READY_FOR_SALES_ACTIVATION"]
        manifest = select_pilot_plans(
            ready_rows=ready,
            catalog=catalog,
            workbook_sha=wb_sha,
            count=args.pilot_count,
        )
        _write_json(manifest_path, manifest.to_public_dict())
        _write_json(out / "pilot_manifest_v1.json", manifest.to_public_dict())
        preview = [
            {
                "sku": p.sku,
                "current": str(p.current_base_price),
                "new": str(p.new_base_price),
                "pct": p.percentage_delta,
                "category": p.category_name,
            }
            for p in manifest.plans
        ]
        _write_json(out / "pilot_before_after_preview.json", preview)
        print(f"[pilot_manifest] {manifest_path}")
        print(f"[checkout_test_sku] {manifest.checkout_test_sku}")
        for p in preview:
            print(
                f"  {p['sku']}: {p['current']} → {p['new']} "
                f"({p['pct']:.2f}%) [{p['category']}]"
            )

    if args.apply:
        required = [
            args.sku_manifest,
            args.expected_sku_count,
            args.expected_workbook_sha256,
            args.expected_rate,
            args.confirm_production_write,
        ]
        if not all(required):
            print(
                "FATAL: --apply requires --sku-manifest, --expected-sku-count, "
                "--expected-workbook-sha256, --expected-rate, "
                "and --confirm-production-write",
                file=sys.stderr,
            )
            return 2
        # Category B production write gate (ingestion policy)
        if os.getenv("KARZAR_ALLOW_PRODUCTION_WRITE", "").strip() != "1":
            print(
                "FATAL: set KARZAR_ALLOW_PRODUCTION_WRITE=1 for production apply",
                file=sys.stderr,
            )
            return 2
        if os.getenv("KARZAR_INGESTION_CATEGORY", "").strip().upper() != "B":
            print(
                "FATAL: set KARZAR_INGESTION_CATEGORY=B for production apply",
                file=sys.stderr,
            )
            return 2
        try:
            manifest = load_pilot_manifest(args.sku_manifest)
            apply_result = _run_apply(
                manifest=manifest,
                catalog=catalog,
                live_products=products,
                expected_count=int(args.expected_sku_count),
                expected_sha=str(args.expected_workbook_sha256),
                expected_rate=Decimal(str(args.expected_rate)),
                xlsx=args.xlsx,
            )
            _write_json(out / "pilot_apply_audit.json", apply_result)
            print("[apply] ok", json.dumps({"updated": len(apply_result["updated"])}))
            if args.verify_after_apply:
                v = _run_verify_only(manifest=manifest)
                _write_json(out / "pilot_verify.json", v)
                print("[verify] ok", json.dumps(v))
        except PilotGateError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            return 4
        return 0

    if args.verify_after_apply:
        if not args.sku_manifest:
            print("FATAL: --verify-after-apply requires --sku-manifest", file=sys.stderr)
            return 2
        try:
            manifest = load_pilot_manifest(args.sku_manifest)
            v = _run_verify_only(manifest=manifest)
            _write_json(out / "pilot_verify.json", v)
            print("[verify] ok", json.dumps(v))
        except PilotGateError as exc:
            print(f"FATAL: {exc}", file=sys.stderr)
            return 4

    print(f"reports → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
