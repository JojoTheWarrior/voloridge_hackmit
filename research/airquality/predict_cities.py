"""Rank cities >=500k with no reference-likely PM2.5 monitor (OpenAQ, 25 km) by predicted 2025 PM2.5; add LCO-residual-based uncertainty."""
import numpy as np, pandas as pd, lightgbm as lgb, joblib, warnings
warnings.filterwarnings("ignore")
src = open("model.py").read(); ns = {}
exec("import numpy as np, pandas as pd\n" + src[src.index("def feats"):src.index("X, y =")], ns); feats = ns["feats"]
c = pd.read_parquet("cities_monthly.parquet").rename(columns={})
mdl = joblib.load("model.joblib"); Xc = feats(c)[mdl["cols"]]
c["pred"] = np.expm1(mdl["model"].predict(Xc))
cv = pd.read_parquet("cv_predictions.parquet")
Xcv = feats(cv)[mdl["cols"]]; res = (np.log1p(cv.pm25) - np.log1p(cv.gbm_lco)).abs()
unc = lgb.LGBMRegressor(n_estimators=200, learning_rate=0.03, num_leaves=7, min_child_samples=60, verbose=-1).fit(Xcv, res)
c["abs_log_err"] = unc.predict(Xc)
a = c.groupby("gid").agg(name=("name", "first"), cc=("cc", "first"), region=("region", "first"), lat=("lat", "first"), lon=("lon", "first"), pop=("pop", "first"),
    n_ref_25=("n_ref_25", "first"), n_any_25=("n_any_25", "first"), cams=("cams_pm2_5", "mean"), pred=("pred", "mean"), abs_log_err=("abs_log_err", "mean")).reset_index()
a["lo"] = a.pred * np.exp(-1.6 * a.abs_log_err); a["hi"] = a.pred * np.exp(1.6 * a.abs_log_err)
a["priority"] = a["pop"] / 1e6 * a.pred * a.abs_log_err
a.to_csv("city_predictions.csv", index=False)
un = a[a.n_ref_25 == 0]
pd.set_option("display.width", 200)
cols = ["name", "cc", "pop", "cams", "pred", "lo", "hi", "n_any_25"]
print("TOP 30 unmonitored (no reference-likely PM2.5 in OpenAQ within 25 km) by predicted PM2.5 -- excluding China:")
print(un[un.cc != "CN"].nlargest(30, "pred")[cols].round(1).to_string(index=False))
print("\nTOP 20 'next monitor' priority = pop x predicted PM2.5 x model uncertainty (excluding China):")
print(un[un.cc != "CN"].nlargest(20, "priority")[cols + ["abs_log_err", "priority"]].round(2).to_string(index=False))
print("\nPeople in unmonitored cities >=500k with predicted PM2.5 > 35: %.0f M (ex-China %.0f M)" % (un[un.pred > 35]["pop"].sum() / 1e6, un[(un.pred > 35) & (un.cc != "CN")]["pop"].sum() / 1e6))
print("Spearman(pred, raw CAMS) across unmonitored cities: %.3f ; top-30 overlap with raw-CAMS ranking: %d/30" % (un.pred.corr(un.cams, method="spearman"),
      len(set(un[un.cc != "CN"].nlargest(30, "pred").gid) & set(un[un.cc != "CN"].nlargest(30, "cams").gid))))
mon = a[a.n_ref_25 > 0]
chk = ["Delhi", "Lahore", "Dhaka", "Kolkata", "Kampala", "Accra", "Almaty", "Tashkent", "Santiago", "Jakarta", "Hanoi", "Kathmandu", "Ulan Bator", "Sarajevo", "Bishkek", "Dushanbe", "Karachi", "Lagos", "Kinshasa", "Cairo", "Baghdad", "N'Djamena", "Ouagadougou", "Bamako", "Khartoum", "Kabul", "Tehran", "Riyadh"]
print("\nSanity cities:\n", a[a.name.isin(chk)].sort_values("pred", ascending=False)[["name", "cc", "cams", "pred", "n_ref_25"]].round(1).to_string(index=False))
