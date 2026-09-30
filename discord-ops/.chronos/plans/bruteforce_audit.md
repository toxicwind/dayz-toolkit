# Implementation Plan - Chronos Director "Brute Force" Audit

This plan outlines the "Brute Force" strategy to acquire total repository awareness and strictly enforce the Chronos protocol.

## User Review Required

> [!IMPORTANT]
> **Director's Intent**: This process is invasive. It will recursively scan, list, and "exhume" every file to find brittleness (hardcoded IDs, paths, secrets).
> **Objective**: Total elimination of magic numbers and "works on my machine" paths.

- **Confirm**: Are there any excluded directories (besides standard `.git`, `venv`, `node_modules`)?
- **Confirm**: Is `dayz_discord_ops_repo` the ONLY scope, or should I scan sibling repos? (Assuming SINGLE REPO per instructions).

## Proposed Changes

### Phase 1: Total Awareness (The "Brute Force" Snapshot)
-   **Topology Sync**: `find . -maxdepth 5` to map the entire terrain.
-   **Pattern Exhumation**: `grep -rE` for:
    -   Discord Snowflakes (`\b[0-9]{17,19}\b`)
    -   Absolute Paths (`/home/toxic/...`)
    -   Suspicious "TODO" / "FIXME" hotspots.
    -   Hardcoded IPs or Tokens.
-   **Output**: A massive `SNAPSHOT.md` artifact in `.chronos/`.

### Phase 2: Registry Hardening (The "Semantics" Pivot)
-   **Action**: Update `channel_spec.json` with *every* new ID found.
-   **Action**: Refactor Python code to use `registry.resolve("key")` instead of raw IDs.
-   **Action**: Ensure `Settings` object loads all paths from env/config, never string literals.

### Phase 3: Smoke & Mirrors (Verification)
-   **Action**: Create `tests/smoke/` directory.
-   **Action**: Add `test_import.py` (verifies imports work).
-   **Action**: Add `test_registry.py` (verifies all keys in spec resolve).
-   **Action**: Add `test_config.py` (verifies env vars load).
-   **Run**: `pytest` or `python -m unittest` to prove stability.

## Verification Plan

### Automated Tests
-   `python3 -m compileall src/` (Syntax purity)
-   `python3 bin/discord_sync.py --dry-run` (Registry integrity)

### Manual Verification
-   User to review `SNAPSHOT.md` to confirm no sensitive keys are leaked (though I will try to redact).
-   User to confirm "Endless" loops are gone (checked via `ps` or logs).
