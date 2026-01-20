# EROS

**Port:** 8104
**Category:** personal
**Status:** LLM-Powered

---

## Identity

**Name:** EROS
**Description:** Relationship Coach - Dating advice, communication

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "arwen",
  "port": 8104
}
```

---

## Actions

### dating-advice
```
POST /advice
```
Get dating advice for situation

### improve-message
```
POST /message
```
Improve dating message/profile


---

## Capabilities

- dating_advice
- relationship_guidance
- communication_strategies
- social_skills

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `arwen.action.completed`
- `arwen.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name arwen \
  --network leveredge-fleet-net \
  -p 8104:8104 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  arwen:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d arwen
```

---

*Generated: 2026-01-20 03:27*
