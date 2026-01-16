# GSD SPEC: Phase 4 Agents

*For Claude Code + GSD (Get Shit Done)*
*Created: January 16, 2026*

---

## PROJECT CONTEXT

### What Already Exists

**Infrastructure:**
- Control plane n8n at `control.n8n.leveredgeai.com` (port 5679)
- Event Bus at `localhost:8099` (FastAPI + SQLite)
- PostgreSQL for n8n at `control-n8n-postgres`
- Docker network: `control-plane-net` bridged to `stack_net`
- All services Dockerized in `/opt/leveredge/control-plane/`

**Working Agents:**
| Agent | Port | Type | Status |
|-------|------|------|--------|
| ATLAS | n8n workflow | AI Router | ✅ Active |
| HEPHAESTUS | 8011 | MCP Server (Docker) | ✅ Active |
| AEGIS | 8012 | FastAPI (systemd) | ✅ Active |
| CHRONOS | Docker | Backup Manager | ✅ Active |
| HADES | Docker | Rollback System | ✅ Active |

**Key Files:**
- `/opt/leveredge/control-plane/n8n/docker-compose.yml` - Control plane services
- `/opt/leveredge/control-plane/agents/` - Agent source code
- `/opt/leveredge/shared/backups/` - Backup storage
- `/opt/leveredge/LESSONS-LEARNED.md` - Technical gotchas
- `/opt/leveredge/FUTURE-VISION-AND-EXPLORATION.md` - Architecture decisions

---

## ARCHITECTURE RULES (MUST FOLLOW)

### Agent Pattern
Every agent = **FastAPI backend** + optional **n8n workflow layer**

```
┌─────────────────────────────────────────────────┐
│                 AGENT PATTERN                    │
│                                                  │
│  n8n Workflow (optional)                        │
│  └── Webhook trigger: /webhook/{agent}          │
│  └── Routes to FastAPI backend                  │
│  └── Logs to Event Bus                          │
│                                                  │
│  FastAPI Backend (required)                     │
│  └── Port: assigned per agent                   │
│  └── /health endpoint                           │
│  └── Core logic                                 │
│  └── Logs ALL actions to Event Bus             │
│                                                  │
│  Docker Container                               │
│  └── In control-plane-net network              │
│  └── Volume mounts for persistence             │
└─────────────────────────────────────────────────┘
```

### Option A: Dumb Executors (CURRENT)
- **NO LLM reasoning in agents** - Claude Web is the brain
- Agents execute specs literally
- No per-request costs
- Human always in loop

### Event Bus Integration (REQUIRED)
Every agent action MUST log to Event Bus:
```python
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://event-bus:8099/events",  # Use Docker service name
            json={
                "source_agent": "AGENT_NAME",
                "action": action,
                "target": target,
                "details": details
            },
            timeout=5.0
        )
```

### Docker Networking Lessons
- Use service names (e.g., `event-bus:8099`), NOT `localhost`
- Add to `control-plane-net` network
- Bridge to `stack_net` if needs Caddy access
- Mount `/opt/leveredge/shared/` for shared data

### n8n Workflow Lessons
- Webhooks REQUIRE `webhookId` field in node config
- Use Docker bridge IP `172.17.0.1` to reach host services
- AI Agent nodes take 30-90 seconds (normal)
- Test webhook accessibility immediately after creation

---

## PHASE 4 AGENTS TO BUILD

### Priority Order
1. **HERMES** (HIGH) - Human-in-the-loop approvals via Telegram
2. **ARGUS** (MEDIUM) - Monitoring integration
3. **ALOY** (MEDIUM) - Audit/anomaly detection  
4. **ATHENA** (LOW) - Documentation agent

---

## AGENT 1: HERMES (Notifications)

**Port:** 8014
**Purpose:** Telegram notifications for human-in-the-loop approvals

### Why HERMES Matters
- TIER 2 operations require human approval
- HERMES sends Telegram message → Human replies → Operation proceeds
- Critical for Option B autonomous upgrade later

### Requirements
```
HERMES must:
1. Send Telegram notifications when approval needed
2. Wait for human response (approve/deny)
3. Return approval status to requesting agent
4. Log all approval requests/responses to Event Bus
5. Support timeout (default 5 min, configurable)
6. Queue pending approvals
```

### Endpoints
```
POST /notify
  - Send notification, don't wait for response
  - Body: {message, priority, channel}

POST /request-approval  
  - Send approval request, wait for response
  - Body: {action, details, timeout_seconds, requesting_agent}
  - Returns: {approved: bool, responder, response_time}

GET /pending
  - List pending approval requests

GET /health
  - Health check
```

### Telegram Integration
```python
# Use python-telegram-bot library
# Bot token from /opt/leveredge/gaia/.telegram_token (if exists)
# Or new bot token in /opt/leveredge/control-plane/agents/hermes/.telegram_token

# Approval flow:
# 1. Agent calls POST /request-approval
# 2. HERMES sends Telegram: "🔔 Approval needed: {action}\nReply 'yes' or 'no'"
# 3. HERMES waits for reply (with timeout)
# 4. HERMES returns result to agent
```

### Docker Setup
```yaml
# Add to /opt/leveredge/control-plane/n8n/docker-compose.yml
hermes:
  build: ../agents/hermes
  container_name: hermes
  ports:
    - "8014:8014"
  environment:
    - EVENT_BUS_URL=http://event-bus:8099
    - TELEGRAM_TOKEN_FILE=/run/secrets/telegram_token
  volumes:
    - ../agents/hermes/.telegram_token:/run/secrets/telegram_token:ro
  networks:
    - control-plane-net
  restart: unless-stopped
```

### Files to Create
```
/opt/leveredge/control-plane/agents/hermes/
├── hermes.py           # FastAPI backend
├── requirements.txt    # python-telegram-bot, fastapi, uvicorn, httpx
├── Dockerfile
└── .telegram_token     # Bot token (manual config)
```

---

## AGENT 2: ARGUS (Monitoring)

**Port:** 8009
**Purpose:** Monitoring wrapper, integrates with existing Prometheus/Grafana

### Why ARGUS Matters
- Grafana already exists at grafana.leveredgeai.com
- ARGUS provides agent-friendly interface to metrics
- Can trigger alerts → HERMES → Human

### Requirements
```
ARGUS must:
1. Query Prometheus metrics
2. Provide simplified health status for all agents
3. Detect anomalies (high latency, failures, resource usage)
4. Trigger alerts via HERMES when thresholds exceeded
5. Log monitoring events to Event Bus
```

### Endpoints
```
GET /health
  - Own health check

GET /status
  - Overall system status (all agents, services)

GET /status/{agent}
  - Specific agent status

GET /metrics
  - Simplified metrics summary

POST /alert
  - Manually trigger alert
  - Body: {severity, message, target}
```

### Integration Points
```python
# Prometheus at localhost:9090 (or prometheus:9090 in Docker)
# Query examples:
# - up{job="n8n"} - n8n availability
# - process_cpu_seconds_total - CPU usage
# - container_memory_usage_bytes - Memory per container

# Alert thresholds (configurable):
# - CPU > 80% for 5 min → warning
# - Memory > 90% → critical
# - Agent /health failing → critical
# - Event Bus unreachable → critical
```

### Files to Create
```
/opt/leveredge/control-plane/agents/argus/
├── argus.py            # FastAPI backend
├── requirements.txt    # fastapi, uvicorn, httpx, prometheus-client
├── Dockerfile
└── thresholds.yaml     # Alert thresholds config
```

---

## AGENT 3: ALOY (Audit)

**Port:** 8015
**Purpose:** Audit trail analysis, anomaly detection from Event Bus

### Why ALOY Matters
- Event Bus captures everything
- ALOY watches for suspicious patterns
- Security watchdog for the system

### Requirements
```
ALOY must:
1. Subscribe to Event Bus events
2. Analyze patterns for anomalies
3. Flag suspicious activity (many failures, unusual times, forbidden attempts)
4. Generate audit reports
5. Alert via HERMES on critical anomalies
```

### Endpoints
```
GET /health
  - Health check

GET /audit/recent
  - Recent audit events (last 24h)

GET /audit/report
  - Generate audit report
  - Query params: start_date, end_date, agent_filter

GET /anomalies
  - List detected anomalies

POST /analyze
  - Trigger manual analysis
```

### Anomaly Detection (Simple Rules - Option A)
```python
# No LLM - just rule-based detection
ANOMALY_RULES = {
    "high_failure_rate": {
        "condition": "failures > 10 in 5 minutes",
        "severity": "warning"
    },
    "forbidden_attempt": {
        "condition": "action contains 'blocked' or 'forbidden'",
        "severity": "critical"
    },
    "unusual_hours": {
        "condition": "action between 2am-5am AND not from CHRONOS",
        "severity": "warning"
    },
    "mass_deletion": {
        "condition": "delete actions > 5 in 1 minute",
        "severity": "critical"
    }
}
```

### Files to Create
```
/opt/leveredge/control-plane/agents/aloy/
├── aloy.py             # FastAPI backend
├── requirements.txt    # fastapi, uvicorn, httpx
├── Dockerfile
└── rules.yaml          # Anomaly detection rules
```

---

## AGENT 4: ATHENA (Documentation)

**Port:** 8013
**Purpose:** Documentation agent (Option A = manual trigger, Option B = automatic)

### Why ATHENA Matters
- Keeps documentation up to date
- Generates reports from Event Bus data
- Future: Automatic doc generation on changes

### Requirements (Option A - Manual)
```
ATHENA must:
1. Generate documentation from templates
2. Create reports from Event Bus data
3. Update ARCHITECTURE.md on request
4. Log documentation actions to Event Bus
```

### Endpoints
```
GET /health
  - Health check

POST /generate/report
  - Generate report
  - Body: {report_type, date_range, output_path}

POST /generate/architecture
  - Regenerate ARCHITECTURE.md from current state

GET /docs
  - List available documentation

POST /update/{doc_name}
  - Update specific document
  - Body: {content} or {append: content}
```

### Files to Create
```
/opt/leveredge/control-plane/agents/athena/
├── athena.py           # FastAPI backend
├── requirements.txt    # fastapi, uvicorn, httpx, jinja2
├── Dockerfile
└── templates/          # Report templates
    ├── daily_report.md.j2
    ├── architecture.md.j2
    └── audit_report.md.j2
```

---

## DOCKER-COMPOSE ADDITIONS

Add all Phase 4 agents to `/opt/leveredge/control-plane/n8n/docker-compose.yml`:

```yaml
  hermes:
    build: ../agents/hermes
    container_name: hermes
    ports:
      - "8014:8014"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
    volumes:
      - ../agents/hermes:/app
    networks:
      - control-plane-net
    restart: unless-stopped

  argus:
    build: ../agents/argus
    container_name: argus
    ports:
      - "8009:8009"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - PROMETHEUS_URL=http://host.docker.internal:9090
      - HERMES_URL=http://hermes:8014
    networks:
      - control-plane-net
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

  aloy:
    build: ../agents/aloy
    container_name: aloy
    ports:
      - "8015:8015"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
    networks:
      - control-plane-net
    restart: unless-stopped

  athena:
    build: ../agents/athena
    container_name: athena
    ports:
      - "8013:8013"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
    volumes:
      - ../../:/opt/leveredge
    networks:
      - control-plane-net
    restart: unless-stopped
```

---

## VERIFICATION CHECKLIST

After building each agent:

```bash
# 1. Container running
docker ps | grep {agent}

# 2. Health check passes
curl http://localhost:{port}/health

# 3. Event Bus logging works
curl http://localhost:8099/events | grep {agent}

# 4. Agent can reach Event Bus
docker exec {agent} curl -s http://event-bus:8099/health

# 5. (For HERMES) Telegram bot responds
# Manual test in Telegram

# 6. Git commit
cd /opt/leveredge && git add . && git commit -m "Add {AGENT} agent"
```

---

## GSD EXECUTION ORDER

```
Phase 4.1: HERMES (human-in-the-loop foundation)
Phase 4.2: ARGUS (monitoring, depends on nothing)
Phase 4.3: ALOY (audit, benefits from HERMES for alerts)
Phase 4.4: ATHENA (documentation, lowest priority)
```

Each phase = max 3 GSD tasks, fresh subagent context.

---

## REFERENCE: Existing Agent Code

Look at these for patterns:
- `/opt/leveredge/control-plane/agents/aegis/aegis.py` - FastAPI pattern
- `/opt/leveredge/control-plane/agents/chronos/chronos.py` - Backup pattern
- `/opt/leveredge/control-plane/agents/hades/hades.py` - Rollback pattern
- `/opt/leveredge/control-plane/agents/hephaestus/hephaestus_mcp_server.py` - MCP pattern

---

## SUCCESS CRITERIA

Phase 4 is complete when:
- [ ] HERMES sends Telegram notifications
- [ ] HERMES approval flow works end-to-end
- [ ] ARGUS shows system health status
- [ ] ARGUS can query Prometheus metrics
- [ ] ALOY detects test anomaly
- [ ] ALOY generates audit report
- [ ] ATHENA generates architecture doc
- [ ] All agents logging to Event Bus
- [ ] All agents in docker-compose
- [ ] All committed to git
