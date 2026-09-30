#!/bin/bash
# mildlyawesome_rsync.sh - Hyper-fast delta sync for DayZ Ops
set -e

REMOTE_HOST="root@mildlyawesome.com"
REMOTE_DIR="/tmp/dayz-deploy"
STAGING_PASSWORD="jHX4X9CdkX0KR8a"

echo "📡 INITIATING DELTA SYNC..."

# Ensure remote dir exists
sshpass -p "$STAGING_PASSWORD" ssh -o StrictHostKeyChecking=no $REMOTE_HOST "mkdir -p $REMOTE_DIR/dashboard"

# Phase 1: Sync Standalone Artifacts
# We only sync .next/standalone and .next/static and public
echo "📦 Syncing Dashboard Artifacts..."
rsync -avz --delete -e "sshpass -p $STAGING_PASSWORD ssh -o StrictHostKeyChecking=no" \
    dashboard/.next/standalone/dashboard/ \
    $REMOTE_HOST:$REMOTE_DIR/dashboard/

rsync -avz --delete -e "sshpass -p $STAGING_PASSWORD ssh -o StrictHostKeyChecking=no" \
    dashboard/.next/static/ \
    $REMOTE_HOST:$REMOTE_DIR/dashboard/.next/static/

rsync -avz --delete -e "sshpass -p $STAGING_PASSWORD ssh -o StrictHostKeyChecking=no" \
    dashboard/public/ \
    $REMOTE_HOST:$REMOTE_DIR/dashboard/public/

# Phase 2: Sync Dockerfile and stack
echo "📜 Syncing Deployment Configs..."
# CRITICAL: We renamed Dockerfile.prod to Dockerfile.prod.remote local side for clarity
# But on remote, we want it INSIDE the dashboard dir for build context
rsync -avz -e "sshpass -p $STAGING_PASSWORD ssh -o StrictHostKeyChecking=no" \
    dashboard/Dockerfile.prod.remote \
    $REMOTE_HOST:$REMOTE_DIR/dashboard/Dockerfile.prod.remote

rsync -avz -e "sshpass -p $STAGING_PASSWORD ssh -o StrictHostKeyChecking=no" \
    $REMOTE_HOST:$REMOTE_DIR/

echo "✅ DELTA SYNC COMPLETE."
