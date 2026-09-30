#!/bin/bash
# PORTAINER REMOTE DEPLOYMENT
# Run this ON the Portainer host (mildlyawesome.com)

set -e

echo "🚀 DayZ Discord Ops - Remote Portainer Deployment"

# Step 1: Load images
echo "[1/3] Loading Docker images..."
if [ -f "dayz-discord-bot.tar.gz" ]; then
    docker load < dayz-discord-bot.tar.gz
    echo "   ✓ Bot image loaded"
else
    echo "   ✗ dayz-discord-bot.tar.gz not found"
    echo "   Transfer it with: scp dayz-discord-bot.tar.gz user@mildlyawesome.com:/tmp/"
    exit 1
fi

if [ -f "dayz-discord-dashboard.tar.gz" ]; then
    docker load < dayz-discord-dashboard.tar.gz
    echo "   ✓ Dashboard image loaded"
else
    echo "   ✗ dayz-discord-dashboard.tar.gz not found"
    exit 1
fi

# Step 2: Deploy stack
echo "[2/3] Deploying stack..."
    # If using docker compose directly (not via Portainer API)
    echo "   ✓ Stack deployed"
else
    exit 1
fi

# Step 3: Verify
echo "[3/3] Verifying deployment..."
sleep 3
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' | grep -E "(dayz|bot|dashboard)"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access points:"
echo "   Bot API: http://mildlyawesome.com:43200"
echo "   Dashboard: http://mildlyawesome.com:43201"
echo ""
echo "📊 Check status:"
echo "   curl http://mildlyawesome.com:43200/health"
