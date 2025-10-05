#!/usr/bin/env python3
"""
Test API and check marker data
"""
import requests

def test_api():
    try:
        r = requests.get('http://localhost:8000/api/stats/current')
        print(f'Status: {r.status_code}')
        
        if r.status_code == 200:
            data = r.json()
            print(f'Total records: {len(data)}')
            print('\nPM2.5 values:')
            
            for d in data[:10]:
                print(f'  Province {d["province_id"]}: {d["pm25"]:.1f} μg/m³ ({d["air_quality_category"]})')
            
            # Check alert levels
            print('\nAlert levels:')
            for d in data[:5]:
                pm25 = d["pm25"]
                if pm25 >= 50:
                    level = "extreme"
                elif pm25 >= 25:
                    level = "high"
                elif pm25 >= 15:
                    level = "moderate"
                elif pm25 >= 8:
                    level = "low"
                else:
                    level = "none"
                print(f'  Province {d["province_id"]}: {level} (PM2.5: {pm25:.1f})')
                
        else:
            print(f'Error: {r.status_code}')
            
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    test_api()
