"""Feature engineering shared by the model, transfer and application scripts.

Everything on the feature side is satellite / reanalysis / static only, expressed relative to each reservoir's OWN
climatology, so the same features exist for a dam that publishes nothing. The label (generation anomaly) is likewise
relative to the dam's own seasonal normal."""
import numpy as np
import pandas as pd

from common import DATA, RESULTS

LAGS = (1, 3, 6, 12)
AREA_FEATS = ["a0", "a1", "a3", "a6", "a12", "da1", "da3", "dA1", "dA3", "fullness", "a_mean12"]
CLIM_FEATS = ["p1", "p3", "p6", "p12", "p24", "s12", "t3"]
PHASE_FEATS = ["ph_sin", "ph_cos"]
STATIC_FEATS = ["area_cv", "log_area", "log_cap", "log_res_time", "depth_avg_m", "log_basin", "abs_lat", "elevation_m"]


def load_inputs():
    panel = pd.read_parquet(RESULTS / "panel_monthly.parquet")
    st = pd.read_csv(RESULTS / "dam_statics.csv")
    clim = pd.read_parquet(DATA / "basin_climate.parquet")
    basins = pd.read_parquet(DATA / "basins.parquet")
    st = st.merge(basins, on="gww_id", how="left")
    return panel, st, clim


def seasonal_anom(df, col, ref_mask, by="gww_id"):
    """(x - clim[month]) / mean(clim), with the climatology estimated on rows where ref_mask is True."""
    ref = df[ref_mask & df[col].notna()]
    cm = ref.groupby([by, ref.month.dt.month])[col].mean().rename("c").reset_index().rename(columns={"month": "moy"})
    mean = cm.groupby(by).c.mean().rename("cmean")
    n = cm.groupby(by).c.size().rename("nmoy")
    x = df[[by, "month", col]].assign(moy=df.month.dt.month).merge(cm, on=[by, "moy"], how="left").merge(mean, on=by, how="left").merge(n, on=by, how="left")
    out = (x[col] - x.c) / x.cmean.where(x.cmean > 0)
    out[x.nmoy < 12] = np.nan
    return out.values, x.c.values, x.cmean.values


def build(panel, st, clim, ref_end=None):
    """Feature table. ref_end: last month (inclusive) used for climatologies/normalisers; None = full record."""
    df = panel.sort_values(["gww_id", "month"]).reset_index(drop=True).copy()
    df = df.merge(clim, on=["gww_id", "month"], how="left")
    ref = (df.month <= ref_end) if ref_end is not None else pd.Series(True, index=df.index)
    ref &= df.month < "2026-01-01"

    df["a0"], _, amean = seasonal_anom(df, "area_km2", ref)
    g = df.groupby("gww_id")
    for k in LAGS:
        df[f"a{k}"] = g.a0.shift(k)
    df["da1"], df["da3"] = df.a0 - df.a1, df.a0 - df.a3
    rel = df.area_km2 / amean
    df["dA1"] = rel - rel.groupby(df.gww_id).shift(1)
    df["dA3"] = rel - rel.groupby(df.gww_id).shift(3)
    df["a_mean12"] = g.a0.transform(lambda s: s.rolling(12, min_periods=8).mean())
    q = df[ref].groupby("gww_id").area_km2.quantile([.05, .95]).unstack()
    lo, hi = df.gww_id.map(q[.05]), df.gww_id.map(q[.95])
    df["fullness"] = ((df.area_km2 - lo) / (hi - lo).where(hi > lo)).clip(-0.5, 1.5)

    # basin climate as fraction-of-normal over trailing windows
    for k in (1, 3, 6, 12, 24):
        df[f"_p{k}"] = g.precip_mm.transform(lambda s: s.rolling(k, min_periods=k).sum())
        df[f"p{k}"], _, _ = seasonal_anom(df, f"_p{k}", ref)
    df["_s12"] = g.snow_mm.transform(lambda s: s.rolling(12, min_periods=12).sum())
    norm = df[ref].groupby("gww_id")._p12.mean()
    smean = df[ref].groupby("gww_id")._s12.mean()
    df["s12"] = (df._s12 - df.gww_id.map(smean)) / df.gww_id.map(norm)
    df["_t3"] = g.temp_c.transform(lambda s: s.rolling(3, min_periods=3).mean())
    tc = df[ref].groupby(["gww_id", df[ref].month.dt.month])._t3.mean()
    df["t3"] = df._t3 - pd.MultiIndex.from_arrays([df.gww_id, df.month.dt.month]).map(tc.to_dict())

    # seasonal phase relative to the reservoir's own climatological area peak (hemisphere-agnostic)
    ac = df[ref].groupby(["gww_id", df[ref].month.dt.month]).area_km2.mean().unstack()
    peak = ac.idxmax(axis=1)
    ph = (df.month.dt.month - df.gww_id.map(peak)) % 12
    df["ph_sin"], df["ph_cos"] = np.sin(2 * np.pi * ph / 12), np.cos(2 * np.pi * ph / 12)

    s = st.set_index("gww_id")
    cv = df[ref].groupby("gww_id").area_km2.agg(lambda x: x.std() / x.mean())
    df["area_cv"] = df.gww_id.map(cv)
    df["log_area"] = np.log10(df.gww_id.map(s.gww_poly_km2).clip(lower=0.1))
    df["log_cap"] = np.log10(df.gww_id.map(s.capacity_mw).clip(lower=0.1))
    df["log_res_time"] = np.log10(df.gww_id.map(s.res_time_days).clip(lower=0.1))
    df["depth_avg_m"] = df.gww_id.map(s.depth_avg_m)
    df["log_basin"] = np.log10(df.gww_id.map(s.basin_km2).clip(lower=1))
    df["abs_lat"] = df.gww_id.map(s.lat).abs()
    df["elevation_m"] = df.gww_id.map(s.elevation_m)

    # label: generation anomaly vs own seasonal normal (same reference period)
    if "mwh" in df:
        df["y"], df["gen_clim"], df["gen_mean"] = seasonal_anom(df, "mwh", ref)
        df["y"] = df.y.clip(-1.5, 3.0)
        gg = df.groupby("gww_id")
        df["y_lag1"], df["y_lag3"] = gg.y.shift(1), gg.y.shift(3)
    return df.drop(columns=[c for c in df.columns if c.startswith("_")])
