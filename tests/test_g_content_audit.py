"""Phase G content/integrations audit: CMS visibility, comments, notify soft-fail."""

import pytest
from app.core.config import settings
from app.main import app
from app.services import notification_service
from app.utils.file_storage import UPLOAD_ROOT, _safe_extension
from fastapi.testclient import TestClient

from tests.conftest import customer_auth_headers

client = TestClient(app)


def test_unpublished_article_hidden_from_storefront(super_admin_headers):
    published = client.post(
        "/api/v1/cms/articles",
        headers=super_admin_headers,
        json={
            "slug": "g-published",
            "title": "منتشر شده",
            "excerpt": "خلاصه",
            "cover_image": "https://cdn.example.com/a.jpg",
            "published_at": "2026-06-01T10:00:00Z",
            "reading_minutes": 2,
            "is_published": True,
        },
    )
    assert published.status_code == 201

    draft = client.post(
        "/api/v1/cms/articles",
        headers=super_admin_headers,
        json={
            "slug": "g-draft",
            "title": "پیش‌نویس",
            "excerpt": "خلاصه",
            "cover_image": "https://cdn.example.com/b.jpg",
            "published_at": "2026-06-02T10:00:00Z",
            "reading_minutes": 2,
            "is_published": False,
        },
    )
    assert draft.status_code == 201

    public = client.get("/api/v1/blog/")
    assert public.status_code == 200
    slugs = {row["slug"] for row in public.json()["data"]}
    assert "g-published" in slugs
    assert "g-draft" not in slugs

    assert client.get("/api/v1/blog/g-draft").status_code == 404
    assert client.get("/api/v1/blog/g-published").status_code == 200


def test_hero_slides_active_only_and_sorted(super_admin_headers):
    for sort_order, title, active in (
        (20, "دوم", True),
        (10, "اول", True),
        (5, "غیرفعال", False),
    ):
        created = client.post(
            "/api/v1/cms/hero-slides",
            headers=super_admin_headers,
            json={
                "title": title,
                "subtitle": "",
                "cta_label": "بیشتر",
                "cta_href": "/catalog",
                "image": "https://cdn.example.com/hero.jpg",
                "accent": "#000",
                "sort_order": sort_order,
                "is_active": active,
            },
        )
        assert created.status_code == 201, created.text

    public = client.get("/api/v1/hero-slides/")
    assert public.status_code == 200
    titles = [row["title"] for row in public.json()["data"]]
    assert "غیرفعال" not in titles
    assert titles.index("اول") < titles.index("دوم")


def test_contact_tickets_are_unique():
    payload = {
        "full_name": "کاربر تماس",
        "phone": "09127770001",
        "subject": "سوال",
        "message": "پیام تست برای صدور تیکت یکتا در فاز G.",
    }
    first = client.post("/api/v1/contact", json=payload)
    second = client.post("/api/v1/contact", json={**payload, "phone": "09127770002"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["ticket"].startswith("TK-")
    assert second.json()["ticket"].startswith("TK-")
    assert first.json()["ticket"] != second.json()["ticket"]


def test_comments_require_auth_and_block_inactive_product(
    valid_product_data, super_admin_headers, monkeypatch
):
    monkeypatch.setattr(settings, "OTP_DEV_ECHO", True)
    active = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "G-CMT-OK"},
        headers=super_admin_headers,
    )
    inactive = client.post(
        "/api/v1/products/",
        json={**valid_product_data, "sku": "G-CMT-OFF", "is_active": False},
        headers=super_admin_headers,
    )
    active_id = active.json()["id"]
    inactive_id = inactive.json()["id"]

    anon = client.post(
        f"/api/v1/products/{active_id}/comments",
        json={"author_name": "مهمان", "rating": 5, "body": "نظر تستی بلند genug"},
    )
    assert anon.status_code == 401

    headers = customer_auth_headers("09127771111")
    blocked = client.post(
        f"/api/v1/products/{inactive_id}/comments",
        json={"author_name": "کاربر", "rating": 4, "body": "نظر روی محصول غیرفعال"},
        headers=headers,
    )
    assert blocked.status_code == 404

    assert client.get(f"/api/v1/products/{inactive_id}/comments").status_code == 404

    ok = client.post(
        f"/api/v1/products/{active_id}/comments",
        json={"author_name": "کاربر", "rating": 5, "body": "نظر مجاز روی محصول فعال"},
        headers=headers,
    )
    assert ok.status_code == 201


def test_cms_requires_admin():
    from app.api.deps import get_current_super_admin
    from app.main import app as fastapi_app

    fastapi_app.dependency_overrides.pop(get_current_super_admin, None)
    assert client.get("/api/v1/cms/articles").status_code == 401
    assert client.get("/api/v1/cms/hero-slides").status_code == 401
    assert client.get("/api/v1/cms/contact-submissions").status_code == 401


def test_order_status_notification_failure_is_soft(monkeypatch):
    class BoomProvider:
        async def send(self, message):
            raise RuntimeError("sms down")

    monkeypatch.setattr(
        notification_service, "get_sms_provider", lambda: BoomProvider()
    )
    # Should not raise — soft-fail path
    import asyncio

    asyncio.run(
        notification_service.notify_order_status_change(
            phone="09120000000",
            tracking_code="KZ-TESTSOFTFAIL",
            status="paid",
        )
    )


def test_upload_storage_guards():
    assert UPLOAD_ROOT.name == "uploads"
    assert _safe_extension("photo.PNG") == ".png"
    with pytest.raises(ValueError):
        _safe_extension("payload.exe")
