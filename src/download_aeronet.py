"""
AERONET station data downloader for validation
Downloads AOD measurements from AERONET ground stations in Turkey region
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import io


class AeronetDownloader:
    """Download AERONET ground station data"""
    
    def __init__(self):
        self.base_url = "https://aeronet.gsfc.nasa.gov/cgi-bin/print_web_data_v3"
        self.session = requests.Session()
    
    def get_turkey_stations(self) -> List[Dict[str, str]]:
        """Get list of AERONET stations in Turkey and nearby regions"""
        # Key stations in/around Turkey
        stations = [
            {"name": "IMS-METU-ERDEMLI", "country": "Turkey"},
            {"name": "Finokalia-FKL", "country": "Greece"},  # Crete, close to Turkey
            {"name": "ATHENS-NOA", "country": "Greece"},
            {"name": "Nicosia", "country": "Cyprus"},
            {"name": "Limassol", "country": "Cyprus"},
            {"name": "SEDE_BOKER", "country": "Israel"},
            {"name": "Mezaira", "country": "United_Arab_Emirates"},
            {"name": "Cairo_EMA_2", "country": "Egypt"},
        ]
        return stations
    
    def download_station_data(self, station_name: str, start_date: datetime, 
                            end_date: datetime, data_type: str = "AOD15") -> Optional[pd.DataFrame]:
        """
        Download data for a specific station and date range
        data_type: 'AOD15' (Level 1.5) or 'AOD20' (Level 2.0)
        """
        params = {
            'site': station_name,
            'year': start_date.year,
            'month': start_date.month,
            'day': start_date.day,
            'year2': end_date.year,
            'month2': end_date.month,
            'day2': end_date.day,
            'product': data_type,
            'AVG': '10',  # Daily averages
            'if_no_html': '1'
        }
        
        try:
            print(f"Downloading {station_name} data from {start_date.date()} to {end_date.date()}")
            
            response = self.session.get(self.base_url, params=params, timeout=60)
            response.raise_for_status()
            
            # Parse CSV data
            if len(response.text.strip()) == 0:
                print(f"No data available for {station_name}")
                return None
            
            # AERONET data has header lines starting with specific comments
            lines = response.text.split('\n')
            data_start = 0
            for i, line in enumerate(lines):
                if line.startswith('Date(dd:mm:yyyy)') or line.startswith('Date'):
                    data_start = i
                    break
            
            if data_start == 0:
                print(f"Could not parse header for {station_name}")
                return None
            
            # Read data into DataFrame
            data_text = '\n'.join(lines[data_start:])
            df = pd.read_csv(io.StringIO(data_text), parse_dates=['Date(dd:mm:yyyy)'])
            
            if len(df) == 0:
                print(f"No data records for {station_name}")
                return None
            
            # Clean and standardize columns
            df = df.rename(columns={
                'Date(dd:mm:yyyy)': 'date',
                'AOD_500nm': 'aod_500',
                'AOD_675nm': 'aod_675', 
                '440-675_Angstrom_Exponent': 'angstrom'
            })
            
            # Add station metadata
            df['station'] = station_name
            df['data_type'] = data_type
            
            print(f"Downloaded {len(df)} records for {station_name}")
            return df
            
        except Exception as e:
            print(f"Error downloading {station_name}: {e}")
            return None
    
    def download_regional_data(self, start_date: datetime, end_date: datetime, 
                              output_dir: str, data_type: str = "AOD15") -> List[str]:
        """
        Download data from all Turkey region stations
        Returns list of output CSV file paths
        """
        stations = self.get_turkey_stations()
        output_files = []
        
        os.makedirs(output_dir, exist_ok=True)
        
        for station_info in stations:
            station_name = station_info["name"]
            
            df = self.download_station_data(station_name, start_date, end_date, data_type)
            
            if df is not None:
                # Save to CSV
                output_file = os.path.join(
                    output_dir, 
                    f"{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{station_name}.lev15.csv"
                )
                df.to_csv(output_file, index=False)
                output_files.append(output_file)
                print(f"Saved: {output_file}")
        
        return output_files


def download_aeronet_validation_data(start_date: datetime, end_date: datetime, 
                                   params: dict) -> List[str]:
    """
    Download AERONET data for validation period
    Returns list of CSV file paths
    """
    output_dir = os.path.join(params["paths"]["raw_dir"], "aeronet")
    
    downloader = AeronetDownloader()
    files = downloader.download_regional_data(start_date, end_date, output_dir)
    
    print(f"Downloaded AERONET data from {len(files)} stations")
    return files


if __name__ == "__main__":
    # Test download
    import yaml
    
    config_path = "../config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    # Download last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    files = download_aeronet_validation_data(start_date, end_date, params)
    print(f"Downloaded AERONET files: {files}")
