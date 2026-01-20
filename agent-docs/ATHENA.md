# ATHENA

**Port:** 8013
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** ATHENA
**Description:** Automated documentation generation

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "athena",
  "port": 8013
}
```

---

## Actions

### generate
```
POST /generate
```
Generate documentation


---

## Capabilities

- documentation
- api_docs
- changelog

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `athena.action.completed`
- `athena.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name athena \
  --network leveredge-fleet-net \
  -p 8013:8013 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  athena:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d athena
```

---

*Generated: 2026-01-20 03:27*
