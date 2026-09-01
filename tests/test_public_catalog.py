"""Tests for public catalog ordering and image eligibility."""

from app.core.config import settings
from app.db.models.product import Product, ProductImage
from app.services.order_workflow import (
    OPEN_INQUIRY_ORDER_STATUSES,
    OPEN_PURCHASE_ORDER_STATUSES,
    is_open_inquiry_order,
    is_open_purchase_order,
)
from app.utils.public_catalog import (
    get_first_valid_public_image_url,
    is_placeholder_image_url,
    local_upload_relative_path,
    product_has_materialized_public_image,
    product_has_storefront_public_image,
    product_has_valid_public_image,
    product_image_materialized_on_disk,
)
from app.utils.storefront_catalog import product_sort_clause


def test_is_placeholder_image_url_detects_known_patterns():
    assert is_placeholder_image_url("/images/placeholders/karzar-editorial.svg")
    assert is_placeholder_image_url("https://cdn.example/woocommerce-placeholder.png")
    assert not is_placeholder_image_url("/uploads/products/1221.webp")


def test_product_has_valid_public_image():
    product = Product(id=1, sku="T1", name="Test", is_active=True, is_available=True)
    product.images = [
        ProductImage(product_id=1, image_url="/images/placeholders/karzar-editorial.svg", is_primary=True),
    ]
    assert product_has_valid_public_image(product) is False
    assert get_first_valid_public_image_url(product) is None
    product.images = [
        ProductImage(product_id=1, image_url="/images/placeholders/karzar-editorial.svg", is_primary=True),
        ProductImage(product_id=1, image_url="/media/p/1221.webp", is_primary=False),
    ]
    assert product_has_valid_public_image(product) is True
    assert get_first_valid_public_image_url(product) == "/media/p/1221.webp"
    product.images = [ProductImage(product_id=1, image_url="/media/p/1221.webp", is_primary=True)]
    assert product_has_valid_public_image(product) is True


def test_product_sort_clause_partitions_availability_first():
    clause = product_sort_clause("price_asc")
    assert len(clause) >= 2


def test_open_order_workflow_sets():
    assert "paid" in OPEN_PURCHASE_ORDER_STATUSES
    assert "inquiry_review" in OPEN_INQUIRY_ORDER_STATUSES
    assert is_open_purchase_order("paid", payment_status="paid")
    assert not is_open_purchase_order("delivered", payment_status="paid")
    assert is_open_inquiry_order("inquiry_review")


def test_local_upload_relative_path_extracts_static_segment():
    url = "https://api.karzartools.com/static/uploads/products/9/abc.webp"
    assert local_upload_relative_path(url) == "products/9/abc.webp"


def test_product_image_materialized_on_disk_unknown_host_is_trusted():
    assert product_image_materialized_on_disk("https://cdn.example/x.jpg") is True


def test_product_has_materialized_public_image_requires_file_when_enabled(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(settings, "STOREFRONT_HIDE_IMAGELESS_PRODUCTS", True)
    monkeypatch.setattr(settings, "STOREFRONT_REQUIRE_MATERIALIZED_IMAGES", True)
    upload_root = tmp_path / "uploads"
    (upload_root / "products" / "1").mkdir(parents=True)
    image_path = upload_root / "products" / "1" / "a.webp"
    image_path.write_bytes(b"x")
    monkeypatch.setattr("app.utils.file_storage.UPLOAD_ROOT", upload_root)

    product = Product(id=1, sku="T2", name="File", is_active=True, is_available=True)
    product.images = [
        ProductImage(
            product_id=1,
            image_url="/static/uploads/products/1/a.webp",
            is_primary=True,
        )
    ]
    assert product_has_materialized_public_image(product) is True
    assert product_has_storefront_public_image(product) is True

    missing = Product(id=2, sku="T3", name="Missing", is_active=True, is_available=True)
    missing.images = [
        ProductImage(
            product_id=2,
            image_url="/static/uploads/products/2/missing.webp",
            is_primary=True,
        )
    ]
    assert product_has_materialized_public_image(missing) is False
    assert product_has_storefront_public_image(missing) is False


def test_restoration_after_assigning_valid_image():
    product = Product(id=3, sku="T4", name="Restore", is_active=True, is_available=True)
    product.images = [
        ProductImage(product_id=3, image_url="/images/placeholders/karzar-editorial.svg", is_primary=True),
    ]
    assert product_has_valid_public_image(product) is False
    product.images.append(
        ProductImage(product_id=3, image_url="/static/uploads/products/3/new.webp", is_primary=False)
    )
    assert get_first_valid_public_image_url(product) == "/static/uploads/products/3/new.webp"
    assert product_has_valid_public_image(product) is True
