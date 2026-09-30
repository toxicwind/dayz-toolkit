#!/usr/bin/env python3
"""Lint XML and JSON files in a directory.

Usage:
    python lint_configs.py <target_dir>

Exits with code 0 if all files are valid, otherwise prints errors and exits with 1.
"""

import json
import os
import sys
import xml.etree.ElementTree as ET


def lint_xml(path):
    try:
        ET.parse(path)
        return None
    except ET.ParseError as e:
        return f"XML parse error in {path}: {e}"


def lint_json(path):
    try:
        with open(path) as f:
            json.load(f)
        return None
    except json.JSONDecodeError as e:
        return f"JSON parse error in {path}: {e}"


def main():
    if len(sys.argv) != 2:
        print("Usage: lint_configs.py <directory>")
        sys.exit(1)
    root = sys.argv[1]
    errors = []
    # exclude archives and backups if they happen to be in the target tree (unlikely if target is well scoped)
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if f.lower().endswith(".xml"):
                err = lint_xml(fp)
                if err:
                    errors.append(err)
            elif f.lower().endswith(".json"):
                err = lint_json(fp)
                if err:
                    errors.append(err)
    if errors:
        print("Lint errors found:")
        for e in errors:
            print(e)
        sys.exit(1)
    else:
        print("All XML and JSON files are valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
