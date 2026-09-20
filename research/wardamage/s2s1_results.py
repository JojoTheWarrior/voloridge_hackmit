"""Assemble s2s1_results.csv: one row per (site, event, sensor, method) from the detector outputs.

Decision rules are applied mechanically (column `detected_rule`), but they were NOT pre-registered: the
detectors and these rules were iterated while looking at the data (S2 differencing went through 3 versions,
the hot threshold was picked from a 6-value sweep, the size-AND-peak false-alarm column was added after
seeing that the South Pars Refinery-4 blob had the top peak z, a second S1 detector was added after the
first was null). `detected` is the reviewed verdict; `notes` says where and why it departs from the rule.
  hot pixels : yes if largest novel cluster in a post-event scene (<=14 d) exceeds the max of the clear-scene
               pre-war null; ambiguous if it only exceeds the p95. No location test.
  change     : uses the largest blob within R m of a reported/VIIRS location. yes if placebo blobs at least that
               large (and, for S2, with at least that peak) occur < 0.05 per placebo pair/look; ambiguous < 0.5.
"""
import numpy as np, pandas as pd
from s2s1_common import *
from s2s1_events import EVENTS

R_NEAR = 700
ts = pd.read_csv(OUT / "s2_hot_timeseries.csv", parse_dates=["dt"])
s2b = pd.read_csv(OUT / "s2_change_blobs.csv")
s2n = pd.read_csv(OUT / "s2_change_placebo_null.csv")
s1b = pd.read_csv(OUT / "s1_change_blobs_vv.csv")
s1n = pd.read_csv(OUT / "s1_change_null_vv.csv")
skb = pd.read_csv(OUT / "s1_stack_blobs_vv.csv")
skn = pd.read_csv(OUT / "s1_stack_null_vv.csv")


def verdict(far, yes=0.05, amb=0.5):
    return "no" if np.isnan(far) else "yes" if far < yes else "ambiguous" if far < amb else "no"


rows = []
for ev in EVENTS:
    site, t = ev["site"], ev["t"]
    g = ts[ts.site == site]
    # --- S2 hot pixels
    null = g[g.baseline].max_novel_cluster
    cloudy_null = g[g.prewar & ~g.baseline & (g.n_hot > 0)].max_novel_cluster
    post = g[(g.dt > t) & (g.dt < t + pd.Timedelta(days=14)) & (g.n_hot + (g.cloud < 0.5) > 0)]
    first_look = post.iloc[0] if len(post) else None
    hit = post[post.max_novel_cluster > null.quantile(0.95)]
    best = hit.iloc[0] if len(hit) else first_look
    if best is not None:
        det = "yes" if best.max_novel_cluster > null.max() else "ambiguous" if len(hit) else "no"
        rows.append(dict(site=site, event=ev["event"], sensor="Sentinel-2", method="SWIR novel hot-pixel cluster (20 m)",
                         detected=det, first_acq_utc=best["dt"].strftime("%Y-%m-%dT%H:%MZ"),
                         latency_h=round((best["dt"] - t).total_seconds() / 3600, 1),
                         statistic=f"largest novel cluster {best.max_novel_cluster} px (scene cloud {best.cloud:.2f})",
                         null_threshold=f"clear pre-war p95={null.quantile(.95):.0f} max={null.max()} px; "
                                        f"cloudy pre-war max={cloudy_null.max() if len(cloudy_null) else 'NA'} px (n={len(cloudy_null)})",
                         n_placebo=len(null)))
    # --- S2 differencing
    for tag in ("first_usable", "first_clear"):
        b = s2b[(s2b.site == site) & (s2b.event == ev["event"]) & (s2b.pair == tag)]
        if b.empty:
            continue
        near = b[b.dist_m < R_NEAR].sort_values("npix", ascending=False)
        npairs = (s2n.site == site).sum()
        post_dt = ts[(ts.site == site) & (ts.date == b.post.iloc[0])].dt.iloc[0]
        far = near.placebo_blobs_per_pair_ge_size_and_peak.iloc[0] if len(near) else np.nan
        rows.append(dict(site=site, event=ev["event"], sensor="Sentinel-2", method=f"B12/B11/B8A differencing ({tag} post scene)",
                         detected=verdict(far), first_acq_utc=post_dt.strftime("%Y-%m-%dT%H:%MZ"),
                         latency_h=round((post_dt - t).total_seconds() / 3600, 1),
                         statistic=(f"largest blob <{R_NEAR} m of reported loc: {near.npix.iloc[0]} px, peak z {near.peak.iloc[0]:.1f}, "
                                    f"size rank {near['rank'].iloc[0]}/{len(b)}, {near.dist_m.iloc[0]} m from {near.nearest_reported.iloc[0]}"
                                    if len(near) else f"no blob <{R_NEAR} m of reported loc ({len(b)} blobs site-wide)"),
                         null_threshold=f"placebo blobs/pair >= size&peak: {far}; site-wide blobs {len(b)} vs placebo p50/p95 "
                                        f"{s2n[s2n.site == site].n_blobs.median():.0f}/{s2n[s2n.site == site].n_blobs.quantile(.95):.0f}",
                         n_placebo=npairs))
    # --- S1 first look (earliest orbit) and best orbit
    b = s1b[(s1b.site == site) & (s1b.event == ev["event"])]
    if len(b):
        nl = s1n[s1n.site == site]
        for orb, bo in b.groupby("orbit"):
            near = bo[bo.dist_m < R_NEAR].sort_values("npix", ascending=False)
            far = near.placebo_blobs_per_look_ge_size.iloc[0] if len(near) else np.nan
            weak = len(nl) < 5
            rows.append(dict(site=site, event=ev["event"], sensor="Sentinel-1", method=f"VV log-ratio first look, rel. orbit {orb}",
                             detected="ambiguous" if weak and len(near) else verdict(far, amb=1.0),
                             first_acq_utc=bo.post.iloc[0], latency_h=bo.latency_h.iloc[0],
                             statistic=(f"largest blob <{R_NEAR} m: {near.npix.iloc[0]} px ({near.area_m2.iloc[0]} m2), {near.mean_dB.iloc[0]:+.1f} dB, "
                                        f"size rank {(bo.npix > near.npix.iloc[0]).sum() + 1}/{len(bo)}, {near.dist_m.iloc[0]} m from {near.nearest_reported.iloc[0]}"
                                        if len(near) else f"no blob <{R_NEAR} m ({len(bo)} blobs site-wide)"),
                             null_threshold=f"placebo blobs/look >= size: {far}; null max blob p50/max {nl.max_blob_px.median():.0f}/{nl.max_blob_px.max()} px"
                                            + ("; NULL INADEQUATE (S1A-only 12-day archive)" if weak else ""),
                             n_placebo=len(nl)))
    k = skb[(skb.site == site) & (skb.event == ev["event"])]
    if len(k):
        near = k[k.dist_m < R_NEAR].sort_values("npix", ascending=False)
        far = near.placebo_blobs_per_look_ge_size.iloc[0] if len(near) else np.nan
        nn = (skn.site == site).sum()
        rows.append(dict(site=site, event=ev["event"], sensor="Sentinel-1", method="VV 4-vs-4 scene stack log-ratio (|dB|>3), all orbits",
                         detected="ambiguous" if nn < 5 and len(near) else verdict(far, amb=1.0),
                         first_acq_utc=near.last_post.iloc[0] if len(near) else k.last_post.min(),
                         latency_h=round(24 * (near.latency_d.iloc[0] if len(near) else k.latency_d.min()), 1),
                         statistic=(f"largest blob <{R_NEAR} m: {near.npix.iloc[0]} px, {near.mean_dB.iloc[0]:+.1f} dB, {near.dist_m.iloc[0]} m from "
                                    f"{near.nearest_reported.iloc[0]} (orbit {near.orbit.iloc[0]})" if len(near) else "none"),
                         null_threshold=f"placebo blobs/window-pair >= size: {far}", n_placebo=nn))

res = pd.DataFrame(rows)
res["latency_d"] = (res.latency_h / 24).round(1)
res["detected_rule"] = res.detected
# reviewed verdicts: (site, event prefix, method prefix) -> (verdict or None to keep the rule's, note)
REVIEW = [
    ("south_pars", "2026-03-18", "B12/B11/B8A", "ambiguous",
     "Rule says yes ONLY via the size-AND-peak FAR, a column added after seeing this blob's peak z. By the original "
     "size-only FAR (9.0 placebo blobs/pair >= 7 px) it is a no; size rank 4/17; sign is SWIR brightening, not the "
     "expected darkening. Site-wide blob count (17) is inside the placebo range."),
    ("south_pars", "2026-03-18", "SWIR novel", None,
     "Null is from clear scenes; this scene is 85% cloud/smoke (cloudy-scene null max 7 px, n=12). Novel clusters sit "
     "200-600 m from Refineries 3 and 5 (blind), but clear pre-war flaring upsets reached 294 px, and new clusters "
     "persist into April, so strike fire vs emergency/re-routed flaring is not separable."),
    ("ras_laffan", "2026-03-18", "SWIR novel", None,
     "Scene is 97% cloud; both novel clusters (16 px near QG1 tanks, first seen 03-09; and a ground flare at 25.8987N "
     "51.5233E) sit on minor pre-existing flare sites: consistent with emergency flaring, not a located strike fire. "
     "Cluster was 21 px / above null max before the baseline was extended to Oct 2025."),
    ("ras_laffan", "2026-03-18", "B12/B11/B8A differencing (first_usable", "no",
     "Post scene 26% cloud with unmasked shadow/wet ground: 460 blobs site-wide (placebo p95 32), so the scene is "
     "contaminated. The blob near the trains is soot/wetness around a ground flare pit, largely gone by 04-18."),
    ("fujairah", "2026-03-03", "SWIR novel", "ambiguous",
     "Genuine active fire (B12-B11 = 1.02; 0/32 baseline scenes had >2 px) but at 25.1945N 56.3541E on 03-13, ~1.2 km "
     "from the 03-03 burn site and 10 d later; matches no listed attack. Not a detection of this event. The 03-03 "
     "07:02Z scene pre-dates the fire (tanks intact)."),
    ("fujairah", "2026-03-03", "B12/B11/B8A", None,
     "Burned tanks ARE visible by eye in the 03-13 RGB at the S1/VIIRS location, but peak z there is ~4.3 (< 5): "
     "floating-roof tanks have high placebo variance. A genuine miss of the automatic detector."),
    ("fujairah", "2026-03-14", "VV log-ratio first look, rel. orbit 166", "no",
     "The blob 32 m from the VIIRS 03-03 point is the 03-03 damage site reverting (-15.6 dB vs a pre-mean that includes "
     "post-03-03 scenes), not the second attack."),
    ("fujairah", "2026-03-14", "VV log-ratio first look, rel. orbit 57", None,
     "Largest site-wide blobs (308, 232 px; none that large in 42 null looks) are on the port quay 1.1-1.6 km away: "
     "likely vessels/cargo. 33 px / -12 dB blob 62 m from the VIIRS 03-14 point is not significant (6 per null look)."),
    ("tehran", "2026-03-07", "VV log-ratio first look", None,
     "Top-1 / top-2 blind blob co-located with the S2 burn scar, but only 1 usable null look: no false-alarm rate."),
    ("tehran", "2026-03-07", "SWIR novel", None,
     "Active fire seen through 77% cloud 4.5 d after the strike; robust to every detector variant tried. Caveat: the "
     "99.5%-cloud 03-02 scene also gave a 10 px 'novel' cluster with B12-B11 of 0.34-0.79, probably cloud-edge band "
     "parallax, a false-positive mode the clear-scene null does not cover."),
]
res["notes"] = ""
for site, evp, mp, v, note in REVIEW:
    m = (res.site == site) & res.event.str.startswith(evp) & res.method.str.startswith(mp)
    assert m.any(), (site, evp, mp)
    if v:
        res.loc[m, "detected"] = v
    res.loc[m, "notes"] = note
res.to_csv(OUT / "s2s1_results.csv", index=False)
pd.set_option("display.width", 300, "display.max_colwidth", 120)
print(res[["site", "event", "method", "detected_rule", "detected", "first_acq_utc", "latency_d", "statistic", "null_threshold", "n_placebo"]].to_string(index=False))
