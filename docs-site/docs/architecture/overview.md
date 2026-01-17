# Architecture Overview

LeverEdge is a multi-agent AI automation infrastructure built on a control plane / data plane separation pattern.

## System Overview

```
+------------------------------------------------------------------+
|                    LEVEREDGE INFRASTRUCTURE                       |
+------------------------------------------------------------------+
|                                                                   |
|   CONTROL PLANE (control.n8n.leveredgeai.com)                    |
|   +----------------------------------------------------------+   |
|   |                                                          |   |
|   |   ATLAS    HEPHAESTUS   AEGIS   CHRONOS   HADES   HERMES |   |
|   |   8007     8011         8012    8010      8008    8014   |   |
|   |   Router   MCP          Vault   Backup    Rollback Notify|   |
|   |                                                          |   |
|   |   ARGUS   ALOY   ATHENA   CHIRON   SCHOLAR   SENTINEL   |   |
|   |   8016    8015   8013     8017     8018      8019       |   |
|   |   Monitor Audit  Docs    Mentor   Research  Router      |   |
|   |                                                          |   |
|   |                  EVENT BUS (8099)                        |   |
|   +----------------------------------------------------------+   |
|                                                                   |
|   DATA PLANE                                                      |
|   +---------------------------+  +---------------------------+   |
|   |          PROD             |  |           DEV             |   |
|   |                           |  |                           |   |
|   |  n8n (5678)               |  |  n8n (5680)               |   |
|   |  n8n.leveredgeai.com      |  |  dev.n8n.leveredgeai.com  |   |
|   |                           |  |                           |   |
|   |  Supabase                 |  |  Supabase DEV             |   |
|   |  api.leveredgeai.com      |  |                           |   |
|   |  studio.leveredgeai.com   |  |                           |   |
|   |                           |  |                           |   |
|   |  ARIA                     |  |  ARIA DEV                 |   |
|   |  aria.leveredgeai.com     |  |  dev-aria.leveredgeai.com |   |
|   +---------------------------+  +---------------------------+   |
|                                                                   |
|   TIER 0: GENESIS                                                 |
|   +----------------------------------------------------------+   |
|   |   GAIA (8000) - Emergency bootstrap, can rebuild all     |   |
|   +----------------------------------------------------------+   |
|                                                                   |
+------------------------------------------------------------------+
```

## Design Principles

### 1. Control Plane / Data Plane Separation

- **Control Plane**: Agent management, orchestration, credentials, monitoring
- **Data Plane**: Production workflows, user-facing services, databases

This separation ensures:

- Control operations don't affect production workloads
- Security boundaries between management and data
- Independent scaling of each plane

### 2. Agent Architecture Pattern

All agents follow a consistent hybrid pattern:

```
+----------------------------------------------------------+
|                    AGENT PATTERN                          |
|                                                           |
|   n8n Workflow (Visual)          FastAPI Backend         |
|   +---------------------+       +---------------------+  |
|   |  Webhook endpoint   |------>|  /health            |  |
|   |  AI Agent routing   |       |  /action endpoints  |  |
|   |  Tool calls         |       |  Business logic     |  |
|   |  Event Bus logging  |       |  External APIs      |  |
|   +---------------------+       +---------------------+  |
|                                                           |
+----------------------------------------------------------+
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

### 3. Option A: Dumb Executors (Current)

The current architecture uses "dumb executors":

- Agents execute commands without LLM reasoning
- Claude Web/Code provides the intelligence
- Zero API cost for agent operations
- Human always in the loop

### 4. Event-Driven Communication

All agents communicate through the Event Bus:

```
Agent A                 Event Bus              Agent B
   |                        |                      |
   |-- publish(event) ----->|                      |
   |                        |-- deliver(event) --->|
   |                        |                      |
   |                        |<-- ack(event) -------|
   |                        |                      |
```

Benefits:
- Loose coupling between agents
- Complete audit trail
- Async communication
- Easy integration

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
│   │   ├── athena/
│   │   ├── chiron/
│   │   ├── scholar/
│   │   ├── sentinel/
│   │   ├── cerberus/
│   │   ├── port-manager/
│   │   ├── muse/
│   │   ├── calliope/
│   │   ├── thalia/
│   │   ├── erato/
│   │   ├── clio/
│   │   └── ... (personal & business fleets)
│   ├── workflows/                 # n8n workflow exports
│   ├── event-bus/                 # SQLite message bus
│   └── shared/                    # Shared modules (cost_tracker, etc.)
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
├── config/                        # Configuration files
│   └── agent-registry.yaml        # Single source of truth
└── monitoring/                    # Prometheus + Grafana
```

---

## Agent Tiers

### Tier 0: Genesis

| Agent | Port | Purpose |
|-------|------|---------|
| GAIA | 8000 | Emergency bootstrap/rebuild |

GAIA can rebuild the entire infrastructure from scratch. Only triggered manually.

### Tier 1: Control Plane - Infrastructure

| Agent | Port | Purpose |
|-------|------|---------|
| ATLAS | 8007 | Orchestration engine |
| SENTINEL | 8019 | Smart routing, health monitoring |
| HEPHAESTUS | 8011 | Builder/deployer, MCP server |
| AEGIS | 8012 | Credential vault |
| CHRONOS | 8010 | Backup manager |
| HADES | 8008 | Rollback/recovery |
| HERMES | 8014 | Notifications |
| ARGUS | 8016 | Monitoring |
| ALOY | 8015 | Audit/anomalies |
| ATHENA | 8013 | Documentation |
| Event Bus | 8099 | Inter-agent communication |

### Tier 1: Control Plane - Business Intelligence (LLM-Powered)

| Agent | Port | Purpose |
|-------|------|---------|
| SCHOLAR | 8018 | Market research |
| CHIRON | 8017 | Business strategy |

### Tier 2: Data Plane

| Component | Port | Purpose |
|-----------|------|---------|
| ARIA | 5678 | Personal AI assistant |
| PROD n8n | 5678 | Production workflows |
| DEV n8n | 5680 | Development/testing |
| PROD Supabase | 54322 | Production database |
| DEV Supabase | 54323 | Development database |

---

## Network Architecture

### Docker Networks

| Network | Purpose | Services |
|---------|---------|----------|
| `control-plane-net` | Control plane internal | All agents, control n8n |
| `data-plane-net` | PROD internal | prod-n8n, prod-n8n-postgres |
| `data-plane-dev-net` | DEV internal | dev-n8n, dev-n8n-postgres |
| `stack_net` | Shared services | Caddy, Supabase |

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

## Execution Flow

```
User Request
     |
     v
+-------------+
| Claude Web  |  <-- Command center via HEPHAESTUS MCP
|  (Brain)    |
+-------------+
     |
     | 1. Write spec
     | 2. CHRONOS backup
     | 3. Dispatch to GSD
     v
+-------------+
| Claude Code |  <-- Builder with fresh context
|  + GSD      |
+-------------+
     |
     | Execute spec
     v
+-------------+
| HEPHAESTUS  |  <-- File ops, commands
|   Agents    |  <-- CHRONOS, HADES, etc.
+-------------+
     |
     | Verify
     v
+-------------+
| Claude Web  |  <-- Confirm success
|  (Verify)   |
+-------------+
```

---

## Development Workflow

```
DEV -> Test -> PROD
```

| Change Type | Flow | Exception |
|-------------|------|-----------|
| Workflows | DEV n8n (5680) -> test -> PROD n8n (5678) | Never |
| Code | DEV -> test -> PROD | Never |
| Schema changes | DEV Supabase -> test -> PROD Supabase | Never |
| Real user data | PROD directly | Only with explicit approval |

### Steps

1. Build/edit in DEV n8n or DEV environment
2. Test thoroughly
3. Run `promote-to-prod.sh` to deploy workflows
4. CHRONOS creates backup before deployment
5. HADES ready for rollback if needed

---

## OLYMPUS Orchestration

The OLYMPUS orchestration system enables multi-agent chains:

```
+------------------------------------------------------------------+
|                      OLYMPUS ORCHESTRATION                        |
|                                                                   |
|   +-------------+                                                 |
|   |  HEPHAESTUS |  MCP Server - Entry point for Claude Web       |
|   |    (MCP)    |  Tools: call_agent, orchestrate, list_chains   |
|   +------+------+                                                 |
|          | orchestrate                                            |
|          v                                                        |
|   +-------------+     +-------------+                             |
|   |  SENTINEL   |---->|    ATLAS    |  Chain execution engine    |
|   |  (Router)   |     |  (Executor) |  Reads agent-registry.yaml |
|   +-------------+     +------+------+                             |
|          |                   |                                    |
|          |                   | Execute steps                      |
|          v                   v                                    |
|   +-------------------------------------------------------+       |
|   |              AGENT POOL                                |       |
|   |                                                        |       |
|   |  Business (LLM)         Infrastructure (Executors)    |       |
|   |  +---------+            +---------+  +---------+      |       |
|   |  | SCHOLAR |            | CHRONOS |  |  HADES  |      |       |
|   |  |  8018   |            |  8010   |  |  8008   |      |       |
|   |  +---------+            +---------+  +---------+      |       |
|   |  +---------+            +---------+  +---------+      |       |
|   |  | CHIRON  |            |  AEGIS  |  | HERMES  |      |       |
|   |  |  8017   |            |  8012   |  |  8014   |      |       |
|   |  +---------+            +---------+  +---------+      |       |
|   +-------------------------------------------------------+       |
|                                                                   |
+------------------------------------------------------------------+
```

---

## Configuration

All agent and chain definitions are in `/opt/leveredge/config/agent-registry.yaml`:

```yaml
version: "2.1"

config:
  default_timeout_ms: 60000
  max_chain_depth: 10
  max_parallel_calls: 5
  cost_tracking_enabled: true
  event_bus_url: http://event-bus:8099

agents:
  atlas:
    name: ATLAS
    port: 8007
    type: orchestrator
    endpoints:
      orchestrate:
        path: /orchestrate
        method: POST

chains:
  research-and-plan:
    description: "Research topic, create plan"
    steps:
      - agent: scholar
        action: deep-research
      - agent: chiron
        action: sprint-plan
```

---

## Related Documentation

- [Event Bus Architecture](event-bus.md)
- [Cost Tracking](cost-tracking.md)
- [Operations Guide](../operations/monitoring.md)
