# ALOY

**Port:** 8015
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** ALOY
**Description:** Audit logging and anomaly detection

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "aloy",
  "port": 8015
}
```

---

## Actions

### logs
```
GET /logs
```
Query audit logs

### anomalies
```
GET /anomalies
```
Get detected anomalies


---

## Capabilities

- audit_logging
- anomaly_detection
- compliance

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `aloy.action.completed`
- `aloy.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name aloy \
  --network leveredge-fleet-net \
  -p 8015:8015 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  aloy:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d aloy
```

---

*Generated: 2026-01-20 03:27*
