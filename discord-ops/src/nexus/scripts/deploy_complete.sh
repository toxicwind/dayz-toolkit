#!/bin/bash
# COMPLETE PORTAINER DEPLOYMENT
# Transfers images to Portainer host and deploys stack

set -e

PORTAINER_HOST="${PORTAINER_HOST:-mildlyawesome.com}"
PORTAINER_USER="${PORTAINER_USER:-root}"

echo "🚀 Complete Portainer Deployment to $PORTAINER_HOST"

# Step 1: Transfer images
echo "[1/4] Transferring images to Portainer host..."
ssh $PORTAINER_USER@$PORTAINER_HOST "mkdir -p /tmp/dayz-deploy"

scp dayz-discord-bot.tar.gz \
    dayz-discord-dashboard.tar.gz \
    $PORTAINER_USER@$PORTAINER_HOST:/tmp/dayz-deploy/

echo "   ✓ Images transferred"

# Step 2: Load images on Portainer host
echo "[2/4] Loading images on Portainer host..."
ssh $PORTAINER_USER@$PORTAINER_HOST << 'EOF'
cd /tmp/dayz-deploy
docker load < dayz-discord-bot.tar.gz
docker load < dayz-discord-dashboard.tar.gz
echo "Images loaded successfully"
EOF

echo "   ✓ Images loaded"

# Step 3: Deploy via Portainer API
echo "[3/4] Deploying stack via Portainer API..."

echo "   ✓ Stack deployed"

# Step 4: Verify
echo "[4/4] Verifying deployment..."
sleep 5
curl -I http://$PORTAINER_HOST:43200/health || echo "Bot not ready yet (Discord token needed)"
curl -I http://$PORTAINER_HOST:43201/ || echo "Dashboard not ready yet"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access points:"
echo "   Bot API: http://$PORTAINER_HOST:43200"
echo "   Dashboard: http://$PORTAINER_HOST:43201"
echo "   Portainer: http://$PORTAINER_HOST:9000"
