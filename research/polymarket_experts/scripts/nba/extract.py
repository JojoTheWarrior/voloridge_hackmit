"""Remote Parquet predicate/projection scan; persist only mapped NBA fills.

HF files are chronological, not token-partitioned. HTTP range reads must scan
column chunks that may contain other tokens. No complete archive/file is saved.
"""
import json,sys,time,datetime
from pathlib import Path
import duckdb
import pandas as pd
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'scripts'))
from access import show
OUT=R/'data/nba/filtered';OUT.mkdir(exist_ok=True)

def run(versions=('v1','v2')):
 markets=pd.read_parquet(R/'data/nba/markets.parquet')
 c=duckdb.connect(str(R/'data/nba/extract.duckdb'))
 c.execute("SET extension_directory='"+str(R/'.cache/duckdb')+"'")
 c.execute('LOAD httpfs')
 c.execute('SET threads=2');c.execute("SET memory_limit='256MB'")
 c.execute("SET temp_directory='"+str(R/'data/nba/tmp')+"'")
 c.execute('SET http_timeout=120000');c.execute('SET http_retries=5')
 for v in versions:
  info=json.loads((R/f'data/access/hf_{v}_info.body').read_text());revision=info['sha']
  if v=='v1':tree=json.loads((R/'data/access/v1_tree.txt').read_text());m=markets[markets.cohort=='primary']
  else:
   raw=show('nba_v2_tree','https://huggingface.co/api/datasets/wzsg/polymarket-orderfilled-v2/tree/'+revision,{'recursive':'true','limit':1000})
   tree=json.loads(raw);m=markets[markets.cohort=='v2_extension']
  for entry in tree:
   path=entry['path']
   if not path.endswith('.parquet'):continue
   month=path.split('/')[0].split('=')[1]
   start=pd.Timestamp(month+'-01',tz='UTC');end=start+pd.offsets.MonthBegin(1)
   active=m[(m.created<end.timestamp())&(m.resolution>=start.timestamp())]
   if active.empty:continue
   name=v+'_'+month+'_'+Path(path).name
   dest=OUT/name
   if dest.exists():continue
   ids=set(active.token0)|set(active.token1)
   assert all(x.isdigit() for x in ids)
   ids_sql=','.join("'"+x+"'" for x in sorted(ids))
   pred=f"token_id IN ({ids_sql})" if v=='v2' else f"(maker_asset_id IN ({ids_sql}) OR taker_asset_id IN ({ids_sql}))"
   columns='timestamp,block_number,log_index,contract,maker,maker_amount_filled,taker_amount_filled,fee,'+('side,token_id' if v=='v2' else 'maker_asset_id,taker_asset_id')
   url=f'https://huggingface.co/datasets/wzsg/polymarket-orderfilled-{v}/resolve/{revision}/{path}'
   low=int(active.created.min());high=int(active.resolution.max())
   sql=f"SELECT {columns} FROM read_parquet('{url}') WHERE {pred} AND timestamp >= {low} AND timestamp <= {high}"
   print(datetime.datetime.now().isoformat(), 'SCAN',v,path,'source_MB',round(entry['size']/1e6,1),'tokens',len(ids),flush=True)
   t=time.time()
   for attempt in range(4):
    try:
     c.execute(f"COPY ({sql}) TO '{dest}.partial' (FORMAT PARQUET, COMPRESSION ZSTD)")
     Path(str(dest)+'.partial').replace(dest)
     n=c.execute(f"SELECT count(*) FROM read_parquet('{dest}')").fetchone()[0]
     meta={'version':v,'revision':revision,'source_path':path,'source_bytes':entry['size'],'url':url,'tokens_filter':len(ids),'min_timestamp':low,'max_timestamp':high,'filtered_rows':n,'output_bytes':dest.stat().st_size,'seconds':time.time()-t,'query_sha256':__import__('hashlib').sha256(sql.encode()).hexdigest(),'accessed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
     dest.with_suffix('.json').write_text(json.dumps(meta,indent=2));print('SAVED',name,n,'rows',round(time.time()-t,1),'sec',flush=True);break
    except Exception as e:
     print('RETRY',attempt,str(e)[:350],flush=True)
     if attempt==3:raise
     time.sleep(2**attempt)
 c.close()
if __name__=='__main__':run(tuple(sys.argv[1:]) or ('v1','v2'))
