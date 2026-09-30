#!/usr/bin/env bash
set -euo pipefail
IMAGE_NAME=${1:-ghcr.io/your-org/dayz-discord-ops:local}
docker build -t "$IMAGE_NAME" .
