import duckdb, time
con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs;")
u = "https://s3.us-west-2.amazonaws.com/pudl.catalyst.coop/nightly/core_epacems__hourly_emissions.parquet"
df = con.execute(f"SELECT row_group_id, path_in_schema, stats_min_value, stats_max_value, row_group_num_rows FROM parquet_metadata('{u}') WHERE path_in_schema IN ('state','year','operating_datetime_utc')").fetchdf()
df.to_parquet("cems_rowgroups.parquet")
print(df.head(9)); print(df.tail(9))
y = df[df.path_in_schema=='year']
print(y.stats_max_value.value_counts().sort_index().tail(5))
d = df[df.path_in_schema=='operating_datetime_utc']
print(d.stats_max_value.max())
