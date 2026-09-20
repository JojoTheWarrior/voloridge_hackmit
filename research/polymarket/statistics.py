"""Fixed-family inference: 10k date-cluster bootstrap, max-stat permutation, BH."""
import numpy as np
import pandas as pd
from scipy.stats import norm

SEED=20260920
B=10000

def bh(p):
    p=np.asarray(p,float);order=np.argsort(p)
    ranked=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
    q=np.empty_like(p);q[order]=np.minimum(ranked,1);return q

def boot_mean(x,seed=SEED):
    x=np.asarray(x,float);x=x[np.isfinite(x)];n=len(x)
    if n<2:return dict(effect=np.nan,lo=np.nan,hi=np.nan,p=1.,mde=np.nan,mde_family=np.nan)
    rng=np.random.default_rng(seed);means=[]
    for _ in range(100):
        means.extend(x[rng.integers(0,n,(B//100,n))].mean(axis=1))
    means=np.asarray(means);mu=x.mean();se=x.std(ddof=1)/np.sqrt(n)
    p=(1+np.sum(np.abs(means-mu)>=abs(mu)-1e-15))/(B+1)
    if np.all(x==0):p=1.
    return dict(effect=mu,lo=np.quantile(means,.025),hi=np.quantile(means,.975),p=p,
                mde=(1.96+.842)*se,mde_family=(norm.ppf(1-.05/(2*22))+.842)*se)

def paired(frame,column='effect',date='date'):
    frame=frame.dropna(subset=[column,date]);x=frame.groupby(date)[column].mean().sort_index()
    out=boot_mean(x.values);out.update(n=len(frame),n_dates=len(x),status='tested' if len(x)>=30 and len(frame)>=50 else 'insufficient')
    if out['status']!='tested':out['p']=1.
    # One fixed sign-randomized placebo per executable specification.
    out['placebo_p']=np.nan
    if out['status']=='tested':
        z=x.values*np.random.default_rng(SEED+99).choice([-1,1],len(x))
        out['placebo_p']=boot_mean(z,SEED+1)['p']
    # Registered descriptive serial-correlation robustness, no extra family claim.
    if len(x)>=7:
        rng=np.random.default_rng(SEED+7);means=[];n=len(x);v=x.values
        for _ in range(100):
            starts=rng.integers(0,n,(100,int(np.ceil(n/7))))
            ix=((starts[:,:,None]+np.arange(7))%n).reshape(100,-1)[:,:n]
            means.extend(v[ix].mean(axis=1))
        out['block7_lo'],out['block7_hi']=np.quantile(means,[.025,.975])
    return out

def correlations(frame,lags):
    """Daily aligned x and y; first 60% trains lag; late block max-stat null."""
    frame=frame.sort_index().copy();pairs=[]
    for lag in lags:
        pairs.append(pd.DataFrame({'x':frame.x,'y':frame.y.shift(-lag)}).dropna())
    dates=sorted(set.intersection(*(set(z.index) for z in pairs)))
    split=int(.6*len(dates));train_dates=dates[:split];test_dates=dates[split:]
    if len(test_dates)<60:
        return dict(status='insufficient',n=len(test_dates),n_dates=len(test_dates),p=1.,effect=np.nan,n_train=len(train_dates))
    def cor(x,y):
        return np.corrcoef(x,y)[0,1] if np.std(x)>0 and np.std(y)>0 else 0.
    train_r=[cor(z.loc[train_dates].x,z.loc[train_dates].y) for z in pairs]
    chosen=int(np.argmax(np.abs(train_r)))
    x=pairs[0].loc[test_dates].x.to_numpy();ys=np.array([z.loc[test_dates].y.to_numpy() for z in pairs])
    r=np.array([cor(x,y) for y in ys]);n=len(x);rng=np.random.default_rng(SEED)
    # Calendar-week blocks, not seven nonmissing observations: sparse GDELT
    # collection dates must not quietly turn a one-week block into months.
    days=pd.DatetimeIndex(pd.to_datetime(test_dates))
    week=((days-days.min()).days//7).to_numpy()
    blocks=[np.flatnonzero(week==w) for w in np.unique(week)]
    null=[]
    for _ in range(B):
        ix=np.concatenate([blocks[i] for i in rng.permutation(len(blocks))]);xp=x[ix]
        null.append(max(abs(cor(xp,y)) for y in ys))
    p=(1+np.sum(np.array(null)>=abs(r[chosen])))/(B+1)
    z=np.arctanh(np.clip(r[chosen],-.999999,.999999));se=1/np.sqrt(n-3)
    # Fisher interval/MDE are approximate; permutation supplies primary p.
    placebo_r=cor(np.roll(x,28),ys[chosen]);placebo_p=(1+np.sum(np.array(null)>=abs(placebo_r)))/(B+1)
    return dict(status='tested',effect=r[chosen],lo=np.tanh(z-1.96*se),hi=np.tanh(z+1.96*se),p=p,
                n=n,n_dates=n,n_train=len(train_dates),train_effect=train_r[chosen],selected_lag=lags[chosen],
                mde=np.tanh((1.96+.842)*se),mde_family=np.tanh((norm.ppf(1-.05/44)+.842)*se),placebo_p=placebo_p)
