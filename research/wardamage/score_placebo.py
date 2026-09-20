"""Detector false-positive rate on pre-war placebo windows.
(a) matched: identical 72 h rule as events, window starts every 3 days 2025-11-01..2026-02-24, baseline = all data before window.
(b) frozen: baseline ends 2025-10-31, count flagged asset-days over 2025-11-01..2026-02-27 (task spec)."""
import sys, json, numpy as np, pandas as pd, score_engine as E
def run(sites, p, tag):
    rows, frozen = [], []
    for s in sites.itertuples():
        q = E.near(p, s.lat, s.lon, s.radius_km + 1)
        for t0 in pd.date_range("2025-11-01", "2026-02-24", freq="3D"):
            r = E.evaluate(q, t0, s.radius_km, follow_days=3)
            rows.append(dict(site=s.name, flare_site=r["base_share_lit"] >= 0.5, t0=t0, flag=r["flag"], flag_novel=r["flag_novel"], flag_excess=r["flag_excess"], n_novel=r["n_novel_72h"]))
        m = E.mark_novel(q, pd.Timestamp("2025-11-01")); m = m[(m.dist_km <= s.radius_km) & m.novel & (m.date >= "2025-11-01") & (m.date <= "2026-02-27")]
        d = m.groupby("date").FRP.agg(["size", "max"])
        frozen.append(dict(site=s.name, flagged_days=int(((d["size"] >= 2) | (d["max"] >= 10)).sum()), any_novel_days=len(d)))
    w = pd.DataFrame(rows); f = pd.DataFrame(frozen); w.to_csv(f"score_out/placebo_windows_{tag}.csv", index=False); f.to_csv(f"score_out/placebo_frozen_{tag}.csv", index=False)
    months = 119 / 30.4
    out = dict(n_sites=len(sites), n_windows=len(w), window_fpr=round(float(w.flag.mean()), 4), window_fpr_novel_only=round(float(w.flag_novel.mean()), 4),
               window_fpr_flare_sites=round(float(w[w.flare_site].flag.mean()), 4), window_fpr_nonflare_sites=round(float(w[~w.flare_site].flag.mean()), 4),
               n_windows_flare=int(w.flare_site.sum()), n_windows_nonflare=int((~w.flare_site).sum()),
               frozen_flagged_days_per_asset_month=round(float(f.flagged_days.sum() / (len(f) * months)), 3),
               frozen_any_novel_days_per_asset_month=round(float(f.any_novel_days.sum() / (len(f) * months)), 3),
               frozen_share_sites_with_any_flag=round(float((f.flagged_days > 0).mean()), 3))
    json.dump(out, open(f"score_out/placebo_{tag}.json", "w"), indent=1); print(tag, out); return out
if __name__ == "__main__":
    p = E.load_hotspots()
    a = pd.read_csv("assets.csv"); a["radius_km"] = 3.0
    run(a, p, "assets")
