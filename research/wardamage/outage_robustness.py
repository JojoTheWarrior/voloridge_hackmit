"""Do the validations lean on SNPP outage months? Recompute headline stats with every month touching an outage window removed."""
import pandas as pd, numpy as np, json
from flarelib import stats_pair, bad_days
bm=sorted(set(d.to_period('M').to_timestamp() for d in bad_days('N',0))); print('months touching SNPP outage/degraded days:',[str(m.date())[:7] for m in bm])
out={'outage_months':[str(m.date())[:7] for m in bm]}
y=pd.read_csv('labels/nd_dmr_gas_monthly.csv',index_col=0,parse_dates=True).flared_mcfd
for basin,var,lab in [('bakken','frp_p90|min3',y)]:
    V=pd.read_csv(f'data/{basin}_monthly_flare_metrics.csv',index_col=0,parse_dates=True)[var]
    a=stats_pair(V,lab); b=stats_pair(V[~V.index.isin(bm)],lab); out[basin]={'all_months':{k:v[0] for k,v in a.items() if isinstance(v,tuple)},'outage_months_removed':{k:v[0] for k,v in b.items() if isinstance(v,tuple)}}
M=pd.read_csv('data/intl_monthly_flare_frp.csv',index_col=0,parse_dates=True); P=pd.read_csv('labels/eia_intl_crude_kbd_monthly.csv',index_col=0,parse_dates=True)
for c in ['Libya','Iraq','Iran','Yemen','Algeria']:
    a=stats_pair(M[c][:'2024-12'],P[c][:'2024-12']); b=stats_pair(M[c][:'2024-12'][~M[c][:'2024-12'].index.isin(bm)],P[c][:'2024-12']); out[c]={'yoy_all':a['yoy_dlog'][0],'yoy_outage_months_removed':b['yoy_dlog'][0],'mom_all':a['mom_dlog'][0],'mom_removed':b['mom_dlog'][0]}
print(json.dumps(out,indent=1)); json.dump(out,open('data/outage_robustness.json','w'),indent=1)
