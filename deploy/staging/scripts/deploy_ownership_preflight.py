#!/usr/bin/env python3
"""Read-only deployment ownership preflight (fail-closed).

Runs before live rsync into /opt/karzar/Karzar. Never chowns/chmods.
Exit 0 = PASS, nonzero = FAIL.
"""

from __future__ import annotations

import argparse
import os
import pwd
import grp
import stat
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

DEFAULT_EXPECTED_USER = "github-runner"
DEFAULT_LIVE = Path("/opt/karzar/Karzar")
DEFAULT_FRONTEND = Path("/opt/karzar/frontend")
DEFAULT_INCOMING_BASE = Path("/opt/karzar/incoming")

# Relative to live checkout: rsync-managed content that must be runner-owned.
MANAGED_REL_PREFIXES = (
    "app/",
    "deploy/",
    "services/",
    "audit/",
    "aods/",
    "scripts/",
    "alembic/",
    "openapi/",
    "tests/",
    "docs/",
    "frontend/",  # leftover under live tree is deleted by workflow after rsync
)

# Basename / relative exclusions (secrets & host state — not runner-owned).
EXCLUDED_REL_PREFIXES = (
    "backups/",
    "rollout-backups/",
    "data/uploads/",
    "logs/",
    "actions-runner/",
)
EXCLUDED_BASENAMES = frozenset(
    {
        ".env",
        ".deploy-secrets",
        ".env.staging.generated",
        ".git",
        ".github",
    }
)

# Same excludes as deploy-staging.yml Sync backend (relative patterns for rsync).
RSYNC_EXCLUDES = (
    ".git/",
    ".github/",
    "/frontend/",
    ".venv/",
    "venv/",
    "__pycache__/",
    ".pytest_cache/",
    ".env",
    ".deploy-secrets",
    ".env.staging.generated",
    "backups/",
    "rollout-backups/",
    "data/uploads/",
    "logs/",
    "*.pyc",
    ".mypy_cache/",
    ".ruff_cache/",
    ".coverage",
    "actions-runner/",
)


@dataclass
class Finding:
    path: str
    owner: str
    group: str
    mode: str
    required_operation: str
    failure_reason: str


@dataclass
class PathMeta:
    path: Path
    uid: int
    gid: int
    mode: int
    is_dir: bool
    exists: bool = True


StatFn = Callable[[Path], PathMeta]
AccessFn = Callable[[Path, int], bool]


def _real_stat(path: Path) -> PathMeta:
    try:
        st = path.lstat()
    except FileNotFoundError:
        return PathMeta(path=path, uid=-1, gid=-1, mode=0, is_dir=False, exists=False)
    return PathMeta(
        path=path,
        uid=st.st_uid,
        gid=st.st_gid,
        mode=st.st_mode,
        is_dir=stat.S_ISDIR(st.st_mode),
        exists=True,
    )


def _real_access(path: Path, mode: int) -> bool:
    return os.access(path, mode)


def _name_uid(uid: int) -> str:
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return str(uid)


def _name_gid(gid: int) -> str:
    try:
        return grp.getgrgid(gid).gr_name
    except KeyError:
        return str(gid)


def _mode_oct(mode: int) -> str:
    return oct(stat.S_IMODE(mode))


def _rel_under(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def is_excluded(rel: str) -> bool:
    base = Path(rel).name
    if base in EXCLUDED_BASENAMES:
        return True
    if rel in EXCLUDED_BASENAMES:
        return True
    for pref in EXCLUDED_REL_PREFIXES:
        if rel == pref.rstrip("/") or rel.startswith(pref):
            return True
    return False


def is_managed_rel(rel: str) -> bool:
    """True for paths inside the live tree that rsync may create/replace/delete.

    Deploy Staging runs ``rsync -a --delete`` over the whole checkout with a
    fixed exclude list. Therefore every non-excluded relative path is managed —
    including destination-only orphans (e.g. ``_ops/``, ``audit/…``) whose first
    component is not in MANAGED_REL_PREFIXES.
    """
    if is_excluded(rel):
        return False
    # Entire non-excluded live tree is rsync-managed (including dest-only orphans).
    # MANAGED_REL_PREFIXES documents the common deploy surface for operators.
    return True


@dataclass
class PreflightConfig:
    expected_user: str = DEFAULT_EXPECTED_USER
    live_root: Path = DEFAULT_LIVE
    frontend_root: Path = DEFAULT_FRONTEND
    incoming_base: Path = DEFAULT_INCOMING_BASE
    source_tree: Path | None = None
    github_sha: str | None = None
    allow_root_runner: bool = False
    use_rsync_dry_run: bool = True
    max_findings: int = 40


@dataclass
class PreflightResult:
    status: str
    findings: list[Finding] = field(default_factory=list)
    objects_checked: int = 0
    managed_paths: int = 0
    unexpected_ownership: int = 0
    undeletable: int = 0
    unreplaceable: int = 0
    runner: str = ""
    uid: int = -1
    gid: int = -1
    summary_lines: list[str] = field(default_factory=list)


def check_runner_identity(
    *,
    expected_user: str,
    allow_root_runner: bool,
) -> tuple[list[Finding], str, int, int]:
    findings: list[Finding] = []
    uid = os.geteuid()
    gid = os.getegid()
    name = _name_uid(uid)
    if uid == 0 and not allow_root_runner:
        findings.append(
            Finding(
                path="(process)",
                owner=name,
                group=_name_gid(gid),
                mode="-",
                required_operation="identity",
                failure_reason="deployment preflight must not run as root",
            )
        )
    elif name != expected_user and uid != 0:
        findings.append(
            Finding(
                path="(process)",
                owner=name,
                group=_name_gid(gid),
                mode="-",
                required_operation="identity",
                failure_reason=f"expected user {expected_user!r}, got {name!r}",
            )
        )
    return findings, name, uid, gid


def check_roots_writable(
    roots: Iterable[Path],
    *,
    stat_fn: StatFn,
    access_fn: AccessFn,
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    checked = 0
    for root in roots:
        checked += 1
        meta = stat_fn(root)
        if not meta.exists:
            findings.append(
                Finding(
                    path=str(root),
                    owner="-",
                    group="-",
                    mode="-",
                    required_operation="traverse",
                    failure_reason="required path missing",
                )
            )
            continue
        if not access_fn(root, os.R_OK | os.X_OK):
            findings.append(
                Finding(
                    path=str(root),
                    owner=_name_uid(meta.uid),
                    group=_name_gid(meta.gid),
                    mode=_mode_oct(meta.mode),
                    required_operation="traverse",
                    failure_reason="runner cannot traverse",
                )
            )
        if not access_fn(root, os.W_OK):
            findings.append(
                Finding(
                    path=str(root),
                    owner=_name_uid(meta.uid),
                    group=_name_gid(meta.gid),
                    mode=_mode_oct(meta.mode),
                    required_operation="write",
                    failure_reason="runner cannot write (rsync requires writable dest)",
                )
            )
    return findings, checked


def scan_unexpected_root_ownership(
    live_root: Path,
    *,
    runner_uid: int,
    stat_fn: StatFn,
    access_fn: AccessFn | None = None,
    walk_fn: Callable[[Path], Iterable[Path]] | None = None,
) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    checked = 0
    access = access_fn or _real_access

    def default_walk(root: Path) -> Iterable[Path]:
        if not root.exists():
            return []
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # Prune excluded directories early
            rel_dir = _rel_under(root, Path(dirpath))
            if is_excluded(rel_dir + "/") or is_excluded(rel_dir):
                dirnames[:] = []
                continue
            # Mutate dirnames to skip excluded children
            keep = []
            for d in dirnames:
                child_rel = f"{rel_dir}/{d}".lstrip("./") if rel_dir not in ("", ".") else d
                if is_excluded(child_rel) or is_excluded(child_rel + "/"):
                    continue
                keep.append(d)
            dirnames[:] = keep
            yield Path(dirpath)
            for fn in filenames:
                yield Path(dirpath) / fn

    walker = walk_fn or default_walk
    for path in walker(live_root):
        rel = _rel_under(live_root, path)
        if is_excluded(rel):
            continue
        if not is_managed_rel(rel) and rel not in ("", "."):
            # Still check top-level managed files; skip deep unmanaged
            if "/" in rel:
                continue
        meta = stat_fn(path)
        if not meta.exists:
            continue
        checked += 1
        if meta.uid == 0:
            findings.append(
                Finding(
                    path=str(path),
                    owner=_name_uid(meta.uid),
                    group=_name_gid(meta.gid),
                    mode=_mode_oct(meta.mode),
                    required_operation="own",
                    failure_reason="unexpected root ownership in runner-managed tree",
                )
            )
        elif meta.uid != runner_uid and runner_uid != 0:
            # Non-root foreign ownership also breaks rsync -a chown/chgrp and writes
            parent = path.parent
            if not access(parent, os.W_OK) or (meta.is_dir is False and not access(path, os.W_OK)):
                findings.append(
                    Finding(
                        path=str(path),
                        owner=_name_uid(meta.uid),
                        group=_name_gid(meta.gid),
                        mode=_mode_oct(meta.mode),
                        required_operation="replace",
                        failure_reason="non-runner ownership and not writable by runner",
                    )
                )
    return findings, checked


def _can_unlink(path: Path, *, access_fn: AccessFn, stat_fn: StatFn) -> bool:
    meta = stat_fn(path)
    if not meta.exists:
        return True
    parent = path.parent
    # Need write+exec on parent to unlink
    if not access_fn(parent, os.W_OK | os.X_OK):
        return False
    # Sticky bit: need to own the file
    pmeta = stat_fn(parent)
    if pmeta.exists and (pmeta.mode & stat.S_ISVTX) and meta.uid != os.geteuid() and os.geteuid() != 0:
        return False
    return True


def _can_replace(path: Path, *, access_fn: AccessFn, stat_fn: StatFn) -> bool:
    meta = stat_fn(path)
    parent = path.parent
    if not access_fn(parent, os.W_OK | os.X_OK):
        return False
    # rsync creates temp file in parent then renames
    if meta.exists and not access_fn(path, os.W_OK) and meta.uid != os.geteuid():
        # May still rename over if parent writable and we can unlink
        return _can_unlink(path, access_fn=access_fn, stat_fn=stat_fn)
    return True


def parse_rsync_itemize(stdout: str) -> tuple[list[str], list[str]]:
    """Return (deleting_rels, transferring_rels) relative paths."""
    deleting: list[str] = []
    transferring: list[str] = []
    for line in stdout.splitlines():
        line = line.rstrip("\n")
        if line.startswith("*deleting "):
            deleting.append(line[len("*deleting ") :].rstrip("/"))
            continue
        # itemize: YXcstpoguax path
        if len(line) > 12 and line[0] in {">", "c", "h", ".", "*"} and " " in line:
            code, _, path = line.partition(" ")
            if not path:
                continue
            # transfers / creates
            if code.startswith(">") or code.startswith("c"):
                transferring.append(path.rstrip("/"))
    return deleting, transferring


def rsync_dry_run_plan(
    source: Path,
    dest: Path,
    *,
    excludes: Iterable[str] = RSYNC_EXCLUDES,
) -> tuple[list[str], list[str], str]:
    cmd = [
        "rsync",
        "-a",
        "--delete",
        "--dry-run",
        "--itemize-changes",
        "--out-format=%i %n",
    ]
    for ex in excludes:
        cmd.append(f"--exclude={ex}")
    cmd.append(f"{source}/")
    cmd.append(f"{dest}/")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    # dry-run can return 23 when dest has permission issues — still parse stdout
    deleting, transferring = parse_rsync_itemize(proc.stdout)
    return deleting, transferring, proc.stderr


def assess_rsync_hazards(
    live_root: Path,
    source_tree: Path,
    *,
    stat_fn: StatFn,
    access_fn: AccessFn,
    use_rsync: bool = True,
    dry_run_fn: Callable[[Path, Path], tuple[list[str], list[str], str]] | None = None,
) -> tuple[list[Finding], int, int, int]:
    findings: list[Finding] = []
    undeletable = 0
    unreplaceable = 0
    checked = 0

    if use_rsync:
        if dry_run_fn is None:
            deleting, transferring, _err = rsync_dry_run_plan(source_tree, live_root)
        else:
            deleting, transferring, _err = dry_run_fn(source_tree, live_root)
    else:
        deleting, transferring = [], []

    for rel in deleting:
        if is_excluded(rel):
            continue
        dest = live_root / rel
        checked += 1
        meta = stat_fn(dest)
        if not meta.exists:
            continue
        if not _can_unlink(dest, access_fn=access_fn, stat_fn=stat_fn):
            undeletable += 1
            findings.append(
                Finding(
                    path=str(dest),
                    owner=_name_uid(meta.uid) if meta.uid >= 0 else "-",
                    group=_name_gid(meta.gid) if meta.gid >= 0 else "-",
                    mode=_mode_oct(meta.mode) if meta.exists else "-",
                    required_operation="delete",
                    failure_reason="destination-only rsync --delete hazard; runner cannot remove",
                )
            )

    for rel in transferring:
        if is_excluded(rel):
            continue
        dest = live_root / rel
        checked += 1
        meta = stat_fn(dest)
        if not meta.exists:
            # creating new — need parent writable
            parent = dest.parent
            pmeta = stat_fn(parent)
            if pmeta.exists and not access_fn(parent, os.W_OK | os.X_OK):
                unreplaceable += 1
                findings.append(
                    Finding(
                        path=str(dest),
                        owner=_name_uid(pmeta.uid),
                        group=_name_gid(pmeta.gid),
                        mode=_mode_oct(pmeta.mode),
                        required_operation="create",
                        failure_reason="runner cannot create temp file in parent (mkstemp class)",
                    )
                )
            continue
        if not _can_replace(dest, access_fn=access_fn, stat_fn=stat_fn):
            unreplaceable += 1
            findings.append(
                Finding(
                    path=str(dest),
                    owner=_name_uid(meta.uid),
                    group=_name_gid(meta.gid),
                    mode=_mode_oct(meta.mode),
                    required_operation="replace",
                    failure_reason="runner cannot replace (mkstemp/rename/unlink class)",
                )
            )

    return findings, checked, undeletable, unreplaceable


def suggest_remediation(findings: list[Finding]) -> list[str]:
    lines = [
        "Remediation is Owner/operator-authorized only. Preflight does NOT chown.",
        "Suggested exact commands (not executed):",
    ]
    seen: set[str] = set()
    for f in findings:
        if f.path == "(process)":
            continue
        if f.path in seen:
            continue
        seen.add(f.path)
        # Exact path only — no wildcards
        lines.append(f"  sudo chown github-runner:github-runner -- {f.path}")
        if len(seen) >= 20:
            lines.append("  … truncated …")
            break
    lines.append(
        "Do not run: chown -R /opt/karzar, chmod 777, or broad recursive repairs."
    )
    return lines


def run_preflight(
    cfg: PreflightConfig,
    *,
    stat_fn: StatFn = _real_stat,
    access_fn: AccessFn = _real_access,
    dry_run_fn: Callable[[Path, Path], tuple[list[str], list[str], str]] | None = None,
) -> PreflightResult:
    result = PreflightResult(status="PASS")
    id_findings, name, uid, gid = check_runner_identity(
        expected_user=cfg.expected_user,
        allow_root_runner=cfg.allow_root_runner,
    )
    result.runner = name
    result.uid = uid
    result.gid = gid
    result.findings.extend(id_findings)

    source = cfg.source_tree
    if source is None and cfg.github_sha:
        source = cfg.incoming_base / cfg.github_sha / "tree"

    roots = [cfg.live_root, cfg.frontend_root, cfg.incoming_base]
    if source is not None:
        roots.append(source)
    root_findings, n_roots = check_roots_writable(roots, stat_fn=stat_fn, access_fn=access_fn)
    result.findings.extend(root_findings)
    result.managed_paths = n_roots
    result.objects_checked += n_roots

    own_findings, n_own = scan_unexpected_root_ownership(
        cfg.live_root,
        runner_uid=uid,
        stat_fn=stat_fn,
        access_fn=access_fn,
    )
    result.findings.extend(own_findings)
    result.objects_checked += n_own
    result.unexpected_ownership = sum(
        1 for f in own_findings if "ownership" in f.failure_reason or f.required_operation == "own"
    )

    if source is not None and source.exists() and cfg.use_rsync_dry_run:
        hz_findings, n_hz, undeletable, unreplaceable = assess_rsync_hazards(
            cfg.live_root,
            source,
            stat_fn=stat_fn,
            access_fn=access_fn,
            use_rsync=True,
            dry_run_fn=dry_run_fn,
        )
        result.findings.extend(hz_findings)
        result.objects_checked += n_hz
        result.undeletable = undeletable
        result.unreplaceable = unreplaceable
    elif cfg.use_rsync_dry_run and source is None:
        result.summary_lines.append(
            "NOTE: source_tree/GITHUB_SHA not set — skipped rsync dry-run delete/replace plan"
        )

    # Deduplicate by path+operation
    uniq: dict[tuple[str, str], Finding] = {}
    for f in result.findings:
        uniq[(f.path, f.required_operation)] = f
    result.findings = list(uniq.values())

    if result.findings:
        result.status = "FAIL"
    return result


def format_report(result: PreflightResult, *, max_findings: int = 40) -> str:
    lines = [
        "DEPLOY_OWNERSHIP_PREFLIGHT",
        f"runner={result.runner} uid={result.uid} gid={result.gid}",
        f"managed_paths={result.managed_paths}",
        f"objects_checked={result.objects_checked}",
        f"unexpected_ownership={result.unexpected_ownership}",
        f"undeletable={result.undeletable}",
        f"unreplaceable={result.unreplaceable}",
        f"status={result.status}",
    ]
    lines.extend(result.summary_lines)
    if result.findings:
        lines.append("")
        lines.append("DEPLOY_OWNERSHIP_PREFLIGHT=FAIL")
        lines.append("PATH | OWNER | GROUP | MODE | REQUIRED_OPERATION | FAILURE_REASON")
        for f in result.findings[:max_findings]:
            lines.append(
                f"{f.path} | {f.owner} | {f.group} | {f.mode} | "
                f"{f.required_operation} | {f.failure_reason}"
            )
        if len(result.findings) > max_findings:
            lines.append(f"... {len(result.findings) - max_findings} more ...")
        lines.append("")
        lines.extend(suggest_remediation(result.findings))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expected-user", default=DEFAULT_EXPECTED_USER)
    p.add_argument("--live-root", type=Path, default=DEFAULT_LIVE)
    p.add_argument("--frontend-root", type=Path, default=DEFAULT_FRONTEND)
    p.add_argument("--incoming-base", type=Path, default=DEFAULT_INCOMING_BASE)
    p.add_argument("--source-tree", type=Path, default=None)
    p.add_argument("--github-sha", default=os.environ.get("GITHUB_SHA") or None)
    p.add_argument("--allow-root-runner", action="store_true")
    p.add_argument("--skip-rsync-dry-run", action="store_true")
    p.add_argument("--json-out", type=Path, default=None)
    args = p.parse_args(argv)

    cfg = PreflightConfig(
        expected_user=args.expected_user,
        live_root=args.live_root,
        frontend_root=args.frontend_root,
        incoming_base=args.incoming_base,
        source_tree=args.source_tree,
        github_sha=args.github_sha,
        allow_root_runner=args.allow_root_runner,
        use_rsync_dry_run=not args.skip_rsync_dry_run,
    )
    result = run_preflight(cfg)
    sys.stdout.write(format_report(result))
    if args.json_out:
        import json

        payload = {
            "status": result.status,
            "runner": result.runner,
            "uid": result.uid,
            "gid": result.gid,
            "managed_paths": result.managed_paths,
            "objects_checked": result.objects_checked,
            "unexpected_ownership": result.unexpected_ownership,
            "undeletable": result.undeletable,
            "unreplaceable": result.unreplaceable,
            "findings": [f.__dict__ for f in result.findings],
            "auto_chown": False,
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0 if result.status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
