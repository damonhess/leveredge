# CERBERUS

**Port:** 8025
**Category:** security
**Status:** Defined

---

## Identity

**Name:** CERBERUS
**Description:** Security Gateway - Authentication, authorization, rate limiting

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "cerberus",
  "port": 8025
}
```

---

## Actions

### authenticate
```
POST /authenticate
```
Authenticate user or service

### authorize
```
POST /authorize
```
Check authorization for action


---

## Capabilities

- authentication
- authorization
- rate_limiting
- security_policy

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `cerberus.action.completed`
- `cerberus.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name cerberus \
  --network leveredge-fleet-net \
  -p 8025:8025 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  cerberus:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d cerberus
```

---

*Generated: 2026-01-20 03:27*
