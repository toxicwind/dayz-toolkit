```python
import os
import sys
import requests
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings

settings = load_settings()
TOKEN = settings.nitrado_token
SERVICE_ID = settings.nitrado_service_id

def list_files(directory="/"):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    
    url = f"https://api.nitrado.net/services/{SERVICE_ID}/gameservers/file_server/list"
    params = {"dir": directory}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            entries = data.get("data", {}).get("entries", [])
            print(f"Directory: {directory}")
            for entry in entries:
                type_str = "DIR " if entry['is_directory'] else "FILE"
                print(f"{type_str} {entry['name']} (Size: {entry.get('size', 0)})")
                
                # If we find "config" or "profile" or "logs", let's note them
                if entry['name'].lower() in ["config", "profile", "logs", "dayzxb"]:
                    print(f">>> Potential Log Directory Found: {entry['name']}")
        else:
            print(f"API Error: {data.get('message')}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    service_id = "18302446"
    # Root
    list_files(service_id, "/")
    # Try common subdirs if root is empty or just has a main folder
    # Based on FTP audit earlier, we saw 'dayzxb_missions'
    # But often logs are in a sibling to mpmissions
    
