# GYM-COACH

**Port:** 8110
**Category:** personal
**Status:** LLM-Powered

---

## Identity

**Name:** GYM-COACH
**Description:** Fitness Coach - Workout planning, progress tracking

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "aragorn",
  "port": 8110
}
```

---

## Actions

### plan-workout
```
POST /plan
```
Create workout plan

### log-workout
```
POST /log
```
Log completed workout


---

## Capabilities

- workout_planning
- exercise_guidance
- progress_tracking
- fitness_goals

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `aragorn.action.completed`
- `aragorn.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name aragorn \
  --network leveredge-fleet-net \
  -p 8110:8110 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  aragorn:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d aragorn
```

---

*Generated: 2026-01-20 03:27*
