# IRIS

**Port:** 8209
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** IRIS
**Description:** World Events Reporter - News, trends

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "raven",
  "port": 8209
}
```

---

## Actions

### get-news
```
POST /news
```
Get relevant news

### analyze-trends
```
POST /trends
```
Analyze industry trends


---

## Capabilities

- news_reporting
- trend_analysis
- market_updates
- competitive_intelligence

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `raven.action.completed`
- `raven.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name raven \
  --network leveredge-fleet-net \
  -p 8209:8209 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  raven:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d raven
```

---

*Generated: 2026-01-20 03:27*
