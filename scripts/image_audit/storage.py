"""URL classification and safe local storage scanning (IMG-02A-01)."""

from __future__ import annotations

import hashlib
import os
import re
import stat as stat_mod
from pathlib import Path
from urllib.parse import unquote, urlparse

from .contracts import (
    MAX_HASH_STREAM_CHUNK,
    MAX_IMAGE_PIXELS,
    MAX_SIGNATURE_READ,
    PUBLIC_PATH_MARKER,
    AuditError,
    FileMeta,
    StorageEntry,
    UrlClassification,
)


def detect_signature(data: bytes) -> tuple[str | None, str | None]:
    if len(data) < 12:
        return None, None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None, None


def assert_real_directory_no_symlink(path: Path, *, label: str) -> Path:
    if not path.is_absolute():
        raise AuditError("path", f"{label} must be absolute: {path}")
    if path.is_symlink():
        raise AuditError("path", f"{label} must not be a symlink: {path}")
    try:
        st = path.lstat()
    except OSError as e:
        raise AuditError("path", f"{label} lstat failed: {path}") from e
    if stat_mod.S_ISLNK(st.st_mode):
        raise AuditError("path", f"{label} must not be a symlink: {path}")
    if not stat_mod.S_ISDIR(st.st_mode):
        raise AuditError("path", f"{label} must be a real directory: {path}")
    return path


def assert_output_dir(path: Path, *, repository_root: Path) -> Path:
    assert_real_directory_no_symlink(path, label="output-dir")
    try:
        path.resolve().relative_to(repository_root.resolve())
        raise AuditError("path", "output-dir must be outside the repository")
    except ValueError:
        pass  # outside repo — good
    # Must be absent-or-empty: if exists, only allow empty
    try:
        entries = list(os.scandir(path))
    except OSError as e:
        raise AuditError("path", f"cannot scan output-dir: {e}") from e
    if entries:
        raise AuditError("path", "output-dir must be empty")
    return path


def prepare_output_dir(path: Path, *, repository_root: Path) -> Path:
    """Create output dir if absent; then validate empty + outside repo + no symlink."""
    if not path.is_absolute():
        raise AuditError("path", f"output-dir must be absolute: {path}")
    if path.exists():
        if path.is_symlink():
            raise AuditError("path", f"output-dir must not be a symlink: {path}")
    else:
        path.mkdir(parents=True, exist_ok=False)
    return assert_output_dir(path, repository_root=repository_root)


_WIN_DRIVE_RE = re.compile(r"^[A-Za-z]:([\\/]|$)")
_NUL_RE = re.compile(r"\x00")


def classify_image_url(image_url: str | None, *, storage_root: Path) -> UrlClassification:
    """Classify URL and optionally map to a relative path under storage_root."""
    reasons: list[str] = []
    raw = "" if image_url is None else str(image_url)
    if not raw.strip():
        return UrlClassification(
            url_kind="empty_url",
            sanitized_url="",
            url_host=None,
            url_path=None,
            query_present=False,
            reason_codes=["empty_url"],
        )

    query_present = False
    try:
        parsed = urlparse(raw.strip())
    except Exception:
        return UrlClassification(
            url_kind="malformed_url",
            sanitized_url="",
            url_host=None,
            url_path=None,
            query_present=False,
            reason_codes=["malformed_url"],
        )

    query_present = bool(parsed.query)
    sanitized_url = _rebuild_sanitized(parsed)
    scheme = (parsed.scheme or "").lower()
    path = (parsed.path or "").replace("\\", "/")
    stripped = raw.strip()

    if _WIN_DRIVE_RE.match(stripped) or (scheme == "file"):
        return UrlClassification(
            url_kind="unsupported_scheme",
            sanitized_url=sanitized_url,
            url_host=parsed.hostname,
            url_path=path,
            query_present=query_present,
            reason_codes=["unsupported_scheme", "absolute_filesystem_path"],
        )

    if scheme in {"http"}:
        return UrlClassification(
            url_kind="external_http",
            sanitized_url=sanitized_url,
            url_host=parsed.hostname,
            url_path=path,
            query_present=query_present,
            reason_codes=["remote_unverified"],
        )
    if scheme in {"https"}:
        return UrlClassification(
            url_kind="external_https",
            sanitized_url=sanitized_url,
            url_host=parsed.hostname,
            url_path=path,
            query_present=query_present,
            reason_codes=["remote_unverified"],
        )
    if scheme:
        return UrlClassification(
            url_kind="unsupported_scheme",
            sanitized_url=sanitized_url,
            url_host=parsed.hostname,
            url_path=path,
            query_present=query_present,
            reason_codes=["unsupported_scheme"],
        )

    # No scheme: path-only internal static candidates
    if not path and stripped:
        # urlparse may put relative paths in path="" and leave netloc empty —
        # treat whole string as path when it looks like a static relative path.
        path = stripped.split("?", 1)[0].split("#", 1)[0].replace("\\", "/")
        query_present = "?" in stripped
        sanitized_url = path

    if path.startswith("/"):
        kind = "internal_static_absolute"
    else:
        kind = "internal_static_relative"
        if "static/uploads/products" in path:
            path = "/" + path.lstrip("/")

    norm_path = path.replace("\\", "/")
    if PUBLIC_PATH_MARKER.rstrip("/") not in norm_path:
        return UrlClassification(
            url_kind=kind,
            sanitized_url=sanitized_url,
            url_host=None,
            url_path=path,
            query_present=query_present,
            reason_codes=["missing_public_path_marker"],
        )

    mapped, map_reasons = map_static_path_to_relative(norm_path, storage_root=storage_root)
    reasons.extend(map_reasons)
    return UrlClassification(
        url_kind=kind,
        sanitized_url=sanitized_url if sanitized_url else norm_path,
        url_host=None,
        url_path=path,
        query_present=query_present,
        mapped_relative_path=mapped,
        reason_codes=reasons,
    )


def _rebuild_sanitized(parsed) -> str:  # type: ignore[no-untyped-def]
    from urllib.parse import urlunparse

    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _looks_like_abs_fs(path: str) -> bool:
    if path.startswith("//") or path.startswith("\\\\"):
        return True
    if _WIN_DRIVE_RE.match(path):
        return True
    return False


def map_static_path_to_relative(
    url_path: str,
    *,
    storage_root: Path,
) -> tuple[str | None, list[str]]:
    """Map `/static/uploads/products/...` to a relative path under storage_root."""
    reasons: list[str] = []
    if _NUL_RE.search(url_path):
        return None, ["nul_in_path"]
    if _WIN_DRIVE_RE.match(url_path) or _WIN_DRIVE_RE.match(unquote(url_path)):
        return None, ["windows_drive_rejected"]

    # Decode once safely
    try:
        decoded = unquote(url_path)
    except Exception:
        return None, ["url_decode_failed"]
    if _NUL_RE.search(decoded):
        return None, ["nul_in_path"]
    if "\\" in decoded:
        decoded = decoded.replace("\\", "/")
    if _looks_like_abs_fs(decoded) and not decoded.startswith("/static/"):
        return None, ["absolute_filesystem_path"]

    marker = PUBLIC_PATH_MARKER.rstrip("/")
    idx = decoded.find(marker)
    if idx < 0:
        return None, ["missing_public_path_marker"]
    rest = decoded[idx + len(marker) :].lstrip("/")
    if not rest:
        return None, ["empty_relative_after_marker"]

    # Reject traversal (plain and encoded forms already decoded)
    parts = [p for p in rest.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None, ["path_traversal_rejected"]
    if any(_WIN_DRIVE_RE.match(p) for p in parts):
        return None, ["windows_drive_rejected"]

    rel = "/".join(parts)
    # Lexical containment under storage_root without following symlinks
    candidate = storage_root.joinpath(*parts)
    try:
        # Use abspath lexical join; reject if resolve would escape — but do not follow
        root_lex = os.path.abspath(str(storage_root))
        cand_lex = os.path.abspath(str(candidate))
        if not (cand_lex == root_lex or cand_lex.startswith(root_lex + os.sep)):
            return None, ["path_outside_storage_root"]
    except Exception:
        return None, ["path_outside_storage_root"]

    return rel, reasons


def inspect_regular_file(path: Path, *, relative_path: str) -> StorageEntry:
    """Hash + metadata for a validated regular file (no symlink)."""
    try:
        st = path.lstat()
    except OSError:
        return StorageEntry(
            relative_path=relative_path,
            status="path_rejected",
            reason_codes=["lstat_failed"],
        )
    if stat_mod.S_ISLNK(st.st_mode):
        return StorageEntry(
            relative_path=relative_path,
            status="symlink_rejected",
            reason_codes=["symlink_rejected"],
        )
    if not stat_mod.S_ISREG(st.st_mode):
        return StorageEntry(
            relative_path=relative_path,
            status="non_regular_rejected",
            reason_codes=["non_regular_rejected"],
        )

    byte_size = int(st.st_size)
    sha = _stream_sha256(path)
    mime, fmt = (None, None)
    width = height = None
    decode_status = "not_image"
    status = "regular_non_image"

    try:
        with open(path, "rb") as f:
            head = f.read(MAX_SIGNATURE_READ)
        mime, fmt = detect_signature(head)
    except OSError:
        return StorageEntry(
            relative_path=relative_path,
            status="path_rejected",
            byte_size=byte_size,
            sha256=sha,
            reason_codes=["read_failed"],
        )

    if mime:
        status = "regular_image"
        decode_status = "ok"
        try:
            from PIL import Image, ImageFile

            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            ImageFile.LOAD_TRUNCATED_IMAGES = False
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im2:
                width, height = int(im2.width), int(im2.height)
                # Force load to catch decode issues
                im2.load()
        except Exception:
            status = "decode_failed"
            decode_status = "decode_failed"

    return StorageEntry(
        relative_path=relative_path,
        status=status,
        byte_size=byte_size,
        sha256=sha,
        detected_format=fmt,
        mime_type=mime,
        width=width,
        height=height,
        decode_status=decode_status,
    )


def _stream_sha256(path: Path) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(MAX_HASH_STREAM_CHUNK)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def scan_storage_tree(storage_root: Path) -> list[StorageEntry]:
    """Safe recursive scan; lexical order; no symlink follow."""
    assert_real_directory_no_symlink(storage_root, label="storage-root")
    entries: list[StorageEntry] = []

    def walk(current: Path, rel_parts: tuple[str, ...]) -> None:
        try:
            names = sorted(os.listdir(current))
        except OSError:
            entries.append(
                StorageEntry(
                    relative_path="/".join(rel_parts) if rel_parts else ".",
                    status="path_rejected",
                    reason_codes=["listdir_failed"],
                )
            )
            return
        for name in names:
            child = current / name
            child_rel = "/".join((*rel_parts, name))
            try:
                st = child.lstat()
            except OSError:
                entries.append(
                    StorageEntry(
                        relative_path=child_rel,
                        status="path_rejected",
                        reason_codes=["lstat_failed"],
                    )
                )
                continue
            if stat_mod.S_ISLNK(st.st_mode):
                entries.append(
                    StorageEntry(
                        relative_path=child_rel,
                        status="symlink_rejected",
                        reason_codes=["symlink_rejected"],
                    )
                )
                continue
            if stat_mod.S_ISDIR(st.st_mode):
                walk(child, (*rel_parts, name))
                continue
            if not stat_mod.S_ISREG(st.st_mode):
                entries.append(
                    StorageEntry(
                        relative_path=child_rel,
                        status="non_regular_rejected",
                        reason_codes=["non_regular_rejected"],
                    )
                )
                continue
            entries.append(inspect_regular_file(child, relative_path=child_rel))

    walk(storage_root, ())
    entries.sort(key=lambda e: e.relative_path)
    return entries


def file_meta_for_mapped_path(
    storage_root: Path,
    relative_path: str | None,
    *,
    storage_index: dict[str, StorageEntry] | None = None,
) -> FileMeta:
    if not relative_path:
        return FileMeta(
            local_exists=False,
            local_relative_path=None,
            local_entry_status=None,
            byte_size=None,
            sha256=None,
            detected_format=None,
            mime_type=None,
            width=None,
            height=None,
            decode_status=None,
        )
    if storage_index is not None and relative_path in storage_index:
        e = storage_index[relative_path]
        exists = e.status in {"regular_image", "regular_non_image", "decode_failed"}
        return FileMeta(
            local_exists=exists,
            local_relative_path=relative_path,
            local_entry_status=e.status,
            byte_size=e.byte_size,
            sha256=e.sha256,
            detected_format=e.detected_format,
            mime_type=e.mime_type,
            width=e.width,
            height=e.height,
            decode_status=e.decode_status,
        )

    path = storage_root.joinpath(*relative_path.split("/"))
    if not path.exists(follow_symlinks=False):
        return FileMeta(
            local_exists=False,
            local_relative_path=relative_path,
            local_entry_status=None,
            byte_size=None,
            sha256=None,
            detected_format=None,
            mime_type=None,
            width=None,
            height=None,
            decode_status=None,
        )
    e = inspect_regular_file(path, relative_path=relative_path)
    exists = e.status in {"regular_image", "regular_non_image", "decode_failed"}
    return FileMeta(
        local_exists=exists if e.status != "symlink_rejected" else False,
        local_relative_path=relative_path,
        local_entry_status=e.status,
        byte_size=e.byte_size,
        sha256=e.sha256,
        detected_format=e.detected_format,
        mime_type=e.mime_type,
        width=e.width,
        height=e.height,
        decode_status=e.decode_status,
    )
