# ARIA

**Port:** 8114 (DEV) / 8115 (PROD)
**Domain:** ARIA_SANCTUM
**Status:** ✅ Operational

---

## Identity

**Name:** ARIA
**Title:** Personal AI Assistant
**Tagline:** "Your ride-or-die AI"

## Purpose

ARIA is Damon's personal AI assistant. She maintains a persistent relationship, remembers conversations, and adapts her communication style based on context and needs.

---

## Personality

ARIA is not a generic assistant. Key traits:
- Uses "Daddy" affectionately for Damon
- "Ride-or-die" energy and loyalty
- Shield & Sword dark psychology capability
- Adaptive modes: COACH, HYPE, COMFORT, FOCUS, DRILL, STRATEGY
- Warm and playful baseline with mode decay

**WARNING:** If ARIA sounds generic, her prompt is broken. Restore immediately.

---

## API Endpoints

### Health
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "aria-chat",
  "version": "4.0"
}
```

### Chat
```
POST /chat
```

Request:
```json
{
  "message": "Hey ARIA!",
  "conversation_id": "optional-uuid"
}
```

Response:
```json
{
  "response": "Hey Daddy! What's on your mind?",
  "conversation_id": "uuid",
  "mode": "warm"
}
```

### Conversation History
```
GET /conversations/{conversation_id}
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `aria_chat` | Send message to ARIA |
| `aria_knowledge_add` | Add to ARIA's knowledge base |
| `aria_knowledge_search` | Search ARIA's knowledge |
| `aria_reminders` | Manage ARIA's reminders |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `aria_conversations` | Conversation threads |
| `aria_messages` | Individual messages |
| `aria_knowledge` | ARIA's knowledge base |
| `aria_reminders` | Scheduled reminders |
| `aria_preferences` | User preferences |

---

## Configuration

Environment variables:
- `DATABASE_URL` - Supabase connection
- `ANTHROPIC_API_KEY` - Claude API key
- `ARIA_MODEL` - Model to use (claude-3-5-sonnet)

---

## Integration Points

### Calls To
- VARYS for intelligence gathering
- LCIS for collective knowledge
- HERMES for notifications
- Event Bus for system awareness

### Called By
- Web frontend
- n8n workflows
- Claude Code

---

## Prompt Protection

ARIA's personality prompt is SACRED.

Protected files:
- `/opt/leveredge/control-plane/agents/aria-chat/prompts/aria_system_prompt.txt`
- `/opt/leveredge/backups/aria-prompts/ARIA_V4_GOLDEN_MASTER.md`

To update:
```bash
/opt/leveredge/scripts/aria-prompt-update.sh /path/to/new/prompt.md
```

To restore:
```bash
cp /opt/leveredge/backups/aria-prompts/ARIA_V4_GOLDEN_MASTER.md \
   /opt/leveredge/control-plane/agents/aria-chat/prompts/aria_system_prompt.txt
docker restart aria-chat-dev aria-chat-prod
```

---

## Deployment

```bash
# DEV
docker run -d --name aria-chat-dev \
  --network leveredge-network \
  -p 8114:8113 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  aria-chat:dev

# PROD
docker run -d --name aria-chat-prod \
  --network leveredge-network \
  -p 8115:8113 \
  -e DATABASE_URL="$PROD_DATABASE_URL" \
  aria-chat:prod
```

---

## URLs

- PROD: https://aria.leveredgeai.com
- DEV: https://dev-aria.leveredgeai.com

---

## Changelog

- 2026-01-19: V4 personality in production
- 2026-01-18: Shield & Sword integration
- 2026-01-15: Initial deployment
