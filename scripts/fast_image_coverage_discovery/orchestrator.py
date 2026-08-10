"""IMG-FAST-01B R2 wave orchestrator — multi-adapter failover."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .assets import is_tiny_tracker, materialize_asset
from .checkpoint import apply_checkpoint, load_checkpoint, save_checkpoint
from .contracts import (
    DiscoveryCandidate,
    DiscoveryRunState,
    ProductTerminalState,
    RunProduct,
)
from .identity import (
    classify_identity,
    normalize_sku,
    owner_policy_for_country,
    temporary_primary_eligible,
)
from .ordering import order_run_universe
from .sources.base import SourceAdapter
from .sources.html_index import HtmlIndexAdapter, brand_slug
from .sources.prior_artifact import PriorArtifactAdapter
from .sources.registry import DEFAULT_SOURCES, build_adapter
from .sources.sitemap import SitemapAdapter
from .sources.spec import allowed_page_hosts, is_iranian_domain
from .transport import MediaAwareFetcher, make_media_fetcher


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


WAVE_ORDER = (
    ("WAVE0", ("REUSE",)),
    ("WAVE1", ("IR-1",)),
    ("WAVE2", ("OFFICIAL",)),
    ("WAVE3", ("IR-2", "DIST")),
    ("WAVE4", ("WIDE",)),
)


def load_r1_identity_hits(r1_checkpoint: Path) -> list[dict[str, Any]]:
    """Recover ~15 R1 checkpoint terminals marked green_exact without assets."""
    if not r1_checkpoint.is_file():
        return []
    data = json.loads(r1_checkpoint.read_text(encoding="utf-8"))
    hits = []
    for pid_s, row in (data.get("terminals") or {}).items():
        if row.get("final_status") == "green_exact":
            hits.append(
                {
                    "product_id": int(pid_s),
                    "old_inferred_status": "green_exact",
                    "r1_materialization_failure": "asset_not_persisted_in_checkpoint",
                }
            )
    return hits


def write_brand_source_plan(
    path: Path,
    universe: list[RunProduct],
    adapters: dict[str, SourceAdapter],
    specs_by_id: dict[str, Any],
) -> list[dict[str, Any]]:
    brand_counts = Counter(p.brand_sort_key or "(none)" for p in universe)
    rows: list[dict[str, Any]] = []
    for brand, count in brand_counts.most_common():
        matched = False
        for sid, adapter in adapters.items():
            spec = specs_by_id.get(sid)
            if not spec:
                continue
            rows.append(
                {
                    "brand_key": brand,
                    "unresolved_products": count,
                    "source_id": sid,
                    "source_domain": adapter.domain,
                    "adapter_type": adapter.adapter_type,
                    "country": adapter.country,
                    "probe_status": (adapter.probe.failure_class if adapter.probe and adapter.probe.failure_class else ("ok" if adapter.probe and adapter.probe.reachable else "not_probed")),
                    "calibration_status": (
                        "passed"
                        if adapter.calibration and adapter.calibration.passed
                        else ("failed" if adapter.calibration else "pending")
                    ),
                    "bulk_enabled": adapter.bulk_enabled,
                    "expected_match_method": adapter.adapter_type,
                    "notes": getattr(spec, "notes", ""),
                }
            )
            if adapter.bulk_enabled:
                matched = True
        if count >= 20 and not matched:
            rows.append(
                {
                    "brand_key": brand,
                    "unresolved_products": count,
                    "source_id": "",
                    "source_domain": "",
                    "adapter_type": "",
                    "country": "",
                    "probe_status": "no_viable_source",
                    "calibration_status": "n/a",
                    "bulk_enabled": False,
                    "expected_match_method": "",
                    "notes": "no_bulk_enabled_source_after_investigation",
                }
            )
    fields = [
        "brand_key",
        "unresolved_products",
        "source_id",
        "source_domain",
        "adapter_type",
        "country",
        "probe_status",
        "calibration_status",
        "bulk_enabled",
        "expected_match_method",
        "notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return rows


def _candidate_from_hit(
    product: RunProduct,
    adapter: SourceAdapter,
    hit,
) -> DiscoveryCandidate:
    page_url = hit.page_url
    page_host = (urlparse(page_url).hostname or "").lower()
    country = adapter.country
    if is_iranian_domain(page_host):
        country = "IR"
    source_domain = page_host or adapter.domain
    policy = owner_policy_for_country(country)
    image_url = hit.image_urls[0] if hit.image_urls else ""
    status, match_type, brand_ev, sku_ev, reason = classify_identity(
        sku=product.sku,
        brand_key=product.brand_key,
        product_name=product.product_name,
        page_title=hit.title or product.product_name,
        page_text=f"{hit.title}\n{hit.brand_text}\n{page_url}",
        has_pdp_structure=bool(page_url),
        image_is_product_gallery=bool(image_url),
        source_country=country,
    )
    if status == "green_exact" and not image_url:
        status = "yellow_review"
        reason = "yellow_gallery_identity_weak"
    return DiscoveryCandidate(
        product_id=product.product_id,
        sku=product.sku,
        brand_key=product.brand_key,
        product_name=product.product_name,
        category=product.category_slug,
        source_id=adapter.source_id,
        source_domain=source_domain,
        source_country=country,
        source_class=adapter.adapter_type,
        lane=adapter.lane,
        source_page_url=page_url,
        source_image_url=image_url,
        match_type=match_type,
        brand_evidence=brand_ev,
        sku_model_evidence=sku_ev,
        page_identity_evidence=adapter.adapter_type,
        gallery_identity_evidence="primary_image" if image_url else "",
        owner_usage_policy=policy,  # type: ignore[arg-type]
        discovery_status=status,  # type: ignore[arg-type]
        temporary_primary_eligible=temporary_primary_eligible(policy),
        reason_code=reason,
        discovery_timestamp=_now(),
        stop_search=status == "green_exact",
    )


def _materialize(
    fetcher: MediaAwareFetcher,
    cand: DiscoveryCandidate,
    assets_dir: Path,
    sha_map: dict[str, str],
) -> DiscoveryCandidate:
    if not cand.source_image_url:
        cand.discovery_status = "yellow_review"
        cand.reason_code = "yellow_gallery_identity_weak"
        cand.recommended_action = "find_product_gallery_image"
        cand.stop_search = False
        return cand
    if not fetcher.allow_media_for_page(cand.source_page_url, cand.source_image_url):
        cand.discovery_status = "yellow_review"
        cand.reason_code = "yellow_media_host_policy"
        cand.recommended_action = "review_media_host"
        cand.stop_search = False
        return cand
    try:
        status, body, _ctype, _final = fetcher.get(
            cand.source_image_url, fail_code="image_fetch", max_bytes=15_000_000
        )
    except Exception:
        cand.discovery_status = "yellow_review"
        cand.reason_code = "yellow_asset_download_failed"
        cand.recommended_action = "retry_download"
        cand.stop_search = False
        return cand
    if status != 200 or not body:
        cand.discovery_status = "yellow_review"
        cand.reason_code = "yellow_asset_download_failed"
        cand.stop_search = False
        return cand
    asset = materialize_asset(
        body, assets_dir=assets_dir, source_url=cand.source_image_url, sha_map=sha_map
    )
    if asset is None or is_tiny_tracker(asset.width, asset.height, asset.byte_size):
        cand.discovery_status = "yellow_review"
        cand.reason_code = "yellow_asset_download_failed"
        cand.stop_search = False
        return cand
    cand.asset = asset
    if cand.discovery_status == "green_exact":
        cand.stop_search = True
    return cand


def run_discovery_r2(
    *,
    api_base: str,
    package_dir: Path,
    run_universe: list[RunProduct],
    seed_manifest_sha256: str,
    drift_counters: dict[str, int],
    r1_checkpoint: Path | None = None,
    pilot: bool = False,
    pilot_limit: int = 100,
    resume: bool = True,
    sync_urlopen=None,
) -> tuple[DiscoveryRunState, dict[str, Any]]:
    package_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = package_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    ordered = order_run_universe(run_universe)
    if pilot:
        # Prefer brands with known prior-artifact coverage (dasqua/insize), then
        # round-robin so one brand cannot monopolize the pilot. Within each brand,
        # prefer SKUs already present in the prior-artifact index.
        prior_probe = PriorArtifactAdapter(
            next(s for s in DEFAULT_SOURCES if s.source_id == "prior_artifact_reuse")
        )
        prior_probe.build_index(None)
        prior_skus = set(prior_probe._index.keys())
        prior_domains_by_sku = {
            k: (h.page_url or "") for k, h in prior_probe._index.items()
        }

        counts = Counter(p.brand_sort_key for p in ordered)
        preferred = [
            b
            for b, _ in counts.most_common()
            if "dasqua" in b.lower() or "insize" in b.lower()
        ][:2]
        fillers = [b for b, _ in counts.most_common(8) if b not in preferred]
        top3 = (preferred + fillers)[:3]

        def _prior_rank(p: RunProduct) -> tuple[int, int]:
            key = normalize_sku(p.sku)
            if key not in prior_skus:
                return (2, 0)
            url = prior_domains_by_sku.get(key, "")
            # Prefer non-abzarham domains first so pilot covers ≥2 domains
            prefer_alt = 0 if ("abzarham" not in url and url) else 1
            return (prefer_alt, 0)

        buckets = {
            b: sorted([p for p in ordered if p.brand_sort_key == b], key=_prior_rank)
            for b in top3
        }
        pilot_products: list[RunProduct] = []
        i = 0
        while len(pilot_products) < pilot_limit and any(buckets.values()):
            b = top3[i % len(top3)]
            if buckets[b]:
                pilot_products.append(buckets[b].pop(0))
            i += 1
        if len(pilot_products) < pilot_limit:
            seen = {p.product_id for p in pilot_products}
            for p in ordered:
                if p.product_id in seen:
                    continue
                pilot_products.append(p)
                if len(pilot_products) >= pilot_limit:
                    break
        ordered = pilot_products
        # Drop the probe index; the real adapter rebuilds below.
        del prior_probe
        del prior_skus
        del prior_domains_by_sku

    state = DiscoveryRunState(
        api_base=api_base,
        package_dir=str(package_dir),
        seed_manifest_sha256=seed_manifest_sha256,
        baseline_seed_total=4708,
        active_seed_missing=drift_counters.get("active_seed_missing", 0),
        resolved_since_baseline=drift_counters.get("resolved_since_baseline", 0),
        removed_since_baseline=drift_counters.get("removed_since_baseline", 0),
        new_missing_since_baseline=drift_counters.get("new_missing_since_baseline", 0),
        run_discovery_universe_total=len(ordered),
    )
    if resume:
        cp = load_checkpoint(package_dir)
        if cp:
            apply_checkpoint(state, cp)

    for p in ordered:
        if p.product_id not in state.products:
            state.products[p.product_id] = ProductTerminalState(
                product_id=p.product_id, final_status="unresolved", stop_search=False
            )

    fetcher = make_media_fetcher(allowed_page_hosts(), urlopen=sync_urlopen)
    specs_by_id = {s.source_id: s for s in DEFAULT_SOURCES}
    adapters: dict[str, SourceAdapter] = {}
    unsupported: list[str] = []
    for spec in DEFAULT_SOURCES:
        adapter = build_adapter(spec)
        if adapter is None:
            unsupported.append(spec.source_id)
            continue
        adapters[spec.source_id] = adapter

    metrics: dict[str, Any] = {
        "sources_configured": len(DEFAULT_SOURCES),
        "sources_probe_attempted": 0,
        "sources_reachable": 0,
        "sources_calibrated": 0,
        "sources_bulk_enabled": 0,
        "sources_bulk_executed": 0,
        "sources_degraded": 0,
        "unsupported_adapters": unsupported,
        "wave_summary": [],
        "pilot": pilot,
        "pilot_abort": False,
    }

    sample_skus = [p.sku for p in ordered if p.sku][:300]
    brand_hints = list(
        dict.fromkeys(brand_slug(p.brand_key) for p in ordered if p.brand_key)
    )[:15]

    def _prepare(adapter: SourceAdapter) -> None:
        probe = adapter.probe_source(fetcher.inner if hasattr(fetcher, "inner") else fetcher)
        metrics["sources_probe_attempted"] += 1
        if probe.reachable:
            metrics["sources_reachable"] += 1
        else:
            metrics["sources_degraded"] += 1
            adapter.degraded = True
            return
        try:
            if isinstance(adapter, HtmlIndexAdapter):
                adapter._brand_hints = brand_hints  # noqa: SLF001 — run-scoped brand hints
            adapter.build_index(fetcher.inner if hasattr(fetcher, "inner") else fetcher, sample_skus)
            cal = adapter.calibrate(sample_skus)
            if cal.passed:
                metrics["sources_calibrated"] += 1
                metrics["sources_bulk_enabled"] += 1
            if adapter.executed:
                metrics["sources_bulk_executed"] += 1
        except Exception as exc:  # noqa: BLE001
            adapter.degraded = True
            adapter.last_error = str(exc)
            metrics["sources_degraded"] += 1

    # Prior reuse first — do not block WAVE0 behind slow live IR index builds.
    prior = adapters.get("prior_artifact_reuse")
    if isinstance(prior, PriorArtifactAdapter):
        _prepare(prior)
        if len(prior._index) > 0:
            prior.bulk_enabled = True
        prior.write_index_cache(package_dir / "prior-reuse-index.json")
        (package_dir / "prior-reuse-summary.json").write_text(
            json.dumps(prior.stats, indent=2), encoding="utf-8"
        )

    write_brand_source_plan(
        package_dir / "brand-source-plan.csv", ordered, adapters, specs_by_id
    )

    # R1 hit remediation scaffold
    r1_hits = load_r1_identity_hits(
        r1_checkpoint
        or Path("/home/moahmmad/Projects/Karzar-image-coverage/IMG-FAST-01B/checkpoint.json")
    )
    r1_rows: list[dict[str, Any]] = []

    def unresolved_products() -> list[RunProduct]:
        return [
            p
            for p in ordered
            if state.products[p.product_id].final_status == "unresolved"
            or (
                state.products[p.product_id].final_status == "yellow_review"
                and not state.products[p.product_id].stop_search
            )
        ]

    def run_wave(wave_name: str, lanes: tuple[str, ...]) -> None:
        nonlocal metrics
        starting = len(
            [p for p in ordered if state.products[p.product_id].final_status == "unresolved"]
        )
        new_green = new_yellow = 0
        source_failures: list[str] = []
        wave_adapters = [
            a for a in adapters.values() if a.lane in lanes and a.bulk_enabled and not a.degraded
        ]
        if not wave_adapters and lanes == ("IR-1",):
            wave_adapters = [
                a
                for a in adapters.values()
                if a.lane in lanes and not a.degraded and a.probe and a.probe.reachable
            ]
            for a in wave_adapters:
                a.bulk_enabled = True

        for product in list(unresolved_products()):
            terminal = state.products[product.product_id]
            if terminal.stop_search and terminal.final_status == "green_exact":
                continue
            best_yellow = terminal.best_yellow
            green = None
            attempts = list(terminal.attempts)

            for adapter in wave_adapters:
                hit = adapter.lookup_product(product)
                # Index-first: only fall back to live HTML search when the brand
                # index is empty (avoids 20s×N hangs on every miss).
                if (
                    hit is None
                    and isinstance(adapter, HtmlIndexAdapter)
                    and len(adapter._index) < 5
                ):
                    hit = adapter.search_sku_on_site(
                        fetcher.inner, product.sku, product.brand_key
                    )
                if hit is None:
                    continue
                if isinstance(adapter, HtmlIndexAdapter | SitemapAdapter):
                    hit = adapter.enrich_hit(fetcher.inner, hit, product.sku)  # type: ignore[attr-defined]
                if not hit.page_url:
                    continue
                cand = _candidate_from_hit(product, adapter, hit)
                if cand.discovery_status == "red_rejected":
                    attempts.append(cand)
                    continue
                cand = _materialize(fetcher, cand, assets_dir, state.sha_assets)
                attempts.append(cand)
                if cand.discovery_status == "green_exact" and cand.asset is not None:
                    green = cand
                    break
                if cand.discovery_status == "yellow_review":
                    best_yellow = cand
            if green:
                state.products[product.product_id] = ProductTerminalState(
                    product_id=product.product_id,
                    final_status="green_exact",
                    stop_search=True,
                    green=green,
                    best_yellow=best_yellow,
                    attempts=attempts,
                )
                new_green += 1
            elif best_yellow:
                state.products[product.product_id] = ProductTerminalState(
                    product_id=product.product_id,
                    final_status="yellow_review",
                    stop_search=False,
                    best_yellow=best_yellow,
                    attempts=attempts,
                )
                new_yellow += 1
            else:
                state.products[product.product_id] = ProductTerminalState(
                    product_id=product.product_id,
                    final_status="unresolved",
                    stop_search=False,
                    attempts=attempts,
                )
            save_checkpoint(state, package_dir)

        remaining = len(
            [p for p in ordered if state.products[p.product_id].final_status == "unresolved"]
        )
        metrics["wave_summary"].append(
            {
                "wave": wave_name,
                "starting_unresolved": starting,
                "new_green": new_green,
                "new_yellow": new_yellow,
                "remaining_unresolved": remaining,
                "source_failures": ";".join(source_failures),
                "adapters": ",".join(a.source_id for a in wave_adapters),
            }
        )

    # WAVE0 immediately after prior index
    run_wave("WAVE0", ("REUSE",))
    if pilot:
        greens_so_far = sum(
            1 for ps in state.products.values() if ps.final_status == "green_exact"
        )
        print(f"pilot WAVE0 green_exact={greens_so_far}", flush=True)

    # Remaining live adapters
    for sid, adapter in adapters.items():
        if sid == "prior_artifact_reuse":
            continue
        _prepare(adapter)

    write_brand_source_plan(
        package_dir / "brand-source-plan.csv", ordered, adapters, specs_by_id
    )

    for wave_name, lanes in WAVE_ORDER:
        if wave_name == "WAVE0":
            continue
        run_wave(wave_name, lanes)
    # R1 remediation rows
    by_id = {p.product_id: p for p in ordered}
    for hit in r1_hits:
        pid = hit["product_id"]
        product = by_id.get(pid)
        ps = state.products.get(pid)
        row = {
            **hit,
            "brand": product.brand_key if product else "",
            "sku": product.sku if product else "",
            "source_page": "",
            "source_image": "",
            "r2_result": ps.final_status if ps else "not_in_run",
        }
        if ps and ps.green:
            row["source_page"] = ps.green.source_page_url
            row["source_image"] = ps.green.source_image_url
        elif ps and ps.best_yellow:
            row["source_page"] = ps.best_yellow.source_page_url
            row["source_image"] = ps.best_yellow.source_image_url
        r1_rows.append(row)

    with (package_dir / "r1-hit-remediation.csv").open("w", encoding="utf-8", newline="") as f:
        fields = [
            "product_id",
            "brand",
            "sku",
            "source_page",
            "source_image",
            "old_inferred_status",
            "r1_materialization_failure",
            "r2_result",
        ]
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(r1_rows)

    with (package_dir / "wave-summary.csv").open("w", encoding="utf-8", newline="") as f:
        fields = [
            "wave",
            "starting_unresolved",
            "new_green",
            "new_yellow",
            "remaining_unresolved",
            "source_failures",
            "adapters",
        ]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(metrics["wave_summary"])

    greens = sum(1 for ps in state.products.values() if ps.final_status == "green_exact")
    green_source_ids = {
        ps.green.source_id
        for ps in state.products.values()
        if ps.final_status == "green_exact" and ps.green is not None and ps.green.source_id
    }
    green_domains = {
        ps.green.source_domain
        for ps in state.products.values()
        if ps.final_status == "green_exact" and ps.green is not None and ps.green.source_domain
    }
    metrics["green_exact"] = greens
    metrics["sources_with_green"] = sorted(green_source_ids)
    metrics["domains_with_green"] = sorted(green_domains)
    # Gate: need greens AND at least two distinct materializing domains/adapters.
    if pilot and (greens == 0 or (len(green_source_ids) < 2 and len(green_domains) < 2)):
        metrics["pilot_abort"] = True
        metrics["pilot_abort_reason"] = (
            "green_exact=0"
            if greens == 0
            else f"sources={sorted(green_source_ids)} domains={sorted(green_domains)}"
        )

    # Source probe CSV
    probe_rows = []
    for a in adapters.values():
        p = a.probe
        probe_rows.append(
            {
                "source_id": a.source_id,
                "domain": a.domain,
                "dns_ok": p.dns_ok if p else False,
                "ipv4_ok": p.ipv4_ok if p else False,
                "ipv6_ok": p.ipv6_ok if p else False,
                "tls_ok": p.tls_ok if p else False,
                "http_status": p.http_status if p else "",
                "failure_class": p.failure_class if p else "",
                "attempt_count": p.attempt_count if p else 0,
                "notes": p.notes if p else "",
            }
        )
    with (package_dir / "source-probe.csv").open("w", encoding="utf-8", newline="") as f:
        fields = list(probe_rows[0].keys()) if probe_rows else ["source_id"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(probe_rows)

    state.source_indexes = adapters  # type: ignore[attr-defined]
    metrics["r1_hits_recovered"] = len(r1_hits)
    metrics["r1_hits_materialized"] = sum(1 for r in r1_rows if r.get("r2_result") == "green_exact")
    metrics["r1_hits_still_failed"] = sum(
        1 for r in r1_rows if r.get("r2_result") != "green_exact"
    )
    return state, metrics


def summarize_from_rows(
    *,
    greens: list[dict[str, Any]],
    yellows: list[dict[str, Any]],
    unresolved: list[dict[str, Any]],
    reds: list[dict[str, Any]],
    run_total: int,
) -> dict[str, int | float]:
    green_ir = sum(1 for g in greens if g.get("owner_usage_policy") == "iranian_source_allowed")
    green_non = len(greens) - green_ir
    total = run_total or 1
    return {
        "green_exact": len(greens),
        "yellow_review": len(yellows),
        "unresolved": len(unresolved),
        "red_attempts": len(reds),
        "green_iranian": green_ir,
        "green_non_iranian": green_non,
        "green_coverage_pct": round(100.0 * len(greens) / total, 2),
        "green_yellow_coverage_pct": round(100.0 * (len(greens) + len(yellows)) / total, 2),
    }


# Backward-compatible alias used by older CLI paths
def run_discovery(**kwargs):  # type: ignore[no-untyped-def]
    state, _metrics = run_discovery_r2(**kwargs)
    return state
