# PROCUREMENT

**Port:** 8206
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** PROCUREMENT
**Description:** Procurement Expert - Vendors, costs

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "bronn",
  "port": 8206
}
```

---

## Actions

### evaluate-vendor
```
POST /evaluate
```
Evaluate vendor options

### negotiate-tips
```
POST /negotiate
```
Get negotiation strategies


---

## Capabilities

- vendor_evaluation
- purchase_recommendations
- contract_negotiation
- cost_optimization

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `bronn.action.completed`
- `bronn.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name bronn \
  --network leveredge-fleet-net \
  -p 8206:8206 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  bronn:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d bronn
```

---

*Generated: 2026-01-20 03:27*
