import os
from datetime import datetime
import numpy as np
import rasterio
from rasterio.transform import from_origin
import xarray as xr
from .download_era5 import download_era5_day


def process_era5_netcdf(netcdf_path: str, params: dict) -> dict:
    """Process ERA5 NetCDF file and extract RH/BLH on target grid"""
    try:
        ds = xr.open_dataset(netcdf_path)
        
        # Target grid parameters
        target_res = float(params["project"]["target_resolution_deg"])
        minx, miny, maxx, maxy = (25.0, 35.5, 45.0, 42.5)
        
        # Create target grid
        target_lons = np.arange(minx, maxx + target_res, target_res)
        target_lats = np.arange(miny, maxy + target_res, target_res)[::-1]
        
        results = {}
        
        # Relative humidity: handle common CDS names or calculate from temperature and dewpoint
        rh_var = None
        for name in ['relative_humidity', 'r', '2m_relative_humidity']:
            if name in ds.variables:
                rh_var = name
                break
        
        if rh_var is not None:
            rh_data = ds[rh_var]
            if 'time' in rh_data.dims:
                rh_data = rh_data.mean(dim='time')  # Daily average
            
            # Interpolate to target grid
            rh_regridded = rh_data.interp(
                latitude=target_lats,
                longitude=target_lons,
                method='linear'
            )
            results['rh'] = rh_regridded.values
        else:
            # Calculate relative humidity from temperature and dewpoint
            temp_var = None
            dewpoint_var = None
            
            for name in ['2m_temperature', 't2m', 'temperature']:
                if name in ds.variables:
                    temp_var = name
                    break
            
            for name in ['2m_dewpoint_temperature', 'd2m', 'dewpoint']:
                if name in ds.variables:
                    dewpoint_var = name
                    break
            
            if temp_var is not None and dewpoint_var is not None:
                print(f"Calculating relative humidity from {temp_var} and {dewpoint_var}")
                temp_data = ds[temp_var]
                dewpoint_data = ds[dewpoint_var]
                
                if 'time' in temp_data.dims:
                    temp_data = temp_data.mean(dim='time')
                if 'time' in dewpoint_data.dims:
                    dewpoint_data = dewpoint_data.mean(dim='time')
                
                # Convert from Kelvin to Celsius
                temp_c = temp_data - 273.15
                dewpoint_c = dewpoint_data - 273.15
                
                # Calculate relative humidity using Magnus formula
                # RH = 100 * exp((17.625 * Td) / (243.04 + Td)) / exp((17.625 * T) / (243.04 + T))
                rh = 100 * np.exp((17.625 * dewpoint_c) / (243.04 + dewpoint_c)) / np.exp((17.625 * temp_c) / (243.04 + temp_c))
                
                # Interpolate to target grid
                rh_regridded = rh.interp(
                    latitude=target_lats,
                    longitude=target_lons,
                    method='linear'
                )
                results['rh'] = rh_regridded.values
                
                # Flatten to 2D if needed
                if len(results['rh'].shape) > 2:
                    results['rh'] = results['rh'].squeeze()
                    # If still not 2D, take the first slice
                    if len(results['rh'].shape) > 2:
                        results['rh'] = results['rh'][0]
            else:
                print("Warning: No temperature/dewpoint data found for RH calculation")
        
        # Boundary layer height: handle common CDS names
        blh_var = None
        for name in ['boundary_layer_height', 'blh']:
            if name in ds.variables:
                blh_var = name
                break
        if blh_var is not None:
            blh_data = ds[blh_var]
            if 'time' in blh_data.dims:
                blh_data = blh_data.mean(dim='time')  # Daily average
            
            # Interpolate to target grid
            blh_regridded = blh_data.interp(
                latitude=target_lats,
                longitude=target_lons,
                method='linear'
            )
            results['blh'] = blh_regridded.values
            
            # Flatten to 2D if needed
            if len(results['blh'].shape) > 2:
                results['blh'] = results['blh'].squeeze()
                # If still not 2D, take the first slice
                if len(results['blh'].shape) > 2:
                    results['blh'] = results['blh'][0]
        
        ds.close()
        return results
        
    except Exception as e:
        print(f"Error processing ERA5 NetCDF: {e}")
        return {}


def create_synthetic_era5(utc_date: datetime, params: dict) -> dict:
    """Create synthetic ERA5 data with realistic patterns"""
    res = float(params["project"]["target_resolution_deg"])
    minx, miny, maxx, maxy = (25.0, 35.5, 45.0, 42.5)
    width = int((maxx - minx) / res)
    height = int((maxy - miny) / res)

    rng = np.random.default_rng((abs(hash(utc_date.date())) + 4242) % (2**32))
    
    # Create coordinate grids
    lat_coords = np.linspace(maxy, miny, height)
    lon_coords = np.linspace(minx, maxx, width)
    lat_grid, lon_grid = np.meshgrid(lat_coords, lon_coords, indexing='ij')
    
    # Relative humidity with realistic patterns
    # Higher near coasts, lower inland, seasonal variation
    coastal_dist_west = np.abs(lon_grid - 25.0)  # Distance from western coast
    coastal_dist_south = np.abs(lat_grid - 35.5)  # Distance from southern coast
    coastal_effect = np.maximum(0, 20 - np.minimum(coastal_dist_west * 3, coastal_dist_south * 4))
    
    base_rh = 45 + coastal_effect
    
    # Add seasonal variation
    month = utc_date.month
    seasonal_rh = 10 * np.sin((month - 1) * np.pi / 6)  # Winter higher, summer lower
    
    # Add daily noise
    rh_noise = rng.normal(0, 5, size=(height, width))
    rh = np.clip(base_rh + seasonal_rh + rh_noise, 10.0, 95.0)
    
    # Boundary layer height (higher inland, daytime peak)
    # Lower near mountains, higher in plains
    elevation_proxy = (lat_grid - 35.5) * 200  # Rough elevation increase northward
    base_blh = 800 + (lon_grid - 25.0) * 15 - elevation_proxy  # Higher inland, lower at altitude
    
    # Add seasonal and daily variation
    seasonal_blh = 200 * np.sin((month - 3) * np.pi / 6)  # Peak in summer
    blh_noise = rng.normal(0, 100, size=(height, width))
    blh = np.clip(base_blh + seasonal_blh + blh_noise, 200.0, 2500.0)
    
    return {
        'rh': rh.astype(np.float32),
        'blh': blh.astype(np.float32)
    }


def is_date_available_for_era5(date: datetime) -> bool:
    """
    Check if date is likely available for ERA5 data
    ERA5 typically has 5-7 days delay for final data
    """
    from datetime import timezone
    days_ago = (datetime.now(timezone.utc) - date).days
    # Conservative estimate: data available after 7 days
    return days_ago >= 7


def ingest_era5_day(utc_date: datetime, params: dict) -> dict:
    """
    Complete ERA5 meteorological data ingestion pipeline
    Downloads and processes RH and BLH data
    """
    out_dir = params["paths"]["derived_dir"]
    os.makedirs(out_dir, exist_ok=True)
    
    # Check if date is too recent for real data
    if not is_date_available_for_era5(utc_date):
        days_ago = (datetime.utcnow() - utc_date).days
        print(f"Date {utc_date.date()} is too recent ({days_ago} days ago) for ERA5 final data")
        print("Using synthetic meteorological data instead...")
        era5_data = create_synthetic_era5(utc_date, params)
    else:
        # Try to download real ERA5 data
        try:
            era5_file = download_era5_day(utc_date, params)
            print(f"Downloaded ERA5 file: {era5_file}")
            
            # Process real data
            era5_data = process_era5_netcdf(era5_file, params)
            if era5_data:
                print("Processed real ERA5 data")
            else:
                print("ERA5 processing failed, using synthetic")
                era5_data = create_synthetic_era5(utc_date, params)
        except Exception as e:
            print(f"ERA5 download/processing failed: {e}")
            era5_data = create_synthetic_era5(utc_date, params)
    
    # Save to GeoTIFF files
    res = float(params["project"]["target_resolution_deg"])
    minx, miny, maxx, maxy = (25.0, 35.5, 45.0, 42.5)
    transform = from_origin(minx, maxy, res, res)
    
    rh_path = os.path.join(out_dir, f"era5_rh_{utc_date.date().isoformat()}.tif")
    blh_path = os.path.join(out_dir, f"era5_blh_{utc_date.date().isoformat()}.tif")
    
    # Get data arrays
    rh_data = era5_data.get('rh')
    blh_data = era5_data.get('blh')
    
    if rh_data is None or blh_data is None:
        # Fallback to original synthetic method
        print("Using fallback synthetic method")
        synthetic = create_synthetic_era5(utc_date, params)
        rh_data = synthetic['rh']
        blh_data = synthetic['blh']
    
    height, width = rh_data.shape[-2:]  # Get last 2 dimensions
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
    
    # Save RH
    with rasterio.open(rh_path, "w", **profile) as dst:
        dst.write(rh_data, 1)
    
    # Save BLH
    with rasterio.open(blh_path, "w", **profile) as dst:
        dst.write(blh_data, 1)

    return {"rh": rh_path, "blh": blh_path}


