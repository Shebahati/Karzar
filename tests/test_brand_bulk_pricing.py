"""Brand bulk base_price adjustment (Feature D)."""

from app.core.config import settings
from app.main import app
from fastapi.testclient import TestClient

BASE = "/api/v1/admin/brand-bulk-pricing"


def _create_product(client: TestClient, headers: dict, valid_product_data: dict, sku: str, **extra):
    payload = {**valid_product_data, "sku": sku, **extra}
    response = client.post("/api/v1/products/", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _preview(client, headers, **payload):
    return client.post(f"{BASE}/preview", json=payload, headers=headers)


def _confirm(client, headers, preview_body: dict):
    payload = {
        "brand_id": preview_body["brand_id"],
        "mode": preview_body["mode"],
        "direction": preview_body["direction"],
        "amount": preview_body["amount"],
        "manifest_sha256": preview_body["manifest_sha256"],
    }
    return client.post(f"{BASE}/confirm", json=payload, headers=headers)


class TestBrandBulkPricing:
    def test_preview_percent_increase(self, super_admin_headers, valid_product_data):
        client = TestClient(app)
        _create_product(client, super_admin_headers, valid_product_data, "BBP-1", base_price="100")
        response = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="increase",
            amount="10",
        )
        assert response.status_code == 200
        body = response.json()
        assert body["eligible_count"] >= 1
        line = next(row for row in body["lines"] if row["sku"] == "BBP-1")
        assert line["new_base_price"] == "110"

    def test_discount_conflict_detected(self, super_admin_headers, valid_product_data):
        client = TestClient(app)
        _create_product(
            client,
            super_admin_headers,
            valid_product_data,
            "BBP-CONFLICT",
            base_price="80",
            original_price="100",
        )
        response = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="increase",
            amount="30",
        )
        assert response.status_code == 200
        line = next(row for row in response.json()["lines"] if row["sku"] == "BBP-CONFLICT")
        assert line["line_status"] == "conflict"
        assert line["conflict_reason"] == "new_base_price_invalidates_discount"

    def test_confirm_and_apply(
        self, super_admin_headers, step_up_headers, valid_product_data, monkeypatch
    ):
        client = TestClient(app)
        created = _create_product(
            client, super_admin_headers, valid_product_data, "BBP-APPLY", base_price="200"
        )
        preview = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="increase",
            amount="25",
        ).json()
        confirm = _confirm(client, super_admin_headers, preview)
        assert confirm.status_code == 201
        operation_id = confirm.json()["id"]

        monkeypatch.setattr(settings, "BRAND_BULK_PRICE_APPLY_ENABLED", False)
        blocked = client.post(f"{BASE}/operations/{operation_id}/apply", headers=step_up_headers)
        assert blocked.status_code == 403

        monkeypatch.setattr(settings, "BRAND_BULK_PRICE_APPLY_ENABLED", True)
        pin_resp = client.post(
            "/api/v1/auth/verify-pin",
            json={"pin": settings.ADMIN_STEP_UP_PIN},
            headers=super_admin_headers,
        )
        fresh_headers = {
            **super_admin_headers,
            "X-Step-Up-Token": pin_resp.json()["secure_token"],
            "Idempotency-Key": "bbp-test-1",
        }
        applied = client.post(f"{BASE}/operations/{operation_id}/apply", headers=fresh_headers)
        assert applied.status_code == 200
        body = applied.json()
        assert body["status"] == "applied"
        assert body["applied_count"] >= 1

        product = client.get(f"/api/v1/products/{created['id']}", headers=super_admin_headers)
        assert product.json()["base_price"] == "250"

    def test_apply_idempotent(self, super_admin_headers, step_up_headers, valid_product_data, monkeypatch):
        client = TestClient(app)
        _create_product(client, super_admin_headers, valid_product_data, "BBP-IDEM", base_price="100")
        preview = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="decrease",
            amount="10",
        ).json()
        operation_id = _confirm(client, super_admin_headers, preview).json()["id"]
        monkeypatch.setattr(settings, "BRAND_BULK_PRICE_APPLY_ENABLED", True)
        headers = {**step_up_headers, "Idempotency-Key": "bbp-idem-key"}
        first = client.post(f"{BASE}/operations/{operation_id}/apply", headers=headers)
        second = client.post(f"{BASE}/operations/{operation_id}/apply", headers=headers)
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()

    def test_catalog_drift_blocks_apply(
        self, super_admin_headers, step_up_headers, valid_product_data, monkeypatch
    ):
        client = TestClient(app)
        created = _create_product(
            client, super_admin_headers, valid_product_data, "BBP-DRIFT", base_price="100"
        )
        preview = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="increase",
            amount="5",
        ).json()
        operation_id = _confirm(client, super_admin_headers, preview).json()["id"]
        client.put(
            f"/api/v1/products/{created['id']}",
            json={"base_price": "999"},
            headers=super_admin_headers,
        )
        monkeypatch.setattr(settings, "BRAND_BULK_PRICE_APPLY_ENABLED", True)
        drift = client.post(
            f"{BASE}/operations/{operation_id}/apply",
            headers=step_up_headers,
        )
        assert drift.status_code == 409

    def test_history_list(self, super_admin_headers, valid_product_data):
        client = TestClient(app)
        preview = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="increase",
            amount="1",
        ).json()
        _confirm(client, super_admin_headers, preview)
        listing = client.get(f"{BASE}/operations", headers=super_admin_headers)
        assert listing.status_code == 200
        assert listing.json()["total"] >= 1




    def test_fixed_mode_rejected(self, super_admin_headers):
        client = TestClient(app)
        response = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="fixed",
            direction="increase",
            amount="10",
        )
        assert response.status_code == 422

    def test_null_base_price_skipped_in_cohort_no_false_drift(
        self, super_admin_headers, step_up_headers, valid_product_data, monkeypatch
    ):
        client = TestClient(app)
        _create_product(
            client, super_admin_headers, valid_product_data, "BBP-NULL", base_price=None
        )
        with_price = _create_product(
            client, super_admin_headers, valid_product_data, "BBP-OK", base_price="100"
        )
        preview = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="increase",
            amount="10",
        ).json()
        null_line = next(row for row in preview["lines"] if row["sku"] == "BBP-NULL")
        ok_line = next(row for row in preview["lines"] if row["sku"] == "BBP-OK")
        assert null_line["line_status"] == "skipped"
        assert ok_line["line_status"] == "pending"
        operation_id = _confirm(client, super_admin_headers, preview).json()["id"]
        monkeypatch.setattr(settings, "BRAND_BULK_PRICE_APPLY_ENABLED", True)
        applied = client.post(
            f"{BASE}/operations/{operation_id}/apply",
            headers={**step_up_headers, "Idempotency-Key": "bbp-mixed-cohort"},
        )
        assert applied.status_code == 200
        assert applied.json()["applied_count"] == 1
        product = client.get(f"/api/v1/products/{with_price['id']}", headers=super_admin_headers)
        assert product.json()["base_price"] == "110"

    def test_stale_manifest_rejected(self, super_admin_headers, valid_product_data):
        client = TestClient(app)
        _create_product(client, super_admin_headers, valid_product_data, "BBP-MAN", base_price="100")
        preview = _preview(
            client,
            super_admin_headers,
            brand_id=1,
            mode="percent",
            direction="increase",
            amount="10",
        ).json()
        preview["manifest_sha256"] = "0" * 64
        confirm = _confirm(client, super_admin_headers, preview)
        assert confirm.status_code == 409

class TestBrandBulkPricingFingerprint:
    def test_unchanged_mixed_cohort_same_fingerprint(self):
        from decimal import Decimal

        from app.db.models.product import Product
        from app.services.brand_bulk_pricing_service import compute_catalog_fingerprint_sha256

        def prod(pid, sku, base, original=None):
            p = Product(id=pid, brand_id=1, sku=sku)
            p.base_price = Decimal(base) if base is not None else None
            p.original_price = Decimal(original) if original is not None else None
            p.deleted_at = None
            return p

        cohort = [
            prod(1, "A", "100"),
            prod(2, "B", None),
            prod(3, "C", "80", "100"),
        ]
        fp1 = compute_catalog_fingerprint_sha256(cohort)
        fp2 = compute_catalog_fingerprint_sha256(list(reversed(cohort)))
        assert fp1 == fp2

class TestBrandBulkPricingUnit:
    def test_compute_adjusted_base_price(self):
        from decimal import Decimal

        from app.db.models.brand_bulk_pricing import (
            BrandPriceAdjustmentDirection,
            BrandPriceAdjustmentMode,
        )
        from app.services.brand_bulk_pricing_service import compute_adjusted_base_price

        result = compute_adjusted_base_price(
            old_base=Decimal("100"),
            mode=BrandPriceAdjustmentMode.PERCENT,
            direction=BrandPriceAdjustmentDirection.INCREASE,
            amount=Decimal("10"),
        )
        assert result == Decimal("110.00")
