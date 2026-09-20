from __future__ import annotations

import re
from datetime import date
from pathlib import Path

_TICKER_SLUGS = {
    "BZ=F": "brent",
    "CL=F": "wti",
    "^GSPC": "sp500",
    "NG=F": "natgas",
    "GC=F": "gold",
}


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return slug[:max_len].strip("-")


def indicator_slug(name: str) -> str:
    short = str(name).split(".", 1)[1] if str(name).startswith("finance.") else str(name)
    ticker, _, rest = short.partition(".")
    ticker_slug = _TICKER_SLUGS.get(ticker, slugify(ticker, 20))
    return f"{ticker_slug}-{slugify(rest, 20)}".strip("-") if rest else ticker_slug


def folder_name(day: date, counter: int, chart_type: str, indicators: list[str]) -> str:
    slugs = "-".join(indicator_slug(name) for name in indicators) or "chart"
    return f"{day:%Y%m%d}-{counter:03d}-{slugify(chart_type, 20)}_{slugs[:60].strip('-')}"


def next_counter(graphs_dir: Path) -> int:
    highest = 0
    if graphs_dir.exists():
        for child in graphs_dir.iterdir():
            match = re.match(r"^\d{8}-(\d{3})-", child.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1
