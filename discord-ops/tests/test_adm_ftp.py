#!/usr/bin/env python3
"""
Test script to download and parse ADM logs via FTP
"""
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'src'))

from dayz_discord_ops.ftp_client import FTPClient
from dayz_discord_ops.adm_log_parser import ADMLogParser

# Hardcoded FTP credentials from .env
host = "usla352.gamedata.io"
port = 21
user = "ni12435433_1"
passwd = "REDACTED"

print(f"Connecting to FTP: {host}")
client = FTPClient(host, port, user, passwd)

if client.connect():
    print("Connected successfully!")
    
    # Try to read an ADM log
    # From earlier FTP audit, we know logs aren't accessible via FTP
    # But let's try the path from Nitrado API
    log_path = "/dayzxb/config/DayZServer_X1_x64_2025-12-22_00-33-29.ADM"
    
    print(f"Attempting to read: {log_path}")
    content = client.read_file(log_path)
    
    if content:
        print(f"Successfully read {len(content)} bytes")
        print("\n--- First 500 chars ---")
        print(content[:500])
        
        # Parse it
        parser = ADMLogParser()
        events = parser.parse_log_content(content)
        print(f"\n--- Parsed {len(events)} events ---")
        for event in events[:5]:
            print(f"{event['timestamp']} - {event['gamertag']} - {event['event_type']}")
    else:
        print("Failed to read file via FTP")
    
    client._close()
else:
    print("Failed to connect")
