import os
from datetime import datetime
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import geometry_mask


def _load_provinces(params: dict) -> gpd.GeoDataFrame:
    shp = params["paths"]["provinces_shp"]
    if not os.path.exists(shp):
        raise FileNotFoundError(f"Provinces shapefile not found: {shp}")
    gdf = gpd.read_file(shp)
    if gdf.crs is None:
        gdf.set_crs(params["project"]["crs"], inplace=True)
    else:
        gdf = gdf.to_crs(params["project"]["crs"])
    return gdf


def compute_meteo_stats(utc_date: datetime, rh_raster: str, blh_raster: str, params: dict) -> str:
    provinces = _load_provinces(params)
    out_csv = os.path.join(
        params["paths"]["derived_dir"],
        f"meteo_stats_{utc_date.date().isoformat()}.csv",
    )

    with rasterio.open(rh_raster) as rh_ds, rasterio.open(blh_raster) as blh_ds:
        if rh_ds.transform != blh_ds.transform or rh_ds.width != blh_ds.width or rh_ds.height != blh_ds.height:
            raise ValueError("RH and BLH rasters are not aligned in this MVP stub")
        rh = rh_ds.read(1)
        blh = blh_ds.read(1)

        rows = []
        for idx, row in provinces.iterrows():
            geom = row.geometry
            mask = geometry_mask(
                [geom.__geo_interface__],
                transform=rh_ds.transform,
                invert=True,
                out_shape=(rh_ds.height, rh_ds.width),
            )
            vals_rh = rh[mask]
            vals_blh = blh[mask]
            if vals_rh.size == 0:
                continue
            rows.append(
                {
                    "date": utc_date.date().isoformat(),
                    "province_id": row.get("id", idx),
                    "province_name": row.get("name", row.get("NAME_1", f"prov_{idx}")),
                    "rh_mean": float(np.nanmean(vals_rh)),
                    "blh_mean": float(np.nanmean(vals_blh)),
                }
            )

    os.makedirs(params["paths"]["derived_dir"], exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    return out_csv


