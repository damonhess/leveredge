# HADES

**Port:** 8008
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** HADES
**Description:** Rollback and disaster recovery

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "hades",
  "port": 8008
}
```

---

## Actions

### rollback
```
POST /rollback
```
Rollback to previous state

### emergency
```
POST /emergency
```
Emergency rollback (last known good)


---

## Capabilities

- rollback
- recovery
- version_management

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `hades.action.completed`
- `hades.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name hades \
  --network leveredge-fleet-net \
  -p 8008:8008 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  hades:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d hades
```

---

*Generated: 2026-01-20 03:27*
