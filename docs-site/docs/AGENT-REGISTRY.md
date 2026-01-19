# LeverEdge Agent Fleet Registry

**Last Updated:** 2026-01-19
**Total Active Agents:** 27
**Naming Convention:** Generic (code) → Alias (display)

---

## Quick Reference

| Generic Name | Alias | Port | Domain | Function |
|--------------|-------|------|--------|----------|
| orchestrator | GAIA | 5678/5679/5680 | GAIA | Workflow automation |
| builder | HEPHAESTUS | 8011/8207 | GAIA | File ops, builds |
| pipeline_engine | ATLAS | 8208 | GAIA | Pipeline orchestration |
| event_bus | EVENT_BUS | 8099 | GAIA | Inter-agent messaging |
| knowledge_ingest | LIBRARIAN | 8050 | GAIA | LCIS ingestion |
| knowledge_query | ORACLE | 8052 | GAIA | LCIS consultation |
| backup | CHRONOS | 8010 | THE_KEEP | Backups & scheduling |
| recovery | HADES | 8008 | THE_KEEP | Disaster recovery |
| credentials | AEGIS | 8012 | THE_KEEP | Secrets management |
| notifications | HERMES | 8014 | THE_KEEP | Alerts & comms |
| auth_gateway | CERBERUS | 8022 | THE_KEEP | Authentication |
| port_manager | PORT_MANAGER | 8021 | THE_KEEP | Port allocation |
| monitoring | PANOPTES | 8023 | SENTINELS | System monitoring |
| diagnostics | ASCLEPIUS | 8024 | SENTINELS | Health diagnostics |
| security | ARGUS | 8016 | SENTINELS | Security scanning |
| evaluation | ALOY | 8015 | SENTINELS | Performance eval |
| project_manager | MAGNUS | 8019 | CHANCERY | Universal PM |
| intelligence | VARYS | 8018 | CHANCERY | Intel & portfolio |
| finance | LITTLEFINGER | 8020 | CHANCERY | Invoicing, MRR |
| research | SCHOLAR | 8030 | CHANCERY | Deep research |
| planning | CHIRON | 8031 | CHANCERY | Strategic planning |
| documentation | ATHENA | 8013 | CHANCERY | Docs & compliance |
| assistant | ARIA | 8114/8115 | ARIA_SANCTUM | Personal AI |
| council | CONVENER | 8025 | ARIA_SANCTUM | Council facilitation |
| nutrition | NUTRITIONIST | 8101 | PERSONAL | Nutrition |
| meals | MEAL_PLANNER | 8102 | PERSONAL | Recipes |
| learning | ACADEMIC_GUIDE | 8103 | PERSONAL | Study help |
| relationships | EROS | 8104 | PERSONAL | Relationship coach |
| fitness | GYM_COACH | 8110 | PERSONAL | Fitness |

---

## Freed Ports (Available)

| Port | Previously |
|------|------------|
| 8200 | HERACLES (consolidated into MAGNUS) |
| 8201 | LIBRARIAN (duplicate, using LCIS 8050) |
| 8202 | WORKFLOW-BUILDER (HEPHAESTUS builds) |
| 8203 | THEMIS (consolidated into ATHENA) |
| 8204 | MENTOR (consolidated into CHIRON) |
| 8205 | PLUTUS (consolidated into LITTLEFINGER) |
| 8206 | PROCUREMENT (consolidated into LITTLEFINGER) |
| 8209 | IRIS (consolidated into HERMES) |

---

## Domains

### GAIA (6 agents)
Core infrastructure and orchestration.

| Generic | Alias | Port | Function |
|---------|-------|------|----------|
| orchestrator | GAIA | 5678/5679/5680 | Workflow automation via n8n |
| builder | HEPHAESTUS | 8011/8207 | File ops, code generation, builds everything |
| pipeline_engine | ATLAS | 8208 | Pipeline orchestration and execution |
| event_bus | EVENT_BUS | 8099 | Inter-agent pub/sub messaging |
| knowledge_ingest | LIBRARIAN | 8050 | LCIS knowledge ingestion |
| knowledge_query | ORACLE | 8052 | LCIS knowledge consultation |

### THE_KEEP (6 agents)
System maintenance and protection.

| Generic | Alias | Port | Function |
|---------|-------|------|----------|
| backup | CHRONOS | 8010 | Automated backups and scheduling |
| recovery | HADES | 8008 | Disaster recovery and rollback |
| credentials | AEGIS | 8012 | Secrets and credential management |
| notifications | HERMES | 8014 | Alerts, notifications, communications |
| auth_gateway | CERBERUS | 8022 | Authentication gateway |
| port_manager | PORT_MANAGER | 8021 | Port allocation tracking |

### SENTINELS (4 agents)
Security and monitoring.

| Generic | Alias | Port | Function |
|---------|-------|------|----------|
| monitoring | PANOPTES | 8023 | Real-time system monitoring |
| diagnostics | ASCLEPIUS | 8024 | Health diagnostics and healing |
| security | ARGUS | 8016 | Security scanning |
| evaluation | ALOY | 8015 | Performance evaluation |

### CHANCERY (6 agents)
Business operations.

| Generic | Alias | Port | Function |
|---------|-------|------|----------|
| project_manager | MAGNUS | 8019 | Universal project management (7 PM tools) |
| intelligence | VARYS | 8018 | Intelligence gathering, portfolio tracking |
| finance | LITTLEFINGER | 8020 | Invoicing, expenses, MRR tracking |
| research | SCHOLAR | 8030 | Deep research and analysis |
| planning | CHIRON | 8031 | Strategic planning and guidance |
| documentation | ATHENA | 8013 | Documentation, knowledge, compliance |

### ARIA_SANCTUM (2 agents)
Personal AI ecosystem.

| Generic | Alias | Port | Function |
|---------|-------|------|----------|
| assistant | ARIA | 8114/8115 | Personal AI assistant |
| council | CONVENER | 8025 | Council meeting facilitation |

### PERSONAL (5 agents)
Life management.

| Generic | Alias | Port | Function |
|---------|-------|------|----------|
| nutrition | NUTRITIONIST | 8101 | Nutrition guidance |
| meals | MEAL_PLANNER | 8102 | Recipe and meal suggestions |
| learning | ACADEMIC_GUIDE | 8103 | Study assistance |
| relationships | EROS | 8104 | Relationship coaching |
| fitness | GYM_COACH | 8110 | Fitness training |

---

## Alias System

Code uses generic names, UI displays aliases.

```python
from shared.agent_aliases import get_alias, get_generic, list_agents

# Get display name
get_alias("builder")  # Returns "HEPHAESTUS"

# Get code name
get_generic("HEPHAESTUS")  # Returns "builder"

# List all agents
list_agents()  # Returns all 27 agents

# List by domain
list_agents(domain="CHANCERY")  # Returns 6 CHANCERY agents
```

Registry file: `/opt/leveredge/config/agent-aliases.json`

---

## Port Ranges

| Range | Purpose |
|-------|---------|
| 5678-5680 | n8n instances (PROD, CONTROL, DEV) |
| 8000-8099 | GAIA / Core Infrastructure |
| 8100-8199 | ARIA_SANCTUM / Personal |
| 8200-8299 | RESERVED (freed from OLYMPUS cleanup) |

---

*"Lean fleet. Clear purpose. No redundancy."*
