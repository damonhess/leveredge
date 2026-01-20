# ARGUS

**Port:** 8016
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** ARGUS
**Description:** System monitoring and metrics

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "argus",
  "port": 8016
}
```

---

## Actions

### status
```
GET /status
```
Get system status

### health
```
GET /health
```
Health check

### costs
```
GET /costs
```
Get cost summary

### costs-daily
```
GET /costs/daily
```
Get daily cost trend


---

## Capabilities

- health_monitoring
- metrics
- alerting
- cost_tracking

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `argus.action.completed`
- `argus.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name argus \
  --network leveredge-fleet-net \
  -p 8016:8016 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  argus:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d argus
```

---

*Generated: 2026-01-20 03:27*
