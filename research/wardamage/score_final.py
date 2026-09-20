"""Assemble final scoreboard: auto detector output + satellite-first rows + GDELT first-news + reviewed verdicts + summary + placebo."""
import json, numpy as np, pandas as pd, score_engine as E, score_placebo as P
p = E.load_hotspots()
s = pd.read_csv("score_out/scoreboard_auto.csv", parse_dates=["first_det_utc", "window_start_utc", "event_time_utc"])
# ---- satellite-first candidates (round-1 novel episodes with no event in the news-first list), scored with the same engine
a = pd.read_csv("assets.csv").set_index("name")
SF = [("S01","2026-03-03","Tehran-Karaj B1 bridge area","unmatched: many Tehran strikes 3-5 Mar, nothing naming this site","",""),
      ("S02","2026-03-20","Riyadh refinery","partial: Iranian missile strike on Riyadh 20 Mar (1 killed); no report naming the refinery","2026-03-20 07:30","https://organiser.org/2026/03/20/344893/world/iran-missile-strike-on-riyadh-raises-tensions-as-saudi-arabia-signals-possible-response/"),
      ("S03","2026-04-09","Abqaiq processing","matched: Saudi statement that attacks forced energy facilities to halt, output -600 kb/d (facility list not given)","2026-04-09 20:15","https://www.straitstimes.com/world/middle-east/attacks-cut-saudi-oil-output-and-east-west-pipeline-flow-state-news-agency-says"),
      ("S04","2026-05-11","Riyadh refinery","unmatched","",""), ("S05","2026-05-29","SATORP Jubail","unmatched","",""),
      ("S06","2026-06-13","Mesaieed Industrial City","unmatched (13 Jun: Qatar denied a US media report of LNG facility damage)","",""),
      ("S07","2026-06-14","Gachsaran field","unmatched","",""), ("S08","2026-07-06","Ras Laffan LNG/Industrial City","unmatched","",""),
      ("S09","2026-07-07","Mesaieed Industrial City","unmatched","",""),
      ("S10","2026-07-26","Abqaiq processing","matched: Houthi/Iraqi-militia drone attacks on Aramco sites 25-28 Jul (Wikipedia: >30 drone attacks on Eastern Province oil infrastructure in 72 h)","2026-07-25 10:00","https://www.moneycontrol.com/world/saudi-aramco-oil-facility-hit-as-yemen-escalates-attacks-after-riyadh-strikes-houthi-targets-article-13983346.html"),
      ("S11","2026-08-16","SATORP Jubail","unmatched","","")]
rows = []
for sid, d, asset, match, nt, nu in SF:
    la, lo = a.loc[asset, ["lat", "lon"]]; t0 = pd.Timestamp(d) - pd.Timedelta(hours=4); r = E.evaluate(E.near(p, la, lo, 6), t0, 5.0)
    oc = E.overpass_check(p, la, lo, t0, 24); oc72 = E.overpass_check(p, la, lo, t0, 72)
    r.update(oc); r.update(n_passes_72h=oc72["n_passes_24h"], n_passes_neighbours_seen_72h=oc72["n_passes_neighbours_seen"], event_id=sid, war=2026, event_date=d, time_utc="", place=asset + " (satellite-first)",
             lat=la, lon=lo, radius_km=5.0, coord_source="round1_asset", country=a.loc[asset, "country"], asset_type=a.loc[asset, "type"], attacker="", reported=match, source_url=nu,
             discovery="satellite_first", round1_known=1, window_start_utc=t0, flare_site=bool(r["base_share_lit"] >= 0.5), news_override=nt)
    rows.append(r)
s = pd.concat([s, pd.DataFrame(rows)], ignore_index=True)
# ---- first news (GDELT raw 15-min export files, URL-slug match) with reviewed overrides
n = pd.read_csv("score_out/news_first_auto.csv", parse_dates=["first_news_gdelt"]).set_index("event_id")
OV = {"E10": ("2026-03-03 15:30", "https://www.indiatvnews.com/news/world/fire-erupts-at-uae-s-fujairah-oil-hub-as-middle-east-conflict-disrupts-energy-supplies-2026-03-03-1032481"),
      "E05": ("2026-03-01 10:00", "https://www.arabtimesonline.com/news/oman-says-attack-on-oil-tanker-in-strait-of-hormuz-wounds-4/"),
      "E06": ("2026-03-02 01:45", "https://en.apa.az/asia/bahrain-claims-iran-attacked-port-salman-494081"),
      "E25": ("2026-03-13 23:30", "https://www.marketscreener.com/news/us-attacks-iran-s-kharg-island-trump-says-ce7e5fd3df89f220"),
      "E29": ("2026-03-16 08:45", "https://www.omanobserver.om/article/1186203/world/region/drone-attack-again-in-fujairah-no-casualties-reported"),
      "E38": ("2026-03-27 15:45", "https://en.apa.az/asia/air-force-bombs-two-large-steel-factories-in-iran-partially-owned-by-irgc-498556"),
      "E39": ("2026-03-27 15:45", "https://en.apa.az/asia/air-force-bombs-two-large-steel-factories-in-iran-partially-owned-by-irgc-498556"),
      "E41": ("2026-03-29 00:00", "https://www.gdnonline.com:443/Details/1379806/Alba-confirms-attack-on-facility"),
      "E54": ("2026-04-07 11:45", "https://economictimes.indiatimes.com/news/international/world-news/iran-kharg-island-under-attack-oil-hub-middle-east-israel-war-escalation-trump-oil-"),
      "E58": ("2026-05-04 16:30", "https://www.dailysabah.com/world/mid-east/iranian-drones-target-oil-facility-in-uaes-fujairah"),
      "E21": ("", ""), "E42": ("", ""), "E17": ("", ""), "E63": ("", "")}
def news(r):
    if r.discovery == "satellite_first": return (pd.Timestamp(r.news_override) if r.news_override else pd.NaT, r.source_url, "gdelt_raw_export_urlslug_15min (post-hoc match)" if r.news_override else "none_found")
    if r.event_id in OV: t, u = OV[r.event_id]; return (pd.Timestamp(t) if t else pd.NaT, u, "gdelt_raw_export_urlslug_15min (reviewed)" if t else "none_found (slug search; auto match was a false positive)")
    if r.war == 2025 and r.event_id != "T06": return pd.NaT, "", "gdelt_gap (raw files 404 from 2025-06-14 18:00 into July 2025); web search gave date-only"
    if r.event_id in n.index and pd.notna(n.loc[r.event_id, "first_news_gdelt"]): return n.loc[r.event_id, "first_news_gdelt"], n.loc[r.event_id, "first_news_url"], "gdelt_raw_export_urlslug_15min"
    return pd.NaT, "", "none_found (slug search)"
nn = s.apply(news, axis=1, result_type="expand"); s["first_news_utc"], s["first_news_url"], s["first_news_method"] = pd.to_datetime(nn[0]), nn[1], nn[2]
s["first_news_resolution"] = np.where(s.first_news_utc.notna(), "15 min (GDELT ingest batch; upper bound on publication; URL-slug match can miss earlier liveblogs/wire)", "")
# ---- reviewed verdicts (auto rule kept in verdict_auto)
def refined(r):
    v, why = r.verdict_auto, r.verdict_reason_auto
    if pd.isna(v):  # satellite-first rows
        v, why = ("hit", "novel-cell pixels (this is how the row was found; not an independent test)") if r.flag_novel else ("ambiguous", "round-1 novel episode not reproduced at r=5 km")
    if v == "ambiguous" and r.flag_excess and r.flare_site and r.peak_daily_frp_72h >= 3 * r.excess_thr: v, why = "hit", "FRP excess >=3x the excess threshold at a permanent-flare site"
    if v == "not_observable" and r.n_det_72h > 0: v, why = "miss", "site itself detected in 72 h (so not fully cloudy) but no novel/excess signal; no neighbour flare seen in first 24 h"
    return v, why
rf = s.apply(refined, axis=1, result_type="expand"); s["verdict"], s["verdict_reason"] = rf[0], rf[1]
MAN = {"E14": ("hit", "MANUAL: 10.9 MW at 22:01 UTC 7 Mar + 3 more days at a site dark since Jun 2025; auto rule missed it because the Jun-2025 fire made these cells 'known' and daily FRP < 20 MW floor", "2026-03-07 22:01", "N21", "N", 10.9),
       "E30": ("miss", "MANUAL downgrade: only 2 novel pixels totalling 3.3 MW, 7.5 km from centre inside a 9 km flare field, FRP below baseline p99; indistinguishable from flare jitter", None, None, None, None),
       "E53": ("ambiguous", "MANUAL downgrade: 3 novel pixels / 5.5 MW in a 9 km flare field; daily FRP 1072 MW is high but under 2x p99", None, None, None, None),
       "E17": ("ambiguous", "MANUAL downgrade: 3 weak pixels (4 MW) 4.8 km from an approximate coordinate, >24 h after strike", None, None, None, None),
       "E50": ("ambiguous", "MANUAL downgrade: FRP excess inside the Ruwais flare complex (site lit 48% of baseline days)", None, None, None, None),
       "E41": ("ambiguous", "MANUAL downgrade: 20.4 MW is just over the 20 MW floor, ~1 day after attack, 2 km from smelter, next to BAPCO flares", None, None, None, None),
       "E29": ("ambiguous", "MANUAL downgrade: tanks already burning since E26 (14 Mar); new strike not separable from the ongoing fire", None, None, None, None)}
for k, (v, why, t, sat, dn, frp) in MAN.items():
    i = s.index[s.event_id == k][0]; s.loc[i, ["verdict", "verdict_reason"]] = [v, why]
    if t: s.loc[i, ["first_det_utc", "first_det_sat", "first_det_daynight", "first_det_frp"]] = [pd.Timestamp(t), sat, dn, frp]
s.loc[s.verdict.isin(["miss", "not_observable"]), ["first_det_utc", "first_det_sat", "first_det_daynight", "first_det_frp", "first_det_dist_km"]] = [pd.NaT, None, None, np.nan, np.nan]
s["detection_mode"] = np.where(s.verdict != "hit", "", np.where(s.flag_novel, "novel_cell", np.where(s.flag_excess, "frp_excess", "manual")))
s["latency_vs_event_h"] = ((s.first_det_utc - s.event_time_utc).dt.total_seconds() / 3600).round(1)
s["latency_vs_news_h"] = ((s.first_det_utc - s.first_news_utc).dt.total_seconds() / 3600).round(1)
s["site_class"] = np.where(s.flare_site, "permanent_flare", "non_flare")
s["cloud_proxy_24h"] = np.where(s.n_persistent_neighbours < 3, "no_reference_flares", np.where(s.n_passes_neighbours_seen > 0, "clear_on_>=1_pass", "no_neighbour_seen"))
cols = ["event_id","discovery","war","event_date","time_utc","place","country","asset_type","lat","lon","radius_km","coord_source","site_class","reported","source_url","round1_known",
        "first_news_utc","first_news_method","first_news_resolution","first_news_url","window_start_utc","first_det_utc","first_det_sat","first_det_daynight","first_det_frp","first_det_dist_km",
        "latency_vs_event_h","latency_vs_news_h","n_det_72h","n_novel_72h","novel_frp_72h","peak_daily_frp_72h","peak_daily_frp_30d","peak_day_30d","burn_days","n_novel_30d",
        "base_days","base_share_lit","base_mean_frp","base_p99_frp","base_max_frp","excess_thr","n_persistent_neighbours","n_passes_24h","n_passes_neighbours_seen","best_pass_neighbour_frac","cloud_proxy_24h",
        "n_passes_72h","n_passes_neighbours_seen_72h","flag_novel","flag_excess","verdict_auto","verdict","detection_mode","verdict_reason"]
s[cols].to_csv("score_out/scoreboard.csv", index=False)
# ---- summary (news-first events only for hit rates)
nf = s[s.discovery == "news_first"]; w26 = nf[nf.war == 2026]
def rate(d): c = d.verdict.value_counts(); return dict(n=len(d), hit=int(c.get("hit", 0)), ambiguous=int(c.get("ambiguous", 0)), miss=int(c.get("miss", 0)), not_observable=int(c.get("not_observable", 0)), hit_rate=round(float((d.verdict == "hit").mean()), 3) if len(d) else None)
lat = nf[(nf.verdict == "hit") & nf.latency_vs_news_h.notna()]
fresh = nf[nf.round1_known == 0]
summ = dict(n_events_news_first=len(nf), n_satellite_first=int((s.discovery == "satellite_first").sum()), overall=rate(nf), war2026=rate(w26), war2025=rate(nf[nf.war == 2025]),
            auto_rule_only=dict(nf.verdict_auto.value_counts()), excluding_round1_known=rate(fresh),
            by_site_class={k: rate(d) for k, d in nf.groupby("site_class")}, by_asset_type={k: rate(d) for k, d in nf.groupby("asset_type")},
            hits_by_first_detection_daynight=dict(nf[nf.verdict == "hit"].first_det_daynight.value_counts()), hits_by_detection_mode=dict(nf[nf.verdict == "hit"].detection_mode.value_counts()),
            latency_vs_news_h=dict(n=len(lat), median=float(lat.latency_vs_news_h.median()), p25=float(lat.latency_vs_news_h.quantile(.25)), p75=float(lat.latency_vs_news_h.quantile(.75)), min=float(lat.latency_vs_news_h.min()), max=float(lat.latency_vs_news_h.max()),
                                   n_satellite_before_news=int((lat.latency_vs_news_h < 0).sum()), events_satellite_before_news=lat[lat.latency_vs_news_h < 0].event_id.tolist()),
            latency_vs_event_h={r.event_id: r.latency_vs_event_h for r in nf[nf.latency_vs_event_h.notna()].itertuples()},
            events_with_reported_clock_time=int(nf.event_time_utc.notna().sum()), events_with_gdelt_first_news=int(nf.first_news_utc.notna().sum()),
            satellite_first={r.event_id: r.reported for r in s[s.discovery == "satellite_first"].itertuples()})
sites = nf.drop_duplicates(["lat", "lon", "radius_km"])[["place", "lat", "lon", "radius_km"]].rename(columns={"place": "name"})
summ["placebo_event_sites"] = P.run(sites, p, "event_sites"); summ["placebo_round1_assets_r3km"] = json.load(open("score_out/placebo_assets.json"))
summ["gdelt_access"] = dict(doc_api="HTTP 429 on every attempt (5 tries over ~40 min, single requests) - unusable from this IP", raw_15min_export="works keyless; 9,672 files (~650 MB) fetched; 2025-06-14 18:00 -> early Jul 2025 files are 404 (GDELT gap)",
                            repo_cache="data/cache/gdelt_daily.parquet is daily-only; gdelt_live.py pulls v1 daily + 4 GKG files/day, no sub-daily event timing")
json.dump(summ, open("score_out/scoreboard_summary.json", "w"), indent=1, default=str)
print(json.dumps(summ, indent=1, default=str)[:6000])
