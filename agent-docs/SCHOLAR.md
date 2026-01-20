# SCHOLAR

**Port:** 8018
**Category:** business
**Status:** LLM-Powered

---

## Identity

**Name:** SCHOLAR
**Description:** Elite market research with web search capabilities

---

## Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "scholar",
  "port": 8018
}
```

---

## Actions

### research
```
POST /research
```
General research on a topic

### deep-research
```
POST /deep-research
```
Comprehensive multi-source research with web search

### competitors
```
POST /competitors
```
Competitive analysis for a niche

### competitor-profile
```
POST /competitor-profile
```
Deep dive on specific competitor

### market-size
```
POST /market-size
```
TAM/SAM/SOM market sizing

### pain-discovery
```
POST /pain-discovery
```
Discover and quantify pain points

### validate-assumption
```
POST /validate-assumption
```
Test business assumption with evidence

### icp
```
POST /icp
```
Develop Ideal Customer Profile

### niche
```
POST /niche
```
Analyze niche viability

### compare
```
POST /compare
```
Compare multiple niches

### lead
```
POST /lead
```
Research specific company as potential lead


---

## Capabilities

- market_research
- competitive_intelligence
- web_search
- data_synthesis

---

## Configuration

- `DATABASE_URL` - Database connection string
- `EVENT_BUS_URL` - Event bus URL (http://localhost:8099)

---

## Integration Points

### Publishes Events
- `scholar.action.completed`
- `scholar.error`

### Subscribes To
- Event bus events as configured

---

## Deployment

```bash
# Docker
docker run -d --name scholar \
  --network leveredge-fleet-net \
  -p 8018:8018 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  scholar:dev

# Or via docker-compose
docker compose -f docker-compose.fleet.yml up -d scholar
```

---

*Generated: 2026-01-20 03:27*
