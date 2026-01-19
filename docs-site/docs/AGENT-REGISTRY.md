# LeverEdge Agent Fleet Registry

**Last Updated:** 2026-01-19
**Total Agents:** 50+
**Status:** Production-ready

---

## Quick Reference

| Agent | Port | Domain | Status | Purpose |
|-------|------|--------|--------|---------|
| GAIA (n8n) | 5678/5679/5680 | GAIA | ✅ | Core workflow orchestration |
| ATLAS | 8208 | GAIA | ✅ | Orchestration & pipeline engine |
| HEPHAESTUS | 8011/8207 | GAIA | ✅ | MCP server, file ops |
| EVENT-BUS | 8099 | GAIA | ✅ | Inter-agent communication |
| CHRONOS | 8010 | THE_KEEP | ✅ | Backup & scheduling |
| HADES | 8008 | THE_KEEP | ✅ | Disaster recovery |
| AEGIS | 8012 | THE_KEEP | ✅ | Credential management |
| HERMES | 8014 | THE_KEEP | ✅ | Notifications |
| CERBERUS | 8022 | THE_KEEP | ✅ | Gate keeper, auth |
| DAEDALUS | 8026 | THE_KEEP | ⏳ | Infrastructure architect |
| PANOPTES | 8023 | SENTINELS | ✅ | System monitoring |
| ASCLEPIUS | 8024 | SENTINELS | ✅ | Health diagnostics |
| ARGUS | 8016 | SENTINELS | ✅ | Security scanning |
| ALOY | 8015 | SENTINELS | ✅ | Performance evaluation |
| ARIA | 8111/8114/8115 | ARIA_SANCTUM | ✅ | Personal AI assistant |
| CONVENER | 8025 | ARIA_SANCTUM | ✅ | Council facilitation |
| MAGNUS | 8019 | CHANCERY | ✅ | Project management |
| VARYS | 8018 | CHANCERY | ✅ | Intelligence gathering |
| LITTLEFINGER | 8020 | CHANCERY | ✅ | Finance management |
| SCHOLAR | 8018 | CHANCERY | ✅ | Research agent |
| CHIRON | 8017 | CHANCERY | ✅ | Planning agent |
| ATHENA | 8013 | CHANCERY | ✅ | Documentation |
| LCIS_LIBRARIAN | 8050 | GAIA | ✅ | Knowledge ingestion |
| LCIS_ORACLE | 8052 | GAIA | ✅ | Knowledge consultation |
| HERACLES | 8200 | OLYMPUS | ✅ | Business development |
| LIBRARIAN | 8201 | OLYMPUS | ✅ | Knowledge management |
| WORKFLOW-BUILDER | 8202 | OLYMPUS | ✅ | n8n workflow generation |
| THEMIS | 8203 | OLYMPUS | ✅ | Compliance & legal |
| MENTOR | 8204 | OLYMPUS | ✅ | Training & guidance |
| PLUTUS | 8205 | OLYMPUS | ✅ | Financial analysis |
| PROCUREMENT | 8206 | OLYMPUS | ✅ | Vendor management |
| IRIS | 8209 | OLYMPUS | ✅ | Communications |
| NUTRITIONIST | 8101 | PERSONAL | ✅ | Meal planning |
| MEAL-PLANNER | 8102 | PERSONAL | ✅ | Recipe suggestions |
| ACADEMIC-GUIDE | 8103 | PERSONAL | ✅ | Study assistance |
| EROS | 8104 | PERSONAL | ✅ | Relationship coach |
| GYM-COACH | 8110 | PERSONAL | ✅ | Fitness training |
| PORT-MANAGER | 8021 | INFRA | ✅ | Port allocation |

**Legend:**
- ✅ Deployed and operational
- ⏳ Planned or in development
- ❌ Down or disabled

---

## Domains

### GAIA (Foundation)
Core infrastructure and orchestration.

| Agent | Port | Role |
|-------|------|------|
| n8n (PROD) | 5678 | Production workflow automation |
| n8n (DEV) | 5680 | Development workflow automation |
| n8n (CONTROL) | 5679 | Control plane workflows |
| ATLAS | 8208 | Orchestration engine, pipeline execution |
| HEPHAESTUS | 8011 | MCP server, file and command operations |
| HEPHAESTUS-HTTP | 8207 | HTTP interface for HEPHAESTUS |
| EVENT-BUS | 8099 | Publish/subscribe event messaging |
| LCIS_LIBRARIAN | 8050 | Collective intelligence ingestion |
| LCIS_ORACLE | 8052 | Collective intelligence consultation |

### THE_KEEP (Infrastructure)
System maintenance and protection.

| Agent | Port | Role |
|-------|------|------|
| CHRONOS | 8010 | Automated backups and scheduling |
| HADES | 8008 | Disaster recovery and rollback |
| AEGIS | 8012 | Credential and secrets management |
| HERMES | 8014 | Notifications and alerts |
| CERBERUS | 8022 | Authentication gateway |
| DAEDALUS | 8026 | Infrastructure architecture (planned) |

### SENTINELS (Security/Monitoring)
System observation and protection.

| Agent | Port | Role |
|-------|------|------|
| PANOPTES | 8023 | Real-time system monitoring |
| ASCLEPIUS | 8024 | Health diagnostics and healing |
| ARGUS | 8016 | Security scanning |
| ALOY | 8015 | Performance evaluation |
| Prometheus | 9090 | Metrics collection |
| Grafana | 3000 | Metrics visualization |
| cAdvisor | 8080 | Container metrics |
| Node Exporter | 9100 | Host metrics |

### CHANCERY (Business Operations)
Business logic and decision support.

| Agent | Port | Role |
|-------|------|------|
| MAGNUS | 8019 | Universal project management (7 PM tools) |
| VARYS | 8018 | Intelligence and portfolio tracking |
| LITTLEFINGER | 8020 | Financial management |
| SCHOLAR | 8018 | Deep research |
| CHIRON | 8017 | Strategic planning |
| ATHENA | 8013 | Documentation and knowledge |

### OLYMPUS (Enterprise Services)
Business-focused agent services.

| Agent | Port | Role |
|-------|------|------|
| HERACLES | 8200 | Business development |
| LIBRARIAN | 8201 | Knowledge management |
| WORKFLOW-BUILDER | 8202 | n8n workflow generation |
| THEMIS | 8203 | Compliance and legal |
| MENTOR | 8204 | Training and guidance |
| PLUTUS | 8205 | Financial analysis |
| PROCUREMENT | 8206 | Vendor management |
| IRIS | 8209 | Communications |

### ALCHEMY (Creative)
Content creation and transformation.

| Agent | Port | Role |
|-------|------|------|
| MUSE | 8032 | Creative ideation |
| QUILL | 8033 | Content writing |
| STAGE | 8034 | Visual design |
| REEL | 8035 | Video production |
| CRITIC | 8036 | Quality review |

### ARIA_SANCTUM (Personal AI)
Damon's personal AI ecosystem.

| Agent | Port | Role |
|-------|------|------|
| ARIA (DEV) | 8114 | Personal AI assistant (development) |
| ARIA (PROD) | 8115 | Personal AI assistant (production) |
| CONVENER | 8025 | Council meeting facilitation |

### PERSONAL (Life Management)
Personal productivity and wellness agents.

| Agent | Port | Role |
|-------|------|------|
| NUTRITIONIST | 8101 | Nutrition guidance |
| MEAL-PLANNER | 8102 | Recipe and meal suggestions |
| ACADEMIC-GUIDE | 8103 | Study assistance |
| EROS | 8104 | Relationship coaching |
| GYM-COACH | 8110 | Fitness training |

---

## Communication Patterns

### Event Bus (Port 8099)
All agents can publish/subscribe to events.

```bash
# Publish event
curl -X POST http://localhost:8099/publish \
  -H "Content-Type: application/json" \
  -d '{"event": "task_completed", "agent": "MAGNUS", "data": {...}}'

# Subscribe
curl -X POST http://localhost:8099/subscribe \
  -d '{"events": ["task_*"], "callback": "http://my-agent:8000/webhook"}'
```

### Direct HTTP
Agents call each other via REST APIs.

### MCP Integration
HEPHAESTUS exposes agent tools via MCP protocol.

---

## Network Configuration

All agents run on `leveredge-network` Docker network.

### Internal Communication
Uses container names:
- `http://gaia:8000`
- `http://magnus:8017`
- `http://aria-chat-dev:8113`
- `http://event-bus:8099`

### External Access via Caddy
- `https://gaia.leveredgeai.com`
- `https://aria.leveredgeai.com`
- `https://n8n.leveredgeai.com`
- `https://dev.n8n.leveredgeai.com`

---

## Database Architecture

### Supabase PROD (Port 54322)
- Production data
- ARIA conversations
- Client portfolios

### Supabase DEV (Port 54323)
- Development testing
- Migration staging
- All agent tables

### n8n Databases
- `prod-n8n-postgres` - Production workflows
- `dev-n8n-postgres` - Development workflows
- `control-n8n-postgres` - Control plane workflows

---

## MCP Servers

| Server | Port | Target |
|--------|------|--------|
| HEPHAESTUS | 8011 | File ops, commands |
| n8n-control | - | Control plane n8n |
| n8n-troubleshooter | 8001 | PROD n8n |
| n8n-troubleshooter-dev | 8002 | DEV n8n |
| mcp-leantime | - | Leantime PM |
| mcp-openproject | - | OpenProject PM |
| playwright-mcp | 3001 | Browser automation |

---

## Quick Health Check

```bash
# Check all agents
for port in 8010 8011 8014 8015 8016 8019 8050 8052 8099; do
  curl -s http://localhost:$port/health 2>/dev/null | jq -r '.service // "unknown"' || echo "port $port: down"
done
```

---

*"An army of specialists, coordinated as one."*
