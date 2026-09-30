#!/bin/bash
echo "=== MILDLYAWESOME REMOTE DIAGNOSTIC SUITE ==="
echo "TS: $(date)"

echo -e "\n[1] HOST DISK SPACE"
df -h / /archive

echo -e "\n[2] DOCKER SERVICE STATUS"
systemctl is-active docker
docker info | grep -i 'root\|storage'

echo -e "\n[3] RECENT DOCKER LOGS (SUSPECTED FAILURES)"
journalctl -u docker --no-pager -n 50 | grep -i "error\|fail"

echo -e "\n[4] DEPLOYMENT STAGING AREA"
ls -lh /tmp/dayz-deploy

echo -e "\n[5] PORTAINER STACKS"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep "dayz"

echo -e "\n[6] NETWORK CONNECTIVITY (INTERNAL)"
# Check if bot can talk to dashboard or vice versa if possible
# (Hard to do without being inside a container, but we can check if ports are bound)
netstat -tulpn | grep -E "43200|43201"

echo "=== DIAGNOSTIC COMPLETE ==="
