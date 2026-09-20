"""Download CAL FIRE Damage Inspection (DINS) records from the public ArcGIS feature service (keyless)."""
import requests, pandas as pd, time
URL = "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/POSTFIRE_MASTER_DATA_SHARE/FeatureServer/0/query"
rows, off = [], 0
while True:
    for attempt in range(5):
        try:
            r = requests.get(URL, params=dict(where="1=1", outFields="*", returnGeometry="false", f="json",
                                              resultOffset=off, resultRecordCount=2000, orderByFields="OBJECTID"), timeout=120)
            js = r.json(); break
        except Exception as e:
            print("retry", e); time.sleep(3)
    feats = js.get("features", [])
    rows += [f["attributes"] for f in feats]
    print(off, len(rows), flush=True)
    if len(feats) < 2000 and not js.get("exceededTransferLimit"):
        break
    off += len(feats)
df = pd.DataFrame(rows)
df["INCIDENTSTARTDATE"] = pd.to_datetime(df["INCIDENTSTARTDATE"], unit="ms", errors="coerce")
df.to_parquet("data/dins_all.parquet")
print(df.shape)
print(df.groupby("INCIDENTNAME").size().sort_values(ascending=False).head(40))
