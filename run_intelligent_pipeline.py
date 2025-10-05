"""
Main script to run the Intelligent Pipeline Orchestrator
Finds latest data for all 81 provinces and fills gaps with forecasts
"""
import sys
import os
from datetime import datetime
import argparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.intelligent_pipeline_orchestrator import IntelligentPipelineOrchestrator
from src.database import db_manager


def main():
    parser = argparse.ArgumentParser(
        description="Intelligent Pipeline - Auto-process data for all 81 provinces",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full pipeline (3 months lookback, 7 days recency)
  python run_intelligent_pipeline.py
  
  # Only analyze current coverage
  python run_intelligent_pipeline.py --analyze-only
  
  # Custom lookback period (30 days instead of 90)
  python run_intelligent_pipeline.py --max-lookback 30
  
  # Consider data fresh if less than 3 days old
  python run_intelligent_pipeline.py --min-age 3
  
  # Verbose logging
  python run_intelligent_pipeline.py --verbose
        """
    )
    
    parser.add_argument(
        "--max-lookback",
        type=int,
        default=90,
        help="Maximum days to look back for data (default: 90 = 3 months)"
    )
    
    parser.add_argument(
        "--min-age",
        type=int,
        default=7,
        help="Data older than this many days is considered stale (default: 7)"
    )
    
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Only analyze current coverage without processing"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--export-report",
        type=str,
        help="Export coverage report to JSON file"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    import logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('intelligent_pipeline.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    print("=" * 80)
    print("INTELLIGENT PIPELINE ORCHESTRATOR")
    print("=" * 80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Max lookback: {args.max_lookback} days")
    print(f"Min data age: {args.min_age} days")
    print("=" * 80)
    print()
    
    try:
        # Initialize orchestrator
        orchestrator = IntelligentPipelineOrchestrator(
            max_lookback_days=args.max_lookback,
            min_data_age_days=args.min_age
        )
        
        if args.analyze_only:
            # Only analyze coverage
            logger.info("Running coverage analysis only...")
            
            with db_manager.get_session() as session:
                analysis = orchestrator.analyze_data_coverage(session)
                latest_data = orchestrator.get_latest_real_data_per_province(session)
                missing_dates = orchestrator.get_missing_dates_per_province(session)
            
            print("\n" + "=" * 80)
            print("DATA COVERAGE ANALYSIS")
            print("=" * 80)
            print(f"Total provinces: {analysis['total_provinces']}")
            print(f"Provinces with data: {analysis['provinces_with_data']} ({analysis['coverage_pct']:.1f}%)")
            print(f"Provinces without data: {analysis['provinces_without_data']}")
            print(f"Provinces needing update: {analysis['provinces_needing_update']}")
            print(f"Total missing records: {analysis['total_missing_records']}")
            print(f"Oldest data: {analysis['oldest_data_date']}")
            print(f"Newest data: {analysis['newest_data_date']}")
            print("=" * 80)
            
            # Show per-province summary
            print("\nPER-PROVINCE SUMMARY (first 10 provinces):")
            print("-" * 80)
            
            with db_manager.get_session() as session:
                from database import Province
                provinces = session.query(Province).limit(10).all()
                
                for province in provinces:
                    latest = latest_data.get(province.id)
                    missing = len(missing_dates.get(province.id, []))
                    
                    if latest:
                        days_old = (datetime.now() - datetime.strptime(latest, '%Y-%m-%d')).days
                        status = "✓ OK" if days_old <= args.min_age else f"⚠ {days_old} days old"
                    else:
                        status = "✗ NO DATA"
                    
                    print(f"{province.name:.<30} {status:.<20} Missing: {missing} dates")
            
            print("-" * 80)
            
            # Export if requested
            if args.export_report:
                import json
                report = {
                    'timestamp': datetime.now().isoformat(),
                    'analysis': analysis,
                    'provinces': {
                        pid: {
                            'latest_date': latest_data.get(pid),
                            'missing_dates': missing_dates.get(pid, [])
                        }
                        for pid in latest_data.keys()
                    }
                }
                
                with open(args.export_report, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)
                
                print(f"\nReport exported to: {args.export_report}")
            
        else:
            # Run full pipeline
            logger.info("Running full intelligent pipeline...")
            
            summary = orchestrator.run_intelligent_pipeline()
            
            print("\n" + "=" * 80)
            print("PIPELINE EXECUTION SUMMARY")
            print("=" * 80)
            print(f"Status: {summary['status'].upper()}")
            print(f"Initial coverage: {summary['initial_coverage_pct']:.1f}%")
            print(f"Final coverage: {summary['final_coverage_pct']:.1f}%")
            print(f"Improvement: +{summary['final_coverage_pct'] - summary['initial_coverage_pct']:.1f}%")
            print()
            print(f"Forecast records generated: {summary['forecast_records_generated']}")
            print(f"Provinces with data: {summary['provinces_updated']}/81")
            print("=" * 80)
            
            # Export if requested
            if args.export_report:
                import json
                summary['timestamp'] = datetime.now().isoformat()
                
                with open(args.export_report, 'w', encoding='utf-8') as f:
                    json.dump(summary, f, indent=2, ensure_ascii=False)
                
                print(f"\nSummary exported to: {args.export_report}")
        
        print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\nOperation cancelled by user")
        return 1
        
    except Exception as e:
        logger.error(f"\nFatal error: {e}", exc_info=True)
        print("\n" + "=" * 80)
        print("ERROR")
        print("=" * 80)
        print(f"An error occurred: {e}")
        print("Check intelligent_pipeline.log for details")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(main())

