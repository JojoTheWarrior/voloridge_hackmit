"""GDELT DOC 2.0 monthly share-of-coverage for power-shortage terms, per country (2017-01 onward; API limit of the DOC index).
One request per country, >= 12 s apart with long backoff (the API enforces 1 request / 5 s per IP). Cached.
Output data/gdelt_shortage_news.parquet (iso3, month, articles, total, share_ppm)."""
import io
import time

import pandas as pd

from common import CACHE, DATA, SESSION

TERMS = '("load shedding" OR loadshedding OR "power cuts" OR "power rationing" OR "electricity rationing" OR blackouts OR "power outages")'
COUNTRIES = {"ZMB": "zambia", "ZWE": "zimbabwe", "MOZ": "mozambique", "MWI": "malawi", "TZA": "tanzania", "KEN": "kenya", "UGA": "uganda",
             "ETH": "ethiopia", "GHA": "ghana", "CMR": "cameroon", "COD": "congo", "AGO": "angola", "NAM": "namibia", "SDN": "sudan",
             "VEN": "venezuela", "ECU": "ecuador", "COL": "colombia", "BRA": "brazil", "PER": "peru", "PRY": "paraguay", "URY": "uruguay",
             "CRI": '"costa rica"', "PAN": "panama", "HND": "honduras", "KGZ": "kyrgyzstan", "TJK": "tajikistan", "GEO": "georgia",
             "ALB": "albania", "NPL": "nepal", "LAO": "laos", "MMR": "myanmar", "KHM": "cambodia", "LKA": '"sri lanka"', "NOR": "norway",
             "CHE": "switzerland", "AUT": "austria", "CAN": "canada", "NZL": '"new zealand"', "VNM": "vietnam", "PAK": "pakistan",
             "TUR": "turkey", "ARG": "argentina", "CHL": "chile", "NGA": "nigeria", "EGY": "egypt", "IRQ": "iraq", "CHN": "yunnan"}
OUT = CACHE / "gdelt"
OUT.mkdir(exist_ok=True)


def fetch(iso, word):
    fn = OUT / f"{iso}.csv"
    if fn.exists():
        return fn.read_text()
    params = {"query": f"{TERMS} {word}", "mode": "timelinevolraw", "format": "csv",
              "startdatetime": "20170101000000", "enddatetime": "20260901000000"}
    for i in range(12):
        time.sleep(12 + 10 * i)
        try:
            r = SESSION.get("https://api.gdeltproject.org/api/v2/doc/doc", params=params, timeout=120)
        except Exception as e:
            print(iso, "error", repr(e)[:80], flush=True)
            continue
        if r.status_code == 200 and "Date" in r.text[:12]:
            fn.write_text(r.text)
            return r.text
        print(iso, "retry", r.status_code, r.text[:60].replace("\n", " "), flush=True)
    return None


PRIORITY = ["ZMB", "ZWE", "VEN", "ECU", "KGZ", "GHA", "TZA", "BRA", "COL", "VNM", "TUR", "PAK", "TJK", "MOZ", "KEN"]  # case studies first
ORDER = PRIORITY + [c for c in COUNTRIES if c not in PRIORITY]
def assemble():
    """Rebuild the tidy parquet from whatever country files are cached (the pull can take hours under shared-IP limits)."""
    rows = []
    for fn in sorted(OUT.glob("*.csv")):
        d = pd.read_csv(io.StringIO(fn.read_text().lstrip("\ufeff")))
        d["Date"] = pd.to_datetime(d.Date)
        m = d.pivot_table(index="Date", columns="Series", values="Value", aggfunc="sum").resample("MS").sum()
        rows.append(pd.DataFrame({"iso3": fn.stem, "month": m.index, "articles": m["Article Count"].values, "total": m["Total Monitored Articles"].values}))
    out = pd.concat(rows)
    out["share_ppm"] = out.articles / out.total * 1e6
    out.to_parquet(DATA / "gdelt_shortage_news.parquet")


assemble()
for iso in ORDER:
    if fetch(iso, COUNTRIES[iso]):
        assemble()
        print(iso, "ok", flush=True)
    else:
        print(iso, "FAILED", flush=True)
