from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

from warsignal.ai.openai_client import AIUnavailable, chat_json, chat_text
from warsignal.indicators import REGISTRY, catalogue_text, get_series
from .chart_template import CHART_TEMPLATE
from .naming import slugify

log = logging.getLogger(__name__)


class GraphError(RuntimeError):
    pass


PLAN_SYSTEM = """You plan charts for WarSignal, an alternative-data lab about the 2026 Iran war.
Return a JSON object:
{"chart_type": "reel|line|spread|scatter",
 "indicators": ["finance.BZ=F.close", ...],
 "external": [{"source": "yfinance"|"fred", "symbol": "MOS", "label": "Mosaic close", "field": "close"|"log_return"}],
 "needs_custom_code": bool, "custom_code_notes": str,
 "title": str, "notes": str, "rationale": str}
Rules:
- If the prompt mentions reel/reels/instagram/animate/video/play, chart_type is "reel".
- "spread"/"minus"/"difference" -> "spread". For Brent-WTI prefer the registered
  finance.spread.brent_wti indicator; otherwise give two indicators and the chart computes a-b.
- "scatter"/"vs"/"returns" -> "scatter" with exactly two series, preferring .log_return indicators.
- Otherwise "line". Multi-series line charts are fine.
- Only use "external" when nothing in the catalogue fits. For fertilizer equities suggest MOS/CF/NTR closes.
- Every entry in "indicators" must appear verbatim in the catalogue below.
- Set needs_custom_code true ONLY when the request cannot be expressed as one of
  reel/line/spread/scatter over the listed series (e.g. bar chart, histogram, dual-axis,
  rolling correlation, candlesticks). Otherwise false, and leave custom_code_notes empty.
"""


def plan_request(prompt: str) -> dict:
    user = f"Prompt: {prompt}\n\nCatalogue:\n{catalogue_text()}"
    try:
        plan = chat_json(PLAN_SYSTEM, user, model="gpt-5.1", max_tokens=3000)
    except AIUnavailable:
        log.info("AI unavailable, using heuristic plan")
        plan = heuristic_plan(prompt)
    plan.pop("_meta", None)
    plan.setdefault("chart_type", "line")
    plan["indicators"] = [name for name in plan.get("indicators", []) if name in REGISTRY]
    plan.setdefault("external", [])
    plan.setdefault("needs_custom_code", False)
    plan.setdefault("custom_code_notes", "")
    plan.setdefault("title", prompt[:80])
    if not plan["indicators"] and not plan["external"]:
        raise GraphError(f"no usable indicators for prompt: {prompt}")
    return plan


def heuristic_plan(prompt: str) -> dict:
    text = prompt.lower()
    tickers = {"brent": "BZ=F", "wti": "CL=F", "s&p": "^GSPC", "sp500": "^GSPC",
               "gold": "GC=F", "natgas": "NG=F", "natural gas": "NG=F", "vix": "^VIX"}
    field = "log_return" if "return" in text else "close"
    indicators = [f"finance.{t}.{field}" for key, t in tickers.items() if key in text and f"finance.{t}.{field}" in REGISTRY]
    if "spread" in text and "brent" in text and "wti" in text and "finance.spread.brent_wti" in REGISTRY:
        indicators = ["finance.spread.brent_wti"]
    if "reel" in text or "instagram" in text or "animate" in text or "video" in text:
        chart_type = "reel"
    elif "spread" in text or "minus" in text:
        chart_type = "spread"
    elif "scatter" in text or " vs " in text:
        chart_type = "scatter"
    else:
        chart_type = "line"
    return {"chart_type": chart_type, "indicators": indicators, "external": [],
            "needs_custom_code": False, "custom_code_notes": "",
            "title": prompt[:80], "notes": "heuristic plan", "rationale": "keyword match"}


def fetch_external(item: dict, out_dir: Path) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source, symbol = item.get("source", "yfinance"), item["symbol"]
    field = item.get("field", "close")
    if source == "fred":
        import requests
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={symbol}"
        frame = pd.read_csv(url)
        frame.columns = ["date", "value"]
        close = pd.Series(pd.to_numeric(frame["value"], errors="coerce").to_numpy(),
                          index=pd.to_datetime(frame["date"]))
        note = url
    else:
        import yfinance as yf
        data = yf.download(symbol, start="2025-01-01", auto_adjust=False, progress=False)
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        note = f"yfinance {symbol} close"
    if field == "log_return":
        close = np.log(close.where(close > 0)).diff()
    series = close.dropna()
    fname = f"{slugify(symbol)}-{field}.csv"
    pd.DataFrame({"date": series.index.date.astype(str), "value": series.values}).to_csv(out_dir / fname, index=False)
    return {"file": fname, "label": item.get("label", f"{symbol} {field}"),
            "indicator": f"external.{source}.{symbol}.{field}", "source_note": note,
            "rows": len(series), "start": str(series.index.min().date()), "end": str(series.index.max().date())}


def collect_data(plan: dict, data_dir: Path) -> list[dict]:
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    descriptors = []
    for name in plan.get("indicators", []):
        series = get_series(name).dropna()
        slug = slugify(name.replace("finance.", ""))
        fname = f"{slug}.csv"
        pd.DataFrame({"date": series.index.date.astype(str), "value": series.values}).to_csv(data_dir / fname, index=False)
        spec = REGISTRY.get(name)
        descriptors.append({"file": fname, "label": spec.description if spec else name,
                            "indicator": name, "rows": len(series),
                            "start": str(series.index.min().date()), "end": str(series.index.max().date())})
    if plan.get("chart_type") == "scatter" and len(descriptors) >= 2:
        plan["x_series"], plan["y_series"] = descriptors[0]["file"], descriptors[1]["file"]
    return descriptors


def generate_chart(plan: dict, series: list[dict], feedback: str | None = None) -> str:
    user = json.dumps({"plan": plan, "series": series,
                       "custom_code_notes": plan.get("custom_code_notes", "")}, indent=2, default=str)
    if feedback:
        user += f"\n\nThe previous script failed. Fix this:\n{feedback}"
    system = (
        "You are writing a self-contained pygame script. Start from the reference implementation "
        "below and change as little as possible: keep the 1280x800 landscape window, palette, fonts, "
        "layout, status bar, controls and headless contract exactly; only add or alter the drawing "
        "needed for the plan's custom_code_notes. Keep it loading only files from its own folder, "
        "no network, imports limited to ALLOWED_IMPORTS. Return ONLY the full Python source "
        "(no markdown fences).\n\n" + CHART_TEMPLATE
    )
    try:
        source, _meta = chat_text(system, user, model="gpt-5.1", max_tokens=12000)
    except AIUnavailable:
        return CHART_TEMPLATE
    source = source.strip()
    source = re.sub(r"^```(?:python)?\s*", "", source)
    source = re.sub(r"\s*```$", "", source)
    return source
