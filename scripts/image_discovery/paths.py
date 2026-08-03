"""Filesystem-safe naming under a governed assets directory."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from pathlib import Path

from .contracts import DiscoveryError

_WIN_RESERVED = frozenset(
    {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
)
_CTRL_RE = re.compile(r"[\x00-\x1f\x7f]")
_MAX_SEGMENT = 48
_MAX_FILENAME = 180


def safe_path_segment(raw: str, *, max_len: int = _MAX_SEGMENT) -> str:
    """Unicode-normalize, strip traversal/controls, bound length, append hash suffix."""
    original = raw if raw is not None else ""
    text = unicodedata.normalize("NFKC", original)
    text = _CTRL_RE.sub("", text)
    text = text.replace("\x00", "")
    text = text.replace("/", "-").replace("\\", "-")
    text = text.replace("..", ".")
    text = text.strip(" .")
    if not text or text in {".", ".."}:
        text = "seg"
    # Collapse to readable slug
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text)
    slug = re.sub(r"-{2,}", "-", slug).strip("-._")
    if not slug:
        slug = "seg"
    upper = slug.upper()
    if upper in _WIN_RESERVED or upper.split(".", 1)[0] in _WIN_RESERVED:
        slug = f"x-{slug}"
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-._")
    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()[:12]
    return f"{slug}__{digest}"


def governed_asset_filename(
    *,
    brand: str,
    label: str,
    sha256: str,
    extension: str,
    max_filename: int = _MAX_FILENAME,
) -> str:
    """Readable slug + short SHA suffix; full SHA remains the integrity key in manifests."""
    if not sha256 or len(sha256) < 64:
        raise DiscoveryError("fs", "invalid_sha256", "full SHA-256 required for asset naming")
    brand_seg = safe_path_segment(brand or "brand", max_len=24)
    label_seg = safe_path_segment(label or "asset", max_len=40)
    ext = re.sub(r"[^A-Za-z0-9]+", "", (extension or "bin").lower()) or "bin"
    short = sha256[:12]
    name = f"{brand_seg}__{label_seg}__{short}.{ext}"
    if len(name) > max_filename:
        # Prefer preserving hash suffix + extension
        keep = max_filename - (len(short) + len(ext) + 3)
        stem = f"{brand_seg}__{label_seg}"[: max(8, keep)]
        name = f"{stem}__{short}.{ext}"
    return name


def assert_under_assets(assets_dir: Path, destination: Path) -> Path:
    """Confirm resolved destination remains beneath governed assets directory."""
    assets = assets_dir.resolve()
    dest = destination.resolve()
    try:
        dest.relative_to(assets)
    except ValueError as e:
        raise DiscoveryError(
            "fs",
            "path_escape",
            f"resolved_destination outside assets: {dest}",
        ) from e
    # Reject if any parent segment is .. after resolve (resolve already collapses)
    parts = dest.parts
    if ".." in parts:
        raise DiscoveryError("fs", "path_escape", f"traversal in destination: {dest}")
    return dest


def resolve_manifest_asset_path(
    *,
    assets_root: Path,
    local_asset_path: str,
    require_exists: bool = True,
) -> Path:
    """Governed resolver for every asset path read from a Manifest.

    ``local_asset_path`` may be ``assets/...`` or a basename; it must resolve to a
    regular file beneath ``assets_root`` (no absolute paths, no ``..``, no symlink).
    Symlinks are rejected even when the final target remains inside Assets.
    """
    raw = (local_asset_path or "").strip()
    if not raw:
        raise DiscoveryError("fs", "missing_source_asset", "empty local_asset_path")
    if Path(raw).is_absolute() or raw.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", raw):
        raise DiscoveryError("fs", "asset_path_absolute", f"absolute path rejected: {raw}")
    parts = Path(raw.replace("\\", "/")).parts
    if any(p == ".." for p in parts):
        raise DiscoveryError("fs", "asset_path_escape", f"traversal rejected: {raw}")
    if parts and parts[0] == "assets":
        parts = parts[1:]
    if not parts:
        raise DiscoveryError("fs", "missing_source_asset", "empty path under assets/")
    if any(p == ".." for p in parts):
        raise DiscoveryError("fs", "asset_path_escape", f"traversal rejected: {raw}")

    assets_root = assets_root.resolve()
    candidate = assets_root.joinpath(*parts)
    return inspect_local_asset_nofollow(candidate, assets_root=assets_root, require_exists=require_exists)


def inspect_local_asset_nofollow(
    path: Path,
    *,
    assets_root: Path,
    require_exists: bool = True,
) -> Path:
    """Validate a path as a regular file under assets without following symlinks.

    Never call ``open`` / ``read_bytes`` / hashing before this check succeeds.
    """
    import stat as stat_mod

    root = assets_root.resolve()
    # Lexical containment only — never Path.resolve() (follows symlinks).
    try:
        path.relative_to(root)
    except ValueError as e:
        raise DiscoveryError(
            "fs",
            "asset_path_escape",
            f"path outside assets: {path}",
        ) from e

    if not path.exists(follow_symlinks=False):
        if require_exists:
            raise DiscoveryError("fs", "missing_source_asset", f"missing {path.name}")
        return path

    try:
        st = path.lstat()
    except OSError as e:
        raise DiscoveryError("fs", "asset_path_escape", f"lstat failed: {path}") from e

    if stat_mod.S_ISLNK(st.st_mode):
        raise DiscoveryError(
            "fs",
            "unexpected_asset_symlink",
            f"symlink rejected (no-follow): {path.name}",
        )
    if stat_mod.S_ISDIR(st.st_mode):
        raise DiscoveryError("fs", "asset_path_not_file", f"not a regular file: {path.name}")
    if not stat_mod.S_ISREG(st.st_mode):
        raise DiscoveryError(
            "fs",
            "unexpected_non_regular_asset",
            f"not a regular file: {path.name}",
        )

    # Parent chain must not escape via symlinked directories
    cur = path.parent
    while True:
        try:
            cur.relative_to(root)
        except ValueError as e:
            raise DiscoveryError(
                "fs",
                "asset_path_escape",
                f"parent outside assets: {path}",
            ) from e
        if cur == root or cur == cur.parent:
            break
        try:
            pst = cur.lstat()
        except OSError as e:
            raise DiscoveryError("fs", "asset_path_escape", f"parent lstat failed: {cur}") from e
        if stat_mod.S_ISLNK(pst.st_mode):
            raise DiscoveryError(
                "fs",
                "unexpected_asset_symlink",
                f"symlinked parent rejected: {cur}",
            )
        cur = cur.parent

    return path


def iter_local_asset_files(assets_dir: Path, *, fail_closed: bool = True) -> list[Path]:
    """List regular files directly under assets/ using lstat (never follow symlinks)."""
    import stat as stat_mod

    if not assets_dir.exists():
        return []
    if not assets_dir.is_dir():
        raise DiscoveryError("fs", "unexpected_non_regular_asset", f"assets is not a directory: {assets_dir}")

    root = assets_dir.resolve()
    found: list[Path] = []
    for entry in sorted(assets_dir.iterdir(), key=lambda p: p.name):
        try:
            st = entry.lstat()
        except OSError as e:
            if fail_closed:
                raise DiscoveryError("fs", "asset_path_escape", f"lstat failed: {entry.name}") from e
            continue
        if stat_mod.S_ISLNK(st.st_mode):
            if fail_closed:
                raise DiscoveryError(
                    "fs",
                    "unexpected_asset_symlink",
                    f"symlink in assets/: {entry.name}",
                )
            continue
        if stat_mod.S_ISDIR(st.st_mode):
            if fail_closed:
                raise DiscoveryError(
                    "fs",
                    "unexpected_non_regular_asset",
                    f"nested directory in assets/: {entry.name}",
                )
            continue
        if not stat_mod.S_ISREG(st.st_mode):
            if fail_closed:
                raise DiscoveryError(
                    "fs",
                    "unexpected_non_regular_asset",
                    f"non-regular entry in assets/: {entry.name}",
                )
            continue
        # Confirm containment without following the file
        try:
            entry.resolve(strict=False).relative_to(root)
        except ValueError as e:
            raise DiscoveryError("fs", "asset_path_escape", f"outside assets: {entry.name}") from e
        # Re-check: resolve(strict=False) may still follow symlinks on some platforms for the path
        # itself — we already rejected S_ISLNK on the entry.
        found.append(entry)
    return found


def inventory_assets_by_sha(
    assets_dir: Path,
    *,
    file_sha256,
    fail_closed: bool = True,
) -> tuple[dict[str, list[str]], int]:
    """Return (sha256 → relative path names, unexpected_symlink_count).

    Hashes only after no-follow validation. Tracks *all* physical paths per SHA.
    """
    from collections import defaultdict

    by_sha: dict[str, list[str]] = defaultdict(list)
    files = iter_local_asset_files(assets_dir, fail_closed=fail_closed)
    for p in files:
        # Validated no-follow regular file — safe to hash
        digest = file_sha256(p)
        by_sha[digest].append(p.name)
    return dict(by_sha), 0
