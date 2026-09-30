
import os
import sys
import subprocess

os.environ["ENABLE_SELFPLAY"] = "true"
print("Launching bot with ENABLE_SELFPLAY=true...")
with open("logs/bot_stdout.log", "w") as f:
    subprocess.run([sys.executable, "-m", "src.mildlyawesome.bot"], stdout=f, stderr=subprocess.STDOUT)
