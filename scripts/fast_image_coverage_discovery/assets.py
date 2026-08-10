"""Physical asset materialization with SHA-256 dedupe."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.image_discovery.contracts import DiscoveryError
from scripts.image_discovery.quality import (
    detect_signature,
    extract_dimensions,
    validate_image_bytes,
)

from .contracts import MaterializedAsset


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def materialize_asset(
    data: bytes,
    *,
    assets_dir: Path,
    source_url: str,
    sha_map: dict[str, str],
) -> MaterializedAsset | None:
    try:
        validate_image_bytes(
            data,
            content_type="image/png",
            final_url=source_url,
            min_bytes=100,
            min_dim=10,
        )
    except DiscoveryError:
        return None
    digest = sha256_bytes(data)
    if digest in sha_map:
        rel = sha_map[digest]
    else:
        sig = detect_signature(data) or "bin"
        ext = {"jpeg": "jpg", "png": "png", "webp": "webp", "gif": "gif"}.get(sig, sig)
        rel = f"assets/{digest}.{ext}"
        path = assets_dir.parent / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file():
            path.write_bytes(data)
        sha_map[digest] = rel
    sig = detect_signature(data) or "unknown"
    w, h = extract_dimensions(data, sig if sig != "unknown" else "image/png")
    return MaterializedAsset(
        sha256=digest,
        relative_path=sha_map[digest],
        width=int(w or 0),
        height=int(h or 0),
        format=sig,
        byte_size=len(data),
        mime_type=f"image/{sig}" if sig in {"jpeg", "png", "webp", "gif"} else "application/octet-stream",
        source_url=source_url,
    )


def is_tiny_tracker(width: int, height: int, byte_size: int) -> bool:
    if byte_size < 500:
        return True
    if width and height and width <= 32 and height <= 32:
        return True
    return False
