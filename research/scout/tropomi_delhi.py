"""TROPOMI tropospheric NO2 (keyless COGs on AWS) vs OpenAQ ground NO2, Delhi, Jan-Jun 2020 (spans the lockdown)."""
import re, numpy as np, pandas as pd, rasterio, boto3
from rasterio.windows import from_bounds
from concurrent.futures import ThreadPoolExecutor
from botocore import UNSIGNED
from botocore.config import Config
from oaq import hourly
s3=boto3.client("s3",region_name="eu-central-1",config=Config(signature_version=UNSIGNED,max_pool_connections=32))
BOX=(76.9,28.4,77.4,28.85)
def day(d):
    pre=f"COGT/OFFL/L2__NO2___/{d:%Y/%m/%d}/"; ks=[o["Key"] for o in s3.list_objects_v2(Bucket="meeo-s5p",Prefix=pre).get("Contents",[])]
    out=[]
    for k in ks:
        if not k.endswith("PRODUCT_nitrogendioxide_tropospheric_column_4326.tif"): continue
        hh=int(re.search(r"____\d{8}T(\d{2})",k).group(1))
        if not 5<=hh<=9: continue
        try:
            with rasterio.Env(AWS_NO_SIGN_REQUEST="YES",AWS_REGION="eu-central-1",GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
                with rasterio.open(f"s3://meeo-s5p/{k}") as ds:
                    if not (ds.bounds.left<BOX[0] and ds.bounds.right>BOX[2] and ds.bounds.bottom<BOX[1] and ds.bounds.top>BOX[3]): continue
                    a=ds.read(1,window=from_bounds(*BOX,ds.transform)).astype(float); nd=ds.nodata
                with rasterio.open(f"s3://meeo-s5p/{k.replace('PRODUCT_nitrogendioxide_tropospheric_column_4326','PRODUCT_qa_value_4326')}") as q:
                    qa=q.read(1,window=from_bounds(*BOX,q.transform)).astype(float)
            if nd is not None: a[a==nd]=np.nan
            a[(a>1)|(a<-1)]=np.nan; qa=qa/100 if np.nanmax(qa)>1.5 else qa
            ok=(qa>=0.75)&np.isfinite(a)
            if ok.sum()>=max(4,0.3*a.size): out.append(np.nanmean(a[ok]))
        except Exception as e: pass
    return d,(np.mean(out) if out else np.nan)
days=pd.date_range("2020-01-01","2020-06-30")
with ThreadPoolExecutor(12) as p: sat=pd.Series(dict(p.map(day,days)))*1e6  # umol/m2
print("valid satellite days",sat.notna().sum(),"of",len(days))
g=pd.concat([hourly(l,2020,range(1,7),"no2").rename(l) for l in (5586,5630,6356,6357,6358)],axis=1)
g.index=g.index+pd.Timedelta(hours=5.5); mid=g[(g.index.hour>=12)&(g.index.hour<=15)].resample("D").mean().mean(axis=1)
df=pd.concat([sat.rename("sat"),mid.rename("ground")],axis=1).dropna(); df.to_csv("data/tropomi_delhi.csv")
wk=df.resample("W").mean().dropna()
pre,post=slice("2020-02-01","2020-03-20"),slice("2020-03-25","2020-04-30")
print(f"daily r={df.sat.corr(df.ground):.2f} n={len(df)}; weekly r={wk.sat.corr(wk.ground):.2f} n={len(wk)}; lockdown change: satellite {df.sat[post].mean()/df.sat[pre].mean()-1:+.0%}, ground {df.ground[post].mean()/df.ground[pre].mean()-1:+.0%}")
