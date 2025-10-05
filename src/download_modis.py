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
from bs4 import BeautifulSoup

class MODISDownloader:
    """Download MODIS AOD data from NASA LAADS/LANCE"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://ladsweb.modaps.eosdis.nasa.gov/api/v2"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })

    def get_available_files(self, product: str, date: datetime, bbox: tuple) -> List[dict]:
        """
        Get list of available files by scraping the HTML archive page.
        """
        year = date.year
        day_of_year = date.timetuple().tm_yday
        collection = "61"

        # Use HTML scraping method that works
        url = f"{self.base_url}/content/archives/allData/{collection}/{product}/{year}/{day_of_year:03d}"

        print(f"Scraping file list from: {url}")

        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()

            # BeautifulSoup kullanarak HTML'i analiz et
            soup = BeautifulSoup(response.text, 'html.parser')

            files_found = []
            # Tüm 'a' (link) etiketlerini bul
            for link in soup.find_all('a'):
                filename = link.get_text()
                # Sadece HDF dosyalarını al
                if filename.endswith('.hdf'):
                    # Script'in geri kalanının beklediği formatta bir sözlük oluştur
                    file_info = {
                        "name": filename,
                        "downloadsLink": link.get('href')  # Linkin URL'ini al
                    }
                    files_found.append(file_info)

            return files_found

        except Exception as e:
            print(f"Error scraping file list: {e}")
            return []
    
    def download_file(self, file_info: dict, output_dir: str) -> Optional[str]:
        """Download a single MODIS file"""
        file_url = file_info["downloadsLink"]
        filename = file_info["name"]
        output_path = os.path.join(output_dir, filename)
        
        if os.path.exists(output_path):
            print(f"File already exists: {filename}")
            return output_path
            
        # Retry mechanism for network issues
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"Downloading {filename}... (attempt {attempt + 1}/{max_retries})")
                response = self.session.get(file_url, stream=True, timeout=60)
                response.raise_for_status()
                
                os.makedirs(output_dir, exist_ok=True)
                with open(output_path, 'wb') as f:
                    # Download in chunks to avoid timeout
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"✓ Downloaded: {output_path}")
                return output_path
                
            except Exception as e:
                print(f"✗ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in 5 seconds...")
                    import time
                    time.sleep(5)
                else:
                    print(f"✗ Failed to download {filename} after {max_retries} attempts")
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
            
            # Limit downloads to avoid timeout (take first 5 files)
            limited_files = files[:5]
            print(f"Limiting downloads to first {len(limited_files)} files to avoid timeout")
            
            for file_info in limited_files:
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

    # =================== GEÇİCİ KONTROL SATIRI ===================
    print(f"\n[DEBUG] Script'in kullandığı token: {token}\n")
    # ============================================================

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
    
    config_path = "config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    test_date = datetime(2024, 10, 1)
    files = download_modis_aod_day(test_date, params)
    print(f"Downloaded files: {files}")