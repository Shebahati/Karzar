"""Safe PDF text extraction for Target Catalog sources.

Prefers the repository's existing ``pdftotext -layout`` tool when present.
Falls back to a stdlib stream decoder. Image-only / empty-text PDFs are
UNPARSED — never silently treated as a valid empty product list.
"""

from __future__ import annotations

import re
import subprocess
import zlib
from dataclasses import dataclass
from pathlib import Path

# Reuse the same CLI already used by scripts/parse_price_list_pdfs.py.
PDFTOTEXT = "pdftotext"


@dataclass
class PdfExtract:
    path: str
    text: str
    status: str  # ok | unparsed_image | unparsed_empty | missing | error
    method: str
    page_count: int | None = None
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "ok" and bool(self.text.strip())


def _unescape_pdf_literal(raw: str) -> str:
    out = raw.replace(r"\n", "\n").replace(r"\r", "\r").replace(r"\t", "\t")
    out = out.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")
    return out


def _strings_from_content(payload: bytes) -> str:
    try:
        s = payload.decode("latin-1", errors="replace")
    except Exception:
        return ""
    chunks: list[str] = []
    for match in re.finditer(r"\((?:\\.|[^\\)])*\)", s):
        chunks.append(_unescape_pdf_literal(match.group(0)[1:-1]))
    for match in re.finditer(r"<([0-9A-Fa-f\s]+)>", s):
        hexes = re.sub(r"\s+", "", match.group(1))
        if len(hexes) % 2:
            continue
        try:
            chunks.append(bytes.fromhex(hexes).decode("latin-1", errors="replace"))
        except ValueError:
            continue
    return "\n".join(c for c in chunks if c.strip())


def _inflate_stream(payload: bytes) -> bytes:
    for candidate in (payload, payload.lstrip(b"\r\n")):
        try:
            return zlib.decompress(candidate)
        except zlib.error:
            continue
    return payload


def extract_pdf_stdlib(path: Path) -> PdfExtract:
    data = path.read_bytes()
    if not data.startswith(b"%PDF"):
        return PdfExtract(str(path), "", "error", "stdlib", error="not_a_pdf")
    page_count = len(re.findall(rb"/Type\s*/Page(?![s])", data))
    has_image = b"/Image" in data or b"/Subtype /Image" in data
    texts: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        payload = _inflate_stream(match.group(1))
        piece = _strings_from_content(payload)
        if piece.strip():
            texts.append(piece)
    text = "\n".join(texts).strip()
    if text:
        return PdfExtract(str(path), text, "ok", "stdlib", page_count=page_count or None)
    if has_image:
        return PdfExtract(
            str(path),
            "",
            "unparsed_image",
            "stdlib",
            page_count=page_count or None,
            error="image_only_or_scanned_pdf_requires_ocr_or_manual_extraction",
        )
    return PdfExtract(
        str(path),
        "",
        "unparsed_empty",
        "stdlib",
        page_count=page_count or None,
        error="no_extractable_text",
    )


def extract_pdf_pdftotext(path: Path) -> PdfExtract | None:
    try:
        result = subprocess.run(
            [PDFTOTEXT, "-layout", str(path), "-"],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        err = (result.stderr or b"").decode("utf-8", errors="replace")[:300]
        return PdfExtract(str(path), "", "error", "pdftotext", error=err or "pdftotext_failed")
    text = (result.stdout or b"").decode("utf-8", errors="replace")
    if text.strip():
        return PdfExtract(str(path), text, "ok", "pdftotext")
    return PdfExtract(
        str(path),
        "",
        "unparsed_empty",
        "pdftotext",
        error="pdftotext_empty",
    )


def extract_pdf_text(path: Path) -> PdfExtract:
    path = Path(path)
    if not path.is_file():
        return PdfExtract(str(path), "", "missing", "none", error="file_missing")
    via_cli = extract_pdf_pdftotext(path)
    if via_cli is not None and via_cli.ok:
        return via_cli
    std = extract_pdf_stdlib(path)
    if std.ok:
        return std
    if via_cli is not None and via_cli.status != "ok":
        # pdftotext ran but empty; prefer image/empty classification from stdlib bytes
        if std.status.startswith("unparsed"):
            return std
        return via_cli
    return std


# Conservative manufacturer-code shapes. Do not strip trailing letters.
INSIZE_SKU_RE = re.compile(r"(?<![A-Z0-9])(\d{3,4}-\d{2,4}[A-Z]{0,2})(?![A-Z0-9-])")
GENERIC_SKU_RE = re.compile(
    r"(?<![A-Z0-9])([A-Z]{1,6}-?[A-Z0-9]{2,20}|\d{3,5}-\d{2,5}[A-Z]{0,3})(?![A-Z0-9-])"
)
PRICE_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3}){1,4}|\d{4,12})(?![\d.])")
JUNK = re.compile(
    r"(?i)^(mm|cm|kg|din|hsse|hss|iso|unf|unc|page|row|pdf|ast|et)$"
)


def _sku_re(kind: str) -> re.Pattern[str]:
    if kind == "insize":
        return INSIZE_SKU_RE
    return GENERIC_SKU_RE


def extract_pdf_rows(
    text: str,
    *,
    sku_kind: str = "generic",
    default_currency: str | None = None,
) -> list[dict[str, str]]:
    """Turn PDF text into sparse row dicts. Never invent SKUs."""
    pattern = _sku_re(sku_kind)
    rows: list[dict[str, str]] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.replace("\u202b", "").replace("\u202c", "").strip()
        if not line:
            continue
        skus = [m.group(1) for m in pattern.finditer(line) if not JUNK.match(m.group(1))]
        if not skus:
            continue
        currency = default_currency
        lowered = line.lower()
        if "تومان" in line or "toman" in lowered:
            currency = "toman"
        elif "ریال" in line or "rial" in lowered:
            currency = "rial"
        prices = [m.group(1) for m in PRICE_RE.finditer(line)]
        price_raw = prices[-1] if prices else ""
        for sku in dict.fromkeys(skus):
            rows.append(
                {
                    "CODE": sku,
                    "sku": sku,
                    "price": price_raw,
                    "currency": currency or "",
                    "__source_row": str(line_no),
                    "__source_line": line[:200],
                }
            )
    return rows
