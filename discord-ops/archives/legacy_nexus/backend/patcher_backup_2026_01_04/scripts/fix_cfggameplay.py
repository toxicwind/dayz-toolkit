import json


def apply(staging_dir, repo_root):
    target_file = staging_dir / "cfggameplay.json"
    if not target_file.exists():
        return False

    with open(target_file) as f:
        data = json.load(f)

    changed = False

    # Remove junk empty key if it exists
    if "" in data:
        print("Removing empty root key junk from cfggameplay.json")
        data.pop("")
        # Optionally merge data from junk if it's newer?
        # For now, just discard if we have the main data.
        changed = True

    # Enforce Build Anywhere in top-level
    def set_recursive(obj, path, val):
        keys = path.split(".")
        curr = obj
        for k in keys[:-1]:
            if k not in curr:
                curr[k] = {}
            curr = curr[k]
        if curr.get(keys[-1]) != val:
            curr[keys[-1]] = val
            return True
        return False

    c_path = "BaseBuildingData.ConstructionData"
    changed |= set_recursive(data, f"{c_path}.disablePerformRoofCheck", True)
    changed |= set_recursive(data, f"{c_path}.disableIsCollidingCheck", True)
    changed |= set_recursive(data, f"{c_path}.disableDistanceCheck", True)

    h_path = "BaseBuildingData.HologramData"
    for k in [
        "disableIsCollidingBBoxCheck",
        "disableIsCollidingPlayerCheck",
        "disableIsClippingRoofCheck",
        "disableIsBaseViableCheck",
        "disableIsCollidingGPlotCheck",
        "disableIsCollidingAngleCheck",
        "disableIsPlacementPermittedCheck",
        "disableHeightPlacementCheck",
        "disableIsUnderwaterCheck",
        "disableIsInTerrainCheck",
    ]:
        changed |= set_recursive(data, f"{h_path}.{k}", True)

    if changed:
        with open(target_file, "w") as f:
            json.dump(data, f, indent=4)
        print("Applied cfggameplay structure fix")
        return True
    return False
