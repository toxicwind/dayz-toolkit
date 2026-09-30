# Quick Reference

## Access Points
- Backend API: http://localhost:18780
- Dashboard: http://localhost:18787  
- MySQL: localhost:3306

## Key Endpoints
```
GET  /economy/intelligence/clusters  # 263 item families
GET  /economy/intelligence/validate  # XML validation warnings
GET  /mission/files                  # List mission XMLs
GET  /nitrado/logs                   # Nitrado cloud logs
POST /nitrado/logs/content           # Download log content
```

## Configuration
- Server Config: `backend_data/EZStreet_ServerConfig.json`
- Environment: `.env`
- Docker: `docker-compose.yml`

## Verification
```bash
# Test backend intelligence
curl http://localhost:18780/economy/intelligence/clusters | jq 'keys | length'

# Test dashboard proxy
curl http://localhost:18787/api/server/mission/files | jq '.files'

# Check containers
docker-compose ps
```

