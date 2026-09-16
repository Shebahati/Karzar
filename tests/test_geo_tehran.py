from app.services.logistics.geo import is_tehran_city, is_tehran_province


def test_tehran_city_eligible():
    assert is_tehran_city("تهران", "تهران") is True


def test_shahriar_not_tehran_city():
    assert is_tehran_city("تهران", "شهریار") is False


def test_eslamshahr_not_tehran_city():
    assert is_tehran_city("تهران", "اسلامشهر") is False


def test_karaj_not_tehran_city():
    assert is_tehran_city("البرز", "کرج") is False


def test_tehran_province_persian():
    assert is_tehran_province("تهران") is True


def test_tehran_province_latin():
    assert is_tehran_province("Tehran") is True


def test_alborz_not_tehran_province():
    assert is_tehran_province("البرز") is False
    assert is_tehran_province("Alborz") is False


def test_other_provinces_not_tehran():
    assert is_tehran_province("اصفهان") is False
    assert is_tehran_province("خراسان رضوی") is False


def test_shahriar_in_tehran_province():
    assert is_tehran_province("تهران") is True
