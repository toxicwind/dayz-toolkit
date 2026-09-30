# Decision map: pasted logs → concrete patches

This file is the bridge between the pasted chat/logs and the concrete patches in `patches/manifest.json`.

## Vehicle moved / event rename (newer = wanted)
- Patches:
  - `xbox_vehicle02admin_events_definition` → `db/events.xml`
  - `xbox_vehicle02admin_eventpos` → `cfgeventspawns.xml`
- Rationale: avoid the “event exists but spawn positions are under a different name” trap.

## Safe distance (saferadius/distanceradius)
- Patch: `xbox_vehicle02admin_events_definition`
- Values: saferadius=500 distanceradius=500 cleanupradius=200

## Locked containers (StaticContainerLocked must exist in events.xml)
- Patch: `xbox_staticcontainerlocked_events_definition`
- Rationale: common failure is “spawn points reference StaticContainerLocked but events.xml doesn’t define it”, so nothing spawns.

## Containers nominal=0 (event controls count)
- Patch: `xbox_locked_container_types_nominal0`
- Mechanism: upsert the Land_ContainerLocked_*_DE type nodes with nominal=0 flags.

## Container keys accidentally tagged Military/Tier4
- Patch: `xbox_container_keys_unrestrict`
- Mechanism: delete `usage Military` + `value Tier4` from both plural and singular key classnames if present.

## Stamina & globals
- Patches:
  - `xbox_stamina_100` (json_merge)
  - `xbox_globals_counts_goopsta` (xml_ops)

## Optional fallback: Object Spawner JSON placement (disabled)
- Patches (disabled):
  - `xbox_lockedcontainers_copy_json` (raw_copy)
  - `xbox_cfggameplay_enable_objectspawner_lockedcontainers` (json_ops)

See the full verbatim line-by-line audits:
- `docs/AUDIT_pasted46_line_by_line.md`
- `docs/AUDIT_pasted45_line_by_line.md`
