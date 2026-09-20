import duckdb, time
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; SET s3_region='us-west-2';")
u = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_epacems__hourly_emissions.parquet"
t=time.time()
print(con.execute(f"DESCRIBE SELECT * FROM read_parquet('{u}')").fetchdf())
print(con.execute(f"SELECT count(*) n_rowgroups, min(stats_min) , max(stats_max) FROM parquet_metadata('{u}') WHERE path_in_schema='year'").fetchdf())
print(time.time()-t)
