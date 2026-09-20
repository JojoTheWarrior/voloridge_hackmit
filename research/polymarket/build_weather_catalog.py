"""Parse Polymarket daily temperature markets into a bucket-level catalogue."""
import json
import re

import pandas as pd

from pmlib import DATA, read_jsonl_gz

MONTHS = {m: i + 1 for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"])}
SLUG = re.compile(r"^(highest|lowest)-temperature-in-(.+)-on-([a-z]+)-(\d+)(?:-(\d{4}))?$")


def parse_bucket(title):
    """Return (lo, hi, unit) inclusive integer bounds; open ends are +-inf."""
    t = title.replace("º", "°").replace("−", "-")
    unit = "F" if "F" in t.upper().replace("OR", "").replace("BELOW", "").replace("HIGHER", "") and "°F" in t else ("C" if "°C" in t else None)
    nums = [int(x) for x in re.findall(r"-?\d+", t)]
    low = t.lower()
    if "or below" in low or "or lower" in low:
        return float("-inf"), nums[0], unit
    if "or higher" in low or "or above" in low:
        return nums[0], float("inf"), unit
    if len(nums) == 2:
        return nums[0], abs(nums[1]) if nums[1] < 0 and "-" in t[1:] and nums[0] >= 0 else nums[1], unit
    if len(nums) == 1:
        return nums[0], nums[0], unit
    return None, None, unit


def main():
    recs = read_jsonl_gz(DATA / "gamma" / "weather.jsonl.gz")
    rows = []
    for r in recs:
        m = SLUG.match(r.get("event_slug") or "")
        if not m:
            continue
        kind, city, mon, day, year = m.groups()
        if mon not in MONTHS:
            continue
        end = pd.Timestamp(r["endDate"] or r["closedTime"] or r["createdAt"])
        year = int(year) if year else end.year
        lo, hi, unit = parse_bucket(r.get("groupItemTitle") or "")
        prices = json.loads(r["outcomePrices"]) if r.get("outcomePrices") else [None, None]
        toks = json.loads(r["clobTokenIds"]) if r.get("clobTokenIds") else [None, None]
        src = r.get("resolutionSource") or ""
        desc = r.get("description") or ""
        url = re.search(r"https?://[^\s\"]+", src + " " + desc)
        rows.append(dict(
            market_id=r["id"], condition_id=r["conditionId"], event_id=r["event_id"],
            event_slug=r["event_slug"], kind=kind, city=city,
            date=f"{year:04d}-{MONTHS[mon]:02d}-{int(day):02d}",
            bucket=r.get("groupItemTitle"), lo=lo, hi=hi, unit=unit,
            yes_token=toks[0], closed=r["closed"], yes_final=float(prices[0]) if prices[0] is not None else None,
            volume=r.get("volumeNum") or 0.0, start=r.get("startDate"), created=r.get("createdAt"),
            closed_time=r.get("closedTime"), res_url=url.group(0).rstrip(".") if url else None,
            wu=("wunderground" in (src + desc).lower()),
        ))
    df = pd.DataFrame(rows)
    df["station"] = df.res_url.str.extract(r"/([A-Z0-9]{4})/?$")
    df.to_parquet(DATA / "weather_catalog.parquet")
    ev = df.groupby("event_slug").agg(city=("city", "first"), kind=("kind", "first"), date=("date", "first"),
                                      n_buckets=("bucket", "count"), vol=("volume", "sum"),
                                      n_yes=("yes_final", lambda s: (s > 0.99).sum()),
                                      station=("station", "first"), unit=("unit", "first"), closed=("closed", "all"))
    print(len(df), "bucket markets;", len(ev), "events; $%.1fM volume" % (df.volume.sum() / 1e6))
    print(ev.groupby(["kind"]).agg(events=("vol", "count"), vol=("vol", "sum")))
    print("resolved events with exactly one YES:", ((ev.n_yes == 1) & ev.closed).sum(), "of", ev.closed.sum())
    print(ev.groupby("city").agg(events=("vol", "count"), vol=("vol", "sum"), first=("date", "min"),
                                 station=("station", lambda s: ",".join(sorted(set(s.dropna())))),
                                 unit=("unit", "first")).sort_values("vol", ascending=False).to_string())
    print("unparsed buckets:", df.lo.isna().sum(), df[df.lo.isna()].bucket.unique()[:10])
    print(df.res_url.str.extract(r"https?://([^/]+)")[0].value_counts())


if __name__ == "__main__":
    main()
