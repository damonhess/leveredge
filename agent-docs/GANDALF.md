# ACADEMIC-GUIDE

**Port:** 8103
**Category:** personal
**Status:** LLM-Powered

---

## Identity

**Name:** ACADEMIC-GUIDE
**Description:** Education Coach - Learning paths, study optimization

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "gandalf",
  "port": 8103
}
```

---

## Actions

### plan-learning
```
POST /plan
```
Create learning plan for skill/topic

### recommend-courses
```
POST /courses
```
Recommend courses for goal


---

## Capabilities

- learning_paths
- study_planning
- skill_development
- course_recommendations

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `gandalf.action.completed`
- `gandalf.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name gandalf \
  --network leveredge-fleet-net \
  -p 8103:8103 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  gandalf:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d gandalf
```

---

*Generated: 2026-01-20 03:27*
