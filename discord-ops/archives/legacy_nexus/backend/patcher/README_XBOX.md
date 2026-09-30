# Xbox-only DayZ Mission Patcher (Tony/Goopsta rollup)

This patcher is **Xbox/Nitrado focused**: it only touches mission files the console server reads
(XML/JSON under `dayzOffline.chernarusplus/`). No mods. No workshop. No init.c reliance.

## What is enabled by default

### 1) Admin vehicle: Vehicle02Admin (event + position)
- Ensures `db/events.xml` contains event **Vehicle02Admin** with:
  - `saferadius=500`, `distanceradius=500`, `cleanupradius=200`
  - 1× child vehicle `Hatchback_02`
- Ensures `cfgeventspawns.xml` contains **Vehicle02Admin** at:
  - `x=10376.90 z=14214.80 a=63.438690`
- Removes legacy/mismatched admin-vehicle names if present:
  - `VehicleHatchback02Admin`
  - `VehicleAdminHatchback02`

### 2) Locked containers: StaticContainerLocked event definition (events.xml)
Upserts the **StaticContainerLocked** event definition (the Sakhal-style locked container event) so the server
can spawn locked containers using its own spawn-position system.

> Important: This patch **does not fabricate spawn positions**. It assumes your server already has spawn points
> configured (in `cfgeventspawns.xml`, eventposdefs, map groups, or whatever method your mission uses).
> The point of this patch is to fix the common "event exists in spawns but not in events.xml" failure.

### 3) Locked containers: nominal=0 type upserts (types.xml)
Upserts these types (nominal=0; event-controlled):
- `Land_ContainerLocked_Blue_DE`
- `Land_ContainerLocked_Orange_DE`
- `Land_ContainerLocked_Red_DE` (lifetime 14400, count_in_map=1)
- `Land_ContainerLocked_Yellow_DE`

### 4) Container keys: remove accidental “Military/Tier4” restrictions (types.xml)
Removes `usage Military` + `value Tier4` from any of these if present:
- `ShippingContainerKeys_*` (plural)
- `ShippingContainerKey_*` (singular)

### 5) Gameplay: stamina max = 100 (cfggameplay.json)
Sets `PlayerData.StaminaData.StaminaMax = 100.0`.

### 6) Globals: Goopsta/Tony counts (db/globals.xml)
- ZombieMaxCount = 1234
- AnimalMaxCount = 200
- LootDamageMin = 0.0
- LootDamageMax = 0.82

## Optional (OFF by default): Object Spawner placement
Two manifest entries are present but disabled:
- `xbox_lockedcontainers_copy_json` (raw_copy)
- `xbox_cfggameplay_enable_objectspawner_lockedcontainers` (json_ops)

Enable them only if you explicitly want **Object Spawner JSON** placement and you are not relying on the CE
event spawn system for containers (otherwise you can double-spawn).

These two patches:
- Copy `assets/custom/LockedContainers_Spawns.json` → `custom/LockedContainers_Spawns.json`
- Append `custom/LockedContainers_Spawns.json` to `WorldsData.objectSpawnersArr` **without clobbering** other entries

## Running it

### A) Patch YOUR real server mission (recommended)
1. FTP-download your server mission folder:
   - `dayzOffline.chernarusplus/`
2. Run:
   ```bash
   python3 patcher.py apply \
     --base /path/to/dayzOffline.chernarusplus \
     --manifest patches/manifest.json \
     --out /path/to/output_mission
   ```
3. Upload the **contents** of `output_mission/` back to the server (overwrite like-for-like).

### B) Patch the included baseline (local test)
This repo includes `base/dayzOffline.chernarusplus` so you can test locally:
```bash
python3 patcher.py apply --base base/dayzOffline.chernarusplus --manifest patches/manifest.json --out output_mission
```

## Verification checklist (Xbox/Nitrado)
- `db/events.xml` contains `<event name="Vehicle02Admin">` and `<event name="StaticContainerLocked">`
- `cfgeventspawns.xml` contains `<event name="Vehicle02Admin">` with the correct `<pos ... />`
- `db/types.xml` contains `Land_ContainerLocked_*_DE` entries with nominal=0
- `db/types.xml` container keys are not restricted to `usage Military` / `value Tier4`
- Restart server → verify admin car moved and containers/keys behavior matches expectations

Build date: 2026-01-05
