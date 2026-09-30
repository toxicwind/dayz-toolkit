#!/usr/bin/env python3
import sys
import os
import json
import time
import socket
import logging
from ftplib import FTP_TLS, FTP
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("probe")

try:
    from bot.config import load_settings
    from bot.a2s_query import query_info
except ImportError as e:
    print(json.dumps({"error": f"Import failed: {e}", "status": "critical_fail"}))
    sys.exit(1)

# Load settings globally
settings = load_settings()

def run_probe():
    results = {
        "timestamp": time.time(),
        "config_loaded": False,
        "effective_config": {},
        "probes": {}
    }

    # 1. Load Config
    try:
        settings = load_settings()
        results["config_loaded"] = True
        
        # Capture effective config (redacted)
        results["effective_config"] = {
            "s_id": settings.nitrado_service_id,
            "ftp_host": settings.ftp_host,
            "ftp_user": settings.ftp_user,
            "ftp_has_pass": bool(settings.ftp_password),
            "query_port": settings.dayz_query_port
        }
    except Exception as e:
        results["error_loading_config"] = str(e)
        print(json.dumps(results, indent=2))
        return

    # 2. Probe FTP
    ftp_res = {"status": "untried", "details": []}
    try:
        # Try TLS first
        ftps = FTP_TLS()
        ftps.timeout = 2.5
        ftps.connect(settings.ftp_host, settings.ftp_port)
        ftps.login(settings.ftp_user, settings.ftp_password)
        ftps.prot_p()
        
        ftp_res["status"] = "connected_tls"
        files = ftps.nlst()
        ftp_res["root_listing"] = files[:10] # Cap listing
        
        # Check specific paths
        for target in ["dayzxb_missions", "dayz_missions", "config", "battleye"]:
             if target in files:
                ftp_res["details"].append(f"Found {target}")
                try:
                    sub = ftps.nlst(target)
                    ftp_res[f"{target}_listing"] = sub[:5]
                except:
                    ftp_res["details"].append(f"Could not list {target}")
    except Exception as e:
        ftp_res["status"] = "failed"
        ftp_res["error"] = str(e)
    
    results["probes"]["ftp"] = ftp_res

    # 3. Probe A2S
    a2s_res = {"status": "untried"}
    try:
        # Simple socket test first
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.5)
        
        # A2S_INFO query: FF FF FF FF 54 "Source Engine Query" 00
        packet = b"\xff\xff\xff\xff\x54Source Engine Query\x00"
        sock.sendto(packet, (settings.dayz_host, settings.dayz_query_port))
        data, addr = sock.recvfrom(4096)
        a2s_res["status"] = "success"
        a2s_res["response_len"] = len(data)
        a2s_res["header"] = data[:5].hex()
    except Exception as e:
        a2s_res["status"] = "failed"
        a2s_res["error"] = str(e)
    results["probes"]["a2s"] = a2s_res

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_probe()
