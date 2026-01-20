# THEMIS

**Port:** 8203
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** THEMIS
**Description:** Legal Advisor - Contracts, compliance

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "stannis",
  "port": 8203
}
```

---

## Actions

### review-contract
```
POST /review
```
Review contract for issues

### check-compliance
```
POST /compliance
```
Check compliance for situation


---

## Capabilities

- contract_review
- compliance_guidance
- risk_assessment
- policy_recommendations

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `stannis.action.completed`
- `stannis.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name stannis \
  --network leveredge-fleet-net \
  -p 8203:8203 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  stannis:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d stannis
```

---

*Generated: 2026-01-20 03:27*
