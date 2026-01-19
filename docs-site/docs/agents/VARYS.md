# VARYS

**Port:** 8018
**Domain:** CHANCERY
**Status:** ✅ Operational

---

## Identity

**Name:** VARYS
**Title:** Master of Whispers
**Tagline:** "Information is power"

## Purpose

VARYS is the intelligence gathering agent. It tracks portfolios, monitors business intelligence, and provides insights across the LeverEdge ecosystem.

---

## API Endpoints

### Health
```
GET /health
```

### Portfolio Tracking
```
GET /portfolios
GET /portfolios/{id}
POST /portfolios
PUT /portfolios/{id}
```

### Intelligence
```
GET /intelligence/summary
GET /intelligence/alerts
POST /intelligence/search
```

### Company Research
```
GET /companies/{domain}
POST /companies/enrich
```

---

## Portfolio Model

```json
{
  "id": "uuid",
  "name": "Company Name",
  "domain": "example.com",
  "status": "active|prospect|churned",
  "tier": "enterprise|growth|startup",
  "contacts": [...],
  "notes": [...],
  "last_contact": "datetime",
  "next_action": "string"
}
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `varys_portfolio_list` | List all portfolios |
| `varys_portfolio_get` | Get portfolio details |
| `varys_company_research` | Research a company |
| `varys_intelligence_summary` | Get intelligence briefing |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `portfolios` | Client/prospect records |
| `portfolio_contacts` | Contact information |
| `portfolio_notes` | Activity notes |
| `intelligence_alerts` | Triggered alerts |

---

## Integration Points

### Calls To
- External APIs for company research
- MAGNUS for project status
- LITTLEFINGER for financial data

### Called By
- ARIA for portfolio queries
- n8n for automated updates
- Claude Code

---

## Deployment

```bash
docker run -d --name varys \
  --network leveredge-network \
  -p 8018:8018 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  varys:dev
```

---

## Changelog

- 2026-01-19: Documentation created
- 2026-01-18: Initial deployment
