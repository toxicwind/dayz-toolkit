#!/usr/bin/env python3
import json
import sys
from pathlib import Path

import jsonpatch


def generate_json_patch(baseline_path: Path, target_path: Path):
    with open(baseline_path) as f:
        base = json.load(f)
    with open(target_path) as f:
        target = json.load(f)

    patch = jsonpatch.make_patch(base, target)
    return patch.patch


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: generate_json_patch.py <baseline> <target>")
        sys.exit(1)

    p = generate_json_patch(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(p, indent=4))
