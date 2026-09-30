# Deploy to mildlyawesome.com

## Quick Deploy (3 commands)

```bash
# 1. Transfer files to Portainer host

# 2. SSH to Portainer host
ssh user@mildlyawesome.com

# 3. Run deployment
cd /tmp/dayz && chmod +x deploy_remote.sh && ./deploy_remote.sh
```

## Verify Deployment

```bash
# Check if services are running on 43200-range
curl http://mildlyawesome.com:43200/health
curl http://mildlyawesome.com:43201/
```

## Portainer UI Method (Alternative)

1. Login to Portainer: http://mildlyawesome.com:9000
2. Go to **Stacks** → **Add stack**
3. Name: `dayz-discord-ops`
5. Add environment variables from `.env`
6. Click **Deploy**

## Port Assignments (LOCKED)
- Bot API: **43200**
- Dashboard: **43201**
- MySQL: **3306**
- Metrics: **9110**
