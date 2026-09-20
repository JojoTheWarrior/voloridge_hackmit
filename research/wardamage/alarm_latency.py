"""How many days until the regional flare gauge flags the 2026 shut-in, and how often does the same alarm fire in the 14-month baseline (false alarms)?"""
import pandas as pd, numpy as np, json
D=pd.read_csv('data/cloud_normalised_daily.csv',header=[0,1],index_col=0,parse_dates=True)
out=[]
for reg in D.columns.levels[0]:
    s=D[reg]; 
    for N in (7,14,28):
        r=(s.obs_clear.rolling(N).sum()/s.exp_clear.rolling(N).sum())
        base=r[:'2026-02-27'].dropna(); thr=base.quantile(0.02)     # alarm = N-day normalised ratio below the 2nd percentile of baseline
        # false-alarm episodes in baseline (distinct runs below thr)
        below=(base<thr); episodes=int(((below)&(~below.shift(1,fill_value=False))).sum())
        war=r['2026-02-28':'2026-06-17']; hit=war[war<thr]
        out.append({'region':reg,'window_days':N,'threshold_ratio':round(float(thr),2),'baseline_alarm_episodes':episodes,'first_alarm_2026':str(hit.index[0].date()) if len(hit) else None,'days_after_war_start':int((hit.index[0]-pd.Timestamp('2026-02-28')).days) if len(hit) else None,'min_ratio_in_war':round(float(war.min()),2),'share_war_days_in_alarm':round(float((war<thr).mean()),2)})
T=pd.DataFrame(out); T.to_csv('data/alarm_latency.csv',index=False); pd.set_option('display.width',250); print(T.to_string())
