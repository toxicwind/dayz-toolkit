#!/usr/bin/env bash
# DayZ Ops Remote Management Helper
# Deployed to: /opt/dayz-ops/manage.sh on mildlyawesome.com

set -euo pipefail

STACK_NAME="dayz-ezstreet-ops-43200"
BOT_CONTAINER="dayz_discord_bot"
DASHBOARD_CONTAINER="dayz_discord_dashboard"
DB_CONTAINER="dayz_discord_db"

log() { echo "[$(date +'%H:%M:%S')] $*"; }

case "${1:-help}" in
  status)
    log "📊 Stack Status"
    docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E "dayz|NAMES"
    ;;
  
  logs)
    SERVICE="${2:-dashboard}"
    case "$SERVICE" in
      bot) docker logs -f "$BOT_CONTAINER" ;;
      dashboard) docker logs -f "$DASHBOARD_CONTAINER" ;;
      db) docker logs -f "$DB_CONTAINER" ;;
      *) echo "Usage: $0 logs [bot|dashboard|db]" ;;
    esac
    ;;
  
  restart)
    SERVICE="${2:-all}"
    case "$SERVICE" in
      bot) docker restart "$BOT_CONTAINER" ;;
      dashboard) docker restart "$DASHBOARD_CONTAINER" ;;
      all) docker restart "$BOT_CONTAINER" "$DASHBOARD_CONTAINER" ;;
      *) echo "Usage: $0 restart [bot|dashboard|all]" ;;
    esac
    ;;
  
  health)
    log "🔍 Health Checks"
    echo "Bot API:"
    curl -s http://localhost:43200/health || echo "❌ Failed"
    echo -e "\nDashboard:"
    curl -I http://localhost:43201 2>&1 | head -n 1
    ;;
  
  env)
    SERVICE="${2:-dashboard}"
    case "$SERVICE" in
      bot) docker exec "$BOT_CONTAINER" env | grep -E "DISCORD|NITRADO|FTP|MYSQL" ;;
      dashboard) docker exec "$DASHBOARD_CONTAINER" env | grep CLERK ;;
      *) echo "Usage: $0 env [bot|dashboard]" ;;
    esac
    ;;
  
  cleanup)
    log "🧹 Cleaning up old images and containers"
    docker system prune -f
    ;;
  
  help|*)
    cat <<EOF
DayZ Ops Remote Management Helper

Usage: $0 <command> [args]

Commands:
  status              Show container status
  logs <service>      Tail logs (bot|dashboard|db)
  restart <service>   Restart service (bot|dashboard|all)
  health              Run health checks
  env <service>       Show environment variables
  cleanup             Clean up Docker resources
  help                Show this help

Examples:
  $0 status
  $0 logs dashboard
  $0 restart all
  $0 health
EOF
    ;;
esac
