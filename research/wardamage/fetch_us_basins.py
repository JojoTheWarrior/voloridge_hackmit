import gibs, pandas as pd
B={'bakken':(-104.6,46.5,-100.5,49.0),'permian':(-104.9,30.4,-100.4,33.6)}
for sat,start in [('SNPP','2012-01-20'),('NOAA20','2018-01-05'),('NOAA21','2024-01-17')]:
    dates=[d.strftime("%Y-%m-%d") for d in pd.date_range(start,"2026-09-19")]
    for b,bbox in B.items():
        gibs.fetch_range(f"VIIRS_{sat}_Thermal_Anomalies_375m_All",dates,bbox,f"data/gibs_{b}",z=5,workers=12)
        print('done',sat,b,flush=True)
