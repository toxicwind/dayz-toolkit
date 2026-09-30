import sys
import os

# Ensure we can import from src
sys.path.append(os.path.join(os.getcwd(), 'src'))

from dayz_discord_ops.ftp_client import FTPClient

def test_ftp():
    host = "usla352.gamedata.io"
    port = 21
    user = "ni12435433_1"
    passwd = "REDACTED"
    
    client = FTPClient(host, port, user, passwd)
    
    if client.connect():
        print("SUCCESS: Connected.")
        print("Reading /restart.log...")
        content = client.read_file("/restart.log")
        if content:
            print("--- LOG START ---")
            print(content)
            print("--- LOG END ---")
        else:
            print("Failed to read log.")
        client._close()

if __name__ == "__main__":
    test_ftp()
