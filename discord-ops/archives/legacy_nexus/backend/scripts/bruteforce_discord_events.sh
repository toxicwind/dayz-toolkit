#!/usr/bin/env bash
# Bruteforce Discord event testing
# Fires 200 events in 10 seconds to verify live updates are working

set -euo pipefail

API="${API_BASE:-http://localhost:19101}"

echo "🔥 Starting bruteforce event burst..."

# Fire 100 killfeed events
echo "💀 Firing 100 killfeed events..."
for i in $(seq 1 100); do
  curl -fsS -X POST "$API/test/killfeed" \
    -H 'content-type: application/json' \
    -d "{\"killer\":\"Killer$i\",\"victim\":\"Victim$i\",\"weapon\":\"M4A1\",\"distance\":$((50+i)),\"timestamp\":\"2026-01-02T22:00:${i}\",\"location\":\"NWAF\"}" >/dev/null 2>&1 &
  
  # Throttle to avoid overwhelming
  if [ $((i % 10)) -eq 0 ]; then
    sleep 0.5
  fi
done

# Fire 50 admin action events
echo "🛡️ Firing 50 admin action events..."
for i in $(seq 1 50); do
  curl -fsS -X POST "$API/test/admin_action" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"BAN\",\"admin\":\"Admin$i\",\"target\":\"Player$i\",\"reason\":\"Bruteforce test event $i\"}" >/dev/null 2>&1 &
  
  if [ $((i % 10)) -eq 0 ]; then
    sleep 0.3
  fi
done

# Fire 50 loot events
echo "🚁 Firing 50 loot events..."
for i in $(seq 1 50); do
  curl -fsS -X POST "$API/test/loot_event" \
    -H 'content-type: application/json' \
    -d "{\"type\":\"Helicopter Crash\",\"location\":\"NWAF\",\"tier\":\"Military\",\"coords\":\"$((12000+i*10)) $((6000+i*5))\"}" >/dev/null 2>&1 &
  
  if [ $((i % 10)) -eq 0 ]; then
    sleep 0.3
  fi
done

wait
echo "✅ Fired 200 events total"
echo "📊 Check Discord channels for live updates"
echo "📝 Check bot logs: docker compose logs dayz-discord-bot --tail=100 | grep 'killfeed\\|admin\\|loot'"
