"""usage: cems_fetch2.py plants.csv out.parquet [first_year]  -- plant-hour CEMS aggregates via remote predicate pushdown."""
import duckdb, sys, time, pandas as pd
pl=pd.read_csv(sys.argv[1]); out=sys.argv[2]; y0=int(sys.argv[3]) if len(sys.argv)>3 else 2023
ids=",".join(map(str,pl.plant_id_eia)); states=",".join(f"'{s}'" for s in pl.state.unique())
con=duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs;")
u="https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_epacems__hourly_emissions.parquet"
t=time.time()
con.execute(f"""COPY (SELECT plant_id_eia, operating_datetime_utc t, sum(coalesce(gross_load_mw,0)) gross_mw, sum(nox_mass_lbs) nox_lbs, sum(so2_mass_lbs) so2_lbs,
  sum(co2_mass_tons) co2_tons, sum(heat_content_mmbtu) heat, count(*) n_units, sum((gross_load_mw>0)::int) n_units_on
  FROM read_parquet('{u}') WHERE year>={y0} AND state IN ({states}) AND plant_id_eia IN ({ids}) GROUP BY 1,2 ORDER BY 1,2) TO '{out}' (FORMAT parquet)""")
print("secs",round(time.time()-t), con.execute(f"SELECT count(*), count(distinct plant_id_eia), max(t) FROM '{out}'").fetchone())
