"""Score every event in score_out/events.csv against VIIRS; writes score_out/scoreboard_auto.csv (before manual verdict review)."""
import pandas as pd, numpy as np, score_engine as E
ev = pd.read_csv("score_out/events.csv", dtype={"time_utc": str}); p = E.load_hotspots()
rows = []
for e in ev.itertuples():
    timed = isinstance(e.time_utc, str) and len(e.time_utc) == 5
    t_event = pd.Timestamp(f"{e.event_date} {e.time_utc}") if timed else pd.NaT
    # undated-time events: window opens 20:00 UTC the previous day (= 00:00 local in the Gulf / 23:30 in Iran)
    t0 = t_event if timed else pd.Timestamp(e.event_date) - pd.Timedelta(hours=4)
    q = E.near(p, e.lat, e.lon, e.radius_km + 1)
    r = E.evaluate(q, t0, e.radius_km); oc = E.overpass_check(p, e.lat, e.lon, t0, 24); oc72 = E.overpass_check(p, e.lat, e.lon, t0, 72)
    r.update(oc); r.update(n_passes_72h=oc72["n_passes_24h"], n_passes_neighbours_seen_72h=oc72["n_passes_neighbours_seen"])
    r.update(event_id=e.event_id, window_start_utc=t0, event_time_utc=t_event, flare_site=bool(r["base_share_lit"] >= 0.5) if r["base_days"] else False)
    rows.append(r)
s = ev.merge(pd.DataFrame(rows), on="event_id")
def verdict(r):
    cloudy = r.n_persistent_neighbours >= 3 and r.n_passes_neighbours_seen_72h == 0
    if r.flag_novel: return "hit", "novel-cell pixels within radius in 72 h"
    if r.flag_excess: return ("ambiguous", "FRP excess only at a permanent-flare site (could be emergency flaring, not fire)") if r.flare_site else ("hit", "FRP excess over baseline at non-flare site")
    if cloudy: return "not_observable", "no persistent neighbour flare seen on any pass in 72 h (cloud/no coverage)"
    if r.n_novel_72h >= 1: return "ambiguous", "single weak novel pixel (<10 MW)"
    return "miss", "no novel pixel and no FRP excess in 72 h" + ("" if r.n_passes_neighbours_seen >= 1 or r.n_persistent_neighbours < 3 else "; first 24 h passes saw no neighbours")
v = s.apply(verdict, axis=1, result_type="expand"); s["verdict_auto"], s["verdict_reason_auto"] = v[0], v[1]
s.to_csv("score_out/scoreboard_auto.csv", index=False)
pd.set_option("display.width", 320); pd.set_option("display.max_rows", 200)
print(s[["event_id","event_date","place","radius_km","base_share_lit","base_p99_frp","n_det_72h","n_novel_72h","novel_frp_72h","peak_daily_frp_72h","excess_thr","first_det_utc","first_det_sat","first_det_dist_km","burn_days","peak_daily_frp_30d","n_persistent_neighbours","n_passes_24h","n_passes_neighbours_seen","verdict_auto"]].assign(place=lambda d: d.place.str[:28]).to_string(index=False))
