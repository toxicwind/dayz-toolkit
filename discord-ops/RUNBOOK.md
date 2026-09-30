# DayZ Discord Ops Runbook

## Quick Start

### Development Mode
```bash
docker compose -f compose.dev.yaml up -d
docker compose -f compose.dev.yaml logs -f bot
```

### Production Mode
```bash
# Build bot image first
docker build -t dayz-discord-ops:latest .

# Start with prod profile
docker compose --profile prod up -d

# View logs
docker compose logs -f bot
```

### Operations Harness

All operations run through `tools/ops.py`:

```bash
# View effective config (redacts secrets)
python3 -m tools.ops config:print ezstreet

# Validate mission XML syntax
python3 -m tools.ops mission:validate

# Enforce repository invariants (removes banned scripts)
python3 -m tools.ops repair
```

## Configuration

YAML is the single source of truth. Precedence:
1. `config/global.yaml`
2. `config/dev.global.yaml`
3. `config/dev.yaml`
4. `config/services/ezstreet.yaml`
5. `config/secrets.local.yaml` (gitignored)

## Discord Channels

Server starts automatically creates:
- **🟢-ezstreet-status**: Single pinned message, auto-updated every 60s
- **✨-deploy-feed**: Change cards on git commits (webhook or poll)

## Secrets Management

Secrets stored in `config/secrets.local.yaml` (gitignored):
```yaml
nitrado:
  api_token: "..."
discord:
  token: "..."
mysql:
  password: "..."
```

## Rollback

```bash
# Stop services
docker compose down

# Revert to previous commit
git revert HEAD

# Rebuild and restart
docker build -t dayz-discord-ops:latest .
docker compose --profile prod up -d
```

## Verification

```bash
# Check all services running
docker compose ps

# Verify config loads
python -m tools.ops config:print

# Check Discord channels exist
# (Auto-created on first bot startup)
```
