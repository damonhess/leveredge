# HERMES

**Port:** 8014
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** HERMES
**Description:** Multi-channel notifications and messaging

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "hermes",
  "port": 8014
}
```

---

## Actions

### notify
```
POST /notify
```
Send notification to specified channel

### telegram
```
POST /telegram
```
Send Telegram message directly


---

## Capabilities

- telegram
- email
- event_bus
- multi_channel

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `hermes.action.completed`
- `hermes.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name hermes \
  --network leveredge-fleet-net \
  -p 8014:8014 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  hermes:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d hermes
```

---

*Generated: 2026-01-20 03:27*
