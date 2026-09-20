"""Build every pre-registered target series -> data/targets_monthly.parquet, data/targets_weekly.parquet (+ control factors)."""
import numpy as np, pandas as pd, yfinance as yf
from pathlib import Path
from signals import ons, wecc_monthly
D = Path(__file__).parent / "data"
TICKERS = "ALI=F HG=F BZ=F CL=F NG=F 000807.SZ 000001.SS AA ^GSPC NHY.OL OSEBX.OL AXIA3.SA CMIG4.SA EGIE3.SA ENEV3.SA ENGI11.SA ^BVSP FM.TO ^GSPTSE USDZMW=X PCG EIX XLU FRO DHT BAS.DE ^GDAXI ^SPGSCI DX-Y.NYB".split()

def prices():
    fn = D / "yf_daily.parquet"
    if not fn.exists():
        p = yf.download(TICKERS, start="2000-01-01", end="2026-09-19", auto_adjust=True, progress=False)["Close"]
        al = pd.read_parquet(D / "shfe_al0_sina.parquet"); p["SHFE_AL"] = pd.Series(al["收盘价"].astype(float).values, index=pd.to_datetime(al["日期"]))
        p.to_parquet(fn)
    return pd.read_parquet(fn)

def rets(p, rule):
    """Period log return = sum of daily log returns. Daily |log return| > 1.5 is a vendor splice error (e.g. CMIG4.SA 2006-05-09, -8.3) and is nulled.
    A period with no fresh print is NaN, never a zero return. The incomplete final month (2026-09) is dropped."""
    d = np.log(p).diff(); d = d.where(d.abs() <= 1.5)
    r = d.resample(rule).sum(min_count=1)
    if rule == "ME": r.index = r.index.to_period("M").to_timestamp(); r = r[r.index < "2026-09-01"]
    return r

def derive(r, spread=None):
    o = pd.DataFrame(index=r.index)
    for t in ["SHFE_AL", "ALI=F", "HG=F", "NG=F", "BZ=F"]: o[t] = r[t]
    o["USDZMW"] = r["USDZMW=X"]
    for a, b in [("000807.SZ", "000001.SS"), ("AA", "^GSPC"), ("NHY.OL", "OSEBX.OL"), ("AXIA3.SA", "^BVSP"), ("CMIG4.SA", "^BVSP"), ("EGIE3.SA", "^BVSP"), ("ENEV3.SA", "^BVSP"), ("ENGI11.SA", "^BVSP"), ("FM.TO", "^GSPTSE"), ("PCG", "XLU"), ("EIX", "XLU"), ("BAS.DE", "^GDAXI")]:
        o[f"{a}-{b}"] = r[a] - r[b]
    o["TANKERS(FRO,DHT)-^GSPC"] = r[["FRO", "DHT"]].mean(axis=1, skipna=False) - r["^GSPC"]
    if spread is not None: o["d_BZ-CL_spread"] = spread
    return o

def deseason(s): return s - s.groupby(s.index.month).transform("mean")

def build():
    p = prices()
    rm, rw = rets(p, "ME"), rets(p, "W-FRI")
    sp = (p["BZ=F"] - p["CL=F"]).resample("W-FRI").last().diff()
    TM, TW = derive(rm), derive(rw, sp)
    ear = pd.read_parquet(D / "ear_seco_monthly.parquet").ear_seco_pct
    TM["d3_EAR_SECO_anom"] = deseason(ear).diff(3)
    cmo = ons("CMO_SEMANAL", ["val_cmomediasemanal"]); cmo = cmo[cmo.id_subsistema == "SE"].set_index("din_instante").val_cmomediasemanal.resample("MS").mean()
    cmo.to_frame("cmo_se").to_parquet(D / "cmo_se_monthly.parquet")
    TM["d3_logCMO_SE"] = np.log1p(cmo).diff(3)
    bal = ons("BALANCO_ENERGIA_SUBSISTEMA", ["val_gerhidraulica", "val_gertermica", "val_gereolica", "val_gersolar"]); bal = bal[bal.id_subsistema == "SIN"].set_index("din_instante")
    bm = bal[["val_gerhidraulica", "val_gertermica", "val_gereolica", "val_gersolar"]].resample("MS").sum()
    share = (bm.val_gertermica / bm.sum(axis=1)); share.to_frame("thermal_share").to_parquet(D / "thermal_share_monthly.parquet")
    TM["d3_thermal_share_SIN"] = deseason(share).diff(3)
    w = wecc_monthly(); w = w[(w.index >= "2018-07-01") & (w.index < "2026-09-01")]
    TM["d3_WECC_hydro_anom"] = deseason(w.hydro / 1e6).diff(3)
    TM["d3_WECC_fossil_anom"] = deseason((w.gas + w.coal) / 1e6).diff(3)
    if (D / "nordpool_daily.parquet").exists():
        np_ = pd.read_parquet(D / "nordpool_daily.parquet")["SYS"].dropna()
        TW["dlog_NordPool_SYS"] = np.log(np_.clip(lower=1).resample("W-FRI").mean()).diff()      # Energi Data Service carries SYS for 2000-2010 only
        no2 = pd.read_parquet(D / "nordpool_daily.parquet")["NO2"].dropna()["2011":]
        TW["dlog_NordPool_NO2"] = np.log(no2.clip(lower=1).resample("W-FRI").mean()).diff()                 # exploratory only
    F = {"M": rm[["^SPGSCI", "DX-Y.NYB", "000001.SS", "HG=F"]], "W": rw[["^SPGSCI", "DX-Y.NYB", "000001.SS", "HG=F"]]}
    TM.to_parquet(D / "targets_monthly.parquet"); TW.to_parquet(D / "targets_weekly.parquet")
    F["M"].to_parquet(D / "factors_monthly.parquet"); F["W"].to_parquet(D / "factors_weekly.parquet")
    return TM, TW

if __name__ == "__main__":
    TM, TW = build()
    for T in (TM, TW): print(pd.DataFrame({"n": T.count(), "first": T.apply(lambda s: s.first_valid_index()), "last": T.apply(lambda s: s.last_valid_index()), "std": T.std().round(4)}).to_string())
