import requests
import json

BASE_URL = "http://localhost:8081"

def test_gameplay_patch():
    print("1. Fetching current gameplay...")
    res = requests.get(f"{BASE_URL}/config/gameplay")
    if res.status_code != 200:
        print(f"Failed to fetch gameplay: {res.text}")
        return
    
    current = res.json().get('gameplay', {})
    print(f"Current staminaMax: {current.get('staminaMax')}")
    print(f"Current disableBaseDamage: {current.get('disableBaseDamage')}")
    
    print("\n2. Updating Gameplay (Stamina 123.0, BaseDamage True)...")
    res = requests.post(f"{BASE_URL}/config/gameplay", json={
        "staminaMax": 123.0,
        "disableBaseDamage": True
    })
    print(f"Update response: {res.json()}")
    
    print("\n3. Verifying update...")
    res = requests.get(f"{BASE_URL}/config/gameplay")
    new_data = res.json().get('gameplay', {})
    print(f"New staminaMax: {new_data.get('staminaMax')}")
    print(f"New disableBaseDamage: {new_data.get('disableBaseDamage')}")
    
    if new_data.get('staminaMax') == 123.0:
        print("SUCCESS: Stamina Updated")
    else:
        print("FAILURE: Stamina Not Updated")
        
    # Note: disableBaseDamage mapping in 'get_gameplay' might still be TBD/wrong in my previous implementation?
    # Let's check get_gameplay logic logic if it reads from GeneralData?
    

if __name__ == "__main__":
    try:
        test_gameplay_patch()
    except Exception as e:
        print(f"Test failed: {e}")
