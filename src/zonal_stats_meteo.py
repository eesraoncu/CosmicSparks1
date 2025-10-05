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


def _get_province_id_mapping() -> dict:
    """
    Create mapping from shapefile province names to database province IDs
    This fixes the mismatch between shapefile IDs and database IDs
    """
    # Shapefile province names -> Database province IDs
    mapping = {
        'Istanbul': 34, 'Bursa': 16, 'Kocaeli': 41, 'Sakarya': 54, 'Tekirdag': 59,
        'Edirne': 22, 'Kirklareli': 39, 'Balikesir': 10, 'Canakkale': 17, 'Yalova': 77,
        'Adana': 1, 'Adiyaman': 2, 'Afyonkarahisar': 3, 'Agri': 4, 'Amasya': 5,
        'Ankara': 6, 'Antalya': 7, 'Artvin': 8, 'Aydin': 9, 'Bilecik': 11,
        'Bingol': 12, 'Bitlis': 13, 'Bolu': 14, 'Burdur': 15, 'Cankiri': 18,
        'Corum': 19, 'Denizli': 20, 'Diyarbakir': 21, 'Elazig': 23, 'Erzincan': 24,
        'Erzurum': 25, 'Eskisehir': 26, 'Gaziantep': 27, 'Giresun': 28, 'Gumushane': 29,
        'Hakkari': 30, 'Hatay': 31, 'Isparta': 32, 'Mersin': 33, 'Izmir': 35,
        'Kars': 36, 'Kastamonu': 37, 'Kayseri': 38, 'Kirsehir': 40, 'Konya': 42,
        'Kutahya': 43, 'Malatya': 44, 'Manisa': 45, 'Kahramanmaras': 46, 'Mardin': 47,
        'Mugla': 48, 'Mus': 49, 'Nevsehir': 50, 'Nigde': 51, 'Ordu': 52,
        'Rize': 53, 'Samsun': 55, 'Siirt': 56, 'Sinop': 57, 'Sivas': 58,
        'Tokat': 60, 'Trabzon': 61, 'Tunceli': 62, 'Sanliurfa': 63, 'Usak': 64,
        'Van': 65, 'Yozgat': 66, 'Zonguldak': 67, 'Aksaray': 68, 'Bayburt': 69,
        'Karaman': 70, 'Kirikkale': 71, 'Batman': 72, 'Sirnak': 73, 'Bartin': 74,
        'Ardahan': 75, 'Igdir': 76, 'Karabuk': 78, 'Kilis': 79, 'Osmaniye': 80,
        'Duzce': 81
    }
    return mapping


def compute_meteo_stats(utc_date: datetime, rh_raster: str, blh_raster: str, params: dict) -> str:
    provinces = _load_provinces(params)
    province_mapping = _get_province_id_mapping()
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
            province_name = row.get("name", row.get("NAME_1", f"prov_{idx}"))
            db_province_id = province_mapping.get(province_name, row.get("id", idx))
            
            rows.append(
                {
                    "date": utc_date.date().isoformat(),
                    "province_id": db_province_id,
                    "province_name": province_name,
                    "rh_mean": float(np.nanmean(vals_rh)),
                    "blh_mean": float(np.nanmean(vals_blh)),
                }
            )

    os.makedirs(params["paths"]["derived_dir"], exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    return out_csv


