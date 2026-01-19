# ATLAS

**Port:** 8208
**Domain:** GAIA
**Status:** ✅ Operational

---

## Identity

**Name:** ATLAS
**Title:** The Orchestrator
**Tagline:** "Bearing the weight of coordination"

## Purpose

ATLAS is the orchestration engine that coordinates multi-agent pipelines, manages execution flows, and provides centralized command capabilities.

---

## API Endpoints

### Health
```
GET /health
```

### Pipelines
```
GET /pipelines
GET /pipelines/{id}
POST /pipelines
POST /pipelines/{id}/execute
GET /pipelines/executions/{id}
```

### Agent Coordination
```
POST /coordinate
{
  "agents": ["MAGNUS", "VARYS"],
  "task": "Portfolio update",
  "parallel": true
}
```

---

## Pipeline Model

```json
{
  "id": "uuid",
  "name": "Pipeline Name",
  "description": "What it does",
  "stages": [
    {
      "name": "Stage 1",
      "agent": "MAGNUS",
      "action": "list_projects",
      "depends_on": []
    },
    {
      "name": "Stage 2",
      "agent": "VARYS",
      "action": "enrich_data",
      "depends_on": ["Stage 1"]
    }
  ],
  "trigger": "manual|schedule|webhook"
}
```

---

## Built-in Pipelines

| Pipeline | Description |
|----------|-------------|
| agent-upgrade | Upgrade agent to new version |
| content-creation | Multi-stage content pipeline |
| deep-research | Research with multiple agents |
| client-onboarding | New client setup |

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `atlas_pipeline_list` | List available pipelines |
| `atlas_pipeline_execute` | Execute a pipeline |
| `atlas_pipeline_status` | Check execution status |
| `atlas_coordinate` | Coordinate multiple agents |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `pipeline_definitions` | Pipeline configurations |
| `pipeline_executions` | Execution records |
| `pipeline_stage_logs` | Stage-level logs |

---

## Execution States

| State | Description |
|-------|-------------|
| `pending` | Waiting to start |
| `running` | Currently executing |
| `completed` | Successfully finished |
| `failed` | Execution failed |
| `cancelled` | Manually cancelled |

---

## Integration Points

### Calls To
- All agents via HTTP
- HEPHAESTUS for tool execution
- Supabase for state management

### Called By
- HEPHAESTUS MCP tools
- n8n workflows
- Claude Code

---

## Deployment

```bash
docker run -d --name atlas \
  --network leveredge-network \
  -p 8208:8208 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  atlas:dev
```

---

## Changelog

- 2026-01-19: Pipeline system added
- 2026-01-18: Initial deployment
