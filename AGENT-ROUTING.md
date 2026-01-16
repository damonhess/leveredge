# LEVEREDGE AGENT ROUTING RULES

**MANDATORY: All operations flow through designated agents.**
**NO floating commands. NO bypassing agents.**

---

## Quick Reference

| Task | Agent | How |
|------|-------|-----|
| File read/write/create | HEPHAESTUS | MCP tool or API |
| Run commands | HEPHAESTUS | MCP tool (whitelisted) |
| Complex multi-step tasks | GSD (Claude Code) | /gsd spec |
| Backup before changes | CHRONOS | API call or GSD |
| Rollback/recovery | HADES | API call |
| Credential management | AEGIS | API call |
| Send notifications | HERMES | API call or Event Bus |
| Check monitoring/metrics | ARGUS | API call |
| Audit logs/anomalies | ALOY | API call |
| Generate documentation | ATHENA | API call |
| Update portfolio | GSD → Supabase + Event Bus | Notify ARIA |
| Update knowledge base | GSD → aria_knowledge + Event Bus | Notify ARIA |
| Emergency restore | GAIA | Manual trigger only |
| Workflow orchestration | ATLAS | Via control n8n |

---

## Detailed Routing Rules

### HEPHAESTUS (Builder) - Port 8011
**Use for:**
- Reading files in /opt/leveredge/
- Creating/editing files
- Listing directories
- Git operations (status, log, diff, commit)
- Docker ps, docker logs
- Simple whitelisted commands

**DO NOT use for:**
- SQL/database operations → GSD
- HTTP requests to external services → GSD
- Complex multi-step tasks → GSD
- Credential values → AEGIS

**Claude Web Access:** ✅ Via MCP
**Claude Code Access:** ✅ Direct + MCP

---

### GSD (Claude Code)
**Use for:**
- Database operations (Supabase, PostgreSQL)
- Complex multi-step tasks
- HTTP requests
- Container exec operations
- Anything requiring full server access
- Tasks that need human-in-loop approval

**Format:** Always as copy-paste `/gsd` block with clear spec

**Claude Web Access:** ❌ (creates spec, user runs)
**Claude Code Access:** ✅ Direct execution

---

### CHRONOS (Backup) - Port 8010
**Use for:**
- Pre-change backups (ALWAYS before destructive ops)
- Scheduled backup verification
- Backup listing and status
- Restore point creation

**Trigger:**
```bash
curl -X POST http://localhost:8010/backup \
  -H "Content-Type: application/json" \
  -d '{"type": "pre-deploy", "component": "name"}'
```

**MANDATORY:** Call CHRONOS before:
- Database migrations
- Workflow changes
- Container modifications
- File deletions

---

### HADES (Rollback) - Port 8008
**Use for:**
- Rolling back failed deployments
- Restoring from CHRONOS backups
- Emergency recovery
- Version rollback in n8n

**Trigger:**
```bash
curl -X POST http://localhost:8008/rollback \
  -H "Content-Type: application/json" \
  -d '{"backup_id": "xxx", "component": "name"}'
```

---

### AEGIS (Credentials) - Port 8012
**Use for:**
- Creating credentials in n8n
- Syncing credential inventory
- Tracking expiration
- Rotation reminders
- Credential audits

**NEVER:**
- Log credential values
- Expose secrets in responses
- Bypass AEGIS for credential ops

**Trigger:**
```bash
# Sync credentials
curl -X POST http://localhost:8012/sync

# List credentials
curl http://localhost:8012/credentials

# Audit
curl http://localhost:8012/audit
```

---

### HERMES (Notifications) - Port 8014
**Use for:**
- Telegram notifications
- Event Bus publishing
- Alert routing
- Multi-channel notifications

**Trigger:**
```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{"channel": "telegram", "message": "text", "priority": "normal"}'
```

**Event Bus:**
```bash
curl -X POST http://localhost:8099/publish \
  -H "Content-Type: application/json" \
  -d '{"event": "type", "data": {...}}'
```

---

### ARGUS (Monitoring) - Port 8016
**Use for:**
- System health checks
- Prometheus metrics
- Container status
- Resource monitoring

**Trigger:**
```bash
curl http://localhost:8016/health
curl http://localhost:8016/metrics
```

---

### ALOY (Audit) - Port 8015
**Use for:**
- Audit log queries
- Anomaly detection
- Activity history
- Compliance checks

**Trigger:**
```bash
curl http://localhost:8015/logs?since=1h
curl http://localhost:8015/anomalies
```

---

### ATHENA (Documentation) - Port 8013
**Use for:**
- Auto-generating docs from code
- Updating README files
- Creating API documentation
- Changelog generation

**Trigger:**
```bash
curl -X POST http://localhost:8013/generate \
  -H "Content-Type: application/json" \
  -d '{"type": "readme", "path": "/opt/leveredge/"}'
```

---

### GAIA (Emergency) - Port 8000
**Use for:**
- Complete system rebuild
- Disaster recovery
- Bootstrap from nothing

**NEVER trigger automatically. Human decision only.**

---

### ATLAS (Orchestrator) - Control n8n
**Use for:**
- Complex workflow chains
- Multi-agent coordination
- Request routing

**Access:** Via control.n8n.leveredgeai.com

---

## ARIA Knowledge Updates

**ARIA must be informed of:**
- Every portfolio update
- Every major deployment
- Every agent status change
- Every system event

**Mechanism:** Event Bus + aria_knowledge table

### Adding Knowledge
```sql
SELECT aria_add_knowledge(
  'category',      -- agent, deployment, decision, lesson, project, event
  'Title',
  'Content description',
  'subcategory',   -- optional
  '{}',            -- metadata JSON
  'source',        -- claude_web, gsd, agent_name
  'importance'     -- critical, high, normal, low
);
```

### Searching Knowledge
```sql
SELECT * FROM aria_search_knowledge('query text', 'category', 10);
```

### Getting Recent Knowledge
```sql
SELECT * FROM aria_get_recent_knowledge('category', 20);
```

### System Status Overview
```sql
SELECT * FROM aria_get_system_status();
```
