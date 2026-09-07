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
    "JAW",
    "JAWS",
    "SHORE",
    "WTG",
}
INSIZE_PREFIX_JUNK = SKU_PREFIX_JUNK - {"ISO"}
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
PAGE_LINE = re.compile(
    r"(?i)^\s*(?:page|صفحه)\s*\d+(?:\s+(?:of|از)\s+\d+)?\s*$"
)
ONLY_PAGE_NUM = re.compile(r"^\d{1,3}$")
INCOMPLETE_PRICE = re.compile(r"(?<!\d),\d{3}\b")
RANGE_MARK = {"-", "–", "—"}


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
    # pdftotext empty means scanned/image-only. Do not promote binary fragments.
    if via_cli is not None and via_cli.status.startswith("unparsed"):
        return via_cli
    std = extract_pdf_stdlib(path)
    if std.ok:
        return std
    if via_cli is not None and via_cli.status != "ok":
        if std.status.startswith("unparsed"):
            return std
        return via_cli
    return std


_BIDI_RE = re.compile(r"[\u200e\u200f\u202a-\u202e\u2066-\u2069]")
INSIZE_CODE = re.compile(
    r"^(?:"
    r"[A-Z]{2,8}(?:-[A-Z0-9]{1,16}){1,2}"
    r"|"
    r"\d{3,5}-[A-Z0-9]{1,12}"
    r"|"
    r"\d{4,6}"
    r")$",
    re.I,
)
INSIZE_GLUED = re.compile(
    r"^("
    r"[A-Z]{2,8}(?:-[A-Z0-9]{1,16}){1,2}"
    r"|"
    r"\d{3,5}-[A-Z0-9]{1,12}"
    r")",
    re.I,
)
TERMA_SKU = re.compile(r"^[A-Z]{2,10}\d{1,4}[A-Z]{0,3}(?:-\d{1,5}[A-Z]{0,3})?$", re.I)
DASQUA_SKU = re.compile(r"^\d{3,5}-\d{3,5}(?:-[A-Z])?$", re.I)
DCOIL_SKU = re.compile(
    r"d\.coil\s*([A-Z0-9]+(?:[./][A-Z0-9]+)*(?:-\d+(?:\.\d+)?)?(?:-[A-Z0-9.]+)?)",
    re.I,
)
DOT_THOUSANDS = re.compile(r"^\d{1,3}(?:\.\d{3}){2,4}$")
COMMA_MONEY = re.compile(r"\d{1,3}(?:,\d{3})+")
ROW_INDEX = re.compile(r"^\d{1,4}$")


def _clean_line(raw: str) -> str:
    line = _BIDI_RE.sub("", raw).replace("\xa0", " ")
    return re.sub(r"[ \t]+", " ", line).strip()


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


def _is_range_endpoint(tokens: list[str], idx: int) -> bool:
    """True for the right-hand number in ``50 - 1000``, not a leading dash cell."""
    if idx <= 0 or tokens[idx - 1] not in RANGE_MARK:
        return False
    if idx < 2:
        return False
    left = _strip_punct(tokens[idx - 2])
    right = _strip_punct(tokens[idx])
    return bool(re.fullmatch(r"\d+(?:[./]\d+)?", left) and re.match(r"\d+", right))


def _has_price_signal(line: str) -> bool:
    return bool(COMMA_MONEY.search(line) or INCOMPLETE_PRICE.search(line))


def _is_price_and_row_index(tokens: list[str]) -> bool:
    if len(tokens) != 2 or not ROW_INDEX.fullmatch(tokens[1]):
        return False
    raw = _strip_punct(tokens[0]).replace("٬", ",")
    return bool(COMMA_PRICE.match(raw) or COMMA_MONEY.search(tokens[0]) or INCOMPLETE_PRICE.search(tokens[0]))


def _insize_code_from_token(token: str, *, allow_bare: bool) -> str | None:
    """Code-column shapes from لیست محصولات.pdf — not a page-wide catch-all."""
    t = _strip_punct(token)
    if not t or t in {"-", "–"} or JUNK_TOKEN.match(t):
        return None
    if re.fullmatch(r"0-\d+", t):
        return None
    glued = INSIZE_GLUED.match(t)
    if glued:
        rest = t[len(glued.group(1)) :]
        if rest and not re.match(r"[A-Z0-9-]", rest, re.I):
            code = glued.group(1)
            if code.split("-", 1)[0].upper() not in INSIZE_PREFIX_JUNK:
                return code
    if _has_unit_suffix(t):
        return None
    if INSIZE_CODE.fullmatch(t):
        prefix = t.split("-", 1)[0].upper()
        if prefix in INSIZE_PREFIX_JUNK:
            return None
        if re.fullmatch(r"\d{4,6}", t):
            if not allow_bare:
                return None
            n = int(t)
            if 1900 <= n <= 2100:
                return None
        return t
    return None


def _is_insize_code(token: str) -> bool:
    return _insize_code_from_token(token, allow_bare=True) is not None


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
        if token in {"تومان", "ریال", "﷼"}:
            return "toman" if token == "تومان" else "rial"
    line = " ".join(tokens)
    lowered = line.lower()
    if "تومان" in line or "toman" in lowered:
        return "toman"
    if "ریال" in line or "rial" in lowered or "﷼" in line:
        return "rial"
    return default


def _dotted_or_comma_price(tokens: list[str], sku_idx: int = -1) -> str:
    dotted: list[str] = []
    comma: list[str] = []
    zeros: list[str] = []
    for idx, token in enumerate(tokens):
        if idx == sku_idx:
            continue
        if _is_range_endpoint(tokens, idx):
            continue
        raw = _strip_punct(token).replace("٬", ",")
        if _has_unit_suffix(raw):
            continue
        if ZERO_PRICE.match(raw):
            zeros.append("0")
            continue
        if DOT_THOUSANDS.match(raw):
            dotted.append(raw.replace(".", ""))
            continue
        if COMMA_PRICE.match(raw) or PLAIN_PRICE.match(raw):
            comma.append(raw)
    if dotted:
        return dotted[0]
    if comma:
        return comma[-1]
    if zeros:
        return "0"
    return ""


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


def _insize_sku_from_table_tokens(tokens: list[str]) -> tuple[str | None, int]:
    """SKU is the manufacturer code immediately before the trailing row index.

    Range endpoints such as ``50 - 1000`` are not codes. Bare numerics are
    accepted only when they are the code cell, not a dimension.
    """
    last = len(tokens) - 1
    scan_from = last - 1 if tokens and ROW_INDEX.fullmatch(tokens[-1]) else last
    for idx in range(scan_from, -1, -1):
        if _is_range_endpoint(tokens, idx):
            continue
        sku = _insize_code_from_token(tokens[idx], allow_bare=False)
        if sku:
            return sku, idx
    idx = scan_from
    if idx >= 0 and not _is_range_endpoint(tokens, idx):
        sku = _insize_code_from_token(tokens[idx], allow_bare=True)
        if sku:
            return sku, idx
    return None, -1


def _leading_insize_sku(tokens: list[str]) -> tuple[str | None, int]:
    for idx, token in enumerate(tokens[:3]):
        if _is_range_endpoint(tokens, idx):
            continue
        sku = _insize_code_from_token(token, allow_bare=True)
        if sku:
            return sku, idx
    return None, -1


def extract_insize_product_rows(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    """INSIZE لیست محصولات.pdf: RTL table, manufacturer code before the row index.

    Fixture PDFs without that table shape still accept a leading code cell.
    Other-brand dash codes and page/dimension tokens are not SKUs.
    Zero or incomplete prices still confer membership.
    """
    parsed = PdfRowParse()
    pending: dict[str, str] | None = None

    def flush_pending() -> None:
        nonlocal pending
        if pending:
            parsed.rows.append(pending)
            pending = None

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line):
            continue
        tokens = _tokens(line)
        if pending and _is_price_and_row_index(tokens):
            pending["price"] = _strip_punct(tokens[0]).replace("٬", ",")
            if pending["price"].startswith(","):
                pending["price"] = ""
            parsed.rows.append(pending)
            pending = None
            continue
        flush_pending()
        sku: str | None = None
        sku_idx = -1
        trailing_index = bool(tokens) and ROW_INDEX.fullmatch(tokens[-1])
        table_row = trailing_index and (
            _has_price_signal(line)
            or any(_insize_code_from_token(t, allow_bare=False) for t in tokens[:-1])
        )
        if table_row:
            sku, sku_idx = _insize_sku_from_table_tokens(tokens)
            if sku is None:
                parsed.rejected.append(
                    {"line": str(line_no), "reason": "table_row_without_code_column", "text": line[:120]}
                )
                continue
        else:
            sku, sku_idx = _leading_insize_sku(tokens)
            if not sku:
                if any(ch.isdigit() for ch in line) and not PAGE_LINE.match(line):
                    parsed.rejected.append(
                        {"line": str(line_no), "reason": "no_insize_code_in_leading_cells", "text": line[:120]}
                    )
                continue
            if BARE_NUMERIC.fullmatch(_strip_punct(sku)) and len(_strip_punct(sku)) == 4:
                has_desc = any(
                    re.search(r"[A-Za-z\u0600-\u06FF]", t) and not _is_insize_code(t) for t in tokens
                )
                if not has_desc and len(tokens) > 1:
                    parsed.rejected.append(
                        {"line": str(line_no), "reason": "bare_4digit_without_description", "text": line[:120]}
                    )
                    continue
        currency = _currency_from_tokens(tokens, default_currency)
        if "تومان" in line:
            currency = "toman"
        price = _dotted_or_comma_price(tokens, sku_idx)
        if price.startswith(","):
            price = ""
        row = _row_dict(sku, line_no, line, price, currency)
        if trailing_index:
            parsed.rows.append(row)
        else:
            pending = row
    flush_pending()
    if parsed.rows and len(parsed.rejected) > len(parsed.rows) * 3:
        parsed.confidence = "low"
    elif parsed.rows:
        parsed.confidence = "high"
    else:
        parsed.confidence = "none"
    return parsed


def _terma_sku(token: str) -> str | None:
    t = _strip_punct(token)
    letters = re.match(r"^([A-Z]+)", t, re.I)
    if letters and letters.group(1).upper() in SKU_PREFIX_JUNK:
        return None
    if TERMA_SKU.fullmatch(t) and t.split("-", 1)[0].upper() not in SKU_PREFIX_JUNK:
        if re.fullmatch(r"\d+", t) or not re.search(r"\d", t):
            return None
        return t
    return None


def _dasqua_sku(token: str) -> str | None:
    t = _strip_punct(token)
    if _has_unit_suffix(t) or re.fullmatch(r"0-\d+", t):
        return None
    if DASQUA_SKU.fullmatch(t):
        return t
    return None


def extract_terma_rows(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    parsed = PdfRowParse()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line):
            continue
        tokens = _tokens(line)
        sku = None
        sku_idx = -1
        if len(tokens) >= 3 and ROW_INDEX.fullmatch(tokens[-1]):
            sku = _terma_sku(tokens[-2])
            sku_idx = len(tokens) - 2
            if sku is None:
                for idx in range(len(tokens) - 3, -1, -1):
                    sku = _terma_sku(tokens[idx])
                    if sku:
                        sku_idx = idx
                        break
        if sku is None:
            sku, sku_idx = _leading_sku(tokens, _is_generic_code)
        if not sku:
            if DOT_THOUSANDS.search(line) or COMMA_MONEY.search(line):
                parsed.rejected.append({"line": str(line_no), "reason": "no_terma_sku", "text": line[:120]})
            continue
        currency = _currency_from_tokens(tokens, default_currency)
        price = _dotted_or_comma_price(tokens, sku_idx)
        parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
    parsed.confidence = "high" if parsed.rows else "none"
    return parsed


def extract_dasqua_rows(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    parsed = PdfRowParse()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line):
            continue
        tokens = _tokens(line)
        sku = None
        sku_idx = -1
        for idx, token in enumerate(tokens[:-1] if tokens and ROW_INDEX.fullmatch(tokens[-1]) else tokens):
            found = _dasqua_sku(token)
            if found:
                sku, sku_idx = found, idx
                break
        if sku is None:
            sku, sku_idx = _leading_sku(tokens, _is_generic_code)
        if not sku:
            if COMMA_MONEY.search(line) or (tokens and tokens[0] == "0"):
                parsed.rejected.append({"line": str(line_no), "reason": "no_dasqua_sku", "text": line[:120]})
            continue
        currency = _currency_from_tokens(tokens, default_currency)
        price = _dotted_or_comma_price(tokens, sku_idx)
        if not price and tokens and tokens[0] in {"0", "0.0"}:
            price = "0"
        parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
    parsed.confidence = "high" if parsed.rows else "none"
    return parsed


def extract_dcoil_rows(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    parsed = PdfRowParse()
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line):
            continue
        normalized = re.sub(r"d\.coil(?=\S)", "d.coil ", line, flags=re.I)
        coil = re.search(r"d\.coil\s+", normalized, re.I)
        if coil:
            rest = normalized[coil.end() :]
            identity = re.split(r"\s*﷼|\s+ریال\b", rest, maxsplit=1)[0]
            identity = re.sub(r"\s+\d{1,3}(?:,\d{3})+\s*$", "", identity)
            sku = re.sub(r"\s+", " ", identity).strip(" -")
            if not sku:
                parsed.rejected.append(
                    {"line": str(line_no), "reason": "dcoil_without_identity", "text": line[:120]}
                )
                continue
            tokens = _tokens(normalized)
            currency = _currency_from_tokens(tokens, default_currency or "rial")
            price = _dotted_or_comma_price(tokens)
            if not price and re.search(r"(?:﷼|ریال)\s*0\b", normalized):
                price = "0"
            parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
            continue
        tokens = _tokens(line)
        sku, sku_idx = _leading_sku(tokens, _is_generic_code)
        if not sku:
            if COMMA_MONEY.search(line):
                parsed.rejected.append({"line": str(line_no), "reason": "no_dcoil_sku", "text": line[:120]})
            continue
        currency = _currency_from_tokens(tokens, default_currency)
        price = _dotted_or_comma_price(tokens, sku_idx)
        parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
    parsed.confidence = "high" if parsed.rows else "none"
    return parsed
    parsed = PdfRowParse()
    coil = re.compile(r"d\.coil\s*(\S+)", re.I)
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line):
            continue
        normalized = re.sub(r"d\.coil(?=\S)", "d.coil ", line, flags=re.I)
        match = coil.search(normalized)
        if match:
            sku = match.group(1).strip().rstrip("﷼")
            after = normalized[match.end() :]
            extra = re.match(r"\s+((?:UNC|UNF|G\(BSP\)|[0-9.]+D)(?:\s+[0-9.]+D)?)", after, re.I)
            if extra:
                sku = f"{sku} {extra.group(1).strip()}"
            tokens = _tokens(normalized)
            currency = _currency_from_tokens(tokens, default_currency or "rial")
            price = _dotted_or_comma_price(tokens)
            if not price and re.search(r"(?:﷼|ریال)\s*0\b", normalized):
                price = "0"
            parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
            continue
        tokens = _tokens(line)
        sku, sku_idx = _leading_sku(tokens, _is_generic_code)
        if not sku:
            if COMMA_MONEY.search(line):
                parsed.rejected.append({"line": str(line_no), "reason": "no_dcoil_sku", "text": line[:120]})
            continue
        currency = _currency_from_tokens(tokens, default_currency)
        price = _dotted_or_comma_price(tokens, sku_idx)
        parsed.rows.append(_row_dict(sku, line_no, line, price, currency))
    parsed.confidence = "high" if parsed.rows else "none"
    return parsed


GUANGLU_TRAILING_PRICE = re.compile(r"(\d{1,3}(?:,\d{3}){1,4})\s*$")


def extract_guanglu_row_parse(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    """Guanglu price list has no manufacturer SKU column.

    Embedded text is encoding-corrupted. Rendered pages show description +
    optional size + price. Identity is not a stable SKU, so membership rows
    are never emitted. Evidence is recorded on rejected lines.
    """
    del default_currency
    parsed = PdfRowParse()
    parsed.confidence = "none"
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _clean_line(raw)
        if not line or _is_header_line(line) or PAGE_LINE.match(line):
            continue
        match = GUANGLU_TRAILING_PRICE.search(line)
        if not match:
            if any(ch.isdigit() for ch in line):
                parsed.rejected.append(
                    {
                        "line": str(line_no),
                        "reason": "no_trailing_price_or_not_a_row",
                        "text": line[:160],
                        "raw_identity": line[:160],
                        "raw_price": "",
                        "price_unit": "rial_unconfirmed",
                        "decision": "reject",
                        "confidence": "low",
                    }
                )
            continue
        identity = line[: match.start()].strip()
        parsed.rejected.append(
            {
                "line": str(line_no),
                "reason": "no_manufacturer_sku_column",
                "text": line[:160],
                "raw_identity": identity[:160],
                "raw_price": match.group(1),
                "price_unit": "rial_unconfirmed",
                "decision": "reject",
                "confidence": "low",
                "manual_review_required": "true",
            }
        )
    return parsed


def extract_generic_sku_price_rows(text: str, *, default_currency: str | None = None) -> PdfRowParse:
    """Generic price tables: SKU in leading cells, money in a price cell."""
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
        price = _dotted_or_comma_price(tokens, sku_idx)
        if not price:
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
    if sku_kind == "terma":
        return extract_terma_rows(text, default_currency=default_currency)
    if sku_kind == "dasqua":
        return extract_dasqua_rows(text, default_currency=default_currency)
    if sku_kind == "dcoil":
        return extract_dcoil_rows(text, default_currency=default_currency)
    if sku_kind == "guanglu":
        return extract_guanglu_row_parse(text, default_currency=default_currency)
    parsed = extract_generic_sku_price_rows(text, default_currency=default_currency)
    if parsed.rows and parsed.confidence == "low" and len(parsed.rows) < 20:
        parsed.confidence = "low"
    return parsed
