# DAEDALUS

**Port:** 8202
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** DAEDALUS
**Description:** Workflow Builder - Automation design, n8n workflows

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "daedalus",
  "port": 8202
}
```

---

## Actions

### design-workflow
```
POST /design
```
Design automation workflow

### optimize-workflow
```
POST /optimize
```
Optimize existing workflow


---

## Capabilities

- workflow_design
- automation_planning
- integration_planning
- n8n_workflows

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `daedalus.action.completed`
- `daedalus.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name daedalus \
  --network leveredge-fleet-net \
  -p 8202:8202 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  daedalus:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d daedalus
```

---

*Generated: 2026-01-20 03:27*
