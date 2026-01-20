# HERACLES

**Port:** 8200
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** HERACLES
**Description:** Project Manager - Planning, tracking, sprints

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "tyrion",
  "port": 8200
}
```

---

## Actions

### plan-project
```
POST /plan
```
Create project plan

### break-down-task
```
POST /break-down
```
Break large task into subtasks


---

## Capabilities

- project_planning
- task_management
- sprint_management
- resource_allocation

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `tyrion.action.completed`
- `tyrion.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name tyrion \
  --network leveredge-fleet-net \
  -p 8200:8200 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  tyrion:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d tyrion
```

---

*Generated: 2026-01-20 03:27*
