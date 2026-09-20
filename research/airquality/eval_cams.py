import pandas as pd, numpy as np
d = pd.read_parquet("dataset_daily.parquet")
d = d[d.cams_pm2_5.notna()]
# QC: drop stations with stuck/absurd values
g = d.groupby("id")
ann = g.agg(obs=("pm25", "mean"), cams=("cams_pm2_5", "mean"), n=("pm25", "size"), sd=("pm25", "std"), region=("region", "first"), cc=("cc", "first"),
            kind=("kind", "first"), lat=("lat", "first"), lon=("lon", "first"), name=("params", "first"))
ann["r_daily"] = g.apply(lambda x: np.corrcoef(x.pm25, x.cams_pm2_5)[0, 1] if len(x) > 20 else np.nan)
ann = ann[(ann.n >= 40) & (ann.sd > 0.5) & (ann.obs.between(1, 400))]
ann.to_csv("station_annual.csv")
def summ(x):
    b = x.cams - x.obs
    return pd.Series({"n_st": len(x), "n_cc": x.cc.nunique(), "obs": x.obs.mean(), "cams": x.cams.mean(), "bias": b.mean(), "NMB%": 100 * b.sum() / x.obs.sum(),
                      "RMSE": np.sqrt((b ** 2).mean()), "r_spatial": np.corrcoef(x.obs, x.cams)[0, 1] if len(x) > 3 else np.nan, "med_r_daily": x.r_daily.median()})
pd.set_option("display.width", 200)
for k in ["reference_likely", "lowcost"]:
    a = ann[ann.kind == k]
    t = a.groupby("region").apply(summ); t.loc["ALL"] = summ(a)
    print(f"\n== {k}: annual-mean CAMS vs OpenAQ, 2025 ==\n", t.round(2).to_string())
a = ann[ann.kind == "reference_likely"]
cc = a.assign(cc2=a.cc).groupby("cc2").apply(summ)
print("\nworst countries by |NMB| (reference-likely, >=3 stations):\n", cc[cc.n_st >= 3].sort_values("NMB%").round(1).iloc[list(range(12)) + list(range(-12, 0))].to_string())
