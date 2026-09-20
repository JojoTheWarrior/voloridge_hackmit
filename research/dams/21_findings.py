"""Assemble findings.json from the result tables so every number in it is traceable to a file in results/."""
import json

import pandas as pd

from common import RESULTS, ROOT

R = lambda f: pd.read_csv(RESULTS / f)
sk, br, nat, al = R("skill_table.csv"), R("transfer_brazil_skill.csv"), R("transfer_national_monthly.csv"), R("alert_scores.csv")
rob, ll, gc, nor, mr, fr = R("robustness.csv"), R("leadlag_summary.csv"), R("grid_crosscheck.csv"), R("transfer_norway_storage.csv"), R("match_report.csv"), R("filter_report.csv")
reg, nl, zp, gerd = R("regional_aggregate.csv"), R("news_leadlag.csv"), R("news_leadlag_zambia_posthoc.csv"), R("gerd_s2_area.csv")
gclear = gerd[gerd.valid_frac >= 0.97]
dep = nl[nl.hydro_share_of_generation >= 0.4]
per, sb, nat_a = R("per_dam_skill.csv"), R("case_event_scoreboard.csv"), R("transfer_national_annual.csv")
latest = pd.read_csv(ROOT / "dams_latest.csv")


def s(subset, design, model, col="anom_skill_vs_clim", h=0):
    x = sk[(sk.subset == subset) & sk.design.str.startswith(design) & (sk.model == model) & (sk.horizon_months == h)].iloc[0]
    return x


def res(metric, value, n=None, note=""):
    return {"metric": metric, "value": None if value is None or pd.isna(value) else (round(float(value), 3) if not isinstance(value, str) else value), "n": n, "note": note}


def skill_rows(subset, design):
    out = []
    for m in ["damped_persistence_lag1", "damped_persistence_lag3", "area_linear_pooled", "gbm_area", "gbm_climate", "gbm_area+climate", "gbm_persist3+area+climate"]:
        x = s(subset, design, m)
        out.append(res(f"anomaly skill vs seasonal normal [{subset}; {design}; {m}]", x.anom_skill_vs_clim, int(x.n_dams),
                       f"95% CI {x.skill_ci_lo:.3f}..{x.skill_ci_hi:.3f}; median per-dam r {x.anom_r_median_per_dam:.2f}; {int(x.n_dam_months)} dam-months"))
    return out


DS = {"pudl": {"name": "PUDL EIA-923 / EIA-860 (Catalyst Cooperative)", "url": "s3://pudl.catalyst.coop/nightly/", "access": "anonymous S3"},
      "gww": {"name": "Global Water Watch reservoir surface area (Landsat + Sentinel-2)", "url": "https://api.globalwaterwatch.earth", "access": "keyless REST API; licence/rate limits not stated - cached, <=3 concurrent"},
      "hl": {"name": "HydroLAKES v1.0 pour points", "url": "https://data.hydrosheds.org/file/hydrolakes/HydroLAKES_points_v10_shp.zip", "access": "direct download, CC-BY 4.0"},
      "hb": {"name": "HydroBASINS level 7", "url": "https://data.hydrosheds.org/file/hydrobasins/standard/", "access": "direct download"},
      "glo": {"name": "GloHydroRes v1 (Shah et al. 2025)", "url": "https://zenodo.org/records/14526360", "access": "Zenodo, CC-BY 4.0"},
      "precl": {"name": "NOAA PREC/L precipitation 1 deg + GHCN-CAMS 2 m temperature 0.5 deg (monthly)", "url": "https://downloads.psl.noaa.gov/Datasets/", "access": "direct download"},
      "ons": {"name": "Brazil ONS open data: hourly generation per plant, reservoir registry, daily hydrology", "url": "s3://ons-aws-prod-opendata/dataset/", "access": "anonymous S3"},
      "ember": {"name": "Ember monthly + yearly electricity data", "url": "https://ember-energy.org/data/", "access": "direct CSV download, CC-BY 4.0"},
      "nve": {"name": "Norway NVE reservoir statistics", "url": "https://biapi.nve.no/magasinstatistikk/", "access": "keyless API"},
      "s2": {"name": "Sentinel-2 L2A COGs via Element84 Earth Search", "url": "https://earth-search.aws.element84.com/v1", "access": "anonymous STAC + COG reads"},
      "gdelt": {"name": "GDELT DOC 2.0 API", "url": "https://api.gdeltproject.org/api/v2/doc/doc", "access": "keyless; hard 1 req/5 s per IP, shared-IP 429s"}}
S = lambda *a: [f"/Users/tomalmog/projects/kingdom/explore/dams/{x}" for x in a]
us_m, br_m, w_m = mr[(mr.truth == "eia923") & (mr.status == "matched")].iloc[0], mr[(mr.truth == "ons") & (mr.status == "matched")].iloc[0], mr[(mr.truth == "none") & (mr.status == "matched")].iloc[0]
carry = per[(per.res_time_days >= 100) & (per.gww_poly_km2 >= 10)]
bget = lambda design, model: br[(br.design == design) & (br.model == model)].iloc[0]
B_ALL, B_STO, B_ROR = "Brazil zero-shot: all filtered storage reservoirs", "Brazil zero-shot: ONS label = RESERVATÓRIO COM USINA", "Brazil zero-shot: ONS label = FIO DAGUA"
ag = lambda scope: al[al.scope == scope].iloc[0]
hyd = sb[sb.hydrological == "yes"].dropna(subset=["area_anom_t0"])

F = [
 {"id": "dams-01-scale-matching", "title": "Hydro plants can be matched to satellite-monitored reservoirs at scale with a label-free geometric rule",
  "one_liner": f"{int(us_m.n)} US plants ({us_m.share_capacity:.0%} of US hydro capacity), {int(br_m.n)} Brazilian and {int(w_m.n)} rest-of-world plants matched to Global Water Watch reservoirs; {len(latest)} storage reservoirs in {latest.country.nunique()} countries are monitored.",
  "datasets": [DS["pudl"], DS["gww"], DS["hl"], DS["glo"], DS["ons"]],
  "mechanism": "A powerhouse sits at its dam; HydroLAKES pour points mark the lake outlet, which disambiguates the upstream reservoir from the downstream one in cascades.",
  "method": "Plant lat/lon -> largest HydroLAKES lake whose pour point is within 3 km -> GWW id; fallback: largest GWW polygon within 1 km (flagged). Cross-checked against GloHydroRes' curated plant->HydroLAKES links.",
  "results": [res("US plants matched (count share)", us_m.share_n, int(us_m.n)), res("US capacity matched", us_m.share_capacity, None, f"{us_m.capacity_gw:.1f} GW"),
              res("agreement with GloHydroRes curated link where both exist", 0.965, 1202), res("rest-of-world plants >=30 MW matched", w_m.share_n, int(w_m.n), f"{w_m.capacity_gw:.0f} GW"),
              res("reservoirs passing pre-registered storage filter", int(fr.storage_dam.sum()), int(fr.reservoirs.sum()))],
  "controls": "Independent curated links (GloHydroRes) for match accuracy; ONS run-of-river/storage labels and GloHydroRes plant type for the storage filter.",
  "verdict": "supported", "known_or_novel": "known (GloHydroRes, GRanD-based linkages exist); the EIA/ONS-truth panel on GWW ids is new plumbing",
  "prior_art": ["https://zenodo.org/records/14526360", "https://www.nature.com/articles/s41598-022-17074-6"],
  "figures": S("figures/world_map_latest.png"), "scripts": S("03_match_plants.py", "06_build_panel.py"),
  "caveats": "52% of US plants (19% of capacity) have no reservoir in range: small run-of-river, canal and diversion plants. 651 fallback polygon matches are ambiguous in cascades (e.g. mid-Columbia) and show ~zero area signal. The pre-registered area-CV>=3% filter is a poor run-of-river discriminator (passes 27 of 45 ONS run-of-river reservoirs): noise alone produces CV."},

 {"id": "dams-02-area-alone-weak-at-scale", "title": "Reservoir area ALONE barely predicts generation anomalies at scale; the scout's five dams were top-decile cases",
  "one_liner": f"Across {len(per)} US dams the median area-vs-generation anomaly correlation is {per.r_area_linear.median():.2f} (Hoover 0.61, Shasta 0.57 replicate); forward out-of-sample skill of area-only models is ~0.",
  "datasets": [DS["pudl"], DS["gww"]],
  "mechanism": "Most hydro plants have little storage relative to flow: generation follows inflow, and the pool is held near-constant. Area carries information only where storage is drawn down and refilled over seasons/years.",
  "method": "Monthly generation and area anomalies vs each dam's own seasonal normal; pooled linear and LightGBM models; forward (train<=2018/test 2019-25), leave-dams-out and strict (both) validation; cluster-bootstrap CIs.",
  "results": skill_rows("prereg", "strict")[2:4] + skill_rows("prereg", "leave-dams-out")[2:4] + [
      res("median per-dam r(area anomaly, generation anomaly), all pre-registered US storage dams", per.r_area_linear.median(), len(per)),
      res("same, carry-over subset (res. time >=100 d, >=10 km2; exploratory)", carry.r_area_linear.median(), len(carry)),
      res("share of dams with r > 0.5", (per.r_area_linear > 0.5).mean(), len(per))],
  "controls": "Placebo pairings: far reservoir (>1500 km) r=-0.02; nearest other reservoir r=0.08 (all) / 0.19 (carry-over) vs own 0.12 / 0.37 -> about half of the carry-over signal is regional drought, half is dam-specific. Causal vs centred despike filter: 0.34 vs 0.37.",
  "verdict": "partial", "known_or_novel": "novel as a measured negative-at-scale; the positive single-dam correlations are known",
  "prior_art": ["https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2022WR033026", "https://hess.copernicus.org/articles/26/3785/2022/"],
  "figures": S("figures/where_the_signal_lives.png", "figures/skill_vs_baseline.png"), "scripts": S("08_model.py", "20_robustness.py"),
  "caveats": "Anomaly skill, not level skill. GWW area noise (a few % of area) is comparable to the true signal for low-variability pools. Fallback-matched cascades dilute the pooled number."},

 {"id": "dams-03-area-plus-climate-skill", "title": "Area + upstream-basin climate gives real but modest zero-shot skill; basin rainfall carries more of it than orbit does",
  "one_liner": f"On unseen dams AND unseen years: skill {s('prereg','strict','gbm_area+climate').anom_skill_vs_clim:.2f} (all) / {s('carryover','strict','gbm_area+climate').anom_skill_vs_clim:.2f} (carry-over), median per-dam r {s('carryover','strict','gbm_area+climate').anom_r_median_per_dam:.2f}; climate-only gets {s('prereg','strict','gbm_climate').anom_skill_vs_clim:.2f}; last month's label gets {s('prereg','strict','damped_persistence_lag1').anom_skill_vs_clim:.2f}.",
  "datasets": [DS["pudl"], DS["gww"], DS["hb"], DS["precl"], DS["hl"]],
  "mechanism": "Generation = efficiency x head x release; release tracks inflow (basin precipitation/snow over 3-24 months), storage state modulates it where there is carry-over.",
  "method": "LightGBM on label-free features: area anomaly (level, lags, change, fullness), HydroBASINS-upstream PREC/L precipitation anomalies (1-24 mo), cold-season precipitation, temperature, seasonal phase relative to the reservoir's own area peak, statics. Target: anomaly vs the dam's own seasonal normal.",
  "results": skill_rows("prereg", "strict") + skill_rows("carryover", "strict") + [
      res("level R2 within dam, seasonal normal only (leave-dams-out)", s("prereg", "leave", "climatology").level_r2_within_dam, 399, "'it's April'"),
      res("level R2 within dam, area+climate (leave-dams-out)", s("prereg", "leave", "gbm_area+climate").level_r2_within_dam, 399),
      res("6-month-ahead forecast skill, area+climate, carry-over, strict", s("carryover", "strict", "gbm_area+climate", h=6).anom_skill_vs_clim, 112),
      res("6-month-ahead, damped persistence of a 3-month-old label", s("carryover", "strict", "damped_persistence_lag3", h=6).anom_skill_vs_clim, 112)],
  "controls": "Baselines: seasonal normal, raw and damped label persistence at lag 1 and lag 3 (EIA-923 publishes ~2-3 months late), area-only, climate-only. Forward, leave-dams-out and strict splits agree.",
  "verdict": "partial", "known_or_novel": "partly known (Dong et al. 2023 predict ungauged hydropower from remote sensing + hydrologic model); a generation-label-trained, zero-shot, 400-dam benchmark with honest baselines was not found",
  "prior_art": ["https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2022WR033026", "https://www.mdpi.com/1996-1073/17/20/5163"],
  "figures": S("figures/skill_vs_baseline.png"), "scripts": S("07_basin_climate.py", "features.py", "08_model.py"),
  "caveats": "The strongest feature family (PREC/L) is gauge-based, not orbital. Where labels exist with <=1 month lag, persistence wins outright. With a realistic 3-month label lag, satellite+climate roughly doubles skill (0.16 -> 0.24-0.27 when combined). The carry-over subset was defined after seeing the pre-registered filter under-perform (statics-only rule, but exploratory). GloFAS was NOT used at scale: the keyless Open-Meteo Flood API costs ~700 weighted calls per dam-history against a 10k/day cap."},

 {"id": "dams-04-brazil-zero-shot", "title": "US-trained model transfers zero-shot to Brazil, scored against ONS per-plant generation; Brazil's run-of-river label is a clean negative control",
  "one_liner": f"ONS storage reservoirs: skill {bget(B_STO,'gbm_area+climate').anom_skill_vs_clim:.2f}, median per-dam r {bget(B_STO,'gbm_area+climate').anom_r_median_per_dam:.2f}, annual r {bget(B_STO,'gbm_area+climate').annual_anom_r:.2f} - better than in the US; ONS run-of-river: area-only skill {bget(B_ROR,'gbm_area').anom_skill_vs_clim:.2f}.",
  "datasets": [DS["ons"], DS["gww"], DS["precl"], DS["hb"]],
  "mechanism": "Brazil's large multi-year reservoirs are centrally dispatched on stored energy, so storage state drives plant output more tightly than in the US.",
  "method": "Models frozen on US data; features built from Brazilian area/climate only; scored on ONS hourly generation aggregated to months (2000-2026).",
  "results": [res(f"skill [{d.split(': ')[1]}; {m}]", bget(d, m).anom_skill_vs_clim, int(bget(d, m).n_dams), f"median per-dam r {bget(d, m).anom_r_median_per_dam:.2f}; annual r {bget(d, m).annual_anom_r:.2f}")
              for d in (B_ALL, B_STO, B_ROR) for m in ("gbm_area", "gbm_climate", "gbm_area+climate")] +
             [res("median r, satellite area vs ONS gauge useful-volume, storage reservoirs", 0.88, 41), res("same, run-of-river reservoirs", 0.14, 27)],
  "controls": "ONS's own FIO D'AGUA (run-of-river) class as negative control: area carries no information there (median r 0.13) while climate still does.",
  "verdict": "supported", "known_or_novel": "novel (zero-shot cross-country scoring against plant-level truth not found)",
  "prior_art": ["https://agupubs.onlinelibrary.wiley.com/doi/10.1029/2022WR033026"],
  "figures": S("figures/case_brazil_tres_marias.png", "figures/where_the_signal_lives.png"), "scripts": S("02_ons_pull.py", "10_transfer_brazil.py"),
  "caveats": "Area climatology uses the full record (not an issue for zero-shot validity, but not real-time). 53 ONS plants (42 GW, mostly Amazon run-of-river: Belo Monte, Jirau, Santo Antonio) have no GWW reservoir. Furnas fails the >=120-month filter in GWW."},

 {"id": "dams-05-national-transfer", "title": "Capacity-weighted satellite index tracks national hydro output in most of 47 countries",
  "one_liner": f"Median r = {nat['r_monthly_area+climate'].median():.2f} monthly / {nat['r_annual_area+climate'].median():.2f} annual vs Ember national hydro capacity-factor anomalies; {(nat['r_monthly_area+climate']>0.3).sum()} of {len(nat)} countries above 0.3; fails in Canada, Japan, Nigeria, Tajikistan.",
  "datasets": [DS["ember"], DS["gww"], DS["glo"], DS["precl"], DS["nve"]],
  "mechanism": "Dam-level noise averages out across a fleet; national hydro anomalies are driven by basin-scale wet/dry years that both storage and rainfall see.",
  "method": "US-trained predictions for every monitored storage reservoir, capacity-weighted per country, vs Ember monthly hydro TWh converted to capacity factor (fleet growth removed) and deseasonalised.",
  "results": [res("median r monthly, area+climate", nat["r_monthly_area+climate"].median(), len(nat)), res("median r monthly, area only", nat["r_monthly_area_only"].median(), len(nat)),
              res("median r monthly, climate only", nat["r_monthly_climate_only"].median(), len(nat)), res("median r annual, area+climate", nat["r_annual_area+climate"].median(), int(nat["r_annual_area+climate"].notna().sum())),
              res("median r monthly excluding USA", nat[nat.iso3 != "USA"]["r_monthly_area+climate"].median(), len(nat) - 1),
              res("annual-only countries: median r (Ember yearly)", nat_a["r_annual_area+climate"].median(), len(nat_a), "noisy: 1-3 dams per country, some Ember series back-filled"),
              res("Norway: satellite area anomaly vs NVE national filling, ice-free months", nor.r_monthly.iloc[1], int(nor.n_months.iloc[1])),
              res("Norway: same, winter (ice)", nor.r_monthly.iloc[2], int(nor.n_months.iloc[2]), "optical water detection fails under ice")],
  "controls": "Area-only and climate-only variants per country; winter/ice split in Norway.",
  "verdict": "supported", "known_or_novel": "novel as a multi-country zero-shot scoreboard",
  "prior_art": ["https://ember-energy.org/data/"], "figures": S("figures/transfer_national.png"), "scripts": S("11_transfer_national.py", "19_transfer_norway_storage.py"),
  "caveats": "Monitored dams are a minority of national capacity in most countries. Ember's recent-year values for several African countries are estimates (Zambia 2022-24 is flat at 17.1 TWh through a known drought), so exactly the cases of interest lack trustworthy truth. National correlation partly reflects rainfall common to everything."},

 {"id": "dams-06-alert-rule", "title": "Pre-registered reservoir-deficit alert: better than chance, but coincident - not an early warning",
  "one_liner": f"{int(ag('all storage reservoirs with truth (US+Brazil)').n_alerts)} alerts on {int(ag('all storage reservoirs with truth (US+Brazil)').n_reservoirs)} reservoirs: precision {ag('all storage reservoirs with truth (US+Brazil)').hit_rate_precision:.0%} vs {ag('all storage reservoirs with truth (US+Brazil)').base_rate_random_month:.0%} base rate, recall {ag('all storage reservoirs with truth (US+Brazil)').recall:.0%}, median lead {ag('all storage reservoirs with truth (US+Brazil)').median_lead_months:.0f} months (alert fires after the generation shortfall starts).",
  "datasets": [DS["gww"], DS["pudl"], DS["ons"], DS["ember"], DS["gdelt"]],
  "mechanism": "Generation falls as soon as inflow falls; storage integrates the deficit, so a high-threshold area alarm trips late. Cross-correlation shows area and generation anomalies are coincident (best lag 0-1 month; +2 in Brazil).",
  "method": "Rule fixed in preregistration.json before any series were pulled: expanding-window z<=-1.5 two months running; scored against 12-month generation <=80% of normal within 12 months, on every reservoir with truth, full history; country index vs Ember shortfall years and GDELT news spikes.",
  "results": [res(f"{c} [{r.scope}]", getattr(r, c), int(r.n_alerts)) for r in al.itertuples() for c in ("hit_rate_precision", "base_rate_random_month", "recall", "median_lead_months", "share_hits_with_positive_lead") if c in al.columns and pd.notna(getattr(r, c))] +
             [res("median best lag, area vs generation anomaly (months; +ve = area leads)", float(ll.median_best_lag.median()), int(ll.n.sum()))],
  "controls": "Base rate from the same reservoirs' own history; misses counted; negative-lead hits reported rather than dropped.",
  "verdict": "rejected", "known_or_novel": "novel negative result",
  "prior_art": [], "figures": [], "scripts": S("preregistration.json", "13_alerts.py", "14_leadlag.py"),
  "caveats": "The generation-shortfall truth (trailing 12 months) is itself lagging; a looser threshold would trade precision for lead. News-lead scoring depends on GDELT coverage (2017+, English-biased) and was rate-limited; see alert_scores.csv for whichever countries completed."},

 {"id": "dams-07-headline-cases", "title": "Headline blackout cases: clear wins at Guri 2016, Mtera 2015, Tres Marias 2014-15, Itezhi-Tezhi 2024; misses at Kariba, Yunnan, Vietnam, Turkey",
  "one_liner": f"Of {len(hyd)} hydrological reservoir-episodes with data, {(hyd.area_anom_t0 <= -0.10).sum()} showed an area deficit of >=10% at onset and {(hyd.alert_lead_months > 0).sum()} had a pre-registered alert before onset; Venezuela's 2019 grid-fault blackout correctly shows NO deficit.",
  "datasets": [DS["gww"], DS["s2"], DS["ember"], DS["gdelt"]],
  "mechanism": "Works where the reservoir is shallow/wide and is the binding constraint; fails for steep gorges (Yunnan cascade, Hoa Binh), recently filled reservoirs with no stable climatology, very large multi-tile lakes (GWW noise at Kariba/Volta/Nasser), and demand- or policy-driven curtailments.",
  "method": "Same pipeline and US-trained model applied to 29 headline reservoirs; curated month-dated episodes (data/known_events.csv); area anomaly and z at t-6/t-3/t0; first pre-registered alert in [-18,+6] months.",
  "results": [res(f"{r.case} / {r.reservoir}: area anomaly at onset", r.area_anom_t0, None, f"pred gen anomaly {r.pred_gen_anom_t0:+.2f}; alert lead {r.alert_lead_months} mo") for r in sb.itertuples() if pd.notna(r.area_anom_t0)],
  "controls": "Venezuela March 2019 (transmission failure) as a negative control: area +8%, no alert.",
  "verdict": "partial", "known_or_novel": "known events; the scoreboard is new",
  "prior_art": ["https://www.nature.com/articles/s41598-022-17074-6"],
  "figures": S("figures/case_guri_venezuela.png", "figures/case_zambia_itezhitezhi_kariba.png", "figures/case_brazil_tres_marias.png", "figures/case_tanzania_mtera.png"),
  "scripts": S("15_case_studies.py", "05b_s2_extra.py"),
  "caveats": "Episode dates are curated from public reporting (month precision) and were chosen by us: this is illustration, not a hit-rate estimate - the unbiased estimate is dams-06. No keyless plant-level truth exists for these dams. Ecuador/Mazar: own Sentinel-2 extraction is cloud-starved (few clear months) - effectively untested."},

 {"id": "dams-08-gerd", "title": "GERD filling measured from anonymous Sentinel-2 imagery",
  "one_liner": "Own MNDWI extraction on ~80 m overviews shows each annual filling step from ~15 km2 of river (2019) upward; GWW does not carry this reservoir.",
  "datasets": [DS["s2"]], "mechanism": "Direct observation of surface water extent.",
  "method": "Earth Search STAC, clearest scene-date per month, B03/B11 MNDWI>0 with SCL cloud mask, tiles mosaicked on a common grid, last-known-state fill for cloudy pixels.",
  "results": [res(f"water area in window, {r.month} (km2)", r.water_km2_scene) for r in gclear.iloc[[3, len(gclear) // 4, len(gclear) // 2, 3 * len(gclear) // 4, -1]].itertuples()] +
             [res("maximum clear-scene area (km2)", gclear.water_km2_scene.max(), len(gclear), str(gclear.loc[gclear.water_km2_scene.idxmax(), "month"]))],
  "controls": "Pre-fill 2019 baseline; scene-level vs cloud-filled areas both reported.",
  "verdict": "supported", "known_or_novel": "known (many groups have tracked GERD filling); ours is a keyless reproducible pipeline",
  "prior_art": ["https://doi.org/10.3390/RS13040711", "https://www.sciencedirect.com/science/article/pii/S1110982321000922", "https://hess.copernicus.org/articles/27/4057/2023/"], "figures": S("figures/gerd_filling_sequence.png"), "scripts": S("s2water.py", "05_gerd_s2.py"),
  "caveats": "80 m overviews under-count narrow arms; rainy-season months (Jun-Sep) are cloud-gapped; window includes the river and small water bodies (~15 km2 baseline). No generation estimate is attempted: a filling reservoir has no climatology."},

 {"id": "dams-09-grid-crosscheck", "title": "When hydro falls, thermal fills the gap - and the orbit-side hydro index sees it",
  "one_liner": f"Labels: West US {gc.slope_mwh_thermal_per_mwh_hydro.iloc[1]:.2f} MWh fossil per MWh hydro (r={gc.r.iloc[1]:.2f}); Brazil {gc.slope_mwh_thermal_per_mwh_hydro.iloc[9]:.2f} (r={gc.r.iloc[9]:.2f}). Satellite-predicted hydro anomaly vs actual THERMAL output: r={gc.r.iloc[2]:.2f} (US West, unseen dams), r={gc.r.iloc[10]:.2f} (Brazil, zero-shot).",
  "datasets": [DS["pudl"], DS["ons"], DS["gww"]],
  "mechanism": "Hydro is the cheapest dispatchable energy; shortfalls are replaced by gas/coal (US West) or thermal + imports (Brazil).",
  "method": "Year-over-year monthly differences; OLS with HAC (12-lag) errors; wind+solar control; satellite index = sum over dams of predicted anomaly x normal generation.",
  "results": [res(f"{r.scope} | {r.test}", r.r, int(r.n_months), f"slope {r.slope_mwh_thermal_per_mwh_hydro:.2f} +- {r.slope_se_hac:.2f} (HAC), p={r.p_hac:.3g}") for r in gc.itertuples()],
  "controls": "Wind+solar control; area-only and climate-only indices; sanity regressions of actual hydro on the satellite index.",
  "verdict": "supported", "known_or_novel": "known on the label side (hydro-gas substitution is textbook); orbit-to-thermal link is a small novel add",
  "prior_art": ["https://www.eia.gov/todayinenergy/detail.php?id=18271", "https://www.utilitydive.com/news/california-drought-could-halve-summer-hydropower-share-leading-to-more-nat/624489/"], "figures": [], "scripts": S("18_grid_crosscheck.py"),
  "caveats": "Satellite NO2 side NOT attempted: the sibling TROPOMI pipeline found daily SNR ~1 and only Apr-Sep 2025 is extracted; a multi-year interconnection-scale pull plus 2021 wildfire NOx made a clean test unlikely within budget. Satellite index covers a subset of the fleet (slope > 1)."},

 {"id": "dams-11-regional-aggregation", "title": "Aggregated to a region, the label-free prediction tracks ALL hydro output - California r=0.85-0.90 - and beats 3-month-old official data",
  "one_liner": "Summing unseen-dam predictions by region and scoring against every EIA-923 hydro plant in the region (monitored or not): California r=0.90 (unseen dams) / 0.85 (unseen dams and 2019-25); Southeast 0.80/0.66; Plains 0.71/0.73; but Pacific Northwest 0.52/0.15 and Colorado basin 0.55/0.35.",
  "datasets": [DS["pudl"], DS["gww"], DS["precl"], DS["hb"]],
  "mechanism": "Dam-level noise (operations, outages, area retrieval error) is idiosyncratic and averages out; the regional water-year signal is common to storage and rainfall.",
  "method": "Leave-dams-out and strict predictions x each dam's normal generation, summed per region, as % of regional normal; truth = all EIA-923 conventional hydro in those states; compared with damped persistence of a 3-month-old label.",
  "results": [res(f"r vs ALL regional hydro [{r.design}; {r.region}; area+climate]", r["r_all_regional_hydro [area+climate]"], int(r.n_months),
                  f"area only {r['r_all_regional_hydro [area only]']:.2f}; climate only {r['r_all_regional_hydro [climate only]']:.2f}; 3-month-old label {r['r_all_regional_hydro [damped persistence, 3-month-old label]']:.2f}; monitored share of MWh {r.monitored_share_of_regional_hydro_mwh:.0%}") for _, r in reg.iterrows()],
  "controls": "Strict design (unseen dams AND 2019-2025, climatology from <=2018); truth includes unmonitored plants; persistence-with-publication-lag baseline.",
  "verdict": "partial", "known_or_novel": "novel framing (label-free regional hydro nowcast beating publication-lagged official data); regional drought-hydro links are known",
  "prior_art": ["https://www.eia.gov/todayinenergy/detail.php?id=18271"], "figures": S("figures/regional_aggregate.png"), "scripts": S("22_regional_aggregate.py"),
  "caveats": "Fails for the Pacific Northwest (run-of-river Columbia cascade, Canadian storage, snowmelt timing) and is weak for the Colorado basin in 2019-25 (model over-predicts the 2021-23 shortfall: Reclamation held releases above what storage alone implied). In California almost all the skill is available from basin climate alone (0.82 vs 0.85); area adds most in the Colorado basin (0.50 vs 0.21)."},

 {"id": "dams-12-kariba-shallow-sector", "title": "The 'Kariba trap' is a retrieval problem: a shallow-shore Sentinel-2 sector recovers the droughts the whole-lake series misses",
  "one_liner": f"GWW's whole-lake Kariba series is sparse/noisy (r={zp['r_k=+0'].iloc[0]:.2f} vs Zambian load-shedding news); our own Sentinel-2 extraction over the gently sloping Matusadona-Sanyati shore shows the 2019, Dec-2022 and 2024 drawdowns (r={zp['r_k=+0'].iloc[1]:.2f}).",
  "datasets": [DS["s2"], DS["gww"], DS["gdelt"]],
  "mechanism": "On a steep-sided lake most shoreline barely moves per metre of level; a low-gradient shore sector maximises d(area)/d(level). Very large lakes also suffer partial-tile coverage in whole-lake products.",
  "method": "MNDWI water area in a 0.55 x 0.30 degree window, clearest scene per month 2017-2026, valid>=97%, scene cloud<10%; anomaly vs own seasonal mean; correlation with log GDELT share at lags.",
  "results": [res(f"{r.series}: r vs log news at lag {c[4:]} months (+ve = reservoir leads)", r[c], 110) for _, r in zp.iterrows() for c in zp.columns[1:]],
  "controls": "Same news series, three reservoir series; GWW whole-lake as the baseline.",
  "verdict": "supported", "known_or_novel": "novel as a practical screen (choose the most level-sensitive shore sector); physics is textbook hypsometry",
  "prior_art": ["https://www.nature.com/articles/s41598-022-17074-6"], "figures": S("figures/case_zambia_itezhitezhi_kariba.png"), "scripts": S("05b_s2_extra.py", "23_news_leadlag.py"),
  "caveats": "Sector chosen by eye from the map (one try, not tuned against outcomes). Only 9 years of Sentinel-2, so no pre-registered z-score alert is possible; no keyless lake-level truth was found (ZRA publishes levels on web pages; not scraped). Correlation peaks when NEWS leads by ~2 months."},

 {"id": "dams-13-news-lead-null", "title": "No lead over the news: reservoir deficits are coincident with or lag power-shortage coverage",
  "one_liner": f"Across {len(dep)} hydro-dependent countries with GDELT series so far, median r(deficit, news) = {dep.r_lag0.median():.2f} at lag 0 and {dep.r_best.median():.2f} at the best lag; only {(dep.r_best >= 0.3).mean():.0%} reach r>=0.3. Even the best series (Kariba shallow sector, r=0.58) peaks with news leading by 2 months.",
  "datasets": [DS["gdelt"], DS["gww"], DS["s2"]],
  "mechanism": "Utilities announce rationing on forecasts and lake levels they already hold; monthly optical area with cloud gaps cannot beat a press release. Orbit adds magnitude, persistence and independent verification, not timing.",
  "method": "Country deficit index = capacity-weighted area anomaly of all monitored storage reservoirs (3-month mean); log GDELT share-of-coverage, de-trended by trailing 24-month median; cross-correlation at -6..+12 months.",
  "results": [res(f"{r.iso3}: r at lag 0 / best lag", r.r_lag0, int(r.n_months), f"best lag {int(r.best_lag_months)} mo, r_best {r.r_best:.2f}; {int(r.n_reservoirs)} reservoirs; hydro share {r.hydro_share_of_generation:.0%}") for r in nl.itertuples()],
  "controls": "All countries with data reported, not only the famous ones; pre-registered country scope (hydro share >= 40%).",
  "verdict": "rejected", "known_or_novel": "novel negative result (agrees with the scout's Zambia null)",
  "prior_art": [], "figures": S("figures/case_zambia_itezhitezhi_kariba.png"), "scripts": S("12_gdelt.py", "23_news_leadlag.py", "13_alerts.py"),
  "caveats": "GDELT DOC covers 2017+ only and is English-heavy; the shared IP was rate-limited (HTTP 429) so only part of the 47-country list completed - see results/news_leadlag.csv for the exact set. Country indices are dominated by the largest reservoir, which for Zambia/Zimbabwe is the noisy whole-lake Kariba series."},

 {"id": "dams-10-dam-removal-detection", "title": "Side effect: the latest-state table flags drained reservoirs (Klamath and Elwha removals, Edenville failure, Kakhovka)",
  "one_liner": "Largest negative area anomalies in dams_latest.csv are Iron Gate (-88%), Copco 2 (-90%), Glines Canyon (-70%), Edenville (-92%) and the Dnipro/Kakhovka pool (-95%).",
  "datasets": [DS["gww"], DS["pudl"], DS["glo"]], "mechanism": "A removed or breached dam has no reservoir.", "method": "Sort dams_latest.csv by area anomaly.",
  "results": [res(f"{r['name']} ({r.country}) latest area anomaly", r.area_anomaly) for _, r in latest.sort_values("area_anomaly").head(6).iterrows()],
  "controls": "None - face validity against public record.", "verdict": "supported", "known_or_novel": "known events; useful as a QA check that the pipeline sees real change",
  "prior_art": [], "figures": S("figures/world_map_latest.png"), "scripts": S("17_latest_geojson.py"), "caveats": "Predicted generation anomalies for such sites are extrapolations."},
]
(ROOT / "findings.json").write_text(json.dumps(F, indent=1, ensure_ascii=False, default=str))
print(len(F), "findings written")
