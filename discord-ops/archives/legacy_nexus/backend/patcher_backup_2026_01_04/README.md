# Patcher (centralized DayZ config toggles)

This folder is the single source of truth for feature patches. Each JSON file describes a modular toggle (stamina, build anywhere, pristine loot, map position, etc.), and `manifest.json` controls which patches are enabled.

Key paths
- `patcher/patches/manifest.json` — active manifest consumed by API/patcher (live_xbox rollup).
- `patcher/patches/*.json` — per-feature patch definitions; some have companion `*_data.xml` for bulk XML inserts.
- `patcher/patches_organized/manifest.json` — curated catalogue (categories: tony_fixes, ezstreet_live, live_xbox, etc).

How it’s consumed
- Local/staging: `backend/scripts/apply_unified_patches.py` reads `patcher/patches` and applies to `staging/ezstreet/dayzxb_missions/dayzOffline.chernarusplus`.
- Dashboard API: `dashboard/src/app/api/patches/route.ts` exposes the manifest (env `PATCHES_DIR`, defaults to `/app/patcher/patches`).
- Node CLI: `tools/missions/apply_patches.js` also targets `patcher/patches` (fallback to `patches/` if ever present).

Adding a patch
1) Drop a `feature.json` (and optional `feature_data.xml`) into the appropriate category folder under `patcher/patches/`.
2) Add an entry to `manifest.json` with `enabled: true|false` and the relative path (e.g., `world/map_trader_zone.json`).
3) Run `python backend/scripts/apply_unified_patches.py` to rebuild staging mission files, or hit the dashboard PATCHES endpoint to toggle.

Notes
- The old `tools/missions/patches` directory was removed; everything lives under `backend/patcher/patches/` in category subfolders:
  - `core/` (server-level basics)
  - `gameplay/` (stamina, weather, map hud, etc.)
  - `economy/` (animals, vehicles counts, locked containers, CE tweaks)
  - `world/` (object spawners, map copies, Path3 resources)
  - `vehicles/` (equip presets for cars/boats)
  - `legacy/` (deprecated keep-for-history)
- Manifest `file` entries now include the relative path (e.g., `world/map_trader_zone.json`).
- XML patches use simple XPath + attribute sets; JSON patches follow the existing path/value merge convention used for cfggameplay.
- `08_vehicles_equipped` is deprecated (kept for history). Use `cars_fully_equipped` for vehicle slotting.
