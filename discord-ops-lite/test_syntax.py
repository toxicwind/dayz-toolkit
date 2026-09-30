import sys
import os
sys.path.append(os.getcwd() + '/src')
from dayz_discord_ops.stat_channels import parse_stat_channels, StatChannelConfig
print("Import successful")
try:
    cfg = parse_stat_channels("INVALID JSON")
    print("Handled invalid JSON")
except Exception as e:
    print(f"Failed to handle invalid JSON: {e}")
