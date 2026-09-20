"""Pick US plants for the S2 plume study: CEMS plants with natural-draft (RN) or mechanical-draft (RI/RF) towers, plus once-through controls."""
import duckdb, pandas as pd, time
con=duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs;")
b="https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/"
t=time.time()
con.execute(f"""CREATE TABLE ph AS SELECT plant_id_eia, operating_datetime_utc t, sum(gross_load_mw) mw
  FROM '{b}core_epacems__hourly_emissions.parquet' WHERE year=2024 GROUP BY 1,2""")
print("cems 2024 plant-hours", con.execute("select count(*) from ph").fetchone(), round(time.time()-t))
stats=con.execute("SELECT plant_id_eia, max(mw) max_mw, avg(coalesce(mw,0)) mean_mw, avg((coalesce(mw,0)<=0.02*m)::int) frac_off FROM ph JOIN (SELECT plant_id_eia p, max(mw) m FROM ph GROUP BY 1) ON p=plant_id_eia GROUP BY 1").fetchdf()
cool=con.execute(f"""SELECT plant_id_eia, string_agg(DISTINCT cooling_type_1, ',') ctypes, string_agg(DISTINCT tower_type_1, ',') ttypes, count(*) n_cool
  FROM '{b}_core_eia860__cooling_equipment.parquet' WHERE report_date='2024-01-01' AND cooling_status_code='OP' GROUP BY 1""").fetchdf()
pl=con.execute(f"SELECT plant_id_eia, plant_name_eia, state, latitude, longitude FROM '{b}core_eia__entity_plants.parquet'").fetchdf()
fuel=con.execute(f"""SELECT plant_id_eia, arg_max(fuel_type_code_pudl, cap) fuel FROM (SELECT plant_id_eia, fuel_type_code_pudl, sum(capacity_mw) cap
  FROM '{b}core_eia860__scd_generators.parquet' WHERE report_date='2024-01-01' AND operational_status='existing' GROUP BY 1,2) GROUP BY 1""").fetchdf()
df=stats.merge(cool,how="left").merge(pl).merge(fuel,how="left"); df.to_csv("us_plant_candidates.csv",index=False)
print(df[df.ctypes.fillna("").str.contains("RN")].sort_values("max_mw",ascending=False).to_string())
