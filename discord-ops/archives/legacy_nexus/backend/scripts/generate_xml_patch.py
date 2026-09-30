#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from lxml import etree


def get_element_id(elem):
    """DayZ-specific: elements usually have a 'name' attribute."""
    return elem.get("name")


def generate_xml_patch(baseline_path: Path, target_path: Path):
    parser = etree.XMLParser(remove_blank_text=True)
    base_tree = etree.parse(str(baseline_path), parser)
    target_tree = etree.parse(str(target_path), parser)

    base_root = base_tree.getroot()
    target_root = target_tree.getroot()

    # Simple semantic diff for DayZ: children of root by name
    base_map = {get_element_id(c): c for c in base_root if get_element_id(c)}
    target_map = {get_element_id(c): c for c in target_root if get_element_id(c)}

    patches = []

    # Modifications and Additions
    for name, target_elem in target_map.items():
        if name in base_map:
            # Check if identical
            if etree.tostring(target_elem) != etree.tostring(base_map[name]):
                patches.append(
                    {
                        "op": "replace",
                        "path": f"/*[@name='{name}']",
                        "value": etree.tostring(target_elem, encoding="unicode"),
                    }
                )
        else:
            patches.append({"op": "add", "path": "/*", "value": etree.tostring(target_elem, encoding="unicode")})

    # Deletions (Rarely recommended for DayZ, usually set nominal to 0)
    for name in base_map:
        if name not in target_map:
            patches.append({"op": "remove", "path": f"/*[@name='{name}']"})

    return patches


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: generate_xml_patch.py <baseline> <target>")
        sys.exit(1)

    p = generate_xml_patch(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(p, indent=4))
