# 📋 TODO SNAPSHOT | DISCORD OPS MIRROR
> **SOURCE OF TRUTH:** Discord `#server-todo` | **SYNC ID:** `1454568932051783918`

---

## 🟥 BACKLOG ANCHORS (3X NON-BASELINE)

### 1. CHANNEL CONFIGURATION [STATUS: SYNCED]
*   **Target Channel:** `#server-todo` (ID: `1454568932051783918`)
*   **Category:** `🧪 Ops` (ID: `1454365349918277704`)
*   **Database:** `state/todo.db` (SQLite driven)

### 2. SEEDING PROTOCOLS
*   **Seed Command:** `/todo seed` (Pins rules & imports `seed_tasks.yaml`)
*   **Patcher Source:** `patcher/patches/manifest.json`
*   **Rebuild Trigger:** `python bot/scripts/apply_unified_patches.py`

### 3. ACTIVE GAMEPLAY KEYS
| FEATURE | TARGET FILE | STATUS |
| :--- | :--- | :--- |
| **Unlimited Stamina** | `cfgGameplay.json` | 🟡 PENDING |
| **Fresh Spawn Loadout** | `spawnPresets.json` | 🟡 PENDING |
| **Build Anywhere** | `BaseBuildingData` | 🟡 PENDING |
| **Fix Map Position** | `MapData` | 🟡 PENDING |
| **Pristine Loot** | `globals.xml` | 🟡 PENDING |
| **Remove Bad Loot** | `types.xml` | 🟡 PENDING |
| **Vehicle Spawns** | `cfgspawnabletypes.xml` | 🟡 PENDING |

---

## 🛠️ ADMIN COMMANDS
*   `/todo owner` - Assign ownership
*   `/todo priority` - Set urgency (CRITICAL/HIGH/MED/LOW)
*   `/todo status` - Update state (OPEN/IN_PROGRESS/DONE/BLOCKED)
*   `/todo export` - Dump to CSV/JSON
*   `/todo archive_done` - Clean up channel

---
*Unified TODO Mirror | Managed by Chronos-Forge MoE.*
