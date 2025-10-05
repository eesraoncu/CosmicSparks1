"""
Real data setup script for dust monitoring system
Checks dependencies and provides setup instructions
"""
import subprocess
import sys
import os
from pathlib import Path

def check_dependency(package_name, import_name=None):
    """Check if a Python package is available"""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        return True
    except ImportError:
        return False

def install_package(package):
    """Install a package using pip"""
    print(f"Installing {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to install {package}")
        return False

def check_api_keys():
    """Check if API keys are configured"""
    keys = {
        'LAADS_TOKEN': 'eyJ0eXAiOiJKV1QiLCJvcmlnaW4iOiJFYXJ0aGRhdGEgTG9naW4iLCJzaWciOiJlZGxqd3RwdWJrZXlfb3BzIiwiYWxnIjoiUlMyNTYifQ.eyJ0eXBlIjoiVXNlciIsInVpZCI6ImVzcmFvbmN1MSIsImV4cCI6MTc2NDExNTE5OSwiaWF0IjoxNzU4ODkwNTA4LCJpc3MiOiJodHRwczovL3Vycy5lYXJ0aGRhdGEubmFzYS5nb3YiLCJpZGVudGl0eV9wcm92aWRlciI6ImVkbF9vcHMiLCJhY3IiOiJlZGwiLCJhc3N1cmFuY2VfbGV2ZWwiOjN9.3WLiqkdqkjrlmWJS2mBIof02BsZRQt3HEgsdTBCzHHoeaYaW5jGmZ40pl8C5exD52V2E2I2LxBbSgOU7I4jOAfwDkSmrFr8YbKVROm_20fiE7GaxxueV9KvP3fBtQeL_BO_dFkjrLIf18rC5Hm3YVsK5JFnDJzXFOAYlVG6vqcKzeeB9DUzYCZF8eO5rUavR8CDRFYyTCMRw-N5nlGzYvZQUIEEuLXdBX5-iyvu0WmaZ0-9UdpnOJefP-xmIbqmZTBl-CS4vFpeozUvulrR7Dqu9LJiy7SgTk33Xj0XpoaNL66O1QDbJW3RgtlX_dFNZFmvoGnYDKA1cBzbU09o1tQ',
        'CAMS_API_KEY': 'c46f9bcc-6720-4d14-aea5-0eebd4b700a9',
        'CDS_API_KEY': 'c46f9bcc-6720-4d14-aea5-0eebd4b700a9'
    }
    
    missing_keys = []
    for key, description in keys.items():
        if not os.getenv(key):
            missing_keys.append((key, description))
    
    return missing_keys

def setup_real_data():
    """Main setup function"""
    print("🛰️ Dust Monitoring System - Real Data Setup")
    print("=" * 50)
    
    # 1. Check core dependencies
    print("\n1. Checking core Python dependencies...")
    core_deps = [
        ('numpy', 'numpy'),
        ('pandas', 'pandas'), 
        ('requests', 'requests'),
        ('pyyaml', 'yaml'),
        ('matplotlib', 'matplotlib')
    ]
    
    core_ok = True
    for pkg, imp in core_deps:
        if check_dependency(pkg, imp):
            print(f"   ✓ {pkg}")
        else:
            print(f"   ✗ {pkg} - installing...")
            if install_package(pkg):
                print(f"   ✓ {pkg} installed")
            else:
                core_ok = False
    
    # 2. Check geospatial dependencies (more complex)
    print("\n2. Checking geospatial dependencies...")
    geo_deps = [
        ('xarray', 'xarray'),
        ('netcdf4', 'netCDF4'),
        ('rasterio', 'rasterio'),
        ('geopandas', 'geopandas'),
        ('shapely', 'shapely')
    ]
    
    geo_missing = []
    for pkg, imp in geo_deps:
        if check_dependency(pkg, imp):
            print(f"   ✓ {pkg}")
        else:
            print(f"   ~ {pkg} - needs installation")
            geo_missing.append(pkg)
    
    # 3. Check specialized dependencies
    print("\n3. Checking specialized dependencies...")
    special_deps = [
        ('cdsapi', 'cdsapi'),
        ('pyhdf', 'pyhdf'),
    ]
    
    special_missing = []
    for pkg, imp in special_deps:
        if check_dependency(pkg, imp):
            print(f"   ✓ {pkg}")
        else:
            print(f"   ~ {pkg} - optional but recommended")
            special_missing.append(pkg)
    
    # 4. Check API keys
    print("\n4. Checking API keys...")
    missing_keys = check_api_keys()
    
    if not missing_keys:
        print("   ✓ All API keys configured")
    else:
        print("   ⚠️  Missing API keys:")
        for key, desc in missing_keys:
            print(f"     - {key}: {desc}")
    
    # 5. Test basic pipeline
    print("\n5. Testing basic pipeline...")
    try:
        # Test import of our modules
        sys.path.append('src')
        from model_pm25 import load_regression_parameters
        from alert_system import PersonalizedAlertSystem
        
        # Test config loading
        import yaml
        with open('config/params.yaml') as f:
            params = yaml.safe_load(f)
        
        print("   ✓ Core modules importable")
        print("   ✓ Configuration loadable")
        
        # Test directories
        for dir_name in ['data', 'data/raw', 'data/derived']:
            os.makedirs(dir_name, exist_ok=True)
        print("   ✓ Data directories created")
        
    except Exception as e:
        print(f"   ✗ Pipeline test failed: {e}")
    
    # 6. Summary and next steps
    print("\n" + "=" * 50)
    print("📋 SETUP SUMMARY")
    print("=" * 50)
    
    if core_ok:
        print("✅ Core dependencies: Ready")
    else:
        print("❌ Core dependencies: Issues found")
    
    if not geo_missing:
        print("✅ Geospatial processing: Ready")
    else:
        print(f"⚠️  Geospatial processing: Missing {', '.join(geo_missing)}")
    
    if not special_missing:
        print("✅ Data access: Ready")
    else:
        print(f"⚠️  Data access: Missing {', '.join(special_missing)}")
    
    if not missing_keys:
        print("✅ API credentials: Configured")
    else:
        print(f"❌ API credentials: {len(missing_keys)} missing")
    
    # Recommendations
    print("\n🚀 NEXT STEPS FOR REAL DATA:")
    print("-" * 30)
    
    if geo_missing:
        print("1. Install geospatial dependencies:")
        print("   conda install -c conda-forge geopandas rasterio xarray netcdf4")
        print("   # OR for pip users:")
        print("   pip install geopandas rasterio xarray netcdf4")
    
    if special_missing:
        print("2. Install data access tools:")
        print("   pip install cdsapi")
        print("   # Note: pyhdf may need system libraries")
    
    if missing_keys:
        print("3. Configure API keys:")
        for key, desc in missing_keys:
            print(f"   export {key}='your_key_here'  # {desc}")
    
    print("\n4. Test with real data:")
    print("   python -m src.orchestrate_day --date 2025-09-26")
    
    print("\n5. If APIs not available, system works with synthetic data!")
    print("   python test_pipeline.py  # Test synthetic mode")
    
    # Current capability assessment
    can_run_basic = core_ok
    can_run_full = core_ok and not geo_missing and not missing_keys
    
    print(f"\n📊 CURRENT CAPABILITY:")
    print(f"   Basic pipeline (synthetic): {'✅' if can_run_basic else '❌'}")
    print(f"   Full pipeline (real data): {'✅' if can_run_full else '⚠️'}")
    
    return can_run_full

if __name__ == "__main__":
    ready = setup_real_data()
    
    if ready:
        print("\n🎉 System ready for real data processing!")
    else:
        print("\n⚠️  Setup incomplete - see recommendations above")
        print("💡 You can still test with synthetic data using: python test_pipeline.py")
