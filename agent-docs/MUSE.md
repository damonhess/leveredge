# MUSE

**Port:** 8030
**Category:** creative
**Status:** LLM-Powered

---

## Identity

**Name:** MUSE
**Description:** Creative Director - Coordinator for content production

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "muse",
  "port": 8030
}
```

---

## Actions

### create-project
```
POST /projects/create
```
Create new creative project with task decomposition

### get-project
```
GET /projects/{id}
```
Get project status and progress

### storyboard
```
POST /storyboard
```
Create video storyboard


---

## Capabilities

- project_coordination
- task_decomposition
- storyboarding
- workflow_management

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `muse.action.completed`
- `muse.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name muse \
  --network leveredge-fleet-net \
  -p 8030:8030 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  muse:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d muse
```

---

*Generated: 2026-01-20 03:27*
