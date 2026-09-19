from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from warsignal.fetch.common import manifest, output_dir, parse_date

TICKERS = "BZ=F CL=F NG=F GC=F ^GSPC ^VIX XLE DX-Y.NYB TLT LMT RTX XOM EEM USO TUR KSA UAE EIS TTF=F ZW=F ZC=F HG=F ALI=F SLV JETS UAL DAL NOC GD BA MOS CF NTR XLU FCX ^TNX HYG".split()
FRED = ["DCOILBRENTEU", "DCOILWTICO", "DHHNGSP", "DGS10"]

def fetch(start=date(2025, 1, 1), end=date.today(), **_) -> list[Path]:
    out = output_dir("finance"); paths = []
    frames = []
    for ticker in TICKERS:
        try:
            data = yf.download(ticker, start=start.isoformat(), end=(end + pd.Timedelta(days=1)).isoformat(), auto_adjust=False, progress=False, threads=False)
            if data.empty: raise ValueError("empty result")
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            frame = data.rename(columns={c: c.lower() for c in data.columns}).reset_index()
            frame["ticker"] = ticker
            frame["date"] = pd.to_datetime(frame["Date"]).dt.date
            frames.append(frame[["date", "ticker", "open", "high", "low", "close", "volume"]])
        except Exception as exc:
            print(f"finance: {ticker} failed: {exc}")
    price_path = out / "prices.parquet"
    if frames:
        result = pd.concat(frames, ignore_index=True)
        result.to_parquet(price_path, index=False)
        manifest("finance", "yfinance", price_path.stat().st_size, start, end, status="downloaded", tickers=len(frames))
        paths.append(price_path)
    for series in FRED:
        path = out / f"fred_{series}.csv"
        if path.exists() and path.stat().st_size > 0: paths.append(path); continue
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
        try:
            response = __import__("requests").get(url, timeout=60); response.raise_for_status()
            path.write_bytes(response.content); manifest("finance", url, len(response.content), start, end, status="downloaded"); paths.append(path)
        except Exception as exc:
            manifest("finance", url, 0, start, end, status="error", error=str(exc))
    print(f"finance: {len(paths)} files")
    return paths

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--quick", action="store_true"); a = p.parse_args()
    from warsignal.config import START, END
    fetch(parse_date(a.start) if a.start else date(2025, 1, 1), parse_date(a.end) if a.end else END)
