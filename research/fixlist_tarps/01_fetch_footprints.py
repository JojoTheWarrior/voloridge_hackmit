"""Stream Microsoft Global ML Building Footprints (keyless) for a bbox -> GeoParquet.
Nothing but the in-bbox subset touches disk."""
import sys, gzip, json, math
import pandas as pd, geopandas as gpd, requests
from shapely.geometry import shape

def quadkey(lat, lon, z=9):
    x = int((lon + 180) / 360 * 2**z)
    s = math.sin(math.radians(lat))
    y = int((0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 2**z)
    return "".join(str(((x >> i) & 1) + 2 * ((y >> i) & 1)) for i in range(z - 1, -1, -1))

def fetch(bbox, out):
    w, s, e, n = bbox
    qks = {quadkey(la, lo) for la in (s, n, (s + n) / 2) for lo in (w, e, (w + e) / 2)}
    links = pd.read_csv("data/ms_dataset_links.csv", dtype=str)
    links = links[(links.Location == "UnitedStates") & links.QuadKey.isin(qks)]
    print(links[["QuadKey", "Size", "UploadDate"]], flush=True)
    geoms, heights = [], []
    for url in links.Url:
        r = requests.get(url, stream=True, timeout=600)
        r.raise_for_status()
        n_seen = 0
        with gzip.GzipFile(fileobj=r.raw) as gz:
            for line in gz:
                n_seen += 1
                f = json.loads(line)
                x, y = f["geometry"]["coordinates"][0][0][:2]
                if w <= x <= e and s <= y <= n:
                    geoms.append(shape(f["geometry"]))
                    heights.append(f.get("properties", {}).get("height", -1))
        print(url[-60:], "seen", n_seen, "kept so far", len(geoms), flush=True)
    gdf = gpd.GeoDataFrame({"ms_height": heights}, geometry=geoms, crs=4326)
    gdf["bid"] = range(len(gdf))
    gdf.to_parquet(out)
    print(len(gdf), "buildings ->", out)

if __name__ == "__main__":
    name = sys.argv[1]; bbox = [float(v) for v in sys.argv[2:6]]
    fetch(bbox, f"data/footprints_{name}.parquet")
