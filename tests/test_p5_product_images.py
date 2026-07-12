"""P5: product image endpoint tests (URL, primary, reorder, delete)."""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

_PUBLIC_IMAGE = "https://cdn.example.com/products/p5-test.jpg"


class TestProductImageEndpoints:
    def _create_product(self, super_admin_headers, sku: str) -> int:
        response = client.post(
            "/api/v1/products/",
            json={
                "sku": sku,
                "name": "P5 Image Product",
                "category_id": 3,
                "brand_id": 1,
                "base_price": "99.99",
                "stock_quantity": "10",
                "stock_unit": "piece",
                "is_active": True,
                "specifications": {
                    "technical_specs": {"range": "0-150mm"},
                    "features": {"waterproof": False},
                    "dimensions": {"L_mm": 100.0},
                    "optional_accessories": [],
                },
            },
            headers=super_admin_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def test_add_delete_reorder_and_set_primary(
        self, valid_product_data, super_admin_headers
    ):
        product_id = self._create_product(super_admin_headers, "P5-IMG-001")

        first = client.post(
            f"/api/v1/products/{product_id}/images",
            json={"image_url": _PUBLIC_IMAGE, "is_primary": True},
            headers=super_admin_headers,
        )
        assert first.status_code == 201, first.text

        detail_after_first = client.get(
            f"/api/v1/products/{product_id}",
            headers=super_admin_headers,
        )
        assert detail_after_first.status_code == 200
        first_id = detail_after_first.json()["images"][0]["id"]
        assert detail_after_first.json()["images"][0]["is_primary"] is True

        second = client.post(
            f"/api/v1/products/{product_id}/images",
            json={
                "image_url": "https://cdn.example.com/products/p5-second.png",
                "is_primary": False,
            },
            headers=super_admin_headers,
        )
        assert second.status_code == 201
        detail_after_second = client.get(
            f"/api/v1/products/{product_id}",
            headers=super_admin_headers,
        )
        second_id = next(
            img["id"]
            for img in detail_after_second.json()["images"]
            if img["id"] != first_id
        )

        primary = client.patch(
            f"/api/v1/products/{product_id}/images/{second_id}/primary",
            headers=super_admin_headers,
        )
        assert primary.status_code == 200
        primary_ids = [img for img in primary.json()["images"] if img["is_primary"]]
        assert len(primary_ids) == 1
        assert primary_ids[0]["id"] == second_id

        reordered = client.patch(
            f"/api/v1/products/{product_id}/images/reorder",
            json={"image_ids": [second_id, first_id]},
            headers=super_admin_headers,
        )
        assert reordered.status_code == 200
        assert [img["id"] for img in reordered.json()["images"]] == [second_id, first_id]

        deleted = client.delete(
            f"/api/v1/products/{product_id}/images/{first_id}",
            headers=super_admin_headers,
        )
        assert deleted.status_code == 204

        detail = client.get(
            f"/api/v1/products/{product_id}",
            headers=super_admin_headers,
        )
        assert detail.status_code == 200
        assert len(detail.json()["images"]) == 1
        assert detail.json()["images"][0]["id"] == second_id

    def test_rejects_internal_image_url(self, valid_product_data, super_admin_headers):
        product_id = self._create_product(super_admin_headers, "P5-IMG-SSRF")
        response = client.post(
            f"/api/v1/products/{product_id}/images",
            json={"image_url": "http://127.0.0.1/secret.jpg"},
            headers=super_admin_headers,
        )
        assert response.status_code == 400
        assert response.json()["error_code"] == "VALIDATION_FAILED"
