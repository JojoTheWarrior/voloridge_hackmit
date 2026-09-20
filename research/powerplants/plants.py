import duckdb
con = duckdb.connect(); con.execute("INSTALL httpfs; LOAD httpfs;")
b = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/"
df = con.execute(f"""
SELECT plant_id_eia, plant_name_eia, state, latitude, longitude FROM read_parquet('{b}core_eia__entity_plants.parquet')
WHERE plant_id_eia IN (2442,8066,6204,6076,6481,6165,8069,6146,6177,8223,2103,6002,6180,6194,470,6021)
""").fetchdf()
print(df.to_string())
df.to_csv("plants.csv", index=False)
