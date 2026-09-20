"""Pull + clean GWW area series for every matched reservoir (and the case-study list) -> data/area_monthly.parquet."""
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from areas import monthly
from common import DATA

ids = set(pd.read_parquet(DATA / "matches.parquet").query("status=='matched'").gww_id.dropna().astype(int))
cs = DATA / "case_studies.csv"
if cs.exists():
    ids |= set(pd.read_csv(cs).gww_id.dropna().astype(int))
ids = sorted(ids)
print(len(ids), "reservoirs", flush=True)


def one(i):
    try:
        m = monthly(i)
        m["gww_id"] = i
        return m.reset_index(names="month")
    except Exception as e:
        print("FAIL", i, e, file=sys.stderr, flush=True)
        return None


out = []
with ThreadPoolExecutor(3) as ex:
    for k, m in enumerate(ex.map(one, ids)):
        if m is not None and len(m):
            out.append(m)
        if k % 100 == 0:
            print(k, flush=True)
pd.concat(out).to_parquet(DATA / "area_monthly.parquet")
print("done", len(out))
