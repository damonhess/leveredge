# CONVENER

**Port:** 8025
**Domain:** ARIA_SANCTUM
**Status:** ✅ Operational

---

## Identity

**Name:** CONVENER
**Title:** Council Facilitator
**Tagline:** "Bringing minds together"

## Purpose

CONVENER facilitates Council meetings - multi-agent deliberations where different AI personas provide diverse perspectives on complex decisions.

---

## API Endpoints

### Health
```
GET /health
```

### Start Council
```
POST /council/start
{
  "topic": "Strategic decision topic",
  "context": "Background information",
  "participants": ["ARIA", "MAGNUS", "VARYS"],
  "rounds": 3
}
```

### Council Status
```
GET /council/{session_id}
```

### Add Input
```
POST /council/{session_id}/input
{
  "message": "Additional context or question"
}
```

---

## Council Participants

Each participant brings a unique perspective:

| Participant | Perspective |
|-------------|-------------|
| ARIA | Personal, emotional, loyalty |
| MAGNUS | Project management, execution |
| VARYS | Intelligence, strategic |
| LITTLEFINGER | Financial, ROI |
| SCHOLAR | Research, evidence-based |

---

## Council Flow

1. **Topic Introduction** - CONVENER presents the decision
2. **Round 1** - Each participant gives initial perspective
3. **Round 2** - Participants respond to each other
4. **Round 3** - Final positions and recommendations
5. **Synthesis** - CONVENER summarizes consensus/dissent

---

## Session Model

```json
{
  "id": "uuid",
  "topic": "string",
  "status": "active|completed|cancelled",
  "participants": ["ARIA", "MAGNUS"],
  "rounds": [
    {
      "number": 1,
      "contributions": [
        {
          "participant": "ARIA",
          "content": "..."
        }
      ]
    }
  ],
  "synthesis": "Final summary"
}
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `convener_start_council` | Start a council session |
| `convener_get_session` | Get session details |
| `convener_add_input` | Add input to session |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `council_sessions` | Session records |
| `council_contributions` | Participant inputs |
| `council_syntheses` | Final summaries |

---

## Integration Points

### Calls To
- ARIA for personal perspective
- MAGNUS for project view
- VARYS for intelligence
- Other participant agents

### Called By
- ARIA when facing complex decisions
- Claude Code for strategic planning
- n8n for automated deliberations

---

## Deployment

```bash
docker run -d --name convener \
  --network leveredge-network \
  -p 8025:8025 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  convener:dev
```

---

## Changelog

- 2026-01-19: Documentation created
- 2026-01-18: Initial deployment
