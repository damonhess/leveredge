# ATLAS-INFRA

**Port:** 8208
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** ATLAS-INFRA
**Description:** Infrastructure Advisor - Cloud architecture, scaling

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "atlas-infra",
  "port": 8208
}
```

---

## Actions

### design-architecture
```
POST /design
```
Design cloud architecture

### optimize-costs
```
POST /optimize
```
Optimize infrastructure costs


---

## Capabilities

- cloud_architecture
- infrastructure_planning
- scaling_recommendations
- cost_optimization

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `atlas-infra.action.completed`
- `atlas-infra.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name atlas-infra \
  --network leveredge-fleet-net \
  -p 8208:8208 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  atlas-infra:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d atlas-infra
```

---

*Generated: 2026-01-20 03:27*
