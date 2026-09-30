# CHRONOS DIRECTOR SNAPSHOT

## 1. Topography
- **Root**: `/home/toxic/dayz_workspace/dayz_discord_ops_repo`
- **Core**: `src/mildlyawesome` (Bot, API, Services)
- **Legacy**: `src/mildlyawesome/scripts`, `src/mildlyawesome/ops` (High brittleness detected)
- **Scaffolding**: `.chronos` (Control Plane)

## 2. Brittle Constants
### Discord IDs (Snowflakes)
- ✅ **CLEAN**: No hardcoded IDs found in Python source for key semantic channels.
- ℹ️ **Registry**: IDs reside correctly in `channel_spec.json`.

### Hardcoded Paths (`/home/toxic/`)
- ⚠️ **CRITICAL**: 21 files detected with hardcoded user paths.
- **Hotspots**:
  - `src/mildlyawesome/spawn_manager.py`
  - `src/mildlyawesome/killfeed.py`
  - `src/mildlyawesome/mcp.py`
  - `src/mildlyawesome/scripts/*` (Deploy scripts)

## 3. Deployment Health
- **Bot**: `OpsBot` wired with `LiveFeedService` (New).
- **Channels**: `ops.livefeed` and `ops.livepoller` created.
- **Blocker**: Shell wrapper instability prevents complex shell execution; pivoting to Python-native tooling.

## 4. Director's Decree
- **Next Cluster**: `CLUSTER_PATH_SANITIZATION` -> Move `/home/toxic` references to `Settings.mission_root` or env vars.
- **Workflow**: `RECURSE` remains active.
