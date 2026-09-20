"""Keyless AEMO NEMWEB MMSDM monthly DISPATCH_UNIT_SCADA (5-min per-unit MW). Keeps only study DUIDs. -> aemo/scada.parquet"""
import requests, re, io, zipfile, pandas as pd, sys, os
from concurrent.futures import ThreadPoolExecutor
H={"User-Agent":"Mozilla/5.0"}
DUIDS={"Loy Yang":["LYA1","LYA2","LYA3","LYA4","LOYYB1","LOYYB2"],"Yallourn":["YWPS1","YWPS2","YWPS3","YWPS4"],"Bayswater":["BW01","BW02","BW03","BW04"],
 "Mt Piper":["MP1","MP2"],"Stanwell":["STAN-1","STAN-2","STAN-3","STAN-4"],"Tarong":["TARONG#1","TARONG#2","TARONG#3","TARONG#4","TNPS1"],
 "Callide":["CALL_B_1","CALL_B_2","CPP_3","CPP_4"],"Millmerran":["MPP_1","MPP_2"],"Kogan Creek":["KPP_1"],"Eraring":["ER01","ER02","ER03","ER04"],
 "Vales Point":["VP5","VP6"],"Gladstone":["GSTONE1","GSTONE2","GSTONE3","GSTONE4","GSTONE5","GSTONE6"]}
d2p={d:p for p,ds in DUIDS.items() for d in ds}
def month(ym):
    y,m=ym; out=f"aemo/scada_{y}-{m:02d}.parquet"
    if os.path.exists(out): return out
    base=f"https://nemweb.com.au/Data_Archive/Wholesale_Electricity/MMSDM/{y}/MMSDM_{y}_{m:02d}/MMSDM_Historical_Data_SQLLoader/DATA/"
    html=requests.get(base,headers=H,timeout=120).text
    links=sorted(set(re.findall(r'HREF="([^"]*DISPATCH_UNIT_SCADA[^"]*\.zip)"',html,flags=re.I)))
    if not links: print(ym,"no file"); return None
    frames=[]
    for l in links:
        z=zipfile.ZipFile(io.BytesIO(requests.get("https://nemweb.com.au"+l,headers=H,timeout=600).content))
        for n in z.namelist():
            df=pd.read_csv(z.open(n),skiprows=1,usecols=["SETTLEMENTDATE","DUID","SCADAVALUE"],dtype={"DUID":str},on_bad_lines="skip")
            frames.append(df[df.DUID.isin(d2p)])
    df=pd.concat(frames); df["t_aest"]=pd.to_datetime(df.SETTLEMENTDATE); df["plant"]=df.DUID.map(d2p)
    df=df.drop(columns="SETTLEMENTDATE").drop_duplicates(["t_aest","DUID"]); df.to_parquet(out); print(ym,len(df),flush=True); return out
yms=[(y,m) for y in (2023,2024,2025,2026) for m in range(1,13) if (2023,7)<=(y,m)<=(2026,7)]
with ThreadPoolExecutor(4) as ex: outs=[o for o in ex.map(month,yms) if o]
pd.concat(pd.read_parquet(o) for o in outs).to_parquet("aemo/scada.parquet"); print("done",len(outs))
