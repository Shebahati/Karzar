"""AODS registry gate: no on_main lifecycle; worktree existence + classification."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "aods" / "tools"
sys.path.insert(0, str(TOOLS))

import aods_validate as av  # noqa: E402


def test_document_registry_has_no_on_main_field() -> None:
    text = (ROOT / "aods/registry/document-registry.yaml").read_text(encoding="utf-8")
    assert "on_main:" not in text


def test_validator_has_no_on_main_sync_failures() -> None:
    text = (ROOT / "aods/tools/aods_validate.py").read_text(encoding="utf-8")
    assert "row claims on_main:" not in text
    assert "stale row" not in text
    assert "doc.get(\"on_main\")" not in text


def test_registered_markdown_passes_without_on_main() -> None:
    result = av.gate_registry(argparse.Namespace())
    assert result.passed, result.findings
    assert result.checked > 0


def test_missing_registered_document_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    real_load = av.load_registry

    def fake_load() -> dict:
        data = real_load()
        docs = list(data["documents"])
        docs.append(
            {
                "id": "TEST-MISSING-DOC",
                "path": "audit/insize-phase3/DOES_NOT_EXIST_PROMPT87.md",
                "class": "EVIDENCE",
                "rank": 6,
                "status": "current",
                "owner_role": "R-DOC-ARCH",
            }
        )
        return {**data, "documents": docs}

    monkeypatch.setattr(av, "load_registry", fake_load)
    result = av.gate_registry(argparse.Namespace())
    assert not result.passed
    assert any("missing from the working tree" in f.message for f in result.findings)


def test_unclassified_markdown_still_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tracked-looking md path that is neither registered nor allowlisted fails."""
    orphan = "audit/insize-phase3/_prompt87_orphan_unclassified.md"
    orphan_path = ROOT / orphan
    orphan_path.write_text("# orphan\n", encoding="utf-8")
    try:
        real_tracked = av.tracked_files

        def fake_tracked(pattern: str = "*") -> list[str]:
            files = list(real_tracked(pattern))
            if orphan not in files:
                files.append(orphan)
            return files

        monkeypatch.setattr(av, "tracked_files", fake_tracked)
        result = av.gate_registry(argparse.Namespace())
        assert not result.passed
        assert any(
            f.path == orphan and "neither registered nor covered by unclassified_allow" in f.message
            for f in result.findings
        )
    finally:
        orphan_path.unlink(missing_ok=True)


def test_ingestion_boundary_gate_unchanged() -> None:
    proc = subprocess.run(
        [sys.executable, "aods/tools/aods_validate.py", "--gate", "ingestion-boundary"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "PASS" in proc.stdout and "ingestion-boundary" in proc.stdout


def test_openapi_gate_still_invocable() -> None:
    """OpenAPI gate must still run (PASS or SKIP for missing deps — never removed)."""
    proc = subprocess.run(
        [sys.executable, "aods/tools/aods_validate.py", "--gate", "openapi"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "LOG_TO_FILE": "false"},
    )
    assert "openapi" in proc.stdout
    assert "PASS" in proc.stdout or "SKIP" in proc.stdout
    assert "removed" not in proc.stdout.lower()
