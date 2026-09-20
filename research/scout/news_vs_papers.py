"""GDELT news surge vs OpenAlex publication surge: how long does science lag the headlines?"""
import io, time, requests, numpy as np, pandas as pd
from concurrent.futures import ThreadPoolExecutor
TOPICS={"mpox":('(monkeypox OR mpox)',"monkeypox|mpox","2021-01","2024-12"),
        "ChatGPT":('chatgpt',"chatgpt","2022-01","2025-12"),
        "Hunga Tonga eruption":('"hunga tonga"',"hunga tonga","2021-06","2025-06"),
        "LK-99 superconductor":('("LK-99" OR "LK99")',"LK-99|LK99","2023-01","2025-06"),
        "Turkey-Syria earthquake":('kahramanmaras earthquake',"kahramanmaras earthquake","2022-06","2025-12")}
def gdelt(q,a,b):
    for _ in range(25):
        time.sleep(12)
        r=requests.get("https://api.gdeltproject.org/api/v2/doc/doc",params={"query":q,"mode":"timelinevolraw","format":"csv","startdatetime":a.replace("-","")+"01000000","enddatetime":(pd.Timestamp(b)+pd.offsets.MonthEnd(0)).strftime("%Y%m%d235959")},timeout=120)
        if r.status_code==200 and "Date" in r.text[:12]: break
    d=pd.read_csv(io.StringIO(r.text.lstrip("﻿"))); d["Date"]=pd.to_datetime(d["Date"])
    p=d.pivot_table(index="Date",columns="Series",values="Value",aggfunc="sum"); return (p["Article Count"]/p["Total Monitored Articles"]).resample("MS").mean()
def oa(args):
    s,m=args; e=(m+pd.offsets.MonthEnd(0)).date(); a=m.date()
    if m.month==1: a=a.replace(day=2)   # drop Jan-1 placeholder dates
    for _ in range(4):
        r=requests.get("https://api.openalex.org/works",params={"filter":f"title_and_abstract.search:{s},from_publication_date:{a},to_publication_date:{e}","per-page":1},timeout=60)
        if r.status_code==200: return m,r.json()["meta"]["count"]
        time.sleep(2)
    return m,np.nan
for name,(gq,oq,a,b) in TOPICS.items():
    news=gdelt(gq,a,b); months=pd.date_range(a,b,freq="MS")
    with ThreadPoolExecutor(4) as p: papers=pd.Series(dict(p.map(oa,[(oq,m) for m in months])))
    df=pd.concat([news.rename("news"),papers.rename("papers")],axis=1).dropna()
    cc={k:df.news.corr(df.papers.shift(-k)) for k in range(0,19)}; best=max(cc,key=lambda k:cc[k])
    half=lambda s:(s.cumsum()/s.sum()>=0.5).idxmax()
    print(f"{name:26s} news peak {df.news.idxmax():%Y-%m}  papers peak {df.papers.idxmax():%Y-%m} (n={int(df.papers.sum())})  best xcorr lag={best} mo (r={cc[best]:.2f}, r@0={cc[0]:.2f})  median-date gap={(half(df.papers)-half(df.news)).days/30.4:.0f} mo")
    df.to_csv(f"data/newspapers_{name.split()[0]}.csv")
