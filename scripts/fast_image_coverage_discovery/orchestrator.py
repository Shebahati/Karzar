"""Discovery orchestrator — first GREEN stop per product."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from scripts.image_discovery.transport import HostThrottledFetcher

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
    owner_policy_for_country,
    temporary_primary_eligible,
)
from .ordering import order_run_universe
from .reuse import load_reuse_candidates
from .sources.registry import DEFAULT_SOURCES, sources_for_lane
from .sources.wc_store import build_wc_index, calibrate_index, lookup_sku
from .transport import make_fetcher


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _allowed_hosts() -> frozenset[str]:
    hosts: set[str] = set()
    for spec in DEFAULT_SOURCES:
        hosts.add(spec.domain.lower())
        if spec.domain.startswith("www."):
            hosts.add(spec.domain[4:])
    return frozenset(hosts)


def _download_image(fetcher: HostThrottledFetcher, url: str) -> bytes | None:
    try:
        status, body, _ctype, _final = fetcher.get(url, fail_code="image_fetch_failed", max_bytes=15_000_000)
        if status == 200 and body:
            return body
    except Exception:
        return None
    return None


def _candidate_from_wc(
    product: RunProduct,
    *,
    spec_lane: str,
    spec_id: str,
    domain: str,
    country: str,
    source_class: str,
    page_url: str,
    image_url: str,
    title: str,
) -> DiscoveryCandidate:
    policy = owner_policy_for_country(country)
    status, match_type, brand_ev, sku_ev, reason = classify_identity(
        sku=product.sku,
        brand_key=product.brand_key,
        product_name=product.product_name,
        page_title=title,
        page_text=title,
        has_pdp_structure=True,
        image_is_product_gallery=True,
        source_country=country,
    )
    return DiscoveryCandidate(
        product_id=product.product_id,
        sku=product.sku,
        brand_key=product.brand_key,
        product_name=product.product_name,
        category=product.category_slug,
        source_id=spec_id,
        source_domain=domain,
        source_country=country,
        source_class=source_class,
        lane=spec_lane,
        source_page_url=page_url,
        source_image_url=image_url,
        match_type=match_type,
        brand_evidence=brand_ev,
        sku_model_evidence=sku_ev,
        page_identity_evidence="wc_product_page",
        gallery_identity_evidence="wc_images_primary",
        owner_usage_policy=policy,  # type: ignore[arg-type]
        discovery_status=status,  # type: ignore[arg-type]
        temporary_primary_eligible=temporary_primary_eligible(policy),
        reason_code=reason,
        discovery_timestamp=_now(),
        stop_search=status == "green_exact",
    )


def run_discovery(
    *,
    api_base: str,
    package_dir: Path,
    run_universe: list[RunProduct],
    seed_manifest_sha256: str,
    drift_counters: dict[str, int],
    resume: bool = True,
    sync_urlopen=None,
) -> DiscoveryRunState:
    package_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = package_dir / "assets"
    assets_dir.mkdir(exist_ok=True)

    state = DiscoveryRunState(
        api_base=api_base,
        package_dir=str(package_dir),
        seed_manifest_sha256=seed_manifest_sha256,
        baseline_seed_total=4708,
        active_seed_missing=drift_counters.get("active_seed_missing", 0),
        resolved_since_baseline=drift_counters.get("resolved_since_baseline", 0),
        removed_since_baseline=drift_counters.get("removed_since_baseline", 0),
        new_missing_since_baseline=drift_counters.get("new_missing_since_baseline", 0),
        run_discovery_universe_total=len(run_universe),
    )
    if resume:
        cp = load_checkpoint(package_dir)
        if cp:
            apply_checkpoint(state, cp)

    ordered = order_run_universe(run_universe)
    fetcher = make_fetcher(_allowed_hosts(), urlopen=sync_urlopen)

    indexes: dict[str, object] = {}
    sample_skus = [p.sku for p in ordered if p.sku][:500]
    for spec in [s for s in DEFAULT_SOURCES if s.wc_store_api]:
        idx = build_wc_index(spec, fetcher)
        calibrate_index(idx, sample_skus)
        if not idx.bulk_enabled and len(idx.by_sku) >= 50:
            # Index populated but sample missed — run lane calibration on brand-top SKUs
            brand_top = [p.sku for p in ordered if p.sku][:20]
            calibrate_index(idx, brand_top)
        indexes[spec.source_id] = idx

    lane_order = ("IR-1", "IR-2", "OFFICIAL", "DIST", "WIDE")
    for product in ordered:
        terminal = state.products.get(product.product_id)
        if terminal and terminal.stop_search:
            continue

        attempts: list[DiscoveryCandidate] = []
        best_yellow: DiscoveryCandidate | None = None
        green: DiscoveryCandidate | None = None

        # Prior artifact reuse
        for cand in load_reuse_candidates(product):
            cand.discovery_timestamp = _now()
            attempts.append(cand)
            if cand.discovery_status == "green_exact":
                green = cand
                break
            if cand.discovery_status == "yellow_review" and (
                best_yellow is None or cand.sku_model_evidence == "exact_sku"
            ):
                best_yellow = cand

        if green is None:
            for lane in lane_order:
                if green:
                    break
                specs = sources_for_lane(lane)
                for spec in specs:
                    idx = indexes.get(spec.source_id)
                    if idx is None:
                        continue
                    hit = lookup_sku(idx, product.sku)  # type: ignore[arg-type]
                    if not hit or not hit.image_urls:
                        continue
                    cand = _candidate_from_wc(
                        product,
                        spec_lane=spec.lane,
                        spec_id=spec.source_id,
                        domain=spec.domain,
                        country=spec.country,
                        source_class=spec.source_class,
                        page_url=hit.permalink,
                        image_url=hit.image_urls[0],
                        title=hit.title,
                    )
                    attempts.append(cand)
                    if cand.discovery_status == "green_exact":
                        green = cand
                        break
                    if cand.discovery_status == "yellow_review":
                        best_yellow = cand
                    elif cand.discovery_status == "red_rejected":
                        pass
                if green:
                    break

        final = green or best_yellow
        if final and final.discovery_status in {"green_exact", "yellow_review"}:
            data = _download_image(fetcher, final.source_image_url)
            if data:
                asset = materialize_asset(
                    data,
                    assets_dir=assets_dir,
                    source_url=final.source_image_url,
                    sha_map=state.sha_assets,
                )
                if asset and is_tiny_tracker(asset.width, asset.height, asset.byte_size):
                    if final.discovery_status == "green_exact":
                        final.discovery_status = "yellow_review"
                        final.reason_code = "tiny_or_tracker_image"
                        final.recommended_action = "verify_not_icon"
                    asset = None
                final.asset = asset

        if green:
            status = "green_exact"
            stop = True
        elif best_yellow:
            status = "yellow_review"
            stop = False
        else:
            status = "unresolved"
            stop = False

        state.products[product.product_id] = ProductTerminalState(
            product_id=product.product_id,
            final_status=status,  # type: ignore[arg-type]
            stop_search=stop,
            best_yellow=best_yellow,
            attempts=attempts,
        )
        save_checkpoint(state, package_dir)

    state.source_indexes = indexes  # type: ignore[attr-defined]
    return state


def summarize_run(state: DiscoveryRunState) -> dict[str, int | float]:
    greens = yellows = unresolved = reds = 0
    green_ir = green_non = 0
    for ps in state.products.values():
        if ps.final_status == "green_exact":
            greens += 1
        elif ps.final_status == "yellow_review":
            yellows += 1
        else:
            unresolved += 1
        for a in ps.attempts:
            if a.discovery_status == "red_rejected":
                reds += 1
            if a.discovery_status == "green_exact" and a.owner_usage_policy == "iranian_source_allowed":
                green_ir += 1
            if a.discovery_status == "green_exact" and a.owner_usage_policy != "iranian_source_allowed":
                green_non += 1
    total = state.run_discovery_universe_total or 1
    return {
        "green_exact": greens,
        "yellow_review": yellows,
        "unresolved": unresolved,
        "red_attempts": reds,
        "green_iranian": green_ir,
        "green_non_iranian": green_non,
        "green_coverage_pct": round(100.0 * greens / total, 2),
        "green_yellow_coverage_pct": round(100.0 * (greens + yellows) / total, 2),
    }
