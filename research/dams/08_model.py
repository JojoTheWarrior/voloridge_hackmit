"""US model + honest validation: does orbit add anything beyond "it's April"?

Validation designs (preregistration.json): forward-in-time (train <= 2018, test >= 2019), leave-dams-out (5-fold by
reservoir), and the strict combination (unseen dams AND unseen years) that mimics applying the model abroad.
Skill is reported on generation ANOMALIES vs each dam's own seasonal normal; climatology therefore scores 0 by
construction and persistence of the label is the bar to beat where labels exist.
Outputs results/skill_table.csv, results/predictions_us_<subset>_h<horizon>.parquet, results/per_dam_skill.csv, models/*.txt"""
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold

from common import RESULTS, ROOT
from features import AREA_FEATS, CLIM_FEATS, PHASE_FEATS, STATIC_FEATS, build, load_inputs
from scoring import metrics

warnings.filterwarnings("ignore")
SPLIT = pd.Timestamp("2018-12-01")
(ROOT / "models").mkdir(exist_ok=True)

FEATSETS = {
    "gbm_area": AREA_FEATS + PHASE_FEATS + STATIC_FEATS,
    "gbm_climate": CLIM_FEATS + PHASE_FEATS + STATIC_FEATS,
    "gbm_area+climate": AREA_FEATS + CLIM_FEATS + PHASE_FEATS + STATIC_FEATS,
    "gbm_persist3+area+climate": ["y_lag3"] + AREA_FEATS + CLIM_FEATS + PHASE_FEATS + STATIC_FEATS,
}
GBM = dict(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=200, subsample=0.8, subsample_freq=1,
           colsample_bytree=0.8, reg_lambda=5.0, verbose=-1, random_state=0)


def gbm(tr, te, cols, **kw):
    m = lgb.LGBMRegressor(**{**GBM, **kw}).fit(tr[cols], tr.y)
    return m.predict(te[cols]), m


def ridge(tr, te, cols):
    mu, sd = tr[cols].mean(), tr[cols].std().replace(0, 1)
    f = lambda d: ((d[cols] - mu) / sd).fillna(0).clip(-5, 5)
    return RidgeCV(alphas=np.logspace(-1, 4, 12)).fit(f(tr), tr.y).predict(f(te))


def predict_all(tr, te, per_dam_ok):
    out = pd.DataFrame(index=te.index)
    out["climatology"] = 0.0
    if not te.y_now.equals(te.y):  # forecast mode: the freshest label a label-holder could have
        out["persistence_lag0"] = te.y_now
    out["persistence_lag1"] = te.y_lag1
    out["persistence_lag3"] = te.y_lag3
    # raw persistence overshoots; the fair label-holder baseline is a damped (regressed) persistence
    fresh = "y_now" if "persistence_lag0" in out else "y_lag1"
    out[f"damped_persistence_{fresh[2:]}"] = np.polyval(np.polyfit(tr[fresh], tr.y, 1), te[fresh])
    out["damped_persistence_lag3"] = np.polyval(np.polyfit(tr.y_lag3, tr.y, 1), te.y_lag3)
    b = np.polyfit(tr.a0, tr.y, 1)
    out["area_linear_pooled"] = np.polyval(b, te.a0)
    if per_dam_ok:  # needs label history at the test dam -> only in the forward design
        sl = tr.groupby("gww_id").apply(lambda d: np.polyfit(d.a0, d.y, 1) if len(d) >= 36 and d.a0.std() > 0 else b)
        out["area_linear_per_dam"] = [np.polyval(sl.get(g, b), a) for g, a in zip(te.gww_id, te.a0)]
    out["ridge_area+climate"] = ridge(tr, te, FEATSETS["gbm_area+climate"])
    for name, cols in FEATSETS.items():
        out[name], _ = gbm(tr, te, cols)
    return out


KEEP = ["gww_id", "month", "y", "y_now", "mwh", "gen_clim", "gen_mean", "a0"]


def prepare(panel, st, clim, ref_end, horizon):
    """horizon 0: nowcast month t. horizon h>0: forecast the mean anomaly over t+1..t+h from features at t; the label
    persistence baselines then are the anomaly at t-1 / t-3 (what a label-holder would know with 1-3 months reporting lag)."""
    df = build(panel, st, clim, ref_end=ref_end)
    df["y_now"] = df.y
    if horizon:
        g = df.groupby("gww_id").y_now
        fwd = sum(g.shift(-k) for k in range(1, horizon + 1)) / horizon
        df["y"] = fwd
        df["last_label_month"] = df.month + pd.DateOffset(months=horizon)
    else:
        df["last_label_month"] = df.month
    df = df.dropna(subset=["y", "y_now", "a0", "y_lag1", "y_lag3"])
    return df[df.last_label_month < "2026-01-01"]


def run(tag, ids, horizon):
    rows, preds = [], []
    pn = panel[panel.gww_id.isin(ids)]
    F = prepare(pn, st, clim, SPLIT, horizon)
    tr, te = F[F.last_label_month <= SPLIT], F[F.month > SPLIT]
    te = te[te.gww_id.isin(tr.gww_id.unique())]
    p = predict_all(tr, te, per_dam_ok=True)
    rows += metrics(te, p, "forward (train<=2018, test 2019-2025)")
    preds.append(pd.concat([te[KEEP], p], axis=1).assign(design="forward"))

    A = prepare(pn, st, clim, None, horizon)
    parts = []
    for itr, ite in GroupKFold(5).split(A, groups=A.gww_id):
        parts.append(pd.concat([A.iloc[ite][KEEP], predict_all(A.iloc[itr], A.iloc[ite], per_dam_ok=False)], axis=1))
    L = pd.concat(parts)
    rows += metrics(L, L.drop(columns=KEEP), "leave-dams-out (5-fold)")
    preds.append(L.assign(design="leave_dams_out"))

    parts = []
    for itr, ite in GroupKFold(5).split(F, groups=F.gww_id):
        trk, tek = F.iloc[itr], F.iloc[ite]
        trk, tek = trk[trk.last_label_month <= SPLIT], tek[tek.month > SPLIT]
        parts.append(pd.concat([tek[KEEP], predict_all(trk, tek, per_dam_ok=False)], axis=1))
    S = pd.concat(parts)
    rows += metrics(S, S.drop(columns=KEEP), "strict (unseen dams AND test 2019-2025)")
    preds.append(S.assign(design="strict"))

    sk = pd.DataFrame(rows).assign(subset=tag, horizon_months=horizon)
    if horizon:
        sk["level_r2_within_dam"] = np.nan  # level reconstruction is only defined for the nowcast
    print(sk.round(3).to_string(), flush=True)
    pd.concat(preds).to_parquet(RESULTS / f"predictions_us_{tag}_h{horizon}.parquet")
    return sk, A, L


panel, st, clim = load_inputs()
us = st[(st.truth == "eia923") & st.storage_dam]
# EXPLORATORY subset, defined after seeing that the pre-registered CV filter lets in noise-dominated reservoirs:
# carry-over storage by statics only (HydroLAKES residence time >= 100 d and polygon >= 10 km2). Label-free.
carry = us[(us.res_time_days >= 100) & (us.gww_poly_km2 >= 10)]
print("pre-registered storage set:", len(us), "| exploratory carry-over set:", len(carry))
tables = []
for tag, ids in [("prereg", us.gww_id), ("carryover", carry.gww_id)]:
    for h in (0, 6):
        sk, A, L = run(tag, ids, h)
        tables.append(sk)
        if tag == "prereg" and h == 0:
            A0, L0 = A, L
pd.concat(tables).to_csv(RESULTS / "skill_table.csv", index=False)
A, L = A0, L0

# per-dam skill in the leave-dams-out design, with statics, to show where the signal lives
per = L.groupby("gww_id").apply(lambda d: pd.Series({
    "n": len(d), "r_area_linear": np.corrcoef(d.y, d.area_linear_pooled)[0, 1], "r_gbm_area": np.corrcoef(d.y, d.gbm_area)[0, 1],
    "r_gbm_all": np.corrcoef(d.y, d["gbm_area+climate"])[0, 1], "r_gbm_climate": np.corrcoef(d.y, d.gbm_climate)[0, 1],
    "skill_gbm_all": 1 - ((d.y - d["gbm_area+climate"]) ** 2).sum() / (d.y ** 2).sum()})).reset_index()
per.merge(st, on="gww_id").to_csv(RESULTS / "per_dam_skill.csv", index=False)

# final models on all US data (features with full-record climatology) for transfer/application
for name in ["gbm_area", "gbm_area+climate", "gbm_climate"]:
    _, m = gbm(A, A.head(5), FEATSETS[name])
    m.booster_.save_model(str(ROOT / "models" / f"{name}.txt"))
    for q in (0.1, 0.9):
        _, mq = gbm(A, A.head(5), FEATSETS[name], objective="quantile", alpha=q)
        mq.booster_.save_model(str(ROOT / "models" / f"{name}_q{int(q * 100)}.txt"))
imp = pd.Series(lgb.Booster(model_file=str(ROOT / "models" / "gbm_area+climate.txt")).feature_importance("gain"), index=FEATSETS["gbm_area+climate"])
(imp / imp.sum()).sort_values(ascending=False).round(4).to_csv(RESULTS / "feature_importance.csv", header=["gain_share"])
print((imp / imp.sum()).sort_values(ascending=False).round(3).head(12))
