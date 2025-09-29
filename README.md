# Dust Nowcast & Alerts MVP (NASA Space Apps)

## Overview
This repository contains the **Yazılım A** (Data Ingest/QC) and **Yazılım B** (Modeling/Validation) complete pipeline for dust monitoring over Türkiye. The system provides:

- **Real-time dust monitoring** using NASA MODIS AOD and ECMWF CAMS data
- **Province-level PM2.5 estimates** with uncertainty quantification
- **Personalized health alerts** based on user sensitivity and location
- **AERONET validation** for quality assurance
- **Comprehensive data pipeline** from satellite to user notifications

## Quick Start

### 1. Environment Setup
```bash
# Create Python 3.10+ environment
python -m venv dust-env
# Windows: dust-env\Scripts\activate
# Linux/Mac: source dust-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Test Pipeline (No Dependencies)
```bash
# Test core functionality without external libraries
python test_pipeline.py
```

### 3. Configuration
- Edit `config/params.yaml` for paths and model parameters
- Set API keys as environment variables:
  ```bash
  export LAADS_TOKEN="your_nasa_token"
  export CAMS_API_KEY="your_copernicus_key"
  ```

### 4. Run Pipeline
```bash
# Single day processing
python -m src.orchestrate_day --date 2025-09-20

# Multi-day processing (last N days)
python -m src.orchestrate_range --days 3

# Validation analysis
python -m src.validation_aeronet
```

## System Architecture

### Data Ingestion (Yazılım A)
- **MODIS AOD**: Downloads Terra/Aqua aerosol optical depth with QC filtering
- **CAMS Dust**: ECMWF dust fraction and forecast data
- **ERA5 Meteorology**: Relative humidity and boundary layer height
- **AERONET Ground Truth**: Validation data from ground stations

### Processing Pipeline
1. **Spatial Alignment**: Reprojects all data to 0.05° Turkey grid
2. **Quality Control**: Filters clouds, invalid pixels, applies QC flags
3. **Dust Detection**: Identifies dust events using AOD×dust_fraction
4. **Zonal Statistics**: Computes province-level aggregated metrics
5. **PM2.5 Modeling**: Enhanced regression with meteorological factors
6. **Alert Generation**: Personalized health risk assessment

### Modeling (Yazılım B)
- **Enhanced PM2.5 Model**: `PM2.5 = a0 + a1×AOD + a2×RH + a3×BLH + a4×DustAOD + a5×DustAOD×RH + a6×DustAOD×BLH`
- **Uncertainty Quantification**: Coverage and variability-based confidence intervals
- **Health Risk Classification**: WHO/EU air quality standards adaptation
- **Dust Episode Detection**: Intensity-based classification system

## Repository Structure

```
dust-mvp/
├── config/
│   └── params.yaml              # Configuration and model parameters
├── data/                        # Data directories (auto-created)
│   ├── raw/                     # Downloaded satellite/model data
│   ├── derived/                 # Processed products and statistics
│   └── admin/                   # Administrative boundaries
├── src/                         # Source code modules
│   ├── download_*.py            # Data downloaders (MODIS, CAMS, ERA5, AERONET)
│   ├── ingest_*.py             # Data processing and QC
│   ├── zonal_stats*.py         # Spatial statistics computation
│   ├── model_pm25.py           # PM2.5 estimation model
│   ├── alert_system.py         # Personalized alert generation
│   ├── validation_aeronet.py   # AERONET validation system
│   ├── orchestrate_*.py        # Pipeline orchestration
│   └── create_turkey_provinces.py # Administrative boundary setup
├── docs/                       # Documentation and notes
├── requirements.txt            # Python dependencies
├── test_pipeline.py           # Core functionality test
└── README.md                  # This file
```

## Key Features

### 🛰️ Multi-Source Data Integration
- **NASA MODIS**: Terra/Aqua AOD with advanced QC filtering
- **ECMWF CAMS**: Dust fraction, analysis, and 72-hour forecasts
- **ERA5 Reanalysis**: Meteorological variables for PM2.5 modeling
- **AERONET**: Ground-based validation network

### 🏥 Health-Focused Design
- **Sensitivity Groups**: General, sensitive, respiratory, cardiac populations
- **Personalized Thresholds**: Customizable PM2.5 alert levels
- **Health Messaging**: Condition-specific advice and recommendations
- **Rate Limiting**: Prevents alert fatigue with intelligent queuing

### 📊 Quality Assurance
- **AERONET Validation**: Bias, RMSE, correlation analysis
- **Uncertainty Quantification**: Coverage and variability metrics
- **Data Quality Monitoring**: Pixel coverage and QC statistics
- **Comprehensive Logging**: Full processing provenance

### ⚡ Production Ready
- **Fallback Systems**: Synthetic data when APIs unavailable
- **Error Handling**: Graceful degradation and recovery
- **Configurable Parameters**: Easy tuning without code changes
- **COG Output**: Cloud-optimized GeoTIFFs for web visualization

## Output Products

### Daily Province Statistics
- AOD statistics (mean, max, p95)
- Dust AOD and intensity classification  
- PM2.5 estimates with uncertainty bounds
- Air quality categories and health risk levels
- Data coverage and quality metrics

### Alert System
- Personalized risk assessments
- Email-ready notification queue
- User preference management
- Alert history and rate limiting

### Validation Reports
- AERONET comparison statistics
- Validation plots and time series
- Quality assessment metrics
- Matched observation pairs

## Development Status

✅ **Completed (Days 1-5)**
- Multi-source data downloaders with API integration
- Complete processing pipeline with QC and spatial alignment
- Enhanced PM2.5 model with meteorological factors
- Personalized alert system with health group classification
- Comprehensive error handling and fallback systems

✅ **Validation & Performance (Days 6-8)**  
- AERONET validation framework with statistical analysis
- Quality control improvements and gap filling
- Performance optimization and caching systems
- Model parameter tuning and validation
- Data quality monitoring dashboard

## ✅ TAMAMLANAN SİSTEM BİLEŞENLERİ

### **Backend API (Yazılım C)** - ✅ TAMAMLANDI
- ✅ REST API endpoints (`src/api.py`)
- ✅ User management ve preferences
- ✅ Email service integration (`src/email_service.py`)
- ✅ PostgreSQL database schema (`src/database.py`)
- ✅ Health check ve monitoring endpoints

### **Frontend (Yazılım D)** - ✅ TAMAMLANDI
- ✅ Interactive web map (`frontend/components/DustMap.tsx`)
- ✅ Province selection ve time series
- ✅ User registration ve alert preferences
- ✅ Modern React/Next.js interface
- ✅ Responsive design ve TailwindCSS

### **Automated Operations** - ✅ TAMAMLANDI
- ✅ Automated daily scheduling (`src/scheduler.py`)
- ✅ Docker containerization
- ✅ Email alert delivery system
- ✅ Database management ve cleanup

### **Production Ready Deployment** - ✅ TAMAMLANDI
- ✅ Docker Compose setup (`docker-compose.yml`)
- ✅ Nginx reverse proxy
- ✅ PostgreSQL + PostGIS database
- ✅ Redis caching
- ✅ Health checks ve monitoring

## Dependencies

**Core Processing**: numpy, pandas, xarray, rasterio, geopandas  
**Data Access**: requests, cdsapi, pyhdf  
**Modeling**: scikit-learn  
**Visualization**: matplotlib, seaborn  
**Utilities**: pyyaml, rich, typer

See `requirements.txt` for complete dependency list.

## License & Credits

This project was developed for the NASA Space Apps Challenge 2024, focusing on dust monitoring and health protection in Türkiye. The system integrates multiple NASA and ECMWF data products to provide actionable health information to vulnerable populations.


