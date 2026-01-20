# CHIRON

**Port:** 8017
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** CHIRON
**Description:** Elite business davos with ADHD-optimized frameworks

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "chiron",
  "port": 8017
}
```

---

## Actions

### chat
```
POST /chat
```
General strategic conversation

### sprint-plan
```
POST /sprint-plan
```
ADHD-optimized sprint planning

### pricing-help
```
POST /pricing-help
```
Value-based pricing strategy

### fear-check
```
POST /fear-check
```
Rapid fear analysis and reframe

### weekly-review
```
POST /weekly-review
```
Structured weekly accountability

### accountability
```
POST /accountability
```
Accountability check-in

### challenge
```
POST /challenge
```
Challenge assumptions and beliefs

### hype
```
POST /hype
```
Evidence-based motivation boost

### decide
```
POST /decide
```
Decision framework analysis

### framework
```
GET /framework/{name}
```
Get specific framework

### break-down
```
POST /break-down
```
Break large task into ADHD-friendly small steps

### prioritize
```
POST /prioritize
```
Order tasks by impact and urgency using Eisenhower matrix


---

## Capabilities

- strategic_planning
- adhd_optimization
- pricing_strategy
- accountability
- fear_analysis

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `chiron.action.completed`
- `chiron.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name chiron \
  --network leveredge-fleet-net \
  -p 8017:8017 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  chiron:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d chiron
```

---

*Generated: 2026-01-20 03:27*
