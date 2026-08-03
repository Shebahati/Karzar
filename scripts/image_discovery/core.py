"""Core discovery orchestration (brand-agnostic)."""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .contracts import DiscoveryError, ImageCandidate, RejectRecord
from .output import (
    compare_runs,
    file_sha256,
    load_previous_manifest,
    load_run_state,
    rename_and_classify,
    semantic_manifest_sha256,
    write_outputs,
    write_summary_and_state,
)
from .paths import (
    assert_run_output_roots_nofollow,
    assert_under_assets,
    inspect_local_asset_nofollow,
    inventory_assets_by_sha,
    iter_local_asset_files,
)
from .quality import estimate_foreground_occupancy, validate_image_bytes
from .sources.base import SourceAdapter
from .transport import HostThrottledFetcher, normalize_url_key

_FORBIDDEN_MODULE_NAMES = (
    "app.db.database",
    "app.db.models",
    "app.crud",
    "sqlalchemy",
)


def assert_no_forbidden_imports_in_tree(root: Path) -> None:
    patterns = [
        r"^\s*import\s+sqlalchemy\b",
        r"^\s*from\s+sqlalchemy\b",
        r"^\s*from\s+app\.db(\.|\s)",
        r"^\s*import\s+app\.db\b",
        r"^\s*from\s+app\.crud\b",
        r"^\s*import\s+app\.crud\b",
        r"^\s*(from|import).*\basync_session_maker\b",
        r"^\s*from\s+app\.db\.models",
    ]
    import re

    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pat in patterns:
            if re.search(pat, text, re.MULTILINE):
                raise AssertionError(f"{path}: forbidden pattern {pat}")


def validate_output_dir(output_dir: Path, repo_root: Path) -> Path:
    if not output_dir.is_absolute():
        raise SystemExit("ERROR: --output-dir must be an absolute path outside the repository")
    # Do not follow symlinks when checking repo containment of the path string;
    # still reject output that resolves inside the repo after a non-symlink resolve of parents.
    if output_dir.is_symlink():
        raise SystemExit("ERROR: --output-dir must not be a symlink")
    resolved = output_dir.resolve()
    try:
        resolved.relative_to(repo_root.resolve())
        raise SystemExit(f"ERROR: --output-dir must be outside the repository ({repo_root})")
    except ValueError:
        pass
    return resolved


def enforce_run_output_policy(
    out: Path,
    *,
    adapter_name: str,
    resume: bool,
    force_refetch: bool,
) -> None:
    """Governed output policy for ``run`` mode (IMG-01E).

    - New run (no resume, no force-refetch): output absent or completely empty.
    - ``--resume``: coherent prior + same adapter + no symlink roots.
    - ``--force-refetch``: if non-empty, must still be a coherent prior + same adapter.
    """
    from .consolidation import recognize_prior_discovery_output

    try:
        assert_run_output_roots_nofollow(out)
    except DiscoveryError as e:
        raise SystemExit(f"ERROR: governed output root rejected ({e.reason_code}: {e.reason_detail})") from e

    exists = out.exists(follow_symlinks=False) or out.is_symlink()
    children = list(out.iterdir()) if exists and out.is_dir() and not out.is_symlink() else []
    empty = (not exists) or (not children)

    if empty:
        if resume:
            raise SystemExit(
                "ERROR: --resume requires a coherent governed prior output "
                "(output directory is absent or empty)"
            )
        return

    # Non-empty: new runs without resume/force-refetch are forbidden
    if not resume and not force_refetch:
        names = sorted(p.name for p in children)
        raise SystemExit(
            "ERROR: --output-dir is non-empty; for a new run use an absent or empty directory, "
            "or pass --resume / --force-refetch only for a coherent governed prior output "
            f"(found: {', '.join(names[:12])}{'…' if len(names) > 12 else ''})"
        )

    ok, reason, stale = recognize_prior_discovery_output(out)
    if not ok:
        raise SystemExit(
            "ERROR: --resume/--force-refetch refused — output is not a coherent governed "
            f"image-discovery directory ({reason})"
        )
    if reason == "recognized_with_stale_assets" and stale:
        # Resume may proceed with stale unreferenced files inventoried later; do not block
        # solely on stale extras — but unknown files already failed recognition.
        pass

    # Same adapter identity
    try:
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    except Exception as e:
        raise SystemExit("ERROR: cannot read summary.json for adapter identity check") from e
    prior_adapter = str(summary.get("source_adapter") or "").strip()
    if prior_adapter and prior_adapter != adapter_name:
        raise SystemExit(
            f"ERROR: adapter mismatch — prior output source_adapter={prior_adapter!r} "
            f"but this run uses {adapter_name!r}"
        )
    if not prior_adapter:
        raise SystemExit("ERROR: prior summary.json missing source_adapter")


class _SingleFlight:
    """One network fetch per key; unrelated keys overlap."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._inflight: dict[str, Future[Any]] = {}

    def do(self, key: str, fn: Any) -> Any:
        with self._lock:
            fut = self._inflight.get(key)
            if fut is None:
                fut = Future()
                self._inflight[key] = fut
                owner = True
            else:
                owner = False
        if not owner:
            return fut.result()
        try:
            result = fn()
            fut.set_result(result)
            return result
        except Exception as e:
            fut.set_exception(e)
            raise
        finally:
            with self._lock:
                if self._inflight.get(key) is fut:
                    del self._inflight[key]


def run_discovery(
    *,
    adapter: SourceAdapter,
    products_csv: Path | None,
    candidates_csv: Path | None,
    output_dir: Path,
    repo_root: Path,
    sku_filters: list[str] | None = None,
    limit: int | None = None,
    offset: int = 0,
    concurrency: int = 2,
    delay: float = 0.5,
    resume: bool = False,
    force_refetch: bool = False,
    max_images_per_product: int = 1,
    fetcher: HostThrottledFetcher | None = None,
    min_bytes: int = 10 * 1024,
    min_dim: int = 250,
    provenance_batch: str = "",
) -> dict[str, Any]:
    if max_images_per_product <= 0:
        raise SystemExit("ERROR: --max-images-per-product must be > 0")
    if concurrency <= 0:
        raise SystemExit("ERROR: --concurrency must be > 0")
    if delay < 0:
        raise SystemExit("ERROR: --delay must be >= 0")
    if limit is not None and limit < 0:
        raise SystemExit("ERROR: --limit must be >= 0")
    if offset < 0:
        raise SystemExit("ERROR: --offset must be >= 0")

    out = validate_output_dir(output_dir, repo_root)
    enforce_run_output_policy(
        out,
        adapter_name=adapter.name,
        resume=resume,
        force_refetch=force_refetch,
    )
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("assets", "manifests", "review", "logs"):
        (out / sub).mkdir(exist_ok=True)
    try:
        assert_run_output_roots_nofollow(out)
    except DiscoveryError as e:
        raise SystemExit(f"ERROR: governed output root rejected ({e.reason_code}: {e.reason_detail})") from e

    batch_name = provenance_batch or out.name
    provenance_manifest = "manifests/manifest.json"

    previous_state = load_run_state(out, resume=resume)
    previous_manifest_map = load_previous_manifest(out, resume=resume)
    if force_refetch:
        # Network assets refetched; comparison may still use previous immutable state when resume
        previous_manifest_map = {}
    previous_manifest_list = list(previous_manifest_map.values())

    candidates = adapter.load_candidates(
        products_csv=products_csv,
        candidates_csv=candidates_csv,
        sku_filters=sku_filters,
        limit=limit,
        offset=offset,
        max_images_per_product=max_images_per_product,
    )

    fetcher = fetcher or HostThrottledFetcher(allowed_hosts=adapter.allowed_hosts(), delay=delay)
    log_lines: list[str] = [f"=== started {datetime.now(UTC).isoformat()} adapter={adapter.name} ==="]

    def log(msg: str) -> None:
        log_lines.append(f"{datetime.now(UTC).isoformat()} {msg}")

    page_flight = _SingleFlight()
    image_flight = _SingleFlight()
    page_cache: dict[str, tuple[int, bytes, str, str]] = {}
    url_cache: dict[str, dict[str, Any]] = {}
    cache_lock = threading.Lock()
    asset_registry: dict[str, dict[str, Any]] = {}
    asset_lock = threading.Lock()

    def materialize(cached: dict[str, Any]) -> tuple[str, str]:
        sha = cached["sha256"]
        ext = cached["ext"]
        data = cached["bytes"]
        assets = out / "assets"
        with asset_lock:
            if sha in asset_registry:
                reg = asset_registry[sha]
                if reg["origin"] == "downloaded_new":
                    return reg["local_name"], "reused_within_run"
                return reg["local_name"], "reused_existing"
            short = sha[:12]
            for p in iter_local_asset_files(assets, fail_closed=True):
                if f"__{short}." not in p.name and not p.name.startswith(f"pending__{short}."):
                    continue
                if file_sha256(p) == sha:
                    asset_registry[sha] = {"local_name": p.name, "origin": "reused_existing"}
                    return p.name, "reused_existing"
            dest = assert_under_assets(assets, assets / f"pending__{sha[:12]}.{ext}")
            if dest.exists(follow_symlinks=False):
                inspect_local_asset_nofollow(dest, assets_root=assets)
                if file_sha256(dest) != sha:
                    raise DiscoveryError("image", "destination_sha_mismatch", f"hash collision: {dest.name}")
            else:
                dest.write_bytes(data)
                if file_sha256(dest) != sha:
                    dest.unlink(missing_ok=True)
                    raise DiscoveryError("image", "destination_sha_mismatch", "write verify failed")
            asset_registry[sha] = {"local_name": dest.name, "origin": "downloaded_new"}
            return dest.name, "downloaded_new"

    def fetch_page(url: str) -> tuple[int, bytes, str, str]:
        key = normalize_url_key(url)

        def _do() -> tuple[int, bytes, str, str]:
            with cache_lock:
                if key in page_cache:
                    return page_cache[key]
            status, body, ctype, final = fetcher.get(
                url, fail_code="detail_fetch_failed", max_bytes=fetcher.max_detail_page_bytes
            )
            with cache_lock:
                page_cache[key] = (status, body, ctype, final)
                return page_cache[key]

        return page_flight.do(key, _do)

    def fetch_image(url: str) -> dict[str, Any]:
        key = normalize_url_key(url)

        def _do() -> dict[str, Any]:
            with cache_lock:
                if key in url_cache:
                    return url_cache[key]
            istatus, ibody, ictype, final_image = fetcher.get(
                url, fail_code="image_fetch_failed", max_bytes=fetcher.max_image_bytes
            )
            if istatus != 200:
                raise DiscoveryError("image", "image_fetch_failed", f"HTTP {istatus}", istatus)
            mime, ext, w, h = validate_image_bytes(
                ibody,
                content_type=ictype,
                final_url=final_image,
                min_bytes=min_bytes,
                min_dim=min_dim,
            )
            cached_img = {
                "bytes": ibody,
                "sha256": hashlib.sha256(ibody).hexdigest(),
                "mime": mime,
                "ext": ext,
                "width": w,
                "height": h,
                "final_url": final_image,
            }
            with cache_lock:
                url_cache[key] = cached_img
                return url_cache[key]

        return image_flight.do(key, _do)

    def process_one(cand: ImageCandidate) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        cand.ensure_identity()
        try:
            prev = previous_manifest_map.get(cand.candidate_id)
            # With --resume, reuse governed previous row when disk SHA matches — no network.
            if (
                resume
                and not force_refetch
                and prev
                and prev.get("source_image_url") == cand.image_url
                and prev.get("sha256")
                and prev.get("local_asset_path")
                and prev.get("sku_confirmed")
                and prev.get("manufacturer_confirmed")
            ):
                from .paths import resolve_manifest_asset_path

                local_path = resolve_manifest_asset_path(
                    assets_root=out / "assets",
                    local_asset_path=str(prev["local_asset_path"]),
                    require_exists=True,
                )
                disk = local_path.read_bytes()
                disk_sha = hashlib.sha256(disk).hexdigest()
                if disk_sha != prev["sha256"]:
                    raise DiscoveryError(
                        "image",
                        "manifest_sha_mismatch",
                        f"disk sha != manifest for {cand.candidate_id}",
                    )
                mime, ext, w, h = validate_image_bytes(
                    disk,
                    content_type=str(prev.get("mime_type") or "image/jpeg"),
                    final_url=str(prev.get("final_image_url") or cand.image_url),
                    min_bytes=min_bytes,
                    min_dim=min_dim,
                )
                cached_img = {
                    "bytes": disk,
                    "sha256": disk_sha,
                    "mime": mime,
                    "ext": ext,
                    "width": w,
                    "height": h,
                    "final_url": prev.get("final_image_url") or cand.image_url,
                }
                with cache_lock:
                    url_cache.setdefault(normalize_url_key(cand.image_url), cached_img)
                local_name, st = materialize(cached_img)
                from .contracts import PageEvidence

                evidence = PageEvidence(
                    True,
                    True,
                    str(prev.get("manufacturer_evidence") or "resume_previous_manifest"),
                    str(prev.get("sku_evidence") or "resume_previous_manifest"),
                    str(prev.get("page_subject_evidence") or "resume_previous_manifest"),
                )
                log(f"[{cand.sku}] resume reuse sha={disk_sha[:12]}")
                return (
                    _build_row(
                        cand,
                        cached_img,
                        local_name,
                        st,
                        evidence,
                        str(prev.get("source_detail_url") or cand.detail_url),
                        batch_name,
                        provenance_manifest,
                    ),
                    None,
                )

            status, body, ctype, final_detail = fetch_page(cand.detail_url)
            log(f"[{cand.sku}] detail status={status}")
            if status != 200:
                raise DiscoveryError("detail", "detail_fetch_failed", f"HTTP {status}", status)
            page_html = body.decode("utf-8", errors="replace")
            evidence = adapter.validate_page(sku=cand.sku, page_html=page_html, detail_url=cand.detail_url)
            if evidence.weak_review_only or not evidence.manufacturer_confirmed or not evidence.sku_confirmed:
                raise DiscoveryError(
                    "detail",
                    evidence.reason_code or "exact_sku_not_confirmed",
                    evidence.reason_detail or "page subject evidence failed",
                    status,
                )

            cached_img = fetch_image(cand.image_url)
            log(f"[{cand.sku}] image bytes={len(cached_img['bytes'])}")
            local_name, st = materialize(cached_img)
            return (
                _build_row(
                    cand,
                    cached_img,
                    local_name,
                    st,
                    evidence,
                    final_detail,
                    batch_name,
                    provenance_manifest,
                ),
                None,
            )
        except DiscoveryError as e:
            log(f"[{cand.sku}] REJECT {e.reason_code}: {e.reason_detail}")
            return None, RejectRecord(
                candidate_id=cand.candidate_id,
                sku=cand.sku,
                product_name=cand.product_name,
                brand=cand.brand,
                stage=e.stage,
                reason_code=e.reason_code,
                reason_detail=e.reason_detail,
                detail_url=cand.detail_url,
                image_url=cand.image_url,
                http_status=e.http_status,
                product_id=cand.product_id,
                product_key=cand.product_key,
                provenance_batch=batch_name,
                provenance_manifest=provenance_manifest,
                provenance_source_adapter=cand.source_adapter,
            ).as_dict()
        except Exception as e:  # noqa: BLE001
            log(f"[{cand.sku}] REJECT unexpected_error: {e}")
            return None, RejectRecord(
                candidate_id=cand.candidate_id,
                sku=cand.sku,
                product_name=cand.product_name,
                brand=cand.brand,
                stage="unexpected",
                reason_code="unexpected_error",
                reason_detail=str(e),
                detail_url=cand.detail_url,
                image_url=cand.image_url,
                product_id=cand.product_id,
                product_key=cand.product_key,
                provenance_batch=batch_name,
                provenance_manifest=provenance_manifest,
                provenance_source_adapter=cand.source_adapter,
            ).as_dict()

    manifests: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futs = {ex.submit(process_one, c): c.candidate_id for c in candidates}
        results: dict[str, tuple] = {}
        for fut in as_completed(futs):
            results[futs[fut]] = fut.result()
    for c in candidates:
        man, rej = results[c.candidate_id]
        if man:
            manifests.append(man)
        if rej:
            rejected.append(rej)

    cross_brand = rename_and_classify(manifests, out)
    for p in iter_local_asset_files(out / "assets", fail_closed=True):
        if not p.name.startswith("pending__"):
            continue
        sha12 = p.stem.split("__")[-1]
        pending_sha = file_sha256(p)
        finals = [
            x
            for x in iter_local_asset_files(out / "assets", fail_closed=True)
            if x != p and f"__{sha12}." in x.name and file_sha256(x) == pending_sha
        ]
        if finals:
            p.unlink(missing_ok=True)

    write_outputs(out, manifests, rejected, cross_brand=cross_brand, conflicts=[])

    downloaded_unique = sum(1 for v in asset_registry.values() if v["origin"] == "downloaded_new")
    reused_existing = sum(1 for v in asset_registry.values() if v["origin"] == "reused_existing")
    reused_within = sum(1 for m in manifests if m["download_status"] == "reused_within_run")
    unique_assets = len({m["sha256"] for m in manifests})

    semantic = semantic_manifest_sha256(manifests)
    comparison = compare_runs(
        previous_state=previous_state,
        previous_manifest=previous_manifest_list,
        current_manifest=manifests,
        current_semantic=semantic,
        asset_dir=out / "assets",
    )
    from .consolidation import _write_duplicate_physical_report

    by_phys, _ = inventory_assets_by_sha(out / "assets", file_sha256=file_sha256, fail_closed=True)
    dup_groups, dup_files = _write_duplicate_physical_report(out, by_phys)
    comparison["duplicate_physical_asset_groups"] = dup_groups
    comparison["duplicate_physical_asset_files"] = dup_files

    summary = {
        "pilot_id": "IMG-01D",
        "source_adapter": adapter.name,
        "workflow": "candidate_validation→materialization→human_review",
        "requested_rows": len(candidates),
        "accepted_rows": len(manifests),
        "rejected_rows": len(rejected),
        "downloaded_unique_assets": downloaded_unique,
        "reused_existing_assets": reused_existing,
        "reused_within_run_rows": reused_within,
        "unique_assets": unique_assets,
        "family_rows": sum(1 for m in manifests if m["image_specificity"] == "family"),
        "singleton_unverified_rows": sum(
            1 for m in manifests if m["image_specificity"] == "singleton_unverified"
        ),
        "sku_specific_rows": sum(1 for m in manifests if m["image_specificity"] == "sku"),
        "cross_brand_duplicate_rows": sum(
            1 for m in manifests if m["image_specificity"] == "cross_brand_duplicate"
        ),
        "cross_brand_duplicate_groups": len(cross_brand),
        "max_images_per_product": max_images_per_product,
        "manifest_file_sha256": file_sha256(out / "manifests" / "manifest.json"),
        "manifest_semantic_sha256": semantic,
        "repository_modified": False,
        "database_accessed": False,
        "rights_status_policy": "review_required",
        "allowed_hosts": sorted(adapter.allowed_hosts()),
        "resume": resume,
        "force_refetch": force_refetch,
    }
    write_summary_and_state(out, summary, manifests, comparison)

    log_path = out / "logs" / "download.log"
    prev = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    log_path.write_text(prev + "\n".join(log_lines) + "\n", encoding="utf-8")

    return json.loads((out / "summary.json").read_text(encoding="utf-8"))


def _build_row(
    cand: ImageCandidate,
    cached: dict[str, Any],
    local_name: str,
    download_status: str,
    evidence: Any,
    final_detail: str,
    provenance_batch: str,
    provenance_manifest: str,
) -> dict[str, Any]:
    occ, pnote = estimate_foreground_occupancy(
        data=cached["bytes"],
        width=cached.get("width"),
        height=cached.get("height"),
        byte_size=len(cached["bytes"]),
    )
    return {
        "candidate_id": cand.candidate_id,
        "product_id": cand.product_id,
        "product_key": cand.product_key,
        "identity_basis": cand.identity_basis,
        "source_candidate_key": cand.source_candidate_key,
        "sku": cand.sku,
        "product_name": cand.product_name,
        "brand": cand.brand,
        "source_adapter": cand.source_adapter,
        "source_class": cand.source_class,
        "image_role": cand.image_role,
        "source_rank": cand.source_rank,
        "display_order_candidate": cand.display_order_candidate,
        "source_image_index": cand.source_image_index,
        "source_detail_url": cand.detail_url,
        "source_image_url": cand.image_url,
        "final_image_url": cached["final_url"],
        "local_asset_path": f"assets/{local_name}",
        "sha256": cached["sha256"],
        "mime_type": cached["mime"],
        "extension": cached["ext"],
        "byte_size": len(cached["bytes"]),
        "width": cached["width"] if cached.get("width") is not None else "",
        "height": cached["height"] if cached.get("height") is not None else "",
        "foreground_occupancy_status": occ,
        "presentation_note": pnote,
        "match_confidence": cand.confidence,
        "sku_confirmed": True,
        "manufacturer_confirmed": True,
        "manufacturer_evidence": evidence.manufacturer_evidence,
        "sku_evidence": evidence.sku_evidence,
        "page_subject_evidence": evidence.page_subject_evidence,
        "image_specificity": "",
        "variant_specific": "",
        "shared_asset_group": "",
        "download_status": download_status,
        "review_status": "pending_human_review",
        "rights_status": "review_required",
        "provenance_batch": provenance_batch,
        "provenance_manifest": provenance_manifest,
        "provenance_source_adapter": cand.source_adapter,
        "notes": f"fetched_at_utc={datetime.now(UTC).isoformat()}; detail_final={final_detail}",
    }
