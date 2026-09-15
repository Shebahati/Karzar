"""Destination normalization for shipping eligibility (provider-neutral)."""

from __future__ import annotations

import re
import unicodedata

# Arabic Yeh / Kaf → Persian forms
_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ك": "ک", "ة": "ه"})

_TEHRAN_CITY_ALIASES = frozenset(
    {
        "تهران",
        "tehran",
        "طهران",  # rare typo
    }
)


def normalize_geo_text(value: str | None) -> str:
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value.strip())
    text = text.translate(_ARABIC_TO_PERSIAN)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def is_tehran_city(province: str | None, city: str | None) -> bool:
    """Tehran **city** only — not Tehran province satellite towns."""
    province_norm = normalize_geo_text(province)
    city_norm = normalize_geo_text(city)
    if not city_norm:
        return False
    if city_norm in {normalize_geo_text(a) for a in _TEHRAN_CITY_ALIASES}:
        # Require Tehran province for consistency (تهران / تهران).
        if province_norm and province_norm not in {normalize_geo_text("تهران"), "tehran"}:
            return False
        return True
    return False
