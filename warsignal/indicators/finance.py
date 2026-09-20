from __future__ import annotations

import pandas as pd

from warsignal.config import DATA_RAW
from .base import IndicatorSpec, IndicatorUnavailable, register


def _prices():
    path = DATA_RAW / "finance" / "prices.parquet"
    if not path.exists():
        raise IndicatorUnavailable("finance", "prices.parquet is missing")
    frame = pd.read_parquet(path)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def _load(ticker, column):
    frame = _prices()
    rows = frame[frame.ticker == ticker].set_index("date").sort_index()
    if rows.empty:
        raise FileNotFoundError(f"ticker {ticker} unavailable")
    if column == "log_return":
        return rows["close"].where(rows.close > 0).pipe(lambda s: __import__("numpy").log(s).diff())
    if column == "abs_return":
        return rows.close.pct_change().abs()
    if column == "range_pct":
        return (rows.high - rows.low) / rows.close
    return rows[column]


def _combine(ticker_a, ticker_b, operation):
    a, b = _load(ticker_a, "close"), _load(ticker_b, "close")
    if operation == "spread":
        return a.subtract(b)
    if operation == "crack":  # RBOB $/gal -> $/bbl minus crude $/bbl
        return a.multiply(42.0).subtract(b)
    return a.divide(b)


def _register():
    try:
        tickers = _prices().ticker.dropna().unique()
    except Exception:
        tickers = []
    for ticker in tickers:
        for column, unit in (("close", "price"), ("log_return", "return"), ("abs_return", "return"), ("range_pct", "ratio")):
            name = f"finance.{ticker}.{column}"
            register(IndicatorSpec(name, "finance", f"{ticker} {column}", unit, "D"), lambda ticker=ticker, column=column: _load(ticker, column))
    for name, ticker_a, ticker_b, operation in [
        ("finance.spread.brent_wti", "BZ=F", "CL=F", "spread"),
        ("finance.ratio.gold_oil", "GC=F", "BZ=F", "ratio"),
        ("finance.spread.gasoline_crack", "RB=F", "CL=F", "crack"),
        ("finance.ratio.ttf_henryhub", "TTF=F", "NG=F", "ratio"),
        ("finance.ratio.tankers_xle", "FRO", "XLE", "ratio"),
        ("finance.ratio.jets_spy", "JETS", "SPY", "ratio"),
        ("finance.ratio.xop_spy", "XOP", "SPY", "ratio"),
        ("finance.ratio.eem_spy", "EEM", "SPY", "ratio"),
    ]:
        register(IndicatorSpec(name, "finance", name, "price", "D"),
                 lambda a=ticker_a, b=ticker_b, op=operation: _combine(a, b, op))
    for fred in ("DCOILBRENTEU", "DCOILWTICO", "DHHNGSP", "DGS10"):
        register(IndicatorSpec(f"finance.fred.{fred}", "finance", f"FRED {fred}", "value", "D"),
                 lambda fred=fred: _fred(fred))


def _fred(series):
    path = DATA_RAW / "finance" / f"fred_{series}.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path)
    date_col = "observation_date" if "observation_date" in frame.columns else "DATE"
    value = next(column for column in frame.columns if column != date_col)
    return pd.Series(pd.to_numeric(frame[value], errors="coerce").to_numpy(), index=pd.to_datetime(frame[date_col]))


_register()
