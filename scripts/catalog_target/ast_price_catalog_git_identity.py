"""Independent repository commit attestation for owner acceptance."""

from __future__ import annotations

import subprocess
from pathlib import Path

from catalog_target.sales_wave_apply import ApplyAbort


def resolve_repository_commit_sha(repo_root: Path | None = None) -> str:
    root = repo_root or Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise ApplyAbort("repository_commit_sha_unavailable")
    value = (proc.stdout or "").strip()
    if len(value) != 40:
        raise ApplyAbort("repository_commit_sha_invalid")
    return value


def assert_repository_commit_sha(expected_sha: str, *, repo_root: Path | None = None) -> str:
    live = resolve_repository_commit_sha(repo_root)
    expected = (expected_sha or "").strip()
    if not expected:
        raise ApplyAbort("owner_acceptance_repository_commit_sha_missing")
    if live != expected:
        raise ApplyAbort("owner_acceptance_repository_commit_sha_mismatch_runtime")
    return live
