#!/usr/bin/env bash
# MS-FAST Delta Deployment Script
# Deploys dashboard to mildlyawesome.com via rsync with <10s target

set -euo pipefail

# Load environment
source "$(dirname "$0")/../.env"

# Configuration
LOCAL_BUILD_DIR="dashboard/.next"
REMOTE_HOST="${DEDI_HOST}"
REMOTE_USER="${DEDI_USER}"
REMOTE_PATH="/opt/dayz-ops/dashboard"
SSH_OPTS="-o ControlMaster=auto -o ControlPath=/tmp/ssh-%r@%h:%p -o ControlPersist=10m"

log() { echo "[$(date +'%H:%M:%S')] $*"; }
timer_start=$(date +%s)

log "🚀 MS-FAST DELTA DEPLOYMENT"
log "   Target: ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

# Step 1: Build locally (parallel with connection setup)
log "📦 Building Next.js (Turbopack)..."
cd dashboard && npm run build &
BUILD_PID=$!

# Step 2: Establish SSH ControlMaster (parallel)
log "🔌 Establishing SSH ControlMaster..."
sshpass -p "${DEDI_PASSWORD}" ssh ${SSH_OPTS} -fN "${REMOTE_USER}@${REMOTE_HOST}" 2>/dev/null || true

# Wait for build
wait $BUILD_PID
log "✅ Build complete"

# Step 3: Delta-sync via rsync
log "📡 Syncing .next build artifacts..."
sshpass -p "${DEDI_PASSWORD}" rsync -avz --delete \
  -e "ssh ${SSH_OPTS}" \
  "${LOCAL_BUILD_DIR}/" \
  "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/.next/"

# Step 4: Restart remote container
log "🔄 Restarting remote dashboard..."
sshpass -p "${DEDI_PASSWORD}" ssh ${SSH_OPTS} "${REMOTE_USER}@${REMOTE_HOST}" \
  "docker restart dayz_discord_dashboard"

# Timing
timer_end=$(date +%s)
elapsed=$((timer_end - timer_start))

log "✅ DEPLOYMENT COMPLETE in ${elapsed}s"
log "🌐 Dashboard: http://${REMOTE_HOST}:43201"

# Verify
log "🔍 Verifying..."
curl -sI "http://${REMOTE_HOST}:43201" | head -n1
