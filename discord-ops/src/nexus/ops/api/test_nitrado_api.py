import os
import requests
import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings

settings = load_settings()
TOKEN = settings.nitrado_token

def list_services():
    token = TOKEN
    if not token:
        print("Error: NITRADO_API_TOKEN not found in settings.")
        return

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = "https://api.nitrado.net/services"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            services = data.get("data", {}).get("services", [])
            print(f"Found {len(services)} services.")
            for svc in services:
                print(f"Service ID: {svc['id']}")
                print(f"Small Info: {svc.get('details', {}).get('name')}")
                print(f"Type: {svc['type']}")
                print(f"Status: {svc['status']}")
                print("-" * 20)
        else:
            print(f"API Error: {data.get('message')}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    list_services()
