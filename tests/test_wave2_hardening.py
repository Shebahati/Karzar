"""Wave2 hardening unit tests (CSRF helpers, SSRF resolve, raster upload)."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace

import pytest
from app.core import security_middleware as sm
from app.utils.image_validation import validate_product_image_url
from starlette.datastructures import UploadFile


class TestOriginHelpers:
    def test_origin_allowed_with_list(self, monkeypatch):
        monkeypatch.setattr(
            sm,
            "settings",
            SimpleNamespace(cors_origins_list=["https://www.karzartools.com"]),
        )
        assert sm._origin_allowed("https://www.karzartools.com") is True
        assert sm._origin_allowed("https://evil.example") is False

    def test_request_origin_from_referer(self):
        class _Req:
            headers = {"referer": "https://shop.example.com/cart"}

        assert sm._request_origin(_Req()) == "https://shop.example.com"  # type: ignore[arg-type]


class TestRasterUpload:
    def test_save_product_image_rejects_svg_filename(self, tmp_path, monkeypatch):
        import asyncio

        from app.utils import file_storage as fs

        monkeypatch.setattr(fs, "UPLOAD_ROOT", tmp_path)
        upload = UploadFile(
            filename="evil.svg",
            file=BytesIO(b"<svg></svg>"),
        )
        with pytest.raises(ValueError, match="Unsupported"):
            asyncio.run(fs.save_product_image_upload(1, upload))


class TestSsrfResolve:
    def test_blocks_literal_loopback_ipv6(self):
        with pytest.raises(ValueError, match="internal or private"):
            validate_product_image_url("http://[::1]/x.png", resolve_dns=False)

    def test_rejects_svg_extension(self):
        with pytest.raises(ValueError, match="image file"):
            validate_product_image_url(
                "https://cdn.example.com/x.svg", resolve_dns=False
            )
