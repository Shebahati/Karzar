#!/usr/bin/env python3
"""Discover & download official Mitutoyo EU/UK leaflets (dimensional metrology).

Primary hub (often JS / currently 503 on shop HTML):
  https://shop.mitutoyo.eu/web/mitutoyo/en/leaflets.xhtml

Working asset CDN (official, no dealer watermarks):
  https://shop.mitutoyo.eu/media/mitutoyoData/DO/base/
  https://mitutoyo.eu/uk/resources/literature/*  (PRE codes → DO/base PDFs)

Does NOT touch product prices, stock, or availability.

Usage:
  .venv/bin/python scripts/mitutoyo_leaflets_discover.py --download
  .venv/bin/python scripts/mitutoyo_leaflets_discover.py --probe-hub
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "data" / "imports" / "mitutoyo" / "leaflets_eu"
PDF_DIR = OUT_DIR / "pdfs"
MANIFEST = OUT_DIR / "leaflets_manifest.json"
UA = "Mozilla/5.0 (compatible; KarzarMitutoyoLeafletBot/1.0; +https://www.karzartools.com)"

LEAFLETS_HUB = "https://shop.mitutoyo.eu/web/mitutoyo/en/leaflets.xhtml"
DO_BASE = "https://shop.mitutoyo.eu/media/mitutoyoData/DO/base/"
LITERATURE_HUB = "https://mitutoyo.eu/uk/resources/literature/small-tools-and-data-management"

# Official PRE / catalog codes observed on mitutoyo.eu literature (small tools)
# and confirmed live on DO/base CDN. Quality over coverage — extend carefully.
KNOWN_DO_FILES: list[tuple[str, str]] = [
    ("PRE1563", "pre_1563_-_digimatic_calipers_web_new.pdf"),
    ("PRE1504", "PRE 1504 - ABSOLUTE Digimatic Calipers_WEB.pdf"),
    ("PRE1429", "PRE 1429 - Dedicated Micrometers and Calipers_WEB.pdf"),
    ("PRE1569", "PRE 1569 - ABS Digimatic Height Gage Series 570_WEB.pdf"),
    ("PRE1564", "PRE 1564 - Digimatic Height Gauge_WEB.pdf"),
    ("PRE1582", "PRE 1582 - High-Accuracy Height Gage - Linear Height LH-600F/FG_WEB.pdf"),
    ("PRE1441", "PRE 1441 - Micrometer Heads_WEB.pdf"),
    ("PRE1515", "PRE 1515 - QM-Height Series_WEB.pdf"),
    ("PRE1502", "PRE 1502 - Data Management Systems_WEB.pdf"),
    ("PRE1604", "PRE 1604 - Measurement Data Management System_WEB.pdf"),
    ("PRE1533", "PRE 1533 - SJ-210,310 SERIES_WEB.pdf"),
    ("PRE1278", "PRE 1278 - Spring Promotion 2026_WEB.pdf"),
    # Promo / styli — SKU overlap limited; kept for completeness of official set
    ("PRE1316", "PRE 1316 - KOMEGPromo2025_WEB.pdf"),
    ("PRE1596", "PRE 1596 - OEM Brochure_WEB.pdf"),
]

# Corporate mirrors (same official content)
CORP_MIRRORS: list[tuple[str, str]] = [
    ("PRE1563", "https://mitutoyo.eu/application/files/6716/8605/8431/PRE_1563_-_Digimatic_Calipers_WEB.pdf"),
    ("PRE1278", "https://mitutoyo.eu/application/files/1117/7493/7849/PRE_1278_-_Spring_Promotion_2026_WEB.pdf"),
]


def http_head(url: str, timeout: float = 25) -> tuple[int, dict[str, str]]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception:  # noqa: BLE001
        return 0, {}


def http_get_bytes(url: str, timeout: float = 120) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read() if exc.fp else b""
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc).encode()


def probe_hub() -> dict:
    code, _ = http_head(LEAFLETS_HUB)
    lit_code, _ = http_head(LITERATURE_HUB)
    do_sample = DO_BASE + urllib.parse.quote("pre_1563_-_digimatic_calipers_web_new.pdf")
    do_code, do_hdr = http_head(do_sample)
    return {
        "leaflets_hub": LEAFLETS_HUB,
        "leaflets_hub_status": code,
        "literature_hub": LITERATURE_HUB,
        "literature_hub_status": lit_code,
        "do_base_sample": do_sample,
        "do_base_status": do_code,
        "do_base_content_type": do_hdr.get("content-type"),
        "notes": [
            "shop leaflets.xhtml has been 503 (service unavailable) during enrichment runs",
            "official PDF CDN media/mitutoyoData/DO/base/ remains reachable",
            "mitutoyo.eu literature page is JS-heavy; PRE codes map to DO/base filenames",
            "never use watermarked dealer sites (e.g. mitutoyoiran) as SoT",
        ],
    }


def safe_filename(code: str, remote_name: str) -> str:
    stem = re.sub(r"[^\w.\-]+", "_", remote_name).strip("_")
    if not stem.lower().endswith(".pdf"):
        stem += ".pdf"
    return f"{code}_{stem}" if not stem.upper().startswith(code.upper()) else stem


def download_known(*, force: bool = False) -> list[dict]:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for code, name in KNOWN_DO_FILES:
        url = DO_BASE + urllib.parse.quote(name)
        dest = PDF_DIR / safe_filename(code, name)
        row = {
            "code": code,
            "source": "do_base",
            "url": url,
            "path": str(dest.relative_to(PROJECT_ROOT)),
            "status": "",
            "bytes": 0,
        }
        if dest.exists() and dest.stat().st_size > 50_000 and not force:
            row["status"] = "exists"
            row["bytes"] = dest.stat().st_size
            rows.append(row)
            print(f"[skip] {dest.name} ({row['bytes']} bytes)")
            continue
        status, body = http_get_bytes(url)
        if status == 200 and body.startswith(b"%PDF"):
            dest.write_bytes(body)
            row["status"] = "downloaded"
            row["bytes"] = len(body)
            print(f"[ok] {dest.name} ({len(body)} bytes)")
        else:
            row["status"] = f"fail_{status}"
            print(f"[fail] {code} {name} -> {status}")
        rows.append(row)
        time.sleep(0.05)

    for code, url in CORP_MIRRORS:
        dest = PDF_DIR / f"corp_{code}.pdf"
        row = {
            "code": code,
            "source": "mitutoyo.eu_application_files",
            "url": url,
            "path": str(dest.relative_to(PROJECT_ROOT)),
            "status": "",
            "bytes": 0,
        }
        if dest.exists() and dest.stat().st_size > 50_000 and not force:
            row["status"] = "exists"
            row["bytes"] = dest.stat().st_size
            rows.append(row)
            continue
        status, body = http_get_bytes(url)
        if status == 200 and body.startswith(b"%PDF"):
            dest.write_bytes(body)
            row["status"] = "downloaded"
            row["bytes"] = len(body)
            print(f"[ok] {dest.name}")
        else:
            row["status"] = f"fail_{status}"
            print(f"[fail] corp {code} -> {status}")
        rows.append(row)
    return rows


def write_manifest(hub: dict, downloads: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "hub_probe": hub,
        "downloads": downloads,
        "policy": {
            "sku_match": "exact Mitutoyo order No. / site SKU token only",
            "forbidden": [
                "price",
                "base_price",
                "original_price",
                "sale_price",
                "list_price",
                "discount",
                "stock_quantity",
                "is_available",
                "availability",
            ],
            "allowed_enrichment": [
                "short_description",
                "description",
                "meta_title",
                "meta_description",
                "specifications.technical_specs",
                "specifications.features (factual flags only)",
            ],
        },
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_path = OUT_DIR / "leaflets_downloaded.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["code", "source", "url", "path", "status", "bytes"]
        )
        writer.writeheader()
        writer.writerows(downloads)
    print(f"Wrote {MANIFEST} and {csv_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-hub", action="store_true", help="Probe leaflets hub + CDN")
    parser.add_argument("--download", action="store_true", help="Download known official PDFs")
    parser.add_argument("--force", action="store_true", help="Re-download even if present")
    args = parser.parse_args()
    if not args.probe_hub and not args.download:
        parser.error("Use --probe-hub and/or --download")

    hub = probe_hub() if (args.probe_hub or args.download) else {}
    if args.probe_hub or not args.download:
        print(json.dumps(hub, ensure_ascii=False, indent=2))

    downloads: list[dict] = []
    if args.download:
        downloads = download_known(force=args.force)
    write_manifest(hub, downloads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
