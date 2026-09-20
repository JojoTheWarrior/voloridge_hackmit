"""Events, approximate strike times (UTC) and reported target locations (from news/OSM; used only AFTER
blind detection, to score whether top anomalies coincide)."""
import pandas as pd

# time_unc_h: my uncertainty on the strike time. Sources: Wikipedia event pages, QatarEnergy statements,
# HRW 2026-04-14 / 2026-04-22 reports, Argus/MEED for Fujairah, round-1 VIIRS for Fujairah/Tehran.
EVENTS = [
    dict(site="ras_laffan", event="2026-03-02 drone attack", t="2026-03-02T12:00Z", time_unc_h=12),
    dict(site="ras_laffan", event="2026-03-18/19 missile strikes", t="2026-03-18T18:00Z", time_unc_h=4),
    dict(site="south_pars", event="2026-03-18 Israeli strike", t="2026-03-18T10:40Z", time_unc_h=1),
    dict(site="fujairah", event="2026-03-03 drone attack (tank fire)", t="2026-03-03T12:00Z", time_unc_h=12),
    dict(site="fujairah", event="2026-03-14 second attack", t="2026-03-14T12:00Z", time_unc_h=12),
    dict(site="tehran", event="2026-03-07 Israeli strike (Rey depot/refinery)", t="2026-03-07T18:30Z", time_unc_h=3),
]
for e in EVENTS:
    e["t"] = pd.Timestamp(e["t"])

# name, lat, lon, kind ("reported" = news-reported damaged unit located via OSM; "viirs" = round-1 hotspot)
REPORTED = {
    "ras_laffan": [("Pearl GTL (T2 hit 03-18; OSM centroid)", 25.9050, 51.5054, "reported"),
                   ("RasGas/South LNG trains (T4,T6 hit 03-19; OSM centroid)", 25.8884, 51.5417, "reported")],
    "south_pars": [("Refinery 3 (ph 4-5)", 27.5409, 52.5713, "reported"),
                   ("Refinery 4 (ph 6-8)", 27.5350, 52.5760, "reported"),
                   ("Refinery 5 (ph 9-10)", 27.5001, 52.6223, "reported"),
                   ("Refinery 6 (ph 15-16)", 27.4881, 52.6437, "reported"),
                   ("Refinery 7 (ph 17-18)", 27.4935, 52.6333, "reported")],
    "fujairah": [("VIIRS 03-03..05", 25.184, 56.346, "viirs"), ("VIIRS 03-14..22", 25.209, 56.349, "viirs")],
    "tehran": [("VIIRS 03-07 (763 MW)", 35.540, 51.432, "viirs"),
               ("Tehran refinery (OSM)", 35.5400, 51.4229, "reported")],
}
