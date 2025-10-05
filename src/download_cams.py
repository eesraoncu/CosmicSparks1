"""
CAMS dust fraction and forecast downloader
Downloads ECMWF CAMS atmospheric composition data via CDS API
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List
import xarray as xr
import numpy as np


class CAMSDownloader:
    """Download CAMS atmospheric composition data"""
    
    def __init__(self, api_key: str = None):
        # Prefer ~/.cdsapirc credentials; don't require env/params
        self.api_key = api_key or os.getenv("CAMS_API_KEY")
        try:
            import cdsapi  # type: ignore
            # Use explicit parameters for better reliability
            if self.api_key:
                self.client = cdsapi.Client(
                    url="https://ads.atmosphere.copernicus.eu/api",
                    key=self.api_key,
                    retry_max=3, 
                    sleep_max=2, 
                    timeout=300
                )
            else:
                # Fallback to config file
                self.client = cdsapi.Client(url="https://ads.atmosphere.copernicus.eu/api")
        except Exception as e:
            print(f"Warning: CDS API setup failed: {e}")
            self.client = None
    
    def download_dust_forecast(self, date: datetime, forecast_hours: List[int], 
                              output_dir: str, bbox: tuple = None) -> str:
        """
        Download CAMS dust aerosol optical depth forecast
        bbox: (west, south, east, north) in degrees
        """
        if not self.client:
            raise Exception("CAMS API client not available. Please check your API key and configuration.")
        
        if bbox is None:
            bbox = (25.0, 35.5, 45.0, 42.5)  # Turkey bbox
        
        # CAMS dataset and variable names - use working combination
        dataset = "cams-global-atmospheric-composition-forecasts"
        variable = "dust_aerosol_optical_depth_550nm"  # This works!
        
        output_file = os.path.join(output_dir, f"cams_dust_forecast_{date.strftime('%Y%m%d')}.nc")
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # Use working parameters from our test - type parameter is required!
            request = {
                'variable': variable,
                'date': date.strftime('%Y-%m-%d'),
                'time': '00:00',
                'leadtime_hour': [f'{h}' for h in forecast_hours],
                'type': 'forecast',  # This is required!
                'area': [bbox[3], bbox[0], bbox[1], bbox[2]],  # N, W, S, E
                'format': 'netcdf',
            }
            
            print(f"Downloading CAMS dust forecast for {date.date()}...")
            self.client.retrieve(dataset, request, output_file)
            print(f"Downloaded: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"Error downloading CAMS forecast: {e}")
            raise Exception(f"CAMS forecast download failed: {e}")
    
    def download_dust_analysis(self, date: datetime, output_dir: str, bbox: tuple = None) -> str:
        """Download CAMS dust analysis (reanalysis) for given date"""
        if not self.client:
            raise Exception("CAMS API client not available. Please check your API key and configuration.")
        
        if bbox is None:
            bbox = (25.0, 35.5, 45.0, 42.5)
        
        output_file = os.path.join(output_dir, f"cams_dust_analysis_{date.strftime('%Y%m%d')}.nc")
        os.makedirs(output_dir, exist_ok=True)

        # Check if date is available for reanalysis
        from datetime import timezone
        days_ago = (datetime.now(timezone.utc) - date).days
        
        # CAMS reanalysis EAC4 ended in 2021, try forecast instead for recent dates
        if date.year >= 2022 or days_ago < 60:
            print(f"Date {date.date()} is too recent or after 2021 for CAMS reanalysis EAC4")
            print("CAMS EAC4 reanalysis dataset covers 2003-2021 only")
            print("Falling back to forecast data...")
            # Try to use forecast instead
            try:
                return self.download_dust_forecast(date, [0], output_dir, bbox)
            except Exception as e2:
                print(f"Forecast fallback also failed: {e2}")
                raise Exception(f"CAMS data not available for {date.date()}. EAC4 covers 2003-2021 only.")

        try:
            # Use working combination from our test for historical data (2003-2021)
            dataset = "cams-global-reanalysis-eac4"
            variable = "aerosol_optical_depth_550nm"
            
            request = {
                'variable': variable,
                'date': date.strftime('%Y-%m-%d'),
                'time': '00:00',
                'area': [bbox[3], bbox[0], bbox[1], bbox[2]],  # N, W, S, E
                'format': 'netcdf',
            }
            
            print(f"Downloading CAMS dust analysis for {date.date()}...")
            self.client.retrieve(dataset, request, output_file)
            print(f"Downloaded: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"Error downloading CAMS analysis: {e}")
            raise Exception(f"CAMS analysis download failed: {e}")
    


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
    
    config_path = "config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    test_date = datetime(2024, 12, 1)  # Use a date that has data
    files = download_cams_dust_day(test_date, params)
    print(f"Downloaded CAMS files: {files}")
