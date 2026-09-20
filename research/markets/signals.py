"""Build every pre-registered physical signal exactly as specified in prereg.json -> data/signals_monthly.parquet, data/signals_weekly.parquet."""
import glob, json
import numpy as np, pandas as pd
from pathlib import Path
import gww
D = Path(__file__).parent / "data"
PRE = json.load(open(Path(__file__).parent / "prereg.json"))
SCOUT930 = "/Users/tomalmog/projects/kingdom/explore/scout/data/core_eia930__hourly_net_generation_by_energy_source.parquet"
WECC = ["AVA","AZPS","BANC","BPAT","CHPD","CISO","DOPD","EPE","GCPD","IID","IPCO","LDWP","NEVP","NWMT","PACE","PACW","PGE","PNM","PSCO","PSEI","SCL","SRP","TEPC","TIDC","TPWR","WACM","WALC","WAUW"]

def expanding_anom(s, key, min_years, center="mean"):
    """value minus the expanding mean/median of PRIOR values sharing the same seasonal key; scaled by expanding std of past anomalies."""
    g = s.groupby(key)
    prior = g.transform(lambda v: (v.expanding().mean() if center == "mean" else v.expanding().median()).shift(1))
    cnt = g.cumcount()
    a = (s - prior).where(cnt >= min_years)
    return a, a / a.expanding(min_periods=12).std().shift(1)

def monthly_area(rid):
    a = gww.area(rid); a = a[a >= 0.4 * a.median()]
    return a.resample("MS").median().interpolate(limit=2, limit_area="inside")

def reservoir_z(spec):
    zs = {}
    for name, rid in spec["gww"].items():
        m = monthly_area(rid)[spec["start"]:]
        zs[name] = expanding_anom(m, m.index.month, spec["min_years"])[1]
    return pd.DataFrame(zs)

def ons(prefix, cols):
    d = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(D / "ons" / f"{prefix}_*.parquet")))])
    for c in cols: d[c] = pd.to_numeric(d[c].astype(str).str.replace(",", "."), errors="coerce")
    return d

def wecc_monthly():
    fn = D / "wecc_monthly.parquet"
    if fn.exists(): return pd.read_parquet(fn)
    import pyarrow.dataset as ds
    t = ds.dataset(SCOUT930).to_table(filter=ds.field("balancing_authority_code_eia").isin(WECC)).to_pandas()
    t["v"] = t.net_generation_adjusted_mwh.fillna(t.net_generation_reported_mwh)
    src = t.generation_energy_source.astype(str).replace({"hydro_excluding_pumped_storage": "hydro", "pumped_storage": "hydro"})
    m = t.groupby([t.datetime_utc.dt.to_period("M").dt.to_timestamp(), src]).v.sum().unstack()
    m.to_parquet(fn); return m

def flare_weekly():
    fn = D / "flare_daily.parquet"
    if not fn.exists():
        R = {"libya": (9, 24, 25.5, 33), "basra": (46.3, 30.1, 48.1, 31.6), "algeria": (3, 27, 9, 33), "gulf_other": (47.8, 24.3, 51.8, 30.1)}
        fr = []
        for f in sorted(glob.glob(str(D / "gibs" / "*.parquet"))):
            d = pd.read_parquet(f)
            if len(d): fr.append(d[["LATITUDE", "LONGITUDE", "FRP"]].assign(date=pd.Timestamp(Path(f).stem)))
        h = pd.concat(fr); h["cx"] = (h.LONGITUDE / 0.02).round().astype(int); h["cy"] = (h.LATITUDE / 0.02).round().astype(int)
        pers = h.groupby(["cx", "cy"]).date.nunique() / h.date.nunique()
        h = h.merge(pers[pers >= 0.05].rename("p").reset_index(), on=["cx", "cy"])
        days = pd.DatetimeIndex(sorted(pd.Timestamp(Path(f).stem) for f in glob.glob(str(D / "gibs" / "*.parquet"))))
        out = {r: h[h.LONGITUDE.between(w, e) & h.LATITUDE.between(s, n)].groupby("date").FRP.sum().reindex(days, fill_value=0) for r, (w, s, e, n) in R.items()}
        pd.DataFrame(out).to_parquet(fn)
    d = pd.read_parquet(fn)
    wk = d.resample("W-THU").apply(lambda x: x.nlargest(3).mean())       # clear-sky proxy: mean of 3 largest daily sums
    lg = np.log(wk.where(wk > 0))
    out = {}
    for c in lg:
        a, _ = expanding_anom(lg[c].dropna(), lg[c].dropna().index.isocalendar().week.to_numpy(), 3)
        out[c + "_flare"] = a.diff(2); out[c + "_flare_level"] = a
    return pd.DataFrame(out), wk

def build():
    M, W = {}, {}
    for name, spec in PRE["reservoir_signals"].items():
        z = reservoir_z(spec); z.to_parquet(D / f"z_{name}.parquet")
        M[name + "|z"] = z.mean(axis=1, skipna=True).where(z.notna().sum(axis=1) >= max(1, len(z.columns) // 2))
    ear = ons("EAR_DIARIO_SUBSISTEMA", ["ear_verif_subsistema_percentual"]); ear = ear[ear.id_subsistema == "SE"]
    ear = ear.set_index(pd.to_datetime(ear.ear_data)).ear_verif_subsistema_percentual.resample("MS").mean()
    ear.to_frame("ear_seco_pct").to_parquet(D / "ear_seco_monthly.parquet")
    M["brazil_ear_seco|z"] = expanding_anom(ear, ear.index.month, 5)[1]
    w = wecc_monthly(); w = w[(w.index >= "2018-07-01") & (w.index < "2026-09-01")]
    M["wecc_hydro_anom|z"] = expanding_anom(w.hydro, w.index.month, 2)[1]      # series starts 2018-07: only 2 prior years required
    M = pd.DataFrame(M)
    for c in list(M): M[c.replace("|z", "|dz3")] = M[c] - M[c].shift(3)
    M.to_parquet(D / "signals_monthly.parquet")
    nve = pd.DataFrame(json.load(open(D / "nve_magasin.json"))); nve = nve[(nve.omrType == "NO")]
    f = nve.set_index(pd.to_datetime(nve.dato_Id)).fyllingsgrad.sort_index() * 100
    a, _ = expanding_anom(f, f.index.isocalendar().week.to_numpy(), 5, center="median")
    a.index = a.index + pd.offsets.Week(weekday=4) - pd.offsets.Week()            # NVE week ends Sunday -> label by the preceding Friday
    W["nve_fill|d1"] = a.diff()
    fl, wk = flare_weekly(); wk.to_parquet(D / "flare_weekly_clear.parquet")
    fl.index = fl.index + pd.Timedelta(days=1)                                     # Thu-ending signal week -> label by the Friday whose close follows it
    for c in ["libya", "basra", "algeria"]: W[c + "_flare|d2"] = fl[c + "_flare"]
    for n in ["rhine_kaub", "danube_placebo_budapest", "loire_placebo_saumur"]:
        q = pd.read_parquet(D / f"glofas_{n}.parquet").q
        q10 = q.expanding(min_periods=3650).quantile(0.10).shift(1)
        st = np.log(q10 / q).clip(lower=0).resample("W-THU").mean(); st.index = st.index + pd.Timedelta(days=1)
        W[n.split("_")[0] + "_stress|d1"] = st.diff()
    W = pd.DataFrame(W); W.to_parquet(D / "signals_weekly.parquet")
    return M, W

if __name__ == "__main__":
    M, W = build()
    print(M.describe().T[["count", "mean", "std", "min", "max"]].round(2).to_string())
    print(W.describe().T[["count", "mean", "std", "min", "max"]].round(3).to_string())
    print(M.apply(lambda s: (s.first_valid_index(), s.last_valid_index())).T.to_string())
