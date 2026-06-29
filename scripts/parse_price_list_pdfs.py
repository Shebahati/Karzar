"""
Parse Insize and Dasqua price-list PDFs into reviewable CSV files.

Usage:
    python scripts/parse_price_list_pdfs.py

Outputs under data/imports/: dasqua_products.csv, insize_products.csv,
all_products.csv, import_review_summary.txt
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DASQUA = Path("/home/moahmmad/لیست قیمت داسکوا 14050212.pdf")
DEFAULT_INSIZE = Path("/home/moahmmad/3654608110343495427_57334447193566_260620_174401.pdf")
OUTPUT_DIR = PROJECT_ROOT / "data" / "imports"

SKU_RE = re.compile(r"\b(\d{3,4}-\d{3,4}[A-Z]?)\b")
PRICE_RE = re.compile(r"\b(\d{1,3}(?:,\d{3})+)\b")
ACCURACY_RE = re.compile(r"0/[\d/\"]+(?:mm)?")
SIZE_MM_RE = re.compile(
    r"0-[\d]+(?:\.\d+)?mm(?:/[\d\"./-]+)?|0-[\d]+/[\d\"]+",
    re.IGNORECASE,
)
PERSIAN_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*سانت|(\d+(?:\.\d+)?)\s*متر")

# First match wins.
CATEGORY_RULES: list[tuple[list[str], int, str, str]] = [
    (["میکروسکوپ"], 88, "میکروسکوپ", "high"),
    (["شور", "shore", "پالستیک", "الستیک"], 91, "سختی سنج لاستیک", "high"),
    (["سختی سنج"], 89, "سختی سنج", "high"),
    (["میکرومتر", "میکرومی", "میله ای", "خارج میله", "داخل میله"], 58, "انواع میکرومتر", "high"),
    (["ساعت شیطانکی"], 60, "ساعت شیطانکی", "high"),
    (["ساعت اندیکاتور", "انگشتی ساعت", "پایه ساعت", "رنیو سنج", "رنیو"], 59, "ساعت اندیکاتور", "medium"),
    (["تاکومی", "دورسنج", "کمی دیجیتال"], 59, "ساعت اندیکاتور", "medium"),
    (["ساعت"], 59, "ساعت اندیکاتور", "medium"),
    (["ارتفاع سنج", "ارتفاع"], 69, "ارتفاع سنج", "high"),
    (["zزد", "z zero", "رفرنس یاب محور", "z سنج"], 82, "Z سنج عقربه ای", "high"),
    (["تراز"], 71, "تراز صنعتی", "high"),
    (["گیج داخل سیلندر"], 63, "گیج داخل سیلندر", "high"),
    (["راپورتر", "گیج بلوک", "گیج بلاک"], 66, "راپورتر(گیج بلوک-گیج بلاک)", "high"),
    (["پیچ", "رزوه", "گیت"], 67, "انواع گیج", "medium"),
    (["گیج"], 67, "انواع گیج", "high"),
    (["سوزن دیجیتال", "سوزن"], 62, "عمق سنج", "high"),
    (["ضخامت سنج", "ضخامت"], 62, "عمق سنج", "medium"),
    (["عمق سنج", "عمق"], 62, "عمق سنج", "high"),
    (["گپ سنج", "گپ"], 78, "گپ سنج", "high"),
    (["شعاع سنج"], 70, "شعاع سنج(R)", "high"),
    (["زاویه"], 68, "زاویه سنج", "high"),
    (["زبری", "صافی سطح"], 65, "شابلون", "medium"),
    (["پرگار"], 72, "پرگار صنعتی", "high"),
    (["شابلون"], 65, "شابلون", "high"),
    (["خط کش"], 76, "خط کش", "high"),
    (["سیرکومتر"], 77, "متر", "medium"),
    (["متر"], 77, "متر", "high"),
    (["فیلر"], 73, "فیلر", "high"),
    (["گونیا"], 75, "گونیا", "high"),
    (["ترمومی", "حرارت سنج", "حرارت"], 92, "ترازو", "low"),
    (["داخیل", "داخلی", "سه فک"], 57, "انواع کولیس", "high"),
    (["ورنیه", "کولیس"], 57, "انواع کولیس", "high"),
]

CSV_FIELDS = [
    "brand",
    "brand_id",
    "sku",
    "name",
    "description",
    "category_id",
    "category_name",
    "category_confidence",
    "price_raw",
    "price_currency",
    "base_price_toman",
    "price_is_inquiry",
    "accuracy",
    "size_range",
    "size_label_fa",
    "specifications_json",
    "section_title",
    "source_file",
    "source_row_hint",
    "parse_flags",
]


@dataclass
class ProductRow:
    brand: str
    brand_id: int
    sku: str
    name: str = ""
    description: str = ""
    category_id: int | None = None
    category_name: str = ""
    category_confidence: str = "low"
    price_raw: str = ""
    price_currency: str = ""
    base_price_toman: str = ""
    price_is_inquiry: str = "false"
    accuracy: str = ""
    size_range: str = ""
    size_label_fa: str = ""
    specifications_json: str = ""
    section_title: str = ""
    source_file: str = ""
    source_row_hint: str = ""
    source_line: str = ""
    parse_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, str]:
        return {
            "brand": self.brand,
            "brand_id": str(self.brand_id),
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "category_id": str(self.category_id) if self.category_id else "",
            "category_name": self.category_name,
            "category_confidence": self.category_confidence,
            "price_raw": self.price_raw,
            "price_currency": self.price_currency,
            "base_price_toman": self.base_price_toman,
            "price_is_inquiry": self.price_is_inquiry,
            "accuracy": self.accuracy,
            "size_range": self.size_range,
            "size_label_fa": self.size_label_fa,
            "specifications_json": self.specifications_json,
            "section_title": self.section_title,
            "source_file": self.source_file,
            "source_row_hint": self.source_row_hint,
            "parse_flags": "|".join(self.parse_flags),
        }


def clean_line(text: str) -> str:
    cleaned = text.replace("\u202b", "").replace("\u202c", "").replace("\ufeff", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_section_title(title: str) -> str:
    title = clean_line(title)
    title = re.sub(r"^[\d/\".\s]+", "", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def pdf_to_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_price_number(raw: str) -> int | None:
    if not raw:
        return None
    cleaned = raw.replace(",", "").strip()
    return int(cleaned) if cleaned.isdigit() else None


def rial_to_toman(rial: int) -> int:
    return rial // 10


def suggest_category(*texts: str) -> tuple[int | None, str, str]:
    blob = " ".join(clean_line(t) for t in texts if t).lower()
    for keywords, category_id, category_name, confidence in CATEGORY_RULES:
        if any(keyword.lower() in blob for keyword in keywords):
            return category_id, category_name, confidence
    return None, "", "low"


def sku_suffix(sku: str) -> str:
    return sku.split("-")[-1].upper()


def is_sku_fragment_size(value: str, sku: str) -> bool:
    digits = re.sub(r"[^0-9]", "", value)
    suffix = re.sub(r"[^0-9]", "", sku_suffix(sku))
    return bool(digits and suffix and digits == suffix)


def extract_size_range(line: str, sku: str) -> tuple[str, str]:
    persian = ""
    pm = PERSIAN_SIZE_RE.search(line)
    if pm:
        if pm.group(1):
            persian = f"{pm.group(1)} سانت"
        elif pm.group(2):
            persian = f"{pm.group(2)} متر"

    for match in SIZE_MM_RE.findall(line):
        if is_sku_fragment_size(match, sku):
            continue
        if "mm" in match.lower() or "/" in match:
            return match, persian

    inferred = infer_size_from_sku(sku)
    if inferred:
        return inferred, persian
    return "", persian


def infer_size_from_sku(sku: str) -> str:
    match = re.search(r"-(\d{2,4})([A-Z]?)$", sku.upper())
    if not match:
        return ""
    num = int(match.group(1))
    if 25 <= num <= 2000:
        return f"0-{num}mm"
    if 1 <= num <= 24:
        return f"0-{num * 10}mm"
    return ""


def extract_accuracy(line: str) -> str:
    match = ACCURACY_RE.search(line)
    return match.group(0) if match else ""


def clean_description_text(text: str) -> str:
    text = clean_line(text)
    text = re.sub(r"0/[\d/\"]+(?:\s*mm)?", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bmm\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"[\u202a\u202c‪‬]", "", text)
    text = re.sub(r"\s+", " ", text).strip(" -|،,.")
    return text


def extract_insize_description(line: str, sku: str, section: str) -> str:
    text = clean_line(line)
    text = re.sub(rf"\b{re.escape(sku)}\b.*$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\b\d{1,3}(?:,\d{3})+\b", " ", text)
    text = clean_description_text(text)
    if len(text) >= 8:
        return text
    return clean_description_text(section)


def extract_dasqua_description(section: str, line: str) -> str:
    section = normalize_section_title(section)
    if len(section) >= 10:
        return section
    text = clean_line(line)
    text = re.sub(r"^[\d,]+\s+", "", text)
    text = re.sub(r"\b\d{3,4}-\d{3,4}[A-Z]?\b.*$", "", text)
    text = re.sub(r"0/[\d/\"]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or section


def build_name(description: str, section: str, size_range: str, size_label_fa: str, brand: str) -> str:
    base = description.strip() or normalize_section_title(section)
    parts = [base] if base else []
    size_part = size_label_fa or size_range
    if size_part and size_part not in base:
        parts.append(size_part)
    if not parts:
        parts.append(f"محصول {brand}")
    name = " — ".join(parts)
    name = re.sub(r"\s+", " ", name)
    return name[:255]


def build_specifications(accuracy: str, size_range: str, description: str) -> str:
    technical: dict[str, str] = {}
    if accuracy:
        technical["دقت"] = accuracy.replace('"', "")
    if size_range:
        technical["بازه اندازه‌گیری"] = size_range
    features: dict[str, bool | str] = {}
    desc = description.lower()
    for token, label in [
        ("ip67", "IP67"),
        ("ip65", "IP65"),
        ("ضدآب", "ضدآب"),
        ("ضد آب", "ضدآب"),
        ("دیجیتال", "دیجیتال"),
        ("شارژی", "شارژی"),
    ]:
        if token in desc:
            features[label] = True
    payload = {
        "technical_specs": [{"key": k, "value": v} for k, v in technical.items()],
        "dimensions": [],
        "features": features,
    }
    return json.dumps(payload, ensure_ascii=False)


def is_section_header(line: str) -> bool:
    if not line or len(line) < 10:
        return False
    if any(token in line for token in ("قیمت", "ردیف", "تصویر", "مشخصات کالا", "Page ")):
        return False
    if SKU_RE.search(line):
        return False
    if re.match(r"^[\d,]", line):
        return False
    keywords = (
        "کولیس", "میکرومتر", "میکرومی", "گیج", "ساعت", "تراز", "ارتفاع", "ورنیه",
        "عمق", "گپ", "زاویه", "پرگار", "دیجیتال", "ترمومی", "حرارت", "ضخامت",
        "زبری", "رنیو", "تاکومی", "دورسنج", "سوزن", "شور", "shore", "میکروسکو",
        "شعاع", "سیرکومتر", "داخیل", "داخلی", "پیچ", "رزوه", "پالستیک", "الستیک",
    )
    return any(keyword in line.lower() for keyword in keywords)


def enrich_row(row: ProductRow) -> ProductRow:
    non_price_flags = [f for f in row.parse_flags if f not in {
        "missing_price", "price_parse_failed", "inquiry_price"
    }]

    if row.description and len(row.description) < 12 and row.section_title:
        row.description = extract_dasqua_description(row.section_title, row.source_line)

    if not row.size_range:
        inferred = infer_size_from_sku(row.sku)
        if inferred:
            row.size_range = inferred
            if "size_inferred_from_sku" not in non_price_flags:
                non_price_flags.append("size_inferred_from_sku")
    elif not row.size_label_fa:
        _, persian = extract_size_range(row.source_line, row.sku)
        row.size_label_fa = persian

    if row.size_range and is_sku_fragment_size(row.size_range, row.sku):
        row.size_range = infer_size_from_sku(row.sku)
        non_price_flags.append("size_corrected")

    if not row.category_id:
        cid, cname, conf = suggest_category(
            row.description, row.section_title, row.source_line, row.name
        )
        if cid:
            row.category_id = cid
            row.category_name = cname
            row.category_confidence = conf
            non_price_flags = [f for f in non_price_flags if f != "category_unmapped"]
        else:
            row.category_id = 80
            row.category_name = "قطعات یدکی"
            row.category_confidence = "fallback"
            non_price_flags.append("category_fallback")

    row.name = build_name(
        row.description, row.section_title, row.size_range, row.size_label_fa, row.brand
    )
    row.name = clean_description_text(row.name)
    row.section_title = normalize_section_title(row.section_title)
    row.description = clean_description_text(row.description)
    row.specifications_json = build_specifications(row.accuracy, row.size_range, row.description)

    weak_names = {"کولیس دیجیتال", "میکرومی", "میکرومتر", "گیج", "ساعت"}
    if row.name.strip() in weak_names or len(row.name) < 12:
        non_price_flags.append("weak_name")

    row.parse_flags = list(dict.fromkeys([
        *non_price_flags,
        *[f for f in row.parse_flags if f in {"missing_price", "price_parse_failed", "inquiry_price"}],
    ]))
    return row


def parse_dasqua_pdf(path: Path) -> list[ProductRow]:
    text = pdf_to_text(path)
    rows: list[ProductRow] = []
    current_section = ""

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = clean_line(raw)
        if not line or line.startswith("1405"):
            continue
        if is_section_header(line):
            current_section = normalize_section_title(line)
            continue

        sku_matches = SKU_RE.findall(line)
        if not sku_matches:
            continue

        sku = sku_matches[-1].upper()
        flags: list[str] = []
        if len(sku_matches) > 1:
            flags.append("multiple_sku_on_line")

        prices = PRICE_RE.findall(line)
        leading_zero = bool(re.match(r"^\s*0\s", line))
        price_raw = prices[0] if prices else ("0" if leading_zero else "")
        base_price_toman = ""
        price_is_inquiry = "false"
        if leading_zero and not prices:
            price_is_inquiry = "true"
            flags.append("inquiry_price")
        elif price_raw:
            rial = parse_price_number(price_raw)
            if rial is not None:
                base_price_toman = str(rial_to_toman(rial))
            else:
                flags.append("price_parse_failed")
        else:
            flags.append("missing_price")

        accuracy = extract_accuracy(line)
        size_range, size_label_fa = extract_size_range(line, sku)
        description = extract_dasqua_description(current_section, line)
        category_id, category_name, confidence = suggest_category(
            current_section, description, line
        )
        if not category_id:
            flags.append("category_unmapped")

        row = ProductRow(
            brand="Dasqua | داسکوا",
            brand_id=4,
            sku=sku,
            name="",
            description=description,
            category_id=category_id,
            category_name=category_name,
            category_confidence=confidence,
            price_raw=price_raw,
            price_currency="rial",
            base_price_toman=base_price_toman,
            price_is_inquiry=price_is_inquiry,
            accuracy=accuracy,
            size_range=size_range,
            size_label_fa=size_label_fa,
            section_title=current_section,
            source_file=path.name,
            source_row_hint=f"line:{line_no}",
            source_line=line,
            parse_flags=flags,
        )
        rows.append(enrich_row(row))

    return dedupe_rows(rows)


def parse_insize_pdf(path: Path) -> list[ProductRow]:
    text = pdf_to_text(path)
    rows: list[ProductRow] = []
    current_family = ""

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = clean_line(raw)
        if not line or "Page " in line or "لیست فروش" in line:
            continue
        if is_section_header(line):
            current_family = normalize_section_title(line)
            continue

        sku_match = SKU_RE.search(line)
        if not sku_match:
            continue

        sku = sku_match.group(1).upper()
        flags: list[str] = []
        prices = PRICE_RE.findall(line)
        price_raw = prices[0] if prices else ""
        base_price_toman = ""
        price_is_inquiry = "false"
        if price_raw:
            toman = parse_price_number(price_raw)
            base_price_toman = str(toman) if toman is not None else ""
            if toman is None:
                flags.append("price_parse_failed")
        else:
            flags.append("missing_price")
            price_is_inquiry = "true"

        accuracy = extract_accuracy(line)
        size_range, size_label_fa = extract_size_range(line, sku)
        description = extract_insize_description(line, sku, current_family)
        category_id, category_name, confidence = suggest_category(
            description, current_family, line
        )
        if not category_id:
            flags.append("category_unmapped")

        row = ProductRow(
            brand="INSIZE | اینسایز",
            brand_id=3,
            sku=sku,
            name="",
            description=description,
            category_id=category_id,
            category_name=category_name,
            category_confidence=confidence,
            price_raw=price_raw,
            price_currency="toman",
            base_price_toman=base_price_toman,
            price_is_inquiry=price_is_inquiry,
            accuracy=accuracy,
            size_range=size_range,
            size_label_fa=size_label_fa,
            section_title=current_family,
            source_file=path.name,
            source_row_hint=f"line:{line_no}",
            source_line=line,
            parse_flags=flags,
        )
        rows.append(enrich_row(row))

    return dedupe_rows(rows)


def dedupe_rows(rows: list[ProductRow]) -> list[ProductRow]:
    by_sku: dict[str, ProductRow] = {}
    duplicate_skus: set[str] = set()

    def richness(row: ProductRow) -> tuple[int, int, int]:
        return (
            0 if row.price_is_inquiry == "true" else 1,
            len(row.name),
            len(row.description),
        )

    for row in rows:
        existing = by_sku.get(row.sku)
        if existing is None:
            by_sku[row.sku] = row
            continue
        duplicate_skus.add(row.sku)
        if richness(row) > richness(existing):
            row.parse_flags = list(dict.fromkeys([*row.parse_flags, "duplicate_sku_merged"]))
            by_sku[row.sku] = enrich_row(row)
        else:
            existing.parse_flags = list(
                dict.fromkeys([*existing.parse_flags, "duplicate_sku_merged"])
            )

    for sku in duplicate_skus:
        by_sku[sku].parse_flags = list(
            dict.fromkeys([*by_sku[sku].parse_flags, "duplicate_sku_in_pdf"])
        )
    return list(by_sku.values())


def write_csv(path: Path, rows: list[ProductRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in sorted(rows, key=lambda item: (item.brand, item.sku)):
            writer.writerow(row.to_dict())


def write_summary(path: Path, dasqua_rows: list[ProductRow], insize_rows: list[ProductRow]) -> None:
    all_rows = dasqua_rows + insize_rows
    non_price_flags = Counter(
        flag
        for row in all_rows
        for flag in row.parse_flags
        if flag not in {"missing_price", "price_parse_failed", "inquiry_price"}
    )
    category_counter = Counter(row.category_name for row in all_rows)

    lines = [
        "Price list import review summary",
        "================================",
        f"Dasqua unique SKUs: {len(dasqua_rows)}",
        f"Insize unique SKUs: {len(insize_rows)}",
        f"Total unique SKUs: {len(all_rows)}",
        "",
        "Non-price quality:",
        f"  all categorized: {sum(1 for r in all_rows if r.category_id)} / {len(all_rows)}",
        f"  with specifications_json: {sum(1 for r in all_rows if r.specifications_json)}",
        f"  with size_range: {sum(1 for r in all_rows if r.size_range)}",
        f"  weak_name flags: {sum(1 for r in all_rows if 'weak_name' in r.parse_flags)}",
        f"  category_fallback: {sum(1 for r in all_rows if 'category_fallback' in r.parse_flags)}",
        "",
        "Category mapping:",
    ]
    for name, count in category_counter.most_common():
        lines.append(f"  {name}: {count}")

    lines.extend(["", "Non-price parse flags:"])
    for name, count in non_price_flags.most_common():
        lines.append(f"  {name}: {count}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse brand price-list PDFs to CSV.")
    parser.add_argument("--dasqua", type=Path, default=DEFAULT_DASQUA)
    parser.add_argument("--insize", type=Path, default=DEFAULT_INSIZE)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()

    if not args.dasqua.exists():
        print(f"Dasqua PDF not found: {args.dasqua}", file=sys.stderr)
        return 1
    if not args.insize.exists():
        print(f"Insize PDF not found: {args.insize}", file=sys.stderr)
        return 1

    print(f"Parsing Dasqua: {args.dasqua}")
    dasqua_rows = parse_dasqua_pdf(args.dasqua)
    print(f"Parsing Insize: {args.insize}")
    insize_rows = parse_insize_pdf(args.insize)

    out = args.output_dir
    write_csv(out / "dasqua_products.csv", dasqua_rows)
    write_csv(out / "insize_products.csv", insize_rows)
    write_csv(out / "all_products.csv", dasqua_rows + insize_rows)
    write_summary(out / "import_review_summary.txt", dasqua_rows, insize_rows)

    print(f"Wrote {len(dasqua_rows)} Dasqua rows -> {out / 'dasqua_products.csv'}")
    print(f"Wrote {len(insize_rows)} Insize rows -> {out / 'insize_products.csv'}")
    print(f"Summary -> {out / 'import_review_summary.txt'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
