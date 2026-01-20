# CRITIC

**Port:** 8034
**Category:** creative
**Status:** LLM-Powered

---

## Identity

**Name:** CRITIC
**Description:** Reviewer - QA, brand compliance, fact-check

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "critic",
  "port": 8034
}
```

---

## Actions

### review
```
POST /review
```
Review any content type

### review-video
```
POST /review/video
```
Review video quality

### review-text
```
POST /review/text
```
Review text for grammar and tone

### fact-check
```
POST /fact-check
```
Verify facts via SCHOLAR


---

## Capabilities

- brand_compliance
- quality_assurance
- fact_checking
- video_review
- accessibility_check

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `critic.action.completed`
- `critic.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name critic \
  --network leveredge-fleet-net \
  -p 8034:8034 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  critic:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d critic
```

---

*Generated: 2026-01-20 03:27*
