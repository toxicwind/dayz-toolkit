#!/usr/bin/env python3
"""
Thin wrapper around tools.ftp_ops.dump_tree for backwards compatibility.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.ftp_ops.dump_tree import cli

if __name__ == "__main__":
    cli()
