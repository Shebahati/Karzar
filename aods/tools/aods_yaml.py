"""Minimal YAML-subset reader for AODS registries.

PyYAML is deliberately not required: it is absent from `requirements.txt` and
`requirements-dev.txt`, so depending on it would make the validators fail on a clean
checkout — a gate that cannot run is worse than no gate (charter failure criterion F-04).

Supported subset, which is all the AODS registries and prompt front-matter use:

    key: value                  scalars (str / int / float / bool / null)
    key:                        nested mapping (by indentation)
      child: value
    key: [a, b, c]              inline flow sequence
    - item                      block sequence of scalars
    - key: value                block sequence of mappings
      other: value
    key: >-                     folded block scalar (newlines become spaces)
      long prose
    key: |-                     literal block scalar (newlines preserved)
      line one
      line two
    # comment                   full-line and trailing comments
    "quoted"  'quoted'          quoted scalars (comment chars inside quotes are safe)

Deliberately NOT supported: anchors, aliases, multiple documents, complex keys,
nested flow mappings. `parse` raises YamlSubsetError on anything it does not
understand rather than guessing, because a silently mis-parsed registry would
produce false-passing gates.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["YamlSubsetError", "parse", "parse_front_matter"]


class YamlSubsetError(ValueError):
    """Raised when input uses YAML features outside the supported subset."""


_BLOCK_SCALAR = re.compile(r"^(?P<indent>\s*)(?P<dash>-\s+)?(?P<key>[^#\s][^:]*):\s*(?P<style>[|>])(?P<chomp>[-+]?)\s*$")


def _strip_comment(text: str) -> str:
    """Remove a trailing comment, respecting quotes."""
    out: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out).rstrip()


def _scalar(raw: str) -> Any:
    raw = raw.strip()
    if not raw:
        return None
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    low = raw.lower()
    if low in ("null", "~", "none"):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _flow_seq(raw: str) -> list[Any]:
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    items: list[str] = []
    depth = 0
    quote: str | None = None
    current: list[str] = []
    for ch in inner:
        if quote:
            current.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            current.append(ch)
        elif ch in "[{":
            depth += 1
            current.append(ch)
        elif ch in "]}":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            items.append("".join(current))
            current = []
        else:
            current.append(ch)
    items.append("".join(current))
    return [_scalar(part) for part in items if part.strip() != ""]


_NO_PRESET = object()


def _join_flow(lines: list["_Line"], index: int, first: str) -> tuple[str, int]:
    """Join a flow sequence that may span several lines, until brackets balance.

    Returns the joined text and the index of the first line after it.
    """
    text = first
    index += 1
    while text.count("[") > text.count("]") and index < len(lines):
        text += " " + lines[index].text
        index += 1
    return text, index


class _Line:
    """One significant input line.

    `preset` holds an already-resolved value for block scalars, whose raw text cannot
    survive comment-stripping and scalar coercion.
    """

    __slots__ = ("indent", "text", "lineno", "preset")

    def __init__(self, indent: int, text: str, lineno: int, preset: Any = _NO_PRESET) -> None:
        self.indent = indent
        self.text = text
        self.lineno = lineno
        self.preset = preset


def _fold_block_scalar(raw_lines: list[str], start: int, parent_indent: int, style: str, chomp: str) -> tuple[str, int]:
    """Collect the body of a block scalar. Returns (value, index_after)."""
    body: list[str] = []
    i = start
    content_indent: int | None = None
    while i < len(raw_lines):
        raw = raw_lines[i]
        if raw.strip() == "":
            body.append("")
            i += 1
            continue
        indent = len(raw) - len(raw.lstrip())
        if indent <= parent_indent:
            break
        if content_indent is None:
            content_indent = indent
        body.append(raw[content_indent:] if len(raw) >= content_indent else raw.lstrip())
        i += 1
    while body and body[-1] == "":
        body.pop()
    if style == "|":
        value = "\n".join(body)
    else:
        # Folded: blank lines become paragraph breaks, others join with a space.
        parts: list[str] = []
        buffer: list[str] = []
        for entry in body:
            if entry == "":
                if buffer:
                    parts.append(" ".join(buffer))
                    buffer = []
            else:
                buffer.append(entry.strip())
        if buffer:
            parts.append(" ".join(buffer))
        value = "\n".join(parts)
    if chomp == "+":
        value += "\n"
    elif chomp != "-":
        value += "\n" if value else ""
    return value, i


def _lines(source: str) -> list[_Line]:
    result: list[_Line] = []
    raw_lines = source.splitlines()
    i = 0
    while i < len(raw_lines):
        raw = raw_lines[i]
        lineno = i + 1
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise YamlSubsetError(f"line {lineno}: tab indentation is not supported")
        block = _BLOCK_SCALAR.match(_strip_comment(raw))
        if block:
            indent = len(block.group("indent"))
            key = block.group("key").strip()
            dash = block.group("dash")
            value, i = _fold_block_scalar(
                raw_lines, i + 1, indent + (len(dash) if dash else 0), block.group("style"), block.group("chomp")
            )
            text = f"{'- ' if dash else ''}{key}:"
            result.append(_Line(indent, text, lineno, value))
            continue
        stripped = _strip_comment(raw)
        i += 1
        if not stripped.strip() or stripped.strip() in ("---", "..."):
            continue
        result.append(_Line(len(stripped) - len(stripped.lstrip()), stripped.strip(), lineno))
    return result


def _parse_block(lines: list[_Line], start: int, indent: int) -> tuple[Any, int]:
    if start >= len(lines):
        return None, start
    if lines[start].text.startswith("- "):
        return _parse_seq(lines, start, indent)
    return _parse_map(lines, start, indent)


def _parse_seq(lines: list[_Line], start: int, indent: int) -> tuple[list[Any], int]:
    items: list[Any] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if line.indent < indent or not line.text.startswith("-"):
            break
        if line.indent > indent:
            raise YamlSubsetError(f"line {line.lineno}: unexpected indentation in sequence")
        body = line.text[1:].strip()
        i += 1
        if line.preset is not _NO_PRESET and ":" in body:
            key, _, _ = body.partition(":")
            entry_preset: dict[str, Any] = {key.strip(): line.preset}
            child_indent = line.indent + 2
            while i < len(lines) and lines[i].indent >= child_indent and not lines[i].text.startswith("- "):
                sub, i = _parse_map_entry(lines, i, lines[i].indent)
                entry_preset.update(sub)
            items.append(entry_preset)
            continue
        if not body:
            value, i = _parse_block(lines, i, indent + 1) if i < len(lines) and lines[i].indent > indent else (None, i)
            items.append(value)
            continue
        if ":" in body and not body.startswith(("'", '"')):
            key, _, rest = body.partition(":")
            entry: dict[str, Any] = {}
            child_indent = line.indent + 2
            rest = rest.strip()
            if rest:
                entry[key.strip()] = _flow_seq(rest) if rest.startswith("[") else _scalar(rest)
            else:
                nested, i = _parse_block(lines, i, child_indent)
                entry[key.strip()] = nested
            while i < len(lines) and lines[i].indent >= child_indent and not lines[i].text.startswith("- "):
                sub, i = _parse_map_entry(lines, i, lines[i].indent)
                entry.update(sub)
            items.append(entry)
        else:
            items.append(_flow_seq(body) if body.startswith("[") else _scalar(body))
    return items, i


def _parse_map_entry(lines: list[_Line], index: int, indent: int) -> tuple[dict[str, Any], int]:
    line = lines[index]
    if ":" not in line.text:
        raise YamlSubsetError(f"line {line.lineno}: expected 'key: value'")
    key, _, rest = line.text.partition(":")
    key = key.strip()
    rest = rest.strip()
    index += 1
    if line.preset is not _NO_PRESET:
        return {key: line.preset}, index
    if rest:
        if rest.startswith("["):
            joined, index = _join_flow(lines, index - 1, rest)
            return {key: _flow_seq(joined)}, index
        return {key: _scalar(rest)}, index
    # A flow sequence may begin on the following, more-indented line.
    if index < len(lines) and lines[index].indent > indent and lines[index].text.startswith("["):
        joined, index = _join_flow(lines, index, lines[index].text)
        return {key: _flow_seq(joined)}, index
    if index < len(lines) and lines[index].indent > indent:
        nested, index = _parse_block(lines, index, lines[index].indent)
        return {key: nested}, index
    if index < len(lines) and lines[index].indent == indent and lines[index].text.startswith("- "):
        nested, index = _parse_seq(lines, index, indent)
        return {key: nested}, index
    return {key: None}, index


def _parse_map(lines: list[_Line], start: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if line.indent < indent:
            break
        if line.indent > indent:
            raise YamlSubsetError(f"line {line.lineno}: unexpected indentation in mapping")
        if line.text.startswith("- "):
            break
        entry, i = _parse_map_entry(lines, i, indent)
        result.update(entry)
    return result, i


def parse(source: str) -> Any:
    """Parse a YAML-subset document into Python data."""
    lines = _lines(source)
    if not lines:
        return {}
    value, consumed = _parse_block(lines, 0, lines[0].indent)
    if consumed != len(lines):
        raise YamlSubsetError(f"line {lines[consumed].lineno}: could not parse (unsupported construct)")
    return value


def parse_front_matter(source: str) -> tuple[dict[str, Any], str]:
    """Split a `---`-delimited front-matter block from a markdown body.

    Returns `({}, source)` when no front matter is present, so callers can distinguish
    "absent" from "malformed" (malformed raises).
    """
    if not source.startswith("---"):
        return {}, source
    parts = source.split("\n")
    if parts[0].strip() != "---":
        return {}, source
    for index in range(1, len(parts)):
        if parts[index].strip() == "---":
            block = "\n".join(parts[1:index])
            body = "\n".join(parts[index + 1 :])
            parsed = parse(block)
            if not isinstance(parsed, dict):
                raise YamlSubsetError("front matter must be a mapping")
            return parsed, body
    raise YamlSubsetError("front matter opened with --- but never closed")
