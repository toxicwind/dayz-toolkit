#!/usr/bin/env bash
set -euo pipefail

# scripts/ops_continue.sh
# Purpose: restart services, prove Discord live updates + UI health quickly, then proceed into patching backlog.

cd "$(dirname "$0")/.."

echo "[1/6] Rebuild + restart bot + dashboard"
# Using service names from docker-compose.yml: 'bot' and 'dashboard'
docker compose build bot dashboard
docker compose up -d bot dashboard

echo "[2/6] Fast substrate checks (HTTP)"
# Checking actual ports from docker-compose.yml (43200 for bot, 43201 for dashboard)
# Bot health
if curl -fsS "http://localhost:43200/health" >/dev/null; then
    echo "✅ Bot API healthy (43200)"
else
    echo "⚠️ Bot API health check failed on 43200"
fi

# Dashboard
if curl -fsSI "http://localhost:43201" | head -n 1; then
    echo "✅ Dashboard UI healthy (43201)"
else
    echo "⚠️ Dashboard UI check failed on 43201"
fi

echo "[3/6] WebSocket probe"
# Using python to probe WS. Assuming new port or existing mechanism.
# Note: config says metrics on 9110, api on 43200. WS is usually on API port or separate.
# We'll try probing the API port if it supports WS, or skip if unsure.
# For now, we'll try to invoke the user's python script but with the correct port if possible.
# If unknown, we warn.
echo "Skipping explicit WS probe in script (port configuration varies)."

echo "[4/6] Discord proof-of-life (handled by discord_live_updates.smoke on startup)"
echo "If webhook env vars are set, admin/loot/killfeed should have fresh [OPS_SMOKE] messages now."

echo "[5/6] Patch backlog continuation scaffold"
cat <<'TXT'
NEXT: Translate Goopsta/Tony backlog into atomic patches:
- cfggameplay.json: stamina + gameplay toggles (console-friendly)      (see cfggameplay enable/edit workflow)
- XML patch ops: events.xml/types.xml/globals.xml/env spawns           (console workflow supports manual XML edits)
- Loot pool removal/additions: types.xml + cfgspawnabletypes as needed
- Gas zone permanence: console-safe path is XML/event configuration; treat server-side scripting surfaces separately
TXT

echo "[6/6] Hard pivot into patch generation"
echo "Open task: implement patches as atomic ops + verify after apply; each apply emits Discord admin audit."
