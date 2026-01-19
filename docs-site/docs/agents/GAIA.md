# GAIA

**Port:** 5678 (PROD) / 5679 (CONTROL) / 5680 (DEV)
**Domain:** GAIA
**Status:** ✅ Operational

---

## Identity

**Name:** GAIA
**Title:** The Foundation
**Tagline:** "All roads lead through GAIA"

## Purpose

GAIA is the core orchestration layer built on n8n. All workflow automation, agent coordination, and event-driven processes flow through GAIA.

---

## Architecture

### n8n Instances

| Instance | Port | Purpose |
|----------|------|---------|
| PROD | 5678 | Client workflows, production automation |
| DEV | 5680 | Development and testing |
| CONTROL | 5679 | Control plane, agent workflows |

### Database

Each instance has its own PostgreSQL database:
- `prod-n8n-postgres`
- `dev-n8n-postgres`
- `control-n8n-postgres`

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_workflow` | Get workflow details |
| `list_workflows` | List all workflows |
| `activate_workflow` | Enable a workflow |
| `deactivate_workflow` | Disable a workflow |
| `execute_workflow` | Manually trigger execution |
| `get_executions` | View execution history |

---

## Key Workflows

### Control Plane (5679)
- ARIA conversation handling
- Agent health monitoring
- Event bus integration

### Production (5678)
- Client automations
- Business processes
- Scheduled tasks

---

## Configuration

Environment variables:
- `N8N_ENCRYPTION_KEY` - Workflow encryption
- `DB_POSTGRESDB_*` - Database connection
- `N8N_HOST` - External hostname
- `WEBHOOK_URL` - Webhook base URL

---

## Integration Points

### Calls To
- All agents via HTTP nodes
- Supabase for data storage
- External APIs

### Called By
- Claude Code via MCP
- Webhooks from external services
- Scheduled triggers

---

## Deployment

```bash
# Production
cd /opt/leveredge/data-plane/prod/n8n
docker-compose up -d

# Development
cd /opt/leveredge/data-plane/dev/n8n
docker-compose up -d

# Control plane
cd /opt/leveredge/control-plane/n8n
docker-compose up -d
```

---

## URLs

- PROD: https://n8n.leveredgeai.com
- DEV: https://dev.n8n.leveredgeai.com
- CONTROL: Internal only (5679)

---

## Changelog

- 2026-01-19: Documentation created
- 2026-01-15: Three-tier architecture established
