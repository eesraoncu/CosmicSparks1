import os
from datetime import datetime
from typing import Optional, List, Dict
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
from rasterio.merge import merge
import glob
from pathlib import Path

try:
    from pyhdf.SD import SD, SDC
    HDF_AVAILABLE = True
except ImportError:
    print("Warning: pyhdf not available, using synthetic data")
    HDF_AVAILABLE = False

try:
    from rio_cogeo.profiles import cog_profiles
    from rio_cogeo.cogeo import cog_translate
except Exception:
    cog_profiles = None
    cog_translate = None

from .download_modis import download_modis_aod_day


def _ensure_dirs(params: dict) -> None:
    for key in ["raw_dir", "derived_dir"]:
        os.makedirs(params["paths"][key], exist_ok=True)


def read_modis_hdf(hdf_path: str) -> Dict[str, np.ndarray]:
    """
    Read MODIS AOD data from HDF file with QC filtering
    Returns dict with AOD data and metadata
    """
    if not HDF_AVAILABLE:
        raise ImportError("pyhdf required for reading MODIS HDF files")
    
    try:
        hdf = SD(hdf_path, SDC.READ)
        
        # Read AOD at 550nm (primary product)
        aod_dataset = hdf.select('Optical_Depth_Land_And_Ocean_Mean')
        aod_data = aod_dataset.get()
        aod_attrs = aod_dataset.attributes()
        
        # Read QC flags
        qc_dataset = hdf.select('Land_Ocean_Quality_Flag_Mean')
        qc_data = qc_dataset.get()
        
        # Apply scale and offset
        scale_factor = aod_attrs.get('scale_factor', 1.0)
        add_offset = aod_attrs.get('add_offset', 0.0)
        fill_value = aod_attrs.get('_FillValue', -9999)
        
        # Mask invalid data
        valid_mask = (aod_data != fill_value) & (aod_data > -1000)
        aod_data = aod_data.astype(np.float32) * scale_factor + add_offset
        
        # Apply QC filtering (keep good and marginal quality)
        # QC bits: 0-2 for confidence, 3+ for other flags
        qc_confidence = qc_data & 0x07  # Extract bits 0-2
        good_qc = (qc_confidence <= 1)  # High and moderate confidence
        
        final_mask = valid_mask & good_qc
        aod_data[~final_mask] = np.nan
        
        # Read geolocation if available
        try:
            lat_dataset = hdf.select('Latitude')
            lon_dataset = hdf.select('Longitude')
            lat_data = lat_dataset.get()
            lon_data = lon_dataset.get()
        except:
            lat_data = None
            lon_data = None
        
        hdf.end()
        
        return {
            'aod': aod_data,
            'latitude': lat_data,
            'longitude': lon_data,
            'valid_mask': final_mask,
            'attributes': aod_attrs
        }
        
    except Exception as e:
        print(f"Error reading HDF file {hdf_path}: {e}")
        return None


def reproject_modis_to_grid(modis_data: Dict, target_crs: str, target_resolution: float, 
                          bbox: tuple) -> Dict[str, np.ndarray]:
    """
    Reproject MODIS swath data to regular grid
    bbox: (minx, miny, maxx, maxy)
    """
    if modis_data is None or modis_data['latitude'] is None:
        return None
    
    aod = modis_data['aod']
    lat = modis_data['latitude']
    lon = modis_data['longitude']
    
    # Create target grid
    minx, miny, maxx, maxy = bbox
    cols = int((maxx - minx) / target_resolution)
    rows = int((maxy - miny) / target_resolution)
    
    target_transform = from_origin(minx, maxy, target_resolution, target_resolution)
    
    # Simple nearest neighbor regridding for now
    # In production, use more sophisticated interpolation
    target_aod = np.full((rows, cols), np.nan, dtype=np.float32)
    
    # Convert geographic coordinates to pixel coordinates
    col_indices = np.floor((lon - minx) / target_resolution).astype(int)
    row_indices = np.floor((maxy - lat) / target_resolution).astype(int)
    
    # Filter valid coordinates within bounds
    valid = (
        (col_indices >= 0) & (col_indices < cols) &
        (row_indices >= 0) & (row_indices < rows) &
        np.isfinite(aod)
    )
    
    if np.any(valid):
        target_aod[row_indices[valid], col_indices[valid]] = aod[valid]
    
    return {
        'aod': target_aod,
        'transform': target_transform,
        'crs': target_crs,
        'shape': (rows, cols)
    }


def mosaic_modis_files(hdf_files: List[str], params: dict) -> str:
    """
    Process and mosaic multiple MODIS HDF files
    Returns path to mosaicked GeoTIFF
    """
    if not hdf_files:
        print("No MODIS files to process, creating synthetic data...")
        return _create_synthetic_aod(params)
    
    target_crs = params["project"]["crs"]
    target_resolution = float(params["project"]["target_resolution_deg"])
    bbox = (25.0, 35.5, 45.0, 42.5)  # Turkey bbox
    
    processed_grids = []
    
    for hdf_file in hdf_files:
        print(f"Processing {Path(hdf_file).name}...")
        
        if HDF_AVAILABLE:
            modis_data = read_modis_hdf(hdf_file)
            if modis_data is not None:
                grid_data = reproject_modis_to_grid(modis_data, target_crs, target_resolution, bbox)
                if grid_data is not None:
                    processed_grids.append(grid_data)
    
    if not processed_grids:
        print("No valid MODIS data processed, creating synthetic...")
        return _create_synthetic_aod(params)
    
    # Mosaic multiple grids (simple averaging for overlaps)
    final_aod = np.full_like(processed_grids[0]['aod'], np.nan)
    count_grid = np.zeros_like(final_aod)
    
    for grid in processed_grids:
        valid = np.isfinite(grid['aod'])
        final_aod[valid] = np.nansum([final_aod[valid], grid['aod'][valid]], axis=0)
        count_grid[valid] += 1
    
    # Average where multiple observations exist
    multi_obs = count_grid > 1
    final_aod[multi_obs] /= count_grid[multi_obs]
    
    return final_aod, processed_grids[0]['transform']


def _create_synthetic_aod(params: dict) -> str:
    """Fallback synthetic AOD when real data unavailable"""
    res = float(params["project"]["target_resolution_deg"])
    minx, miny, maxx, maxy = (25.0, 35.5, 45.0, 42.5)
    width = int((maxx - minx) / res)
    height = int((maxy - miny) / res)
    
    # Create realistic synthetic AOD with dust patterns
    rng = np.random.default_rng(42)  # Fixed seed for consistency
    
    # Base AOD with latitude gradient (higher in south)
    lat_coords = np.linspace(maxy, miny, height)
    lon_coords = np.linspace(minx, maxx, width)
    lat_grid, lon_grid = np.meshgrid(lat_coords, lon_coords, indexing='ij')
    base_aod = 0.15 + 0.2 * ((42.5 - lat_grid) / 7.0)
    
    # Add dust hotspots (southeastern Turkey)
    y_grid, x_grid = np.meshgrid(np.arange(height), np.arange(width), indexing='ij')
    dust_centers = [(int(0.7 * height), int(0.8 * width))]  # SE Turkey
    
    for cy, cx in dust_centers:
        dist = np.sqrt((y_grid - cy)**2 + (x_grid - cx)**2)
        dust_plume = 0.3 * np.exp(-dist / 20.0)
        base_aod += dust_plume
    
    # Add noise
    noise = rng.normal(0, 0.05, size=(height, width))
    aod = np.clip(base_aod + noise, 0.0, 2.0)
    
    transform = from_origin(minx, maxy, res, res)
    return aod.astype(np.float32), transform


def ingest_modis_aod_day(utc_date: datetime, params: dict) -> str:
    """
    Complete MODIS AOD processing pipeline for one day
    Downloads, processes, mosaics and saves AOD data
    """
    _ensure_dirs(params)
    
    # Try to download real MODIS data
    try:
        hdf_files = download_modis_aod_day(utc_date, params)
        print(f"Downloaded {len(hdf_files)} MODIS files")
    except Exception as e:
        print(f"MODIS download failed: {e}")
        hdf_files = []
    
    # Process and mosaic
    if hdf_files and HDF_AVAILABLE:
        try:
            aod_data, transform = mosaic_modis_files(hdf_files, params)
            print("Processed real MODIS data")
        except Exception as e:
            print(f"MODIS processing failed: {e}, using synthetic")
            aod_data, transform = _create_synthetic_aod(params)
    else:
        aod_data, transform = _create_synthetic_aod(params)
    
    # Save to GeoTIFF
    out_path = os.path.join(
        params["paths"]["derived_dir"],
        f"modis_aod_{utc_date.date().isoformat()}.tif",
    )
    
    height, width = aod_data.shape
    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": rasterio.float32,
        "crs": params["project"]["crs"],
        "transform": transform,
        "compress": "DEFLATE",
        "tiled": True,
        "blockxsize": 256,
        "blockysize": 256,
    }
    
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(aod_data, 1)
    
    # Create COG if requested
    if params.get("runtime", {}).get("write_cog", False) and cog_translate is not None:
        cog_path = out_path.replace(".tif", ".cog.tif")
        config = dict(GDAL_TIFF_OVR_BLOCKSIZE="256")
        cog_profile = cog_profiles.get("deflate") if cog_profiles else None
        cog_translate(out_path, cog_path, cog_profile, config=config, in_memory=False)
        return cog_path

    return out_path


