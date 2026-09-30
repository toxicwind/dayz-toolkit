#!/usr/bin/env bash
set -euo pipefail

REPO_SRC="/home/toxic/dayz_workspace/dayz_discord_ops_repo"
DEPLOY_DST="/home/toxic/development/dedi-ops"

log() { printf '[reset] %s\n' "$*"; }

log "Ensuring deploy dir exists: $DEPLOY_DST"
mkdir -p "$DEPLOY_DST"

log "Killing local DayZ/dedi/bot processes (best effort)"
pkill -f "dedi_agent" 2>/dev/null || true
pkill -f "dedi-ops" 2>/dev/null || true
pkill -f "src/mildlyawesome/bot.py" 2>/dev/null || true
pkill -f "bin/dedi" 2>/dev/null || true

log "Stopping docker containers matching dayz|dedi|ezstreet (best effort)"
if command -v docker >/dev/null 2>&1; then
  mapfile -t targets < <(docker ps --format '{{.ID}} {{.Names}}' | awk 'tolower($0) ~ /(dayz|dedi|ezstreet)/ {print $1}')
  if [[ ${#targets[@]} -gt 0 ]]; then
    docker stop "${targets[@]}" || true
  else
    log "No matching containers running"
  fi
else
  log "docker not available; skipping container stop"
fi

log "Rsync source -> deploy (excludes .git/.venv/node_modules)"
rsync -av --exclude='.git' --exclude='.venv' --exclude='node_modules' "$REPO_SRC"/ "$DEPLOY_DST"/

log "Optional: validate docker-compose.yml if present"
if [[ -f "$DEPLOY_DST/docker-compose.yml" ]]; then
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose -f "$DEPLOY_DST/docker-compose.yml" config >/dev/null
  elif command -v docker >/dev/null 2>&1; then
    docker compose -f "$DEPLOY_DST/docker-compose.yml" config >/dev/null
  else
    log "docker compose not available; skip config validation"
  fi
else
  log "No docker-compose.yml at $DEPLOY_DST"
fi

log "Done."
