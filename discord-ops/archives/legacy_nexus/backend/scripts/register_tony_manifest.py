#!/usr/bin/env python3
import json
from pathlib import Path

repo_root = Path("/home/toxic/dayz_workspace/dayz_discord_ops_repo")
manifest_path = repo_root / "backend" / "patcher" / "patches" / "manifest.json"
tony_dir = repo_root / "backend" / "patcher" / "patches" / "tony_128"

with open(manifest_path) as f:
    manifest = json.load(f)

# Clear existing tony_128 to avoid duplicates
manifest["patches"] = [p for p in manifest["patches"] if p.get("category") != "tony_128"]

tony_patches = []

# Order matters: JSON patches first, then XML, then RAW
# Actually we'll just follow a logical flow

files = list(tony_dir.rglob("*"))
for f in files:
    if f.is_dir():
        continue
    if "_data.xml" in f.name:
        continue
    if f.suffix == ".patch":
        continue  # Skip raw diffs

    rel = f.relative_to(tony_dir)
    category = "tony_128"

    if f.suffix == ".json":
        # Check if it's a JSON patch
        with open(f) as jf:
            data = json.load(jf)
            if "target" in data:
                tony_patches.append(
                    {
                        "file": f"tony_128/{rel}",
                        "enabled": True,
                        "category": category,
                        "description": f"Tony's customization for {data['target']}",
                    }
                )
    elif f.suffix in [".xml", ".c", ".map", ".json"]:  # The inner .json in custom/ are raw copies
        # If it wasn't caught by the JSON check (e.g. in custom/) it's a raw copy
        # Create a JSON wrapper
        wrapper_rel = rel.with_suffix(rel.suffix + ".json")
        wrapper_abs = tony_dir / wrapper_rel
        wrapper_abs.parent.mkdir(parents=True, exist_ok=True)

        target = str(rel)
        if rel.name == "init.c":
            target = "init.c"

        wrapper_data = {
            "id": f"tony_raw_{rel.stem}",
            "type": "raw_copy",
            "source": str(Path("backend/patcher/patches/tony_128") / rel),
            "target": target,
            "enabled": True,
        }
        with open(wrapper_abs, "w") as wf:
            json.dump(wrapper_data, wf, indent=4)

        tony_patches.append({"file": f"tony_128/{wrapper_rel}", "enabled": True, "category": category})

manifest["patches"].extend(tony_patches)

with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=4)

print(f"Registered {len(tony_patches)} Tony patches in manifest.json")
