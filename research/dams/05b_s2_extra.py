"""Own Sentinel-2 extraction for headline reservoirs where GWW is missing or unusable:
- Kariba: GWW's whole-lake series is sparse/noisy (5,000 km2 over many tiles) and the lake is steep-sided, so we monitor
  the gently sloping Matusadona / Sanyati shore sector, where a metre of level moves the shoreline the most.
- Mazar (Ecuador, Paute cascade head reservoir): absent from GWW."""
import sys

import pandas as pd

from common import RESULTS
from s2water import monthly_series

SITES = {"kariba_matusadona": ([28.40, -16.98, 28.95, -16.68], 40), "mazar": ([-78.72, -2.70, -78.57, -2.54], 85)}
for name in sys.argv[1:] or SITES:
    bbox, cloud = SITES[name]
    d = monthly_series(name, bbox, "2015-11-01", "2026-09-15", max_cloud=cloud)
    pd.DataFrame.from_dict(d, orient="index").rename_axis("month").reset_index().to_csv(RESULTS / f"s2_{name}_area.csv", index=False)
