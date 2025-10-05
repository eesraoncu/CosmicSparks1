"""
Test script for Intelligent Pipeline Orchestrator
Tests all major functionality without running full pipeline
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from datetime import datetime, timedelta
from src.database import db_manager, Province, DailyStats
from src.intelligent_pipeline_orchestrator import IntelligentPipelineOrchestrator


def test_database_connection():
    """Test database connection"""
    print("\n" + "=" * 80)
    print("TEST 1: Database Connection")
    print("=" * 80)
    
    try:
        with db_manager.get_session() as session:
            province_count = session.query(Province).count()
            stats_count = session.query(DailyStats).count()
            
            print(f"✓ Database connection successful")
            print(f"  Provinces in DB: {province_count}")
            print(f"  Daily stats records: {stats_count}")
            
            if province_count != 81:
                print(f"  ⚠ Warning: Expected 81 provinces, found {province_count}")
                
            return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False


def test_orchestrator_initialization():
    """Test orchestrator initialization"""
    print("\n" + "=" * 80)
    print("TEST 2: Orchestrator Initialization")
    print("=" * 80)
    
    try:
        orchestrator = IntelligentPipelineOrchestrator(
            max_lookback_days=90,
            min_data_age_days=7
        )
        
        print(f"✓ Orchestrator initialized successfully")
        print(f"  Max lookback: {orchestrator.max_lookback_days} days")
        print(f"  Min data age: {orchestrator.min_data_age_days} days")
        
        return True
    except Exception as e:
        print(f"✗ Orchestrator initialization failed: {e}")
        return False


def test_latest_data_detection():
    """Test latest data detection per province"""
    print("\n" + "=" * 80)
    print("TEST 3: Latest Data Detection")
    print("=" * 80)
    
    try:
        orchestrator = IntelligentPipelineOrchestrator()
        
        with db_manager.get_session() as session:
            latest_data = orchestrator.get_latest_real_data_per_province(session)
            
            print(f"✓ Latest data detection successful")
            print(f"  Total provinces checked: {len(latest_data)}")
            
            # Count provinces with/without data
            with_data = sum(1 for v in latest_data.values() if v is not None)
            without_data = len(latest_data) - with_data
            
            print(f"  Provinces with data: {with_data}")
            print(f"  Provinces without data: {without_data}")
            
            # Show sample
            print("\n  Sample (first 5 provinces):")
            for i, (prov_id, date) in enumerate(list(latest_data.items())[:5]):
                province = session.query(Province).filter(Province.id == prov_id).first()
                name = province.name if province else f"Province {prov_id}"
                status = date if date else "NO DATA"
                print(f"    {name}: {status}")
            
            return True
    except Exception as e:
        print(f"✗ Latest data detection failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_coverage_analysis():
    """Test coverage analysis"""
    print("\n" + "=" * 80)
    print("TEST 4: Coverage Analysis")
    print("=" * 80)
    
    try:
        orchestrator = IntelligentPipelineOrchestrator()
        
        with db_manager.get_session() as session:
            analysis = orchestrator.analyze_data_coverage(session)
            
            print(f"✓ Coverage analysis successful")
            print(f"\n  Analysis Results:")
            for key, value in analysis.items():
                print(f"    {key}: {value}")
            
            return True
    except Exception as e:
        print(f"✗ Coverage analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_missing_dates_identification():
    """Test missing dates identification"""
    print("\n" + "=" * 80)
    print("TEST 5: Missing Dates Identification")
    print("=" * 80)
    
    try:
        orchestrator = IntelligentPipelineOrchestrator(min_data_age_days=7)
        
        with db_manager.get_session() as session:
            missing_dates = orchestrator.get_missing_dates_per_province(session)
            
            print(f"✓ Missing dates identification successful")
            print(f"  Provinces checked: {len(missing_dates)}")
            
            # Count provinces needing updates
            needing_update = sum(1 for dates in missing_dates.values() if len(dates) > 0)
            total_missing = sum(len(dates) for dates in missing_dates.values())
            
            print(f"  Provinces needing update: {needing_update}")
            print(f"  Total missing date-province combinations: {total_missing}")
            
            # Show sample
            if needing_update > 0:
                print("\n  Sample provinces needing update:")
                count = 0
                for prov_id, dates in missing_dates.items():
                    if len(dates) > 0:
                        province = session.query(Province).filter(Province.id == prov_id).first()
                        name = province.name if province else f"Province {prov_id}"
                        print(f"    {name}: {len(dates)} missing dates (e.g., {dates[0]} to {dates[-1]})")
                        count += 1
                        if count >= 5:
                            break
            
            return True
    except Exception as e:
        print(f"✗ Missing dates identification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_forecast_generation():
    """Test forecast generation for a single province-date"""
    print("\n" + "=" * 80)
    print("TEST 6: Forecast Generation (Single Record)")
    print("=" * 80)
    
    try:
        orchestrator = IntelligentPipelineOrchestrator()
        
        # Test with Ankara (province_id=6) for tomorrow
        test_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        prediction = orchestrator.forecast_system.predict_pm25(6, test_date)
        
        print(f"✓ Forecast generation successful")
        print(f"\n  Test Parameters:")
        print(f"    Province: Ankara (ID: 6)")
        print(f"    Date: {test_date}")
        print(f"\n  Forecast Results:")
        print(f"    PM2.5: {prediction['pm25']:.1f} μg/m³")
        print(f"    Confidence: [{prediction['pm25_lower']:.1f}, {prediction['pm25_upper']:.1f}]")
        print(f"    AOD Mean: {prediction['aod_mean']:.3f}")
        print(f"    Dust Event: {prediction['dust_event_detected']}")
        print(f"    Dust Intensity: {prediction['dust_intensity']}")
        print(f"    Air Quality: {prediction['air_quality_category']}")
        print(f"    Data Quality Score: {prediction['data_quality_score']}")
        
        return True
    except Exception as e:
        print(f"✗ Forecast generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_insertion():
    """Test inserting a sample forecast record"""
    print("\n" + "=" * 80)
    print("TEST 7: Database Insertion")
    print("=" * 80)
    
    try:
        orchestrator = IntelligentPipelineOrchestrator()
        
        # Create a test forecast record
        test_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')  # Far future to avoid conflicts
        
        prediction = orchestrator.forecast_system.predict_pm25(6, test_date)
        
        test_data = [{
            'date': test_date,
            'province_id': 6,
            **prediction
        }]
        
        # Save to database
        with db_manager.get_session() as session:
            db_manager.store_daily_stats(session, test_data)
            
            # Verify insertion
            record = session.query(DailyStats).filter(
                DailyStats.date == test_date,
                DailyStats.province_id == 6
            ).first()
            
            if record:
                print(f"✓ Database insertion successful")
                print(f"\n  Inserted Record:")
                print(f"    Date: {record.date}")
                print(f"    Province ID: {record.province_id}")
                print(f"    PM2.5: {record.pm25:.1f} μg/m³")
                print(f"    Data Quality: {record.data_quality_score}")
                
                # Clean up test record
                session.delete(record)
                session.commit()
                print(f"\n  Test record cleaned up")
                
                return True
            else:
                print(f"✗ Record not found after insertion")
                return False
                
    except Exception as e:
        print(f"✗ Database insertion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("INTELLIGENT PIPELINE ORCHESTRATOR - TEST SUITE")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Orchestrator Init", test_orchestrator_initialization),
        ("Latest Data Detection", test_latest_data_detection),
        ("Coverage Analysis", test_coverage_analysis),
        ("Missing Dates ID", test_missing_dates_identification),
        ("Forecast Generation", test_forecast_generation),
        ("Database Insertion", test_data_insertion),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:.<10} {test_name}")
    
    print("=" * 80)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

