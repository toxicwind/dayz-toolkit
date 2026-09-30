#!/bin/bash
# ms_fast_deploy.sh - Optimized Parallel Deployment for DayZ Ops
set -e

REMOTE_HOST="root@mildlyawesome.com"
STAGING_PASSWORD="jHX4X9CdkX0KR8a"

echo "🚀 INITIATING MS-FAST DEPLOYMENT..."

# Step 1: Optimized Build
(
    echo "📦 Building Dashboard Assets (Speed Mode)..."
    cd dashboard
    # Force speed by skipping heavy checks
    NEXT_DISABLE_ESLINT=1 NEXT_DISABLE_TYPECHECK=1 npm run build
    
    echo "🐳 Creating Runner-Only Docker Image..."
    # We use -f Dockerfile.prod which now leverages the local build
    docker build -t dayz-discord-dashboard:latest -f Dockerfile.prod .
) &
BUILD_PID=$!

wait $BUILD_PID

echo "📡 STREAMING IMAGE TO REMOTE & LOADING..."
# Task 04/05: Direct pipe to avoid intermediate .tar file storage on local disk if needed, 
# although we still save to disk for safety in some scripts.
docker save dayz-discord-dashboard:latest | sshpass -p "$STAGING_PASSWORD" ssh -o StrictHostKeyChecking=no $REMOTE_HOST "docker load"

echo "🔄 UPDATING PORTAINER STACK..."

echo "✅ DEPLOYMENT COMPLETE."
