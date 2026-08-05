"""Image quality metrics and deduplication helpers (Pillow only; no new deps)."""

from __future__ import annotations

import hashlib
from io import BytesIO
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import MultisourceError


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_source_url(url: str) -> str:
    parts = urlsplit((url or "").strip())
    scheme = parts.scheme.casefold()
    netloc = parts.netloc.casefold()
    path = parts.path or "/"
    # Drop fragment and common tracking query noise while keeping path identity.
    return urlunsplit((scheme, netloc, path, "", ""))


def average_perceptual_hash(data: bytes, *, hash_size: int = 8) -> str:
    """Average hash using Pillow only (dependency already present)."""
    try:
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise MultisourceError("quality", f"Pillow unavailable: {exc}") from exc
    with Image.open(BytesIO(data)) as im:
        gray = im.convert("L").resize((hash_size, hash_size))
        if hasattr(gray, "get_flattened_data"):
            pixels = list(gray.get_flattened_data())
        else:  # pragma: no cover
            pixels = list(gray.getdata())  # type: ignore[attr-defined]
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if px >= avg else "0" for px in pixels)
    # Pack to hex
    value = int(bits, 2)
    width = (hash_size * hash_size + 3) // 4
    return f"{value:0{width}x}"


def hamming_distance_hex(a: str, b: str) -> int:
    if len(a) != len(b):
        raise MultisourceError("quality", "perceptual hash length mismatch")
    x = int(a, 16) ^ int(b, 16)
    return x.bit_count()


def inspect_image_bytes(data: bytes) -> dict[str, Any]:
    if not data:
        return {"quality_status": "reject", "reject_reason": "broken_empty"}
    head = data[:512].lstrip().lower()
    if head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head[:200]:
        return {"quality_status": "reject", "reject_reason": "html_response"}
    try:
        from PIL import Image  # type: ignore

        with Image.open(BytesIO(data)) as im:
            im.load()
            width, height = int(im.width), int(im.height)
            fmt = (im.format or "").upper()
    except Exception:
        return {"quality_status": "reject", "reject_reason": "broken_image"}

    if width < 64 or height < 64 or len(data) < 2048:
        return {
            "quality_status": "reject",
            "reject_reason": "very_small",
            "width": width,
            "height": height,
            "byte_size": len(data),
            "format": fmt,
            "sha256": sha256_bytes(data),
        }

    phash = average_perceptual_hash(data)
    return {
        "quality_status": "ok",
        "reject_reason": "",
        "width": width,
        "height": height,
        "byte_size": len(data),
        "format": fmt,
        "sha256": sha256_bytes(data),
        "perceptual_hash": phash,
        "watermark_status": "review_required",
        "background_status": "unknown",
    }


def dedupe_key_exact(sha256: str) -> str:
    return f"sha256:{sha256}"


def dedupe_key_url(url: str) -> str:
    return f"url:{normalize_source_url(url)}"


def dedupe_key_phash(phash: str) -> str:
    return f"phash:{phash}"


def group_duplicates(
    assets: list[dict[str, str]],
    *,
    phash_hamming_threshold: int = 0,
) -> list[dict[str, str]]:
    """Group by exact sha, normalized URL, and identical perceptual hash by default."""
    groups: dict[str, list[str]] = {}
    for row in assets:
        aid = row.get("asset_id") or row.get("sha256") or ""
        if not aid:
            continue
        keys = []
        if row.get("sha256"):
            keys.append(dedupe_key_exact(row["sha256"]))
        if row.get("source_image_url"):
            keys.append(dedupe_key_url(row["source_image_url"]))
        if row.get("perceptual_hash"):
            keys.append(dedupe_key_phash(row["perceptual_hash"]))
        for key in keys:
            groups.setdefault(key, []).append(aid)

    # Optional near-duplicate expansion (threshold > 0)
    if phash_hamming_threshold > 0:
        hashed = [
            (r.get("asset_id") or r.get("sha256") or "", r.get("perceptual_hash") or "")
            for r in assets
            if r.get("perceptual_hash")
        ]
        for i, (aid_a, ha) in enumerate(hashed):
            for aid_b, hb in hashed[i + 1 :]:
                if hamming_distance_hex(ha, hb) <= phash_hamming_threshold:
                    key = f"phash_near:{min(ha, hb)}:{max(ha, hb)}"
                    groups.setdefault(key, []).extend([aid_a, aid_b])

    out: list[dict[str, str]] = []
    for key, members in sorted(groups.items()):
        uniq = sorted(set(members))
        if len(uniq) < 2:
            continue
        out.append(
            {
                "group_key": key,
                "member_count": str(len(uniq)),
                "asset_ids": "|".join(uniq),
            }
        )
    return out
