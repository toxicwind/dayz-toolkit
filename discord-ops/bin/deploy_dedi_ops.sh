#!/usr/bin/env bash
# Deploy a curated runtime bundle into /home/toxic/dedi-ops with a minimal, 2026-ready layout.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TARGET=${DEPLOY_ROOT:-/home/toxic/dedi-ops}
RSYNC_EXCLUDES=("--exclude=.git" "--exclude=__pycache__" "--exclude=*.pyc" "--exclude=tests" "--exclude=logs" "--exclude=outputs" "--exclude=.chronos")

mkdir -p "$TARGET"

# Sync only deployment-relevant assets; compose is duplicated as docker-compose.yml for convenience.
rsync -av --delete "${RSYNC_EXCLUDES[@]}" \
  --include='docker-compose.modern.yml' \
  --include='docker-compose.yml' \
  --include='Dockerfile' \
  --include='Makefile' \
  --include='launch_bot.py' \
  --include='requirements.txt' \
  --include='requirements-dev.txt' \
  --include='serena-config/***' \
  --include='config/***' \
  --include='bin/dayz_reset_local.sh' \
  --include='state/***' \
  --exclude='*' "$ROOT"/ "$TARGET"/

# Ensure a canonical compose filename exists in the target.
if [[ -f "$TARGET/docker-compose.modern.yml" ]]; then
  cp "$TARGET/docker-compose.modern.yml" "$TARGET/docker-compose.yml"
fi

# Basic structure for downstream convenience.
mkdir -p "$TARGET/bin"
cp "$ROOT/bin/dayz_reset_local.sh" "$TARGET/bin/dayz_reset_local.sh"
chmod +x "$TARGET/bin/dayz_reset_local.sh"

# Validate compose if present.
if command -v docker >/dev/null 2>&1 && [[ -f "$TARGET/docker-compose.yml" ]]; then
  (cd "$TARGET" && docker compose config >/dev/null)
fi

echo "Deployment bundle refreshed at $TARGET"
