"""URL classification and safe local storage scanning (IMG-02A-01)."""

from __future__ import annotations

import hashlib
import os
import re
import stat as stat_mod
import warnings
from pathlib import Path
from urllib.parse import unquote, urlparse, urlunparse

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

O_RDONLY = getattr(os, "O_RDONLY", 0)
O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

_REJECTED_STORAGE_STATUSES = frozenset(
    {"symlink_rejected", "non_regular_rejected", "path_rejected"}
)

_WIN_DRIVE_RE = re.compile(r"^[A-Za-z]:([\\/]|$)")
_NUL_RE = re.compile(r"\x00")


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


def assert_no_symlink_ancestors(path: Path, *, label: str) -> None:
    """Reject when any path component (including the leaf) is a symlink."""
    if not path.is_absolute():
        raise AuditError("path", f"{label} must be absolute: {path}")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            st = current.lstat()
        except OSError as e:
            raise AuditError("path", f"{label} lstat failed at {current}") from e
        if stat_mod.S_ISLNK(st.st_mode):
            raise AuditError("path", f"{label} has symlink ancestor: {current}")


def assert_real_directory_no_symlink(path: Path, *, label: str) -> Path:
    assert_no_symlink_ancestors(path, label=label)
    try:
        st = path.lstat()
    except OSError as e:
        raise AuditError("path", f"{label} lstat failed: {path}") from e
    if stat_mod.S_ISLNK(st.st_mode):
        raise AuditError("path", f"{label} must not be a symlink: {path}")
    if not stat_mod.S_ISDIR(st.st_mode):
        raise AuditError("path", f"{label} must be a real directory: {path}")
    return path


def assert_disjoint_output_storage(output_dir: Path, storage_root: Path) -> None:
    """Reject when output and storage roots overlap or nest."""
    try:
        out_r = output_dir.resolve()
        stor_r = storage_root.resolve()
    except OSError as e:
        raise AuditError("path", f"cannot resolve output/storage paths: {e}") from e
    if out_r == stor_r:
        raise AuditError("path", "output-dir must not equal storage-root")
    try:
        out_r.relative_to(stor_r)
        raise AuditError("path", "output-dir must not be inside storage-root")
    except ValueError:
        pass
    try:
        stor_r.relative_to(out_r)
        raise AuditError("path", "storage-root must not be inside output-dir")
    except ValueError:
        pass


def assert_output_dir(path: Path, *, repository_root: Path, storage_root: Path | None = None) -> Path:
    assert_real_directory_no_symlink(path, label="output-dir")
    if storage_root is not None:
        assert_disjoint_output_storage(path, storage_root)
    try:
        path.resolve().relative_to(repository_root.resolve())
        raise AuditError("path", "output-dir must be outside the repository")
    except ValueError:
        pass
    try:
        entries = list(os.scandir(path))
    except OSError as e:
        raise AuditError("path", f"cannot scan output-dir: {e}") from e
    if entries:
        raise AuditError("path", "output-dir must be empty")
    return path


def prepare_output_dir(
    path: Path,
    *,
    repository_root: Path,
    storage_root: Path | None = None,
) -> Path:
    """Create output dir if absent; then validate empty + outside repo + no symlink."""
    if not path.is_absolute():
        raise AuditError("path", f"output-dir must be absolute: {path}")
    if path.exists():
        if path.is_symlink():
            raise AuditError("path", f"output-dir must not be a symlink: {path}")
    else:
        path.mkdir(parents=True, exist_ok=False)
    return assert_output_dir(path, repository_root=repository_root, storage_root=storage_root)


def _netloc_without_userinfo(parsed) -> str:  # type: ignore[no-untyped-def]
    host = parsed.hostname or ""
    port = parsed.port
    if port is None:
        return host
    default = (parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)
    if default:
        return host
    return f"{host}:{port}"


def _rebuild_sanitized(parsed) -> str:  # type: ignore[no-untyped-def]
    netloc = _netloc_without_userinfo(parsed)
    return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def _looks_like_abs_fs(path: str) -> bool:
    if path.startswith("//") or path.startswith("\\\\"):
        return True
    if _WIN_DRIVE_RE.match(path):
        return True
    return False


def _find_exact_public_marker(path: str) -> int | None:
    norm = path.replace("\\", "/")
    idx = norm.find(PUBLIC_PATH_MARKER)
    if idx < 0:
        return None
    return idx


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

    idx = _find_exact_public_marker(decoded)
    if idx is None:
        return None, ["missing_public_path_marker"]
    rest = decoded[idx + len(PUBLIC_PATH_MARKER) :].lstrip("/")
    if not rest:
        return None, ["empty_relative_after_marker"]

    parts = [p for p in rest.split("/") if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None, ["path_traversal_rejected"]
    if any(_WIN_DRIVE_RE.match(p) for p in parts):
        return None, ["windows_drive_rejected"]

    rel = "/".join(parts)
    candidate = storage_root.joinpath(*parts)
    try:
        root_lex = os.path.abspath(str(storage_root))
        cand_lex = os.path.abspath(str(candidate))
        if not (cand_lex == root_lex or cand_lex.startswith(root_lex + os.sep)):
            return None, ["path_outside_storage_root"]
    except Exception:
        return None, ["path_outside_storage_root"]

    return rel, reasons


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

    query_present = bool(parsed.query or parsed.fragment)
    sanitized_url = _rebuild_sanitized(parsed)
    scheme = (parsed.scheme or "").lower()
    path = (parsed.path or "").replace("\\", "/")
    stripped = raw.strip()
    host = parsed.hostname

    if _WIN_DRIVE_RE.match(stripped) or scheme == "file":
        return UrlClassification(
            url_kind="unsupported_scheme",
            sanitized_url=sanitized_url,
            url_host=host,
            url_path=path,
            query_present=query_present,
            reason_codes=["unsupported_scheme", "absolute_filesystem_path"],
        )

    if scheme in {"http", "https"}:
        if _find_exact_public_marker(path) is not None:
            mapped, map_reasons = map_static_path_to_relative(path, storage_root=storage_root)
            reasons.extend(map_reasons)
            return UrlClassification(
                url_kind="internal_static_absolute",
                sanitized_url=sanitized_url,
                url_host=host,
                url_path=path,
                query_present=query_present,
                mapped_relative_path=mapped,
                reason_codes=reasons,
            )
        kind = "external_https" if scheme == "https" else "external_http"
        return UrlClassification(
            url_kind=kind,
            sanitized_url=sanitized_url,
            url_host=host,
            url_path=path,
            query_present=query_present,
            reason_codes=["remote_unverified"],
        )

    if scheme:
        return UrlClassification(
            url_kind="unsupported_scheme",
            sanitized_url=sanitized_url,
            url_host=host,
            url_path=path,
            query_present=query_present,
            reason_codes=["unsupported_scheme"],
        )

    if not path and stripped:
        path = stripped.split("?", 1)[0].split("#", 1)[0].replace("\\", "/")
        query_present = "?" in stripped or "#" in stripped
        sanitized_url = path

    if path.startswith("/"):
        kind = "internal_static_absolute"
    else:
        kind = "internal_static_relative"
        if "static/uploads/products/" in path:
            path = "/" + path.lstrip("/")

    norm_path = path.replace("\\", "/")
    if _find_exact_public_marker(norm_path) is None:
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


def _open_regular_nofollow(path: Path) -> int:
    return os.open(str(path), O_RDONLY | O_NOFOLLOW)


def _validate_path_components_lstat(storage_root: Path, relative_path: str) -> StorageEntry | None:
    """Validate each component under storage_root with lstat; return rejection or None."""
    parts = [p for p in relative_path.split("/") if p]
    current = storage_root
    rel_so_far: list[str] = []
    for part in parts:
        rel_so_far.append(part)
        child = current / part
        try:
            st = child.lstat()
        except OSError:
            return None
        if stat_mod.S_ISLNK(st.st_mode):
            return StorageEntry(
                relative_path="/".join(rel_so_far),
                status="symlink_rejected",
                reason_codes=["symlink_rejected"],
            )
        if not (stat_mod.S_ISDIR(st.st_mode) or stat_mod.S_ISREG(st.st_mode)):
            return StorageEntry(
                relative_path="/".join(rel_so_far),
                status="non_regular_rejected",
                reason_codes=["non_regular_rejected"],
            )
        current = child
    return None


def inspect_regular_file(path: Path, *, relative_path: str) -> StorageEntry:
    """Hash + metadata for a validated regular file (no symlink)."""
    try:
        fd = _open_regular_nofollow(path)
    except OSError:
        return StorageEntry(
            relative_path=relative_path,
            status="path_rejected",
            reason_codes=["open_nofollow_failed"],
        )
    try:
        try:
            st = os.fstat(fd)
        except OSError:
            return StorageEntry(
                relative_path=relative_path,
                status="path_rejected",
                reason_codes=["fstat_failed"],
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
        try:
            with os.fdopen(os.dup(fd), "rb") as f:
                head = f.read(MAX_SIGNATURE_READ)
        except OSError:
            return StorageEntry(
                relative_path=relative_path,
                status="path_rejected",
                byte_size=byte_size,
                reason_codes=["read_failed"],
            )

        sha = _stream_sha256_fd(fd)
        mime, fmt = (None, None)
        width = height = None
        decode_status = "not_image"
        status = "regular_non_image"

        if mime_pair := detect_signature(head):
            mime, fmt = mime_pair
        if mime:
            status = "regular_image"
            decode_status = "ok"
            try:
                from PIL import Image, ImageFile

                Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
                ImageFile.LOAD_TRUNCATED_IMAGES = False
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(path) as im:
                        im.verify()
                    with Image.open(path) as im2:
                        width, height = int(im2.width), int(im2.height)
                        im2.load()
            except Image.DecompressionBombError:
                status = "decode_failed"
                decode_status = "decode_failed"
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
    finally:
        os.close(fd)


def _stream_sha256_fd(fd: int) -> str | None:
    h = hashlib.sha256()
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), "rb") as f:
            while True:
                chunk = f.read(MAX_HASH_STREAM_CHUNK)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _stream_sha256(path: Path) -> str | None:
    try:
        fd = _open_regular_nofollow(path)
    except OSError:
        return None
    try:
        return _stream_sha256_fd(fd)
    finally:
        os.close(fd)


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


def _nearest_rejected_ancestor(
    relative_path: str,
    storage_index: dict[str, StorageEntry],
) -> StorageEntry | None:
    parts = [p for p in relative_path.split("/") if p]
    for end in range(len(parts), 0, -1):
        prefix = "/".join(parts[:end])
        entry = storage_index.get(prefix)
        if entry is not None and entry.status in _REJECTED_STORAGE_STATUSES:
            return entry
    return None


def _meta_from_storage_entry(relative_path: str, e: StorageEntry) -> FileMeta:
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


def file_meta_for_mapped_path(
    storage_root: Path,
    relative_path: str | None,
    *,
    storage_index: dict[str, StorageEntry] | None = None,
    allow_filesystem_fallback: bool = True,
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

    if storage_index is not None:
        if relative_path in storage_index:
            return _meta_from_storage_entry(relative_path, storage_index[relative_path])
        rejected = _nearest_rejected_ancestor(relative_path, storage_index)
        if rejected is not None:
            return FileMeta(
                local_exists=False,
                local_relative_path=relative_path,
                local_entry_status=rejected.status,
                byte_size=None,
                sha256=None,
                detected_format=None,
                mime_type=None,
                width=None,
                height=None,
                decode_status=None,
            )
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

    if not allow_filesystem_fallback:
        return FileMeta(
            local_exists=None,
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

    component_reject = _validate_path_components_lstat(storage_root, relative_path)
    if component_reject is not None:
        return FileMeta(
            local_exists=False,
            local_relative_path=relative_path,
            local_entry_status=component_reject.status,
            byte_size=None,
            sha256=None,
            detected_format=None,
            mime_type=None,
            width=None,
            height=None,
            decode_status=None,
        )

    path = storage_root.joinpath(*relative_path.split("/"))
    try:
        st = path.lstat()
    except OSError:
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
    if stat_mod.S_ISLNK(st.st_mode):
        return FileMeta(
            local_exists=False,
            local_relative_path=relative_path,
            local_entry_status="symlink_rejected",
            byte_size=None,
            sha256=None,
            detected_format=None,
            mime_type=None,
            width=None,
            height=None,
            decode_status=None,
        )
    if not stat_mod.S_ISREG(st.st_mode):
        return FileMeta(
            local_exists=False,
            local_relative_path=relative_path,
            local_entry_status="non_regular_rejected",
            byte_size=None,
            sha256=None,
            detected_format=None,
            mime_type=None,
            width=None,
            height=None,
            decode_status=None,
        )
    e = inspect_regular_file(path, relative_path=relative_path)
    return _meta_from_storage_entry(relative_path, e)
