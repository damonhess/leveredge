# LEVEREDGE ARCHITECTURE

*Last Updated: January 17, 2026*

---

## System Overview

Multi-agent AI automation infrastructure with control plane / data plane separation.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LEVEREDGE INFRASTRUCTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        CONTROL PLANE                                 │   │
│  │                   control.n8n.leveredgeai.com                        │   │
│  │                                                                      │   │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │   │
│  │   │  ATLAS  │  │HEPHAEST │  │  AEGIS  │  │ CHRONOS │  │  HADES  │  │   │
│  │   │  n8n    │  │  8011   │  │  8012   │  │  8010   │  │  8008   │  │   │
│  │   │ Router  │  │   MCP   │  │  Vault  │  │ Backup  │  │Rollback │  │   │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │   │
│  │                                                                      │   │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │   │
│  │   │ HERMES  │  │  ARGUS  │  │  ALOY   │  │ ATHENA  │               │   │
│  │   │  8014   │  │  8016   │  │  8015   │  │  8013   │               │   │
│  │   │ Notify  │  │ Monitor │  │  Audit  │  │  Docs   │               │   │
│  │   └─────────┘  └─────────┘  └─────────┘  └─────────┘               │   │
│  │                                                                      │   │
│  │                     ┌─────────────────┐                             │   │
│  │                     │    EVENT BUS    │                             │   │
│  │                     │      8099       │                             │   │
│  │                     └─────────────────┘                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA PLANE                                   │   │
│  │                                                                      │   │
│  │   ┌─────────────────────────┐    ┌─────────────────────────┐       │   │
│  │   │          PROD           │    │           DEV            │       │   │
│  │   │                         │    │                          │       │   │
│  │   │  n8n (5678)             │    │  n8n (5680)              │       │   │
│  │   │  n8n.leveredgeai.com    │    │  dev.n8n.leveredgeai.com │       │   │
│  │   │                         │    │                          │       │   │
│  │   │  Supabase               │    │  Supabase DEV            │       │   │
│  │   │  api.leveredgeai.com    │    │  (shares DB container)   │       │   │
│  │   │  studio.leveredgeai.com │    │                          │       │   │
│  │   │                         │    │                          │       │   │
│  │   │  ARIA                   │    │  ARIA DEV                │       │   │
│  │   │  aria.leveredgeai.com   │    │  dev-aria.leveredgeai.com│       │   │
│  │   └─────────────────────────┘    └─────────────────────────┘       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         TIER 0: GENESIS                              │   │
│  │                                                                      │   │
│  │   ┌─────────┐                                                       │   │
│  │   │  GAIA   │  Emergency bootstrap - can rebuild everything         │   │
│  │   │  8000   │  /opt/leveredge/gaia/                                 │   │
│  │   └─────────┘                                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
/opt/leveredge/
├── gaia/                          # Tier 0 - Emergency restore
│   ├── gaia.py
│   └── restore.sh
├── control-plane/
│   ├── n8n/                       # control.n8n.leveredgeai.com (5679)
│   │   ├── docker-compose.yml
│   │   └── .env
│   ├── agents/                    # FastAPI backends
│   │   ├── atlas/
│   │   ├── hephaestus/
│   │   ├── aegis/
│   │   ├── chronos/
│   │   ├── hades/
│   │   ├── hermes/
│   │   ├── argus/
│   │   ├── aloy/
│   │   └── athena/
│   ├── workflows/                 # n8n workflow exports
│   └── event-bus/                 # SQLite message bus
├── data-plane/
│   ├── prod/
│   │   ├── n8n/                   # n8n.leveredgeai.com (5678)
│   │   └── supabase/              # api.leveredgeai.com
│   └── dev/
│       ├── n8n/                   # dev.n8n.leveredgeai.com (5680)
│       └── supabase/              # dev.supabase.leveredgeai.com
├── shared/
│   ├── scripts/                   # CLI tools (promote-to-prod.sh, etc.)
│   └── backups/                   # CHRONOS destination
└── monitoring/                    # Prometheus + Grafana
```

---

## Agent Registry

### Tier 0: Genesis
| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| GAIA | 8000 | Emergency bootstrap/rebuild | ✅ Ready |

### Tier 1: Control Plane - Core Infrastructure
| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| ATLAS | 8007 | Orchestration engine, chain execution | ✅ Active |
| HADES | 8008 | Rollback/recovery system | ✅ Active |
| CHRONOS | 8010 | Backup manager, scheduled snapshots | ✅ Active |
| HEPHAESTUS | 8011 | Builder/deployer, MCP server | ✅ Active |
| AEGIS | 8012 | Credential vault, secret management | ✅ Active |
| ATHENA | 8013 | Documentation generation | ✅ Active |
| HERMES | 8014 | Notifications (Telegram, Event Bus) | ✅ Active |
| ALOY | 8015 | Audit log analysis, anomaly detection | ✅ Active |
| ARGUS | 8016 | Monitoring, Prometheus integration | ✅ Active |
| CHIRON | 8017 | Business strategy, ADHD planning (LLM) | ✅ Active |
| SCHOLAR | 8018 | Market research, web search (LLM) | ✅ Active |
| SENTINEL | 8019 | Smart routing, health monitoring | ✅ Active |
| Event Bus | 8099 | Inter-agent communication | ✅ Active |

### Tier 1: Control Plane - New Infrastructure Agents
| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| FILE-PROCESSOR | 8050 | PDF, image, audio processing | ✅ Built |
| VOICE | 8051 | Voice interface (Whisper + TTS) | ✅ Built |
| MEMORY-V2 | 8066 | Unified cross-conversation memory | ✅ Built |
| SHIELD-SWORD | 8067 | Manipulation detection/influence | ✅ Built |
| GATEWAY | 8070 | API gateway, rate limiting | ✅ Built |

### Tier 1: Security Fleet (8020-8021)
| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| CERBERUS | 8020 | Security gateway, auth, rate limiting | ✅ Built |
| PORT-MANAGER | 8021 | Port allocation, conflict resolution | ✅ Built |

### Tier 1: Creative Fleet (8030-8034)
| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| MUSE | 8030 | Creative director, project orchestration | ✅ Built |
| CALLIOPE | 8031 | Writer - articles, scripts, copy (LLM) | ✅ Built |
| THALIA | 8032 | Designer - presentations, UI, landing pages | ✅ Built |
| ERATO | 8033 | Media producer - images, video, voiceover | ✅ Built |
| CLIO | 8034 | Reviewer - QA, fact-check, brand compliance (LLM) | ✅ Built |

### Tier 1: Personal Fleet (8100-8110)
| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| NUTRITIONIST | 8101 | Nutrition advice, diet planning (LLM) | ✅ Built |
| MEAL-PLANNER | 8102 | Recipes, grocery lists, meal prep (LLM) | ✅ Built |
| ACADEMIC-GUIDE | 8103 | Learning paths, study optimization (LLM) | ✅ Built |
| EROS | 8104 | Relationship advice, dating coaching (LLM) | ✅ Built |
| GYM-COACH | 8110 | Workout programming, fitness tracking (LLM) | ✅ Built |

### Tier 1: Business Fleet (8200-8209)
| Agent | Port | Purpose | Status |
|-------|------|---------|--------|
| HERACLES | 8200 | Project management, task breakdown (LLM) | ✅ Built |
| LIBRARIAN | 8201 | Knowledge management, document org (LLM) | ✅ Built |
| DAEDALUS | 8202 | Workflow builder, n8n automation (LLM) | ✅ Built |
| THEMIS | 8203 | Legal advisor, contracts, compliance (LLM) | ✅ Built |
| MENTOR | 8204 | Business coach, leadership dev (LLM) | ✅ Built |
| PLUTUS | 8205 | Financial analyst, budgets, ROI (LLM) | ✅ Built |
| PROCUREMENT | 8206 | Vendor evaluation, cost optimization (LLM) | ✅ Built |
| HEPHAESTUS-SERVER | 8207 | Server admin, DevOps guidance (LLM) | ✅ Built |
| ATLAS-INFRA | 8208 | Cloud architecture, scaling (LLM) | ✅ Built |
| IRIS | 8209 | World events, news, trends (LLM) | ✅ Built |

### Tier 1: Dashboards & Monitoring
| Dashboard | Port | Purpose | Status |
|-----------|------|---------|--------|
| Fleet Dashboard | 8060 | Agent status, health monitoring | ✅ Built |
| Cost Dashboard | 8061 | LLM usage tracking, cost analysis | ✅ Built |
| Log Aggregation | 8062 | Centralized logging | ✅ Built |
| Uptime Monitor | 8063 | Service availability checks | ✅ Built |
| SSL Monitor | 8064 | Certificate expiration tracking | ✅ Built |

### Tier 2: Data Plane
| Component | Port | Purpose | Status |
|-----------|------|---------|--------|
| ARIA | 5678 | Personal AI assistant | ✅ V3.2 Active |
| PROD n8n | 5678 | Production workflows | ✅ Active |
| DEV n8n | 5680 | Development/testing | ✅ Active |
| PROD Supabase | 54322 | Production database | ✅ Active |
| DEV Supabase | 54323 | Development database (isolated) | ✅ Active |

---

## Agent Architecture Pattern

All control plane agents follow the same pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT PATTERN                             │
│                                                              │
│   n8n Workflow (Visual)          FastAPI Backend            │
│   ┌─────────────────────┐       ┌─────────────────────┐    │
│   │  Webhook endpoint   │──────▶│  /health            │    │
│   │  AI Agent routing   │       │  /action endpoints  │    │
│   │  Tool calls         │       │  Business logic     │    │
│   │  Event Bus logging  │       │  External APIs      │    │
│   └─────────────────────┘       └─────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**n8n workflow handles:**
- Webhook ingestion
- AI-powered request interpretation
- Tool selection and orchestration
- Event Bus logging

**FastAPI backend handles:**
- Actual execution logic
- External API calls
- Database operations
- Health checks

---

## Network Architecture

### Docker Networks
| Network | Purpose | Services |
|---------|---------|----------|
| `control-plane-net` | Control plane internal | All agents, control n8n |
| `data-plane-net` | PROD internal | prod-n8n, prod-n8n-postgres |
| `data-plane-dev-net` | DEV internal | dev-n8n, dev-n8n-postgres |
| `stack_net` | Shared services | Caddy, Supabase, cross-plane communication |

### External Domains
| Domain | Target | Purpose |
|--------|--------|---------|
| control.n8n.leveredgeai.com | Control n8n (5679) | Agent management |
| n8n.leveredgeai.com | PROD n8n (5678) | Production workflows |
| dev.n8n.leveredgeai.com | DEV n8n (5680) | Development |
| aria.leveredgeai.com | ARIA frontend | Personal assistant |
| api.leveredgeai.com | Supabase Kong | REST API |
| studio.leveredgeai.com | Supabase Studio | Database UI |
| grafana.leveredgeai.com | Grafana | Monitoring dashboards |

---

## Key Design Decisions

### Option A: Dumb Executors (Current)
- Agents execute commands without LLM reasoning
- Claude Web/Code provides the intelligence
- Zero API cost for agent operations
- Human always in the loop

### Option B: Autonomous Agents (Future)
- Agents have LLM reasoning capability
- Can interpret vague requests
- Requires cost monitoring
- Tiered approval system via HERMES

### Communication
- All agents log to Event Bus (audit trail)
- HERMES handles human notifications
- AEGIS manages credentials (builders never see values)

### Development Workflow (MANDATORY)
```
DEV → Test → PROD
```

| Change Type | Flow | Exception |
|-------------|------|-----------|
| Workflows | DEV n8n (5680) → test → PROD n8n (5678) | Never |
| Code | DEV → test → PROD | Never |
| Schema changes | DEV Supabase → test → PROD Supabase | Never |
| Real user data | PROD directly | Only with explicit approval |

**Steps:**
1. Build/edit in DEV n8n or DEV environment
2. Test thoroughly
3. Run `promote-to-prod.sh` to deploy workflows
4. CHRONOS creates backup before deployment
5. HADES ready for rollback if needed

**Full rules:** See `/home/damon/.claude/EXECUTION_RULES.md`

---

## MCP Server Mapping

| MCP Server | Target | Port | Use For |
|------------|--------|------|---------|
| **n8n-control** | Control plane | 5679 | Agent workflows |
| n8n-troubleshooter | PROD data plane | 5678 | ARIA, client workflows |
| n8n-troubleshooter-dev | DEV data plane | 5680 | Development |

**CRITICAL:** Always specify which MCP when creating workflows.

---

## Execution Flow

```
User Request
     │
     ▼
┌─────────────┐
│ Claude Web  │  ◄── Command center via HEPHAESTUS MCP
│  (Brain)    │
└─────────────┘
     │
     │ 1. Write spec
     │ 2. CHRONOS backup
     │ 3. Dispatch to GSD
     ▼
┌─────────────┐
│ Claude Code │  ◄── Builder with fresh context
│  + GSD      │
└─────────────┘
     │
     │ Execute spec
     ▼
┌─────────────┐
│ HEPHAESTUS  │  ◄── File ops, commands
│   Agents    │  ◄── CHRONOS, HADES, etc.
└─────────────┘
     │
     │ Verify
     ▼
┌─────────────┐
│ Claude Web  │  ◄── Confirm success
│  (Verify)   │
└─────────────┘
```

---

## OLYMPUS Orchestration System

The OLYMPUS orchestration system enables multi-agent chains for complex tasks.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      OLYMPUS ORCHESTRATION                          │
│                                                                     │
│   ┌─────────────┐                                                  │
│   │  HEPHAESTUS │  MCP Server - Entry point for Claude Web         │
│   │    (MCP)    │  Tools: call_agent, orchestrate, list_chains     │
│   └──────┬──────┘                                                  │
│          │ orchestrate                                              │
│          ▼                                                          │
│   ┌─────────────┐     ┌─────────────┐                              │
│   │  SENTINEL   │────▶│    ATLAS    │  Chain execution engine      │
│   │  (Router)   │     │  (Executor) │  Reads agent-registry.yaml   │
│   └─────────────┘     └──────┬──────┘                              │
│          │                    │                                     │
│          │                    │ Execute steps                       │
│          ▼                    ▼                                     │
│   ┌─────────────────────────────────────────────────────────┐      │
│   │              AGENT POOL                                  │      │
│   │                                                          │      │
│   │  Business (LLM)         Infrastructure (Executors)      │      │
│   │  ┌─────────┐            ┌─────────┐  ┌─────────┐       │      │
│   │  │ SCHOLAR │            │ CHRONOS │  │  HADES  │       │      │
│   │  │  8018   │            │  8010   │  │  8008   │       │      │
│   │  └─────────┘            └─────────┘  └─────────┘       │      │
│   │  ┌─────────┐            ┌─────────┐  ┌─────────┐       │      │
│   │  │ CHIRON  │            │  AEGIS  │  │ HERMES  │       │      │
│   │  │  8017   │            │  8012   │  │  8014   │       │      │
│   │  └─────────┘            └─────────┘  └─────────┘       │      │
│   └─────────────────────────────────────────────────────────┘      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Available Chains

| Chain | Description | Agents |
|-------|-------------|--------|
| `research-and-plan` | Research a topic, create action plan | SCHOLAR → CHIRON |
| `validate-and-decide` | Validate assumption, decide next steps | SCHOLAR → CHIRON |
| `comprehensive-market-analysis` | Parallel research, strategic synthesis | SCHOLAR (parallel) → CHIRON |
| `niche-evaluation` | Compare niches, recommend best | SCHOLAR → CHIRON |
| `weekly-planning` | Review week, research blockers, plan sprint | CHIRON → SCHOLAR → CHIRON |
| `fear-to-action` | Analyze fear, find evidence, create plan | CHIRON → SCHOLAR → CHIRON |
| `safe-deployment` | Backup, deploy, verify, rollback if needed | CHRONOS → HERMES → ARGUS → HADES |

### SCHOLAR Actions

| Action | Endpoint | Purpose |
|--------|----------|---------|
| `deep-research` | /deep-research | Comprehensive multi-source research with web search |
| `competitors` | /competitors | Competitive analysis for a niche |
| `market-size` | /market-size | TAM/SAM/SOM market sizing |
| `pain-discovery` | /pain-discovery | Discover and quantify pain points |
| `validate-assumption` | /validate-assumption | Test business assumption with evidence |
| `niche` | /niche | Analyze niche viability |
| `compare` | /compare | Compare multiple niches |
| `lead` | /lead | Research specific company as lead |
| `icp` | /icp | Develop Ideal Customer Profile |

### CHIRON Actions

| Action | Endpoint | Purpose |
|--------|----------|---------|
| `sprint-plan` | /sprint-plan | ADHD-optimized sprint planning |
| `break-down` | /break-down | Break large task into small steps |
| `prioritize` | /prioritize | Order tasks by impact/urgency |
| `chat` | /chat | General strategic conversation |
| `decide` | /decide | Decision framework analysis |
| `fear-check` | /fear-check | Rapid fear analysis and reframe |
| `weekly-review` | /weekly-review | Structured weekly accountability |
| `pricing-help` | /pricing-help | Value-based pricing strategy |
| `hype` | /hype | Evidence-based motivation boost |

### Usage via HEPHAESTUS MCP

**Single Agent Call:**
```json
{
  "agent": "scholar",
  "action": "deep-research",
  "payload": {"question": "Water utility compliance market size"}
}
```

**Chain Execution:**
```json
{
  "chain_name": "research-and-plan",
  "input": {"topic": "Cold outreach strategy for water utilities"}
}
```

### Configuration

All agent and chain definitions are in `/opt/leveredge/config/agent-registry.yaml`.

---

## File Reference

| File | Purpose |
|------|---------|
| ARCHITECTURE.md | This file - system design |
| MASTER-LAUNCH-CALENDAR.md | Launch timeline, milestones |
| LESSONS-LEARNED.md | Technical knowledge base |
| LESSONS-SCRATCH.md | Quick debug capture |
| /opt/leveredge/config/agent-registry.yaml | Agent and chain definitions |
| /home/damon/.claude/EXECUTION_RULES.md | Claude Code rules |
