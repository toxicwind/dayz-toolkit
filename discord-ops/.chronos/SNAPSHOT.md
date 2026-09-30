# Chronos Snapshot - 2026-01-10

## Repository State
- **Root**: /home/toxic/dayz_workspace/dayz_discord_ops_repo
- **Hash**: 2958b3c8a5a66c1e
- **Branch**: main (assumed)
- **Discord Library**: discord.py >= 2.3.0

## Existing Discord Configuration
- `src/mildlyawesome/discord/channel_spec.json`: Contains declarative channel definitions.
- `src/mildlyawesome/discord_registry.py`: Existing registry logic to resolve and sync channels.
- Hardcoded IDs found in:
    - `configs/seeding/ezstreet.env.seed`
    - `config/config.mildlyawesome/teams/ezstreet.yaml`
    - `config/teams/ezstreet.yaml`
    - `discord_postcheck.json`

## Target Category
- **Private Category ID**: 1454365349918277704 (defined in `channel_spec.json`)

## Legacy IDs (to preserve but supersede)
- 1454356540587905075
- 1452830719582933054
- 1452830604633571348
- 1459130454874525739

## Current Code Patterns
- `OpsBot` in `src/mildlyawesome/bot.py` uses `DiscordRegistry` to resolve tracked channels.
- `KillfeedManager` uses bot-level channel references.
- `stat_channels.py`, `tickets.py`, `casino.py` use `get_channel`.
