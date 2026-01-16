# GSD ROADMAP - January 16, 2026

**CHRONOS Backup:** `__20260116_053456`
**Rollback:** Call HADES if anything breaks

---

## TRACK 1: Phase 4 Agent n8n Workflows

### Background
GSD built Phase 4 agents (HERMES, ARGUS, ALOY, ATHENA) as FastAPI-only.
They need n8n workflow wrappers like CHRONOS for consistent access pattern.

### Pattern (from CHRONOS workflow qChUsjmSZDFX0qnG)
```
Webhook → AI Agent (Claude Sonnet) → Respond to Webhook
         ↑
    Tool nodes: Event Bus, Health, Action-specific endpoints
```

### Tasks

| # | Agent | Webhook | Backend | Actions |
|---|-------|---------|---------|---------|
| 1.1 | HERMES | /webhook/hermes | http://hermes:8014 | notify, request-approval, pending, health |
| 1.2 | ARGUS | /webhook/argus | http://argus:8016 | status, status/{agent}, metrics, alert, health |
| 1.3 | ALOY | /webhook/aloy | http://aloy:8015 | audit/recent, audit/report, anomalies, analyze, health |
| 1.4 | ATHENA | /webhook/athena | http://athena:8013 | generate/report, generate/architecture, docs, update/{doc}, health |

### Execution Steps (per agent)
1. Create workflow with n8n-troubleshooter MCP
2. Configure webhook with unique webhookId
3. Add AI Agent node with Claude Sonnet
4. Add tool nodes for each endpoint
5. Add Event Bus logging tool
6. Activate workflow
7. Test with health check curl

### Verification
```bash
curl https://control.n8n.leveredgeai.com/webhook/hermes -d '{"action":"health"}'
curl https://control.n8n.leveredgeai.com/webhook/argus -d '{"action":"health"}'
curl https://control.n8n.leveredgeai.com/webhook/aloy -d '{"action":"health"}'
curl https://control.n8n.leveredgeai.com/webhook/athena -d '{"action":"health"}'
```

---

## TRACK 2: Data Plane Migration

### Current State
- **PROD**: `/home/damon/stack/` - n8n on port 5678 (ARIA Jan 13)
- **DEV**: Same docker-compose, different DB (n8n_dev) - ARIA Jan 14 (**NEWER**)
- Both use shared `n8n-postgres` container with Docker volumes

### Target State
```
/opt/leveredge/data-plane/
├── prod/n8n/           # port 5678, Docker volume n8n_postgres_data
└── dev/n8n/            # port 5680, Docker volume n8n_dev_data
```

### Critical Notes
- **DO NOT stop old containers until new verified**
- **DEV is source of truth** - has newer ARIA
- Current setup uses Docker volumes, not host paths
- Single postgres serves both (different DBs)

### Tasks

| # | Task | Notes |
|---|------|-------|
| 2.1 | Create directory structure | mkdir -p prod/n8n, dev/n8n |
| 2.2 | Get credentials from stack/.env | POSTGRES_PASSWORD, OPENAI_API_KEY |
| 2.3 | Create prod docker-compose.yml | Port 5678, DB=n8n, volume=n8n_postgres_data |
| 2.4 | Create dev docker-compose.yml | Port 5680, DB=n8n_dev, volume=n8n_dev_data |
| 2.5 | Create .env files | Copy creds from stack/.env |
| 2.6 | Start new containers (parallel to old) | docker compose up -d |
| 2.7 | Verify ARIA accessible | Test webhooks on both |
| 2.8 | Stop old containers | Only after verification |
| 2.9 | Promote DEV ARIA to PROD | Export/import newer workflows |

### Volume Strategy
```yaml
# PROD uses existing volume
volumes:
  n8n_postgres_data:
    external: true
    name: stack_n8n_postgres_data

# DEV uses existing volume
volumes:
  n8n_dev_data:
    external: true
    name: stack_n8n_dev_data
```

### Verification
```bash
curl https://n8n.leveredgeai.com/webhook/aria-health
curl https://dev.n8n.leveredgeai.com/webhook/aria-health
```

---

## FINAL STEPS

| # | Task |
|---|------|
| 3.1 | Verify all Phase 4 webhooks respond |
| 3.2 | Verify prod n8n accessible at n8n.leveredgeai.com |
| 3.3 | Verify dev n8n accessible at dev.n8n.leveredgeai.com |
| 3.4 | Git add and commit all changes |

---

## GSD EXECUTION ORDER

Execute each track with fresh GSD agent for clean context:

### GSD Agent 1: Track 1 - Phase 4 Workflows
```
Prompt: Create n8n workflows for HERMES, ARGUS, ALOY, ATHENA following CHRONOS pattern.
Use n8n-troubleshooter MCP. Activate and verify each.
```

### GSD Agent 2: Track 2 - Data Plane Migration
```
Prompt: Execute data plane migration per DATA-PLANE-MIGRATION-SPEC.md.
Create structure, docker-compose files, start new containers, verify, then stop old.
```

### GSD Agent 3: Verification & Commit
```
Prompt: Verify all webhooks respond, git commit everything.
```

---

## ROLLBACK

If anything breaks:
```bash
# Call HADES for automated rollback
curl https://control.n8n.leveredgeai.com/webhook/hades \
  -H "Content-Type: application/json" \
  -d '{"action":"rollback","backup_id":"__20260116_053456","confirm":true}'
```

Manual fallback:
```bash
# Restart old containers
cd /home/damon/stack && docker compose up -d n8n n8n-postgres n8n-dev
```
