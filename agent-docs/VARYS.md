# VARYS

**Port:** 8020
**Category:** infrastructure
**Status:** Defined

---

## Identity

**Name:** VARYS
**Description:** Mission Guardian - accountability, drift detection, strategic alignment

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "varys",
  "port": 8020
}
```

---

## Actions

### daily-brief
```
POST /daily-brief
```
Generate and send daily accountability brief

### weekly-review
```
POST /weekly-review
```
Generate comprehensive weekly review

### days-to-launch
```
GET /days-to-launch
```
Get days remaining until launch

### todays-focus
```
GET /todays-focus
```
Get today's focus from calendar

### scan-drift
```
GET /scan-drift
```
Scan for scope creep in recent commits

### validate-decision
```
POST /validate-decision
```
Validate a decision against mission alignment

### mission
```
GET /mission/{document}
```
Retrieve sacred mission documents


---

## Capabilities

- accountability
- drift_detection
- mission_alignment
- daily_briefs
- weekly_reviews

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `varys.action.completed`
- `varys.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name varys \
  --network leveredge-fleet-net \
  -p 8020:8020 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  varys:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d varys
```

---

*Generated: 2026-01-20 03:27*
