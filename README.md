# LEVEREDGE

*AI Automation Agency Infrastructure*
*Launch: March 1, 2026*

---

## Quick Status

| Component | Status |
|-----------|--------|
| Control Plane | ✅ 40+ agents active |
| Data Plane PROD | ✅ n8n + Supabase |
| Data Plane DEV | ✅ n8n + Supabase |
| ARIA | ✅ V3.2 Working |
| Monitoring | ✅ Prometheus + Grafana + Uptime + SSL |
| Dashboards | ✅ Fleet + Cost Tracking |
| Documentation | ✅ MkDocs Site |
| Testing | ✅ pytest Integration Suite |

---

## Documentation

| File | Purpose | Update Frequency |
|------|---------|------------------|
| **ARCHITECTURE.md** | System design, agent registry, networks | Major changes |
| **MASTER-LAUNCH-CALENDAR.md** | Timeline, milestones, weekly tasks | Weekly |
| **LOOSE-ENDS.md** | All tasks, priorities, technical debt | After each session |
| **LESSONS-LEARNED.md** | Technical knowledge base | After each session |
| **LESSONS-SCRATCH.md** | Quick debug capture | During debugging |
| **FUTURE-VISION.md** | Business roadmap, autonomy plans | Monthly |

---

## Directory Structure

```
/opt/leveredge/
├── gaia/                          # Tier 0 - Emergency restore
├── control-plane/
│   ├── n8n/                       # control.n8n.leveredgeai.com
│   ├── agents/                    # 40+ FastAPI backends
│   ├── event-bus/                 # Inter-agent communication
│   └── workflows/                 # n8n workflow exports
├── data-plane/
│   ├── prod/
│   │   ├── n8n/                   # n8n.leveredgeai.com
│   │   └── supabase/              # api.leveredgeai.com
│   └── dev/
│       ├── n8n/                   # dev.n8n.leveredgeai.com
│       └── supabase/
├── shared/
│   ├── scripts/                   # CLI tools
│   ├── backups/                   # CHRONOS destination
│   └── systemd/                   # Service templates
├── monitoring/
│   ├── prometheus/                # Metrics collection
│   ├── grafana/                   # Dashboards
│   ├── uptime/                    # Service uptime checks
│   ├── ssl/                       # Certificate monitoring
│   └── logs/                      # Log aggregation
├── integrations/
│   ├── google-calendar/           # Two-way sync
│   ├── google-tasks/              # Two-way sync
│   ├── telegram/                  # Bot integration
│   └── email/                     # SendGrid
├── maintenance/
│   ├── storage-cleanup/           # Supabase cleanup
│   └── chat-cleanup/              # n8n memory cleanup
├── billing/                       # Invoice & usage tracking
├── security/                      # Hardening configs
├── tests/                         # pytest integration suite
├── docs-site/                     # MkDocs documentation
├── demo/                          # Demo environment
├── aria-frontend-v2/              # React components
└── client-portal/                 # Next.js client portal
```

---

## Agent Fleet

### Core Infrastructure (8000-8099)
| Agent | Port | Purpose |
|-------|------|---------|
| GAIA | 8000 | Emergency bootstrap |
| ATLAS | 8007 | Orchestration engine |
| HADES | 8008 | Rollback system |
| CHRONOS | 8010 | Backup manager |
| HEPHAESTUS | 8011 | Builder (MCP) |
| AEGIS | 8012 | Credential vault |
| ATHENA | 8013 | Documentation |
| HERMES | 8014 | Notifications |
| ALOY | 8015 | Audit/anomaly |
| ARGUS | 8016 | Monitoring |
| CHIRON | 8017 | Business mentor (LLM) |
| SCHOLAR | 8018 | Market research (LLM) |
| SENTINEL | 8019 | Smart router |
| FILE-PROCESSOR | 8050 | PDF/image/audio processing |
| VOICE | 8051 | Voice interface |
| GATEWAY | 8070 | API gateway |
| MEMORY-V2 | 8066 | Unified memory |
| SHIELD-SWORD | 8067 | Manipulation detection |
| Event Bus | 8099 | Inter-agent communication |

### Security Fleet (8020-8021)
| Agent | Port | Purpose |
|-------|------|---------|
| CERBERUS | 8020 | Security gateway |
| PORT-MANAGER | 8021 | Port allocation |

### Creative Fleet (8030-8034)
| Agent | Port | Purpose |
|-------|------|---------|
| MUSE | 8030 | Creative director |
| CALLIOPE | 8031 | Writer (LLM) |
| THALIA | 8032 | Designer |
| ERATO | 8033 | Media producer |
| CLIO | 8034 | Reviewer (LLM) |

### Personal Fleet (8100-8110)
| Agent | Port | Purpose |
|-------|------|---------|
| NUTRITIONIST | 8101 | Nutrition (LLM) |
| MEAL-PLANNER | 8102 | Meals (LLM) |
| ACADEMIC-GUIDE | 8103 | Learning (LLM) |
| EROS | 8104 | Relationships (LLM) |
| GYM-COACH | 8110 | Fitness (LLM) |

### Business Fleet (8200-8209)
| Agent | Port | Purpose |
|-------|------|---------|
| HERACLES | 8200 | Project manager (LLM) |
| LIBRARIAN | 8201 | Knowledge manager (LLM) |
| DAEDALUS | 8202 | Workflow builder (LLM) |
| THEMIS | 8203 | Legal advisor (LLM) |
| MENTOR | 8204 | Business coach (LLM) |
| PLUTUS | 8205 | Financial analyst (LLM) |
| PROCUREMENT | 8206 | Procurement expert (LLM) |
| HEPHAESTUS-SERVER | 8207 | Server admin (LLM) |
| ATLAS-INFRA | 8208 | Infrastructure advisor (LLM) |
| IRIS | 8209 | World events (LLM) |

### Dashboards
| Dashboard | Port | Purpose |
|-----------|------|---------|
| Fleet Dashboard | 8060 | Agent status & health |
| Cost Dashboard | 8061 | LLM usage & costs |

---

## Key URLs

### Control Plane
- control.n8n.leveredgeai.com

### Production
- n8n.leveredgeai.com
- aria.leveredgeai.com
- api.leveredgeai.com
- studio.leveredgeai.com
- grafana.leveredgeai.com

### Development
- dev.n8n.leveredgeai.com
- dev-aria.leveredgeai.com

---

## Execution Workflow

```
1. Claude Web writes spec via HEPHAESTUS
2. CHRONOS backup
3. Dispatch to GSD: /gsd [spec path]
4. Verify via HEPHAESTUS
5. HADES rollback if needed
6. Git commit
```

---

## MCP Server Mapping

| MCP | Port | Target |
|-----|------|--------|
| n8n-control | 5679 | Control plane agents |
| n8n-troubleshooter | 5678 | PROD data plane |
| n8n-troubleshooter-dev | 5680 | DEV data plane |
