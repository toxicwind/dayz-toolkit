# dayz-discord-ops (Swarm/Portainer-ready)

A production-shaped Discord bot for **DayZ server ops** that integrates:

- **Steam A2S Query** (server info, players)
- **BattlEye RCON**
- Optional: **/metrics** (Prometheus)
- Optional: **stat voice channels** (locked channels whose names show live counts)

> **Security:** do **not** hardcode provider passwords in source or git. Use env vars or Swarm secrets.
> If you posted credentials anywhere, rotate them.

## Discord setup
Create an application+bot in the Discord Developer Portal, copy **Bot Token**.
For member/presence counts, enable privileged gateway intents:
- Server Members Intent
- Presence Intent

## Configure endpoints
Set:
- `DAYZ_HOST`
- `DAYZ_QUERY_PORT` (A2S)
- `DAYZ_RCON_PORT` + `DAYZ_RCON_PASSWORD` (BattlEye)

### Harden the A2S path
The bot now defends against missing `python-a2s`, mismatched packages, and flaky servers:

- `A2S_TIMEOUT` (seconds, default `2.0`)
- `A2S_RETRIES` (default `2`) + `A2S_RETRY_BACKOFF` (default `1.5`) expand timeouts per attempt without blocking the event loop.
- `A2S_CACHE_TTL_SECONDS` (default `300`) defines how long a successful info/players query can be reused if the next live poll fails. When cache is used, stats update with stale data and the `/dayz_*` commands annotate the output.
- Metrics: `dayz_a2s_up`, `dayz_a2s_stale`, `dayz_a2s_errors_total{reason="..."}` help dashboards distinguish healthy queries vs cached fallbacks vs dependency errors.

## Local / Server Deployment (Docker Compose)
Swarm support has been removed in favor of a simpler `docker compose` flow. To deploy:

1. `cp .env.example .env` and populate all required secrets (Discord token, RCON password, etc.).
2. Optional: tweak `PUBLIC_*` and `METRICS_PORT` if you need different host ports.
3. Build + launch:
   ```bash
   python scripts/deploy_compose.py
   # or, if you prefer make:
   make build
   make deploy
   ```
   The script wraps `docker compose build` + `docker compose up -d mysql dayz-discord-bot` and tails the bot logs so you can verify startup.
4. To stop everything when needed: `docker compose down`.

The bundled `docker-compose.yml` includes a MySQL container for local metrics logging and an optional dashboard profile (run via `docker compose --profile dashboard up -d dashboard` if you need it).

## Slash commands
- `/dayz_status`
- `/dayz_players`
- `/dayz_rcon_raw` (guarded by role allowlist)
- `/stat_tick`
