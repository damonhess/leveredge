# LITTLEFINGER

**Port:** 8020
**Domain:** CHANCERY
**Status:** ✅ Operational

---

## Identity

**Name:** LITTLEFINGER
**Title:** Master of Coin
**Tagline:** "Gold wins wars without a single sword drawn"

## Purpose

LITTLEFINGER manages financial operations, tracks revenue, monitors expenses, and provides financial analytics across the LeverEdge ecosystem.

---

## API Endpoints

### Health
```
GET /health
```

### Transactions
```
GET /transactions
GET /transactions/{id}
POST /transactions
```

### Revenue
```
GET /revenue/summary
GET /revenue/by-client
GET /revenue/forecast
```

### Expenses
```
GET /expenses
POST /expenses
GET /expenses/by-category
```

### Reports
```
GET /reports/pnl
GET /reports/cashflow
GET /reports/runway
```

---

## Transaction Model

```json
{
  "id": "uuid",
  "type": "income|expense",
  "amount": 1000.00,
  "currency": "USD",
  "category": "string",
  "description": "string",
  "client_id": "uuid",
  "date": "date",
  "status": "pending|completed|cancelled"
}
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `littlefinger_revenue_summary` | Get revenue overview |
| `littlefinger_expense_track` | Track an expense |
| `littlefinger_pnl_report` | Generate P&L report |
| `littlefinger_forecast` | Revenue forecast |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `transactions` | All financial transactions |
| `revenue_entries` | Revenue records |
| `expense_entries` | Expense records |
| `financial_reports` | Generated reports |

---

## Categories

### Income Categories
- Consulting
- Retainer
- Project
- Training
- Licensing

### Expense Categories
- Infrastructure
- Software
- Contractors
- Marketing
- Operations

---

## Integration Points

### Calls To
- VARYS for client data
- External accounting APIs
- Bank APIs (future)

### Called By
- ARIA for financial queries
- n8n for automated tracking
- Claude Code

---

## Deployment

```bash
docker run -d --name littlefinger \
  --network leveredge-network \
  -p 8020:8020 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  littlefinger:dev
```

---

## Changelog

- 2026-01-19: Documentation created
- 2026-01-18: Initial deployment
