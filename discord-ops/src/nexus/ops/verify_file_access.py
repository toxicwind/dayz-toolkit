#!/usr/bin/env python3
import sys
import ftplib
import re
from pathlib import Path

# Repo root
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings

settings = load_settings()

def verify_access():
    print("=== FTP FILE ACCESS VERIFICATION ===")
    ftp_host = settings.ftp_host
    ftp_port = settings.ftp_port
    ftp_user = settings.ftp_user
    ftp_pass = settings.ftp_password

    if not ftp_user or not ftp_pass:
        print("Error: Missing FTP credentials")
        return

    try:
        ftp = ftplib.FTP()
        ftp.connect(ftp_host, ftp_port)
        ftp.login(ftp_user, ftp_pass)
        print("Connected to FTP.")
        
        # 1. Verify Config (Did our write persist?)
        config_path = "dayzxb/config/BEServer_x64.cfg"
        print(f"\n[1] Checking {config_path}...")
        try:
            local_path = repo_root / "verify_config.cfg"
            with open(local_path, "wb") as f:
                ftp.retrbinary(f"RETR {config_path}", f.write)
            
            with open(local_path, "r") as f:
                content = f.read()
                print("--- CONTENT START ---")
                print(content.strip())
                print("--- CONTENT END ---")
                
                if "RConPort = 2305" in content:
                    print("SUCCESS: RCON Port 2305 configured confirmed.")
                else:
                    print("WARNING: RConPort setting not found or mismatch.")
        except Exception as e:
            print(f"FAILED to read config: {e}")

        # 2. Verify Log Access (.ADM)
        print(f"\n[2] Finding latest .ADM log in dayzxb/config...")
        ftp.cwd("dayzxb/config")
        files = ftp.nlst()
        adm_files = sorted([f for f in files if f.endswith(".ADM")])
        
        if adm_files:
            latest_adm = adm_files[-1]
            print(f"Latest ADM: {latest_adm}")
            
            local_log = repo_root / "verify_log.adm"
            try:
                with open(local_log, "wb") as f:
                    ftp.retrbinary(f"RETR {latest_adm}", f.write)
                
                with open(local_log, "r", encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    print(f"Read {len(lines)} lines.")
                    print("Last 5 lines:")
                    for line in lines[-5:]:
                        print(f"  {line.strip()}")
                print("SUCCESS: Log file downloaded and read.")
            except Exception as e:
                print(f"FAILED to download/read log: {e}")
        else:
            print("WARNING: No .ADM files found.")

        ftp.quit()

    except Exception as e:
        print(f"FTP Error: {e}")

if __name__ == "__main__":
    verify_access()
