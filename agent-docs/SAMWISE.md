# MEAL-PLANNER

**Port:** 8102
**Category:** personal
**Status:** LLM-Powered

---

## Identity

**Name:** MEAL-PLANNER
**Description:** Meal Planning - Weekly menus, grocery lists

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "samwise",
  "port": 8102
}
```

---

## Actions

### plan-week
```
POST /plan-week
```
Create weekly meal plan

### suggest-recipe
```
POST /suggest
```
Suggest recipe based on ingredients


---

## Capabilities

- meal_planning
- recipe_suggestions
- grocery_lists
- calorie_tracking

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `samwise.action.completed`
- `samwise.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name samwise \
  --network leveredge-fleet-net \
  -p 8102:8102 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  samwise:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d samwise
```

---

*Generated: 2026-01-20 03:27*
