"""Hero Studio pack validation regression tests."""

from app.services import hero_design_service as hero_svc


def test_validate_rejects_wrong_slide_id():
    pack = hero_svc.load_pack_from_path(hero_svc.FIXTURE_PACK_PATH)
    pack["slides"][0]["id"] = "slide_wrong"
    errors = hero_svc.validate_pack(pack)
    assert any(e.field == "slides.id" for e in errors)
