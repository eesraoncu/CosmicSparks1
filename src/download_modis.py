"""
MODIS AOD downloader from NASA LAADS/LANCE NRT
Downloads and processes MODIS Terra/Aqua AOD products for dust monitoring
"""
import os
import requests
from datetime import datetime, timedelta
from typing import List, Optional
import tempfile
import shutil
from pathlib import Path


class MODISDownloader:
    """Download MODIS AOD data from NASA LAADS/LANCE"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://ladsweb.modaps.eosdis.nasa.gov/api/v2"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
    
    def get_available_files(self, product: str, date: datetime, bbox: tuple) -> List[dict]:
        """
        Get list of available files for given product and date
        bbox: (min_lon, min_lat, max_lon, max_lat)
        """
        # MODIS products: MOD04_L2 (Terra), MYD04_L2 (Aqua)
        url = f"{self.base_url}/content/archives/allData/61/{product}"
        
        # Date hierarchy: YYYY/DDD (day of year)
        year = date.year
        day_of_year = date.timetuple().tm_yday
        
        params = {
            "year": year,
            "dayOfYear": f"{day_of_year:03d}",
            "bbox": f"{bbox[1]},{bbox[0]},{bbox[3]},{bbox[2]}",  # N,W,S,E format
            "format": "json"
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json().get("content", [])
        except Exception as e:
            print(f"Error fetching file list: {e}")
            return []
    
    def download_file(self, file_info: dict, output_dir: str) -> Optional[str]:
        """Download a single MODIS file"""
        file_url = file_info["downloadsLink"]
        filename = file_info["name"]
        output_path = os.path.join(output_dir, filename)
        
        if os.path.exists(output_path):
            print(f"File already exists: {filename}")
            return output_path
            
        try:
            print(f"Downloading {filename}...")
            response = self.session.get(file_url, stream=True, timeout=300)
            response.raise_for_status()
            
            os.makedirs(output_dir, exist_ok=True)
            with open(output_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
            
            print(f"Downloaded: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error downloading {filename}: {e}")
            return None
    
    def download_day_bbox(self, date: datetime, bbox: tuple, output_dir: str, 
                         products: List[str] = None) -> List[str]:
        """
        Download all MODIS files for a day and bounding box
        Returns list of downloaded file paths
        """
        if products is None:
            products = ["MOD04_L2", "MYD04_L2"]  # Terra and Aqua AOD
            
        downloaded_files = []
        
        for product in products:
            files = self.get_available_files(product, date, bbox)
            print(f"Found {len(files)} {product} files for {date.date()}")
            
            for file_info in files:
                downloaded_path = self.download_file(file_info, output_dir)
                if downloaded_path:
                    downloaded_files.append(downloaded_path)
        
        return downloaded_files


def download_modis_aod_day(utc_date: datetime, params: dict) -> List[str]:
    """
    Download MODIS AOD for Turkey bbox on given date
    Returns list of downloaded HDF files
    """
    token = os.getenv("LAADS_TOKEN") or params.get("apis", {}).get("laads", {}).get("token")
    if not token or token == "${LAADS_TOKEN}":
        print("WARNING: No LAADS token found, skipping real download")
        return []
    
    # Turkey bounding box
    turkey_bbox = (25.0, 35.5, 45.0, 42.5)  # min_lon, min_lat, max_lon, max_lat
    
    output_dir = os.path.join(params["paths"]["raw_dir"], "modis", utc_date.strftime("%Y%m%d"))
    
    downloader = MODISDownloader(token)
    files = downloader.download_day_bbox(utc_date, turkey_bbox, output_dir)
    
    print(f"Downloaded {len(files)} MODIS files for {utc_date.date()}")
    return files


if __name__ == "__main__":
    # Test download
    import yaml
    from datetime import datetime
    
    config_path = "../config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    test_date = datetime(2025, 9, 20)
    files = download_modis_aod_day(test_date, params)
    print(f"Downloaded files: {files}")
