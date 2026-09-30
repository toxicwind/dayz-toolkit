#!/usr/bin/env python3
import sys
import ftplib
from pathlib import Path

# Repo root
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings

settings = load_settings()

def fetch_be_config():
    print("=== FTP CONFIG SEARCH ===")
    ftp_host = settings.ftp_host
    ftp_port = settings.ftp_port
    ftp_user = settings.ftp_user
    ftp_pass = settings.ftp_password
    
    if not ftp_user or not ftp_pass:
        print("Error: Missing FTP credentials")
        return

    try:
        ftp = ftplib.FTP()
        print(f"Connecting to {ftp_host}:{ftp_port}...")
        ftp.connect(ftp_host, ftp_port)
        ftp.login(ftp_user, ftp_pass)
        print("Connected to FTP (RCON configs ignored in console build).")
        ftp.quit()

    except Exception as e:
        print(f"FTP Error: {e}")

if __name__ == "__main__":
    fetch_be_config()
