# Chronos Plan - Discord Channel Reconstitution

## Objectives
1.  **Remap Layer**: Implement a "Registry v2" that supersedes all runtime channel lookups.
2.  **Private-First Policy**: Force all new channels under category `1454365349918277704`.
3.  **Migration CLI**: Create `./bin/discord_migrate` with `--dry-run` and `--apply`.
4.  **Audit & Evidence**: Generate `DISCORD_AUDIT.md` and `discord_channel_map.json`.
5.  **Write Guard**: Block unintentional writes to legacy channels.

## Detailed Steps

### Phase 1: Registry Enhancement (SURGEON/OPERATOR)
- [ ] Update `src/mildlyawesome/discord_registry.py`:
    - Add `discord_channel_map.json` persistence.
    - Implement search logic for legacy IDs to block writes.
    - Enhance `sync` to strictly enforce the private category `1454365349918277704`.
- [ ] Add `is_legacy(channel_id)` and `block_legacy_writes()` methods.

### Phase 2: CLI Entrypoint (OPERATOR)
- [ ] Create `bin/discord_migrate` script.
- [ ] Support `--dry-run`, `--apply`, and `--guild`.

### Phase 3: Runtime Routing (SURGEON)
- [ ] Modify `src/mildlyawesome/bot.py` to ensure all modules use the registry for lookups.
- [ ] Implement a wrapper for `send` that checks `block_legacy_writes`.

### Phase 4: Audit & Evidence (CARTOGRAPHER)
- [ ] Script to scan all files for Discord IDs.
- [ ] Generate `DISCORD_AUDIT.md`.
- [ ] Generate initial `discord_channel_map.json`.

### Phase 5: Verification (SYNTH)
- [ ] Run linting and type checks.
- [ ] Dry-run migration.
- [ ] Final evidence confirmation.

## Hard Invariants
- `target_category_id` MUST be `1454365349918277704`.
- No new channels outside this category.
