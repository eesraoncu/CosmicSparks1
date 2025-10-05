"""
Intelligent Pipeline Orchestrator
Automatically finds the latest available data for each province and runs pipeline
If recent data is missing, generates forecasts going back up to 3 months
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd

from .database import db_manager, Province, DailyStats
from .forecast_system import DustForecastSystem
from .orchestrate_day import orchestrate as orchestrate_day, load_params

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IntelligentPipelineOrchestrator:
    """
    Intelligent orchestrator that finds latest data for each province
    and fills gaps with forecasts when needed
    """
    
    def __init__(self, max_lookback_days: int = 90, min_data_age_days: int = 7):
        """
        Args:
            max_lookback_days: Maximum days to look back for data (default 90 = 3 months)
            min_data_age_days: Minimum data age to consider "recent" (default 7 days)
        """
        self.max_lookback_days = max_lookback_days
        self.min_data_age_days = min_data_age_days
        self.forecast_system = DustForecastSystem()
        self.params = load_params()
        
    def get_latest_real_data_per_province(self, session: Session) -> Dict[int, Optional[str]]:
        """
        Find the latest date with real data for each province
        Returns dict: {province_id: latest_date_str or None}
        """
        logger.info("Finding latest real data for each province...")
        
        # Get all provinces
        provinces = session.query(Province).all()
        
        # Calculate lookback date
        lookback_date = (datetime.now() - timedelta(days=self.max_lookback_days)).strftime('%Y-%m-%d')
        
        latest_data = {}
        
        for province in provinces:
            # Find latest real data (excluding forecasts with data_quality_score = 0.7)
            # Real data has score 1.0 or None, forecast data has score 0.7
            latest = session.query(DailyStats).filter(
                DailyStats.province_id == province.id,
                DailyStats.date >= lookback_date,
                DailyStats.data_quality_score != 0.7  # Exclude forecast data
            ).order_by(DailyStats.date.desc()).first()
            
            if latest:
                latest_data[province.id] = latest.date
                logger.info(f"Province {province.name} ({province.id}): Latest data on {latest.date}")
            else:
                latest_data[province.id] = None
                logger.warning(f"Province {province.name} ({province.id}): No real data in last {self.max_lookback_days} days")
        
        return latest_data
    
    def get_missing_dates_per_province(self, session: Session) -> Dict[int, List[str]]:
        """
        Identify missing dates for each province up to today
        Returns dict: {province_id: [missing_date_strs]}
        """
        logger.info("Identifying missing dates per province...")
        
        latest_data = self.get_latest_real_data_per_province(session)
        today = datetime.now().strftime('%Y-%m-%d')
        
        missing_dates = {}
        
        for province_id, latest_date in latest_data.items():
            if latest_date is None:
                # No data at all - need to generate from 3 months ago
                start_date = (datetime.now() - timedelta(days=self.max_lookback_days)).strftime('%Y-%m-%d')
                date_list = pd.date_range(start=start_date, end=today, freq='D')
                missing_dates[province_id] = [d.strftime('%Y-%m-%d') for d in date_list]
            else:
                # Check if data is recent enough
                latest_dt = datetime.strptime(latest_date, '%Y-%m-%d')
                days_old = (datetime.now() - latest_dt).days
                
                if days_old > self.min_data_age_days:
                    # Generate dates from day after latest to today
                    start_date = (latest_dt + timedelta(days=1)).strftime('%Y-%m-%d')
                    date_list = pd.date_range(start=start_date, end=today, freq='D')
                    missing_dates[province_id] = [d.strftime('%Y-%m-%d') for d in date_list]
                else:
                    missing_dates[province_id] = []
        
        return missing_dates
    
    def get_missing_dates_for_province_after_date(self, session: Session, province_id: int, last_date: str) -> List[str]:
        """
        Bir il için belirli tarihten sonraki eksik tarihleri bul
        Sadece gerçek veri (data_quality_score != 0.7) olan tarihleri atla
        """
        from datetime import datetime, timedelta
        
        last_date_obj = datetime.strptime(last_date, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Son tarihten bugüne kadar olan eksik günleri bul
        missing_dates = []
        current_date = last_date_obj + timedelta(days=1)
        
        while current_date < today:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Bu tarihte GERÇEK veri var mı kontrol et (forecast değil)
            existing = session.query(DailyStats).filter(
                DailyStats.province_id == province_id,
                DailyStats.date == date_str,
                DailyStats.data_quality_score != 0.7  # Forecast verisini sayma
            ).first()
            
            if not existing:
                missing_dates.append(date_str)
            
            current_date += timedelta(days=1)
        
        return missing_dates
    
    def get_missing_dates_for_province_no_data(self, session: Session, province_id: int) -> List[str]:
        """
        Hiç veri olmayan il için son 90 günün eksik tarihlerini bul
        Sadece gerçek veri (data_quality_score != 0.7) olan tarihleri atla
        """
        from datetime import datetime, timedelta
        
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_date = today - timedelta(days=self.max_lookback_days)
        
        missing_dates = []
        current_date = start_date
        
        while current_date < today:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Bu tarihte GERÇEK veri var mı kontrol et (forecast değil)
            existing = session.query(DailyStats).filter(
                DailyStats.province_id == province_id,
                DailyStats.date == date_str,
                DailyStats.data_quality_score != 0.7  # Forecast verisini say
            ).first()
            
            if not existing:
                missing_dates.append(date_str)
            
            current_date += timedelta(days=1)
        
        return missing_dates
    
    def try_run_real_pipeline_for_province(self, date_str: str, province_id: int) -> bool:
        """
        Belirli bir il için belirli bir tarihte gerçek veri indirmeye çalış
        """
        try:
            # Skip if date is too recent for real data
            if self.is_date_too_recent(date_str):
                logger.debug(f"Skipping {date_str} for province {province_id} - too recent for real data")
                return False
            
            logger.debug(f"Attempting to download real data for province {province_id} on {date_str}...")
            
            # Try to download real data first
            try:
                from .download_modis import download_modis_aod_day
                from .download_cams import download_cams_dust_day
                from .download_era5 import download_era5_day
                
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Try to download MODIS data
                try:
                    modis_files = download_modis_aod_day(date_obj, self.params)
                    if modis_files:
                        logger.debug(f"Successfully downloaded MODIS data for {date_str}")
                    else:
                        logger.debug(f"No MODIS data available for {date_str}")
                except Exception as e:
                    logger.debug(f"MODIS download failed for {date_str}: {e}")
                
                # Try to download CAMS data
                try:
                    cams_files = download_cams_dust_day(date_obj, self.params)
                    if cams_files:
                        logger.debug(f"Successfully downloaded CAMS data for {date_str}")
                    else:
                        logger.debug(f"No CAMS data available for {date_str}")
                except Exception as e:
                    logger.debug(f"CAMS download failed for {date_str}: {e}")
                
                # Try to download ERA5 data
                try:
                    era5_file = download_era5_day(date_obj, self.params)
                    if era5_file:
                        logger.debug(f"Successfully downloaded ERA5 data for {date_str}")
                    else:
                        logger.debug(f"No ERA5 data available for {date_str}")
                except Exception as e:
                    logger.debug(f"ERA5 download failed for {date_str}: {e}")
                
            except ImportError as e:
                logger.warning(f"Could not import download modules: {e}")
            
            # Check if raw data exists for this date after download attempts
            raw_modis_dir = os.path.join(self.params['paths']['raw_dir'], 'modis', date_str.replace('-', ''))
            raw_cams_file = os.path.join(self.params['paths']['raw_dir'], 'cams', f'cams_dust_analysis_{date_str.replace("-", "")}.nc')
            raw_era5_file = os.path.join(self.params['paths']['raw_dir'], 'era5', f'era5_{date_str.replace("-", "")}.nc')
            
            # Check if at least MODIS or CAMS data exists
            has_modis = os.path.exists(raw_modis_dir) and len(os.listdir(raw_modis_dir)) > 0
            has_cams = os.path.exists(raw_cams_file)
            has_era5 = os.path.exists(raw_era5_file)
            
            if has_modis or has_cams:
                logger.debug(f"Real data available for {date_str}: MODIS={has_modis}, CAMS={has_cams}, ERA5={has_era5}")
                
                # Run the pipeline
                orchestrate_day(date_str)
                
                logger.debug(f"Successfully processed real data for {date_str}")
                return True
            else:
                logger.debug(f"No real data available for {date_str}")
                return False
                
        except Exception as e:
            logger.error(f"Error running real pipeline for province {province_id} on {date_str}: {e}")
            return False
    
    def analyze_data_coverage(self, session: Session) -> Dict[str, Any]:
        """
        Analyze current data coverage across all provinces
        """
        logger.info("Analyzing data coverage...")
        
        provinces = session.query(Province).count()
        latest_data = self.get_latest_real_data_per_province(session)
        missing_dates = self.get_missing_dates_per_province(session)
        
        # Statistics
        provinces_with_data = sum(1 for v in latest_data.values() if v is not None)
        provinces_without_data = provinces - provinces_with_data
        
        provinces_needing_update = sum(1 for dates in missing_dates.values() if len(dates) > 0)
        total_missing_records = sum(len(dates) for dates in missing_dates.values())
        
        # Find oldest and newest data
        dates_with_data = [d for d in latest_data.values() if d is not None]
        oldest_data = min(dates_with_data) if dates_with_data else None
        newest_data = max(dates_with_data) if dates_with_data else None
        
        analysis = {
            'total_provinces': provinces,
            'provinces_with_data': provinces_with_data,
            'provinces_without_data': provinces_without_data,
            'provinces_needing_update': provinces_needing_update,
            'total_missing_records': total_missing_records,
            'oldest_data_date': oldest_data,
            'newest_data_date': newest_data,
            'coverage_pct': (provinces_with_data / provinces * 100) if provinces > 0 else 0
        }
        
        logger.info(f"Data Coverage Analysis:")
        logger.info(f"  Total provinces: {analysis['total_provinces']}")
        logger.info(f"  Provinces with data: {analysis['provinces_with_data']}")
        logger.info(f"  Provinces without data: {analysis['provinces_without_data']}")
        logger.info(f"  Provinces needing update: {analysis['provinces_needing_update']}")
        logger.info(f"  Total missing records: {analysis['total_missing_records']}")
        logger.info(f"  Coverage: {analysis['coverage_pct']:.1f}%")
        logger.info(f"  Date range: {analysis['oldest_data_date']} to {analysis['newest_data_date']}")
        
        return analysis
    
    def is_date_too_recent(self, date_str: str) -> bool:
        """
        Check if date is too recent for real data availability
        CAMS and ERA5 typically have 3-5 days delay
        """
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_ago = (today - date_obj).days
        
        # Real satellite/reanalysis data typically available after 3-5 days
        if days_ago < 3:
            logger.debug(f"Date {date_str} is too recent ({days_ago} days ago), real data likely not available yet")
            return True
        return False
    
    def try_run_real_pipeline(self, date_str: str) -> bool:
        """
        Try to run real pipeline for a specific date
        Returns True if successful, False if data not available
        """
        try:
            # Skip if date is too recent for real data
            if self.is_date_too_recent(date_str):
                logger.info(f"Skipping {date_str} - too recent for real data (use forecast instead)")
                return False
            
            logger.info(f"Attempting to run real pipeline for {date_str}...")
            
            # Try to download real data first
            try:
                from .download_modis import download_modis_aod_day
                from .download_cams import download_cams_dust_day
                from .download_era5 import download_era5_day
                
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Try to download MODIS data
                logger.info(f"Attempting to download MODIS data for {date_str}...")
                try:
                    modis_files = download_modis_aod_day(date_obj, self.params)
                    if modis_files:
                        logger.info(f"Successfully downloaded MODIS data for {date_str}")
                    else:
                        logger.warning(f"No MODIS data available for {date_str}")
                except Exception as e:
                    logger.warning(f"MODIS download failed for {date_str}: {e}")
                
                # Try to download CAMS data
                logger.info(f"Attempting to download CAMS data for {date_str}...")
                try:
                    cams_files = download_cams_dust_day(date_obj, self.params)
                    if cams_files:
                        logger.info(f"Successfully downloaded CAMS data for {date_str}")
                    else:
                        logger.warning(f"No CAMS data available for {date_str}")
                except Exception as e:
                    logger.warning(f"CAMS download failed for {date_str}: {e}")
                
                # Try to download ERA5 data
                logger.info(f"Attempting to download ERA5 data for {date_str}...")
                try:
                    era5_file = download_era5_day(date_obj, self.params)
                    if era5_file:
                        logger.info(f"Successfully downloaded ERA5 data for {date_str}")
                    else:
                        logger.warning(f"No ERA5 data available for {date_str}")
                except Exception as e:
                    logger.warning(f"ERA5 download failed for {date_str}: {e}")
                
            except ImportError as e:
                logger.warning(f"Could not import download modules: {e}")
            
            # Check if raw data exists for this date after download attempts
            raw_modis_dir = os.path.join(self.params['paths']['raw_dir'], 'modis', date_str.replace('-', ''))
            raw_cams_file = os.path.join(self.params['paths']['raw_dir'], 'cams', f'cams_dust_analysis_{date_str.replace("-", "")}.nc')
            raw_era5_file = os.path.join(self.params['paths']['raw_dir'], 'era5', f'era5_{date_str.replace("-", "")}.nc')
            
            # Check if at least MODIS or CAMS data exists
            has_modis = os.path.exists(raw_modis_dir) and len(os.listdir(raw_modis_dir)) > 0
            has_cams = os.path.exists(raw_cams_file)
            has_era5 = os.path.exists(raw_era5_file)
            
            if has_modis or has_cams:
                logger.info(f"Real data available for {date_str}: MODIS={has_modis}, CAMS={has_cams}, ERA5={has_era5}")
                
                # Run the pipeline
                orchestrate_day(date_str)
                
                logger.info(f"Successfully processed real data for {date_str}")
                return True
            else:
                logger.warning(f"No real data available for {date_str}")
                return False
                
        except Exception as e:
            logger.error(f"Error running real pipeline for {date_str}: {e}")
            return False
    
    def generate_forecasts_for_missing_data(self, session: Session, 
                                           missing_dates: Dict[int, List[str]]) -> int:
        """
        Generate forecasts for missing dates
        Returns number of forecast records created
        """
        logger.info("Generating forecasts for missing data...")
        
        # Collect all unique dates that need forecasting
        all_missing_dates = set()
        for dates in missing_dates.values():
            all_missing_dates.update(dates)
        
        all_missing_dates = sorted(list(all_missing_dates))
        
        if not all_missing_dates:
            logger.info("No missing dates to forecast")
            return 0
        
        logger.info(f"Need to forecast {len(all_missing_dates)} unique dates")
        
        # Debug: Check how many provinces need updates
        provinces_needing_forecast = len([p for p in missing_dates.keys() if len(missing_dates[p]) > 0])
        logger.info(f"Provinces needing forecast: {provinces_needing_forecast}")
        
        forecast_data = []
        provinces = session.query(Province).all()
        
        for date_str in all_missing_dates:
            logger.info(f"Generating forecasts for {date_str}...")
            
            for province in provinces:
                # Check if this province-date combination needs forecasting
                needs_forecast = (province.id in missing_dates and 
                                date_str in missing_dates.get(province.id, []))
                
                if needs_forecast:
                    try:
                        # Check if forecast already exists
                        existing = session.query(DailyStats).filter(
                            DailyStats.province_id == province.id,
                            DailyStats.date == date_str
                        ).first()
                        
                        if existing:
                            logger.debug(f"Data already exists for province {province.id} on {date_str}")
                            continue
                        
                        # Generate forecast
                        prediction = self.forecast_system.predict_pm25(province.id, date_str)
                        
                        forecast_record = {
                            'date': date_str,
                            'province_id': province.id,
                            **prediction
                        }
                        
                        forecast_data.append(forecast_record)
                        
                    except Exception as e:
                        logger.error(f"Error forecasting for province {province.id} on {date_str}: {e}")
                        continue
        
        # Debug: Log how many records we generated
        logger.info(f"Generated {len(forecast_data)} forecast records in total")
        
        # Save forecasts to database
        if forecast_data:
            logger.info(f"Saving {len(forecast_data)} forecast records to database...")
            self.forecast_system.save_forecasts_to_database(forecast_data)
            logger.info(f"Successfully saved {len(forecast_data)} forecast records")
        
        return len(forecast_data)
    
    def run_intelligent_pipeline(self, force_update: bool = False) -> Dict[str, Any]:
        """
        Main orchestration method - İL BAZINDA ÇALIŞIR:
        1. Her il için en son veri tarihini bul
        2. Her il için eksik tarihleri tespit et
        3. Her il için sadece eksik tarihlerin verilerini indir
        4. Gerçek veri yoksa tahmin üret
        
        Args:
            force_update: If True, regenerate all data regardless of existing data
            
        Returns:
            Summary of what was processed
        """
        logger.info("=" * 80)
        logger.info("Starting Intelligent Pipeline Orchestrator (İL BAZINDA)")
        logger.info("=" * 80)
        
        with db_manager.get_session() as session:
            # Step 1: Analyze current state
            analysis = self.analyze_data_coverage(session)
            
            # Step 2: Her il için en son veri tarihini bul
            latest_data_per_province = self.get_latest_real_data_per_province(session)
            
            # Step 3: Her il için eksik tarihleri hesapla
            provinces = session.query(Province).all()
            real_data_processed = 0
            forecast_data_generated = 0
            
            logger.info(f"Processing {len(provinces)} provinces individually...")
            
            for province in provinces:
                province_id = province.id
                province_name = province.name
                
                # Bu il için en son veri tarihi
                latest_date = latest_data_per_province.get(province_id)
                
                if latest_date:
                    # En son veri tarihinden sonraki eksik günleri bul
                    missing_dates = self.get_missing_dates_for_province_after_date(
                        session, province_id, latest_date
                    )
                    logger.info(f"Province {province_name} ({province_id}): Latest data {latest_date}, missing {len(missing_dates)} dates")
                else:
                    # Hiç veri yoksa son 90 günün tümünü al
                    missing_dates = self.get_missing_dates_for_province_no_data(
                        session, province_id
                    )
                    logger.info(f"Province {province_name} ({province_id}): No data, need {len(missing_dates)} dates")
                
                # Bu il için eksik tarihleri işle - SADECE TAHMIN ÜRET
                # Gerçek veri indirme scheduler tarafından yapılır
                for date_str in missing_dates:
                    try:
                        # Önce bu tarih için zaten veri var mı kontrol et
                        existing = session.query(DailyStats).filter(
                            DailyStats.province_id == province_id,
                            DailyStats.date == date_str
                        ).first()
                        
                        if existing:
                            logger.debug(f"Data already exists for province {province_id} on {date_str}, skipping")
                            continue
                        
                        # Tahmin üret
                        prediction = self.forecast_system.predict_pm25(province_id, date_str)
                        forecast_record = {
                            'date': date_str,
                            'province_id': province_id,
                            **prediction
                        }
                        self.forecast_system.save_forecasts_to_database([forecast_record])
                        forecast_data_generated += 1
                        logger.debug(f"Generated forecast for province {province_id} on {date_str}")
                    except Exception as e:
                        logger.error(f"Error forecasting for province {province_id} on {date_str}: {e}")
            
            # Step 4: Final analysis
            final_analysis = self.analyze_data_coverage(session)
            
            # Prepare summary
            summary = {
                'initial_coverage_pct': analysis['coverage_pct'],
                'final_coverage_pct': final_analysis['coverage_pct'],
                'forecast_records_generated': forecast_data_generated,
                'provinces_updated': final_analysis['provinces_with_data'],
                'status': 'success'
            }
            
            logger.info("=" * 80)
            logger.info("Intelligent Pipeline Orchestrator Complete (İL BAZINDA)")
            logger.info(f"  Initial coverage: {summary['initial_coverage_pct']:.1f}%")
            logger.info(f"  Final coverage: {summary['final_coverage_pct']:.1f}%")
            logger.info(f"  Forecast records generated: {summary['forecast_records_generated']}")
            logger.info(f"  Provinces with data: {summary['provinces_updated']}")
            logger.info("=" * 80)
            
            return summary


def run_intelligent_orchestrator(max_lookback_days: int = 90, 
                                 min_data_age_days: int = 7) -> Dict[str, Any]:
    """
    Convenience function to run the intelligent orchestrator
    
    Args:
        max_lookback_days: Maximum days to look back (default 90 = 3 months)
        min_data_age_days: Data older than this is considered stale (default 7 days)
    """
    orchestrator = IntelligentPipelineOrchestrator(
        max_lookback_days=max_lookback_days,
        min_data_age_days=min_data_age_days
    )
    
    return orchestrator.run_intelligent_pipeline()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Intelligent Pipeline Orchestrator - Automatically finds and processes data"
    )
    parser.add_argument(
        "--max-lookback",
        type=int,
        default=90,
        help="Maximum days to look back for data (default: 90)"
    )
    parser.add_argument(
        "--min-age",
        type=int,
        default=7,
        help="Minimum data age to consider recent (default: 7)"
    )
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze coverage without processing"
    )
    
    args = parser.parse_args()
    
    if args.analyze_only:
        # Only analyze
        orchestrator = IntelligentPipelineOrchestrator(
            max_lookback_days=args.max_lookback,
            min_data_age_days=args.min_age
        )
        
        with db_manager.get_session() as session:
            analysis = orchestrator.analyze_data_coverage(session)
            print("\n" + "=" * 80)
            print("DATA COVERAGE ANALYSIS")
            print("=" * 80)
            for key, value in analysis.items():
                print(f"{key:.<40} {value}")
            print("=" * 80)
    else:
        # Run full pipeline
        summary = run_intelligent_orchestrator(
            max_lookback_days=args.max_lookback,
            min_data_age_days=args.min_age
        )
        
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 80)
        for key, value in summary.items():
            print(f"{key:.<40} {value}")
        print("=" * 80)

