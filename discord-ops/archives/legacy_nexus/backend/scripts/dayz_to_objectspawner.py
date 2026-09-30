#!/usr/bin/env python3
"""
DayZ to ObjectSpawner Converter
Converts Editor-style JSON exports (pos/ypr/scale) into standard
Vanilla ObjectSpawner JSON format.

Physics Invariants:
1. Output is always {"Objects": [...]}
2. Positions are always absolute [x, y, z].
3. Rotations are always [yaw, pitch, roll].
"""

import argparse
import json
import sys
from pathlib import Path


def convert(input_path: Path, output_path: Path):
    if not input_path.exists():
        print(f"Error: Input file {input_path} not found.")
        sys.exit(1)

    try:
        data = json.loads(input_path.read_text())
    except Exception as e:
        print(f"Error: Failed to parse input JSON: {e}")
        sys.exit(1)

    # Handle both {"Objects": [...]} and raw array formats
    raw_objects = data.get("Objects", []) if isinstance(data, dict) else data

    if not isinstance(raw_objects, list):
        print("Error: Input JSON must contain an array of objects.")
        sys.exit(1)

    standardized_objects = []
    for obj in raw_objects:
        # Standardize keys to lowercase/canonical
        clean_obj = {
            "name": obj.get("name", obj.get("type", "Unknown")),
            "pos": obj.get("pos", [0, 0, 0]),
            "ypr": obj.get("ypr", [0, 0, 0]),
        }

        # Ensure floats and rounding for cleanliness
        clean_obj["pos"] = [round(float(v), 4) for v in clean_obj["pos"]]
        clean_obj["ypr"] = [round(float(v), 4) for v in clean_obj["ypr"]]

        standardized_objects.append(clean_obj)

    output_data = {"Objects": standardized_objects}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_data, indent=4))
    print(f"OK: Converted {len(standardized_objects)} objects to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert DayZ Editor exports to Vanilla ObjectSpawner format.")
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("output", help="Output JSON file")
    args = parser.parse_args()

    convert(Path(args.input), Path(args.output))


if __name__ == "__main__":
    main()
