import os
from datetime import datetime
from typing import Dict, List
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling
import xarray as xr
import logging
import threading
import time

try:
    from rio_cogeo.profiles import cog_profiles
    from rio_cogeo.cogeo import cog_translate
except Exception:
    cog_profiles = None
    cog_translate = None

from .download_cams import download_cams_dust_day
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    pass

def process_cams_netcdf(netcdf_path: str, target_params: dict, timeout_seconds: int = 120) -> np.ndarray:
    """
    Process CAMS NetCDF file and regrid to target resolution
    Returns dust fraction array aligned with target grid
    """
    logger.info(f"Processing CAMS NetCDF: {netcdf_path}")
    
    result = [None]
    exception = [None]
    
    def process_netcdf():
        try:
            logger.info("Opening NetCDF file...")
            # Read CAMS data with explicit engine
            ds = xr.open_dataset(netcdf_path, engine='netcdf4')
            
            logger.info(f"NetCDF variables: {list(ds.variables.keys())}")
            logger.info(f"NetCDF dimensions: {dict(ds.dims)}")
            
            # Get dust AOD variable (name may vary)
            dust_var = None
            possible_names = ['dust_aerosol_optical_depth_550nm', 'duaod550', 'aod550', 'od550dust']
            for name in possible_names:
                if name in ds.variables:
                    dust_var = name
                    logger.info(f"Found dust variable: {dust_var}")
                    break
            
            if dust_var is None:
                logger.warning(f"No dust variable found in {netcdf_path}")
                logger.warning(f"Available variables: {list(ds.variables.keys())}")
                result[0] = None
                return
            
            logger.info("Extracting dust data...")
            # Get the latest time step
            dust_data = ds[dust_var]
            if 'time' in dust_data.dims:
                dust_data = dust_data.isel(time=-1)  # Latest forecast
                logger.info("Selected latest time step")
            
            # Squeeze all single dimensions
            dust_data = dust_data.squeeze()
            logger.info(f"Dust data shape after squeeze: {dust_data.shape}")
            
            # Get coordinates - handle different naming conventions
            lat_name = 'latitude' if 'latitude' in ds else 'lat'
            lon_name = 'longitude' if 'longitude' in ds else 'lon'
            logger.info(f"Using coordinate names: lat={lat_name}, lon={lon_name}")
            
            # Ensure we have 1D coordinate arrays
            if lat_name in dust_data.coords:
                lats = dust_data[lat_name].values
            else:
                lats = ds[lat_name].values
                
            if lon_name in dust_data.coords:
                lons = dust_data[lon_name].values
            else:
                lons = ds[lon_name].values
            
            logger.info(f"Coordinate ranges: lat={lats.min():.2f} to {lats.max():.2f}, lon={lons.min():.2f} to {lons.max():.2f}")
            
            # Target grid parameters
            target_res = float(target_params["project"]["target_resolution_deg"])
            minx, miny, maxx, maxy = (25.0, 35.5, 45.0, 42.5)  # Turkey bbox
            
            # Create target grid
            target_lons = np.arange(minx, maxx + target_res, target_res)
            target_lats = np.arange(miny, maxy + target_res, target_res)[::-1]  # Flip for north-up
            
            logger.info(f"Target grid: {len(target_lats)} x {len(target_lons)} points")
            
            # Ensure dust_data has proper coordinates for interpolation
            if lat_name not in dust_data.coords or lon_name not in dust_data.coords:
                logger.info("Assigning coordinates to dust data...")
                # Manually assign coordinates if missing
                dust_data = dust_data.assign_coords({lat_name: lats, lon_name: lons})
            
            logger.info("Performing interpolation...")
            # Use numpy/scipy for much faster interpolation
            from scipy.interpolate import RegularGridInterpolator
            
            # Create interpolator
            points = (lats, lons)
            values = dust_data.values
            
            # Handle multi-dimensional data
            if values.ndim > 2:
                values = values[0]  # Take first time/level slice
            
            interpolator = RegularGridInterpolator(points, values, method='linear', bounds_error=False, fill_value=0)
            
            # Create target grid points
            lon_grid, lat_grid = np.meshgrid(target_lons, target_lats)
            target_points = np.column_stack([lat_grid.ravel(), lon_grid.ravel()])
            
            # Interpolate
            regridded_values = interpolator(target_points).reshape(len(target_lats), len(target_lons))
            
            logger.info("Interpolation completed")
            
            logger.info("Converting to dust fraction...")
            # Convert dust AOD to dust fraction (simplified)
            # In reality, this would need total AOD from CAMS
            dust_fraction = np.clip(regridded_values / 0.5, 0.0, 1.0)  # Assume max dust AOD of 0.5
            
            # Ensure we have exactly 2D array
            while dust_fraction.ndim > 2:
                dust_fraction = dust_fraction.squeeze()
            
            # If still not 2D, take the first slice
            if dust_fraction.ndim > 2:
                dust_fraction = dust_fraction[0]
            elif dust_fraction.ndim < 2:
                raise ValueError(f"Dust fraction has unexpected shape: {dust_fraction.shape}")
            
            logger.info(f"Final dust fraction shape: {dust_fraction.shape}")
            logger.info(f"Dust fraction range: {dust_fraction.min():.4f} to {dust_fraction.max():.4f}")
            
            ds.close()
            result[0] = dust_fraction
            
        except Exception as e:
            logger.error(f"Error processing CAMS NetCDF: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            exception[0] = e
    
    # Run processing in a separate thread with timeout
    thread = threading.Thread(target=process_netcdf)
    thread.daemon = True
    thread.start()
    thread.join(timeout_seconds)
    
    if thread.is_alive():
        logger.error(f"CAMS NetCDF processing timed out after {timeout_seconds} seconds")
        return None
    
    if exception[0] is not None:
        raise exception[0]
    
    return result[0]


def create_synthetic_dust_fraction(target_params: dict, utc_date: datetime) -> np.ndarray:
    """Create synthetic dust fraction with realistic patterns"""
    res = float(target_params["project"]["target_resolution_deg"])
    minx, miny, maxx, maxy = (25.0, 35.5, 45.0, 42.5)
    width = int((maxx - minx) / res)
    height = int((maxy - miny) / res)

    # Use date-dependent seed for consistency
    rng = np.random.default_rng((abs(hash(utc_date.date())) + 1337) % (2**32))
    
    # Create realistic dust patterns
    # Higher dust activity in south and east (towards Syria/Iraq)
    lat_grid = np.linspace(maxy, miny, height)
    lon_grid = np.linspace(minx, maxx, width)
    
    lat_mesh, lon_mesh = np.meshgrid(lat_grid, lon_grid, indexing='ij')
    
    # Base dust fraction (higher in southeast)
    base_dust = 0.1 + 0.4 * (1 - (lat_mesh - miny) / (maxy - miny))  # Higher in south
    base_dust += 0.3 * ((lon_mesh - minx) / (maxx - minx))  # Higher in east
    
    # Add seasonal variation (higher in spring/summer)
    month = utc_date.month
    seasonal_factor = 0.8 + 0.4 * np.sin((month - 3) * np.pi / 6)  # Peak in June
    base_dust *= seasonal_factor
    
    # Add random variability
    noise = rng.beta(2.0, 5.0, size=(height, width)) * 0.3
    dust_fraction = np.clip(base_dust + noise, 0.0, 1.0)
    
    return dust_fraction


def is_date_available_for_cams(date: datetime) -> bool:
    """
    Check if date is likely available for CAMS data
    CAMS EAC4 reanalysis covers 2003-2021 only
    For recent dates, we use forecast data or synthetic data
    """
    from datetime import timezone
    
    # CAMS EAC4 reanalysis ended in 2021
    if date.year >= 2022:
        return False
    
    # For dates before 2022, check if old enough
    days_ago = (datetime.now(timezone.utc) - date).days
    # Conservative estimate: reanalysis data available after 60 days
    return days_ago >= 60


def ingest_cams_dust_day(utc_date: datetime, params: dict) -> Dict[str, str]:
    """
    Complete CAMS dust ingestion pipeline
    Downloads CAMS dust data and creates regridded dust fraction raster
    Returns dict with paths to analysis and forecast rasters
    """
    os.makedirs(params["paths"]["derived_dir"], exist_ok=True)
    
    cams_files = {}
    
    # Check if date is too recent for reanalysis data (EAC4 covers 2003-2021)
    if not is_date_available_for_cams(utc_date):
        from datetime import timezone
        # Make sure we handle timezone-aware dates correctly
        utc_now = datetime.now(timezone.utc)
        if utc_date.tzinfo is None:
            utc_date_aware = utc_date.replace(tzinfo=timezone.utc)
        else:
            utc_date_aware = utc_date
        days_ago = (utc_now - utc_date_aware).days
        
        if utc_date.year >= 2022:
            print(f"Date {utc_date.date()} is after 2021 - CAMS EAC4 reanalysis ended in 2021")
        else:
            print(f"Date {utc_date.date()} is too recent ({days_ago} days ago) for CAMS reanalysis data")
        
        # Try to download forecast data instead for recent dates
        if utc_date.year >= 2022:
            print("Attempting to use CAMS forecast data...")
            try:
                from .download_cams import CAMSDownloader
                api_key = params.get("apis", {}).get("cams", {}).get("key")
                output_dir = os.path.join(params["paths"]["raw_dir"], "cams")
                downloader = CAMSDownloader(api_key)
                
                # Try forecast data with 0-hour leadtime (nowcast)
                forecast_file = downloader.download_dust_forecast(
                    utc_date, [0, 24], output_dir
                )
                cams_files = {'forecast': forecast_file, 'analysis': forecast_file}
                print(f"Using forecast data as substitute")
            except Exception as e:
                print(f"CAMS forecast download also failed: {e}")
                print("Falling back to synthetic dust data...")
                # Use synthetic data instead of failing
                dust_fraction = create_synthetic_dust_fraction(params, utc_date)
                analysis_path = _save_dust_raster(dust_fraction, utc_date, "analysis", params)
                forecast_path = _save_dust_raster(dust_fraction, utc_date, "forecast", params)
                return {'analysis': analysis_path, 'forecast': forecast_path}
        else:
            print("Falling back to synthetic dust data...")
            # Use synthetic data instead of failing
            dust_fraction = create_synthetic_dust_fraction(params, utc_date)
            analysis_path = _save_dust_raster(dust_fraction, utc_date, "analysis", params)
            forecast_path = _save_dust_raster(dust_fraction, utc_date, "forecast", params)
            return {'analysis': analysis_path, 'forecast': forecast_path}
    else:
        # Try to download real CAMS reanalysis data (2003-2021)
        try:
            cams_files = download_cams_dust_day(utc_date, params)
            if not isinstance(cams_files, dict):
                cams_files = {}
            print(f"Downloaded CAMS files: {list(cams_files.keys())}")
        except Exception as e:
            print(f"CAMS download failed: {e}")
            print("Falling back to synthetic dust data...")
            # Use synthetic data instead of failing
            dust_fraction = create_synthetic_dust_fraction(params, utc_date)
            analysis_path = _save_dust_raster(dust_fraction, utc_date, "analysis", params)
            forecast_path = _save_dust_raster(dust_fraction, utc_date, "forecast", params)
            return {'analysis': analysis_path, 'forecast': forecast_path}
    
    results = {}
    
    # Process analysis file
    analysis_file = cams_files.get('analysis')
    if not analysis_file or not os.path.exists(analysis_file):
        print(f"CAMS analysis file not found for {utc_date.date()}")
        print("Falling back to synthetic dust data...")
        # Use synthetic data instead of failing
        dust_fraction = create_synthetic_dust_fraction(params, utc_date)
        analysis_path = _save_dust_raster(dust_fraction, utc_date, "analysis", params)
        forecast_path = _save_dust_raster(dust_fraction, utc_date, "forecast", params)
        return {'analysis': analysis_path, 'forecast': forecast_path}
    
    try:
        dust_fraction = process_cams_netcdf(analysis_file, params)
        if dust_fraction is None:
            logger.warning(f"Failed to process CAMS NetCDF file: {analysis_file}")
            logger.info("Falling back to synthetic dust data...")
            dust_fraction = create_synthetic_dust_fraction(params, utc_date)
            print("Using synthetic dust data (CAMS processing failed)")
        else:
            print("Processed real CAMS analysis data")
    except Exception as e:
        logger.error(f"CAMS analysis processing failed: {e}")
        logger.info("Falling back to synthetic dust data...")
        dust_fraction = create_synthetic_dust_fraction(params, utc_date)
        print("Using synthetic dust data (CAMS processing failed)")
    
    # Save analysis dust fraction
    analysis_path = _save_dust_raster(dust_fraction, utc_date, "analysis", params)
    results['analysis'] = analysis_path
    
    # Process forecast file (for 24h, 48h, 72h forecasts)
    forecast_file = cams_files.get('forecast')
    if not forecast_file or not os.path.exists(forecast_file):
        print(f"CAMS forecast file not found for {utc_date.date()}")
        print("Using analysis data as forecast...")
        forecast_file = analysis_file  # Use analysis file as fallback
    
    try:
        # Process forecast NetCDF - if it's the same as analysis, use analysis data
        if forecast_file == analysis_file:
            forecast_dust = dust_fraction.copy()
            print("Using analysis data as forecast (same file)")
        else:
            forecast_dust = process_cams_netcdf(forecast_file, params)
            if forecast_dust is None:
                logger.warning(f"Failed to process CAMS forecast NetCDF: {forecast_file}")
                logger.info("Using analysis data as forecast fallback...")
                forecast_dust = dust_fraction.copy()
                print("Using analysis data as forecast (forecast processing failed)")
            else:
                print("Processed real CAMS forecast data")
    except Exception as e:
        logger.error(f"CAMS forecast processing failed: {e}")
        logger.info("Using analysis data as forecast fallback...")
        forecast_dust = dust_fraction.copy()
        print("Using analysis data as forecast (forecast processing failed)")
    
    # Save forecast dust fraction
    forecast_path = _save_dust_raster(forecast_dust, utc_date, "forecast", params)
    results['forecast'] = forecast_path
    
    return results


def _save_dust_raster(dust_data: np.ndarray, date: datetime, data_type: str, params: dict) -> str:
    """Save dust fraction data to GeoTIFF"""
    res = float(params["project"]["target_resolution_deg"])
    minx, miny, maxx, maxy = (25.0, 35.5, 45.0, 42.5)
    transform = from_origin(minx, maxy, res, res)
    
    out_path = os.path.join(
        params["paths"]["derived_dir"],
        f"cams_dustfrac_{data_type}_{date.date().isoformat()}.tif",
    )
    
    # Ensure we have a 2D array
    while dust_data.ndim > 2:
        dust_data = dust_data.squeeze()
    
    if dust_data.ndim > 2:
        # If still > 2D after squeeze, take the first 2D slice
        dust_data = dust_data[0]
        print(f"Warning: Dust data had {dust_data.ndim} dimensions, taking first 2D slice")
    
    if dust_data.ndim != 2:
        raise ValueError(f"Cannot save dust raster: expected 2D array, got shape {dust_data.shape}")
    
    height, width = dust_data.shape
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
        dst.write(dust_data.astype(np.float32), 1)

    # Create COG if requested
    if params.get("runtime", {}).get("write_cog", False) and cog_translate is not None:
        cog_path = out_path.replace(".tif", ".cog.tif")
        config = dict(GDAL_TIFF_OVR_BLOCKSIZE="256")
        cog_profile = cog_profiles.get("deflate") if cog_profiles else None
        cog_translate(out_path, cog_path, cog_profile, config=config, in_memory=False)
        return cog_path

    return out_path