"""Pre-registered reservoir-deficit alert rule (preregistration.json), applied to EVERY monitored storage reservoir over the
full history, scored against (a) plant generation shortfalls where truth exists (US, Brazil), (b) Ember national hydro
shortfall years, (c) GDELT power-shortage news spikes (2017+). Reports hits, false alarms, misses, base rates and leads.
Outputs results/alerts_reservoir.csv, alerts_country.csv, alert_scores.csv, country_deficit_index.parquet"""
import numpy as np
import pandas as pd

from common import DATA, RESULTS

Z_ON, Z_OFF, MIN_PRIOR, SD_FLOOR, REFRACT, WINDOW = -1.5, -0.75, 8, 0.02, 12, 12


def expanding_z(s):
    """z-score of each month vs the same calendar month in PRIOR years only."""
    z = pd.Series(np.nan, index=s.index)
    for moy in range(1, 13):
        x = s[s.index.month == moy]
        prior_n = x.notna().cumsum().shift(1)
        mu = x.expanding().mean().shift(1)
        sd = x.expanding().std().shift(1)
        all_mu = s.expanding().mean().shift(1).reindex(x.index)
        z[x.index] = ((x - mu) / np.maximum(sd, SD_FLOOR * all_mu)).where(prior_n >= MIN_PRIOR)
    return z


def alerts_from_z(z):
    """Onset: z <= Z_ON two months running. End: z > Z_OFF two months running. 12-month refractory after an end."""
    out, active, last_end = [], None, None
    idx, v = z.index, z.values
    for i in range(1, len(v)):
        if active is None:
            if v[i] <= Z_ON and v[i - 1] <= Z_ON and (last_end is None or (idx[i].to_period("M") - last_end.to_period("M")).n >= REFRACT):
                active = idx[i]
        elif v[i] > Z_OFF and v[i - 1] > Z_OFF:
            out.append((active, idx[i]))
            active, last_end = None, idx[i]
    if active is not None:
        out.append((active, pd.NaT))
    return out


def episodes(flag, merge_gap=6):
    """Contiguous runs of True (gaps < merge_gap months merged) -> list of (start, end)."""
    t = flag[flag].index
    eps = []
    for m in t:
        if eps and (m.to_period("M") - eps[-1][1].to_period("M")).n <= merge_gap:
            eps[-1][1] = m
        else:
            eps.append([m, m])
    return eps


def months_between(a, b):
    return (b.to_period("M") - a.to_period("M")).n


def score(alerts, events):
    """alerts: onset months; events: (start, end). Hit = an event overlaps [onset, onset+WINDOW]; an alert raised while an
    event is already under way still counts as a hit but gets a negative lead. Miss = event start with no alert in the
    WINDOW months before it."""
    hits, leads = 0, []
    for a in alerts:
        hit = [e for e in events if months_between(a, e[1]) >= 0 and months_between(a, e[0]) <= WINDOW]
        if hit:
            hits += 1
            leads.append(months_between(a, hit[0][0]))
    missed = sum(not any(0 <= months_between(a, e[0]) <= WINDOW for a in alerts) for e in events)
    return hits, leads, missed


panel = pd.read_parquet(RESULTS / "panel_monthly.parquet")
st = pd.read_csv(RESULTS / "dam_statics.csv")
st = st[st.storage_dam]
panel = panel[panel.gww_id.isin(st.gww_id) & (panel.month < "2026-07-01")]

rows, zs = [], []
for gid, d in panel.groupby("gww_id"):
    s = d.set_index("month").area_km2.asfreq("MS")
    z = expanding_z(s)
    zs.append(pd.DataFrame({"gww_id": gid, "month": z.index, "z": z.values}))
    al = alerts_from_z(z)
    g = d.set_index("month").mwh.asfreq("MS")
    ev, base, scor = [], np.nan, False
    if g.notna().sum() >= 120:
        t12 = g.rolling(12, min_periods=12).sum()
        norm = t12.expanding(min_periods=60).mean().shift(12)
        flag = (t12 <= 0.8 * norm) & norm.notna()
        ev = episodes(flag)
        valid = norm.notna() & z.notna()
        # base rate: share of valid months from which a shortfall month is reached within the window
        fut = pd.concat([flag.shift(-k) for k in range(0, WINDOW + 1)], axis=1).fillna(False).any(axis=1)
        base, scor = fut[valid].mean(), True
        al_s = [a for a in al if valid.get(a[0], False)]
        ev_s = [e for e in ev if valid.get(e[0], False)]
        hits, leads, missed = score([a[0] for a in al_s], ev_s)
    for a in al:
        rec = {"gww_id": gid, "onset": a[0], "end": a[1], "z_min": z[a[0]:a[1] if pd.notna(a[1]) else None].min(), "has_truth": scor}
        if scor and valid.get(a[0], False):
            hit = [e for e in ev if months_between(a[0], e[1]) >= 0 and months_between(a[0], e[0]) <= WINDOW]
            rec.update({"scored": True, "hit": bool(hit), "lead_months": months_between(a[0], hit[0][0]) if hit else np.nan})
        rows.append(rec)
    if scor:
        rows.append({"gww_id": gid, "onset": pd.NaT, "summary": True, "n_events": len(ev_s), "n_missed": missed, "base_rate": base,
                     "valid_months": int(valid.sum())})
R = pd.DataFrame(rows)
Z = pd.concat(zs)
A = R[R.summary != True].drop(columns=["summary", "n_events", "n_missed", "base_rate", "valid_months"], errors="ignore")  # noqa: E712
A = A.merge(st[["gww_id", "name", "country", "truth", "capacity_mw", "res_time_days", "gww_poly_km2"]], on="gww_id")
A.to_csv(RESULTS / "alerts_reservoir.csv", index=False)
S = R[R.summary == True].merge(st[["gww_id", "truth", "res_time_days", "gww_poly_km2"]], on="gww_id")  # noqa: E712

out = []
for label, a, s in [("all storage reservoirs with truth (US+Brazil)", A[A.scored == True], S),  # noqa: E712
                    ("US", A[(A.scored == True) & (A.truth == "eia923")], S[S.truth == "eia923"]),  # noqa: E712
                    ("Brazil", A[(A.scored == True) & (A.truth == "ons")], S[S.truth == "ons"]),  # noqa: E712
                    ("exploratory: carry-over subset", A[(A.scored == True) & (A.res_time_days >= 100) & (A.gww_poly_km2 >= 10)],  # noqa: E712
                     S[(S.res_time_days >= 100) & (S.gww_poly_km2 >= 10)])]:
    n = len(a)
    base = np.average(s.base_rate, weights=s.valid_months)
    out.append({"truth": "generation shortfall (12-mo gen <= 80% of normal) within 12 months", "scope": label, "n_reservoirs": len(s),
                "n_alerts": n, "hit_rate_precision": a.hit.mean(), "false_alarm_rate": 1 - a.hit.mean(), "base_rate_random_month": base,
                "lift_vs_base": a.hit.mean() / base, "n_events": int(s.n_events.sum()), "events_missed": int(s.n_missed.sum()),
                "recall": 1 - s.n_missed.sum() / max(1, s.n_events.sum()), "median_lead_months": a.lead_months.median(),
                "share_hits_with_positive_lead": (a.lead_months.dropna() > 0).mean()})

# ---------------- country level ----------------
import pycountry  # noqa: E402

FIX = {"Russia": "RUS", "Turkey": "TUR", "Iran": "IRN", "Vietnam": "VNM", "Laos": "LAO", "South Korea": "KOR", "North Korea": "PRK",
       "Bolivia": "BOL", "Venezuela": "VEN", "Tanzania": "TZA", "Syria": "SYR", "Democratic Republic of the Congo": "COD",
       "Ivory Coast": "CIV", "Macedonia": "MKD", "Czech Republic": "CZE", "USA": "USA", "BRA": "BRA", "Myanmar": "MMR"}


def iso3(n):
    try:
        return FIX.get(n) or pycountry.countries.lookup(n).alpha_3
    except LookupError:
        return None


st["iso3"] = st.country.map(iso3)
Zc = Z.merge(st[["gww_id", "iso3", "capacity_mw"]], on="gww_id").dropna(subset=["z", "iso3"])
idx = Zc.groupby(["iso3", "month"]).apply(lambda d: pd.Series({"z_index": np.average(d.z, weights=d.capacity_mw.fillna(1).clip(lower=1)),
                                                               "n": len(d)})).reset_index()
idx.to_parquet(RESULTS / "country_deficit_index.parquet")
yr = pd.read_parquet(DATA / "ember" / "yearly_country.parquet")
yr["share"] = yr.hydro_twh / yr.total_twh
dep = yr[(yr.year >= 2015) & (yr.year <= 2023)].groupby("iso3").share.mean()
scope = [c for c in idx.iso3.unique() if dep.get(c, 0) >= 0.4]
print("hydro-dependent countries monitored:", len(scope), scope)
yr["event"] = yr.groupby("iso3").hydro_twh.transform(lambda s: s <= 0.85 * s.rolling(5, min_periods=5).mean().shift(1))
news_fn = DATA / "gdelt_shortage_news.parquet"
news = pd.read_parquet(news_fn) if news_fn.exists() else pd.DataFrame(columns=["iso3", "month", "share_ppm"])
crow = []
for c in scope:
    z = idx[idx.iso3 == c].set_index("month").z_index.asfreq("MS")
    # the country index is a mean of z-scores, so re-standardise on prior values before applying the same thresholds
    zz = (z - z.expanding(min_periods=24).mean().shift(1)) / z.expanding(min_periods=24).std().shift(1)
    al = alerts_from_z(zz)
    evy = set(yr[(yr.iso3 == c) & yr.event].year)
    nw = news[news.iso3 == c].set_index("month").share_ppm if len(news) else pd.Series(dtype=float)
    spikes = []
    if nw.gt(0).sum() >= 24:
        thr = np.maximum(3 * nw.rolling(24, min_periods=12).median().shift(1), nw.quantile(0.9))
        spikes = [e[0] for e in episodes(nw >= thr, merge_gap=3)]
    for a in al:
        on = a[0]
        rec = {"iso3": c, "onset": on, "end": a[1], "hydro_share": dep[c], "ember_hit": bool({on.year, on.year + 1} & evy),
               "ember_scorable": on.year <= 2024}
        if len(spikes) and on >= pd.Timestamp("2017-01-01"):
            fut = [s for s in spikes if 0 <= months_between(on, s) <= WINDOW]
            rec.update({"news_scorable": True, "news_hit": bool(fut), "news_lead_months": months_between(on, fut[0]) if fut else np.nan})
        crow.append(rec)
    crow.append({"iso3": c, "summary": True, "n_event_years": len([y for y in evy if y >= 2010]), "n_news_spikes": len(spikes),
                 "event_years_missed": len([y for y in evy if y >= 2010 and not any(a[0].year in (y, y - 1) for a in al)]),
                 "news_spikes_missed": len([s for s in spikes if not any(0 <= months_between(a[0], s) <= WINDOW for a in al)])})
C = pd.DataFrame(crow)
C.to_csv(RESULTS / "alerts_country.csv", index=False)
ca, cs = C[C.summary != True], C[C.summary == True]  # noqa: E712
e = ca[ca.ember_scorable == True]  # noqa: E712
base_year = yr[yr.iso3.isin(scope) & (yr.year >= 2010)].event.mean()
out.append({"truth": "Ember national hydro year <= 85% of prior 5-yr mean (onset year or next)", "scope": f"{len(scope)} hydro-dependent countries",
            "n_alerts": len(e), "hit_rate_precision": e.ember_hit.mean(), "false_alarm_rate": 1 - e.ember_hit.mean(),
            "base_rate_random_month": 1 - (1 - base_year) ** 2, "lift_vs_base": e.ember_hit.mean() / (1 - (1 - base_year) ** 2),
            "n_events": int(cs.n_event_years.sum()), "events_missed": int(cs.event_years_missed.sum()),
            "recall": 1 - cs.event_years_missed.sum() / max(1, cs.n_event_years.sum())})
if "news_scorable" in ca:
    n = ca[ca.news_scorable == True]  # noqa: E712
    out.append({"truth": "GDELT power-shortage news spike within 12 months (2017+)", "scope": f"{n.iso3.nunique()} hydro-dependent countries with GDELT coverage",
                "n_alerts": len(n), "hit_rate_precision": n.news_hit.mean(), "false_alarm_rate": 1 - n.news_hit.mean(),
                "n_events": int(cs.n_news_spikes.sum()), "events_missed": int(cs.news_spikes_missed.sum()),
                "recall": 1 - cs.news_spikes_missed.sum() / max(1, cs.n_news_spikes.sum()), "median_lead_months": n.news_lead_months.median(),
                "share_hits_with_positive_lead": (n.news_lead_months.dropna() > 0).mean()})
O = pd.DataFrame(out)
O.to_csv(RESULTS / "alert_scores.csv", index=False)
print(O.round(3).T.to_string())
