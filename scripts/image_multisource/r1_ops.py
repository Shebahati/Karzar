"""IMG-02C-01 R1 live ops: research ledger, PDP/PDF calibration, bulk discovery."""

from __future__ import annotations

import csv
import hashlib
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.error import URLError

from . import BATCH_ID, NODE_ID, TASK_ID, MultisourceError
from .adapters_pdf import (
    discover_pdf_sku,
    index_skus_in_pdf,
    pdf_page_count,
    pdf_tools_available,
    render_pdf_page_jpeg,
)
from .adapters_retail import (
    evaluate_pdp,
    extract_abzarham_product_images,
    extract_abzarmarket_product_images,
    index_product_urls_by_sku,
    lookup_catalog_url,
    parse_abzarmarket_brand_catalog,
    parse_sitemap_locs,
)
from .calibrate import CalibrationResult, calibrate_source, summarize_calibrations
from .eligibility import build_eligibility_report, write_eligibility_report
from .http_fetch import USER_AGENT, fetch_url
from .matching import classify_match, host_allowed
from .output import (
    assert_external_output,
    ensure_absent_or_empty,
    write_checksums,
    write_csv,
    write_json,
)
from .quality import group_duplicates, inspect_image_bytes, sha256_bytes
from .registry import SourceDeclaration, builtin_r1_registry, sort_sources, write_registry_snapshot
from .robots import classify_robots_text

RELATION_FIELDS = [
    "schema_version",
    "task_id",
    "node_id",
    "batch_id",
    "product_id",
    "product_key",
    "sku",
    "brand_key",
    "work_type",
    "priority",
    "source_id",
    "source_class",
    "source_detail_url",
    "source_image_url",
    "match_basis",
    "discovery_status",
    "eligible_for_automatic_acceptance",
    "rights_status",
    "apply_status",
    "notes",
]

EU261_URL = "https://www.tosag.ch/mediafiles/kataloge/CATALOGUE-NO-EU261.pdf"
ABZARHAM_SITEMAPS = [
    f"https://abzarham.com/product-sitemap{i}.xml" for i in range(1, 5)
]
RESEARCH_FIELDS = [
    "source_id",
    "brand",
    "source_class",
    "page_host",
    "asset_hosts",
    "country",
    "authorization_status",
    "authorization_evidence_url",
    "authorization_evidence_type",
    "robots_status",
    "exact_sku_support",
    "exact_model_support",
    "catalog_pdf_support",
    "redirect_behavior",
    "sample_products_attempted",
    "successful_exact_matches",
    "false_matches",
    "parser_drift_rate",
    "enable_decision",
    "decision_reason",
]


def _load_worklist(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _seed_sha_set(r2_seed: Path) -> set[str]:
    out: set[str] = set()
    inv = None
    if r2_seed.is_dir():
        cand = r2_seed / "asset-hash-inventory.csv"
        if cand.is_file():
            inv = cand
    elif r2_seed.is_file() and r2_seed.suffix.casefold() == ".zip":
        with zipfile.ZipFile(r2_seed) as zf:
            for name in zf.namelist():
                if name.replace("\\", "/").endswith("asset-hash-inventory.csv"):
                    text = zf.read(name).decode("utf-8-sig")
                    import io

                    for row in csv.DictReader(io.StringIO(text)):
                        sha = (row.get("sha256") or "").strip()
                        if sha:
                            out.add(sha)
                    return out
    if inv is not None:
        for row in csv.DictReader(inv.open(encoding="utf-8-sig")):
            sha = (row.get("sha256") or "").strip()
            if sha:
                out.add(sha)
    return out


def _eligible_rows(worklist: list[dict[str, str]], eligibility: dict[str, Any]) -> list[dict[str, str]]:
    ids = set(eligibility["remaining_eligible_product_ids"])
    rows = [r for r in worklist if (r.get("product_id") or "") in ids]
    rows.sort(key=lambda r: (r.get("brand_key") or "", int(r.get("product_id") or 0)))
    return rows


def _fetch_text(url: str, *, delay: float) -> tuple[str, str]:
    status, final, data = fetch_url(url, delay=delay, max_bytes=5_000_000)
    if status >= 400:
        raise MultisourceError("live", f"HTTP {status} for {url}")
    return final, data.decode("utf-8", errors="replace")


def build_research_ledger_rows(sources: list[SourceDeclaration]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for s in sort_sources(sources):
        rows.append(
            {
                "source_id": s.source_id,
                "brand": "|".join(s.brand_keys),
                "source_class": s.source_class,
                "page_host": "|".join(s.allowed_page_hosts),
                "asset_hosts": "|".join(s.allowed_asset_hosts),
                "country": s.country,
                "authorization_status": s.authorization_status,
                "authorization_evidence_url": s.authorization_evidence,
                "authorization_evidence_type": (
                    "catalog_pdf"
                    if s.catalog_pdf_supported
                    else "brand_or_distributor_page"
                ),
                "robots_status": s.robots_status,
                "exact_sku_support": str(s.exact_sku_supported).lower(),
                "exact_model_support": str(s.exact_sku_supported).lower(),
                "catalog_pdf_support": str(s.catalog_pdf_supported).lower(),
                "redirect_behavior": "host_allowlist_fail_closed",
                "sample_products_attempted": "",
                "successful_exact_matches": "",
                "false_matches": "",
                "parser_drift_rate": "",
                "enable_decision": "pending_calibration",
                "decision_reason": s.notes,
            }
        )
    return rows


def _prefer_catalog_sample(
    rows: list[dict[str, str]],
    catalog_index: dict[str, str],
    *,
    brand_keys: set[str],
    limit: int,
) -> list[dict[str, str]]:
    pool = [r for r in rows if (r.get("brand_key") or "") in brand_keys]
    hits = []
    misses = []
    for r in pool:
        url, kind = lookup_catalog_url(catalog_index, r.get("sku") or "")
        if kind == "exact":
            hits.append(r)
        else:
            misses.append(r)
    # Include one near-miss / absent for negative coverage when available
    ordered = hits + misses
    return ordered[:limit]


class R1Context:
    def __init__(
        self,
        *,
        work_root: Path,
        delay: float = 0.8,
        seed_shas: set[str] | None = None,
    ) -> None:
        self.work_root = work_root
        self.delay = delay
        self.seed_shas = seed_shas or set()
        self.cache = work_root / "cache"
        self.cache.mkdir(parents=True, exist_ok=True)
        self.abzarham_index: dict[str, str] = {}
        self.abzarmarket_index: dict[str, str] = {}
        self.pdf_path: Path | None = None
        self.pdf_bytes: bytes | None = None
        self.pdf_hits: dict[str, Any] = {}
        self.robots: dict[str, str] = {}
        self.page_render_cache: dict[int, Path] = {}

    def load_robots(self, source: SourceDeclaration, probe_url: str) -> str:
        if source.source_id in self.robots:
            return self.robots[source.source_id]
        host = source.allowed_page_hosts[0]
        url = f"https://{host}/robots.txt"
        try:
            _final, text = _fetch_text(url, delay=self.delay)
        except (MultisourceError, URLError, TimeoutError, OSError):
            text = "User-agent: *\nDisallow:\n"
        self.robots[source.source_id] = text
        # validate probe path
        rob = classify_robots_text(text, user_agent=USER_AGENT, url=probe_url)
        if rob["crawl_permitted"] != "true":
            raise MultisourceError(
                "robots",
                f"{source.source_id} robots disallow probe url {probe_url}",
            )
        return text

    def ensure_abzarham_index(self) -> dict[str, str]:
        if self.abzarham_index:
            return self.abzarham_index
        locs: list[str] = []
        for sm in ABZARHAM_SITEMAPS:
            _f, xml = _fetch_text(sm, delay=self.delay)
            locs.extend(parse_sitemap_locs(xml))
        self.abzarham_index = index_product_urls_by_sku(locs)
        write_json(self.cache / "abzarham-sku-index.json", {"count": len(self.abzarham_index), "index": self.abzarham_index})
        return self.abzarham_index

    def ensure_abzarmarket_index(self) -> dict[str, str]:
        if self.abzarmarket_index:
            return self.abzarmarket_index
        index: dict[str, str] = {}
        for brand in ("dasqua", "insize"):
            _f, html = _fetch_text(f"https://abzarmarket.com/brand/{brand}", delay=self.delay)
            index.update(parse_abzarmarket_brand_catalog(html))
        self.abzarmarket_index = index
        write_json(
            self.cache / "abzarmarket-sku-index.json",
            {"count": len(index), "index": index},
        )
        return index

    def ensure_eu261(self, eligible_skus: list[str]) -> None:
        if self.pdf_path and self.pdf_bytes is not None and self.pdf_hits:
            return
        if not pdf_tools_available():
            raise MultisourceError("pdf", "pdftotext/pdftoppm/pdfinfo required for EU261")
        dest = self.cache / "CATALOGUE-NO-EU261.pdf"
        if not dest.is_file():
            status, _final, data = fetch_url(EU261_URL, delay=self.delay, max_bytes=60_000_000, timeout=120)
            if status >= 400 or not data.startswith(b"%PDF"):
                raise MultisourceError("pdf", f"EU261 download failed status={status}")
            dest.write_bytes(data)
        self.pdf_path = dest
        self.pdf_bytes = dest.read_bytes()
        self.pdf_hits = index_skus_in_pdf(dest, eligible_skus)
        write_json(
            self.cache / "eu261-sku-index.json",
            {
                "sha256": sha256_bytes(self.pdf_bytes),
                "pages": pdf_page_count(dest),
                "hits": {
                    k: {"page": v.page_number, "others": list(v.other_skus_on_page)}
                    for k, v in self.pdf_hits.items()
                },
            },
        )

    def render_page(self, page_number: int) -> Path:
        assert self.pdf_path is not None
        if page_number in self.page_render_cache:
            return self.page_render_cache[page_number]
        stem = self.cache / "pdf-pages" / f"eu261-p{page_number}"
        path = render_pdf_page_jpeg(self.pdf_path, page_number, stem)
        self.page_render_cache[page_number] = path
        return path


def probe_for_source(ctx: R1Context, source: SourceDeclaration):
    def _probe(_src: SourceDeclaration, row: dict[str, str]) -> dict[str, Any]:
        sku = (row.get("sku") or "").strip()
        pid = (row.get("product_id") or "").strip()
        brand = (row.get("brand_key") or "").strip()
        base = {
            "product_id": pid,
            "sku": sku,
            "brand_key": brand,
        }
        try:
            if source.source_id == "insize_eu261_pdf":
                from .sku_norm import normalize_sku

                hit = ctx.pdf_hits.get(normalize_sku(sku))
                rendered = None
                if hit is not None:
                    rendered = ctx.render_page(hit.page_number)
                result = discover_pdf_sku(
                    pdf_path=ctx.pdf_path,  # type: ignore[arg-type]
                    pdf_bytes=ctx.pdf_bytes or b"",
                    catalog_url=EU261_URL,
                    sku=sku,
                    hit=hit,
                    rendered_page_path=rendered,
                )
                result.update(base)
                result["redirect_ok"] = True
                result["asset_host_ok"] = bool(rendered)
                return result

            if source.source_id == "abzarham_sitemap":
                index = ctx.ensure_abzarham_index()
                url, kind = lookup_catalog_url(index, sku)
                if not url:
                    return {
                        **base,
                        "status": "not_found",
                        "exact_sku_ok": False,
                        "false_match": False,
                        "page_identity_ok": False,
                        "parser_drift": False,
                        "redirect_ok": True,
                        "asset_host_ok": False,
                        "notes": "sku_absent_from_sitemap_index",
                    }
                if kind == "family":
                    # Do not fetch family as exact calibration success
                    status, final, data = fetch_url(url, delay=ctx.delay)
                    html = data.decode("utf-8", errors="replace")
                    imgs = extract_abzarham_product_images(html, sku=sku)
                    ev = evaluate_pdp(
                        sku=sku,
                        brand_key=brand,
                        final_url=final,
                        html=html,
                        expected_match_kind="family",
                        image_urls=imgs,
                    )
                    ev.update(base)
                    return ev
                status, final, data = fetch_url(url, delay=ctx.delay)
                if status >= 400:
                    return {
                        **base,
                        "status": "fetch_error",
                        "exact_sku_ok": False,
                        "false_match": False,
                        "page_identity_ok": False,
                        "parser_drift": True,
                        "redirect_ok": host_allowed(final, source.allowed_page_hosts),
                        "asset_host_ok": False,
                        "notes": f"http_{status}",
                    }
                if not host_allowed(final, source.allowed_page_hosts):
                    return {
                        **base,
                        "status": "false_match",
                        "exact_sku_ok": False,
                        "false_match": True,
                        "page_identity_ok": False,
                        "parser_drift": False,
                        "redirect_ok": False,
                        "asset_host_ok": False,
                        "notes": "unapproved_redirect",
                    }
                html = data.decode("utf-8", errors="replace")
                imgs = extract_abzarham_product_images(html, sku=sku)
                ev = evaluate_pdp(
                    sku=sku,
                    brand_key=brand,
                    final_url=final,
                    html=html,
                    expected_match_kind=kind,
                    image_urls=imgs,
                )
                ev.update(base)
                return ev

            if source.source_id == "abzarmarket_brand_catalog":
                index = ctx.ensure_abzarmarket_index()
                url, kind = lookup_catalog_url(index, sku)
                if not url:
                    return {
                        **base,
                        "status": "not_found",
                        "exact_sku_ok": False,
                        "false_match": False,
                        "page_identity_ok": False,
                        "parser_drift": False,
                        "redirect_ok": True,
                        "asset_host_ok": False,
                        "notes": "sku_absent_from_brand_catalog",
                    }
                status, final, data = fetch_url(url, delay=ctx.delay)
                if status >= 400 or not host_allowed(final, source.allowed_page_hosts):
                    return {
                        **base,
                        "status": "fetch_error",
                        "exact_sku_ok": False,
                        "false_match": False,
                        "page_identity_ok": False,
                        "parser_drift": True,
                        "redirect_ok": host_allowed(final, source.allowed_page_hosts),
                        "asset_host_ok": False,
                        "notes": f"http_{status}",
                    }
                html = data.decode("utf-8", errors="replace")
                imgs = extract_abzarmarket_product_images(html)
                ev = evaluate_pdp(
                    sku=sku,
                    brand_key=brand,
                    final_url=final,
                    html=html,
                    expected_match_kind=kind,
                    image_urls=imgs,
                )
                ev.update(base)
                return ev

            return {
                **base,
                "status": "skipped",
                "exact_sku_ok": False,
                "false_match": False,
                "page_identity_ok": False,
                "parser_drift": False,
                "redirect_ok": True,
                "asset_host_ok": False,
                "notes": "no_r1_adapter_for_source",
            }
        except (MultisourceError, URLError, TimeoutError, OSError) as exc:
            return {
                **base,
                "status": "fetch_error",
                "exact_sku_ok": False,
                "false_match": False,
                "page_identity_ok": False,
                "parser_drift": True,
                "redirect_ok": True,
                "asset_host_ok": False,
                "notes": f"error:{type(exc).__name__}:{exc}",
            }

    return _probe


def _relation_from_match(
    *,
    row: dict[str, str],
    source: SourceDeclaration,
    probe_result: dict[str, Any],
) -> dict[str, str] | None:
    status = probe_result.get("status")
    if status == "family_only":
        return {
            "schema_version": "1",
            "task_id": TASK_ID,
            "node_id": NODE_ID,
            "batch_id": BATCH_ID,
            "product_id": row.get("product_id") or "",
            "product_key": row.get("product_key") or "",
            "sku": row.get("sku") or "",
            "brand_key": row.get("brand_key") or "",
            "work_type": row.get("work_type") or "",
            "priority": row.get("priority") or "",
            "source_id": source.source_id,
            "source_class": source.source_class,
            "source_detail_url": probe_result.get("final_url") or "",
            "source_image_url": (probe_result.get("image_urls") or [""])[0],
            "match_basis": "family_variant_slug",
            "discovery_status": "manual_review",
            "eligible_for_automatic_acceptance": "false",
            "rights_status": "review_required",
            "apply_status": "not_started",
            "notes": probe_result.get("notes") or "",
        }
    if status != "matched":
        return None
    detail = probe_result.get("source_detail_url") or probe_result.get("final_url") or ""
    image = probe_result.get("source_image_url") or ""
    # Prefer classify_match for host/SKU gates when we have page text cues
    classified = {
        "discovery_status": probe_result.get("discovery_status") or "manual_review",
        "eligible_for_automatic_acceptance": probe_result.get(
            "eligible_for_automatic_acceptance"
        )
        or "false",
        "match_basis": probe_result.get("match_basis") or "",
    }
    # Preserve multi-SKU catalog / family quarantine; only host-validate otherwise.
    preserve_review = classified.get("discovery_status") in {
        "manual_review",
        "retailer_review",
    }
    if detail and image and probe_result.get("exact_sku_ok") and not preserve_review:
        asset_for_host = image if image.startswith("http") else detail
        cm = classify_match(
            source=source,
            product_id=row.get("product_id") or "",
            sku=row.get("sku") or "",
            brand_key=row.get("brand_key") or "",
            page_url=detail,
            asset_url=asset_for_host,
            page_text=f"{row.get('sku')} {row.get('brand_key')}",
            match_basis=classified["match_basis"] or "exact_sku_product_page",
            brand_confirmed=bool(probe_result.get("brand_confirmed", True)),
            subject_exact=True,
            redirect_approved=bool(probe_result.get("redirect_ok", True)),
        )
        if cm["discovery_status"] == "rejected":
            return {
                "schema_version": "1",
                "task_id": TASK_ID,
                "node_id": NODE_ID,
                "batch_id": BATCH_ID,
                "product_id": row.get("product_id") or "",
                "product_key": row.get("product_key") or "",
                "sku": row.get("sku") or "",
                "brand_key": row.get("brand_key") or "",
                "work_type": row.get("work_type") or "",
                "priority": row.get("priority") or "",
                "source_id": source.source_id,
                "source_class": source.source_class,
                "source_detail_url": detail,
                "source_image_url": image,
                "match_basis": "",
                "discovery_status": "rejected",
                "eligible_for_automatic_acceptance": "false",
                "rights_status": "review_required",
                "apply_status": "not_started",
                "notes": cm.get("reason_code") or "",
            }
        classified = cm
    return {
        "schema_version": "1",
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "batch_id": BATCH_ID,
        "product_id": row.get("product_id") or "",
        "product_key": row.get("product_key") or "",
        "sku": row.get("sku") or "",
        "brand_key": row.get("brand_key") or "",
        "work_type": row.get("work_type") or "",
        "priority": row.get("priority") or "",
        "source_id": source.source_id,
        "source_class": source.source_class,
        "source_detail_url": detail,
        "source_image_url": image,
        "match_basis": classified.get("match_basis") or "",
        "discovery_status": classified.get("discovery_status") or "manual_review",
        "eligible_for_automatic_acceptance": classified.get(
            "eligible_for_automatic_acceptance"
        )
        or "false",
        "rights_status": "review_required",
        "apply_status": "not_started",
        "notes": probe_result.get("notes") or "",
        "_local_page_image": probe_result.get("local_page_image") or "",
        "_image_urls": probe_result.get("image_urls") or [],
    }


def _store_asset(
    *,
    assets_dir: Path,
    source_id: str,
    product_id: str,
    sku: str,
    source_image_url: str,
    data: bytes,
    seed_shas: set[str],
) -> dict[str, str] | None:
    meta = inspect_image_bytes(data)
    if meta.get("quality_status") != "ok":
        return None
    sha = meta["sha256"]
    if sha in seed_shas:
        return {
            "asset_id": sha[:16],
            "sha256": sha,
            "skipped_seed_redownload": "true",
            "source_image_url": source_image_url,
            "quality_status": "skipped_seed",
        }
    fname = f"{source_id}__{product_id}__{sku.replace('/', '_')}__{sha[:12]}.jpg"
    path = assets_dir / fname
    if not path.is_file():
        path.write_bytes(data)
    return {
        "asset_id": sha[:16],
        "sha256": sha,
        "perceptual_hash": meta.get("perceptual_hash") or "",
        "source_image_url": source_image_url,
        "width": str(meta.get("width") or ""),
        "height": str(meta.get("height") or ""),
        "format": meta.get("format") or "",
        "byte_size": str(meta.get("byte_size") or ""),
        "quality_status": "ok",
        "watermark_status": meta.get("watermark_status") or "review_required",
        "local_asset_path": str(path),
    }


def run_r1_bulk(
    *,
    worklist_csv: Path,
    r2_seed: Path,
    output_dir: Path,
    repo_root: Path,
    work_root: Path,
    delay: float = 0.8,
    relation_cap: int = 400,
    calibration_limit: int = 20,
) -> dict[str, Any]:
    out = assert_external_output(output_dir, repo_root)
    ensure_absent_or_empty(out)
    for sub in (
        "source-calibrations",
        "assets",
        "evidence",
        "cache-refs",
    ):
        (out / sub).mkdir()

    sources = builtin_r1_registry()
    write_registry_snapshot(sources, out / "source-registry-snapshot.json")
    eligibility = build_eligibility_report(worklist_csv=worklist_csv, r2_seed=r2_seed)
    write_eligibility_report(eligibility, out / "eligibility-report.json")
    worklist = _load_worklist(worklist_csv)
    eligible = _eligible_rows(worklist, eligibility)
    seed_shas = _seed_sha_set(r2_seed)

    ctx = R1Context(work_root=work_root, delay=delay, seed_shas=seed_shas)
    research_rows = build_research_ledger_rows(sources)

    # Prepare indexes / PDF for candidate sources
    insize_skus = [
        r["sku"] for r in eligible if r.get("brand_key") == "insize" and r.get("sku")
    ]
    ctx.ensure_eu261(insize_skus)
    ctx.ensure_abzarham_index()
    ctx.ensure_abzarmarket_index()

    enable_candidates = {
        "insize_eu261_pdf",
        "abzarham_sitemap",
        "abzarmarket_brand_catalog",
    }
    calib_results: list[CalibrationResult] = []
    for source in sort_sources(sources):
        if source.authorization_status == "unknown":
            result = calibrate_source(
                source=source,
                eligibility_report=eligibility,
                worklist_csv=worklist_csv,
                output_dir=out / "source-calibrations",
                limit=1,
                probe=lambda _s, _r: {
                    "product_id": "",
                    "sku": "",
                    "status": "skipped",
                    "page_identity_ok": False,
                    "exact_sku_ok": False,
                    "false_match": False,
                    "redirect_ok": True,
                    "generic_category": False,
                    "parser_drift": False,
                    "asset_host_ok": False,
                    "notes": "unknown authorization — not probed",
                },
            )
            result.enabled_after_calibration = False
            result.disable_reason = "unknown_authorization"
            write_json(out / "source-calibrations" / f"{source.source_id}.json", result.to_dict())
            calib_results.append(result)
            continue

        if source.source_id not in enable_candidates:
            skip_notes = source.notes or "not selected for R1 enablement path"

            def _skip_probe(_s: SourceDeclaration, row: dict[str, str], notes: str = skip_notes) -> dict[str, Any]:
                return {
                    "product_id": row.get("product_id") or "",
                    "sku": row.get("sku") or "",
                    "status": "skipped",
                    "page_identity_ok": False,
                    "exact_sku_ok": False,
                    "false_match": False,
                    "redirect_ok": True,
                    "generic_category": False,
                    "parser_drift": False,
                    "asset_host_ok": False,
                    "notes": notes,
                }

            result = calibrate_source(
                source=source,
                eligibility_report=eligibility,
                worklist_csv=worklist_csv,
                output_dir=out / "source-calibrations",
                limit=min(5, calibration_limit),
                probe=_skip_probe,
            )
            result.enabled_after_calibration = False
            result.disable_reason = "not_selected_for_r1_or_prior_failure"
            write_json(out / "source-calibrations" / f"{source.source_id}.json", result.to_dict())
            calib_results.append(result)
            continue

        # robots probe URL must be an allowed discovery path
        if source.source_id == "insize_eu261_pdf":
            probe_url = EU261_URL
            sample = [
                r
                for r in eligible
                if r.get("brand_key") == "insize"
                and (r.get("sku") or "").strip().casefold() in ctx.pdf_hits
            ][:calibration_limit]
            # add negatives not in PDF
            negatives = [
                r
                for r in eligible
                if r.get("brand_key") == "insize"
                and (r.get("sku") or "").strip().casefold() not in ctx.pdf_hits
            ][: max(0, min(3, calibration_limit - len(sample)))]
            sample = (sample + negatives)[:calibration_limit]
        elif source.source_id == "abzarham_sitemap":
            probe_url = "https://abzarham.com/product-sitemap1.xml"
            sample = _prefer_catalog_sample(
                eligible,
                ctx.abzarham_index,
                brand_keys={"dasqua", "insize"},
                limit=calibration_limit,
            )
        else:
            probe_url = "https://abzarmarket.com/brand/dasqua"
            sample = _prefer_catalog_sample(
                eligible,
                ctx.abzarmarket_index,
                brand_keys={"dasqua", "insize"},
                limit=calibration_limit,
            )

        robots_txt = ctx.load_robots(source, probe_url)
        result = calibrate_source(
            source=source,
            eligibility_report=eligibility,
            worklist_csv=worklist_csv,
            output_dir=out / "source-calibrations",
            limit=len(sample) or 1,
            robots_txt=robots_txt,
            robots_probe_url=probe_url,
            sample_rows=sample or eligible[:1],
            probe=probe_for_source(ctx, source),
        )
        calib_results.append(result)

        # update research ledger row
        for row in research_rows:
            if row["source_id"] == source.source_id:
                row["sample_products_attempted"] = str(result.sample_size)
                row["successful_exact_matches"] = str(result.exact_match_count)
                row["false_matches"] = str(result.false_match_count)
                row["parser_drift_rate"] = str(result.parser_drift_rate)
                row["robots_status"] = result.robots_status
                row["enable_decision"] = (
                    "enabled" if result.enabled_after_calibration else "disabled"
                )
                row["decision_reason"] = result.disable_reason or "calibration_passed"

    calib_summary = summarize_calibrations(calib_results)
    enabled_sources = [
        s
        for s in sort_sources(sources)
        if any(
            r.source_id == s.source_id and r.enabled_after_calibration for r in calib_results
        )
    ]
    enabled_classes = {s.source_class for s in enabled_sources}
    if len(enabled_sources) < 3 or len(enabled_classes) < 2:
        raise MultisourceError(
            "r1",
            f"enable gate failed: enabled={len(enabled_sources)} classes={sorted(enabled_classes)}",
        )

    # ---- bulk discovery ----
    relations: list[dict[str, Any]] = []
    assets: list[dict[str, str]] = []
    attempted = 0
    with_candidates = 0
    products_done: set[str] = set()

    # Prefer higher-priority sources first per product
    for row in eligible:
        if len(relations) >= relation_cap:
            break
        attempted += 1
        pid = row.get("product_id") or ""
        got = False
        for source in enabled_sources:
            if (row.get("brand_key") or "") not in source.brand_keys:
                continue
            probe = probe_for_source(ctx, source)
            pr = probe(source, row)
            rel = _relation_from_match(row=row, source=source, probe_result=pr)
            if rel is None:
                continue
            # materialize asset
            local = rel.pop("_local_page_image", "")
            rel.pop("_image_urls", None)
            data = None
            source_image_url = rel.get("source_image_url") or ""
            if local and Path(local).is_file():
                data = Path(local).read_bytes()
                # copy into package assets
            elif source_image_url.startswith("http"):
                try:
                    st, final, blob = fetch_url(source_image_url, delay=delay)
                    if st < 400 and host_allowed(final, source.allowed_asset_hosts):
                        data = blob
                        source_image_url = final
                        rel["source_image_url"] = final
                except (URLError, TimeoutError, OSError, MultisourceError):
                    data = None
            if data:
                asset = _store_asset(
                    assets_dir=out / "assets",
                    source_id=source.source_id,
                    product_id=pid,
                    sku=row.get("sku") or "sku",
                    source_image_url=source_image_url,
                    data=data,
                    seed_shas=seed_shas,
                )
                if asset and asset.get("quality_status") == "ok":
                    assets.append(asset)
                elif asset and asset.get("skipped_seed_redownload") == "true":
                    rel["notes"] = (rel.get("notes") or "") + "|skipped_seed_sha"
            relations.append(rel)
            got = True
            # one relation per product from highest-priority enabled source
            break
        if got:
            with_candidates += 1
            products_done.add(pid)

    # split queues
    stable = [r for r in relations if r.get("discovery_status") == "candidate_ready"]
    retailer = [r for r in relations if r.get("discovery_status") == "retailer_review"]
    manual = [r for r in relations if r.get("discovery_status") == "manual_review"]
    rejected = [r for r in relations if r.get("discovery_status") == "rejected"]

    write_csv(out / "candidate-relations.csv", relations, RELATION_FIELDS)
    write_csv(out / "stable-candidates.csv", stable, RELATION_FIELDS)
    write_csv(out / "retailer-review.csv", retailer, RELATION_FIELDS)
    write_csv(out / "manual-review.csv", manual, RELATION_FIELDS)
    write_csv(out / "rejected.csv", rejected, RELATION_FIELDS)

    asset_fields = [
        "asset_id",
        "sha256",
        "perceptual_hash",
        "source_image_url",
        "width",
        "height",
        "format",
        "byte_size",
        "quality_status",
        "watermark_status",
        "local_asset_path",
    ]
    write_csv(out / "asset-manifest.csv", assets, asset_fields)
    write_csv(out / "duplicate-groups.csv", group_duplicates(assets), ["group_key", "member_count", "asset_ids"])

    brand_cov: dict[str, Counter] = {}
    for r in relations:
        b = r.get("brand_key") or ""
        brand_cov.setdefault(b, Counter())[r.get("discovery_status") or ""] += 1
    rem_brand = eligibility["remaining_eligible_by_brand"]
    write_csv(
        out / "coverage-by-brand.csv",
        [
            {
                "brand_key": b,
                "remaining_eligible": str(rem_brand.get(b, 0)),
                "stable_candidates": str(brand_cov.get(b, {}).get("candidate_ready", 0)),
                "retailer_review": str(brand_cov.get(b, {}).get("retailer_review", 0)),
                "manual_review": str(brand_cov.get(b, {}).get("manual_review", 0)),
            }
            for b in sorted(set(rem_brand) | set(brand_cov))
        ],
        [
            "brand_key",
            "remaining_eligible",
            "stable_candidates",
            "retailer_review",
            "manual_review",
        ],
    )
    by_source = Counter(r.get("source_id") for r in relations)
    write_csv(
        out / "coverage-by-source.csv",
        [
            {"source_id": sid, "candidate_relations": str(cnt)}
            for sid, cnt in sorted(by_source.items())
        ],
        ["source_id", "candidate_relations"],
    )
    by_class = Counter(r.get("source_class") for r in relations)
    enabled_by_class = Counter(s.source_class for s in enabled_sources)
    write_csv(
        out / "coverage-by-source-class.csv",
        [
            {
                "source_class": c,
                "enabled_sources": str(enabled_by_class.get(c, 0)),
                "candidate_relations": str(by_class.get(c, 0)),
            }
            for c in ("S1", "S2", "S3", "S4", "S5")
        ],
        ["source_class", "enabled_sources", "candidate_relations"],
    )

    write_csv(out / "source-research-ledger.csv", research_rows, RESEARCH_FIELDS)
    auth_rows = [
        {
            "source_id": s.source_id,
            "authorization_status": s.authorization_status,
            "authorization_evidence_url": s.authorization_evidence,
            "evidence_type": "catalog_pdf" if s.catalog_pdf_supported else "page",
        }
        for s in sources
        if s.authorization_evidence
    ]
    write_csv(
        out / "authorization-evidence.csv",
        auth_rows,
        [
            "source_id",
            "authorization_status",
            "authorization_evidence_url",
            "evidence_type",
        ],
    )

    # evidence copies
    if ctx.pdf_path and ctx.pdf_path.is_file():
        evidence_pdf = out / "evidence" / "CATALOGUE-NO-EU261.sha256.txt"
        evidence_pdf.write_text(
            f"{sha256_bytes(ctx.pdf_bytes or b'')}  {EU261_URL}\n", encoding="utf-8"
        )
    shutil.copytree(ctx.cache, out / "cache-refs" / "work-cache", dirs_exist_ok=True)

    unique_images = len({a["sha256"] for a in assets if a.get("sha256")})
    summary = {
        "schema_version": 1,
        "task_id": TASK_ID,
        "node_id": NODE_ID,
        "batch_id": BATCH_ID,
        "phase": "r1_bulk_discovery",
        "progress_suggested": 60,
        "eligibility_totals": eligibility["totals"],
        "calibration": calib_summary,
        "enabled_sources": [s.source_id for s in enabled_sources],
        "enabled_source_classes": sorted(enabled_classes),
        "products_attempted": attempted,
        "products_with_candidates": with_candidates,
        "candidate_relations": len(relations),
        "stable_candidates": len(stable),
        "retailer_review_candidates": len(retailer),
        "manual_review_candidates": len(manual),
        "rejected_candidates": len(rejected),
        "unique_image_candidates": unique_images,
        "relation_cap": relation_cap,
        "stop_reason": (
            "relation_cap"
            if len(relations) >= relation_cap
            else "eligible_universe_exhausted"
        ),
        "rights_status": "review_required",
        "apply_status": "not_started",
        "safety": {
            "database_accessed": False,
            "ProductImage_modified": False,
            "application_storage_mutations": 0,
            "images_applied": 0,
            "replacement_execution": False,
            "rights_cleared": 0,
            "raw_generated_output_tracked_in_git": 0,
            "seed_assets_skipped": len(seed_shas),
        },
    }
    write_json(out / "summary.json", summary)
    (out / "README.md").write_text(
        "# IMG-02C-01-R1 Multisource Bulk Discovery\n\n"
        "Real source onboarding + bulk discovery package.\n"
        "rights_status=review_required; apply_status=not_started.\n"
        "Do not commit raw assets to Git.\n",
        encoding="utf-8",
    )

    members = [
        "source-research-ledger.csv",
        "authorization-evidence.csv",
        "source-registry-snapshot.json",
        "eligibility-report.json",
        "candidate-relations.csv",
        "stable-candidates.csv",
        "retailer-review.csv",
        "manual-review.csv",
        "rejected.csv",
        "asset-manifest.csv",
        "duplicate-groups.csv",
        "coverage-by-brand.csv",
        "coverage-by-source.csv",
        "coverage-by-source-class.csv",
        "summary.json",
        "README.md",
    ]
    digest = write_checksums(out, members)
    return {
        "output_dir": str(out),
        "checksums_digest": digest,
        "summary": summary,
        "calibration": calib_summary,
        "enabled_sources": [s.source_id for s in enabled_sources],
    }


def package_review_zip(output_dir: Path, zip_path: Path) -> str:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"{output_dir.name}/{path.relative_to(output_dir)}")
    h = hashlib.sha256()
    with zip_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
