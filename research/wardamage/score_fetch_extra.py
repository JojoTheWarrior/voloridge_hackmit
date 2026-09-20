"""Fetch VIIRS detections for areas outside the round-1 Gulf bbox (Israel; Salalah) via keyless GIBS tiles."""
import pandas as pd, gibs
LAYERS = [f"VIIRS_{s}_Thermal_Anomalies_375m_All" for s in ("NOAA20", "NOAA21", "SNPP")]
dates = [d.strftime("%Y-%m-%d") for d in pd.date_range("2025-01-01", "2026-09-19")]
for name, bbox in {"israel": (34.0, 29.0, 36.0, 33.5), "salalah": (53.5, 16.5, 55.0, 18.0)}.items():
    for L in LAYERS:
        gibs.fetch_range(L, dates, bbox, f"score_out/gibs_{name}", workers=12)
    print("done", name, flush=True)
