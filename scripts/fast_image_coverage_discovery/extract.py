"""Product image extraction from HTML/JSON-LD/OpenGraph."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin

from scripts.image_discovery.sources.html_subject import parse_page_subject, text_of

_OG_IMAGE = re.compile(
    r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_IMAGE_REV = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::secure_url)?["\']',
    re.I,
)
_IMG_SRC = re.compile(
    r'<img[^>]+(?:src|data-src|data-original)=["\']([^"\']+)["\'][^>]*>',
    re.I,
)
_BAD_IMG = re.compile(r"(logo|icon|banner|placeholder|tracking|pixel|sprite)", re.I)


class _TitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title += data


def extract_title(html: str) -> str:
    p = _TitleParser()
    try:
        p.feed(html)
    except Exception:
        return ""
    return re.sub(r"\s+", " ", p.title).strip()


def extract_json_ld_products(html: str) -> list[dict[str, Any]]:
    subject = parse_page_subject(html)
    return list(subject.subject_json_ld_products)


def extract_product_images(
    html: str,
    page_url: str,
    *,
    sku: str = "",
) -> tuple[list[str], str, bool]:
    """Return (image_urls priority order, gallery_evidence, has_pdp_structure)."""
    title = extract_title(html)
    subject = parse_page_subject(html)
    text = text_of(subject.subject_html())
    has_pdp = bool(title) and (sku.lower() in text.lower() if sku else len(text) > 200)

    urls: list[str] = []

    for prod in extract_json_ld_products(html):
        imgs = prod.get("image")
        if isinstance(imgs, str):
            urls.append(urljoin(page_url, imgs))
        elif isinstance(imgs, list):
            for item in imgs:
                if isinstance(item, str):
                    urls.append(urljoin(page_url, item))
                elif isinstance(item, dict) and item.get("url"):
                    urls.append(urljoin(page_url, str(item["url"])))

    for rx in (_OG_IMAGE, _OG_IMAGE_REV):
        for m in rx.finditer(html):
            urls.append(urljoin(page_url, m.group(1)))

    for m in _IMG_SRC.finditer(html):
        src = m.group(1)
        if _BAD_IMG.search(src):
            continue
        urls.append(urljoin(page_url, src))

    deduped: list[str] = []
    seen: set[str] = set()
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        deduped.append(u)

    gallery_evidence = "json_ld" if extract_json_ld_products(html) else (
        "og_image" if deduped else "dom_img"
    )
    return deduped, gallery_evidence, has_pdp


def parse_wc_product_images(product: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for img in product.get("images") or []:
        if isinstance(img, dict):
            src = img.get("src") or img.get("thumbnail") or img.get("url")
            if src:
                out.append(str(src))
        elif isinstance(img, str):
            out.append(img)
    return out
