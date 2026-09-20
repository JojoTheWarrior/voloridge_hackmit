"""Pure formatting of a mission ``note.md`` into styled lines for ``TextPanel``.

``format_note`` understands the note layout written by the mission agents: a
``| Field | Value |`` markdown table followed by prose paragraphs. Fields become
``Attribute: value`` lines with a bold attribute, dict-like values are
pretty-printed as JSON, floats are shortened to 5 decimals and every block is
separated by a blank line. Wrapping happens later, in the widget.
"""
from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass

DECIMALS = 5
_FLOAT = re.compile(r"(?<![\w.])-?\d+\.\d{%d,}(?![\w.])" % (DECIMALS + 1))
_BOLD_PREFIX = re.compile(r"^\*\*([^*]+?)\*\*\s*(.*)$")
_LIST_ITEM = re.compile(r"^(?:[-*+]|\d+[.)])\s+(.*)$")
_LABELLED = re.compile(r"^([A-Za-z][^:]{0,40}):\s+(.*)$")


@dataclass(frozen=True)
class NoteLine:
    """One logical (unwrapped) line: ``bold`` prefix, plain ``text``, ``indent`` in spaces."""
    text: str = ""
    bold: str = ""
    indent: int = 0

    @property
    def blank(self) -> bool:
        return not self.text and not self.bold


BLANK = NoteLine()


def round_numbers(text: str, decimals: int = DECIMALS) -> str:
    """Shorten floats with more than ``decimals`` places; integers are untouched."""

    def repl(m: re.Match) -> str:
        out = f"{float(m.group()):.{decimals}f}".rstrip("0")
        return out + "0" if out.endswith(".") else out

    return _FLOAT.sub(repl, text)


def _clean(text: str) -> str:
    return text.replace("`", "").replace("**", "").strip()


def _table_cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_separator(cells: list[str]) -> bool:
    return all(set(c) <= set("-: ") for c in cells)


def _is_header(cells: list[str]) -> bool:
    return len(cells) >= 2 and cells[0].lower() == "field" and cells[1].lower() == "value"


def pretty_value(value: str) -> list[str] | None:
    """``{'a': 1}`` -> JSON lines (indent 2); ``None`` when ``value`` is not a literal container."""
    stripped = value.strip()
    if not stripped or stripped[0] not in "{[":
        return None
    try:
        parsed = ast.literal_eval(stripped)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None
    if not isinstance(parsed, (dict, list, tuple)):
        return None
    return json.dumps(parsed, indent=2, ensure_ascii=False).splitlines()


def field_lines(attribute: str, value: str) -> list[NoteLine]:
    attribute = _clean(attribute)
    value = _clean(value)
    pretty = pretty_value(value)
    if pretty is None:
        return [NoteLine(round_numbers(value), bold=f"{attribute}:")]
    lines = [NoteLine("", bold=f"{attribute}:")]
    for raw in pretty:
        body = raw.lstrip(" ")
        lines.append(NoteLine(round_numbers(body), indent=2 + (len(raw) - len(body))))
    return lines


def prose_lines(paragraph: str) -> list[NoteLine]:
    paragraph = round_numbers(paragraph)
    m = _BOLD_PREFIX.match(paragraph)
    if m:
        return [NoteLine(_clean(m.group(2)), bold=_clean(m.group(1)))]
    return [NoteLine(_clean(paragraph))]


def list_item_lines(item: str) -> list[NoteLine]:
    """``- Entry: rule`` -> bold ``Entry:`` + text; ``- **X**, rest`` -> bold ``X`` + text."""
    item = round_numbers(item)
    m = _BOLD_PREFIX.match(item)
    if m:
        return [NoteLine(_clean(m.group(2)), bold=_clean(m.group(1)))]
    m = _LABELLED.match(item)
    if m:
        return [NoteLine(_clean(m.group(2)), bold=_clean(m.group(1)) + ":")]
    return [NoteLine(_clean(item))]


def format_note(text: str, title: str = "", subtitle: str = "") -> list[NoteLine]:
    """Parse ``note.md`` into logical lines; ``title``/``subtitle`` head the output."""
    blocks: list[list[NoteLine]] = []
    if subtitle:
        blocks.append([NoteLine(bold=subtitle.strip())])
    if title and title.strip() != subtitle.strip():
        blocks.append([NoteLine(title.strip())])

    paragraph: list[str] = []

    def flush():
        if paragraph:
            blocks.append(prose_lines(" ".join(paragraph)))
            paragraph.clear()

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if line.startswith("|"):
            flush()
            cells = _table_cells(line)
            if _is_separator(cells) or _is_header(cells):
                continue
            if len(cells) >= 2:
                blocks.append(field_lines(cells[0], " ".join(c for c in cells[1:] if c)))
            elif cells and cells[0]:
                blocks.append([NoteLine(_clean(cells[0]))])
            continue
        if line.startswith("#"):
            flush()
            heading = _clean(line.lstrip("#"))
            if heading and heading != subtitle.strip():
                blocks.append([NoteLine(bold=heading)])
            continue
        item = _LIST_ITEM.match(line)
        if item:
            flush()
            blocks.append(list_item_lines(item.group(1)))
            continue
        paragraph.append(line)
    flush()

    out: list[NoteLine] = []
    for block in blocks:
        if out:
            out.append(BLANK)
        out.extend(block)
    return out
