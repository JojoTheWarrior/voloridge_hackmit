"""GERD (Ethiopia) reservoir filling from our own Sentinel-2 extraction; GWW does not carry it."""
import pandas as pd

from common import RESULTS
from s2water import monthly_series

BBOX = [34.75, 10.25, 35.60, 11.35]
d = monthly_series("gerd", BBOX, "2019-01-01", "2026-09-15")
df = pd.DataFrame.from_dict(d, orient="index").rename_axis("month").reset_index()
df.to_csv(RESULTS / "gerd_s2_area.csv", index=False)
print(df.to_string())
