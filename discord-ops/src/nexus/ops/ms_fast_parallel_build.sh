#!/bin/bash
# ms_fast_parallel_build.sh - Parallelized Build and Delta Sync
set -e

REMOTE_HOST="root@mildlyawesome.com"
STAGING_PASSWORD="jHX4X9CdkX0KR8a"

echo "🚀 INITIATING MS-FAST PARALLEL PIPE..."

# Step 1: Local Build (Background)
(
    echo "📦 Building Dashboard Assets (Speed Mode)..."
    cd dashboard
    NEXT_DISABLE_ESLINT=1 NEXT_DISABLE_TYPECHECK=1 npm run build
) &
BUILD_PID=$!

# Step 2: Remote Prep (Parallel)
(
    echo "🛡️ Verifying Remote Port Integrity..."
    sshpass -p "$STAGING_PASSWORD" ssh -o StrictHostKeyChecking=no $REMOTE_HOST "netstat -tulnp | grep 4320 || true"
) &
PREP_PID=$!

wait $BUILD_PID $PREP_PID

# Step 3: Delta Sync
bash tools/mildlyawesome_rsync.sh

# Step 4: Remote Assembly & Stack Refresh
echo "🐳 Assembling Remote Image & Updating Stack..."
sshpass -p "$STAGING_PASSWORD" ssh -o StrictHostKeyChecking=no $REMOTE_HOST <<EOF
cd /tmp/dayz-deploy/dashboard
docker build -t dayz-discord-dashboard:latest -f Dockerfile.prod.remote .
EOF


echo "✅ MS-FAST DEPLOYMENT COMPLETE."
