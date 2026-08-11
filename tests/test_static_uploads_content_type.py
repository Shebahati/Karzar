"""Regression: StaticFiles must serve product images with correct Content-Type (#229)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

import pytest
from app.core.static_mime import ensure_image_static_mime_types
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

# Minimal payloads (magic only); StaticFiles does not decode images.
_TINY = {
    ".webp": b"RIFF\x08\x00\x00\x00WEBP",
    ".jpg": b"\xff\xd8\xff\xd9",
    ".jpeg": b"\xff\xd8\xff\xd9",
    ".png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00",
}

_EXPECTED = {
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def test_ensure_image_static_mime_types_registers_webp():
    mimetypes.types_map.pop(".webp", None)
    if hasattr(mimetypes, "common_types"):
        mimetypes.common_types.pop(".webp", None)  # type: ignore[attr-defined]
    ensure_image_static_mime_types()
    assert mimetypes.guess_type("x.webp")[0] == "image/webp"
    assert mimetypes.guess_type("x.jpg")[0] == "image/jpeg"
    assert mimetypes.guess_type("x.jpeg")[0] == "image/jpeg"
    assert mimetypes.guess_type("x.png")[0] == "image/png"


@pytest.mark.parametrize("ext,expected", list(_EXPECTED.items()))
def test_static_uploads_content_type(tmp_path: Path, ext: str, expected: str):
    # Drop .webp from the map first (matches lathe_api / Python 3.12 slim).
    mimetypes.types_map.pop(".webp", None)
    if hasattr(mimetypes, "common_types"):
        mimetypes.common_types.pop(".webp", None)  # type: ignore[attr-defined]
    ensure_image_static_mime_types()
    for e, blob in _TINY.items():
        (tmp_path / f"sample{e}").write_bytes(blob)

    mini = FastAPI()
    mini.mount("/static/uploads", StaticFiles(directory=tmp_path), name="uploads")
    client = TestClient(mini)

    resp = client.get(f"/static/uploads/sample{ext}")
    assert resp.status_code == 200, resp.text
    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    assert ctype == expected
    assert ctype != "application/octet-stream"
