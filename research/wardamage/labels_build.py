"""Keyless production labels -> tidy CSVs. Sources: EIA bulk INTL.zip, EIA dnav XLS, ND DMR Gas1990ToPresent.xls, JODI primary CSV."""
import json, pandas as pd, numpy as np
ISO={'IRQ':'Iraq','LBY':'Libya','DZA':'Algeria','NGA':'Nigeria','VEN':'Venezuela','KAZ':'Kazakhstan','RUS':'Russia','IRN':'Iran','SAU':'Saudi_Arabia','QAT':'Qatar','KWT':'Kuwait','ARE':'United_Arab_Emirates','OMN':'Oman','EGY':'Egypt','AGO':'Angola','TKM':'Turkmenistan','SYR':'Syria','YEM':'Yemen','USA':'USA'}
out={}
with open('labels/intl/INTL.txt') as f:
    for line in f:
        if '"INTL.57-1-' not in line or '-TBPD.M"' not in line: continue
        j=json.loads(line)
        if 'series_id' not in j: continue
        iso=j['series_id'].split('-')[2]
        if iso in ISO: out[ISO[iso]]=pd.Series({pd.Timestamp(d[:4]+'-'+d[4:]+'-01'):(np.nan if v in (None,'--','NA') else float(v)) for d,v in j['data']}).sort_index()
intl=pd.DataFrame(out)['2011':]; intl.to_csv('labels/eia_intl_crude_kbd_monthly.csv'); print(intl.tail(3).T.to_string())
# JODI crude production (KBD) cross-check
j=pd.read_csv('labels/jodi/NewProcedure_Primary_CSV.csv',dtype=str)
j=j[(j.ENERGY_PRODUCT=='CRUDEOIL')&(j.FLOW_BREAKDOWN=='INDPROD')&(j.UNIT_MEASURE=='KBD')]
j['v']=pd.to_numeric(j.OBS_VALUE,errors='coerce'); j['t']=pd.to_datetime(j.TIME_PERIOD+'-01')
jp=j.pivot_table(index='t',columns='REF_AREA',values='v')['2011':]
jp.to_csv('labels/jodi_crude_kbd_monthly.csv'); print('JODI last month',jp.index.max(), 'countries',jp.shape[1]); print(jp[['IQ','SA','QA','KW','AE','LY','DZ','NG','KZ']].tail(4).to_string() if set(['IQ','SA','QA','KW','AE']).issubset(jp.columns) else jp.columns.tolist())
# ND DMR gas
g=pd.read_excel('labels/Gas1990ToPresent.xls',header=0); g.columns=['date','prod_mcf','sold_mcf','flared_mcf','bk_prod','bk_sold','bk_flared']
g['t']=pd.to_datetime(g.date.astype(str).str.strip(),format='%m-%Y',errors='coerce'); g=g.dropna(subset=['t']).set_index('t').drop(columns='date').astype(float)
g['flared_mcfd']=g.flared_mcf/g.index.days_in_month; g.to_csv('labels/nd_dmr_gas_monthly.csv'); print(g['2025-12':].to_string())
# EIA state crude
x=pd.read_excel('labels/PET_CRD_CRPDN_ADC_MBBLPD_M.xls',sheet_name='Data 1',header=2); x=x.rename(columns={x.columns[0]:'t'}); x['t']=pd.to_datetime(x.t).dt.to_period('M').dt.to_timestamp(); x=x.set_index('t')
cols={c:c.replace(' Field Production of Crude Oil (Thousand Barrels per Day)','') for c in x.columns}; x=x.rename(columns=cols)['2011':]; x.to_csv('labels/eia_state_crude_kbd_monthly.csv'); print(x[['North Dakota','Texas','New Mexico']].tail(3))
v=pd.read_excel('labels/NG_PROD_SUM_A_EPG0_VGV_MMCF_M.xls',sheet_name='Data 1',header=2); print(v.columns.tolist()[:12]); print(v.tail(3).iloc[:,:6])
