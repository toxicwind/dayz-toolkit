#!/usr/bin/env python3
import json
import shutil
from pathlib import Path

from lxml import etree

baseline_root = Path(
    "/home/toxic/dayz_workspace/dayz_discord_ops_repo/staging/baselines/dz_128/dayzOffline.chernarusplus"
)
tony_root = Path("/home/toxic/dayz_workspace/backup_orig_tony/dayzxb_missions/dayzOffline.chernarusplus")
output_dir = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo/backend/patcher/patches/tony_128")


def harvest_json(rel_path):
    print(f"Harvesting JSON: {rel_path}")
    baseline_root / rel_path
    tony_file = tony_root / rel_path

    # Using simple Deep Merge proxy (since the applicator uses it)
    with open(tony_file) as f:
        tony_data = json.load(f)

    patch = {
        "id": f"tony_{rel_path.stem}",
        "target": str(rel_path),
        "path": "",  # Root
        "values": tony_data,
        "enabled": True,
    }

    dest = output_dir / rel_path.with_suffix(".json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w") as f:
        json.dump(patch, f, indent=4)


def harvest_xml(rel_path):
    print(f"Harvesting XML: {rel_path}")
    baseline_root / rel_path
    tony_file = tony_root / rel_path

    parser = etree.XMLParser(remove_blank_text=True)
    tony_tree = etree.parse(str(tony_file), parser)

    # Convention: put all nodes in _data.xml for replacement
    patch = {"id": f"tony_{rel_path.stem}", "target": str(rel_path), "type": "xml_patch", "enabled": True}

    dest = output_dir / rel_path.with_suffix(".json")
    data_dest = output_dir / rel_path.with_name(rel_path.stem + "_data.xml")

    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w") as f:
        json.dump(patch, f, indent=4)

    tony_tree.write(str(data_dest), pretty_print=True, xml_declaration=True, encoding="utf-8")


def harvest_raw(rel_path):
    print(f"Harvesting RAW: {rel_path}")
    tony_file = tony_root / rel_path
    dest = output_dir / rel_path
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tony_file, dest)


if __name__ == "__main__":
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Gameplay
    harvest_json(Path("cfggameplay.json"))

    # 2. Economy & World (XML replacements)
    xml_files = [
        "cfgspawnabletypes.xml",
        "cfgweather.xml",
        "db/events.xml",
        "db/globals.xml",
        "db/messages.xml",
        "mapgroupproto.xml",
        "mapgroupdirt.xml",
        "mapclusterproto.xml",
        "cfglimitsdefinitionuser.xml",
    ]
    for f in xml_files:
        if (tony_root / f).exists():
            harvest_xml(Path(f))

    # 3. Territories (XML replacements)
    env_dir = tony_root / "env"
    if env_dir.exists():
        for f in env_dir.glob("*.xml"):
            harvest_xml(Path("env") / f.name)

    # 4. Added Structures
    custom_dir = tony_root / "custom"
    if custom_dir.exists():
        for f in custom_dir.glob("*"):
            harvest_raw(Path("custom") / f.name)

    # 5. Core files (init.c)
    if (tony_root / "init.c").exists():
        harvest_raw(Path("init.c"))

    print(f"Harvest complete. Patches in {output_dir}")
