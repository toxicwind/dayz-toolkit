import requests
import os
import subprocess
import sys
from pathlib import Path

def clone_all(username, out_dir):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    page = 1
    repos = []
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        print(f"Fetching page {page}...")
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Error: {resp.status_code} {resp.text}")
            break
            
        page_data = resp.json()
        if not page_data:
            break
            
        repos.extend(page_data)
        page += 1
        
    print(f"Found {len(repos)} repositories.")
    
    for repo in repos:
        name = repo['name']
        clone_url = repo['clone_url']
        target_dir = out_path / name
        
        if target_dir.exists():
            print(f"Skipping {name} (already exists)")
            continue
            
        print(f"Cloning {name}...")
        subprocess.run(["git", "clone", clone_url, str(target_dir)], check=False)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 clone_all.py <username> <out_dir>")
        sys.exit(1)
        
    clone_all(sys.argv[1], sys.argv[2])
