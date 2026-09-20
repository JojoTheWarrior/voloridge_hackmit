"""Availability probe: which candidate reservoirs exist in GWW and their coverage. No targets touched."""
import gww
sites={"Xiaowan":(100.09,24.70),"Nuozhadu":(100.43,22.64),"Jinghong":(100.77,22.06),"Manwan":(100.45,24.62),"Dachaoshan":(100.37,24.03),"Gongguoqiao":(99.33,25.59),
"Longtan":(107.05,25.03),"Ertan":(101.78,26.82),
"Kariba":(27.9,-17.0),"ItezhiTezhi":(26.0,-15.75),"CahoraBassa":(31.8,-15.7),
"Mead":(-114.60,36.13),"Powell":(-111.30,37.05),"Shasta":(-122.30,40.78),"Oroville":(-121.40,39.58),"Trinity":(-122.75,40.85),"NewMelones":(-120.52,37.98),"DonPedro":(-120.40,37.72),
"Furnas":(-45.9,-20.9),"Sobradinho":(-41.8,-9.6),"SerraDaMesa":(-48.3,-13.9),"TresMarias":(-45.25,-18.4),"Emborcacao":(-47.9,-18.5),"Itumbiara":(-49.0,-18.4),"NovaPonte":(-47.5,-19.2),"IlhaSolteira":(-51.2,-20.3),"Marimbondo":(-49.1,-20.3),
"Blasjo":(6.85,59.33),"Akosombo":(0.1,7.0),"Toktogul":(72.9,41.8),"Ataturk":(38.5,37.6),"Argyle(AUS placebo)":(128.75,-16.3),"Guri(placebo)":(-62.8,7.5)}
for n,(x,y) in sites.items():
    fs=gww.find(x,y)
    if not fs: print(f"{n:22s} NOT FOUND"); continue
    a=gww.area(fs[0]["id"])
    print(f"{n:22s} id={fs[0]['id']} name={fs[0]['name']} n={len(a)} {a.index.min().date() if len(a) else None}->{a.index.max().date() if len(a) else None} p90={a.quantile(.9):.0f}km2 n2021+={int((a.index>='2021').sum())}")
