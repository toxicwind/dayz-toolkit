import os
import re
import sys
from pathlib import Path

# Config
ROOT_DIR = Path(".").resolve()
CHRONOS_DIR = ROOT_DIR / ".chronos"
INBOX_DIR = CHRONOS_DIR / "inbox"
SNAPSHOT_FILE = INBOX_DIR / "bruteforce_snapshot.txt"

# Regex
DISCORD_ID_REGEX = re.compile(r"\b[0-9]{17,19}\b")
PATH_REGEX = re.compile(r"/home/toxic/")
TODO_REGEX = re.compile(r"(TODO|FIXME)")

def setup_dirs():
    for d in ["inbox", "outbox", "artifacts", "locks", "tasks", "plans", "repos"]:
        (CHRONOS_DIR / d).mkdir(parents=True, exist_ok=True)

def audit_file(filepath):
    results = {
        "ids": [],
        "paths": [],
        "todos": []
    }
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if "channel_state.json" in str(filepath): continue
                if "channel_spec.json" in str(filepath): continue
                
                # Check IDs
                for match in DISCORD_ID_REGEX.findall(line):
                    results["ids"].append(f"{filepath}:{i}: {match}")
                
                # Check Paths
                if PATH_REGEX.search(line):
                    results["paths"].append(f"{filepath}:{i}: {line.strip()}")
                
                # Check TODOs
                if TODO_REGEX.search(line):
                    results["todos"].append(f"{filepath}:{i}: {line.strip()}")
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return results

def main():
    setup_dirs()
    
    with open(SNAPSHOT_FILE, "w") as out:
        out.write("--- CHRONOS BRUTE FORCE SNAPSHOT ---\n")
        
        # 1. Topology
        out.write("\n--- TOPOLOGY ---\n")
        file_list = []
        for root, dirs, files in os.walk(ROOT_DIR):
            if ".git" in dirs: dirs.remove(".git")
            if "venv" in dirs: dirs.remove("venv")
            if "node_modules" in dirs: dirs.remove("node_modules")
            if ".chronos" in dirs: dirs.remove(".chronos")
            
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR)
                out.write(f"{rel_path}\n")
                if full_path.suffix in [".py", ".json", ".yaml", ".sh", ".md"]:
                     file_list.append(full_path)

        # 2. Scan Content
        all_ids = []
        all_paths = []
        all_todos = []
        
        for f in file_list:
            res = audit_file(f)
            all_ids.extend(res["ids"])
            all_paths.extend(res["paths"])
            all_todos.extend(res["todos"])
            
        out.write("\n--- HARDCODED IDS ---\n")
        for x in sorted(all_ids): out.write(f"{x}\n")
            
        out.write("\n--- HARDCODED PATHS ---\n")
        for x in sorted(all_paths): out.write(f"{x}\n")
            
        out.write("\n--- TODOs & FIXMEs ---\n")
        for x in sorted(all_todos): out.write(f"{x}\n")

    print(f"Snapshot written to {SNAPSHOT_FILE}")

if __name__ == "__main__":
    main()
