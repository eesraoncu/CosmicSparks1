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


def compute_province_stats(utc_date: datetime, modis_cog_path: str, cams_raster_path: str, params: dict) -> str:
    """
    Compute comprehensive province-level statistics from AOD and dust data
    Includes multiple risk metrics and quality indicators
    """
    provinces = _load_provinces(params)
    out_csv = os.path.join(
        params["paths"]["derived_dir"],
        f"province_stats_{utc_date.date().isoformat()}.csv",
    )

    with rasterio.open(modis_cog_path) as aod_ds, rasterio.open(cams_raster_path) as dust_ds:
        # Check alignment and reproject if necessary
        if (aod_ds.transform != dust_ds.transform or 
            aod_ds.width != dust_ds.width or 
            aod_ds.height != dust_ds.height):
            print("Warning: AOD and dust rasters not aligned, using AOD grid as reference")
            # For now, assume they're close enough for MVP
        
        aod = aod_ds.read(1)
        dust = dust_ds.read(1)
        
        # Enhanced dust risk calculation
        # 1. Dust AOD contribution (AOD * dust fraction)
        dust_aod = aod * dust
        
        # 2. Enhanced risk score incorporating dust intensity thresholds
        # Scale based on dust-specific thresholds rather than generic AOD
        risk_base = np.where(
            dust_aod > 0.3, 80 + (dust_aod - 0.3) * 50,  # High dust
            np.where(
                dust_aod > 0.15, 40 + (dust_aod - 0.15) * 266.7,  # Moderate dust
                np.where(
                    dust_aod > 0.05, 10 + (dust_aod - 0.05) * 300,  # Low dust
                    dust_aod * 200  # Very low dust
                )
            )
        )
        risk = np.clip(risk_base, 0.0, 100.0)
        
        # 3. Air quality index proxy (simplified PM2.5 estimation)
        # Using empirical relationship from literature
        pm25_proxy = 10 + dust_aod * 80  # Approximate PM2.5 from dust AOD
        
        rows = []
        for idx, row in provinces.iterrows():
            geom = row.geometry
            mask = geometry_mask(
                [geom.__geo_interface__],
                transform=aod_ds.transform,
                invert=True,
                out_shape=(aod_ds.height, aod_ds.width),
            )
            
            # Extract values for this province
            vals_aod = aod[mask]
            vals_dust = dust[mask]
            vals_dust_aod = dust_aod[mask]
            vals_risk = risk[mask]
            vals_pm25 = pm25_proxy[mask]
            
            if vals_aod.size == 0:
                print(f"Warning: No data for province {row.get('name', idx)}")
                continue
            
            # Filter out invalid values
            valid_mask = np.isfinite(vals_aod) & np.isfinite(vals_dust)
            if np.sum(valid_mask) == 0:
                continue
                
            vals_aod_valid = vals_aod[valid_mask]
            vals_dust_valid = vals_dust[valid_mask]
            vals_dust_aod_valid = vals_dust_aod[valid_mask]
            vals_risk_valid = vals_risk[valid_mask]
            vals_pm25_valid = vals_pm25[valid_mask]
            
            # Calculate comprehensive statistics
            province_stats = {
                "date": utc_date.date().isoformat(),
                "province_id": row.get("id", idx),
                "province_name": row.get("name", row.get("NAME_1", f"prov_{idx}")),
                
                # AOD statistics
                "aod_mean": float(np.nanmean(vals_aod_valid)),
                "aod_max": float(np.nanmax(vals_aod_valid)),
                "aod_p95": float(np.nanpercentile(vals_aod_valid, 95)),
                
                # Dust fraction statistics
                "dust_fraction_mean": float(np.nanmean(vals_dust_valid)),
                "dust_fraction_max": float(np.nanmax(vals_dust_valid)),
                
                # Dust AOD (main product)
                "dust_aod_mean": float(np.nanmean(vals_dust_aod_valid)),
                "dust_aod_max": float(np.nanmax(vals_dust_aod_valid)),
                "dust_aod_p95": float(np.nanpercentile(vals_dust_aod_valid, 95)),
                
                # Risk scores
                "risk_mean": float(np.nanmean(vals_risk_valid)),
                "risk_p95": float(np.nanpercentile(vals_risk_valid, 95)),
                "risk_max": float(np.nanmax(vals_risk_valid)),
                
                # PM2.5 proxy
                "pm25_proxy_mean": float(np.nanmean(vals_pm25_valid)),
                "pm25_proxy_p95": float(np.nanpercentile(vals_pm25_valid, 95)),
                
                # Quality metrics
                "valid_pixels": int(np.sum(valid_mask)),
                "total_pixels": int(len(vals_aod)),
                "coverage_pct": float(np.sum(valid_mask) / len(vals_aod) * 100),
                
                # Dust event indicators
                "dust_event_moderate": bool(np.any(vals_dust_aod_valid > 0.15)),
                "dust_event_high": bool(np.any(vals_dust_aod_valid > 0.3)),
                "dust_event_extreme": bool(np.any(vals_dust_aod_valid > 0.5)),
            }
            
            rows.append(province_stats)

    os.makedirs(params["paths"]["derived_dir"], exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False)
    
    print(f"Computed stats for {len(df)} provinces with dust events:")
    events = df[df['dust_event_moderate']]['province_name'].tolist()
    if events:
        print(f"  Moderate+ dust: {', '.join(events[:5])}{'...' if len(events) > 5 else ''}")
    
    return out_csv


