import rasterio, time, os
from rasterio.windows import from_bounds
os.environ.update(AWS_NO_SIGN_REQUEST="YES", GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES")
p="/vsis3/meeo-s5p/COGT/OFFL/L2__NO2___/2025/07/15/S5P_OFFL_L2__NO2____20250715T193219_20250715T211349_40185_03_020800_20250717T114612_PRODUCT_nitrogendioxide_tropospheric_column_4326.tif"
t=time.time()
with rasterio.open(p) as ds:
    for name,(lat,lon) in {"FourCorners":(36.69,-108.4814),"Colstrip":(45.8831,-106.614),"Bridger":(41.7378,-108.7875)}.items():
        w=from_bounds(lon-1,lat-1,lon+1,lat+1,ds.transform)
        a=ds.read(1,window=w); a[a==-9999]=float('nan')
        import numpy as np
        print(name,a.shape,np.nanmean(a)*1e6,np.nanmax(a)*1e6, np.isnan(a).mean(), round(time.time()-t,1))
