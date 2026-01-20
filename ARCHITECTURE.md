# LEVEREDGE ARCHITECTURE

*Last Updated: January 20, 2026*

---

## Visual Architecture

### High-Level Network Topology

```
                                    ┌─────────────────┐
                                    │    INTERNET     │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │   CLOUDFLARE    │
                                    │   (CDN + WAF)   │
                                    └────────┬────────┘
                                             │
                                    ┌────────▼────────┐
                                    │     CADDY       │
                                    │ (Reverse Proxy) │
                                    └────────┬────────┘
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         │                          LEVEREDGE NETWORK                            │
         │                                   │                                   │
         │  ┌─────────┐  ┌─────────┐  ┌───┴───┐  ┌─────────┐  ┌─────────┐      │
         │  │  ARIA   │  │ VARYS   │  │ ATLAS │  │ CHIRON  │  │ SCHOLAR │      │
         │  │  8111   │  │  8020   │  │ 8007  │  │  8017   │  │  8018   │      │
         │  └────┬────┘  └────┬────┘  └───┬───┘  └────┬────┘  └────┬────┘      │
         │       └────────────┴─────┬──────┴───────────┴────────────┘           │
         │                          │                                           │
         │                 ┌────────▼────────┐                                  │
         │                 │   EVENT BUS     │                                  │
         │                 │     8099        │                                  │
         │                 └────────┬────────┘                                  │
         │                          │                                           │
         │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
         │  │CHRONOS  │  │ HADES   │  │ AEGIS   │  │ HERMES  │                 │
         │  │  8010   │  │  8008   │  │  8012   │  │  8014   │                 │
         │  └─────────┘  └─────────┘  └─────────┘  └─────────┘                 │
         │       THE KEEP (Infrastructure)                                      │
         │                                                                      │
         │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐                 │
         │  │PANOPTES │  │ASCLEPIUS│  │  ARGUS  │  │  ALOY   │                 │
         │  │  8023   │  │  8024   │  │  8016   │  │  8015   │                 │
         │  └─────────┘  └─────────┘  └─────────┘  └─────────┘                 │
         │       SENTINELS (Security/Monitoring)                                │
         │                                                                      │
         │  ┌─────────┐  ┌─────────┐                                           │
         │  │  LCIS   │  │  LCIS   │                                           │
         │  │LIBRARIAN│  │ ORACLE  │                                           │
         │  │  8050   │  │  8052   │                                           │
         │  └─────────┘  └─────────┘                                           │
         │       KNOWLEDGE                                                      │
         │                          │                                           │
         │                 ┌────────▼────────┐                                  │
         │                 │    SUPABASE     │                                  │
         │                 │   (Database)    │                                  │
         │                 │   DEV + PROD    │                                  │
         │                 └─────────────────┘                                  │
         │                                                                      │
         └──────────────────────────────────────────────────────────────────────┘
```

### Domain Organization

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            LEVEREDGE AGENT FLEET                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│  🏔️ GAIA          │ ATLAS, HEPHAESTUS, ATHENA, EVENT-BUS, LCIS                 │
│  🏰 THE KEEP      │ CHRONOS, HADES, AEGIS, HERMES                              │
│  👁️ SENTINELS     │ PANOPTES, ASCLEPIUS, ARGUS, ALOY, CERBERUS                 │
│  📊 CHANCERY      │ VARYS, CHIRON, SCHOLAR, PLUTUS, SOLON                      │
│  🎭 ALCHEMY       │ MUSE, CALLIOPE, THALIA, ERATO, CLIO                        │
│  ⚔️ ARIA SANCTUM  │ ARIA, OMNISCIENCE, CONVENER                                │
│  🏋️ PERSONAL      │ GYM-COACH, ACADEMIC-GUIDE                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## System Overview

Multi-agent AI automation infrastructure with control plane / data plane separation, self-healing capabilities, and themed domain organization.

**Health Score:** 85%+
**Agents:** 40+
**Database Tables:** 53+

---

## Directory Structure

```
/opt/leveredge/                        # System root
├── gaia/                              # Tier 0 - Emergency restore
├── control-plane/                     # The brain
│   ├── n8n/                           # control.n8n.leveredgeai.com
│   ├── agents/                        # FastAPI backends
│   │   ├── atlas/                     # Orchestrator
│   │   ├── sentinel/                  # Gatekeeper
│   │   ├── panoptes/                  # Integrity guardian
│   │   ├── asclepius/                 # Healing agent
│   │   └── [other agents]/
│   ├── workflows/                     # n8n workflow exports
│   └── event-bus/                     # Agent communication (8099)
├── data-plane/
│   ├── prod/
│   │   ├── n8n/                       # n8n.leveredgeai.com
│   │   ├── supabase/                  # Production database
│   │   ├── aria-frontend/             # aria.leveredgeai.com
│   │   └── command-center/            # command.leveredgeai.com
│   └── dev/
│       ├── n8n/                       # dev.n8n.leveredgeai.com
│       ├── supabase/                  # Development database
│       ├── aria-frontend/             # dev.aria.leveredgeai.com
│       └── command-center/            # dev.command.leveredgeai.com
├── shared/
│   ├── scripts/                       # CLI tools
│   │   ├── promote-to-prod.sh
│   │   ├── add-win.sh
│   │   └── promote-aria.sh
│   ├── backups/                       # CHRONOS destination
│   ├── credentials/                   # AEGIS store (encrypted)
│   └── systemd/                       # Service files
├── config/
│   └── agent-registry.yaml            # Master agent definitions (AUTHORITATIVE)
├── specs/
│   └── gsd-*.md                       # Build specifications
├── monitoring/                        # Prometheus + Grafana
└── archive/                           # Old versions
    └── docs/                          # Superseded documentation
```

---

## Agent Registry by Domain

### GAIA (Genesis) - Tier 0
| Agent | Port | Purpose |
|-------|------|---------|
| GAIA | 8000 | Emergency bootstrap/rebuild |

### THE KEEP (Infrastructure) - Tier 1
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| AEGIS | 8012 | Running | Credential vault |
| CHRONOS | 8010 | Running | Backup manager |
| HADES | 8008 | Running | Rollback/recovery |
| HERMES | 8014 | Running | Notifications |
| ARGUS | 8016 | Running | Monitoring/costs |
| ALOY | 8015 | Running | Audit/anomaly |
| ATHENA | 8013 | Running | Documentation |

### PANTHEON (Orchestration) - Tier 1
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| ATLAS | 8007 | Running | Master orchestrator |
| SENTINEL | 8019 | Running | Gatekeeper/routing |
| HEPHAESTUS | 8011 | Running | Builder/deployer + MCP |
| EVENT-BUS | 8099 | Running | Agent communication |

### SENTINELS (Security) - Tier 1
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| PANOPTES | 8023 | Running | Integrity guardian |
| ASCLEPIUS | 8024 | Running | Auto-healing |
| CERBERUS | 8025 | Defined | Security gateway |

### ARIA SANCTUM (Personal/Project Core) - Tier 1
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| ARIA-THREADING | 8113 | Running | Context/memory management (systemd) |
| ARIA-CHAT | 8114 | Running | Chat API with V4 personality (Docker) |
| ARIA-OMNISCIENCE | 8112 | Defined | Event ingestion for awareness |
| VARYS | 8020 | Running | LeverEdge mission guardian |

**ARIA Architecture Note:**
- `aria-threading.service` (8113): Handles context retrieval, memory chunking, semantic search
- `aria-chat-dev` container (8114): Chat endpoint with full personality prompt (V4)
- Frontend at `dev.aria.leveredgeai.com` routes `/api/*` to port 8114
- Personality prompt protected: `/opt/leveredge/backups/aria-prompts/ARIA_V4_GOLDEN_MASTER.md`

### CHANCERY (Business) - Tier 2
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| SCHOLAR | 8018 | Running | Research/analysis |
| CHIRON | 8017 | Running | Business coaching |
| CONSUL | 8021 | Defined | External project management |
| PLUTUS | 8205 | Defined | Financial analysis |

### ALCHEMY (Creative) - Tier 3
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| MUSE | 8030 | Defined | Creative director |
| QUILL | 8031 | Defined | Writer |
| STAGE | 8032 | Defined | Designer |
| REEL | 8033 | Defined | Media producer |
| CRITIC | 8034 | Defined | QA reviewer |

### THE SHIRE (Personal) - Tier 4
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| ARAGORN | 8110 | Defined | Fitness coach |
| BOMBADIL | 8101 | Defined | Nutritionist |
| SAMWISE | 8102 | Defined | Meal planner |
| GANDALF | 8103 | Defined | Learning guide |
| ARWEN | 8104 | Defined | Relationship coach |

---

## Self-Healing Architecture

```
                    +------------------+
                    |    PANOPTES      |
                    |  (Scan Daily)    |
                    +--------+---------+
                             |
                             v
                    +------------------+
                    |  Issues Found?   |
                    +--------+---------+
                             |
              +--------------+--------------+
              v                              v
        +-----------+                 +-----------+
        |    No     |                 |    Yes    |
        |  (Done)   |                 |           |
        +-----------+                 +-----+-----+
                                            |
                                            v
                                   +------------------+
                                   |   ASCLEPIUS      |
                                   |  (Auto-Heal)     |
                                   +--------+---------+
                                            |
                              +-------------+-------------+
                              v                           v
                        +-----------+              +-----------+
                        | Healable  |              |  Manual   |
                        |(auto-fix) |              | Required  |
                        +-----------+              +-----+-----+
                                                         |
                                                         v
                                                  +-----------+
                                                  |  HERMES   |
                                                  | (Alert)   |
                                                  +-----------+
```

### Cron Schedule
- **6:00 AM** - PANOPTES full scan
- **6:30 AM** - ASCLEPIUS auto-heal
- **Weekly** - Backup cleanup (keep 7 days)

---

## Database Schema (53+ Tables)

### Core Agent Tables
```sql
agents                    -- Agent registry (name, port, domain, status)
agent_health              -- Health checks per agent
agent_activity            -- Action logs
agent_conversations       -- Chat sessions with agents
agent_messages            -- Individual messages
```

### Per-Agent Tables
```sql
-- AEGIS
aegis_credentials         -- API keys, tokens, passwords
aegis_audit_log           -- Access tracking
aegis_personal_vault      -- Personal passwords

-- CHRONOS
chronos_backups           -- Backup records
chronos_schedules         -- Backup schedules

-- HADES
hades_deployments         -- Deployment history
hades_rollbacks           -- Rollback events

-- PANOPTES
panoptes_scans            -- Scan results
panoptes_issues           -- Detected issues

-- ASCLEPIUS
asclepius_healing_plans   -- Healing plans
asclepius_healing_history -- Healing actions
asclepius_strategies      -- Healing strategies

-- HERMES
hermes_channels           -- Notification channels
hermes_notification_rules -- Alert rules
hermes_message_log        -- Message history

-- ARGUS
argus_metrics             -- System metrics
argus_cost_tracking       -- API costs
argus_alerts              -- Active alerts

-- ALOY
aloy_audit_events         -- Audit trail
aloy_anomalies            -- Detected anomalies
aloy_compliance_checks    -- Compliance status

-- ATLAS
atlas_chain_executions    -- Chain runs
atlas_batch_executions    -- Batch operations

-- SCHOLAR
scholar_research_projects -- Research history

-- CHIRON
chiron_commitments        -- Accountability
chiron_weekly_reviews     -- Reviews
chiron_sprint_plans       -- Sprint plans

-- VARYS
varys_mission_documents   -- Sacred documents
varys_drift_flags         -- Scope creep alerts
varys_daily_briefs        -- Daily accountability
```

### Pipeline & Council Tables (NEW)
```sql
-- Pipelines
pipeline_definitions      -- Pipeline templates
pipeline_executions       -- Pipeline runs
pipeline_stage_logs       -- Per-stage execution

-- Council
council_decisions         -- Decision records
council_decision_impacts  -- Impact tracking

-- Agent Skills (ALOY)
agent_skills              -- Skill inventory
agent_skill_gaps          -- Gap tracking
agent_audits              -- Agent audits

-- CONSUL PM
consul_pm_connections     -- External PM connections
consul_projects           -- Project tracking
consul_project_sync       -- Sync state
```

---

## Web Domains

### Production
| Domain | Service |
|--------|---------|
| command.leveredgeai.com | Master Control Center |
| aria.leveredgeai.com | ARIA Frontend |
| n8n.leveredgeai.com | Production n8n |
| studio.leveredgeai.com | Supabase Studio |
| grafana.leveredgeai.com | Grafana dashboards |
| api.leveredgeai.com | Supabase API (Kong) |

### Development
| Domain | Service |
|--------|---------|
| dev.command.leveredgeai.com | DEV Control Center |
| dev.aria.leveredgeai.com | DEV ARIA Frontend |
| dev.n8n.leveredgeai.com | DEV n8n |
| dev.studio.leveredgeai.com | DEV Supabase Studio |

### Control Plane
| Domain | Service |
|--------|---------|
| control.n8n.leveredgeai.com | Control plane n8n |

---

## Communication Patterns

### Event Bus (Port 8099)
All agents publish events to centralized bus:
```json
{
  "event": "backup.completed",
  "source": "chronos",
  "timestamp": "2026-01-18T06:00:00Z",
  "data": { "backup_id": "...", "size": "2.4GB" }
}
```

### Agent-to-Agent Direct
For low-latency operations, agents can call each other directly:
```
ATLAS -> POST http://localhost:8018/research -> SCHOLAR
```

### MCP (Model Context Protocol)
HEPHAESTUS exposes tools via MCP for Claude:
- list_directory, read_file, create_file
- run_command, git_commit
- list_workflows, call_agent
- orchestrate (chain execution)

---

## Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| Event Bus for coordination | Loose coupling, event sourcing |
| AEGIS applies credentials | Builders never see secret values |
| localhost URLs for systemd agents | Avoid Docker networking issues |
| DEV-first deployment | Never push directly to prod |
| Themed domains | Memorable, organized, expandable |
| Self-healing by default | Reduce manual intervention |
| Per-agent database tables | Separation of concerns |
| Native n8n nodes over Code | Better debugging, maintenance |
| Single source of truth docs | No dated duplicates, use git |

---

## Deployment Workflow

```
1. Build in Bolt.new
          |
          v
2. Push to GitHub
          |
          v
3. Pull to DEV server
   cd /opt/leveredge/data-plane/dev/[service]
   git pull origin main
          |
          v
4. Build
   npm install && npm run build
          |
          v
5. Test on dev.*.leveredgeai.com
          |
          v
6. Promote to PROD
   ./promote-to-prod.sh [service]
          |
          v
7. Restart Caddy
   docker compose restart caddy
```

---

## Build Phases

| Phase | Components | Status |
|-------|------------|--------|
| 0 | GAIA + Event Bus | Complete |
| 1 | Control plane n8n + ATLAS | Complete |
| 2 | HEPHAESTUS + AEGIS + SENTINEL | Complete |
| 3 | CHRONOS + HADES | Complete |
| 4 | ARGUS + ALOY + HERMES + ATHENA | Complete |
| 5 | PANOPTES + ASCLEPIUS (self-healing) | Complete |
| 6 | Database schema (42 tables) | Complete |
| 6.5 | Pipeline/ARIA tables (11 tables) | Complete |
| 7 | Agent page UIs | In Progress |
| 8 | Backend API wiring | Next |
| 9 | Business agents (SCHOLAR, CHIRON, VARYS) | Running, UIs next |
| 10 | Creative agents | Post-launch |
| 11 | Personal agents | Post-launch |

---

## Quick Commands

```bash
# Check system health
curl http://localhost:8023/status | python3 -m json.tool

# Auto-heal issues
curl -X POST http://localhost:8024/emergency/auto

# List all agents
cat /opt/leveredge/config/agent-registry.yaml | grep "name:"

# Check agent status
sudo systemctl status leveredge-{event-bus,atlas,panoptes,asclepius}

# Deploy frontend update
cd /opt/leveredge/data-plane/dev/aria-frontend
git pull && npm install && npm run build
cd /home/damon/stack && docker compose restart caddy
```

---

## Authoritative Sources

| What | Where |
|------|-------|
| Agent routing | /opt/leveredge/AGENT-ROUTING.md |
| Agent definitions | /opt/leveredge/config/agent-registry.yaml |
| Current status | /opt/leveredge/LOOSE-ENDS.md |
| Documentation rules | /opt/leveredge/DOCUMENTATION-RULES.md |
| Execution rules | /home/damon/.claude/EXECUTION_RULES.md |
