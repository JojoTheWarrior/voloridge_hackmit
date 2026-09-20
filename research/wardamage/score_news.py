"""First-news timestamp per event from GDELT 2.0 raw 15-min export files (URL-slug match). Resolution 15 min; timestamp = GDELT ingest
batch (DATEADDED), an upper bound on first publication. Writes candidates for manual review + first hit."""
import pandas as pd, re
ev = pd.read_csv("score_out/events.csv"); a = pd.read_parquet("score_out/gdelt_urls.parquet")
INC = re.compile(r"fire|blaze|ablaze|attack|strike|struck|drone|missile|explo|blast|hit|bomb|burn|smoke|damage|target|flames|shut|halt|force-majeure", re.I)
a["slug"] = a.url.str.replace(r"^https?://[^/]+", "", regex=True)
a = a[a.slug.str.contains(INC)]
rows, cand = [], []
for e in ev.itertuples():
    t0 = pd.Timestamp(e.event_date) - pd.Timedelta(hours=6)
    if isinstance(e.time_utc, str) and e.time_utc: t0 = pd.Timestamp(f"{e.event_date} {e.time_utc}") - pd.Timedelta(hours=1)
    m = a[(a.added >= t0) & (a.added < t0 + pd.Timedelta(days=4)) & a.slug.str.contains(e.gdelt_rx, case=False, regex=True)].sort_values("added").head(6)
    for r in m.itertuples(): cand.append(dict(event_id=e.event_id, place=e.place, added=r.added, url=r.url))
    rows.append(dict(event_id=e.event_id, n_cand=len(m), first_news_gdelt=m.added.iloc[0] if len(m) else pd.NaT, first_news_url=m.url.iloc[0] if len(m) else ""))
pd.DataFrame(cand).to_csv("score_out/news_candidates.csv", index=False); pd.DataFrame(rows).to_csv("score_out/news_first_auto.csv", index=False)
for c in cand: print(c["event_id"], c["added"], c["url"][:170])
