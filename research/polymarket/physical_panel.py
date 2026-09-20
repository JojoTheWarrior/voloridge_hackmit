"""F1: freeze hotspot membership using 2025 only, then measure 2026 recovery.

Reads sibling cached NASA observations, writes only this folder. This avoids the
look-ahead in the sibling's full-history persistent-cell definition.
"""
import json

import numpy as np
import pandas as pd

from pmlib import DATA, ROOT

def main():
    source=ROOT.parent/'markets/data/gibs'
    frames=[];dates=[]
    for f in sorted(source.glob('2025-*.parquet'))+sorted(source.glob('2026-*.parquet')):
        if f.stem>'2026-09-18':continue
        d=pd.read_parquet(f);dates.append(f.stem)
        if d.empty:continue
        d=d[d.LONGITUDE.between(46.3,51.8)&d.LATITUDE.between(24.3,31.6)].copy()
        d['date']=f.stem;d['cx']=np.rint(d.LONGITUDE/.02).astype(int);d['cy']=np.rint(d.LATITUDE/.02).astype(int)
        frames.append(d[['date','cx','cy','FRP']])
    h=pd.concat(frames,ignore_index=True);train=h[h.date<'2026-01-01']
    n_train=sum(d.startswith('2025') for d in dates)
    count=train.groupby(['cx','cy']).date.nunique()
    cells=count[count/n_train>=.05].rename('prior_days').reset_index()
    cells.to_parquet(DATA/'flare_frozen_cells_2025.parquet',index=False)
    h=h[h.date>='2026-01-01'].merge(cells,on=['cx','cy'],how='inner')
    s=h.groupby('date').FRP.sum().reindex([d for d in dates if d>='2026-01-01'],fill_value=0).sort_index()
    # Only archived observation dates are counted; absent source files are missing.
    s=s.reindex(pd.date_range('2026-01-01','2026-09-18').strftime('%Y-%m-%d'))
    out=pd.DataFrame({'date':s.index,'frp':s.values,'change':np.log1p(s).diff().to_numpy()})
    out.to_parquet(DATA/'flare_point_in_time.parquet',index=False)
    (DATA/'flare_point_in_time_metadata.json').write_text(json.dumps(dict(training_days=n_train,cells=len(cells),
        frozen_before='2026-01-01',region=[46.3,24.3,51.8,31.6],persistence_threshold=.05,
        note='Geographic union of Basra/Gulf region; cells frozen in 2025. File-date observations, 48h lag assumed; archive is not publication-vintage and cloud coverage still confounds FRP.'),indent=2))
    print('physical panel',len(out),'days;',len(cells),'cells frozen before 2026',flush=True)

if __name__=='__main__':
    main()
