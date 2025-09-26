"""
Create Turkey provinces shapefile for zonal statistics
Downloads admin boundaries or creates simplified version
"""
import os
import geopandas as gpd
import pandas as pd
import requests
from shapely.geometry import Polygon, box
import zipfile
import tempfile


def download_turkey_admin_data(output_dir: str) -> str:
    """
    Download Turkey administrative boundaries
    Returns path to created shapefile
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Try to download from Natural Earth (simplified admin boundaries)
    ne_url = "https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_admin_1_states_provinces.zip"
    
    try:
        print("Downloading Turkey admin boundaries...")
        response = requests.get(ne_url, timeout=60)
        response.raise_for_status()
        
        # Extract to temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "admin_boundaries.zip")
            with open(zip_path, 'wb') as f:
                f.write(response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Read the shapefile
            shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
            if not shp_files:
                raise Exception("No shapefile found in downloaded data")
            
            gdf = gpd.read_file(os.path.join(temp_dir, shp_files[0]))
            
            # Filter for Turkey provinces
            turkey_gdf = gdf[gdf['admin'] == 'Turkey'].copy()
            
            if len(turkey_gdf) == 0:
                raise Exception("No Turkey provinces found in data")
            
            # Clean up columns
            turkey_gdf = turkey_gdf[['name', 'name_en', 'type_en', 'geometry']].copy()
            turkey_gdf = turkey_gdf.rename(columns={
                'name': 'name_tr',
                'name_en': 'name',
                'type_en': 'type'
            })
            
            # Add province ID
            turkey_gdf['id'] = range(1, len(turkey_gdf) + 1)
            
            # Save to output directory
            output_path = os.path.join(output_dir, "turkiye_provinces.shp")
            turkey_gdf.to_file(output_path)
            
            print(f"Downloaded {len(turkey_gdf)} Turkey provinces")
            return output_path
            
    except Exception as e:
        print(f"Download failed: {e}")
        print("Creating simplified Turkey provinces...")
        return create_simplified_turkey_provinces(output_dir)


def create_simplified_turkey_provinces(output_dir: str) -> str:
    """
    Create simplified Turkey provinces shapefile
    Uses approximate boundaries for major provinces
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Simplified province data (approximate centroids and rough boundaries)
    provinces_data = [
        {"name": "Istanbul", "name_tr": "İstanbul", "lat": 41.0, "lon": 29.0, "region": "Marmara"},
        {"name": "Ankara", "name_tr": "Ankara", "lat": 39.9, "lon": 32.8, "region": "Central"},
        {"name": "Izmir", "name_tr": "İzmir", "lat": 38.4, "lon": 27.1, "region": "Aegean"},
        {"name": "Bursa", "name_tr": "Bursa", "lat": 40.2, "lon": 29.1, "region": "Marmara"},
        {"name": "Antalya", "name_tr": "Antalya", "lat": 36.9, "lon": 30.7, "region": "Mediterranean"},
        {"name": "Adana", "name_tr": "Adana", "lat": 37.0, "lon": 35.3, "region": "Mediterranean"},
        {"name": "Konya", "name_tr": "Konya", "lat": 37.9, "lon": 32.5, "region": "Central"},
        {"name": "Sanliurfa", "name_tr": "Şanlıurfa", "lat": 37.2, "lon": 38.8, "region": "Southeast"},
        {"name": "Gaziantep", "name_tr": "Gaziantep", "lat": 37.1, "lon": 37.4, "region": "Southeast"},
        {"name": "Kayseri", "name_tr": "Kayseri", "lat": 38.7, "lon": 35.5, "region": "Central"},
        {"name": "Mersin", "name_tr": "Mersin", "lat": 36.8, "lon": 34.6, "region": "Mediterranean"},
        {"name": "Eskisehir", "name_tr": "Eskişehir", "lat": 39.8, "lon": 30.5, "region": "Central"},
        {"name": "Diyarbakir", "name_tr": "Diyarbakır", "lat": 37.9, "lon": 40.2, "region": "Southeast"},
        {"name": "Samsun", "name_tr": "Samsun", "lat": 41.3, "lon": 36.3, "region": "Black Sea"},
        {"name": "Denizli", "name_tr": "Denizli", "lat": 37.8, "lon": 29.1, "region": "Aegean"},
        {"name": "Malatya", "name_tr": "Malatya", "lat": 38.4, "lon": 38.3, "region": "Eastern"},
        {"name": "Trabzon", "name_tr": "Trabzon", "lat": 41.0, "lon": 39.7, "region": "Black Sea"},
        {"name": "Van", "name_tr": "Van", "lat": 38.5, "lon": 43.4, "region": "Eastern"},
        {"name": "Erzurum", "name_tr": "Erzurum", "lat": 39.9, "lon": 41.3, "region": "Eastern"},
        {"name": "Kars", "name_tr": "Kars", "lat": 40.6, "lon": 43.1, "region": "Eastern"},
    ]
    
    # Create voronoi-like polygons around province centers
    geometries = []
    
    for i, prov in enumerate(provinces_data):
        # Simple rectangular approximation around each province center
        size = 0.8  # degrees
        west = prov["lon"] - size
        east = prov["lon"] + size
        south = prov["lat"] - size
        north = prov["lat"] + size
        
        # Constrain to Turkey bounds
        west = max(west, 25.0)
        east = min(east, 45.0)
        south = max(south, 35.5)
        north = min(north, 42.5)
        
        polygon = box(west, south, east, north)
        geometries.append(polygon)
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(
        provinces_data,
        geometry=geometries,
        crs="EPSG:4326"
    )
    
    # Add ID column
    gdf['id'] = range(1, len(gdf) + 1)
    
    # Save to shapefile
    output_path = os.path.join(output_dir, "turkiye_provinces.shp")
    gdf.to_file(output_path)
    
    print(f"Created simplified Turkey provinces shapefile with {len(gdf)} provinces")
    return output_path


def ensure_turkey_provinces_exist(params: dict) -> str:
    """
    Ensure Turkey provinces shapefile exists
    Downloads or creates if missing
    """
    admin_dir = params["paths"]["admin_dir"]
    provinces_shp = params["paths"]["provinces_shp"]
    
    if os.path.exists(provinces_shp):
        print(f"Turkey provinces shapefile already exists: {provinces_shp}")
        return provinces_shp
    
    print("Turkey provinces shapefile not found, creating...")
    
    try:
        # Try to download first
        return download_turkey_admin_data(admin_dir)
    except Exception as e:
        print(f"Download failed: {e}")
        # Fall back to simplified version
        return create_simplified_turkey_provinces(admin_dir)


if __name__ == "__main__":
    # Test creation
    import yaml
    
    config_path = "../config/params.yaml"
    with open(config_path) as f:
        params = yaml.safe_load(f)
    
    shapefile_path = ensure_turkey_provinces_exist(params)
    print(f"Turkey provinces shapefile: {shapefile_path}")
    
    # Test reading
    gdf = gpd.read_file(shapefile_path)
    print(f"Loaded {len(gdf)} provinces")
    print(gdf.head())
