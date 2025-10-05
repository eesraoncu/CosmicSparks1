import os
from datetime import datetime
from dateutil import tz
import yaml
from rich import print

from .ingest_modis import ingest_modis_aod_day
from .ingest_cams import ingest_cams_dust_day
from .zonal_stats import compute_province_stats
from .model_pm25 import estimate_pm25_for_day
from .ingest_era5 import ingest_era5_day
from .zonal_stats_meteo import compute_meteo_stats
from .create_turkey_provinces import ensure_turkey_provinces_exist
from .alert_system import generate_alerts_for_day
from .database import db_manager


def save_pipeline_data_to_database(utc_date: datetime, pm25_csv_path: str, params: dict):
    """Save pipeline data to database with proper data_quality_score"""
    import pandas as pd
    
    # Load PM2.5 data
    df = pd.read_csv(pm25_csv_path)
    
    # Prepare data for database
    stats_data = []
    for _, row in df.iterrows():
        stat_record = {
            'date': utc_date.date().isoformat(),
            'province_id': int(row['province_id']),
            'pm25': float(row.get('pm25', 0)) if pd.notna(row.get('pm25')) else None,
            'pm25_lower': float(row.get('pm25_lower', 0)) if pd.notna(row.get('pm25_lower')) else None,
            'pm25_upper': float(row.get('pm25_upper', 0)) if pd.notna(row.get('pm25_upper')) else None,
            'air_quality_category': str(row.get('air_quality_category', 'Unknown')),
            'rh_mean': float(row.get('rh_mean', 0)) if pd.notna(row.get('rh_mean')) else None,
            'blh_mean': float(row.get('blh_mean', 0)) if pd.notna(row.get('blh_mean')) else None,
            'data_quality_score': 1.0  # Real data from pipeline
        }
        stats_data.append(stat_record)
    
    # Store in database
    with db_manager.get_session() as session:
        db_manager.store_daily_stats(session, stats_data)
    
    print(f"Saved {len(stats_data)} province records to database")


def load_params() -> dict:
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "params.yaml")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def orchestrate(date_str: str) -> None:
    params = load_params()
    utc_date = datetime.fromisoformat(date_str).replace(tzinfo=tz.UTC)
    print(f"[bold cyan]Running day pipeline for {utc_date.date()} (UTC)\n[/bold cyan]")

    # Ensure Turkey provinces shapefile exists
    print("[bold green]Step 1: Ensuring Turkey provinces shapefile[/bold green]")
    provinces_shp = ensure_turkey_provinces_exist(params)
    print(f"Using provinces shapefile: {provinces_shp}")

    # Ingest satellite and model data
    print("[bold green]Step 2: Ingesting MODIS AOD data[/bold green]")
    modis_cog = ingest_modis_aod_day(utc_date, params)
    print(f"MODIS AOD: {modis_cog}")

    print("[bold green]Step 3: Ingesting CAMS dust data[/bold green]")
    cams_results = ingest_cams_dust_day(utc_date, params)
    cams_analysis = cams_results.get('analysis', cams_results)  # Backward compatibility
    print(f"CAMS dust: {cams_analysis}")

    print("[bold green]Step 4: Ingesting ERA5 meteorological data[/bold green]")
    era5 = ingest_era5_day(utc_date, params)
    print(f"ERA5 data: RH={era5['rh']}, BLH={era5['blh']}")

    # Compute zonal statistics
    print("[bold green]Step 5: Computing province-level AOD and dust statistics[/bold green]")
    stats_table = compute_province_stats(utc_date, modis_cog, cams_analysis, params)
    print(f"Wrote province stats: {stats_table}")

    print("[bold green]Step 6: Computing province-level meteorological statistics[/bold green]")
    meteo_table = compute_meteo_stats(utc_date, era5["rh"], era5["blh"], params)
    print(f"Wrote meteo stats: {meteo_table}")

    # Model PM2.5
    print("[bold green]Step 7: Estimating PM2.5 concentrations[/bold green]")
    pm25_table = estimate_pm25_for_day(utc_date, stats_table, params, meteo_table)
    print(f"Wrote PM2.5 estimates: {pm25_table}")

    # Generate personalized alerts
    print("[bold green]Step 8: Generating personalized dust alerts[/bold green]")
    alert_queue = generate_alerts_for_day(utc_date, pm25_table, params)
    print(f"Alert queue: {alert_queue}")

    # Save to database
    print("[bold green]Step 9: Saving data to database[/bold green]")
    save_pipeline_data_to_database(utc_date, pm25_table, params)
    print("Data saved to database successfully")

    print(f"[bold cyan]Pipeline completed successfully for {utc_date.date()}[/bold cyan]")
    print("[dim]Pipeline outputs:[/dim]")
    print(f"[dim]  - MODIS AOD: {modis_cog}[/dim]")
    print(f"[dim]  - CAMS dust: {cams_analysis}[/dim]")
    print(f"[dim]  - Province stats: {stats_table}[/dim]") 
    print(f"[dim]  - PM2.5 estimates: {pm25_table}[/dim]")
    print(f"[dim]  - Alert queue: {alert_queue}[/dim]")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run one-day dust pipeline")
    parser.add_argument("--date", required=True, help="ISO date, e.g., 2025-09-20 (UTC)")
    args = parser.parse_args()

    orchestrate(args.date)


