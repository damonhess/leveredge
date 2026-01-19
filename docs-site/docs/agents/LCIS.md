# LCIS - LeverEdge Collective Intelligence System

**Ports:** 8050 (LIBRARIAN) / 8052 (ORACLE)
**Domain:** GAIA
**Status:** ✅ Operational

---

## Identity

**Name:** LCIS
**Title:** Collective Intelligence
**Tagline:** "Fail once, learn forever"

## Purpose

LCIS provides institutional memory for the LeverEdge system. It captures failures, successes, and lessons learned to prevent repeated mistakes and promote successful patterns.

---

## Components

### LIBRARIAN (Port 8050)
Ingests knowledge into the system.

### ORACLE (Port 8052)
Consults knowledge before actions.

---

## LIBRARIAN API

### Health
```
GET /health
```

### Ingest Knowledge
```
POST /ingest
{
  "content": "Description of what happened",
  "type": "failure|success|warning|insight|anti_pattern",
  "domain": "THE_KEEP|SENTINELS|CHANCERY|ARIA_SANCTUM|ALCHEMY",
  "title": "Short title",
  "solution": "How to fix/replicate",
  "severity": "critical|high|medium|low",
  "source_agent": "AGENT_NAME",
  "source_type": "claude_code|n8n|manual",
  "tags": ["tag1", "tag2"]
}
```

### Dashboard
```
GET /dashboard
```

---

## ORACLE API

### Health
```
GET /health
```

### Consult Before Action
```
POST /consult
{
  "action": "Description of intended action",
  "domain": "THE_KEEP",
  "agent": "CLAUDE_CODE"
}
```

Response:
```json
{
  "blocked": false,
  "warnings": [
    {
      "title": "Warning title",
      "content": "Details",
      "severity": "medium"
    }
  ],
  "related_failures": [...],
  "recommendations": [...]
}
```

### List Rules
```
GET /rules
```

### Get Context
```
GET /context/{agent}
```

---

## Knowledge Types

| Type | Description | Example |
|------|-------------|---------|
| `failure` | Something that broke | "Direct SQL update broke n8n versioning" |
| `success` | Something that worked | "Using MCP tools for workflow updates" |
| `warning` | Potential issue | "Container restart doesn't reload baked files" |
| `insight` | Useful knowledge | "ARIA prompt requires specific keywords" |
| `anti_pattern` | Common mistake | "Editing production without DEV test" |

---

## Domains

| Domain | Description |
|--------|-------------|
| THE_KEEP | Infrastructure, Docker, backups |
| SENTINELS | Security, credentials, auth |
| CHANCERY | Business, clients, projects |
| ARIA_SANCTUM | ARIA personality and prompts |
| ALCHEMY | Creative content, writing |

---

## Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| `critical` | System-breaking | Block action |
| `high` | Major impact | Strong warning |
| `medium` | Moderate impact | Warning |
| `low` | Minor impact | Note |

---

## Active Rules

Default seed rules:
1. **No Direct Prod Database Modifications** - DEV first
2. **Docker Image Rebuild Required** - Restart won't reload baked files
3. **ARIA Prompt Protection** - Use proper update script
4. **No n8n Workflow SQL Updates** - Use MCP tools
5. **Git Commit Before Major Changes** - Checkpoint first

---

## Integration with Claude Code

Before risky operations:
```bash
curl -s -X POST http://localhost:8052/consult \
  -H "Content-Type: application/json" \
  -d '{
    "action": "Restart aria-chat container",
    "domain": "ARIA_SANCTUM",
    "agent": "CLAUDE_CODE"
  }' | jq .
```

After failures:
```bash
curl -s -X POST http://localhost:8050/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Container restart did not load new prompt",
    "type": "failure",
    "domain": "ARIA_SANCTUM",
    "title": "Prompt not loaded after restart",
    "solution": "Rebuild image with docker build",
    "severity": "high",
    "source_agent": "CLAUDE_CODE",
    "source_type": "claude_code",
    "tags": ["docker", "aria", "prompt"]
  }' | jq .
```

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `lcis_knowledge` | All knowledge entries |
| `lcis_rules` | Active blocking/warning rules |
| `lcis_consultations` | Query history |

---

## Deployment

```bash
# LIBRARIAN
docker run -d --name lcis-librarian \
  --network leveredge-network \
  -p 8050:8050 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  lcis-librarian:dev

# ORACLE
docker run -d --name lcis-oracle \
  --network leveredge-network \
  -p 8052:8052 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  lcis-oracle:dev
```

---

## Changelog

- 2026-01-19: Production deployment
- 2026-01-18: Initial implementation
