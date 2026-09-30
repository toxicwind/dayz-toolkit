# Patcher (centralized DayZ config toggles)

This folder is the single source of truth for feature patches. Each JSON file describes a modular toggle (stamina, build anywhere, pristine loot, map position, etc.), and `manifest.json` controls which patches are enabled.

Key paths
- `patcher/patches/manifest.json` — enable/disable patches and category metadata.
- `patcher/patches/*.json` — per-feature patch definitions; some have companion `*_data.xml` for bulk XML inserts.

How it’s consumed
- Local/staging: `bot/scripts/apply_unified_patches.py` reads `patcher/patches` and applies to `backend_data/staging/dayzxb_missions/dayzOffline.chernarusplus`.
- Dashboard API: `dashboard/src/app/api/patches/route.ts` exposes the manifest (env `PATCHES_DIR`, defaults to `/app/patcher/patches`).
- Node CLI: `tools/missions/apply_patches.js` also targets `patcher/patches` (fallback to `patches/` if ever present).

Adding a patch
1) Drop a `NN_feature.json` (and optional `NN_feature_data.xml`) in `patcher/patches/`.
2) Add an entry to `manifest.json` with `enabled: true|false`.
3) Run `python bot/scripts/apply_unified_patches.py` to rebuild staging mission files, or hit the dashboard PATCHES endpoint to toggle.

Notes
- The old `tools/missions/patches` directory was removed; everything lives here now.
- XML patches use simple XPath + attribute sets; JSON patches follow the existing path/value merge convention used for cfggameplay.
