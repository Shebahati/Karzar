"""Orchestrate one IMG-02B candidate-discovery lane (external outputs only)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import ALLOWED_HOSTS, LANE_SPECS, SCHEMA_VERSION, TASK_ID, CandidateDiscoveryError
from .output import write_lane_outputs
from .providers.dasqua_official import discover_dasqua_candidates
from .providers.insize_tosag import discover_insize_candidates
from .providers.sanou_official import discover_sanou_candidates
from .transport import HostThrottledFetcher
from .worklists import load_worklist_rows, verify_worklist_checksums, worklist_facts

Clock = Callable[[], datetime]


def run_lane_candidate_discovery(
    *,
    lane: str,
    worklist_root: Path,
    output_dir: Path,
    repo_root: Path,
    concurrency: int = 3,
    delay: float = 0.75,
    timeout: float = 60.0,
    max_transient_retries: int = 2,
    limit: int | None = None,
    fetcher: HostThrottledFetcher | None = None,
    clock: Clock | None = None,
) -> dict[str, Any]:
    """Run one brand lane and write absolute-external candidate outputs."""
    if lane not in LANE_SPECS:
        raise CandidateDiscoveryError(
            "lane",
            f"unknown lane {lane!r}; known: {sorted(LANE_SPECS)}",
        )
    if concurrency <= 0:
        raise CandidateDiscoveryError("args", "--concurrency must be > 0")
    if delay < 0:
        raise CandidateDiscoveryError("args", "--delay must be >= 0")
    if limit is not None and limit < 0:
        raise CandidateDiscoveryError("args", "--limit must be >= 0")

    now = clock or (lambda: datetime.now(UTC))
    # started_at must precede any potentially networked operation.
    started_at = now()

    spec = LANE_SPECS[lane]
    checksums_digest = verify_worklist_checksums(worklist_root)
    facts = worklist_facts(worklist_root)
    work_items = load_worklist_rows(
        worklist_root,
        brand_key=spec["brand_key"],
        filename=spec["worklist"],
        # SAN OU: include ineligible tokenless rows so they become manual_review
        # (model_token_not_found), not silently dropped from the lane.
        include_ineligible=(lane == "san_ou"),
    )

    hosts = ALLOWED_HOSTS[lane]
    active_fetcher = fetcher or HostThrottledFetcher(
        allowed_hosts=hosts,
        delay=delay,
        timeout=timeout,
        max_transient_retries=max_transient_retries,
    )

    if lane == "dasqua":
        result = discover_dasqua_candidates(
            work_items,
            fetcher=active_fetcher,
            concurrency=concurrency,
            limit=limit,
        )
    elif lane == "insize":
        result = discover_insize_candidates(
            work_items,
            fetcher=active_fetcher,
            concurrency=concurrency,
            limit=limit,
        )
    elif lane == "san_ou":
        result = discover_sanou_candidates(
            work_items,
            fetcher=active_fetcher,
            concurrency=concurrency,
            limit=limit,
        )
    else:  # pragma: no cover — guarded by LANE_SPECS check
        raise CandidateDiscoveryError("lane", f"unhandled lane {lane!r}")

    finished_at = now()
    if finished_at < started_at:
        raise CandidateDiscoveryError(
            "clock",
            f"finished_at {finished_at.isoformat()} precedes started_at {started_at.isoformat()}",
        )
    elapsed_seconds = (finished_at - started_at).total_seconds()
    if elapsed_seconds < 0:
        raise CandidateDiscoveryError("clock", "elapsed_seconds must be >= 0")

    candidates = result["candidates"]
    rejected = result["rejected"]
    manual = result["manual"]
    stats = dict(result.get("stats") or {})
    discovered = int(stats.get("discovered_candidates", len(candidates)))
    validated = int(stats.get("validated_candidate_rows", len(candidates)))

    summary: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "lane_id": spec["lane_id"],
        "lane": lane,
        "brand_key": spec["brand_key"],
        "source_adapter": spec["adapter"],
        "source_class": spec["source_class"],
        "worklist_root": str(worklist_root),
        "worklist_checksums_digest": checksums_digest,
        "worklist_facts": facts,
        "requested": stats.get(
            "requested", len(work_items if limit is None else work_items[:limit])
        ),
        "discovered_candidates": discovered,
        "validated_candidate_rows": validated,
        # Legacy aliases kept for readers; do not treat as "accepted downloads".
        "accepted_candidates": discovered,
        "rejected": len(rejected),
        "manual_review": len(manual),
        "rights_status": "review_required",
        "apply_status": "not_started",
        "stats": stats,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": elapsed_seconds,
    }
    run_state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": TASK_ID,
        "lane_id": spec["lane_id"],
        "lane": lane,
        "concurrency": concurrency,
        "delay": delay,
        "timeout": timeout,
        "max_transient_retries": max_transient_retries,
        "limit": limit,
        "allowed_hosts": sorted(hosts),
        "discovered_candidates": discovered,
        "validated_candidate_rows": validated,
        "rejected_count": len(rejected),
        "manual_count": len(manual),
        "worklist_checksums_digest": checksums_digest,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": elapsed_seconds,
    }

    written = write_lane_outputs(
        output_dir,
        repo_root=repo_root,
        lane_id=spec["lane_id"],
        brand_key=spec["brand_key"],
        candidates=candidates,
        rejected=rejected,
        manual=manual,
        summary=summary,
        run_state=run_state,
    )
    return {
        **written,
        "summary": summary,
        "stats": stats,
    }
