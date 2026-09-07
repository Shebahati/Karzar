"""Safe PDF text extraction for Target Catalog sources.

Prefers the repository's existing ``pdftotext -layout`` tool when present.
Falls back to a stdlib stream decoder. Image-only / empty-text PDFs are
UNPARSED — never silently treated as a valid empty product list.

SKU extraction is derived from product-row structure, not a single broad
regex over the whole page. Dimensions, page numbers, and isolated junk
tokens are not manufacturer codes.
"""

from __future__ import annotations

import re
import subprocess
import zlib
from dataclasses import dataclass, field
from pathlib import Path

PDFTOTEXT = "pdftotext"

HEADER_HINTS = (
    "code",
    "sku",
    "page",
    "صفحه",
    "کدکالا",
    "کد محصول",
    "کد",
    "شرح",
    "description",
    "price",
    "قیمت",
    "index",
    "contents",
    "فهرست",
)
UNIT_SUFFIXES = ("mm", "cm", "kg", "in", '"', "″", "سانت", "متر")
CURRENCY_TOKENS = {
    "rial": "rial",
    "rials": "rial",
    "irr": "rial",
    "ریال": "rial",
    "toman": "toman",
    "tomans": "toman",
    "تومان": "toman",
    "irt": "toman",
}
SKU_PREFIX_JUNK = {
    "ISO",
    "DIN",
    "PAGE",
    "ROW",
    "PDF",
    "ASTM",
    "HSS",
    "HSSE",
    "UNC",
    "UNF",
    "NPT",
    "MM",
    "CM",
    "KG",
}
JUNK_TOKEN = re.compile(
    r"(?i)^(mm|cm|kg|din|hsse|hss|iso|unf|unc|page|row|pdf|ast|et|in)$"
)
NUMERIC_HYPHEN = re.compile(r"^(\d{3,5}-\d{2,5}[A-Z]{0,3})$", re.I)
LETTER_HYPHEN = re.compile(r"^([A-Z]{2,8}-[A-Z0-9]{1,16})$", re.I)
BARE_NUMERIC = re.compile(r"^(\d{4,6})$")
DIMENSION_RANGE = re.compile(r"^0-\d", re.I)
HAS_UNIT = re.compile(r"(?i)(?:mm|cm|kg|inch|in)\s*$")
COMMA_PRICE = re.compile(r"^\d{1,3}(?:,\d{3}){1,4}$")
PLAIN_PRICE = re.compile(r"^\d{4,12}$")
ZERO_PRICE = re.compile(r"^0(?:\.0+)?$")
PAGE_LINE = re.compile(r"(?i)^\s*(?:page|صفحه)\s*\d+\s*$")
ONLY_PAGE_NUM = re.compile(r"^\d{1,3}$")


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


@dataclass
class PdfRowParse:
    rows: list[dict[str, str]] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    confidence: str = "high"


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
        if std.status.startswith("unparsed"):
            return std
        return via_cli
    return std


def _clean_line(raw: str) -> str:
    return raw.replace("\u202b", "").replace("\u202c", "").replace("\xa0", " ").strip()


def _tokens(line: str) -> list[str]:
    return [t for t in re.split(r"\s+", line) if t]


def _strip_punct(token: str) -> str:
    return token.strip(".,;:()[]{}")


def _has_unit_suffix(token: str) -> bool:
    lowered = token.lower()
    return bool(HAS_UNIT.search(lowered)) or any(lowered.endswith(u) for u in UNIT_SUFFIXES)


def _is_header_line(line: str) -> bool:
    folded = re.sub(r"\s+", "", line).casefold()
    if PAGE_LINE.match(line) or ONLY_PAGE_NUM.match(line):
        return True
    hits = sum(1 for hint in HEADER_HINTS if hint in folded)
    return hits >= 2 or folded in {"code", "sku", "کد", "شرح"}


def _is_insize_code(token: str) -> bool:
    """Manufacturer code shapes observed in INSIZE product rows — not a catch-all."""
    t = _strip_punct(token).upper()
    if not t or JUNK_TOKEN.match(t) or _has_unit_suffix(t):
        return False
    if DIMENSION_RANGE.match(t):
        return False
    if NUMERIC_HYPHEN.fullmatch(t):
        return True
    if LETTER_HYPHEN.fullmatch(t):
        prefix = t.split("-", 1)[0]
        return prefix not in SKU_PREFIX_JUNK
    if BARE_NUMERIC.fullmatch(t):
        n = int(t)
        if 1900 <= n <= 2100:
            return False
        return True
    return False


def _is_generic_code(token: str) -> bool:
    t = _strip_punct(token).upper()
    if not t or JUNK_TOKEN.match(t) or _has_unit_suffix(t) or DIMENSION_RANGE.match(t):
        return False
    if NUMERIC_HYPHEN.fullmatch(t):
        return True
    if LETTER_HYPHEN.fullmatch(t):
        return t.split("-", 1)[0] not in SKU_PREFIX_JUNK
    return False


def _leading_sku(tokens: list[str], predicate) -> tuple[str | None, int]:
    """SKU lives in the leading product-row cells, not in mid-line dimensions."""
    for idx, token in enumerate(tokens[:3]):
        if predicate(token):
            return _strip_punct(token), idx
    return None, -1


def _currency_from_tokens(tokens: list[str], default: str | None) -> str | None:
    for token in tokens:
        key = _strip_punct(token).lower()
        if key in CURRENCY_TOKENS:
            return CURRENCY_TOKENS[key]
        if token in {"تومان", "ریال"}:
            return CURRENCY_TOKENS[token]
    line = " ".join(tokens)
    lowered = line.lower()
    if "تومان" in line or "toman" in lowered:
        return "toman"
    if "ریال" in line or "rial" in lowered:
        return "rial"
    return default


def _price_from_tokens(tokens: list[str], sku_idx: int) -> str:
    """Price is a trailing money-like cell. Dimensions and page numbers are ignored."""
    candidates: list[str] = []
    for idx, token in enumerate(tokens):
        if idx == sku_idx:
            continue
        raw = _strip_punct(token).replace("٬", ",")
        if _has_unit_suffix(raw):
            continue
        if ZERO_PRICE.match(raw):
            # Accept zero only in a trailing/price-column position.
            if idx >= max(sku_idx + 1, len(tokens) - 3):
                candidates.append("0")
            continue
        if COMMA_PRICE.match(raw) or PLAIN_PRICE.match(raw):
            candidates.append(raw)
    if not candidates:
        return ""
    return candidates[-1]


def _row_dict(sku: str, line_no: int, line: str, price: str, currency: str | None) -> dict[str, str]:
    return {
        "CODE": sku,
        "sku": sku,
        "price": price,
        "currency": currency or "",
        "__source_row": str(line_no),
        "__source_line": line[:200],
    }


def extract_insize_product_rows(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    """INSIZE product-list rows: leading manufacturer code, ignore ranges/pages."""
    parsed = PdfRowParse()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line):
            if line and not _is_header_line(line):
                parsed.rejected.append({"line": str(line_no), "reason": "empty", "text": line[:120]})
            continue
        tokens = _tokens(line)
        sku, sku_idx = _leading_sku(tokens, _is_insize_code)
        if not sku:
            if any(ch.isdigit() for ch in line) and not PAGE_LINE.match(line):
                parsed.rejected.append(
                    {"line": str(line_no), "reason": "no_insize_code_in_leading_cells", "text": line[:120]}
                )
            continue
        # Bare 4-digit codes need product-row context (description text), except 5–6 digits.
        if BARE_NUMERIC.fullmatch(_strip_punct(sku)) and len(_strip_punct(sku)) == 4:
            has_desc = any(
                re.search(r"[A-Za-z\u0600-\u06FF]", t) and not _is_insize_code(t)
                for t in tokens
            )
            if not has_desc and len(tokens) > 1:
                parsed.rejected.append(
                    {"line": str(line_no), "reason": "bare_4digit_without_description", "text": line[:120]}
                )
                continue
        currency = _currency_from_tokens(tokens, default_currency)
        price = _price_from_tokens(tokens, sku_idx)
        parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
    if parsed.rows and len(parsed.rejected) > len(parsed.rows) * 3:
        parsed.confidence = "low"
    elif parsed.rows:
        parsed.confidence = "high"
    else:
        parsed.confidence = "none"
    return parsed


def extract_generic_sku_price_rows(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    """TERMA/DASQUA/DCOIL-style tables: SKU in leading cells, price in a money cell."""
    parsed = PdfRowParse()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line):
            continue
        tokens = _tokens(line)
        sku, sku_idx = _leading_sku(tokens, _is_generic_code)
        if not sku:
            if any(ch.isdigit() for ch in line) and not PAGE_LINE.match(line):
                parsed.rejected.append(
                    {"line": str(line_no), "reason": "no_sku_in_leading_cells", "text": line[:120]}
                )
            continue
        currency = _currency_from_tokens(tokens, default_currency)
        price = _price_from_tokens(tokens, sku_idx)
        parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
    if not parsed.rows:
        parsed.confidence = "none"
    elif len(parsed.rows) < 5 and len(parsed.rejected) >= len(parsed.rows):
        parsed.confidence = "low"
    else:
        parsed.confidence = "high"
    return parsed


def extract_pdf_rows(
    text: str,
    *,
    sku_kind: str = "generic",
    default_currency: str | None = None,
) -> list[dict[str, str]]:
    """Turn PDF text into sparse row dicts. Never invent SKUs."""
    parsed = extract_pdf_row_parse(text, sku_kind=sku_kind, default_currency=default_currency)
    return parsed.rows


def extract_pdf_row_parse(
    text: str,
    *,
    sku_kind: str = "generic",
    default_currency: str | None = None,
) -> PdfRowParse:
    if sku_kind == "insize":
        return extract_insize_product_rows(text, default_currency=default_currency)
    return extract_generic_sku_price_rows(text, default_currency=default_currency)
