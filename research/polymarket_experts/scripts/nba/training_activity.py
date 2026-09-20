"""Freeze market-maker flags using only fills before the training cutoff."""
import sys
from pathlib import Path
import pandas as pd
import duckdb
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from build import EXCHANGES

def main():
 c=duckdb.connect();c.execute("SET memory_limit='256MB'");c.execute("SET temp_directory='"+str(R/'data/nba/tmp')+"'")
 files=str(R/'data/nba/filtered/v1_*.parquet')
 d=c.execute(f"""SELECT lower(maker) wallet, count(*) flow_n_fills,
 sum(CASE WHEN maker_asset_id='0' THEN maker_amount_filled::DOUBLE ELSE taker_amount_filled::DOUBLE END)/1e6 flow_notional,
 sum(CASE WHEN maker_asset_id='0' THEN maker_amount_filled::DOUBLE ELSE 0 END)/1e6 flow_buy_volume,
 sum(CASE WHEN maker_asset_id='0' THEN 0 ELSE taker_amount_filled::DOUBLE END)/1e6 flow_sell_volume,
 sum(CASE WHEN maker_asset_id='0' THEN -maker_amount_filled::DOUBLE ELSE taker_amount_filled::DOUBLE-fee::DOUBLE END)/1e6 flow_cash
 FROM read_parquet('{files}') WHERE timestamp<1735689600 GROUP BY 1""").df()
 d=d[~d.wallet.isin(EXCHANGES)]
 d['market_maker']=(d.flow_n_fills>=100)&(d.flow_buy_volume>=.25*d.flow_notional)&(d.flow_sell_volume>=.25*d.flow_notional)&(d.flow_notional/(1+d.flow_cash.abs())>10)
 d.to_parquet(R/'data/nba/training_wallet_activity.parquet',index=False,compression='zstd');print('Training MM flags',int(d.market_maker.sum()),'of',len(d))
if __name__=='__main__':main()
