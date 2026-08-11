"""Unit tests for ShopMill watermark detection/remediation (no DB/network)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from scripts.shopmill_watermark.detect import detect_shopmill, remaining_logo_zone_yellow
from scripts.shopmill_watermark.remediate import remediate_array


def _synthetic_shopmill(size: int = 800) -> np.ndarray:
    img = Image.new("RGB", (size, size), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Approximate Shop (yellow) + Mill (navy) blocks in top-left
    draw.rectangle((80, 70, 260, 145), fill=(255, 180, 0))
    draw.rectangle((270, 70, 400, 135), fill=(20, 30, 70))
    # dummy product blob
    draw.ellipse((250, 300, 550, 600), fill=(180, 180, 185))
    return np.asarray(img)


def test_detect_synthetic_shopmill():
    rgb = _synthetic_shopmill()
    det = detect_shopmill(rgb)
    assert det.detected is True
    assert det.bbox is not None
    assert det.confidence in {"high", "medium"}


def test_remediate_clears_logo_zone():
    rgb = _synthetic_shopmill()
    repaired, det = remediate_array(rgb)
    assert det.detected is True
    post = detect_shopmill(repaired)
    assert post.detected is False
    assert remaining_logo_zone_yellow(repaired) < 40


def test_clean_white_image_not_flagged():
    rgb = np.full((600, 600, 3), 255, dtype=np.uint8)
    det = detect_shopmill(rgb)
    assert det.detected is False


def test_real_sample_if_present():
    sample = Path(
        "aods/reports/tasks/IMG-SHOPMILL-WATERMARK-CLEANUP/samples/SAN_OU_13a01cc6a6b8.jpg"
    )
    if not sample.is_file():
        return
    rgb = np.asarray(Image.open(sample).convert("RGB"))
    det = detect_shopmill(rgb)
    assert det.detected is True
    repaired, _ = remediate_array(rgb, det)
    assert detect_shopmill(repaired).detected is False
