"""Advisory technical pre-screen signals (not verdicts)."""

from __future__ import annotations

from typing import Any

from PIL import Image, ImageFilter, ImageOps, ImageStat


def _border_metrics(im: Image.Image, *, border: int = 8) -> tuple[float, float]:
    """Return (border_lightness_mean, border_uniformity_score) in [0,1]-ish floats."""
    rgb = im.convert("RGB")
    w, h = rgb.size
    if w < border * 2 + 1 or h < border * 2 + 1:
        border = max(1, min(w, h) // 4)
    pixels: list[tuple[int, int, int]] = []
    for x in range(w):
        for y in range(border):
            pixels.append(rgb.getpixel((x, y)))
            pixels.append(rgb.getpixel((x, h - 1 - y)))
    for y in range(border, h - border):
        for x in range(border):
            pixels.append(rgb.getpixel((x, y)))
            pixels.append(rgb.getpixel((w - 1 - x, y)))
    if not pixels:
        return 0.0, 0.0
    lightness = [((r + g + b) / 3.0) / 255.0 for r, g, b in pixels]
    mean = sum(lightness) / len(lightness)
    var = sum((v - mean) ** 2 for v in lightness) / len(lightness)
    # uniformity: 1 = perfectly uniform border
    uniformity = max(0.0, 1.0 - (var * 8.0))
    return round(mean, 6), round(uniformity, 6)


def _sharpness_score(im: Image.Image) -> float:
    gray = ImageOps.exif_transpose(im).convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    # mean edge magnitude normalized roughly to 0..1
    mean = float(stat.mean[0]) if stat.mean else 0.0
    return round(min(1.0, mean / 40.0), 6)


def compute_prescreen(
    im: Image.Image,
    *,
    width: int | None = None,
    height: int | None = None,
) -> dict[str, Any]:
    """Deterministic advisory flags for one opened image (already oriented)."""
    oriented = ImageOps.exif_transpose(im)
    w = int(width if width is not None else oriented.width)
    h = int(height if height is not None else oriented.height)
    min_dim = min(w, h)
    max_dim = max(w, h)
    megapixels = round((w * h) / 1_000_000.0, 6)
    aspect_ratio = round((w / h) if h else 0.0, 6)
    alpha_present = (
        oriented.mode in {"RGBA", "LA"}
        or (oriented.mode == "P" and "transparency" in oriented.info)
    )
    border_lightness_mean, border_uniformity_score = _border_metrics(oriented)
    sharpness_score = _sharpness_score(oriented)

    low_resolution_candidate = bool(min_dim < 600 or megapixels < 0.5)
    extreme_aspect_candidate = bool(aspect_ratio > 4.0 or aspect_ratio < 0.25)
    transparent_background_candidate = bool(alpha_present)
    busy_or_nonuniform_border_candidate = bool(border_uniformity_score < 0.85)

    return {
        "min_dimension": min_dim,
        "max_dimension": max_dim,
        "megapixels": megapixels,
        "aspect_ratio": aspect_ratio,
        "alpha_present": alpha_present,
        "border_lightness_mean": border_lightness_mean,
        "border_uniformity_score": border_uniformity_score,
        "sharpness_score": sharpness_score,
        "low_resolution_candidate": low_resolution_candidate,
        "extreme_aspect_candidate": extreme_aspect_candidate,
        "transparent_background_candidate": transparent_background_candidate,
        "busy_or_nonuniform_border_candidate": busy_or_nonuniform_border_candidate,
        "watermark_prescreen": "not_run",
        "watermark_review_required": True,
    }
