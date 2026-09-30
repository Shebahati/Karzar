"""Unit tests for Emalls PDF feed preflight analyzer (no live HTTP)."""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "emalls_pdf_feed_preflight",
    ROOT / "scripts" / "emalls_pdf_feed_preflight.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
analyze_feed = MODULE.analyze_feed


def _product(
    *,
    pid: str,
    price: int = 1000,
    old_price: int | None = None,
) -> dict:
    return {
        "title": f"Product {pid}",
        "id": pid,
        "price": price,
        "old_price": old_price,
        "category": "Calipers",
        "image": "https://cdn.karzartools.com/static/uploads/p.webp",
        "color": "",
        "guarantee": "",
        "is_available": True,
        "url": f"https://www.karzartools.com/product/p-{pid}",
    }


def _page(
    *,
    page_num: int,
    item_per_page: int,
    total_items: int,
    pages_count: int,
    products: list[dict],
) -> dict:
    return {
        "success": True,
        "products": products,
        "total_items": total_items,
        "pages_count": pages_count,
        "item_per_page": item_per_page,
        "page_num": page_num,
    }


def test_valid_three_page_full_feed_pass():
    item_per_page = 2
    products = [_product(pid=str(i)) for i in range(1, 6)]
    total = 5
    pages_count = math.ceil(total / item_per_page)
    pages = [
        _page(
            page_num=1,
            item_per_page=item_per_page,
            total_items=total,
            pages_count=pages_count,
            products=products[0:2],
        ),
        _page(
            page_num=2,
            item_per_page=item_per_page,
            total_items=total,
            pages_count=pages_count,
            products=products[2:4],
        ),
        _page(
            page_num=3,
            item_per_page=item_per_page,
            total_items=total,
            pages_count=pages_count,
            products=products[4:5],
        ),
    ]
    result = analyze_feed(
        pages, requested_item_per_page=item_per_page, scan_complete=True
    )
    assert result["ok"] is True
    assert result["fetched"] == 5
    assert result["scan_complete"] is True


def test_reported_total_gt_fetched_fail():
    pages = [
        _page(
            page_num=1,
            item_per_page=2,
            total_items=4,
            pages_count=2,
            products=[_product(pid="1"), _product(pid="2")],
        ),
        _page(
            page_num=2,
            item_per_page=2,
            total_items=4,
            pages_count=2,
            products=[_product(pid="3")],
        ),
    ]
    result = analyze_feed(pages, requested_item_per_page=2, scan_complete=True)
    assert result["ok"] is False
    assert any("fetched_ne_total_items" in i for i in result["issues"])


def test_wrong_pages_count_fail():
    pages = [
        _page(
            page_num=1,
            item_per_page=2,
            total_items=4,
            pages_count=99,
            products=[_product(pid="1"), _product(pid="2")],
        ),
        _page(
            page_num=2,
            item_per_page=2,
            total_items=4,
            pages_count=99,
            products=[_product(pid="3"), _product(pid="4")],
        ),
    ]
    result = analyze_feed(pages, requested_item_per_page=2, scan_complete=True)
    assert result["ok"] is False
    assert any("pages_count_mismatch" in i for i in result["issues"])


def test_premature_empty_page_fail():
    pages = [
        _page(
            page_num=1,
            item_per_page=2,
            total_items=4,
            pages_count=2,
            products=[_product(pid="1"), _product(pid="2")],
        ),
        _page(
            page_num=2,
            item_per_page=2,
            total_items=4,
            pages_count=2,
            products=[],
        ),
    ]
    result = analyze_feed(pages, requested_item_per_page=2, scan_complete=True)
    assert result["ok"] is False
    assert any("premature_empty_page" in i for i in result["issues"])


def test_wrong_page_num_fail():
    pages = [
        _page(
            page_num=2,
            item_per_page=1,
            total_items=1,
            pages_count=1,
            products=[_product(pid="1")],
        ),
    ]
    result = analyze_feed(pages, requested_item_per_page=1, scan_complete=True)
    assert result["ok"] is False
    assert any("wrong_page_num" in i for i in result["issues"])


def test_changing_total_items_fail():
    pages = [
        _page(
            page_num=1,
            item_per_page=1,
            total_items=2,
            pages_count=2,
            products=[_product(pid="1")],
        ),
        _page(
            page_num=2,
            item_per_page=1,
            total_items=3,
            pages_count=2,
            products=[_product(pid="2")],
        ),
    ]
    result = analyze_feed(pages, requested_item_per_page=1, scan_complete=True)
    assert result["ok"] is False
    assert any("total_items_changed" in i for i in result["issues"])


def test_wrong_item_per_page_fail():
    pages = [
        _page(
            page_num=1,
            item_per_page=50,
            total_items=1,
            pages_count=1,
            products=[_product(pid="1")],
        ),
    ]
    result = analyze_feed(pages, requested_item_per_page=10, scan_complete=True)
    assert result["ok"] is False
    assert any("wrong_item_per_page" in i for i in result["issues"])


def test_non_integer_root_pagination_fail():
    page = _page(
        page_num=1,
        item_per_page=1,
        total_items=1,
        pages_count=1,
        products=[_product(pid="1")],
    )
    page["total_items"] = True
    result = analyze_feed([page], requested_item_per_page=1, scan_complete=True)
    assert result["ok"] is False
    assert any("total_items_not_int" in i for i in result["issues"])


def test_unexpected_root_field_fail():
    page = _page(
        page_num=1,
        item_per_page=1,
        total_items=1,
        pages_count=1,
        products=[_product(pid="1")],
    )
    page["Version"] = "1.3.0"
    result = analyze_feed([page], requested_item_per_page=1, scan_complete=True)
    assert result["ok"] is False
    assert any("unexpected_root" in i for i in result["issues"])


def test_partial_scan_does_not_require_fetched_eq_total():
    pages = [
        _page(
            page_num=1,
            item_per_page=2,
            total_items=10,
            pages_count=5,
            products=[_product(pid="1"), _product(pid="2")],
        ),
    ]
    result = analyze_feed(pages, requested_item_per_page=2, scan_complete=False)
    assert result["ok"] is True
    assert result["scan_complete"] is False
    assert result["fetched"] == 2
    assert not any("fetched_ne_total_items" in i for i in result["issues"])
