"""Persian / Arabic character normalization for search."""

from __future__ import annotations

# Arabic yeh/kaf → Persian yeh/kaf; Arabic digits → Western digits (optional for SKU).
_TRANSLATION = str.maketrans(
    {
        "\u064a": "\u06cc",  # ي → ی
        "\u0643": "\u06a9",  # ك → ک
        "\u0660": "0",
        "\u0661": "1",
        "\u0662": "2",
        "\u0663": "3",
        "\u0664": "4",
        "\u0665": "5",
        "\u0666": "6",
        "\u0667": "7",
        "\u0668": "8",
        "\u0669": "9",
        "\u06f0": "0",
        "\u06f1": "1",
        "\u06f2": "2",
        "\u06f3": "3",
        "\u06f4": "4",
        "\u06f5": "5",
        "\u06f6": "6",
        "\u06f7": "7",
        "\u06f8": "8",
        "\u06f9": "9",
    }
)


def normalize_persian_search(text: str) -> str:
    """Normalize Arabic lookalikes, Eastern digits, and ZWNJ for ILIKE search."""
    return text.translate(_TRANSLATION).replace("\u200c", "").strip()
