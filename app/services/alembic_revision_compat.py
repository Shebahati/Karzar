"""Alembic revision compatibility for sealed Wave / batch environment pins.

``environment_pins.alembic`` is a *minimum compatible lineage pin*:
runtime must equal the sealed revision or be a proper descendant of it
in the application's Alembic revision graph.

Exact string equality is insufficient after additive schema advancements
(e.g. PR3-B.1) that leave sealed Waves intact.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from alembic.script import ScriptDirectory

_REPO_ROOT = Path(__file__).resolve().parents[2]
_script_directory: ScriptDirectory | None = None


class SupportsAlembicRevisions(Protocol):
    """Minimal surface used by compatibility checks (real ScriptDirectory or test doubles)."""

    def get_revision(self, id_: str) -> Any: ...


def get_alembic_script_directory() -> ScriptDirectory:
    """Return the process-cached Alembic ScriptDirectory for this repo."""
    global _script_directory
    if _script_directory is None:
        _script_directory = ScriptDirectory(str(_REPO_ROOT / "alembic"))
    return _script_directory


def _parent_ids(revision: Any) -> tuple[str, ...]:
    down = getattr(revision, "down_revision", None)
    if down is None:
        return ()
    if isinstance(down, tuple | list):
        return tuple(str(p) for p in down if p is not None)
    return (str(down),)


def _resolve_revision(script: SupportsAlembicRevisions, revision_id: str) -> Any | None:
    try:
        rev = script.get_revision(revision_id)
    except Exception:
        return None
    return rev


def collect_ancestor_revision_ids(
    script: SupportsAlembicRevisions,
    revision_id: str,
) -> set[str] | None:
    """Return ``{revision_id} ∪ ancestors``, or ``None`` if the graph is unresolvable."""
    start = _resolve_revision(script, revision_id)
    if start is None:
        return None
    start_id = str(getattr(start, "revision", revision_id))
    seen: set[str] = set()
    stack: list[Any] = [start]
    while stack:
        current = stack.pop()
        current_id = str(getattr(current, "revision", ""))
        if not current_id or current_id in seen:
            continue
        seen.add(current_id)
        for parent_id in _parent_ids(current):
            parent = _resolve_revision(script, parent_id)
            if parent is None:
                return None
            stack.append(parent)
    if start_id not in seen:
        return None
    return seen


def is_runtime_revision_compatible(
    sealed_revision: str,
    runtime_revision: str,
    *,
    script_directory: SupportsAlembicRevisions | None = None,
) -> bool:
    """Return True iff runtime equals sealed or is a descendant of sealed.

    Fail-closed for blank, unknown, older, or divergent revisions.
    Does not mutate state and does not order revision ids lexicographically.
    """
    sealed = (sealed_revision or "").strip()
    runtime = (runtime_revision or "").strip()
    if not sealed or not runtime:
        return False

    script: SupportsAlembicRevisions = script_directory or get_alembic_script_directory()
    if _resolve_revision(script, sealed) is None:
        return False
    if _resolve_revision(script, runtime) is None:
        return False
    if sealed == runtime:
        return True

    ancestors = collect_ancestor_revision_ids(script, runtime)
    if ancestors is None:
        return False
    return sealed in ancestors
