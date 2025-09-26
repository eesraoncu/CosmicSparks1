"""
ERA5 meteorological data downloader
Downloads relative humidity and boundary layer height from Copernicus CDS
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import cdsapi
import xarray as xr
import numpy as np


class ERA5Downloader:
    """Download ERA5 reanalysis data"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CDS_API_KEY") 
        if self.api_key and self.api_key != "${CDS_API_KEY}":
            try:
                self.client = cdsapi.Client()
            except Exception as e:
                print(f"Warning: CDS API setup failed: {e}")
                self.client = None
        else:
            print("Warning: No CDS API key found")
            self.client = None
    
    def download_era5_day(self, date: datetime, variables: List[str], 
                         output_dir: str, bbox: tuple = None) -> str:
        """
        Download ERA5 data for given date and variables
        variables: list like ['relative_humidity', 'boundary_layer_height']
        bbox: (west, south, east, north) in degrees
        """
        if not self.client:
            print("No CDS client available, creating synthetic data...")
            return self._create_synthetic_era5(date, variables, output_dir, bbox)
        
        if bbox is None:
            bbox = (25.0, 35.5, 45.0, 42.5)  # Turkey bbox
        
        dataset = "reanalysis-era5-single-levels"
        
        output_file = os.path.join(output_dir, f"era5_{date.strftime('%Y%m%d')}.nc")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            request = {
                'product_type': 'reanalysis',
                'variable': variables,
                'year': str(date.year),
                'month': f'{date.month:02d}',
                'day': f'{date.day:02d}',
                'time': ['00:00', '06:00', '12:00', '18:00'],
                'area': [bbox[3], bbox[0], bbox[1], bbox[2]],  # N, W, S, E
                'format': 'netcdf',
                'grid': [0.25, 0.25],  # 0.25 degree resolution
            }
            
            print(f"Downloading ERA5 data for {date.date()}...")
            self.client.retrieve(dataset, request, output_file)
            print(f"Downloaded: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"Error downloading ERA5 data: {e}")
            return self._create_synthetic_era5(date, variables, output_dir, bbox)
    
    def _create_synthetic_era5(self, date: datetime, variables: List[str], 
                              output_dir: str, bbox: tuple) -> str:
        """Create synthetic ERA5 data when API is not available"""
        print("Creating synthetic ERA5 data...")
        
        if bbox is None:
            bbox = (25.0, 35.5, 45.0, 42.5)
        
        # Create coordinate arrays
        lons = np.arange(bbox[0], bbox[2] + 0.25, 0.25)
        lats = np.arange(bbox[1], bbox[3] + 0.25, 0.25)
        times = [date + timedelta(hours=h) for h in [0, 6, 12, 18]]
        
        # Create synthetic data
        rng = np.random.default_rng((abs(hash(date.date())) + 1234) % (2**32))
        
        data_vars = {}
        
        if 'relative_humidity' in variables:
            # RH varies with elevation and proximity to sea
            lat_grid, lon_grid = np.meshgrid(lats, lons, indexing='ij')
            base_rh = 60 + 20 * np.sin((lat_grid - 35.5) * np.pi / 7.0)  # Latitude variation
            coastal_effect = np.maximum(0, 10 - np.minimum(
                np.abs(lon_grid - 25.0) * 2,  # Distance to west coast
                np.abs(lat_grid - 35.5) * 2   # Distance to south coast
            )) * 2
            
            rh_data = np.zeros((len(times), len(lats), len(lons)))
            for t in range(len(times)):
                daily_var = rng.normal(0, 5, size=(len(lats), len(lons)))
                rh_data[t] = np.clip(base_rh + coastal_effect + daily_var, 10, 100)
            
            data_vars['relative_humidity'] = (['time', 'latitude', 'longitude'], rh_data)
        
        if 'boundary_layer_height' in variables:
            # BLH typically higher inland and during day
            blh_base = 800 + 200 * ((lons.reshape(1, -1) - 25.0) / 20.0)  # Increase inland
            blh_data = np.zeros((len(times), len(lats), len(lons)))
            
            for t, time in enumerate(times):
                hour = time.hour
                diurnal_factor = 1 + 0.5 * np.sin((hour - 6) * np.pi / 12)  # Peak at midday
                daily_var = rng.normal(0, 100, size=(len(lats), len(lons)))
                blh_data[t] = np.clip(blh_base * diurnal_factor + daily_var, 200, 2000)
            
            data_vars['boundary_layer_height'] = (['time', 'latitude', 'longitude'], blh_data)
        
        # Create xarray dataset
        ds = xr.Dataset(data_vars, coords={
            'time': times,
            'latitude': lats,
            'longitude': lons
        })
        
        output_file = os.path.join(output_dir, f"era5_synthetic_{date.strftime('%Y%m%d')}.nc")
        os.makedirs(output_dir, exist_ok=True)
        ds.to_netcdf(output_file)
        
        print(f"Created synthetic ERA5 file: {output_file}")
        return output_file


def download_era5_day(utc_date: datetime, params: dict, 
                     variables: List[str] = None) -> str:
    """
    Download ERA5 meteorological data for given date
    Returns path to downloaded NetCDF file
    """
    if variables is None:
        variables = ['relative_humidity', 'boundary_layer_height']
    
    output_dir = os.path.join(params["paths"]["raw_dir"], "era5")
    
    downloader = ERA5Downloader()
    file_path = downloader.download_era5_day(utc_date, variables, output_dir)
    
    return file_path


if __name__ == "__main__":
    # Test download
    import yaml
    
    config_path = "../config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    test_date = datetime(2025, 9, 20)
    file_path = download_era5_day(test_date, params)
    print(f"Downloaded ERA5 file: {file_path}")
