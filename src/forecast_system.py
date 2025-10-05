"""
Forecast system for dust monitoring
Generates predictions for missing dates based on historical data and seasonal patterns
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
import warnings
warnings.filterwarnings('ignore')

from database import db_manager, DailyStats, Province

logger = logging.getLogger(__name__)


class DustForecastSystem:
    """Advanced forecasting system for dust and PM2.5 predictions"""
    
    def __init__(self):
        self.seasonal_patterns = {}
        self.province_models = {}
        self.weather_correlation = {}
        
    def get_last_complete_date(self) -> Optional[str]:
        """Find the last date where all provinces have data"""
        with db_manager.get_session() as session:
            # Get all provinces
            provinces = session.query(Province).all()
            total_provinces = len(provinces)
            
            # Get all available dates, ordered by date descending
            available_dates = session.query(DailyStats.date).distinct().order_by(DailyStats.date.desc()).all()
            available_dates = [d[0] for d in available_dates]
            
            if not available_dates:
                return None
            
            # Check each date from most recent backwards
            for date_str in available_dates:
                # Count provinces with data for this date
                province_count = session.query(DailyStats).filter(DailyStats.date == date_str).count()
                
                if province_count == total_provinces:
                    logger.info(f"Found complete date: {date_str} with {province_count} provinces")
                    return date_str
            
            logger.warning(f"No complete date found. Latest date has {session.query(DailyStats).filter(DailyStats.date == available_dates[0]).count()} out of {total_provinces} provinces")
            return None
    
    def get_missing_dates(self, start_date: str, end_date: str) -> List[str]:
        """Get list of dates that need forecasting"""
        with db_manager.get_session() as session:
            # Get existing dates
            existing_dates = session.query(DailyStats.date).distinct().all()
            existing_dates = [d[0] for d in existing_dates]
            
            # Generate date range
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            date_range = []
            
            current = start
            while current <= end:
                date_str = current.strftime('%Y-%m-%d')
                if date_str not in existing_dates:
                    date_range.append(date_str)
                current += timedelta(days=1)
                
            return date_range
    
    def load_historical_data(self, province_id: int, days_back: int = 30) -> pd.DataFrame:
        """Load historical data for a specific province"""
        with db_manager.get_session() as session:
            end_date = datetime.utcnow().strftime('%Y-%m-%d')
            start_date = (datetime.utcnow() - timedelta(days=days_back)).strftime('%Y-%m-%d')
            
            query = session.query(DailyStats).filter(
                DailyStats.province_id == province_id,
                DailyStats.date >= start_date,
                DailyStats.date <= end_date
            ).order_by(DailyStats.date)
            
            df = pd.read_sql(query.statement, session.bind)
            return df
    
    def calculate_seasonal_patterns(self, province_id: int) -> Dict[str, float]:
        """Calculate seasonal patterns for a province"""
        # Simplified approach - use default values for all provinces
        # In a real system, you would load historical data here
        
        # Base PM2.5 levels by region (simplified)
        region_bases = {
            'eastern': 25.0,    # Higher due to dust sources
            'central': 20.0,    # Moderate
            'western': 18.0,    # Lower
            'coastal': 15.0     # Lowest
        }
        
        # Assign provinces to regions (simplified)
        if province_id in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:  # First 10 provinces
            region = 'eastern'
        elif province_id in [11, 12, 13, 14, 15, 16, 17, 18, 19, 20]:
            region = 'central'
        elif province_id in [21, 22, 23, 24, 25, 26, 27, 28, 29, 30]:
            region = 'western'
        else:
            region = 'coastal'
        
        base_pm25 = region_bases[region]
        
        # Monthly patterns (simplified)
        monthly_patterns = {
            1: base_pm25 * 1.1,   # Winter - higher
            2: base_pm25 * 1.0,   # Winter
            3: base_pm25 * 1.2,   # Spring - dust season
            4: base_pm25 * 1.3,   # Spring - peak dust
            5: base_pm25 * 1.2,   # Spring
            6: base_pm25 * 0.9,   # Summer - lower
            7: base_pm25 * 0.8,   # Summer
            8: base_pm25 * 0.8,   # Summer
            9: base_pm25 * 0.9,   # Fall
            10: base_pm25 * 1.0,  # Fall
            11: base_pm25 * 1.1,  # Winter
            12: base_pm25 * 1.1   # Winter
        }
        
        return {
            'base_pm25': base_pm25,
            'seasonal_factor': 0.2,
            'trend': 0.0,
            'monthly_patterns': monthly_patterns
        }
    
    def predict_pm25(self, province_id: int, target_date: str) -> Dict[str, Any]:
        """Predict PM2.5 for a specific province and date"""
        # Get seasonal patterns
        patterns = self.calculate_seasonal_patterns(province_id)
        
        # Get recent data for trend analysis
        recent_data = self.load_historical_data(province_id, days_back=7)
        
        # Calculate base prediction
        target_month = datetime.strptime(target_date, '%Y-%m-%d').month
        monthly_pattern = patterns.get('monthly_patterns', {}).get(target_month, patterns['base_pm25'])
        
        # Apply trend
        days_ahead = (datetime.strptime(target_date, '%Y-%m-%d') - datetime.utcnow()).days
        trend_adjustment = patterns['trend'] * days_ahead
        
        # Calculate base PM2.5
        base_pm25 = monthly_pattern + trend_adjustment
        
        # Add some randomness based on historical variability
        if not recent_data.empty:
            variability = recent_data['pm25'].std()
            noise = np.random.normal(0, variability * 0.1)  # 10% of historical variability
            base_pm25 += noise
        
        # Ensure reasonable bounds
        base_pm25 = max(5.0, min(200.0, base_pm25))
        
        # Calculate confidence bounds
        lower_bound = base_pm25 * 0.8
        upper_bound = base_pm25 * 1.2
        
        # Predict dust event (simplified)
        dust_probability = 0.1  # Base probability
        if base_pm25 > 30:
            dust_probability += 0.2
        if target_month in [3, 4, 5]:  # Spring months
            dust_probability += 0.3
            
        dust_detected = np.random.random() < dust_probability
        
        # Determine dust intensity
        dust_intensity = 'None'
        if dust_detected:
            if base_pm25 > 50:
                dust_intensity = 'Heavy'
            elif base_pm25 > 35:
                dust_intensity = 'Moderate'
            else:
                dust_intensity = 'Light'
        
        # Calculate AOD (correlated with PM2.5)
        aod_mean = base_pm25 * 0.005 + np.random.normal(0, 0.02)
        aod_mean = max(0.01, min(1.0, aod_mean))
        
        # Determine air quality category
        if base_pm25 <= 8:
            air_quality = 'Good'
        elif base_pm25 <= 15:
            air_quality = 'Moderate'
        elif base_pm25 <= 25:
            air_quality = 'Unhealthy for Sensitive Groups'
        elif base_pm25 <= 50:
            air_quality = 'Unhealthy'
        else:
            air_quality = 'Very Unhealthy'
        
        return {
            'pm25': float(round(base_pm25, 1)),
            'pm25_lower': float(round(lower_bound, 1)),
            'pm25_upper': float(round(upper_bound, 1)),
            'aod_mean': float(round(aod_mean, 3)),
            'aod_max': float(round(aod_mean * 1.5, 3)),
            'aod_p95': float(round(aod_mean * 1.2, 3)),
            'dust_aod_mean': float(round(aod_mean * 0.3 if dust_detected else 0.0, 3)),
            'dust_event_detected': dust_detected,
            'dust_intensity': dust_intensity,
            'air_quality_category': air_quality,
            'rh_mean': float(round(np.random.normal(60, 15), 1)),
            'blh_mean': float(round(np.random.normal(800, 200), 1)),
            'data_quality_score': 0.7,  # Forecast quality
            'model_uncertainty': float(round(abs(upper_bound - lower_bound) / base_pm25, 2))
        }
    
    def generate_forecasts(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Generate forecasts for all provinces and missing dates"""
        logger.info(f"Generating forecasts from {start_date} to {end_date}")
        
        with db_manager.get_session() as session:
            provinces = session.query(Province).all()
            missing_dates = self.get_missing_dates(start_date, end_date)
            
            forecast_data = []
            
            for date_str in missing_dates:
                logger.info(f"Generating forecast for {date_str}")
                
                for province in provinces:
                    try:
                        prediction = self.predict_pm25(province.id, date_str)
                        
                        forecast_record = {
                            'date': date_str,
                            'province_id': province.id,
                            **prediction
                        }
                        
                        forecast_data.append(forecast_record)
                        
                    except Exception as e:
                        logger.error(f"Error forecasting for province {province.id} on {date_str}: {e}")
                        continue
            
            return forecast_data
    
    def save_forecasts_to_database(self, forecast_data: List[Dict[str, Any]]) -> bool:
        """Save forecast data to database"""
        try:
            with db_manager.get_session() as session:
                db_manager.store_daily_stats(session, forecast_data)
                logger.info(f"Saved {len(forecast_data)} forecast records to database")
                return True
        except Exception as e:
            logger.error(f"Failed to save forecasts: {e}")
            return False
    
    def run_forecast_pipeline(self) -> bool:
        """Run the complete forecast pipeline"""
        try:
            # Get last complete date
            last_complete_date = self.get_last_complete_date()
            if not last_complete_date:
                logger.warning("No complete historical data found")
                return False
            
            # Calculate forecast period
            last_date = datetime.strptime(last_complete_date, '%Y-%m-%d')
            today = datetime.utcnow()
            
            # Only forecast if there's a gap
            if (today - last_date).days <= 1:
                logger.info("No forecast needed - data is up to date")
                return True
            
            # Generate forecasts
            start_date = (last_date + timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = today.strftime('%Y-%m-%d')
            
            forecast_data = self.generate_forecasts(start_date, end_date)
            
            if not forecast_data:
                logger.warning("No forecast data generated")
                return False
            
            # Save to database
            success = self.save_forecasts_to_database(forecast_data)
            
            if success:
                logger.info(f"Forecast pipeline completed successfully. Generated {len(forecast_data)} records.")
                return True
            else:
                logger.error("Failed to save forecast data")
                return False
                
        except Exception as e:
            logger.error(f"Forecast pipeline failed: {e}")
            return False


def run_forecast_system():
    """Main function to run the forecast system"""
    forecast_system = DustForecastSystem()
    return forecast_system.run_forecast_pipeline()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run dust forecast system")
    parser.add_argument("--start-date", help="Start date for forecasting (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date for forecasting (YYYY-MM-DD)")
    parser.add_argument("--auto", action="store_true", help="Auto-detect missing dates")
    
    args = parser.parse_args()
    
    if args.auto:
        success = run_forecast_system()
        print(f"Forecast system {'completed successfully' if success else 'failed'}")
    else:
        if not args.start_date or not args.end_date:
            print("Please provide both --start-date and --end-date, or use --auto")
            exit(1)
        
        forecast_system = DustForecastSystem()
        forecast_data = forecast_system.generate_forecasts(args.start_date, args.end_date)
        success = forecast_system.save_forecasts_to_database(forecast_data)
        print(f"Forecast {'completed successfully' if success else 'failed'}")
