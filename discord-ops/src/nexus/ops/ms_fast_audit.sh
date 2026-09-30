#!/bin/bash
# ms_fast_audit.sh - Parallelized Health & Connectivity Probe
set -e

HOST="mildlyawesome.com"
API_PORT=43200
DASHBOARD_PORT=43201

echo "🔍 INITIATING MS-FAST AUDIT FOR $HOST..."

# Parallel HTTP probes
(
    RES=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$API_PORT/health || echo "FAIL")
    echo "🤖 Bot API Health: [$RES]"
) &
API_PID=$!

(
    RES=$(curl -s -o /dev/null -w "%{http_code}" http://$HOST:$DASHBOARD_PORT/ || echo "FAIL")
    echo "📊 Dashboard UI:   [$RES]"
) &
DASH_PID=$!

wait $API_PID $DASH_PID

echo "✅ AUDIT COMPLETE."
if [[ $(cat /tmp/audit_results 2>/dev/null) == *"FAIL"* ]]; then
    exit 1
fi
