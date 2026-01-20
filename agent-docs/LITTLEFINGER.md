# PLUTUS

**Port:** 8205
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** PLUTUS
**Description:** Financial Analyst - Budgets, ROI, analysis

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "littlefinger",
  "port": 8205
}
```

---

## Actions

### analyze-financials
```
POST /analyze
```
Analyze financial data

### calculate-roi
```
POST /roi
```
Calculate ROI for investment


---

## Capabilities

- financial_analysis
- budget_planning
- investment_guidance
- roi_calculations

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `littlefinger.action.completed`
- `littlefinger.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name littlefinger \
  --network leveredge-fleet-net \
  -p 8205:8205 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  littlefinger:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d littlefinger
```

---

*Generated: 2026-01-20 03:27*
