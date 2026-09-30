import time
import requests
import subprocess
import logging

# MildlyAwesome Watchdog - Autonomous Self-Healing Sentinel
# Deployed to mildlyawesome.com to monitor 43200/43201

logging.basicConfig(
    filename='/var/log/mildlyawesome_watchdog.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

TARGETS = [
    {"name": "Bot API", "url": "http://localhost:43200/health", "expected": 200},
    {"name": "Dashboard", "url": "http://localhost:43201/dashboard", "expected": 307} # or 200 if authed
]

def check_health():
    for target in TARGETS:
        try:
            r = requests.get(target["url"], timeout=5, allow_redirects=False)
            if r.status_code == target["expected"] or (target["name"] == "Dashboard" and r.status_code in [200, 307]):
                # logging.info(f"{target['name']} OK [{r.status_code}]")
                pass
            else:
                logging.error(f"{target['name']} UNHEALTHY: {r.status_code}")
                return False
        except Exception as e:
            logging.error(f"{target['name']} FAILED: {e}")
            return False
    return True

def heal():
    logging.warning("🏥 INITIATING SELF-HEALING PROTOCOL...")
    try:
        # Restart the specific stack services
        subprocess.run(["docker", "service", "update", "--force", "dayz-ezstreet-ops-43200_dashboard"], check=True)
        subprocess.run(["docker", "service", "update", "--force", "dayz-ezstreet-ops-43200_bot"], check=True)
        logging.info("✅ Stack restarted.")
    except Exception as e:
        logging.error(f"❌ HEALING FAILED: {e}")

if __name__ == "__main__":
    logging.info("🤖 MildlyAwesome Watchdog Started.")
    while True:
        if not check_health():
            heal()
            time.sleep(60) # Cooldown after heal
        time.sleep(10)
