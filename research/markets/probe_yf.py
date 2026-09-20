"""Availability probe only: coverage of candidate tickers (no signal/target relationships examined)."""
import yfinance as yf, pandas as pd
T="ALI=F HG=F BZ=F CL=F NG=F TTF=F 2600.HK 601600.SS 000807.SZ AA NHY.OL 0486.HK ELET3.SA AXIA3.SA CMIG4.SA ENGI11.SA ENEV3.SA EGIE3.SA CPLE6.SA FM.TO ZMW=X USDZMW=X PCG EIX FRO STNG DHT BAS.DE 000300.SS DX-Y.NYB ^BVSP EWZ XLU DBC ^SPGSCI BRL=X NOK=X CNY=X ^GSPC ^GSPTSE ^HSI ^GDAXI XLE XME COPX NGN=X KZT=X UNG AH=F".split()
d=yf.download(T,start="2000-01-01",auto_adjust=True,progress=False,threads=True)["Close"]
d.to_parquet("data/yf_probe.parquet")
for t in T:
    s=d[t].dropna() if t in d else pd.Series(dtype=float)
    print(f"{t:12s} n={len(s):5d} {s.index.min().date() if len(s) else None} -> {s.index.max().date() if len(s) else None}")
