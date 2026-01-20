# ASCLEPIUS

**Port:** 8024
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** ASCLEPIUS
**Description:** The Divine Physician - automated healing and remediation

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "asclepius",
  "port": 8024
}
```

---

## Actions

### plan-generate
```
POST /plan/generate
```
Generate healing plan from PANOPTES issues

### plan-execute
```
POST /plan/{plan_id}/execute
```
Execute a healing plan

### restart-service
```
POST /heal/service/restart/{service_name}
```
Restart a service

### emergency-full
```
POST /emergency/full
```
Full system healing

### emergency-auto
```
POST /emergency/auto
```
Auto-heal from PANOPTES issues

### emergency-nuclear
```
POST /emergency/nuclear
```
Nuclear restart - requires confirmation


---

## Capabilities

- service_healing
- port_healing
- registry_healing
- filesystem_healing
- database_healing
- network_healing
- emergency_protocols

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `asclepius.action.completed`
- `asclepius.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name asclepius \
  --network leveredge-fleet-net \
  -p 8024:8024 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  asclepius:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d asclepius
```

---

*Generated: 2026-01-20 03:27*
