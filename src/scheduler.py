"""
Automated scheduler for dust monitoring pipeline
Handles daily data processing and alert distribution
"""
import os
import sys
import schedule
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
import yaml
import subprocess
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

from database import db_manager, SystemStatus
from email_service import EmailService
from api import process_alert_queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DustPipelineScheduler:
    """Automated scheduler for dust monitoring pipeline"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.email_service = EmailService()
        
        # Ensure logs directory exists
        os.makedirs('logs', exist_ok=True)
        
        # Initialize database
        db_manager.create_tables()
        
        logger.info("Dust Pipeline Scheduler initialized")
    
    def _load_config(self, config_path: str = None) -> dict:
        """Load scheduler configuration"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "params.yaml")
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except FileNotFoundError:
            config = {}
        
        # Default scheduler settings
        default_scheduler = {
            'daily_run_time': '06:00',  # UTC time
            'pipeline_timeout_minutes': 60,
            'max_retries': 3,
            'retry_delay_minutes': 15,
            'alert_processing_interval_minutes': 10,
            'cleanup_old_data_days': 90
        }
        
        if 'scheduler' not in config:
            config['scheduler'] = default_scheduler
        else:
            for key, value in default_scheduler.items():
                if key not in config['scheduler']:
                    config['scheduler'][key] = value
        
        return config
    
    def log_system_status(self, component: str, status: str, message: str, 
                         processing_time: float = None, data_coverage: float = None, 
                         error_details: Dict = None):
        """Log system status to database"""
        try:
            with db_manager.get_session() as session:
                status_record = SystemStatus(
                    date=datetime.utcnow().strftime('%Y-%m-%d'),
                    component=component,
                    status=status,
                    message=message,
                    processing_time_seconds=processing_time,
                    data_coverage_pct=data_coverage,
                    error_details=error_details
                )
                session.add(status_record)
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to log system status: {e}")
    
    def run_daily_pipeline(self, date_str: str = None) -> bool:
        """Run the daily data processing pipeline"""
        if date_str is None:
            # Use yesterday's date (data availability lag)
            date_str = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        logger.info(f"Starting daily pipeline for {date_str}")
        start_time = datetime.utcnow()
        
        try:
            # Run orchestrate_day script
            script_path = os.path.join(os.path.dirname(__file__), 'orchestrate_day.py')
            cmd = [sys.executable, '-m', 'src.orchestrate_day', '--date', date_str]
            
            logger.info(f"Executing: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config['scheduler']['pipeline_timeout_minutes'] * 60,
                cwd=os.path.dirname(os.path.dirname(__file__))
            )
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            if result.returncode == 0:
                logger.info(f"Pipeline completed successfully for {date_str}")
                logger.info(f"Processing time: {processing_time:.1f} seconds")
                
                # Parse output for data coverage info
                output = result.stdout
                data_coverage = self._extract_coverage_from_output(output)
                
                self.log_system_status(
                    component='pipeline',
                    status='success',
                    message=f'Daily pipeline completed for {date_str}',
                    processing_time=processing_time,
                    data_coverage=data_coverage
                )
                
                # Update database with new data
                self._update_database_from_pipeline(date_str)
                
                return True
            else:
                error_msg = f"Pipeline failed for {date_str}: {result.stderr}"
                logger.error(error_msg)
                
                self.log_system_status(
                    component='pipeline',
                    status='error',
                    message=error_msg,
                    processing_time=processing_time,
                    error_details={'stderr': result.stderr, 'stdout': result.stdout}
                )
                
                return False
                
        except subprocess.TimeoutExpired:
            error_msg = f"Pipeline timeout for {date_str}"
            logger.error(error_msg)
            
            self.log_system_status(
                component='pipeline',
                status='error',
                message=error_msg,
                error_details={'error_type': 'timeout'}
            )
            
            return False
            
        except Exception as e:
            error_msg = f"Pipeline exception for {date_str}: {str(e)}"
            logger.error(error_msg)
            
            self.log_system_status(
                component='pipeline',
                status='error',
                message=error_msg,
                error_details={'error_type': 'exception', 'error': str(e)}
            )
            
            return False
    
    def _extract_coverage_from_output(self, output: str) -> float:
        """Extract data coverage percentage from pipeline output"""
        try:
            # Look for coverage information in output
            lines = output.split('\n')
            for line in lines:
                if 'coverage' in line.lower() and '%' in line:
                    # Extract percentage
                    import re
                    match = re.search(r'(\d+\.?\d*)%', line)
                    if match:
                        return float(match.group(1))
            return 85.0  # Default assumption
        except:
            return 85.0
    
    def _update_database_from_pipeline(self, date_str: str):
        """Update database with pipeline outputs"""
        try:
            derived_dir = self.config['paths']['derived_dir']
            
            # Load province stats
            province_stats_file = os.path.join(derived_dir, f'province_stats_{date_str}.csv')
            pm25_file = os.path.join(derived_dir, f'pm25_{date_str}.csv')
            
            if os.path.exists(pm25_file):
                import pandas as pd
                
                # Load PM2.5 data
                df = pd.read_csv(pm25_file)
                
                # Convert to database format
                stats_data = []
                for _, row in df.iterrows():
                    stat_record = {
                        'date': date_str,
                        'province_id': int(row['province_id']),
                        'aod_mean': float(row.get('aod_mean', 0)) if pd.notna(row.get('aod_mean')) else None,
                        'aod_max': float(row.get('aod_max', 0)) if pd.notna(row.get('aod_max')) else None,
                        'aod_p95': float(row.get('aod_p95', 0)) if pd.notna(row.get('aod_p95')) else None,
                        'dust_aod_mean': float(row.get('dust_aod_mean', 0)) if pd.notna(row.get('dust_aod_mean')) else None,
                        'dust_event_detected': bool(row.get('dust_event_detected', False)),
                        'dust_intensity': str(row.get('dust_intensity', 'None')),
                        'pm25': float(row['pm25']) if pd.notna(row['pm25']) else None,
                        'pm25_lower': float(row.get('pm25_lower', 0)) if pd.notna(row.get('pm25_lower')) else None,
                        'pm25_upper': float(row.get('pm25_upper', 0)) if pd.notna(row.get('pm25_upper')) else None,
                        'air_quality_category': str(row.get('air_quality', 'Unknown')),
                        'rh_mean': float(row.get('rh_mean', 0)) if pd.notna(row.get('rh_mean')) else None,
                        'blh_mean': float(row.get('blh_mean', 0)) if pd.notna(row.get('blh_mean')) else None,
                        'data_quality_score': float(row.get('coverage_pct', 85)) / 100.0 if pd.notna(row.get('coverage_pct')) else 0.85
                    }
                    stats_data.append(stat_record)
                
                # Store in database
                with db_manager.get_session() as session:
                    db_manager.store_daily_stats(session, stats_data)
                
                logger.info(f"Updated database with {len(stats_data)} province statistics for {date_str}")
            
        except Exception as e:
            logger.error(f"Failed to update database from pipeline outputs: {e}")
    
    def process_alerts(self):
        """Process pending alerts and send emails"""
        logger.info("Processing alert queue")
        
        try:
            # This will use the API's background task function
            import asyncio
            asyncio.run(process_alert_queue())
            
            logger.info("Alert processing completed")
            
        except Exception as e:
            logger.error(f"Alert processing failed: {e}")
            
            self.log_system_status(
                component='alerts',
                status='error',
                message=f'Alert processing failed: {str(e)}',
                error_details={'error': str(e)}
            )
    
    def cleanup_old_data(self):
        """Clean up old data from database and files"""
        try:
            cleanup_days = self.config['scheduler']['cleanup_old_data_days']
            cutoff_date = (datetime.utcnow() - timedelta(days=cleanup_days)).strftime('%Y-%m-%d')
            
            with db_manager.get_session() as session:
                # Clean old daily stats
                from database import DailyStats, Alert
                
                old_stats = session.query(DailyStats).filter(DailyStats.date < cutoff_date).all()
                old_alerts = session.query(Alert).filter(Alert.created_at < (datetime.utcnow() - timedelta(days=cleanup_days))).all()
                
                for stat in old_stats:
                    session.delete(stat)
                
                for alert in old_alerts:
                    session.delete(alert)
                
                session.commit()
                
                logger.info(f"Cleaned up {len(old_stats)} old statistics and {len(old_alerts)} old alerts")
            
            # Clean old files
            derived_dir = self.config['paths']['derived_dir']
            if os.path.exists(derived_dir):
                import glob
                
                cutoff_timestamp = (datetime.utcnow() - timedelta(days=cleanup_days)).timestamp()
                
                for file_pattern in ['*.csv', '*.tif', '*.json']:
                    for file_path in glob.glob(os.path.join(derived_dir, file_pattern)):
                        if os.path.getmtime(file_path) < cutoff_timestamp:
                            try:
                                os.remove(file_path)
                                logger.info(f"Removed old file: {file_path}")
                            except:
                                pass
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def retry_failed_pipeline(self, date_str: str, max_retries: int = None) -> bool:
        """Retry failed pipeline execution"""
        if max_retries is None:
            max_retries = self.config['scheduler']['max_retries']
        
        retry_delay = self.config['scheduler']['retry_delay_minutes'] * 60
        
        for attempt in range(max_retries):
            logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {date_str}")
            
            if self.run_daily_pipeline(date_str):
                logger.info(f"Pipeline succeeded on retry {attempt + 1} for {date_str}")
                return True
            
            if attempt < max_retries - 1:
                logger.info(f"Waiting {retry_delay} seconds before next retry")
                time.sleep(retry_delay)
        
        logger.error(f"Pipeline failed after {max_retries} retries for {date_str}")
        return False
    
    def scheduled_daily_job(self):
        """Main scheduled job for daily processing"""
        logger.info("Starting scheduled daily job")
        
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Run pipeline
        success = self.run_daily_pipeline(yesterday)
        
        if not success:
            # Retry if failed
            success = self.retry_failed_pipeline(yesterday)
        
        # Process alerts regardless (might have data from previous days)
        self.process_alerts()
        
        logger.info(f"Scheduled daily job completed. Success: {success}")
    
    def start_scheduler(self):
        """Start the scheduler daemon"""
        logger.info("Starting Dust Pipeline Scheduler")
        
        # Schedule daily pipeline
        daily_time = self.config['scheduler']['daily_run_time']
        schedule.every().day.at(daily_time).do(self.scheduled_daily_job)
        
        # Schedule alert processing every 10 minutes
        alert_interval = self.config['scheduler']['alert_processing_interval_minutes']
        schedule.every(alert_interval).minutes.do(self.process_alerts)
        
        # Schedule cleanup once a week
        schedule.every().sunday.at("02:00").do(self.cleanup_old_data)
        
        logger.info(f"Scheduled jobs:")
        logger.info(f"  - Daily pipeline: every day at {daily_time} UTC")
        logger.info(f"  - Alert processing: every {alert_interval} minutes")
        logger.info(f"  - Data cleanup: every Sunday at 02:00 UTC")
        
        # Main scheduler loop
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise


def main():
    """Main entry point for scheduler"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dust Pipeline Scheduler")
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--run-once', help='Run pipeline once for specific date (YYYY-MM-DD)')
    parser.add_argument('--process-alerts', action='store_true', help='Process alerts once and exit')
    parser.add_argument('--cleanup', action='store_true', help='Run cleanup once and exit')
    parser.add_argument('--daemon', action='store_true', help='Run as daemon (default)')
    
    args = parser.parse_args()
    
    scheduler = DustPipelineScheduler(args.config)
    
    if args.run_once:
        success = scheduler.run_daily_pipeline(args.run_once)
        sys.exit(0 if success else 1)
    elif args.process_alerts:
        scheduler.process_alerts()
        sys.exit(0)
    elif args.cleanup:
        scheduler.cleanup_old_data()
        sys.exit(0)
    else:
        # Run as daemon
        scheduler.start_scheduler()


if __name__ == "__main__":
    main()
