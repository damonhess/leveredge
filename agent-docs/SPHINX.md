# PORT-MANAGER

**Port:** 8021
**Category:** security
**Status:** Defined

---

## Identity

**Name:** PORT-MANAGER
**Description:** Network Manager - Port allocation, service discovery

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "sphinx",
  "port": 8021
}
```

---

## Actions

### allocate
```
POST /allocate
```
Allocate a port for a service

### list-ports
```
GET /ports
```
List all allocated ports

### check-conflicts
```
GET /conflicts
```
Check for port conflicts


---

## Capabilities

- port_allocation
- service_discovery
- network_health
- conflict_resolution

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `sphinx.action.completed`
- `sphinx.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name sphinx \
  --network leveredge-fleet-net \
  -p 8021:8021 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  sphinx:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d sphinx
```

---

*Generated: 2026-01-20 03:27*
