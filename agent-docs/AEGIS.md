# AEGIS

**Port:** 8012
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** AEGIS
**Description:** Credential vault and secret management

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "aegis",
  "port": 8012
}
```

---

## Actions

### list
```
GET /credentials
```
List credentials (metadata only)

### get
```
GET /credentials/{name}
```
Get credential metadata

### sync
```
POST /sync
```
Sync credentials from n8n

### audit
```
GET /audit
```
Audit credential access


---

## Capabilities

- credential_storage
- rotation
- audit

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `aegis.action.completed`
- `aegis.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name aegis \
  --network leveredge-fleet-net \
  -p 8012:8012 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  aegis:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d aegis
```

---

*Generated: 2026-01-20 03:27*
