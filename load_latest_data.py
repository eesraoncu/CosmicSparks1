#!/usr/bin/env python3
"""
Load latest PM2.5 data to database
"""
import pandas as pd
from src.database import get_db, DailyStats

def load_latest_data():
    # Load the latest PM2.5 data
    df = pd.read_csv('data/derived/pm25_2024-01-03.csv')
    
    db = next(get_db())
    
    # Clear existing data for this date
    db.query(DailyStats).filter(DailyStats.date == '2024-01-03').delete()
    
    # Load new data
    for _, row in df.iterrows():
        stats = DailyStats(
            date=row['date'],
            province_id=row['province_id'],
            pm25=row['pm25'],
            dust_event_detected=row['dust_event_detected'],
            dust_intensity=row['dust_intensity'],
            aod_mean=row['aod_mean'],
            dust_aod_mean=row['dust_aod_mean'],
            air_quality_category=row['air_quality_category']
        )
        db.add(stats)
    
    db.commit()
    print(f'✅ Loaded {len(df)} records for 2024-01-03')
    
    # Verify
    count = db.query(DailyStats).filter(DailyStats.date == '2024-01-03').count()
    print(f'📊 Database now has {count} records for 2024-01-03')

if __name__ == "__main__":
    load_latest_data()
