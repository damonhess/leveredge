# LeverEdge System Architecture

**Version:** 2.0
**Last Updated:** 2026-01-19

---

## High-Level Overview

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
                                    │   Port 80/443   │
                                    └────────┬────────┘
                                             │
         ┌───────────────────────────────────┼───────────────────────────────────┐
         │                                   │                                   │
         │                          LEVEREDGE NETWORK                            │
         │                                   │                                   │
         │  ┌────────────────────────────────┼────────────────────────────────┐ │
         │  │                                │                                │ │
         │  │  ┌─────────┐  ┌─────────┐  ┌───┴───┐  ┌─────────┐  ┌─────────┐ │ │
         │  │  │  ARIA   │  │ MAGNUS  │  │ GAIA  │  │ VARYS   │  │LITTLEFIN│ │ │
         │  │  │8114/8115│  │  8019   │  │ n8n   │  │  8018   │  │  8020   │ │ │
         │  │  └────┬────┘  └────┬────┘  └───┬───┘  └────┬────┘  └────┬────┘ │ │
         │  │       │            │            │           │            │      │ │
         │  │       └────────────┴─────┬──────┴───────────┴────────────┘      │ │
         │  │                          │                                       │ │
         │  │                 ┌────────▼────────┐                             │ │
         │  │                 │   EVENT BUS     │                             │ │
         │  │                 │     8099        │                             │ │
         │  │                 └────────┬────────┘                             │ │
         │  │                          │                                       │ │
         │  │  ┌─────────┐  ┌─────────┐│ ┌─────────┐  ┌─────────┐            │ │
         │  │  │CHRONOS  │  │ HADES   ││ │ AEGIS   │  │ HERMES  │            │ │
         │  │  │  8010   │  │  8008   ││ │  8012   │  │  8014   │            │ │
         │  │  └─────────┘  └─────────┘│ └─────────┘  └─────────┘            │ │
         │  │                          │                                       │ │
         │  │  ┌─────────┐  ┌─────────┐│ ┌─────────┐  ┌─────────┐            │ │
         │  │  │PANOPTES │  │ASCLEPIUS││ │  ARGUS  │  │  ALOY   │            │ │
         │  │  │  8023   │  │  8024   ││ │  8016   │  │  8015   │            │ │
         │  │  └─────────┘  └─────────┘│ └─────────┘  └─────────┘            │ │
         │  │                          │                                       │ │
         │  │  ┌─────────┐  ┌─────────┐│ ┌─────────┐                         │ │
         │  │  │  LCIS   │  │  LCIS   ││ │HEPHASTUS│                         │ │
         │  │  │LIBRARIAN│  │ ORACLE  ││ │  8011   │                         │ │
         │  │  │  8050   │  │  8052   ││ └─────────┘                         │ │
         │  │  └─────────┘  └─────────┘│                                      │ │
         │  │                          │                                       │ │
         │  └──────────────────────────┼───────────────────────────────────────┘ │
         │                             │                                         │
         │     ┌───────────────────────┼───────────────────────────┐            │
         │     │                       │                           │            │
         │     │  ┌────────────────────▼────────────────────┐     │            │
         │     │  │              SUPABASE                   │     │            │
         │     │  │   ┌─────────────┐  ┌─────────────┐     │     │            │
         │     │  │   │    PROD     │  │     DEV     │     │     │            │
         │     │  │   │   54322     │  │   54323     │     │     │            │
         │     │  │   └─────────────┘  └─────────────┘     │     │            │
         │     │  └────────────────────────────────────────┘     │            │
         │     │                                                   │            │
         │     └───────────────────────────────────────────────────┘            │
         │                                                                       │
         └───────────────────────────────────────────────────────────────────────┘
```

---

## Domain Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              LEVEREDGE DOMAINS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │    GAIA     │  │  THE_KEEP   │  │  SENTINELS  │  │  CHANCERY   │        │
│  │ Foundation  │  │Infrastructure│  │ Security    │  │ Business    │        │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤        │
│  │ n8n         │  │ CHRONOS     │  │ PANOPTES    │  │ MAGNUS      │        │
│  │ ATLAS       │  │ HADES       │  │ ASCLEPIUS   │  │ VARYS       │        │
│  │ HEPHAESTUS  │  │ AEGIS       │  │ ARGUS       │  │ LITTLEFINGER│        │
│  │ EVENT-BUS   │  │ HERMES      │  │ ALOY        │  │ SCHOLAR     │        │
│  │ LCIS        │  │ CERBERUS    │  │ Prometheus  │  │ CHIRON      │        │
│  │             │  │ DAEDALUS    │  │ Grafana     │  │ ATHENA      │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                         │
│  │   OLYMPUS   │  │   ALCHEMY   │  │ARIA_SANCTUM │                         │
│  │ Enterprise  │  │  Creative   │  │  Personal   │                         │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤                         │
│  │ HERACLES    │  │ MUSE        │  │ ARIA        │                         │
│  │ LIBRARIAN   │  │ QUILL       │  │ CONVENER    │                         │
│  │ WORKFLOW-   │  │ STAGE       │  │             │                         │
│  │   BUILDER   │  │ REEL        │  │             │                         │
│  │ THEMIS      │  │ CRITIC      │  │             │                         │
│  │ MENTOR      │  │             │  │             │                         │
│  │ PLUTUS      │  │             │  │             │                         │
│  │ PROCUREMENT │  │             │  │             │                         │
│  │ IRIS        │  │             │  │             │                         │
│  └─────────────┘  └─────────────┘  └─────────────┘                         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Request Flow
```
User → Cloudflare → Caddy → Agent → Database
                         ↓
                   Event Bus (optional)
                         ↓
                   Other Agents
```

### Event Flow
```
Agent A → Event Bus → Subscribed Agents
              ↓
         LCIS (learning)
              ↓
         ARIA (awareness)
```

### Pipeline Flow (ATLAS)
```
Trigger → ATLAS → Stage 1 → Agent A
                      ↓
                  Stage 2 → Agent B
                      ↓
                  Stage 3 → Agent C
                      ↓
                  Complete
```

---

## Database Architecture

### DEV Supabase (Port 54323)
- Development and testing
- All agent tables
- Migrations applied here first
- Studio: `http://localhost:3100`

### PROD Supabase (Port 54322)
- Production data
- ARIA conversations
- Real client data
- Protected by environment lock

### n8n Databases
```
┌─────────────────────────────────────────────────┐
│                 n8n INSTANCES                    │
├─────────────┬─────────────┬─────────────────────┤
│    PROD     │     DEV     │      CONTROL        │
│  Port 5678  │  Port 5680  │     Port 5679       │
├─────────────┼─────────────┼─────────────────────┤
│ Client      │ Testing     │ Agent workflows     │
│ workflows   │ & dev       │ ARIA, GAIA, etc.    │
│             │             │                     │
│ prod-n8n-   │ dev-n8n-    │ control-n8n-        │
│ postgres    │ postgres    │ postgres            │
└─────────────┴─────────────┴─────────────────────┘
```

### Migration Pattern
```
DEV Supabase → Test → PROD Supabase
DEV n8n → Test → PROD n8n
```

---

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: CLOUDFLARE                                        │
│  ├── DDoS protection                                        │
│  ├── WAF rules                                              │
│  └── SSL termination                                        │
│                                                              │
│  Layer 2: CADDY                                             │
│  ├── TLS termination                                        │
│  ├── Rate limiting                                          │
│  └── Reverse proxy                                          │
│                                                              │
│  Layer 3: AEGIS                                             │
│  ├── Credential management                                  │
│  ├── Secret rotation                                        │
│  └── Access audit                                           │
│                                                              │
│  Layer 4: ARGUS                                             │
│  ├── Security scanning                                      │
│  ├── Vulnerability detection                                │
│  └── Compliance checks                                      │
│                                                              │
│  Layer 5: CONTAINER ISOLATION                               │
│  ├── Docker network isolation                               │
│  ├── Resource limits                                        │
│  └── Non-root users                                         │
│                                                              │
│  Layer 6: ENVIRONMENT LOCK                                  │
│  ├── PROD protection                                        │
│  ├── DEV-first enforcement                                  │
│  └── Explicit unlock required                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP Integration

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐                                           │
│  │ Claude Code  │                                           │
│  └──────┬───────┘                                           │
│         │                                                    │
│         ▼                                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              MCP SERVERS                              │   │
│  ├──────────────┬──────────────┬──────────────────────┬─┤   │
│  │ HEPHAESTUS   │ n8n-control  │ n8n-troubleshooter   │ │   │
│  │   :8011      │   (control)  │   :8001 / :8002      │ │   │
│  ├──────────────┼──────────────┼──────────────────────┤ │   │
│  │ File ops     │ Control      │ Workflow             │ │   │
│  │ Commands     │ plane        │ troubleshooting      │ │   │
│  │ Pipelines    │ workflows    │ PROD/DEV             │ │   │
│  └──────────────┴──────────────┴──────────────────────┴─┘   │
│                                                              │
│  ┌──────────────┬──────────────┬──────────────────────┐     │
│  │ mcp-leantime │mcp-openproj  │ playwright-mcp       │     │
│  │   PM tools   │   PM tools   │  Browser automation  │     │
│  └──────────────┴──────────────┴──────────────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## LCIS (Collective Intelligence)

```
┌─────────────────────────────────────────────────────────────┐
│          LEVEREDGE COLLECTIVE INTELLIGENCE SYSTEM           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│                    ┌───────────────┐                        │
│                    │   LIBRARIAN   │                        │
│                    │    :8050      │                        │
│                    │   (Ingest)    │                        │
│                    └───────┬───────┘                        │
│                            │                                 │
│   Agent Failures ──────────┼──────────── Agent Successes    │
│   Lessons Learned ─────────┼──────────── Best Practices     │
│   Anti-Patterns ───────────┼──────────── Insights           │
│                            │                                 │
│                            ▼                                 │
│                    ┌───────────────┐                        │
│                    │   Knowledge   │                        │
│                    │     Base      │                        │
│                    │  (Supabase)   │                        │
│                    └───────┬───────┘                        │
│                            │                                 │
│                            ▼                                 │
│                    ┌───────────────┐                        │
│                    │    ORACLE     │                        │
│                    │    :8052      │                        │
│                    │   (Consult)   │                        │
│                    └───────┬───────┘                        │
│                            │                                 │
│                            ▼                                 │
│   "Should I do X?" ────── Rules & Warnings ────── "Do Y"   │
│   "Is this safe?" ─────── Block/Allow ──────── Alternatives │
│                                                              │
└─────────────────────────────────────────────────────────────┘

Mantra: "Fail once, learn forever."
```

---

## MAGNUS PM Integration

```
┌─────────────────────────────────────────────────────────────┐
│                MAGNUS - Universal PM Master                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                    MAGNUS :8019                       │   │
│  │              Universal PM Interface                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                            │                                 │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│         ▼                  ▼                  ▼             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │  Leantime   │   │ OpenProject │   │   Asana     │       │
│  │  Adapter    │   │   Adapter   │   │  Adapter    │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
│         │                  │                  │             │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │    Jira     │   │  Monday.com │   │   Notion    │       │
│  │  Adapter    │   │   Adapter   │   │  Adapter    │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
│         │                                                    │
│  ┌─────────────┐                                            │
│  │   Linear    │   "MAGNUS speaks 7 PM languages"           │
│  │  Adapter    │                                            │
│  └─────────────┘                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Monitoring Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    MONITORING STACK                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ Prometheus  │──▶│  Grafana    │   │  PANOPTES   │       │
│  │   :9090     │   │   :3000     │   │   :8023     │       │
│  └──────┬──────┘   └─────────────┘   └─────────────┘       │
│         │                                                    │
│         │ scrapes                                            │
│         │                                                    │
│  ┌──────▼──────┐   ┌─────────────┐   ┌─────────────┐       │
│  │ Node        │   │  cAdvisor   │   │  ASCLEPIUS  │       │
│  │ Exporter    │   │   :8080     │   │   :8024     │       │
│  │   :9100     │   │             │   │   (Health)  │       │
│  └─────────────┘   └─────────────┘   └─────────────┘       │
│                                                              │
│  Metrics collected:                                          │
│  - Host CPU, Memory, Disk                                   │
│  - Container resource usage                                 │
│  - Agent health endpoints                                   │
│  - n8n workflow executions                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Deployment Pattern

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT FLOW                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Code Change                                              │
│     └── /opt/leveredge/control-plane/agents/{agent}/        │
│                                                              │
│  2. Build Image                                              │
│     └── docker build -t {agent}:dev .                       │
│                                                              │
│  3. Test in DEV                                              │
│     └── docker-compose -f docker-compose.dev.yml up         │
│                                                              │
│  4. Verify                                                   │
│     └── curl http://localhost:{port}/health                 │
│                                                              │
│  5. Promote to PROD                                          │
│     └── /opt/leveredge/shared/scripts/promote-to-prod.sh    │
│                                                              │
│  6. Monitor                                                  │
│     └── PANOPTES / Grafana / Logs                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File System Layout

```
/opt/leveredge/
├── control-plane/
│   └── agents/
│       ├── aria-chat/
│       ├── magnus/
│       ├── varys/
│       ├── littlefinger/
│       ├── chronos/
│       ├── hades/
│       ├── hephaestus/
│       └── ... (50+ agents)
├── data-plane/
│   ├── prod/
│   │   └── n8n/
│   └── dev/
│       └── n8n/
├── shared/
│   ├── scripts/
│   ├── backups/
│   └── config/
├── migrations/
├── specs/
├── docs-site/
│   └── docs/
│       ├── AGENT-REGISTRY.md
│       ├── ARCHITECTURE.md
│       └── agents/
└── config/
    └── agent-registry.yaml
```

---

*"Architecture is destiny."*
