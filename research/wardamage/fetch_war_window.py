import gibs, pandas as pd, sys
bbox=(36.0,18.01,64.0,40.0)
dates=[d.strftime("%Y-%m-%d") for d in pd.date_range("2025-01-01","2026-09-19")]
for layer in ["VIIRS_NOAA20_Thermal_Anomalies_375m_All","VIIRS_NOAA21_Thermal_Anomalies_375m_All","VIIRS_SNPP_Thermal_Anomalies_375m_All"]:
    gibs.fetch_range(layer,dates,bbox,"data/gibs_gulf",z=3,workers=10)
    print("done",layer,flush=True)
