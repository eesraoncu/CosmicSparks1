import os
from datetime import datetime
import pandas as pd
import numpy as np
from typing import Dict, Optional


def load_regression_parameters(params: dict) -> Dict[str, float]:
    """Load and validate PM2.5 regression parameters"""
    model_params = params.get("model", {}).get("pm25_regression", {})
    
    # Default parameters based on literature (Gupta et al., 2006; van Donkelaar et al., 2010)
    default_params = {
        "a0": 8.0,      # Intercept (background PM2.5)
        "a1": 25.0,     # AOD coefficient
        "a2": 0.08,     # RH coefficient (positive, hygroscopic growth)
        "a3": -0.012,   # BLH coefficient (negative, dilution effect)
        "a4": 15.0,     # Dust AOD coefficient (higher for dust)
        "a5": 0.1,      # Dust-RH interaction
        "a6": -0.005,   # Dust-BLH interaction
    }
    
    # Update with user parameters
    for key, default_val in default_params.items():
        default_params[key] = float(model_params.get(key, default_val))
    
    return default_params


def enhanced_pm25_model(df: pd.DataFrame, params: Dict[str, float]) -> pd.Series:
    """
    Enhanced PM2.5 estimation model
    PM2.5 = a0 + a1*AOD + a2*RH + a3*BLH + a4*DustAOD + a5*DustAOD*RH + a6*DustAOD*BLH
    """
    # Extract variables
    aod = df["aod_mean"].fillna(0.0)
    rh = df["RH"]
    blh = df["BLH"]
    dust_aod = df.get("dust_aod_mean", aod * 0.3)  # Fallback if dust AOD not available
    
    # Base model
    pm25 = (params["a0"] + 
            params["a1"] * aod + 
            params["a2"] * rh + 
            params["a3"] * blh)
    
    # Dust-specific terms
    pm25 += (params["a4"] * dust_aod + 
             params["a5"] * dust_aod * rh + 
             params["a6"] * dust_aod * blh)
    
    # Apply constraints
    pm25 = pm25.clip(lower=0.0, upper=300.0)  # Reasonable PM2.5 range
    
    return pm25


def calculate_uncertainty_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate uncertainty metrics for PM2.5 estimates"""
    # Uncertainty based on data coverage and variability
    coverage = df.get("coverage_pct", 100.0) / 100.0
    
    # Lower coverage = higher uncertainty
    coverage_uncertainty = (1 - coverage) * 10
    
    # Variability uncertainty (difference between mean and p95)
    if "aod_p95" in df.columns and "aod_mean" in df.columns:
        aod_variability = (df["aod_p95"] - df["aod_mean"]).fillna(0)
        variability_uncertainty = aod_variability * 20  # Scale factor
    else:
        variability_uncertainty = 5.0  # Default uncertainty
    
    # Total uncertainty (combine quadratically)
    total_uncertainty = np.sqrt(coverage_uncertainty**2 + variability_uncertainty**2)
    
    # Confidence levels
    df["pm25_uncertainty"] = total_uncertainty.clip(lower=2.0, upper=50.0)
    df["pm25_lower"] = df["pm25"] - df["pm25_uncertainty"]
    df["pm25_upper"] = df["pm25"] + df["pm25_uncertainty"]
    df["pm25_confidence"] = np.where(
        df["pm25_uncertainty"] < 10, "high",
        np.where(df["pm25_uncertainty"] < 20, "medium", "low")
    )
    
    return df


def classify_air_quality(pm25_values: pd.Series) -> pd.Series:
    """Classify air quality based on PM2.5 concentrations (WHO/EU standards)"""
    return pd.cut(
        pm25_values,
        bins=[0, 15, 25, 35, 55, 75, float('inf')],
        labels=["Good", "Moderate", "Unhealthy for Sensitive", "Unhealthy", "Very Unhealthy", "Hazardous"],
        include_lowest=True
    )


def detect_dust_episodes(df: pd.DataFrame) -> pd.DataFrame:
    """Detect and classify dust episodes"""
    # Dust episode criteria
    dust_criteria = {
        "dust_event_detected": df.get("dust_event_moderate", False),
        "dust_intensity": pd.cut(
            df.get("dust_aod_mean", 0),
            bins=[0, 0.1, 0.2, 0.3, 0.5, float('inf')],
            labels=["None", "Light", "Moderate", "Heavy", "Extreme"],
            include_lowest=True
        ),
        "dust_pm25_contribution": df.get("dust_aod_mean", 0) * 40,  # Estimate dust PM2.5 contribution
    }
    
    for key, values in dust_criteria.items():
        df[key] = values
    
    return df


def estimate_pm25_for_day(utc_date: datetime, stats_csv_path: str, params: dict, 
                         meteo_csv_path: Optional[str] = None) -> str:
    """
    Enhanced PM2.5 estimation with uncertainty quantification and dust episode detection
    """
    # Load data
    df = pd.read_csv(stats_csv_path)
    
    # Merge meteorological data
    if meteo_csv_path and os.path.exists(meteo_csv_path):
        met = pd.read_csv(meteo_csv_path)
        df = df.merge(met[["province_id", "rh_mean", "blh_mean"]], on="province_id", how="left")
        df["RH"] = df["rh_mean"].fillna(55.0)  # Typical Turkey RH
        df["BLH"] = df["blh_mean"].fillna(900.0)  # Typical Turkey BLH
        print(f"Merged meteorological data for {len(met)} provinces")
    else:
        # Use climatological defaults for Turkey
        df["RH"] = 55.0
        df["BLH"] = 900.0
        print("Using climatological meteorology (no ERA5 data)")
    
    # Load model parameters
    model_params = load_regression_parameters(params)
    
    # Estimate PM2.5
    print("Applying enhanced PM2.5 model...")
    df["pm25"] = enhanced_pm25_model(df, model_params)
    
    # Calculate uncertainty metrics
    df = calculate_uncertainty_metrics(df)
    
    # Classify air quality
    df["air_quality_category"] = classify_air_quality(df["pm25"])
    
    # Detect dust episodes
    df = detect_dust_episodes(df)
    
    # Add model metadata
    df["model_version"] = "enhanced_v1.0"
    df["model_timestamp"] = datetime.utcnow().isoformat()
    
    # Health risk indicators
    df["health_risk_level"] = pd.cut(
        df["pm25"],
        bins=[0, 25, 50, 75, 100, float('inf')],
        labels=["Low", "Moderate", "High", "Very High", "Extreme"],
        include_lowest=True
    )
    
    # Summary statistics
    print(f"PM2.5 estimates computed for {len(df)} provinces:")
    print(f"  Mean PM2.5: {df['pm25'].mean():.1f} ± {df['pm25_uncertainty'].mean():.1f} μg/m³")
    print(f"  Range: {df['pm25'].min():.1f} - {df['pm25'].max():.1f} μg/m³")
    
    unhealthy_provinces = df[df['pm25'] > 35]['province_name'].tolist()
    if unhealthy_provinces:
        print(f"  Unhealthy levels (>35 μg/m³): {', '.join(unhealthy_provinces[:5])}")
    
    dust_provinces = df[df['dust_event_detected']]['province_name'].tolist()
    if dust_provinces:
        print(f"  Dust episodes detected: {', '.join(dust_provinces[:5])}")
    
    # Save results
    out_csv = os.path.join(
        params["paths"]["derived_dir"],
        f"pm25_{utc_date.date().isoformat()}.csv",
    )
    df.to_csv(out_csv, index=False)
    
    return out_csv


