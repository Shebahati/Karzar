"""Remediate ShopMill watermarks (Method C — professional corner fill)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .detect import DetectionResult, detect_shopmill, remaining_logo_zone_yellow


@dataclass(frozen=True)
class RemediationResult:
    ok: bool
    method: str
    detection: DetectionResult
    output_path: Path | None
    original_sha256: str
    final_sha256: str
    remaining_logo_yellow: int
    width: int
    height: int
    reason: str = ""


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def remediate_array(rgb: np.ndarray, detection: DetectionResult | None = None) -> tuple[np.ndarray, DetectionResult]:
    det = detection or detect_shopmill(rgb)
    if not det.detected or det.bbox is None:
        return rgb, det
    out = rgb.copy()
    xmin, ymin, xmax, ymax = det.bbox
    out[ymin : ymax + 1, xmin : xmax + 1] = 255
    return out, det


def remediate_file(
    source: Path,
    destination: Path,
    *,
    force_jpeg: bool = False,
) -> RemediationResult:
    original_sha = _sha256_file(source)
    image = Image.open(source).convert("RGB")
    rgb = np.asarray(image)
    repaired, det = remediate_array(rgb)
    if not det.detected or det.bbox is None:
        return RemediationResult(
            ok=False,
            method="method_c_bbox_fill",
            detection=det,
            output_path=None,
            original_sha256=original_sha,
            final_sha256=original_sha,
            remaining_logo_yellow=remaining_logo_zone_yellow(rgb),
            width=int(rgb.shape[1]),
            height=int(rgb.shape[0]),
            reason=det.reason or "not_detected",
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    out_img = Image.fromarray(repaired)
    suffix = ".jpg" if force_jpeg else source.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix = ".jpg"
    if destination.suffix.lower() != suffix:
        destination = destination.with_suffix(suffix)

    if suffix in {".jpg", ".jpeg"}:
        out_img.save(destination, format="JPEG", quality=95, optimize=True)
    elif suffix == ".png":
        out_img.save(destination, format="PNG", optimize=True)
    else:
        out_img.save(destination, format="WEBP", quality=95)

    final_sha = _sha256_file(destination)
    rem = remaining_logo_zone_yellow(repaired)
    # Pattern must no longer detect, and logo-zone yellow must be gone.
    post = detect_shopmill(repaired)
    ok = (not post.detected) and rem < 40
    return RemediationResult(
        ok=ok,
        method="method_c_bbox_fill",
        detection=det,
        output_path=destination,
        original_sha256=original_sha,
        final_sha256=final_sha,
        remaining_logo_yellow=rem,
        width=int(repaired.shape[1]),
        height=int(repaired.shape[0]),
        reason="" if ok else "post_detection_failed",
    )
