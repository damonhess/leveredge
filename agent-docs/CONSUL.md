# CONSUL

**Port:** 8021
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** CONSUL
**Description:** External project manager - client projects, PM tool integration

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "consul",
  "port": 8021
}
```

---

## Actions

### list-projects
```
GET /projects
```
List all managed projects

### create-project
```
POST /projects/create
```
Create new project

### get-project
```
GET /projects/{id}
```
Get project details

### sync-project
```
POST /projects/{id}/sync
```
Sync project with external PM system

### list-connections
```
GET /connections
```
List PM system connections


---

## Capabilities

- project_management
- pm_integration
- resource_allocation
- deliverable_tracking
- methodology_support

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `consul.action.completed`
- `consul.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name consul \
  --network leveredge-fleet-net \
  -p 8021:8021 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  consul:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d consul
```

---

*Generated: 2026-01-20 03:27*
