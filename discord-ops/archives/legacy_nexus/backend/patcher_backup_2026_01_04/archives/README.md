# Archived patch sources

Reference configs recovered from `data/archives/dayz_console_mod_provenance/custom`:

- `1C-128-milicon-types.xml` – locked container loot types + shipping container keys definitions.
- `1C-128-milicon-events.xml` – `StaticContainerLocked` event with nominal/min/max and children.
- `1C-128-rubberboats-spawnabletypes.xml` – boat spawnable types with spark plug + gasoline can cargo.
- `EZStreet_Loadout_Fresh.json` – example spawn preset.

Use these as inputs when crafting new modular patches in `patcher/patches/` (e.g., locked container events, boat equipment, loadouts). They are not auto-applied; copy relevant snippets into new numbered patch files, then enable in `manifest.json`.
