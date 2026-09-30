#!/usr/bin/env bash
set -euo pipefail

# Quick helper to start the Serena MCP server via Docker Compose
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.serena.yml"

echo "Starting Serena MCP server using $COMPOSE_FILE"
# Allow override of ports via env as needed
docker compose -f "$COMPOSE_FILE" up -d serena

echo "Waiting for Serena MCP to become healthy (port 9121)..."
for i in {1..30}; do
  if curl -sSf http://localhost:9121/ > /dev/null 2>&1; then
    echo "Serena MCP server is up"
    exit 0
  fi
  sleep 1
done

echo "Serena MCP server did not respond on 9121 in time"
exit 1
