import requests
import json
import time

BASE_URL = "http://localhost:8081"

def test_patching():
    print("1. Fetching current globals...")
    res = requests.get(f"{BASE_URL}/config/globals")
    if res.status_code != 200:
        print(f"Failed to fetch globals: {res.text}")
        return
    
    current = res.json()['globals']
    print(f"Current ZombieMaxCount: {current.get('ZombieMaxCount')}")
    
    print("\n2. Updating ZombieMaxCount to 1234...")
    res = requests.post(f"{BASE_URL}/config/globals", json={"ZombieMaxCount": 1234})
    print(f"Update response: {res.json()}")
    
    print("\n3. Verifying update...")
    res = requests.get(f"{BASE_URL}/config/globals")
    new_val = res.json()['globals'].get('ZombieMaxCount')
    print(f"New ZombieMaxCount: {new_val}")
    
    if new_val == 1234:
        print("SUCCESS: API reflected the change.")
    else:
        print("FAILURE: API did not reflect the change.")

if __name__ == "__main__":
    try:
        test_patching()
    except Exception as e:
        print(f"Test failed: {e}")
