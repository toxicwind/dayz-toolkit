# Production Deployment Checklist

## Pre-Deployment

### Environment Configuration
- [ ] Copy `.env.example` to `.env`
- [ ] Set `DISCORD_BOT_TOKEN` (from Discord Developer Portal)
- [ ] Set `DISCORD_GUILD_ID` (your server ID)
- [ ] Set `DISCORD_ADMIN_ROLE_IDS` (comma-separated role IDs)
- [ ] Set `DAYZ_HOST` (your DayZ server IP)
- [ ] Set `DAYZ_QUERY_PORT` (default: 27016)
- [ ] Set `DAYZ_RCON_PORT` (default: 2305)
- [ ] Set `DAYZ_RCON_PASSWORD` (BattlEye RCON password)
- [ ] Set `NITRADO_API_TOKEN` (from Nitrado dashboard)
- [ ] Set `NITRADO_SERVICE_ID` (your Nitrado service ID)
- [ ] Set `DAYZ_FTP_HOST`, `DAYZ_FTP_USER`, `DAYZ_FTP_PASS` (optional, for FTP logs)
- [ ] Set `DAYZ_MYSQL_HOST`, `DAYZ_MYSQL_USER`, `DAYZ_MYSQL_PASS`, `DAYZ_MYSQL_DB` (for stats)

### Backend Data
- [ ] Verify `backend_data/EZStreet_ServerConfig.json` exists
- [ ] Configure economy settings in the JSON file
- [ ] Verify `backend_data/configeconomy.py` is executable
- [ ] Test the economy compiler script locally

### Database Setup
- [ ] Ensure MySQL is running (via Docker Compose or external)
- [ ] Verify database schema is created (tables: `activity_logs`, `player_activity`, `server_stats`)
- [ ] Test database connection with credentials

## Deployment Steps

### Option 1: Docker Compose (Recommended)
```bash
# 1. Build images
docker compose build

# 2. Start services
docker compose up -d mysql dayz-discord-bot

# 3. Start dashboard (optional)
docker compose --profile dashboard up -d dashboard

# 4. Check logs
docker compose logs -f dayz-discord-bot
```

### Option 2: Manual Deployment

#### Backend (Python Bot + API)
```bash
# 1. Install dependencies
pip install -e .

# 2. Start the bot (includes API server)
python -m dayz_discord_ops.bot
```

#### Frontend (Next.js Dashboard)
```bash
# 1. Navigate to dashboard
cd dashboard

# 2. Install dependencies
npm install

# 3. Build for production
npm run build

# 4. Start production server
npm start
```

## Post-Deployment Verification

### Backend Health Checks
- [ ] Bot appears online in Discord
- [ ] `/dayz_status` slash command works
- [ ] API responds at `http://localhost:8080/health`
- [ ] Run `python verify_api.py` to test all endpoints
- [ ] Check bot logs for any errors

### Frontend Health Checks
- [ ] Dashboard loads at `http://localhost:3000`
- [ ] All pages render without errors:
  - [ ] `/dashboard/overview`
  - [ ] `/dashboard/logistics`
  - [ ] `/dashboard/economy`
  - [ ] `/dashboard/bot`
  - [ ] `/dashboard/settings`
  - [ ] `/dashboard/rcon`
  - [ ] `/dashboard/logs`
  - [ ] `/dashboard/players`
  - [ ] `/dashboard/intelligence`

### Integration Tests
- [ ] Test RCON command execution from dashboard
- [ ] Verify Nitrado server status displays correctly
- [ ] Test server restart/stop controls (in safe environment!)
- [ ] Verify economy intelligence shows clusters and warnings
- [ ] Test log viewer with Nitrado cloud logs
- [ ] Verify bot status page shows live data
- [ ] Test settings page integration health checks

## Production Hardening

### Security
- [ ] Enable HTTPS (use Nginx reverse proxy + Let's Encrypt)
- [ ] Configure CORS properly for dashboard
- [ ] Add rate limiting to API endpoints
- [ ] Enable Clerk authentication for dashboard (already integrated)
- [ ] Set up firewall rules (only expose necessary ports)
- [ ] Rotate all secrets and API tokens
- [ ] Enable audit logging for configuration changes

### Performance
- [ ] Enable Redis for API caching (optional)
- [ ] Configure CDN for dashboard static assets
- [ ] Set up database connection pooling
- [ ] Enable Prometheus metrics collection
- [ ] Configure log rotation

### Monitoring
- [ ] Set up Sentry for error tracking
- [ ] Configure uptime monitoring (UptimeRobot, etc.)
- [ ] Set up alerts for bot disconnections
- [ ] Monitor API response times
- [ ] Track database query performance

### Backup & Recovery
- [ ] Set up automated database backups
- [ ] Backup `EZStreet_ServerConfig.json` regularly
- [ ] Document restore procedures
- [ ] Test disaster recovery plan

## Troubleshooting

### Bot Won't Start
1. Check Discord token is valid
2. Verify bot has necessary intents enabled
3. Check guild ID is correct
4. Review logs for connection errors

### API Endpoints Failing
1. Verify .env variables are set
2. Check Nitrado API token is valid
3. Test RCON connection manually
4. Review FastAPI logs

### Dashboard Not Loading
1. Check Next.js is running on correct port
2. Verify API proxy configuration in `next.config.ts`
3. Check browser console for errors
4. Verify all dependencies are installed

### Economy Intelligence Not Working
1. Verify `types.xml` exists in mission folder
2. Check file permissions
3. Review `economy_intelligence.py` logs
4. Test with sample data

## Rollback Plan

If deployment fails:
1. Stop all services: `docker compose down`
2. Restore previous `.env` file
3. Restore database backup
4. Restart with known-good configuration
5. Review logs to identify issue

## Success Criteria

Deployment is successful when:
- ✅ Bot is online in Discord
- ✅ All slash commands respond
- ✅ Dashboard loads without errors
- ✅ All API endpoints return 200 OK
- ✅ Nitrado integration works
- ✅ Economy intelligence displays data
- ✅ No errors in logs for 24 hours

---

**Last Updated**: 2025-12-23
**Version**: 1.0.0
