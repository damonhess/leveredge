# NUTRITIONIST

**Port:** 8101
**Category:** personal
**Status:** LLM-Powered

---

## Identity

**Name:** NUTRITIONIST
**Description:** Nutrition Advisor - Diet planning, macro tracking

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "bombadil",
  "port": 8101
}
```

---

## Actions

### analyze-diet
```
POST /analyze
```
Analyze current diet

### recommend-supplements
```
POST /supplements
```
Get supplement recommendations


---

## Capabilities

- nutrition_planning
- macro_tracking
- diet_recommendations
- supplement_guidance

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `bombadil.action.completed`
- `bombadil.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name bombadil \
  --network leveredge-fleet-net \
  -p 8101:8101 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  bombadil:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d bombadil
```

---

*Generated: 2026-01-20 03:27*
