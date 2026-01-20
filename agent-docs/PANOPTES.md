# PANOPTES

**Port:** 8023
**Category:** security
**Status:** Defined

---

## Identity

**Name:** PANOPTES
**Description:** The All-Seeing Integrity Guardian - system verification and audit

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "panoptes",
  "port": 8023
}
```

---

## Actions

### scan
```
POST /scan
```
Run full integrity scan

### status
```
GET /status
```
Quick status overview

### dashboard
```
GET /dashboard
```
Dashboard view with key metrics

### ports
```
GET /ports
```
Scan for port conflicts

### verify-agents
```
GET /agents/verify
```
Verify agent identities

### validate-registry
```
GET /registry/validate
```
Validate registry file


---

## Capabilities

- registry_validation
- port_scanning
- identity_verification
- code_scanning
- integrity_reporting

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `panoptes.action.completed`
- `panoptes.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name panoptes \
  --network leveredge-fleet-net \
  -p 8023:8023 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  panoptes:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d panoptes
```

---

*Generated: 2026-01-20 03:27*
