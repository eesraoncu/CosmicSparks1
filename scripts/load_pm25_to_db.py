import os
import argparse
from typing import Optional, List, Dict, Any

import pandas as pd

# Ensure we can import src package when executed from repo root
import sys
repo_root = os.path.dirname(os.path.dirname(__file__))
if repo_root not in sys.path:
    sys.path.append(repo_root)

from src.database import db_manager


def find_pm25_file(derived_dir: str, date_str: Optional[str]) -> str:
    if date_str:
        path = os.path.join(derived_dir, f"pm25_{date_str}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"PM2.5 file not found for date {date_str}: {path}")
        return path
    # pick latest
    files = [f for f in os.listdir(derived_dir) if f.startswith("pm25_") and f.endswith(".csv")]
    if not files:
        raise FileNotFoundError("No pm25_YYYY-MM-DD.csv files found in derived directory")
    files.sort()
    return os.path.join(derived_dir, files[-1])


def rows_from_pm25_csv(path: str) -> List[Dict[str, Any]]:
    date_str = os.path.basename(path).replace("pm25_", "").replace(".csv", "")
    df = pd.read_csv(path)
    stats: List[Dict[str, Any]] = []

    def getf(row: pd.Series, key: str):
        val = row.get(key)
        return float(val) if pd.notna(val) else None

    for _, r in df.iterrows():
        stats.append({
            "date": date_str,
            "province_id": int(r["province_id"]),
            "aod_mean": getf(r, "aod_mean"),
            "aod_max": getf(r, "aod_max"),
            "aod_p95": getf(r, "aod_p95"),
            "dust_aod_mean": getf(r, "dust_aod_mean"),
            "dust_event_detected": bool(r.get("dust_event_detected", False)),
            "dust_intensity": str(r.get("dust_intensity", "None")),
            "pm25": getf(r, "pm25"),
            "pm25_lower": getf(r, "pm25_lower"),
            "pm25_upper": getf(r, "pm25_upper"),
            "air_quality_category": str(r.get("air_quality", "Unknown")),
            "rh_mean": getf(r, "rh_mean"),
            "blh_mean": getf(r, "blh_mean"),
            "data_quality_score": (float(r.get("coverage_pct", 85)) / 100.0) if pd.notna(r.get("coverage_pct")) else 0.85,
        })
    return stats


def main():
    parser = argparse.ArgumentParser(description="Load pm25_YYYY-MM-DD.csv into DB as DailyStats")
    parser.add_argument("--date", help="Date in YYYY-MM-DD. If omitted, uses the latest pm25_*.csv")
    parser.add_argument("--derived-dir", default=os.path.join("data", "derived"), help="Derived data directory")
    args = parser.parse_args()

    pm25_path = find_pm25_file(args.derived_dir, args.date)
    stats = rows_from_pm25_csv(pm25_path)

    with db_manager.get_session() as session:
        db_manager.store_daily_stats(session, stats)

    print(f"Loaded {len(stats)} records from {os.path.basename(pm25_path)} into database")


if __name__ == "__main__":
    main()


