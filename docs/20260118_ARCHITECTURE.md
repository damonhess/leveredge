# LEVEREDGE ARCHITECTURE - January 18, 2026

## System Overview

Multi-agent AI automation infrastructure with control plane / data plane separation, self-healing capabilities, and themed domain organization.

**Health Score:** 85%+
**Agents:** 35+
**Database Tables:** 42+

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
│   └── agent-registry.yaml            # Master agent definitions
├── docs/
│   ├── ARIA-AGENT-PAGES-SPEC.md       # Agent UI specifications
│   └── LOOSE-ENDS-*.md                # Status tracking
├── specs/
│   └── gsd-*.md                       # Build specifications
├── monitoring/                        # Prometheus + Grafana
└── archive/                           # Old versions
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
| AEGIS | 8012 | ✅ Running | Credential vault |
| CHRONOS | 8010 | ✅ Running | Backup manager |
| HADES | 8008 | ✅ Running | Rollback/recovery |
| HERMES | 8014 | ✅ Running | Notifications |
| ARGUS | 8016 | ✅ Running | Monitoring/costs |
| ALOY | 8015 | ✅ Running | Audit/anomaly |
| ATHENA | 8013 | ✅ Running | Documentation |

### PANTHEON (Orchestration) - Tier 1
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| ATLAS | 8007 | ✅ Running | Master orchestrator |
| SENTINEL | 8019 | ✅ Running | Gatekeeper/routing |
| HEPHAESTUS | 8011 | ✅ Running | Builder/deployer + MCP |
| EVENT-BUS | 8099 | ✅ Running | Agent communication |

### SENTINELS (Security) - Tier 1
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| PANOPTES | 8023 | ✅ Running | Integrity guardian |
| ASCLEPIUS | 8024 | ✅ Running | Auto-healing |
| CERBERUS | 8025 | 🟡 Defined | Security gateway |

### CHANCERY (Business) - Tier 2
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| SCHOLAR | 8018 | ✅ Running | Research/analysis |
| CHIRON | 8017 | ✅ Running | Business coaching |
| VARYS | 8020 | ✅ Running | Mission guardian |
| PLUTUS | 8205 | 🟡 Defined | Financial analysis |

### ALCHEMY (Creative) - Tier 3
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| MUSE | 8030 | 🟡 Defined | Creative director |
| CALLIOPE | 8031 | 🟡 Defined | Writer |
| THALIA | 8032 | 🟡 Defined | Designer |
| ERATO | 8033 | 🟡 Defined | Media producer |
| CLIO | 8034 | 🟡 Defined | QA reviewer |

### THE SHIRE (Personal) - Tier 4
| Agent | Port | Status | Purpose |
|-------|------|--------|---------|
| ARAGORN | 8110 | 🟡 Defined | Fitness coach |
| BOMBADIL | 8101 | 🟡 Defined | Nutritionist |
| SAMWISE | 8102 | 🟡 Defined | Meal planner |
| GANDALF | 8103 | 🟡 Defined | Learning guide |
| ARWEN | 8104 | 🟡 Defined | Relationship coach |

---

## Self-Healing Architecture

```
                    ┌─────────────────┐
                    │   PANOPTES      │
                    │  (Scan Daily)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Issues Found?  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
        ┌───────────┐                 ┌───────────┐
        │    No     │                 │    Yes    │
        │  (Done)   │                 │           │
        └───────────┘                 └─────┬─────┘
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │   ASCLEPIUS     │
                                   │  (Auto-Heal)    │
                                   └────────┬────────┘
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                           ▼
                        ┌───────────┐              ┌───────────┐
                        │ Healable  │              │  Manual   │
                        │(auto-fix) │              │ Required  │
                        └───────────┘              └─────┬─────┘
                                                         │
                                                         ▼
                                                  ┌───────────┐
                                                  │  HERMES   │
                                                  │ (Alert)   │
                                                  └───────────┘
```

### Cron Schedule
- **6:00 AM** - PANOPTES full scan
- **6:30 AM** - ASCLEPIUS auto-heal
- **Weekly** - Backup cleanup (keep 7 days)

---

## Database Schema (42+ Tables)

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
ATLAS → POST http://localhost:8018/research → SCHOLAR
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

---

## Deployment Workflow

```
1. Build in Bolt.new
          ↓
2. Push to GitHub
          ↓
3. Pull to DEV server
   cd /opt/leveredge/data-plane/dev/[service]
   git pull origin main
          ↓
4. Build
   npm install && npm run build
          ↓
5. Test on dev.*.leveredgeai.com
          ↓
6. Promote to PROD
   ./promote-to-prod.sh [service]
          ↓
7. Restart Caddy
   docker compose restart caddy
```

---

## Build Phases

| Phase | Components | Status |
|-------|------------|--------|
| 0 | GAIA + Event Bus | ✅ Complete |
| 1 | Control plane n8n + ATLAS | ✅ Complete |
| 2 | HEPHAESTUS + AEGIS + SENTINEL | ✅ Complete |
| 3 | CHRONOS + HADES | ✅ Complete |
| 4 | ARGUS + ALOY + HERMES + ATHENA | ✅ Complete |
| 5 | PANOPTES + ASCLEPIUS (self-healing) | ✅ Complete |
| 6 | Database schema (42 tables) | ✅ Complete |
| 7 | Agent page UIs | 🟡 In Progress |
| 8 | Backend API wiring | ⬜ Next |
| 9 | Business agents (SCHOLAR, CHIRON, VARYS) | 🟡 Running, UIs next |
| 10 | Creative agents | ⬜ Post-launch |
| 11 | Personal agents | ⬜ Post-launch |

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
