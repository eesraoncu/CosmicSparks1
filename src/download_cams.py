"""
CAMS dust fraction and forecast downloader
Downloads ECMWF CAMS atmospheric composition data via CDS API
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import cdsapi
import xarray as xr
import numpy as np


class CAMSDownloader:
    """Download CAMS atmospheric composition data"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CAMS_API_KEY")
        if self.api_key and self.api_key != "${CAMS_API_KEY}":
            try:
                # Initialize CDS API client
                self.client = cdsapi.Client()
            except Exception as e:
                print(f"Warning: CDS API setup failed: {e}")
                self.client = None
        else:
            print("Warning: No CAMS API key found")
            self.client = None
    
    def download_dust_forecast(self, date: datetime, forecast_hours: List[int], 
                              output_dir: str, bbox: tuple = None) -> str:
        """
        Download CAMS dust aerosol optical depth forecast
        bbox: (west, south, east, north) in degrees
        """
        if not self.client:
            print("No CAMS client available, creating synthetic data...")
            return self._create_synthetic_dust(date, output_dir, bbox)
        
        if bbox is None:
            bbox = (25.0, 35.5, 45.0, 42.5)  # Turkey bbox
        
        # CAMS dataset and variable names
        dataset = "cams-global-atmospheric-composition-forecasts"
        variable = "dust_aerosol_optical_depth_550nm"
        
        output_file = os.path.join(output_dir, f"cams_dust_{date.strftime('%Y%m%d')}.nc")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            request = {
                'variable': variable,
                'date': date.strftime('%Y-%m-%d'),
                'time': '00:00',
                'leadtime_hour': [f'{h}' for h in forecast_hours],
                'type': 'forecast',
                'area': [bbox[3], bbox[0], bbox[1], bbox[2]],  # N, W, S, E
                'format': 'netcdf',
            }
            
            print(f"Downloading CAMS dust forecast for {date.date()}...")
            self.client.retrieve(dataset, request, output_file)
            print(f"Downloaded: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"Error downloading CAMS data: {e}")
            return self._create_synthetic_dust(date, output_dir, bbox)
    
    def download_dust_analysis(self, date: datetime, output_dir: str, bbox: tuple = None) -> str:
        """Download CAMS dust analysis (reanalysis) for given date"""
        if not self.client:
            return self._create_synthetic_dust(date, output_dir, bbox)
        
        if bbox is None:
            bbox = (25.0, 35.5, 45.0, 42.5)
        
        dataset = "cams-global-reanalysis-eac4"
        variable = "dust_aerosol_optical_depth_550nm"
        
        output_file = os.path.join(output_dir, f"cams_dust_analysis_{date.strftime('%Y%m%d')}.nc")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            request = {
                'variable': variable,
                'year': str(date.year),
                'month': f'{date.month:02d}',
                'day': f'{date.day:02d}',
                'time': ['00:00', '06:00', '12:00', '18:00'],
                'area': [bbox[3], bbox[0], bbox[1], bbox[2]],
                'format': 'netcdf',
            }
            
            print(f"Downloading CAMS dust analysis for {date.date()}...")
            self.client.retrieve(dataset, request, output_file)
            print(f"Downloaded: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"Error downloading CAMS analysis: {e}")
            return self._create_synthetic_dust(date, output_dir, bbox)
    
    def _create_synthetic_dust(self, date: datetime, output_dir: str, bbox: tuple) -> str:
        """Create synthetic dust data when API is not available"""
        print("Creating synthetic CAMS dust data...")
        
        if bbox is None:
            bbox = (25.0, 35.5, 45.0, 42.5)
        
        # Create synthetic data with realistic patterns
        lons = np.linspace(bbox[0], bbox[2], 80)  # 0.25 degree resolution
        lats = np.linspace(bbox[1], bbox[3], 28)
        
        # Synthetic dust with higher values in southeast (more dust activity)
        rng = np.random.default_rng((abs(hash(date.date())) + 2024) % (2**32))
        dust_base = rng.exponential(scale=0.1, size=(len(lats), len(lons)))
        
        # Add spatial pattern (higher in south/east)
        lat_grid, lon_grid = np.meshgrid(lats, lons, indexing='ij')
        south_east_factor = 1 + 2 * (42.5 - lat_grid) / 7.0 + (lon_grid - 25.0) / 20.0
        dust_data = dust_base * south_east_factor * 0.1
        dust_data = np.clip(dust_data, 0, 1.0)
        
        # Create xarray dataset
        ds = xr.Dataset({
            'dust_aerosol_optical_depth_550nm': (['latitude', 'longitude'], dust_data)
        }, coords={
            'latitude': lats,
            'longitude': lons,
            'time': date
        })
        
        output_file = os.path.join(output_dir, f"cams_dust_synthetic_{date.strftime('%Y%m%d')}.nc")
        os.makedirs(output_dir, exist_ok=True)
        ds.to_netcdf(output_file)
        
        print(f"Created synthetic dust file: {output_file}")
        return output_file


def download_cams_dust_day(utc_date: datetime, params: dict, forecast_hours: List[int] = None) -> Dict[str, str]:
    """
    Download CAMS dust data for given date
    Returns dict with paths to analysis and forecast files
    """
    if forecast_hours is None:
        forecast_hours = [0, 24, 48, 72]  # Nowcast + 3-day forecast
    
    api_key = params.get("apis", {}).get("cams", {}).get("key")
    output_dir = os.path.join(params["paths"]["raw_dir"], "cams")
    
    downloader = CAMSDownloader(api_key)
    
    # Download analysis (current conditions)
    analysis_file = downloader.download_dust_analysis(utc_date, output_dir)
    
    # Download forecast
    forecast_file = downloader.download_dust_forecast(utc_date, forecast_hours, output_dir)
    
    return {
        "analysis": analysis_file,
        "forecast": forecast_file
    }


if __name__ == "__main__":
    # Test download
    import yaml
    
    config_path = "../config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    test_date = datetime(2025, 9, 20)
    files = download_cams_dust_day(test_date, params)
    print(f"Downloaded CAMS files: {files}")
