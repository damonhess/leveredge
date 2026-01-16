# PHASE 4 AGENTS: Add n8n Workflow Layer

*Created: January 16, 2026*
*Status: URGENT - Architecture fix*

---

## Problem

GSD built Phase 4 agents as FastAPI-only. They should have n8n workflows like CHRONOS/HADES.

## Pattern to Follow

Look at CHRONOS workflow (ID: qChUsjmSZDFX0qnG):
```
Webhook → Switch (by action) → HTTP Request to FastAPI → Response
```

## Agents to Fix

### HERMES (port 8014)
```
Webhook: /webhook/hermes
Actions: notify, request-approval, pending, health
Backend: http://hermes:8014
```

### ARGUS (port 8016)
```
Webhook: /webhook/argus
Actions: status, status/{agent}, metrics, alert, health
Backend: http://argus:8016
```

### ALOY (port 8015)
```
Webhook: /webhook/aloy
Actions: audit/recent, audit/report, anomalies, analyze, health
Backend: http://aloy:8015
```

### ATHENA (port 8013)
```
Webhook: /webhook/athena
Actions: generate/report, generate/architecture, docs, update/{doc}, health
Backend: http://athena:8013
```

## Workflow Template

Each workflow needs:
1. Webhook node with webhookId
2. Switch node routing by action
3. HTTP Request nodes calling FastAPI
4. Respond to Webhook node

## Docker Network

All agents already on control-plane-net. n8n can reach them by service name.

## Execution

Use n8n-troubleshooter MCP to create workflows in control n8n (port 5679).

## Verification

After creation:
```bash
curl https://control.n8n.leveredgeai.com/webhook/hermes -d '{"action":"health"}'
curl https://control.n8n.leveredgeai.com/webhook/argus -d '{"action":"health"}'
curl https://control.n8n.leveredgeai.com/webhook/aloy -d '{"action":"health"}'
curl https://control.n8n.leveredgeai.com/webhook/athena -d '{"action":"health"}'
```
