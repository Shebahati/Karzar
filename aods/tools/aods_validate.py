#!/usr/bin/env python3
"""AODS validation orchestrator.

Runs the mechanical gates defined in aods/80-validation/VALIDATION-FRAMEWORK.md.
Standard library only, so the gates run on a clean checkout without installing anything
(PyYAML is absent from requirements*.txt; see aods/tools/aods_yaml.py).

    python3 aods/tools/aods_validate.py --gate all
    python3 aods/tools/aods_validate.py --gate links --gate registry
    python3 aods/tools/aods_validate.py --gate citation --pr-body /tmp/pr.md
    python3 aods/tools/aods_validate.py --gate allowlist --node IMPL-x-001 --base origin/main
    python3 aods/tools/aods_validate.py --gate all --json
    python3 aods/tools/aods_validate.py --gate all --write-baseline

Exit codes: 0 all selected gates passed · 1 at least one failed · 2 usage/internal error.

These gates are expected to FAIL on the repository as it stands today. That is the point:
they report the real state recorded in aods/10-repository-intelligence/CONFLICT-REGISTER.md.
Use --write-baseline to record known failures so CI can enforce "no new failures" while the
existing ones are worked off. A baselined failure stays visible in the baseline file; it is
not silenced.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aods_yaml  # noqa: E402  (path set above so the module resolves on a clean checkout)

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "aods/registry/document-registry.yaml"
TASK_GRAPH = REPO / "aods/registry/task-graph.yaml"
ROLE_REGISTRY = REPO / "aods/registry/role-registry.yaml"
PROMPT_DIR = REPO / "aods/70-prompts"
PROMPT_TEMPLATE = PROMPT_DIR / "PROMPT-TEMPLATE.md"
BASELINE = REPO / "aods/registry/validation-baseline.json"
TASKS_JSON = REPO / "project-management/exports/tasks.json"

SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".next", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "htmlcov", ".turbo", "dist", "build", "out",
}

PROMPT_ARCHETYPES = ("AUD", "SPEC", "IMPL", "TEST", "KNOW", "DOC", "GOV", "REL")
KNOWN_GATES = (
    "registry", "links", "pmo", "prompts", "graph", "naming", "citation",
    "allowlist", "openapi", "ingestion-boundary",
)
# Gates enforced by existing project tooling rather than by this script. Prompts and nodes
# legitimately name these, so they must be recognised — but this script cannot run them,
# and claiming otherwise would be failure criterion F-04.
EXTERNAL_GATES = (
    "lint", "types", "typecheck", "test", "coverage", "e2e", "build", "smoke",
    "workflow-lint", "migration-updown", "post-deploy",
)
# The generic token used in prose when a prompt talks about placeholders in the abstract
# (e.g. "if any {{PLACEHOLDER}} remains unfilled, HALT"). Not a real parameter.
META_PLACEHOLDERS = {"PLACEHOLDER"}
REQUIRED_PROMPT_FIELDS = (
    "id", "version", "archetype", "role", "capability_class", "reasoning_depth",
    "decision_ceiling", "parameters", "context_tiers", "forbidden_context", "gates", "produces",
)
REQUIRED_PROMPT_SECTIONS = (
    "AUTO MODE PROTOCOL", "PURPOSE", "ALLOWED SCOPE", "FORBIDDEN SCOPE", "FORBIDDEN CONTEXT",
    "INPUTS", "ARCHITECTURE RULES", "FILE MODIFICATION RULES", "TASK", "EXPECTED OUTPUTS",
    "VALIDATION CHECKLIST", "STOPPING CONDITIONS", "FAILURE HANDLING", "OUTPUT FORMAT",
)
MODEL_NAME_PATTERN = re.compile(
    r"\b(gpt-[0-9]|claude[- ](?:opus|sonnet|haiku)|opus[- ]?[0-9]|sonnet[- ]?[0-9]|"
    r"gemini[- ][0-9]|o[0-9][- ]mini|llama[- ][0-9]|deepseek|mistral|grok[- ][0-9])",
    re.IGNORECASE,
)
SECRET_PATTERN = re.compile(r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})")
# "backup" is deliberately absent: scripts/backup_db.sh names its purpose, which is legitimate.
# The reserved words are the ones that describe a file's *relationship to another file*, since
# those are the ones that become lies (NAMING-CONVENTIONS.md §2.1).
RESERVED_NAME = re.compile(
    r"(^|[-_.])(final|latest|new|old|copy\d*|temp|tmp|wip|bak|draft\d+|untitled)([-_.]|$)",
    re.IGNORECASE,
)
NAMING_ALLOW = {"openapi/v1.json"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


# --------------------------------------------------------------------------- results


@dataclass
class Finding:
    gate: str
    path: str
    message: str
    key: str = ""

    def __post_init__(self) -> None:
        if not self.key:
            self.key = f"{self.gate}:{self.path}:{self.message}"

    def as_dict(self) -> dict[str, str]:
        return {"gate": self.gate, "path": self.path, "message": self.message, "key": self.key}


@dataclass
class GateResult:
    name: str
    findings: list[Finding] = field(default_factory=list)
    skipped: str = ""
    checked: int = 0

    @property
    def passed(self) -> bool:
        return not self.findings

    def fail(self, path: str, message: str) -> None:
        self.findings.append(Finding(self.name, path, message))


# --------------------------------------------------------------------------- helpers


def run(
    cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd or REPO), capture_output=True, text=True, timeout=300,
            check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def tracked_files(pattern: str = "") -> list[str]:
    code, out, _ = run(["git", "ls-files"] + ([pattern] if pattern else []))
    if code != 0:
        return []
    return [line for line in out.splitlines() if line and not _skipped(line)]


def _skipped(rel: str) -> bool:
    return any(part in SKIP_DIRS for part in Path(rel).parts)


def load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        raise FileNotFoundError(f"registry missing: {REGISTRY}")
    data = aods_yaml.parse(REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "documents" not in data:
        raise ValueError("registry has no 'documents' key")
    return data


def forbidden_context_paths(registry: dict[str, Any]) -> set[str]:
    return {
        str(doc["path"])
        for doc in registry["documents"]
        if isinstance(doc, dict) and doc.get("forbidden_context") and doc.get("path")
    }


def matches_any(rel: str, globs: Iterable[str]) -> bool:
    for pattern in globs:
        if fnmatch.fnmatch(rel, pattern):
            return True
        # Treat "dir/**" as also matching "dir/file" (fnmatch needs the extra form).
        if pattern.endswith("/**") and fnmatch.fnmatch(rel, pattern[:-3] + "/*"):
            return True
        if pattern.endswith("/") and rel.startswith(pattern):
            return True
    return False


def resolves_on_base(rel: str, base: str) -> bool:
    """Whether a path exists in the merge base — the CR-001 check."""
    code, _, _ = run(["git", "cat-file", "-e", f"{base}:{rel}"])
    return code == 0


# --------------------------------------------------------------------------- gates


def gate_registry(_: argparse.Namespace) -> GateResult:
    """Every markdown file is classified, and every classified path exists."""
    result = GateResult("registry")
    registry = load_registry()
    allow = [str(g) for g in (registry.get("unclassified_allow") or [])]
    documents = [d for d in registry["documents"] if isinstance(d, dict)]

    registered: dict[str, dict[str, Any]] = {}
    for doc in documents:
        path = str(doc.get("path", ""))
        if not path:
            result.fail(str(doc.get("id", "?")), "registry row has no 'path'")
            continue
        if path in registered:
            result.fail(path, f"duplicate registry row (ids {registered[path].get('id')} and {doc.get('id')})")
        registered[path] = doc
        if not doc.get("id"):
            result.fail(path, "registry row has no 'id'")
        if not doc.get("class"):
            result.fail(path, "registry row has no 'class'")

    # `on_main` is a claim about the base branch, not about the working tree. An AODS document
    # can legitimately exist locally while `on_main: false` — that is every document on this
    # very branch. Verify it against git so the field means what it says.
    for path, doc in registered.items():
        on_main = doc.get("on_main")
        in_worktree = (REPO / path).exists()
        actually_on_main = resolves_on_base(path, "origin/main")
        if not in_worktree and on_main is not False:
            result.fail(path, f"registered document is missing from the working tree (id {doc.get('id')})")
        if on_main is True and not actually_on_main:
            result.fail(path, f"row claims on_main: true but the path is absent from origin/main (id {doc.get('id')})")
        if on_main is False and actually_on_main:
            result.fail(
                path,
                f"row claims on_main: false but the path IS on origin/main (id {doc.get('id')}) — stale row",
            )

    for rel in tracked_files("*.md"):
        result.checked += 1
        if rel in registered or matches_any(rel, allow):
            continue
        result.fail(rel, "markdown file is neither registered nor covered by unclassified_allow")
    return result


def gate_links(_: argparse.Namespace) -> GateResult:
    """Relative markdown links resolve to something that exists.

    A link whose target is a registered document with `on_main: false` gets a distinct
    message: it is not a typo but the CR-001 condition (binding documents cited from a
    branch that has not merged). Same failure, far more useful diagnosis.
    """
    result = GateResult("links")
    unmerged: dict[str, str] = {}
    try:
        for doc in load_registry()["documents"]:
            if isinstance(doc, dict) and doc.get("on_main") is False and doc.get("path"):
                unmerged[str(doc["path"])] = str(doc.get("branch") or "unmerged branch")
    except (OSError, ValueError, aods_yaml.YamlSubsetError):
        pass

    for rel in tracked_files("*.md"):
        source = REPO / rel
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            result.fail(rel, f"unreadable: {exc}")
            continue
        result.checked += 1
        for match in MD_LINK.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "tel:", "#", "<")):
                continue
            if target.startswith("{{") or "${" in target:
                continue
            clean = target.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            resolved = (source.parent / clean).resolve()
            try:
                resolved.relative_to(REPO)
            except ValueError:
                result.fail(rel, f"link escapes the repository: {target}")
                continue
            if not resolved.exists():
                line = text[: match.start()].count("\n") + 1
                target_rel = str(resolved.relative_to(REPO))
                if target_rel in unmerged:
                    result.fail(
                        f"{rel}:{line}",
                        f"link target is registered but not on main: {target} "
                        f"(lives on {unmerged[target_rel]} — CR-001)",
                    )
                else:
                    result.fail(f"{rel}:{line}", f"broken link: {target} (CR-023)")
    return result


def gate_pmo(_: argparse.Namespace) -> GateResult:
    """tasks.json is valid, IDs are unique, and status agrees with the markdown mirrors."""
    result = GateResult("pmo")
    if not TASKS_JSON.exists():
        result.skipped = f"{TASKS_JSON.relative_to(REPO)} not found"
        return result
    try:
        data = json.loads(TASKS_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.fail(str(TASKS_JSON.relative_to(REPO)), f"invalid JSON: {exc}")
        return result

    tasks = data.get("tasks") if isinstance(data, dict) else data
    if not isinstance(tasks, list):
        result.fail(str(TASKS_JSON.relative_to(REPO)), "no 'tasks' list")
        return result

    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        tid = str(task.get("id", ""))
        result.checked += 1
        if not tid:
            result.fail("tasks.json", "task entry has no id")
            continue
        if tid in seen:
            result.fail("tasks.json", f"duplicate task id {tid}")
        seen.add(tid)
        by_id[tid] = task
        status = str(task.get("status", ""))
        progress = task.get("progress")
        if status == "done" and progress not in (100, "100"):
            result.fail("tasks.json", f"{tid}: status=done but progress={progress!r}")
        if progress in (100, "100") and status != "done":
            result.fail("tasks.json", f"{tid}: progress=100 but status={status!r}")

    # Orphan IDs: a task-shaped ID cited in PMO markdown that has no entry.
    pmo_md = [r for r in tracked_files("project-management/*.md")]
    pmo_md += [r for r in tracked_files("project-management/**/*.md")]
    id_pattern = re.compile(r"\b(PMO|SEO|CAT|UX|PERF|SEC|BE|FE|KB|REL|TD|OPS|AODS)-\d{3}\b")
    cited: dict[str, str] = {}
    for rel in sorted(set(pmo_md)):
        try:
            text = (REPO / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for match in id_pattern.finditer(text):
            cited.setdefault(match.group(0), rel)
    for tid, where in sorted(cited.items()):
        if tid not in by_id:
            result.fail(where, f"cites task {tid}, which has no entry in tasks.json")

    # Divergent duplicate progress ledgers (CR-007).
    for rel in tracked_files("project-management/*_PROGRESS.md"):
        twin = Path("project-management/progress") / Path(rel).name
        if (REPO / twin).exists():
            a = (REPO / rel).read_bytes()
            b = (REPO / twin).read_bytes()
            if a != b:
                result.fail(rel, f"diverges from duplicate at {twin} (CR-007: no canonical path decided)")
    return result


def gate_prompts(_: argparse.Namespace) -> GateResult:
    """Prompt files satisfy the lint rules in PROMPT-LIBRARY-ARCHITECTURE.md §10."""
    result = GateResult("prompts")
    registry_forbidden: set[str] = set()
    try:
        registry_forbidden = forbidden_context_paths(load_registry())
    except (OSError, ValueError, aods_yaml.YamlSubsetError) as exc:
        result.fail("aods/registry/document-registry.yaml", f"cannot load registry: {exc}")

    prompts = sorted(PROMPT_DIR.glob("*/*.prompt.md"))
    if not prompts:
        result.skipped = "no prompt files found"
        return result

    for prompt in prompts:
        rel = str(prompt.relative_to(REPO))
        result.checked += 1
        text = prompt.read_text(encoding="utf-8")
        try:
            front, body = aods_yaml.parse_front_matter(text)
        except aods_yaml.YamlSubsetError as exc:
            result.fail(rel, f"P-01 front matter unparseable: {exc}")
            continue
        if not front:
            result.fail(rel, "P-01 front matter missing")
            continue

        for key in REQUIRED_PROMPT_FIELDS:
            if key not in front:
                result.fail(rel, f"P-02 front matter missing '{key}'")

        headings = re.findall(r"^##\s+\d*\.?\s*(.+)$", body, re.MULTILINE)
        normalised = [h.split("—")[0].strip().upper() for h in headings]
        position = 0
        for section in REQUIRED_PROMPT_SECTIONS:
            found = next((i for i, h in enumerate(normalised) if h.startswith(section)), -1)
            if found < 0:
                result.fail(rel, f"P-03 missing section '{section}'")
            elif found < position:
                result.fail(rel, f"P-03 section '{section}' is out of order")
            else:
                position = found

        declared = {str(p) for p in (front.get("parameters") or [])}
        used = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", body)) - META_PLACEHOLDERS
        for name in sorted(used - declared):
            result.fail(rel, f"P-04 placeholder {{{{{name}}}}} is not declared in parameters")
        for name in sorted(declared - used):
            result.fail(rel, f"P-05 parameter '{name}' is declared but never used")

        tiers = front.get("context_tiers") or {}
        tier_paths: list[str] = []
        if isinstance(tiers, dict):
            for entries in tiers.values():
                if isinstance(entries, list):
                    tier_paths += [str(e) for e in entries]
        for path in tier_paths:
            if path in registry_forbidden:
                result.fail(rel, f"P-06 context_tiers includes forbidden document {path}")

        prompt_forbidden = {str(p) for p in (front.get("forbidden_context") or [])}
        for path in sorted(registry_forbidden - prompt_forbidden):
            result.fail(rel, f"P-07 forbidden_context omits registry-forbidden document {path}")

        for match in MODEL_NAME_PATTERN.finditer(body):
            result.fail(rel, f"P-08 model name in prompt body: {match.group(0)!r}")
            break

        for name in (front.get("gates") or []):
            if str(name) not in KNOWN_GATES + EXTERNAL_GATES:
                result.fail(rel, f"P-09 unknown gate '{name}'")

        archetype = str(front.get("archetype", ""))
        directory = prompt.parent.name
        expected = {
            "audit": "AUD", "spec": "SPEC", "impl": "IMPL", "test": "TEST",
            "know": "KNOW", "doc": "DOC", "gov": "GOV", "rel": "REL",
        }.get(directory)
        if expected and archetype != expected:
            result.fail(rel, f"P-10 archetype '{archetype}' does not match directory '{directory}'")

        checklist = re.search(r"^##\s+\d*\.?\s*VALIDATION CHECKLIST(.+?)^##\s", body, re.S | re.M)
        if checklist and "`" not in checklist.group(1):
            result.fail(rel, "P-11 VALIDATION CHECKLIST contains no runnable command")

        lines = len(text.splitlines())
        if lines > 400:
            result.fail(rel, f"P-12 prompt is {lines} lines (limit 400)")

        version = str(front.get("version", ""))
        if not SEMVER.match(version):
            result.fail(rel, f"P-13 version {version!r} is not SemVer")

        if SECRET_PATTERN.search(text):
            result.fail(rel, "P-14 possible secret literal in prompt")

        if PROMPT_TEMPLATE.exists():
            canonical = _canonical_preamble()
            if canonical and canonical not in body:
                result.fail(rel, "P-15 AUTO MODE PROTOCOL text differs from PROMPT-TEMPLATE.md")
    return result


def _canonical_preamble() -> str:
    """The 10 hard prohibitions, extracted from the template, used as the drift reference."""
    text = PROMPT_TEMPLATE.read_text(encoding="utf-8")
    start = text.find("HARD PROHIBITIONS")
    end = text.find("REQUIRED PHASE ORDER", start)
    return text[start:end].strip() if start >= 0 and end > start else ""


def gate_graph(_: argparse.Namespace) -> GateResult:
    """The task graph is a DAG with resolvable references."""
    result = GateResult("graph")
    if not TASK_GRAPH.exists():
        result.skipped = "task-graph.yaml not found"
        return result
    try:
        data = aods_yaml.parse(TASK_GRAPH.read_text(encoding="utf-8"))
    except aods_yaml.YamlSubsetError as exc:
        result.fail("aods/registry/task-graph.yaml", f"unparseable: {exc}")
        return result

    nodes = [n for n in (data.get("nodes") or []) if isinstance(n, dict)]
    if not nodes:
        result.skipped = "task-graph.yaml declares no nodes"
        return result

    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        nid = str(node.get("id", ""))
        result.checked += 1
        if not nid:
            result.fail("task-graph.yaml", "node has no id")
            continue
        if nid in by_id:
            result.fail("task-graph.yaml", f"duplicate node id {nid}")
        by_id[nid] = node
        # Work nodes are <TYPE>-<slug>-<nnn>; human checkpoints appear in the graph as
        # HC-<nnn>-<slug> nodes, because a checkpoint is a real dependency, not an annotation.
        work = re.match(rf"^({'|'.join(PROMPT_ARCHETYPES)})-[a-z0-9]+(-[a-z0-9]+)*-\d{{3}}$", nid)
        checkpoint = re.match(r"^HC-\d{2,3}(-[a-z0-9]+)+$", nid)
        if not (work or checkpoint):
            result.fail("task-graph.yaml", f"node id {nid} does not match the naming pattern")

    roles: set[str] = set()
    if ROLE_REGISTRY.exists():
        try:
            role_data = aods_yaml.parse(ROLE_REGISTRY.read_text(encoding="utf-8"))
            roles = {
                str(r.get("id"))
                for r in (role_data.get("roles") or [])
                if isinstance(r, dict) and r.get("id")
            }
        except aods_yaml.YamlSubsetError as exc:
            result.fail("aods/registry/role-registry.yaml", f"unparseable: {exc}")

    for nid, node in by_id.items():
        for dep in node.get("depends_on") or []:
            if str(dep) not in by_id:
                result.fail("task-graph.yaml", f"{nid} depends on unknown node {dep}")
        role = node.get("role")
        if roles and role and str(role) not in roles:
            result.fail("task-graph.yaml", f"{nid} names unknown role {role}")
        for name in node.get("gates") or []:
            if str(name) not in KNOWN_GATES + EXTERNAL_GATES:
                result.fail("task-graph.yaml", f"{nid} names unknown gate '{name}'")

    # Cycle detection over depends_on.
    state: dict[str, int] = {}

    def visit(nid: str, trail: list[str]) -> None:
        if state.get(nid) == 2:
            return
        if state.get(nid) == 1:
            cycle = " -> ".join(trail[trail.index(nid):] + [nid])
            result.fail("task-graph.yaml", f"dependency cycle: {cycle}")
            return
        state[nid] = 1
        for dep in by_id.get(nid, {}).get("depends_on") or []:
            if str(dep) in by_id:
                visit(str(dep), trail + [nid])
        state[nid] = 2

    for nid in by_id:
        visit(nid, [])
    return result


def gate_naming(_: argparse.Namespace) -> GateResult:
    """No reserved words in tracked filenames (NAMING-CONVENTIONS.md §2.1)."""
    result = GateResult("naming")
    for rel in tracked_files():
        if rel in NAMING_ALLOW or _skipped(rel):
            continue
        if rel.startswith("alembic/versions/") or "/src/app/" in rel:
            continue
        result.checked += 1
        stem = Path(rel).stem
        if RESERVED_NAME.search(stem):
            result.fail(rel, "filename contains a reserved word (NAMING-CONVENTIONS.md §2.1)")
    return result


def gate_citation(args: argparse.Namespace) -> GateResult:
    """Every path cited in a PR body resolves ON THE MERGE BASE (the CR-001 check)."""
    result = GateResult("citation")
    if not args.pr_body:
        result.skipped = "no --pr-body supplied"
        return result
    body_path = Path(args.pr_body)
    if not body_path.exists():
        result.fail(str(body_path), "PR body file not found")
        return result
    body = body_path.read_text(encoding="utf-8")
    base = args.base

    if not re.search(r"^\s*Node:\s*\S+", body, re.M):
        result.fail(str(body_path), "PR body has no 'Node:' line (required for --gate allowlist to work)")
    if not re.search(r"^\s*Authority:", body, re.M):
        result.fail(str(body_path), "PR body has no 'Authority:' line")

    cited = set(re.findall(r"(?:^|[\s`(])((?:docs|app|aods|project-management|alembic|scripts)/[\w./\-]+\.\w+)", body))
    if not cited:
        result.fail(str(body_path), "PR body cites no repository paths")
    for rel in sorted(cited):
        result.checked += 1
        if not resolves_on_base(rel, base):
            result.fail(
                str(body_path),
                f"cited path does not resolve on merge base '{base}': {rel} (CR-001 failure mode)",
            )
    return result


def gate_allowlist(args: argparse.Namespace) -> GateResult:
    """The working diff stays inside the node's declared allowed_paths."""
    result = GateResult("allowlist")
    if not args.node:
        result.skipped = "no --node supplied"
        return result
    if not TASK_GRAPH.exists():
        result.skipped = "task-graph.yaml not found"
        return result
    data = aods_yaml.parse(TASK_GRAPH.read_text(encoding="utf-8"))
    node = next(
        (n for n in (data.get("nodes") or []) if isinstance(n, dict) and str(n.get("id")) == args.node),
        None,
    )
    if node is None:
        result.fail(args.node, "node not found in task-graph.yaml")
        return result
    allowed = [str(p) for p in (node.get("allowed_paths") or [])]
    if not allowed:
        result.fail(args.node, "node declares no allowed_paths, so scope cannot be verified")
        return result

    code, out, err = run(["git", "diff", "--name-only", f"{args.base}...HEAD"])
    if code != 0:
        code, out, err = run(["git", "diff", "--name-only", args.base])
    changed = [line for line in out.splitlines() if line.strip()]
    code2, out2, _ = run(["git", "status", "--porcelain"])
    for line in out2.splitlines():
        if len(line) > 3:
            changed.append(line[3:].strip())
    if code != 0 and code2 != 0:
        result.fail(args.node, f"cannot read the diff: {err.strip()}")
        return result

    always_allowed = [f"aods/reports/**", f"aods/reports/tasks/{args.node}.md"]
    for rel in sorted(set(changed)):
        result.checked += 1
        if matches_any(rel, allowed) or matches_any(rel, always_allowed):
            continue
        result.fail(rel, f"changed file is outside allowed_paths for {args.node}")
    return result


OPENAPI_PLACEHOLDER_ENV = {
    "POSTGRES_USER": "aods_validate",
    "POSTGRES_PASSWORD": "aods_validate_not_a_real_password",
    "POSTGRES_SERVER": "127.0.0.1",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "aods_validate",
    "SECRET_KEY": "aods-validate-placeholder-secret-key-32-chars-min",
    "ADMIN_STEP_UP_PIN": "000000",
    "DEBUG": "True",
}


def gate_openapi(_: argparse.Namespace) -> GateResult:
    """The committed OpenAPI snapshot matches the running app (CR-012)."""
    result = GateResult("openapi")
    snapshot = REPO / "openapi/v1.json"
    if not snapshot.exists():
        result.skipped = "openapi/v1.json not present"
        return result
    # Schema generation only needs Settings to validate; it opens no socket and touches no database.
    # Placeholders are supplied so the gate is runnable on a bare checkout without a .env, and are
    # deliberately non-functional values that could not reach a real service if something tried.
    env = dict(os.environ)
    env.setdefault("PYTHONPATH", str(REPO))
    for key, value in OPENAPI_PLACEHOLDER_ENV.items():
        env.setdefault(key, value)

    code, out, err = run(
        [
            sys.executable, "-c",
            "import json,sys;from app.main import app;"
            "sys.stdout.write(json.dumps(app.openapi(), ensure_ascii=False, sort_keys=True))",
        ],
        env=env,
    )
    if code != 0:
        tail = (err or out or "").strip().splitlines()[-3:]
        detail = " | ".join(line.strip() for line in tail) or "no output"
        if "ModuleNotFoundError" in (err or ""):
            result.skipped = (
                "cannot import app.main — dependencies not installed; "
                f"run with requirements.txt installed ({detail})"
            )
        else:
            # Anything other than a missing dependency is a real problem: the app cannot
            # produce its own contract, so the snapshot is unverifiable. Never a silent pass.
            result.fail("openapi/v1.json", f"could not generate the live schema: {detail} (CR-012)")
        return result
    try:
        live = json.loads(out)
        committed = json.loads(snapshot.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.fail("openapi/v1.json", f"invalid JSON: {exc}")
        return result
    result.checked = 1
    live_paths = set(live.get("paths", {}))
    committed_paths = set(committed.get("paths", {}))
    for path in sorted(live_paths - committed_paths):
        result.fail("openapi/v1.json", f"path present in the app but missing from the snapshot: {path} (CR-012)")
    for path in sorted(committed_paths - live_paths):
        result.fail("openapi/v1.json", f"path in the snapshot no longer exists in the app: {path} (CR-012)")
    if live_paths == committed_paths and json.dumps(live, sort_keys=True) != json.dumps(committed, sort_keys=True):
        result.fail("openapi/v1.json", "paths match but schemas differ — regenerate the snapshot (CR-012)")
    return result


PROD_HOST = "karzartools.com"

# A production default can be spelled three ways in this repository, and an earlier version of this
# gate only recognised the first — it reported 15 offenders where the audit had found 18. All three
# forms are equally effective at pointing a routine script at the live site, so all three are checked.
INGESTION_PATTERNS = (
    # 1. os.getenv("ANY_BASE_VAR", "https://api.karzartools.com/...")
    (
        re.compile(
            r"""(?:getenv|environ\.get)\(\s*["'](?P<var>[A-Z0-9_]+)["']\s*,\s*["'](?P<default>[^"']+)["']"""
        ),
        "defaults {var} to production: {default}",
    ),
    # 2. argparse: default="https://api.karzartools.com/..."
    (
        re.compile(r"""\bdefault\s*=\s*["'](?P<default>https?://[^"']+)["']"""),
        "argparse default targets production: {default}",
    ),
    # 3. A bare assignment to a production URL with no environment override at all.
    (
        re.compile(r"""^\s*(?P<var>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*["'](?P<default>https?://[^"']+)["']""", re.M),
        "hardcodes production base in {var}: {default}",
    ),
)


def gate_ingestion_boundary(_: argparse.Namespace) -> GateResult:
    """No script defaults to a production API or asset base (ADR-012 / CR-004)."""
    result = GateResult("ingestion-boundary")
    for rel in tracked_files("scripts/*.py"):
        text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        result.checked += 1
        seen: set[int] = set()
        for pattern, template in INGESTION_PATTERNS:
            for match in pattern.finditer(text):
                default = match.group("default")
                if PROD_HOST not in default:
                    continue
                line = text[: match.start()].count("\n") + 1
                if line in seen:  # one line, one finding, whichever pattern matched first
                    continue
                seen.add(line)
                groups = match.groupdict()
                detail = template.format(var=groups.get("var") or "value", default=default)
                result.fail(f"{rel}:{line}", f"{detail} (ADR-012, CR-004)")
    return result


GATES: dict[str, Callable[[argparse.Namespace], GateResult]] = {
    "registry": gate_registry,
    "links": gate_links,
    "pmo": gate_pmo,
    "prompts": gate_prompts,
    "graph": gate_graph,
    "naming": gate_naming,
    "citation": gate_citation,
    "allowlist": gate_allowlist,
    "openapi": gate_openapi,
    "ingestion-boundary": gate_ingestion_boundary,
}

# Gates that need a per-invocation argument, so "--gate all" skips them rather than
# reporting a misleading pass.
CONTEXTUAL = {"citation", "allowlist"}


# --------------------------------------------------------------------------- baseline


def load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    try:
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {str(entry["key"]) for entry in data.get("known_failures", []) if "key" in entry}


# A baseline entry with no owner is a suppression, so the writer refuses to produce one:
# it derives the conflict ID from the finding message and the owner from the gate.
# ARTIFACT-ARCHITECTURE.md requires date + owner + conflict ID on every baselined violation.
BASELINE_OWNER_BY_GATE = {
    "links": "R-DOC-ARCH",
    "registry": "R-DOC-ARCH",
    "pmo": "R-PMO",
    "prompts": "R-PROMPT-ENG",
    "graph": "R-PROJ-ARCH",
    "naming": "R-DOC-ARCH",
    "openapi": "R-BE-ARCH",
    "ingestion-boundary": "R-DATA-ENG",
    "citation": "R-AI-REVIEWER",
    "allowlist": "R-AI-REVIEWER",
}

CONFLICT_ID_RE = re.compile(r"\bCR-\d{3}\b")


def write_baseline(results: list[GateResult]) -> int:
    entries = []
    unattributed = []
    for result in results:
        for finding in result.findings:
            entry = finding.as_dict()
            match = CONFLICT_ID_RE.search(entry.get("message", ""))
            entry["conflict_id"] = match.group(0) if match else "UNASSIGNED"
            entry["owner_role"] = BASELINE_OWNER_BY_GATE.get(result.name, "R-PROJ-ARCH")
            entry["recorded_at"] = os.environ.get("AODS_BASELINE_DATE", "")
            if entry["conflict_id"] == "UNASSIGNED":
                unattributed.append(entry["path"])
            entries.append(entry)

    payload = {
        "_comment": (
            "Known validation failures, recorded so CI can enforce 'no new failures' while the "
            "existing ones are worked off. Entries are visible debt, not suppressions. Removing an "
            "entry that still fails will fail CI. Each should map to a CR-nnn in "
            "aods/10-repository-intelligence/CONFLICT-REGISTER.md; conflict_id UNASSIGNED means "
            "the debt is real but not yet registered, which is itself a finding."
        ),
        "recorded_at": os.environ.get("AODS_BASELINE_DATE", ""),
        "count": len(entries),
        "unassigned_conflict_ids": len(unattributed),
        "known_failures": entries,
    }
    BASELINE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if unattributed:
        print(f"WARNING: {len(unattributed)} entr(ies) have no CR-nnn; register them or fix them:")
        for path in unattributed:
            print(f"  - {path}")
    return len(entries)


# --------------------------------------------------------------------------- reporting


def report(results: list[GateResult], baseline: set[str], use_baseline: bool) -> tuple[int, int]:
    new_failures = 0
    baselined = 0
    for result in results:
        if result.skipped:
            print(f"  SKIP  {result.name:<20} {result.skipped}")
            continue
        fresh = [f for f in result.findings if not (use_baseline and f.key in baseline)]
        known = len(result.findings) - len(fresh)
        baselined += known
        new_failures += len(fresh)
        status = "PASS" if not fresh else "FAIL"
        detail = f"{result.checked} checked"
        if known:
            detail += f", {known} baselined"
        print(f"  {status:<5} {result.name:<20} {detail}")
        for finding in fresh:
            print(f"          - {finding.path}: {finding.message}")
    return new_failures, baselined


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aods_validate.py",
        description="Run AODS validation gates (see aods/80-validation/VALIDATION-FRAMEWORK.md).",
    )
    parser.add_argument(
        "--gate", action="append", default=[], metavar="NAME",
        help=f"gate to run; repeatable. 'all' runs every non-contextual gate. Known: {', '.join(KNOWN_GATES)}",
    )
    parser.add_argument("--pr-body", help="file containing a PR body (for --gate citation)")
    parser.add_argument("--node", help="node id (for --gate allowlist)")
    parser.add_argument("--base", default="origin/main", help="merge base ref (default: origin/main)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    parser.add_argument("--write-baseline", action="store_true", help="record current failures as known")
    parser.add_argument("--no-baseline", action="store_true", help="ignore the baseline; report every failure")
    parser.add_argument(
        "--all", action="store_true",
        help="every non-contextual gate with the baseline ignored: the honest picture, including known debt",
    )
    parser.add_argument("--list-gates", action="store_true", help="list gate names and exit")
    args = parser.parse_args(argv)

    if args.all:
        args.no_baseline = True

    if args.list_gates:
        for name in KNOWN_GATES:
            marker = " (needs an argument)" if name in CONTEXTUAL else ""
            print(f"{name}{marker}")
        return 0

    selected = args.gate or ["all"]
    if "all" in selected:
        names = [g for g in KNOWN_GATES if g not in CONTEXTUAL]
        if args.pr_body:
            names.append("citation")
        if args.node:
            names.append("allowlist")
    else:
        names = []
        for name in selected:
            if name not in GATES:
                parser.error(f"unknown gate {name!r}; try --list-gates")
            names.append(name)

    results: list[GateResult] = []
    for name in names:
        try:
            results.append(GATES[name](args))
        except Exception as exc:  # a crashing gate must be loud, never a silent pass
            broken = GateResult(name)
            broken.fail(name, f"gate crashed: {type(exc).__name__}: {exc}")
            results.append(broken)

    if args.write_baseline:
        count = write_baseline(results)
        print(f"Wrote {count} known failures to {BASELINE.relative_to(REPO)}")
        return 0

    baseline = set() if args.no_baseline else load_baseline()
    if args.json:
        payload = {
            "gates": [
                {
                    "name": r.name,
                    "skipped": r.skipped,
                    "checked": r.checked,
                    "findings": [f.as_dict() for f in r.findings],
                    "new_findings": [f.as_dict() for f in r.findings if f.key not in baseline],
                }
                for r in results
            ],
        }
        payload["new_failure_count"] = sum(len(g["new_findings"]) for g in payload["gates"])
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 1 if payload["new_failure_count"] else 0

    print(f"AODS validation — {len(results)} gate(s), base={args.base}")
    new_failures, baselined = report(results, baseline, not args.no_baseline)
    print()
    if new_failures:
        print(f"RESULT: FAIL — {new_failures} new finding(s), {baselined} baselined")
        return 1
    print(f"RESULT: PASS — 0 new findings, {baselined} baselined")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
