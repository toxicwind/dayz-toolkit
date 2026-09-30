#!/usr/bin/env python3
"""
PORTFORGE_43200: Aggressive port rewriter for DayZ Discord Ops
Eliminates 35xxx/37xxx contamination and normalizes to 43200-43249 range.
"""
import re
import sys
from pathlib import Path
from typing import Dict, List

# Port mapping: old -> new
PORT_MAP = {
    "35120": "43200",  # Bot API
    "35121": "43201",  # Dashboard
    "37100": "43210",  # Reserved
    "37200": "43220",  # Reserved
}

# Files to rewrite (aggressive glob patterns)
TARGET_PATTERNS = [
    "docker-compose.yml",
    "scripts/**/*.sh",
    "src/**/*.py",
    "dashboard/**/*.json",
    "dashboard/**/*.js",
    "dashboard/**/*.ts",
    "dashboard/**/*.tsx",
    ".env*",
    "*.md",
]

# Exclude patterns
EXCLUDE_PATTERNS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/cfgeventspawns.xml",  # Coordinate files
    "**/trader_items*.csv",   # Price data
    "**/SOURCE_INDEX.json",   # File metadata
]

def should_process(file_path: Path, repo_root: Path) -> bool:
    """Check if file should be processed."""
    rel_path = str(file_path.relative_to(repo_root))
    
    # Exclude patterns
    for pattern in EXCLUDE_PATTERNS:
        if file_path.match(pattern):
            return False
    
    # Check if it matches any target pattern
    for pattern in TARGET_PATTERNS:
        if file_path.match(pattern):
            return True
    
    return False

def rewrite_ports(content: str, port_map: Dict[str, str]) -> tuple[str, int]:
    """Rewrite ports in content. Returns (new_content, num_replacements)."""
    new_content = content
    total_replacements = 0
    
    for old_port, new_port in port_map.items():
        # Match port in various contexts
        patterns = [
            (rf'\b{old_port}\b', new_port),  # Standalone
            (rf':{old_port}\b', f':{new_port}'),  # After colon
            (rf'localhost:{old_port}', f'localhost:{new_port}'),
            (rf'0\.0\.0\.0:{old_port}', f'0.0.0.0:{new_port}'),
        ]
        
        for pattern, replacement in patterns:
            new_content, count = re.subn(pattern, replacement, new_content)
            total_replacements += count
    
    return new_content, total_replacements

def main(repo_root: str, base_port: int = 43200):
    """Execute port forge."""
    root = Path(repo_root).resolve()
    
    if not root.exists():
        print(f"ERROR: Repo root not found: {root}")
        sys.exit(1)
    
    print(f"🔨 PORTFORGE_43200 starting at {root}")
    print(f"   Base port: {base_port}")
    print(f"   Port map: {PORT_MAP}")
    
    changed_files = []
    total_replacements = 0
    
    # Find all files
    all_files = []
    for pattern in TARGET_PATTERNS:
        all_files.extend(root.glob(pattern))
    
    # Process each file
    for file_path in all_files:
        if not file_path.is_file():
            continue
        
        if not should_process(file_path, root):
            continue
        
        try:
            # Read file
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            
            # Rewrite ports
            new_content, replacements = rewrite_ports(content, PORT_MAP)
            
            if replacements > 0:
                # Write back
                file_path.write_text(new_content, encoding='utf-8')
                changed_files.append(str(file_path.relative_to(root)))
                total_replacements += replacements
                print(f"   ✓ {file_path.relative_to(root)}: {replacements} replacements")
        
        except Exception as e:
            print(f"   ✗ {file_path.relative_to(root)}: {e}")
    
    print(f"\n✅ PORTFORGE complete:")
    print(f"   Files changed: {len(changed_files)}")
    print(f"   Total replacements: {total_replacements}")
    
    # Write report
    report_path = root / "logs" / "portforge_report_43200.json"
    report_path.parent.mkdir(exist_ok=True)
    
    import json
    report = {
        "port_map": PORT_MAP,
        "files_changed": changed_files,
        "total_replacements": total_replacements,
    }
    report_path.write_text(json.dumps(report, indent=2))
    print(f"   Report: {report_path}")

if __name__ == "__main__":
    from src.mildlyawesome.config import get_settings
    main(str(get_settings().chronos_root), 43200)
