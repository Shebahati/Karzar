from app.services.logistics.geo import is_tehran_city


def test_tehran_city_eligible():
    assert is_tehran_city("تهران", "تهران") is True


def test_shahriar_not_eligible():
    assert is_tehran_city("تهران", "شهریار") is False


def test_eslamshahr_not_eligible():
    assert is_tehran_city("تهران", "اسلامشهر") is False


def test_karaj_not_eligible():
    assert is_tehran_city("البرز", "کرج") is False
