"""Tests for deploy ownership preflight (stdlib fixtures; no VPS mutation)."""

from __future__ import annotations

import os
import stat
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "deploy" / "staging" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from deploy_ownership_preflight import (  # noqa: E402
    Finding,
    PathMeta,
    PreflightConfig,
    PreflightResult,
    assess_rsync_hazards,
    check_runner_identity,
    format_report,
    is_excluded,
    is_managed_rel,
    parse_rsync_itemize,
    run_preflight,
    scan_unexpected_root_ownership,
)


def _meta(
    path: Path, *, uid: int, gid: int = 1000, mode: int = 0o755, is_dir: bool = False
) -> PathMeta:
    return PathMeta(
        path=path,
        uid=uid,
        gid=gid,
        mode=mode | (stat.S_IFDIR if is_dir else stat.S_IFREG),
        is_dir=is_dir,
    )


def test_is_excluded_secrets_and_backups():
    assert is_excluded(".env")
    assert is_excluded("backups/foo")
    assert is_excluded("data/uploads/x")
    assert not is_excluded("deploy/staging/x")
    assert not is_excluded("services/gsc_mcp/server.py")


def test_is_managed_rel():
    assert is_managed_rel("deploy/staging/foo")
    assert is_managed_rel("services/gsc_mcp/x")
    assert is_managed_rel("audit/orphan")
    assert is_managed_rel("docker-compose.yml")
    assert is_managed_rel("_ops/input/file.xlsx")
    assert not is_managed_rel("backups/x")
    assert not is_managed_rel(".env")


def test_parse_rsync_itemize_deleting_and_transfer():
    out = textwrap.dedent(
        """\
        *deleting audit/insize-price-20-trailing-a/
        *deleting audit/insize-price-20-trailing-a/SYNC_REPORT.json
        >f+++++++++ deploy/staging/.env.gsc-mcp.template
        .d..t...... services/
        """
    )
    deleting, transferring = parse_rsync_itemize(out)
    assert "audit/insize-price-20-trailing-a" in deleting
    assert "audit/insize-price-20-trailing-a/SYNC_REPORT.json" in deleting
    assert "deploy/staging/.env.gsc-mcp.template" in transferring


def test_runner_identity_rejects_wrong_user(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    monkeypatch.setattr(os, "getegid", lambda: 1000)

    class FakePwd:
        pw_name = "other"

    monkeypatch.setattr(
        "deploy_ownership_preflight.pwd.getpwuid",
        lambda uid: FakePwd(),
    )
    findings, name, uid, gid = check_runner_identity(
        expected_user="github-runner", allow_root_runner=False
    )
    assert findings
    assert "expected user" in findings[0].failure_reason


def test_runner_identity_rejects_root(monkeypatch):
    monkeypatch.setattr(os, "geteuid", lambda: 0)
    monkeypatch.setattr(os, "getegid", lambda: 0)

    class FakePwd:
        pw_name = "root"

    monkeypatch.setattr(
        "deploy_ownership_preflight.pwd.getpwuid",
        lambda uid: FakePwd(),
    )
    findings, *_ = check_runner_identity(
        expected_user="github-runner", allow_root_runner=False
    )
    assert any("root" in f.failure_reason for f in findings)


def test_root_owned_replace_target_fails(tmp_path: Path):
    live = tmp_path / "Karzar"
    (live / "services" / "gsc_mcp").mkdir(parents=True)
    bad = live / "services" / "gsc_mcp" / "server.py"
    bad.write_text("x", encoding="utf-8")

    metas = {
        live: _meta(live, uid=1000, is_dir=True),
        live / "services": _meta(live / "services", uid=1000, is_dir=True),
        live / "services" / "gsc_mcp": _meta(live / "services" / "gsc_mcp", uid=0, is_dir=True),
        bad: _meta(bad, uid=0, mode=0o644),
    }

    def stat_fn(p: Path) -> PathMeta:
        if p in metas:
            return metas[p]
        return PathMeta(p, -1, -1, 0, False, exists=False)

    findings, checked = scan_unexpected_root_ownership(
        live,
        runner_uid=1000,
        stat_fn=stat_fn,
        walk_fn=lambda root: [bad, live / "services" / "gsc_mcp"],
    )
    assert checked >= 1
    assert any(f.path == str(bad) for f in findings)


def test_destination_only_undeletable_detected(tmp_path: Path):
    live = tmp_path / "live"
    src = tmp_path / "src"
    live.mkdir()
    src.mkdir()
    orphan = live / "audit" / "orphan-dir"
    orphan.mkdir(parents=True)
    (orphan / "file.csv").write_text("x", encoding="utf-8")
    os.chmod(live / "audit", 0o555)

    def dry_run(s: Path, d: Path):
        return (
            ["audit/orphan-dir", "audit/orphan-dir/file.csv"],
            [],
            "",
        )

    try:
        findings, _n, undeletable, _ur = assess_rsync_hazards(
            live,
            src,
            stat_fn=lambda p: PathMeta(
                p,
                uid=os.geteuid(),
                gid=os.getegid(),
                mode=p.stat().st_mode if p.exists() else 0,
                is_dir=p.is_dir() if p.exists() else False,
                exists=p.exists(),
            ),
            access_fn=os.access,
            dry_run_fn=dry_run,
        )
    finally:
        os.chmod(live / "audit", 0o755)

    assert undeletable >= 1
    assert any(f.required_operation == "delete" for f in findings)


def test_unreplaceable_when_parent_not_writable(tmp_path: Path):
    live = tmp_path / "live"
    src = tmp_path / "src"
    (live / "deploy" / "staging").mkdir(parents=True)
    (src / "deploy" / "staging").mkdir(parents=True)
    target = live / "deploy" / "staging" / "x.template"
    target.write_text("old", encoding="utf-8")
    (src / "deploy" / "staging" / "x.template").write_text("new", encoding="utf-8")
    os.chmod(live / "deploy" / "staging", 0o555)

    def dry_run(s: Path, d: Path):
        return ([], ["deploy/staging/x.template"], "")

    try:
        findings, _n, _ud, unreplaceable = assess_rsync_hazards(
            live,
            src,
            stat_fn=lambda p: PathMeta(
                p,
                uid=os.geteuid(),
                gid=os.getegid(),
                mode=p.stat().st_mode if p.exists() else 0,
                is_dir=p.is_dir() if p.exists() else False,
                exists=p.exists(),
            ),
            access_fn=os.access,
            dry_run_fn=dry_run,
        )
    finally:
        os.chmod(live / "deploy" / "staging", 0o755)

    assert unreplaceable >= 1
    assert any(f.required_operation == "replace" for f in findings)


def test_expected_env_excluded_from_root_scan(tmp_path: Path):
    live = tmp_path / "Karzar"
    live.mkdir()
    env = live / ".env"
    env.write_text("SECRET=1", encoding="utf-8")
    assert is_excluded(".env")

    findings, checked = scan_unexpected_root_ownership(
        live,
        runner_uid=1000,
        stat_fn=lambda p: (
            _meta(p, uid=0, mode=0o640) if p == env else _meta(p, uid=1000, is_dir=True)
        ),
        walk_fn=lambda root: [env],
    )
    assert findings == []
    assert checked == 0


def test_root_owned_outside_managed_ignored(tmp_path: Path):
    """Excluded host-state paths (backups/) are ignored even if root-owned."""
    live = tmp_path / "Karzar"
    deep = live / "backups" / "blob"
    deep.parent.mkdir(parents=True)
    deep.write_text("x", encoding="utf-8")
    assert not is_managed_rel("backups/blob")
    findings, _ = scan_unexpected_root_ownership(
        live,
        runner_uid=1000,
        stat_fn=lambda p: _meta(p, uid=0, mode=0o644, is_dir=p.is_dir()),
        walk_fn=lambda root: [deep],
    )
    assert findings == []


def test_unicode_and_spaces_paths_in_report():
    f = Finding(
        path="/opt/karzar/Karzar/audit/گزارش spaced/file.csv",
        owner="root",
        group="root",
        mode="0o644",
        required_operation="delete",
        failure_reason="destination-only rsync --delete hazard; runner cannot remove",
    )
    report = format_report(
        PreflightResult(
            status="FAIL", findings=[f], runner="github-runner", uid=1000, gid=1000
        )
    )
    assert "گزارش spaced/file.csv" in report
    assert "DEPLOY_OWNERSHIP_PREFLIGHT=FAIL" in report


def test_pass_all_runner_owned(tmp_path: Path, monkeypatch):
    live = tmp_path / "Karzar"
    fe = tmp_path / "frontend"
    incoming = tmp_path / "incoming"
    src = incoming / "abc" / "tree"
    for d in (live / "app", live / "deploy", fe, src / "app"):
        d.mkdir(parents=True)
    (src / "app" / "x.py").write_text("ok", encoding="utf-8")
    (live / "app" / "x.py").write_text("ok", encoding="utf-8")

    monkeypatch.setattr(os, "geteuid", lambda: os.getuid())
    monkeypatch.setattr(os, "getegid", lambda: os.getgid())

    class FakePwd:
        pw_name = "github-runner"

    monkeypatch.setattr(
        "deploy_ownership_preflight.pwd.getpwuid",
        lambda uid: FakePwd(),
    )

    cfg = PreflightConfig(
        expected_user="github-runner",
        live_root=live,
        frontend_root=fe,
        incoming_base=incoming,
        source_tree=src,
        use_rsync_dry_run=True,
    )
    result = run_preflight(
        cfg,
        dry_run_fn=lambda s, d: ([], [], ""),
    )
    assert result.status == "PASS"
    assert result.findings == []


def test_missing_optional_frontend_reports_required_missing(tmp_path: Path, monkeypatch):
    live = tmp_path / "Karzar"
    live.mkdir()
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    fe = tmp_path / "frontend-missing"

    monkeypatch.setattr(os, "geteuid", lambda: os.getuid())
    monkeypatch.setattr(os, "getegid", lambda: os.getgid())

    class FakePwd:
        pw_name = "github-runner"

    monkeypatch.setattr(
        "deploy_ownership_preflight.pwd.getpwuid",
        lambda uid: FakePwd(),
    )

    cfg = PreflightConfig(
        expected_user="github-runner",
        live_root=live,
        frontend_root=fe,
        incoming_base=incoming,
        source_tree=None,
        use_rsync_dry_run=False,
    )
    result = run_preflight(cfg)
    assert result.status == "FAIL"
    assert any("missing" in f.failure_reason for f in result.findings)


def test_workflow_orders_preflight_before_rsync():
    wf = Path(".github/workflows/deploy-staging.yml").read_text(encoding="utf-8")
    pre = wf.index("Ownership preflight")
    sync = wf.index("Sync backend → /opt/karzar/Karzar")
    assert pre < sync
    assert "chown -R" not in wf
    assert "deploy_ownership_preflight.py" in wf
    # Freeze gate remains before package/deploy; preflight does not clear freeze.
    assert "Deployment freeze gate" in wf
    assert wf.index("Deployment freeze gate") < pre


def test_historical_failure_model_preflight_before_rsync(tmp_path: Path, monkeypatch):
    """Model historical class: root-owned dest-only + replace target → FAIL before rsync."""
    live = tmp_path / "Karzar"
    src = tmp_path / "tree"
    fe = tmp_path / "frontend"
    incoming = tmp_path / "incoming"
    for d in (
        live / "services" / "gsc_mcp",
        live / "audit" / "insize-price-20-x",
        src / "services" / "gsc_mcp",
        fe,
        incoming,
    ):
        d.mkdir(parents=True)
    (src / "services" / "gsc_mcp" / "server.py").write_text("new", encoding="utf-8")
    (live / "services" / "gsc_mcp" / "server.py").write_text("old", encoding="utf-8")
    (live / "audit" / "insize-price-20-x" / "SYNC.json").write_text("{}", encoding="utf-8")

    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    monkeypatch.setattr(os, "getegid", lambda: 1000)

    class FakePwd:
        pw_name = "github-runner"

    monkeypatch.setattr(
        "deploy_ownership_preflight.pwd.getpwuid",
        lambda uid: FakePwd(),
    )

    rootish = {
        str(live / "services" / "gsc_mcp"),
        str(live / "services" / "gsc_mcp" / "server.py"),
        str(live / "audit" / "insize-price-20-x"),
        str(live / "audit" / "insize-price-20-x" / "SYNC.json"),
    }

    def stat_fn(p: Path) -> PathMeta:
        if not p.exists():
            return PathMeta(p, -1, -1, 0, False, exists=False)
        st = p.lstat()
        uid = 0 if str(p) in rootish else 1000
        return PathMeta(
            p, uid=uid, gid=0 if uid == 0 else 1000, mode=st.st_mode, is_dir=p.is_dir()
        )

    def access_fn(p: Path, mode: int) -> bool:
        meta = stat_fn(p)
        if meta.exists and meta.uid == 0 and mode & os.W_OK:
            return False
        # Parent of root-owned file: treat as non-writable for delete/replace
        if mode & os.W_OK:
            for child in list(rootish):
                try:
                    Path(child).relative_to(p)
                    if p != Path(child) and meta.exists:
                        # if p is parent of a rootish path, deny write to simulate
                        if any(Path(c).parent == p for c in rootish):
                            return False
                except ValueError:
                    pass
        return True if meta.exists else os.access(p, mode)

    def dry_run(s: Path, d: Path):
        return (
            ["audit/insize-price-20-x", "audit/insize-price-20-x/SYNC.json"],
            ["services/gsc_mcp/server.py"],
            "",
        )

    rsync_invoked = {"n": 0}

    def guarded_dry_run(s: Path, d: Path):
        rsync_invoked["n"] += 1
        return dry_run(s, d)

    cfg = PreflightConfig(
        expected_user="github-runner",
        live_root=live,
        frontend_root=fe,
        incoming_base=incoming,
        source_tree=src,
    )
    result = run_preflight(
        cfg, stat_fn=stat_fn, access_fn=access_fn, dry_run_fn=guarded_dry_run
    )
    assert result.status == "FAIL"
    assert (
        result.undeletable >= 1
        or result.unreplaceable >= 1
        or result.unexpected_ownership >= 1
    )
    # Preflight may call dry-run plan once; never mutates (no real rsync).
    assert rsync_invoked["n"] == 1
