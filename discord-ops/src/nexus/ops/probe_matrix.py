#!/usr/bin/env python3
import socket
import time
import sys
import struct
import binascii
from datetime import datetime
from pathlib import Path

# Repo root
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from bot.config import load_settings

class ProbeMatrix:
    def __init__(self):
        self.settings = load_settings()
        self.host = self.settings.dayz_host
        self.proof_file = repo_root / f"logs/proof/probe_matrix_{int(time.time())}.txt"
        self.proof_file.parent.mkdir(exist_ok=True, parents=True)
        self.log_buffer = []

    def log(self, msg):
        print(msg)
        self.log_buffer.append(msg)

    def save_proof(self):
        with open(self.proof_file, "w") as f:
            f.write("\n".join(self.log_buffer))
        print(f"\nProof saved to: {self.proof_file}")

    def probe_a2s(self, port, timeout=2.0) -> str:
        """Sends A2S_INFO (TSource Engine Query)"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        # A2S_INFO Request: FF FF FF FF 54 53 6F 75 72 63 65 20 45 6E 67 69 6E 65 20 51 75 65 72 79 00
        payload = b'\xFF\xFF\xFF\xFFTSource Engine Query\x00'
        
        try:
            sock.sendto(payload, (self.host, port))
            data, _ = sock.recvfrom(4096)
            hex_data = binascii.hexlify(data).decode('utf-8')
            
            if data.startswith(b'\xFF\xFF\xFF\xFF\x49'): # 'I' for Info Response
                return f"SUCCESS (A2S Response) | Hex: {hex_data[:32]}..."
            elif data.startswith(b'\xFF\xFF\xFF\xFF'):
                return f"PARTIAL (A2S Header) | Hex: {hex_data[:32]}..."
            else:
                return f"UNKNOWN_DATA | Hex: {hex_data[:32]}..."
        except socket.timeout:
            return "TIMEOUT"
        except Exception as e:
            return f"ERROR: {e}"
        finally:
            sock.close()

    def run(self):
        self.log(f"=== PROBE MATRIX: {self.host} ===")
        self.log(f"Timestamp: {datetime.now().isoformat()}")
        self.log(f"Config Query Port: {self.settings.dayz_query_port}")
        
        # Ports to scan: Configured ports + standard range + documented Nitrado offsets
        scan_ports = sorted(list(set([
            self.settings.dayz_query_port,
            11603, # Known Nitrado Default
            11604,
            2302, 2303, 2304, 2305
        ])))
        
        results = []
        
        self.log("\n{:<10} | {:<30} | {:<40}".format("PORT", "TEST: A2S (QUERY)", "TEST: RESERVED"))
        self.log("-" * 85)
        
        for port in scan_ports:
            res_a2s = self.probe_a2s(port)
            res_be = "DISABLED"
            
            classification = "CLOSED/UNKNOWN"
            if "SUCCESS (A2S" in res_a2s:
                classification = "QUERY (A2S)"
                
            row = "{:<10} | {:<30} | {:<40}".format(port, res_a2s.split('|')[0].strip(), res_be)
            self.log(row)
            results.append((port, classification, res_a2s, res_be))
            
        self.log("\n=== CLASSIFICATION VERDICT ===")
        for port, cls, _, _ in results:
            if cls != "CLOSED/UNKNOWN":
                self.log(f"PORT {port}: {cls}")
            
            if cls == "RCON (BattlEye)":
                self.log(f"!!! FOUND VALID RCON ON PORT {port} !!!")
                
        self.save_proof()

if __name__ == "__main__":
    matrix = ProbeMatrix()
    matrix.run()
