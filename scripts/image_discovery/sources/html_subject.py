"""Structural HTML page-subject boundary (stdlib HTMLParser — not regex nesting)."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

# Tags that are always unrelated regions (entire subtree suppressed from subject).
_UNRELATED_TAGS = frozenset({"footer", "nav", "aside", "header"})

# Tokens matched against class / id / data-* attribute values (case-insensitive).
_UNRELATED_TOKENS = (
    "footer",
    "nav",
    "aside",
    "header",
    "breadcrumb",
    "related",
    "cross-sell",
    "cross_sell",
    "crosssell",
    "recommend",
    "upsell",
    "also-see",
    "also_see",
    "product-list",
    "product_list",
    "similar",
    "data-related",
    "data-crosssell",
)

_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)

_TAG_RE = re.compile(r"<[^>]+>")


def _attrs_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {k.lower(): (v or "") for k, v in attrs}


def _attr_blob(attrs: dict[str, str]) -> str:
    parts = [attrs.get("class", ""), attrs.get("id", "")]
    for k, v in attrs.items():
        if k.startswith("data-"):
            parts.append(f"{k} {v}")
    return " ".join(parts).casefold()


def _element_starts_unrelated(tag: str, attrs: dict[str, str]) -> bool:
    t = tag.lower()
    if t in _UNRELATED_TAGS:
        return True
    blob = _attr_blob(attrs)
    if not blob:
        # data-related / data-crosssell as bare attribute names
        for k in attrs:
            kl = k.casefold()
            if kl in {"data-related", "data-crosssell"} or "related" in kl or "crosssell" in kl:
                return True
        return False
    for tok in _UNRELATED_TOKENS:
        if tok.casefold() in blob:
            return True
    return False


def _fmt_start(tag: str, attrs: list[tuple[str, str | None]]) -> str:
    if not attrs:
        return f"<{tag}>"
    inner = " ".join(f'{k}="{v}"' if v is not None else k for k, v in attrs)
    return f"<{tag} {inner}>"


class PageSubjectParser(HTMLParser):
    """Stack-based subject/unrelated split; nested closings never end an outer unrelated block early."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []  # (tag, started_unrelated_here)
        self.suppress_depth = 0
        self.subject_chunks: list[str] = []
        self.unrelated_chunks: list[str] = []
        self.script_chunks: list[str] = []
        self._in_script = False
        self._script_type = ""
        self._script_buf: list[str] = []
        self.headings: list[str] = []
        self._in_heading: str | None = None
        self._heading_buf: list[str] = []
        self.json_ld_products: list[dict[str, Any]] = []
        self.meta_fields: dict[str, str] = {}

    def _emit(self, text: str) -> None:
        if self._in_script:
            self._script_buf.append(text)
            self.script_chunks.append(text)
            return
        if self.suppress_depth > 0:
            self.unrelated_chunks.append(text)
        else:
            self.subject_chunks.append(text)
            if self._in_heading:
                self._heading_buf.append(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        ad = _attrs_dict(attrs)
        start_html = _fmt_start(t, attrs)

        if t == "meta":
            name = (ad.get("property") or ad.get("name") or "").lower()
            content = ad.get("content") or ""
            if name:
                self.meta_fields[name] = content.strip()
            self._emit(start_html)
            return

        if t == "script":
            self._in_script = True
            self._script_type = (ad.get("type") or "").lower()
            self._script_buf = []
            self.script_chunks.append(start_html)
            if self.suppress_depth > 0:
                self.suppress_depth += 1
            self.stack.append((t, False))
            return

        if t == "style":
            # Always suppress style subtrees from page-subject evidence
            if self.suppress_depth > 0:
                self.suppress_depth += 1
                started_here = False
            else:
                self.suppress_depth = 1
                started_here = True
            self.stack.append((t, started_here))
            self._emit(start_html)
            return

        starts_unrelated = _element_starts_unrelated(t, ad)
        if self.suppress_depth > 0:
            self.suppress_depth += 1
            started_here = False
        elif starts_unrelated:
            self.suppress_depth = 1
            started_here = True
        else:
            started_here = False

        if t not in _VOID:
            self.stack.append((t, started_here))

        if t in {"h1", "h2"} and self.suppress_depth == 0:
            self._in_heading = t
            self._heading_buf = []

        self._emit(start_html)

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        end_html = f"</{t}>"

        if t == "script" and self._in_script:
            raw = "".join(self._script_buf)
            if "ld+json" in self._script_type:
                self._ingest_json_ld(raw)
            self.script_chunks.append(end_html)
            self._in_script = False
            self._script_type = ""
            self._script_buf = []
            self._pop_tag(t)
            return

        if self._in_heading == t:
            text = re.sub(r"\s+", " ", "".join(self._heading_buf)).strip()
            if text:
                self.headings.append(text)
            self._in_heading = None
            self._heading_buf = []

        self._emit(end_html)
        self._pop_tag(t)

    def _pop_tag(self, tag: str) -> None:
        """Pop stack until ``tag``; only the matching open reduces suppress_depth correctly."""
        if tag in _VOID:
            return
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                idx = i
                break
        if idx is None:
            # Malformed: ignore unmatched close for suppress accounting
            return
        # Pop nested opens above the match first (recoverable HTML)
        while len(self.stack) > idx + 1:
            _t, started = self.stack.pop()
            if self.suppress_depth > 0:
                self.suppress_depth -= 1
        _t, started = self.stack.pop()
        if self.suppress_depth > 0:
            self.suppress_depth -= 1

    def handle_data(self, data: str) -> None:
        self._emit(data)

    def handle_entityref(self, name: str) -> None:
        self._emit(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._emit(f"&#{name};")

    def _ingest_json_ld(self, raw: str) -> None:
        try:
            node = json.loads(raw.strip())
        except Exception:
            return

        def walk(obj: object) -> None:
            if isinstance(obj, dict):
                t = str(obj.get("@type") or "")
                types = t if isinstance(t, str) else " ".join(str(x) for x in t)
                if "Product" in types:
                    self.json_ld_products.append(obj)
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)

        walk(node)

    def subject_html(self) -> str:
        return "".join(self.subject_chunks)

    def unrelated_html(self) -> str:
        return "".join(self.unrelated_chunks)

    def scripts_html(self) -> str:
        return "".join(self.script_chunks)


def parse_page_subject(page_html: str) -> PageSubjectParser:
    parser = PageSubjectParser()
    try:
        parser.feed(page_html or "")
        parser.close()
    except Exception:
        # Recoverable: return whatever was collected
        pass
    return parser


def text_of(fragment: str) -> str:
    t = _TAG_RE.sub(" ", fragment)
    return re.sub(r"\s+", " ", t).strip()
