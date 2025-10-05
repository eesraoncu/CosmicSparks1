#!/usr/bin/env python3
"""
Simple API test
"""
import requests
import time

def test_api():
    # Wait for backend to start
    for i in range(10):
        try:
            r = requests.get('http://127.0.0.1:8000/api/stats/current', timeout=5)
            print(f'Status: {r.status_code}')
            
            if r.status_code == 200:
                data = r.json()
                print(f'Total records: {len(data)}')
                
                if len(data) > 0:
                    print(f'First record PM2.5: {data[0]["pm25"]:.1f} μg/m³')
                    print(f'First record Air Quality: {data[0]["air_quality_category"]}')
                    
                    # Check alert levels
                    print('\nAlert levels (first 5):')
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
                    print('No data returned')
                return True
            else:
                print(f'Error: {r.status_code}')
                
        except requests.exceptions.ConnectionError:
            print(f'Attempt {i+1}: Backend not ready, waiting...')
            time.sleep(2)
        except Exception as e:
            print(f'Error: {e}')
            break
    
    print('Backend failed to start')
    return False

if __name__ == "__main__":
    test_api()
