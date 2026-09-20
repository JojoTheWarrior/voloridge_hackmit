"""TROPOMI SO2 over Gulf/Iran/Iraq plants: fuel discrimination (GPPD oil vs gas), winter mazut switching in Iran, war-window change."""
import pandas as pd, numpy as np
from sklearn.metrics import roc_auc_score
R = pd.read_csv("foreign_activity_index.csv"); s = pd.read_csv("so2_daily_foreign.csv", parse_dates=["day"]); s = s[s.ws.between(2, 9)]
print("AUC of SO2 t-stat for GPPD fuel Oil vs Gas: %.3f (n_oil=%d, n_gas=%d)" % (roc_auc_score(R.fuel == "Oil", R.so2_t), (R.fuel == "Oil").sum(), (R.fuel == "Gas").sum()))
print("AUC of NO2 t-stat for Oil vs Gas (control): %.3f" % roc_auc_score(R.fuel == "Oil", R.t_stat))
rows = []
for p, g in s.groupby("plant"):
    g = g.set_index("day").enh; w = g[(g.index.month.isin([12, 1, 2])) & (g.index < "2026-02-28")]; su = g[g.index.month.isin([6, 7, 8])]
    war = g["2026-02-28":"2026-04-08"]; ref = g["2025-02-28":"2025-04-08"]
    rows.append(dict(plant=p, so2_winter=w.mean(), so2_summer=su.mean(), n_w=len(w), n_s=len(su), winter_t=w.mean()/(w.std()/np.sqrt(len(w))), summer_t=su.mean()/(su.std()/np.sqrt(len(su))), so2_war=war.mean(), so2_same_window_2025=ref.mean(), n_war=len(war)))
S = R[["plant", "country", "fuel", "so2_t"]].merge(pd.DataFrame(rows)); S.to_csv("so2_foreign_results.csv", index=False)
ir = S[S.country == "IRN"]; pd.set_option("display.width", 250); print(ir.round(1).to_string())
print("Iran gas-labelled plants: median SO2 winter %.0f vs summer %.0f umol/m2" % (ir[ir.fuel == "Gas"].so2_winter.median(), ir[ir.fuel == "Gas"].so2_summer.median()))
d = S[S.so2_t > 5]; print("SO2-detectable plants n=%d: median war/2025-same-window SO2 ratio %.2f" % (len(d), (d.so2_war/d.so2_same_window_2025).median()))
