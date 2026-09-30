import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def get_gameserver_info(service_id):
    token = os.getenv("NITRADO_API_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    
    url = f"https://api.nitrado.net/services/{service_id}/gameservers"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            print(json.dumps(data, indent=2))
        else:
            print(f"API Error: {data.get('message')}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    service_id = "18302446"
    get_gameserver_info(service_id)
