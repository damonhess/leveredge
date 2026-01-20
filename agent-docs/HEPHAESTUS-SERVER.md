# HEPHAESTUS-SERVER

**Port:** 8207
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** HEPHAESTUS-SERVER
**Description:** Server Admin - Infrastructure management

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "hephaestus-server",
  "port": 8207
}
```

---

## Actions

### diagnose
```
POST /diagnose
```
Diagnose server issue

### recommend-setup
```
POST /recommend
```
Recommend server setup


---

## Capabilities

- server_management
- infrastructure_recommendations
- devops_practices
- system_administration

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `hephaestus-server.action.completed`
- `hephaestus-server.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name hephaestus-server \
  --network leveredge-fleet-net \
  -p 8207:8207 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  hephaestus-server:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d hephaestus-server
```

---

*Generated: 2026-01-20 03:27*
