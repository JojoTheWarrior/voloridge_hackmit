"""Download NOAA GHCNh (successor of ISD; same METAR/synoptic feed) for market stations."""
import time

import pandas as pd
import requests

from pmlib import DATA, cached_response

BASE = "https://www.ncei.noaa.gov/oa/global-historical-climatology-network/hourly/access/by-year"
OUT = DATA / "ghcnh"
EXTRA = {"moscow": "UUWW", "istanbul": "LTFM"}


def main():
    cat = pd.read_parquet(DATA / "catalog_enriched.parquet")
    icaos = set(cat.station.dropna().str.upper())
    sl = pd.read_csv(OUT / "ghcnh-station-list.csv", dtype=str)
    sl = sl[sl.ICAO.isin(icaos)]
    s = requests.Session()
    s.headers["User-Agent"] = "hackathon-research-readonly/0.1"
    rows = []
    for _, st in sl.iterrows():
        for year in (2025, 2026):
            f = OUT / f"GHCNh_{st.GHCN_ID}_{year}.psv"
            if not f.exists():
                f = f.with_suffix('.parquet')
                if not f.exists():
                    meta, content = cached_response(f"{BASE}/{year}/parquet/{f.name}", cache_dir='noaa_http', timeout=60, retries=4)
                    if meta['status'] != 200:
                        rows.append((st.ICAO, st.GHCN_ID, year, 0))
                        continue
                    f.write_bytes(content)
                    print(f'{st.ICAO} {year}: {len(content)} bytes', flush=True)
            rows.append((st.ICAO, st.GHCN_ID, year, f.stat().st_size))
            pd.DataFrame(rows, columns=['icao','ghcn_id','year','bytes']).to_csv(OUT/'download_index.csv',index=False)
    res = pd.DataFrame(rows, columns=["icao", "ghcn_id", "year", "bytes"])
    res.to_csv(OUT / "download_index.csv", index=False)
    print(res.pivot_table(index=["icao", "ghcn_id"], columns="year", values="bytes").to_string())
    print("missing ICAOs:", sorted(icaos - set(sl.ICAO)))


if __name__ == "__main__":
    main()
