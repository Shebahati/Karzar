"""Hero Studio pack validation regression tests."""

import copy

from app.services import hero_design_service as hero_svc


def _r0_pack():
    return copy.deepcopy(hero_svc.load_pack_from_path(hero_svc.FIXTURE_PACK_PATH))


def test_validate_accepts_r0_fixture():
    assert not hero_svc.validate_pack(_r0_pack())


def test_validate_rejects_wrong_slide_id():
    pack = _r0_pack()
    pack["slides"][0]["id"] = "slide_wrong"
    errors = hero_svc.validate_pack(pack)
    assert any(e.field == "slides.id" for e in errors)


def test_validate_rejects_wrong_desktop_asset():
    pack = _r0_pack()
    pack["slides"][0]["config"]["background"]["imageUrl"] = (
        "/images/hero/reborn-5/photo-20261021-v2/H99-wrong-desktop.webp"
    )
    errors = hero_svc.validate_pack(pack)
    assert any("imageUrl" in e.field for e in errors)


def test_validate_rejects_invalid_sort_order_sequence():
    pack = _r0_pack()
    pack["slides"][0]["sortOrder"] = 9
    errors = hero_svc.validate_pack(pack)
    assert any(e.field == "slides.sortOrder" for e in errors)


def test_validate_rejects_non_integer_featured_order():
    pack = _r0_pack()
    pack["categoryDock"]["categories"][0]["featuredOrder"] = "zero"
    errors = hero_svc.validate_pack(pack)
    assert any("featuredOrder" in e.field for e in errors)


def test_validate_rejects_non_object_slide_without_raising():
    pack = {"version": 1, "slides": [None, "bad"], "categoryDock": {"categories": []}}
    errors = hero_svc.validate_pack(pack)
    assert errors
