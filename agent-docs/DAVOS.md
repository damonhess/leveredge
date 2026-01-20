# MENTOR

**Port:** 8204
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** MENTOR
**Description:** Business Coach - Mentorship, leadership

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "davos",
  "port": 8204
}
```

---

## Actions

### davos-session
```
POST /session
```
Get davosship advice

### career-path
```
POST /career
```
Plan career path


---

## Capabilities

- business_davosship
- career_guidance
- leadership_development
- professional_growth

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `davos.action.completed`
- `davos.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name davos \
  --network leveredge-fleet-net \
  -p 8204:8204 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  davos:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d davos
```

---

*Generated: 2026-01-20 03:27*
