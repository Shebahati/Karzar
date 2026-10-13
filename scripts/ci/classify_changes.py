#!/usr/bin/env python3
"""Classify changed paths into CI risk tiers (default-deny UNKNOWN → conservative FULL)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO / ".github" / "ci" / "policy.json"
FULL_LABEL = "ci:full"

DOMAIN_BY_TAG: dict[str, str] = {
    "docs_only": "docs",
    "frontend_storefront": "storefront",
    "frontend_admin": "admin",
    "backend_heavy": "backend",
    "aods_governance": "aods-governance",
    "aods_tools": "aods-tools",
    "ci_meta": "ci-control-plane",
    "workflows": "ci-control-plane",
    "deploy": "deploy",
    "critical_r3": "critical",
    "scripts_audit": "scripts-audit",
    "scripts_apply": "scripts-mutation",
    "scripts_unknown": "scripts-unknown",
    "unknown": "unknown",
}


@dataclass
class Classification:
    risk_tier: str
    scenario: str
    conservative: bool
    unknown_paths: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)
    run_backend_lint: bool = False
    run_backend_test_heavy: bool = False
    run_aods_fast: bool = True
    run_aods_openapi: bool = False
    run_frontend_storefront: bool = False
    run_frontend_admin: bool = False
    run_frontend_e2e: bool = False
    run_deploy_staging_guard: bool = False
    run_audit_script_validation: bool = False
    changed_paths: list[str] = field(default_factory=list)
    changed_readonly_audit_scripts: list[str] = field(default_factory=list)

    def to_github_outputs(self) -> dict[str, str]:
        data = asdict(self)
        out: dict[str, str] = {}
        for key, value in data.items():
            if isinstance(value, bool):
                out[key] = "true" if value else "false"
            elif isinstance(value, list):
                out[key] = json.dumps(value)
            else:
                out[key] = str(value)
        return out


def load_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _prefixes(rule_id: str, policy: dict) -> list[str]:
    for rule in policy["path_rules"]:
        if rule["id"] == rule_id:
            return list(rule["prefixes"])
    return []


def matches_any(path: str, prefixes: list[str]) -> bool:
    for prefix in prefixes:
        if prefix.endswith("/"):
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                return True
        elif path == prefix or path.startswith(prefix + "/") or path.startswith(prefix):
            return True
    return False


def _is_script_mutation(path: str, policy: dict) -> bool:
    """Mutation / high-risk script paths win before read-only audit allowlist."""
    name = Path(path).name
    mutation_prefixes = policy.get("script_mutation_prefixes", [])
    if any(matches_any(path, [p]) for p in mutation_prefixes):
        return True
    for marker in policy.get("script_mutation_name_markers", []):
        if marker in name:
            return True
    return False


def _is_readonly_audit_script(path: str, policy: dict) -> bool:
    return path in set(policy.get("script_readonly_audit_allowlist", []))


def script_tags(path: str, policy: dict) -> set[str]:
    if not path.startswith("scripts/"):
        return set()
    if _is_script_mutation(path, policy):
        return {"scripts_apply"}
    if _is_readonly_audit_script(path, policy):
        return {"scripts_audit"}
    return {"scripts_unknown"}


def classify_path(path: str, policy: dict) -> set[str]:
    tags: set[str] = set()
    for rule in policy["path_rules"]:
        if matches_any(path, rule["prefixes"]):
            tags.add(rule["id"])
    tags |= script_tags(path, policy)
    if not tags:
        tags.add("unknown")
    return tags


def domains_from_tags(tag_union: set[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in sorted(tag_union):
        domain = DOMAIN_BY_TAG.get(tag, tag)
        if domain not in seen:
            seen.add(domain)
            ordered.append(domain)
    return ordered


def git_changed_paths(base: str, head: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...{head}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        proc = subprocess.run(
            ["git", "diff", "--name-only", base, head],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        )
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def parse_labels(raw: str | None) -> set[str]:
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def _deploy_staging_guard(paths: list[str]) -> bool:
    return any(p.startswith("deploy/staging/") for p in paths)


def _openapi_needed(paths: list[str], policy: dict, *, force: bool = False) -> bool:
    if force:
        return True
    openapi_prefixes = policy.get("openapi_triggers", {}).get("prefixes", [])
    return any(matches_any(p, openapi_prefixes) for p in paths) or not paths


def _e2e_needed(paths: list[str], policy: dict) -> bool:
    e2e_prefixes = policy.get("storefront_e2e_triggers", {}).get("prefixes", [])
    return any(matches_any(p, e2e_prefixes) for p in paths)


def _stack_flags(paths: list[str], policy: dict) -> tuple[bool, bool, bool]:
    has_storefront = any(p.startswith("frontend/Storefront/") for p in paths)
    has_admin = any(p.startswith("frontend/admin-panel/") for p in paths)
    backend_prefixes = _prefixes("backend_heavy", policy)
    has_backend = any(matches_any(p, backend_prefixes) for p in paths)
    return has_backend, has_storefront, has_admin


def _full_classification(
    paths: list[str],
    *,
    scenario: str,
    unknown_paths: list[str] | None = None,
    tag_union: set[str] | None = None,
) -> Classification:
    policy = load_policy()
    tags = set(tag_union or ())
    for path in paths:
        tags |= classify_path(path, policy)
    return Classification(
        risk_tier="FULL",
        scenario=scenario,
        conservative=True,
        unknown_paths=unknown_paths or [],
        domains=domains_from_tags(tags),
        run_backend_lint=True,
        run_backend_test_heavy=True,
        run_aods_fast=True,
        run_aods_openapi=True,
        run_frontend_storefront=True,
        run_frontend_admin=True,
        run_frontend_e2e=True,
        run_deploy_staging_guard=_deploy_staging_guard(paths),
        changed_paths=paths,
    )


def _r3_classification(
    paths: list[str],
    *,
    scenario: str,
    tag_union: set[str],
    policy: dict,
) -> Classification:
    _, has_storefront, has_admin = _stack_flags(paths, policy)
    e2e = _e2e_needed(paths, policy) or has_storefront
    return Classification(
        risk_tier="R3",
        scenario=scenario,
        conservative=True,
        domains=domains_from_tags(tag_union),
        run_backend_lint=True,
        run_backend_test_heavy=True,
        run_aods_fast=True,
        run_aods_openapi=True,
        run_frontend_storefront=has_storefront,
        run_frontend_admin=has_admin,
        run_frontend_e2e=e2e,
        run_deploy_staging_guard=_deploy_staging_guard(paths),
        changed_paths=paths,
    )


def _backend_r2(
    paths: list[str],
    *,
    scenario: str,
    policy: dict,
    tag_union: set[str],
    conservative: bool = False,
    openapi_force: bool = False,
) -> Classification:
    openapi_needed = _openapi_needed(paths, policy, force=openapi_force)
    return Classification(
        risk_tier="R2",
        scenario=scenario,
        conservative=conservative,
        domains=domains_from_tags(tag_union),
        run_backend_lint=True,
        run_backend_test_heavy=True,
        run_aods_fast=True,
        run_aods_openapi=openapi_needed,
        run_deploy_staging_guard=_deploy_staging_guard(paths),
        changed_paths=paths,
    )


def _is_critical(tag_union: set[str]) -> bool:
    return bool(
        tag_union
        & {
            "critical_r3",
            "scripts_apply",
            "scripts_unknown",
            "deploy",
            "workflows",
            "ci_meta",
        }
    )


def classify(
    paths: list[str],
    *,
    force_full: bool = False,
    pr_labels: set[str] | None = None,
    event_name: str | None = None,
) -> Classification:
    policy = load_policy()
    pr_labels = pr_labels or set()
    full_label = policy.get("full_regression_label", FULL_LABEL)

    if force_full or full_label in pr_labels or event_name in {"schedule", "workflow_dispatch"}:
        scenario = "J" if full_label in pr_labels else "FULL"
        return _full_classification(paths, scenario=scenario)

    if not paths:
        return Classification(
            risk_tier="R0",
            scenario="A",
            conservative=False,
            domains=["none"],
            run_aods_fast=True,
            changed_paths=[],
        )

    per_path_tags = {p: classify_path(p, policy) for p in paths}
    unknown_paths = sorted(p for p, tags in per_path_tags.items() if "unknown" in tags)
    tag_union: set[str] = set()
    for tags in per_path_tags.values():
        tag_union |= tags

    openapi_needed = _openapi_needed(paths, policy)
    e2e_needed = _e2e_needed(paths, policy)

    has_workflows = "workflows" in tag_union or "ci_meta" in tag_union
    has_backend = "backend_heavy" in tag_union or "aods_tools" in tag_union
    has_storefront = "frontend_storefront" in tag_union
    has_admin = "frontend_admin" in tag_union
    has_docs_only = tag_union <= {"docs_only"} or (
        tag_union <= {"docs_only", "aods_governance"} and not has_backend
    )

    if unknown_paths:
        return _full_classification(
            paths, scenario="I", unknown_paths=unknown_paths, tag_union=tag_union
        )
    if has_workflows:
        return _full_classification(paths, scenario="H", tag_union=tag_union)

    if any(p.startswith("alembic/") for p in paths):
        return _r3_classification(paths, scenario="E", tag_union=tag_union, policy=policy)

    if _is_critical(tag_union):
        scenario = "K" if tag_union <= {"deploy"} else "R3"
        return _r3_classification(paths, scenario=scenario, tag_union=tag_union, policy=policy)

    if tag_union <= {"aods_governance"}:
        return Classification(
            risk_tier="R0",
            scenario="G",
            conservative=False,
            domains=domains_from_tags(tag_union),
            run_aods_fast=True,
            run_aods_openapi=openapi_needed,
            changed_paths=paths,
        )

    if "aods_tools" in tag_union:
        return _backend_r2(
            paths,
            scenario="G2",
            policy=policy,
            tag_union=tag_union,
            openapi_force=True,
        )

    if paths and all(p.startswith("openapi/") for p in paths):
        return _backend_r2(
            paths, scenario="F", policy=policy, tag_union=tag_union, openapi_force=True
        )

    if "scripts_audit" in tag_union and tag_union <= {"scripts_audit", "docs_only"}:
        readonly_scripts = sorted(
            p for p in paths if _is_readonly_audit_script(p, policy)
        )
        return Classification(
            risk_tier="R1",
            scenario="M",
            conservative=False,
            domains=domains_from_tags(tag_union),
            run_audit_script_validation=True,
            changed_readonly_audit_scripts=readonly_scripts,
            run_aods_fast=True,
            changed_paths=paths,
        )

    if has_docs_only and not (has_storefront or has_admin or has_backend):
        return Classification(
            risk_tier="R0",
            scenario="A",
            conservative=False,
            domains=domains_from_tags(tag_union),
            run_aods_fast=True,
            changed_paths=paths,
        )

    if openapi_needed and not has_backend:
        return _backend_r2(
            paths, scenario="F", policy=policy, tag_union=tag_union, openapi_force=True
        )

    if has_backend and not has_storefront and not has_admin:
        return _backend_r2(
            paths,
            scenario="D",
            policy=policy,
            tag_union=tag_union,
            openapi_force=openapi_needed,
        )

    if has_storefront and not has_admin and not has_backend:
        return Classification(
            risk_tier="R1",
            scenario="B",
            conservative=False,
            domains=domains_from_tags(tag_union),
            run_frontend_storefront=True,
            run_frontend_e2e=e2e_needed,
            run_aods_fast=True,
            changed_paths=paths,
        )

    if has_admin and not has_storefront and not has_backend:
        return Classification(
            risk_tier="R1",
            scenario="C",
            conservative=False,
            domains=domains_from_tags(tag_union),
            run_frontend_admin=True,
            run_aods_fast=True,
            changed_paths=paths,
        )

    return _full_classification(paths, scenario="FULL", tag_union=tag_union)


def skip_reasons(result: Classification) -> list[str]:
    reasons: list[str] = []
    if not result.run_backend_lint:
        reasons.append("backend app lint skipped (tier/scenario does not require full ruff/mypy)")
    if not result.run_audit_script_validation:
        reasons.append("read-only audit script validation skipped (no allowlisted audit scripts)")
    if not result.run_backend_test_heavy:
        reasons.append("Postgres/Redis pytest skipped (R0/R1 or deploy-guard-only)")
    if not result.run_aods_openapi:
        reasons.append("AODS OpenAPI gate skipped (no API contract touch)")
    if not result.run_frontend_storefront:
        reasons.append("storefront unit checks skipped (no Storefront paths)")
    if not result.run_frontend_admin:
        reasons.append("admin-panel checks skipped (no admin paths)")
    if not result.run_frontend_e2e:
        reasons.append("storefront e2e skipped (non-sensitive Storefront paths)")
    if not result.run_deploy_staging_guard:
        reasons.append("deploy/staging Dockerfile guard skipped (no staging deploy paths)")
    return reasons


def write_step_summary(result: Classification) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    flags = {
        "run_backend_lint": result.run_backend_lint,
        "run_backend_test_heavy": result.run_backend_test_heavy,
        "run_aods_fast": result.run_aods_fast,
        "run_aods_openapi": result.run_aods_openapi,
        "run_frontend_storefront": result.run_frontend_storefront,
        "run_frontend_admin": result.run_frontend_admin,
        "run_frontend_e2e": result.run_frontend_e2e,
        "run_deploy_staging_guard": result.run_deploy_staging_guard,
        "run_audit_script_validation": result.run_audit_script_validation,
    }
    lines = [
        "## CI risk classification",
        "",
        f"- **Risk tier:** `{result.risk_tier}` (scenario `{result.scenario}`, conservative={result.conservative})",
        f"- **Domains:** {', '.join(result.domains) or 'none'}",
        f"- **Changed paths:** {len(result.changed_paths)}",
        "",
        "### Flags",
    ]
    for key, enabled in flags.items():
        lines.append(f"- `{key}`: **{'on' if enabled else 'off'}**")
    if result.changed_readonly_audit_scripts:
        lines.extend(
            [
                "",
                "### Read-only audit scripts",
                "",
                ", ".join(f"`{p}`" for p in result.changed_readonly_audit_scripts),
            ]
        )
    if result.unknown_paths:
        lines.extend(["", "### Unknown paths (fail-safe FULL)", ""])
        for path in result.unknown_paths:
            lines.append(f"- `{path}`")
    lines.extend(["", "### Why skipped", ""])
    for reason in skip_reasons(result):
        lines.append(f"- {reason}")
    lines.append("")
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def write_github_output(outputs: dict[str, str]) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            if "\n" in value:
                delimiter = f"ghadelim_{key}"
                handle.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")
            else:
                handle.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--paths", nargs="*", help="explicit paths (skip git diff)")
    parser.add_argument("--force-full", action="store_true")
    parser.add_argument("--pr-labels", default="")
    parser.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--github-output", action="store_true")
    parser.add_argument("--step-summary", action="store_true")
    args = parser.parse_args(argv)

    paths = args.paths if args.paths is not None else git_changed_paths(args.base, args.head)
    result = classify(
        paths,
        force_full=args.force_full,
        pr_labels=parse_labels(args.pr_labels),
        event_name=args.event or None,
    )
    if args.github_output:
        write_github_output(result.to_github_outputs())
    if args.step_summary:
        write_step_summary(result)
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
