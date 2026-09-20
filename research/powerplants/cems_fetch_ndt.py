import duckdb, time
con = duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs;")
b = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/"
ids="(6257,703,8102,3935,6002)"
con.execute(f"COPY (SELECT plant_id_eia, plant_name_eia, state, latitude, longitude FROM read_parquet('{b}core_eia__entity_plants.parquet') WHERE plant_id_eia IN {ids}) TO 'plants_ndt.csv' (HEADER)")
t=time.time()
con.execute(f"""COPY (
SELECT plant_id_eia, operating_datetime_utc AS t, sum(gross_load_mw) AS gross_mw, sum(nox_lbs) nox_lbs, sum(op) op_hours, count(*) n_units, sum(CASE WHEN gross_load_mw>0 THEN 1 ELSE 0 END) n_units_on
FROM (SELECT plant_id_eia, operating_datetime_utc, gross_load_mw, nox_mass_lbs nox_lbs, operating_time_hours op FROM read_parquet('{b}core_epacems__hourly_emissions.parquet') WHERE year>=2024 AND state IN ('GA','OH','WV','AL') AND plant_id_eia IN {ids})
GROUP BY 1,2 ORDER BY 1,2) TO 'cems_ndt.parquet' (FORMAT parquet)""")
print("secs", time.time()-t)
print(con.execute("SELECT plant_id_eia, max(t), avg(gross_mw), max(gross_mw), avg((gross_mw=0 or gross_mw is null)::int) frac_off, max(n_units) FROM 'cems_ndt.parquet' GROUP BY 1").fetchdf().to_string())
print(open('plants_ndt.csv').read())
