"""Shared helpers: load GIBS tile parquet dirs / FIRMS CSVs -> night detections; monthly flare metrics; validation stats."""
import pandas as pd, numpy as np, glob
def load_gibs(dirpath, sat_prefix=None):
    dfs=[]
    for f in sorted(glob.glob(f'{dirpath}/*.parquet')):
        if sat_prefix and sat_prefix not in f: continue
        d=pd.read_parquet(f)
        if len(d) and 'LONGITUDE' in d: dfs.append(d[[c for c in ['LATITUDE','LONGITUDE','ACQ_DATE','ACQ_TIME','SATELLITE','FRP','CONFIDENCE','TYPE'] if c in d]])
    h=pd.concat(dfs,ignore_index=True).drop_duplicates(['LATITUDE','LONGITUDE','ACQ_DATE','ACQ_TIME','SATELLITE'])
    h=h.rename(columns={'LATITUDE':'lat','LONGITUDE':'lon','FRP':'frp','SATELLITE':'sat','DAYNIGHT':'dn'}); h['ACQ_DATE']=h.ACQ_DATE.astype(str).str.replace('/','-'); h['date']=pd.to_datetime(h.ACQ_DATE)
    t=h.ACQ_TIME.astype(str).str.replace(':','').str.zfill(4); lst=(t.str[:2].astype(int)+t.str[2:].astype(int)/60+h.lon/15)%24
    h['dn']=np.where((lst<6)|(lst>18),'N','D'); h['sat']=h.sat.replace({'Suomi NPP':'N','NOAA-20':'N20','NOAA-21':'N21','1':'N20','2':'N21'}); return h
def load_firms(country, years, sensor='viirs-snpp', root='data/firms_archive'):
    dfs=[]
    for y in years:
        try: d=pd.read_csv(f'{root}/{sensor}_{y}_{country}.csv',usecols=['latitude','longitude','acq_date','acq_time','satellite','frp','daynight','confidence'])
        except Exception: continue
        dfs.append(d)
    h=pd.concat(dfs,ignore_index=True).rename(columns={'latitude':'lat','longitude':'lon','satellite':'sat','daynight':'dn'}); h['date']=pd.to_datetime(h.acq_date); return h
def add_cells(h,res=0.02):
    h=h.copy(); h['cx']=np.round(h.lon/res).astype(int); h['cy']=np.round(h.lat/res).astype(int); return h
def monthly_metrics(n, full_days=None):
    """n: night detections (one satellite). Returns monthly mean nightly FRP sum, p75 of nightly sums, top-half mean, count, lit-cells."""
    s=n.groupby('date').frp.sum(); c=n.groupby('date').size()
    idx=pd.date_range(s.index.min(),s.index.max()) if full_days is None else full_days
    s=s.reindex(idx,fill_value=0.0); c=c.reindex(idx,fill_value=0)
    g=s.groupby(s.index.to_period('M'))
    out=pd.DataFrame({'frp_mean':g.mean(),'frp_p75':g.quantile(.75),'frp_p90':g.quantile(.90),'frp_tophalf':g.apply(lambda x:x.sort_values().iloc[len(x)//2:].mean()),'n_det':c.groupby(c.index.to_period('M')).mean(),'days':g.size(),'days_lit':g.apply(lambda x:(x>0).sum())})
    out.index=out.index.to_timestamp(); out.loc[out.days<15]=np.nan; return out
def stats_pair(x,y,name=''):
    """x: satellite metric, y: label. monthly. returns dict of correlations in levels / logs / MoM dlog / YoY dlog / deseasonalised."""
    from scipy import stats as st
    d=pd.concat([x,y],axis=1,keys=['x','y']).replace(0,np.nan).dropna(); r={}
    if len(d)<12: return {'n':len(d)}
    lx,ly=np.log(d.x),np.log(d.y)
    def rr(a,b):
        m=pd.concat([a,b],axis=1).dropna(); 
        return (round(float(st.pearsonr(m.iloc[:,0],m.iloc[:,1])[0]),3), round(float(st.spearmanr(m.iloc[:,0],m.iloc[:,1])[0]),3), len(m)) if len(m)>5 else (np.nan,np.nan,len(m))
    r['levels_log']=rr(lx,ly); r['mom_dlog']=rr(lx.diff(),ly.diff()); r['d3_dlog']=rr(lx.diff(3),ly.diff(3)); r['yoy_dlog']=rr(lx.diff(12),ly.diff(12))
    ds=lambda s:s-s.groupby(s.index.month).transform('mean'); 
    dt=lambda s:pd.Series(np.polyval(np.polyfit(np.arange(len(s)),s.values,2),np.arange(len(s))),index=s.index)
    r['deseason_detrend']=rr(ds(lx-dt(lx)),ds(ly-dt(ly))); r['n']=len(d); return r

def bad_days(sat='N', buffer=1, path='data/satellite_outage_calendar.csv'):
    """Outage/degraded days for a satellite (from outage_check.py), widened by +-buffer days to catch partial transition days."""
    o=pd.read_csv(path,index_col=0,parse_dates=True); o=o[(o.sat==sat)&(o.outage|o.degraded)]
    b=set()
    for d in o.index:
        for k in range(-buffer,buffer+1): b.add(d+pd.Timedelta(days=k))
    return pd.DatetimeIndex(sorted(b))
