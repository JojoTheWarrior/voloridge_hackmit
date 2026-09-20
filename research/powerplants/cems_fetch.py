import duckdb, time
con = duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs;")
u = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_epacems__hourly_emissions.parquet"
ids = "(2442,8066,6204,6076,6481,6165,8069,6146,6177,8223,2103,6002,6180,6194,470,6021)"
states = "('AZ','UT','WY','TX','MT','CO','AL','NM','MO')"
t=time.time()
con.execute(f"""COPY (
SELECT plant_id_eia, operating_datetime_utc AS t, sum(gross_load_mw) AS gross_mw, sum(nox_mass_lbs) AS nox_lbs,
       sum(so2_mass_lbs) so2_lbs, sum(co2_mass_tons) co2_tons, sum(heat_content_mmbtu) heat, sum(operating_time_hours) op_hours, count(*) n_units
FROM read_parquet('{u}') WHERE year>=2023 AND state IN {states} AND plant_id_eia IN {ids}
GROUP BY 1,2 ORDER BY 1,2) TO 'cems_plants.parquet' (FORMAT parquet)""")
print("secs", time.time()-t)
print(con.execute("SELECT plant_id_eia, min(t), max(t), count(*), avg(gross_mw), max(gross_mw), avg(nox_lbs) FROM 'cems_plants.parquet' GROUP BY 1 ORDER BY 1").fetchdf().to_string())
