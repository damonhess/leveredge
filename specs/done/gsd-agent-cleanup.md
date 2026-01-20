# GSD: Agent Fleet Cleanup & Alias System

**Priority:** HIGH
**Estimated Time:** 2-3 hours
**Purpose:** Eliminate redundant agents, establish clean naming convention

---

## OBJECTIVE

1. Kill redundant agents
2. Establish generic names (code) → alias (display) system
3. Update all documentation and dashboards
4. Free up ports for future use

---

## PHASE 1: STOP REDUNDANT AGENTS

### Kill List

| Container | Port | Reason |
|-----------|------|--------|
| workflow-builder | 8202 | HEPHAESTUS builds everything |
| plutus | 8205 | LITTLEFINGER handles finance |
| iris | 8209 | HERMES handles communications |
| librarian | 8201 | LCIS LIBRARIAN (8050) handles knowledge |
| heracles | 8200 | Consolidate into MAGNUS/VARYS |
| themis | 8203 | Consolidate into ATHENA (compliance) |
| mentor | 8204 | Consolidate into CHIRON (guidance) |
| procurement | 8206 | Consolidate into LITTLEFINGER |

### Commands

```bash
# Stop and remove redundant containers
docker stop workflow-builder plutus iris librarian heracles themis mentor procurement 2>/dev/null
docker rm workflow-builder plutus iris librarian heracles themis mentor procurement 2>/dev/null

# Verify they're gone
docker ps --format "{{.Names}}" | grep -E "(workflow-builder|plutus|iris|librarian|heracles|themis|mentor|procurement)" && echo "FAILED: Some still running" || echo "SUCCESS: All removed"
```

---

## PHASE 2: CREATE ALIAS REGISTRY

Create `/opt/leveredge/config/agent-aliases.json`:

```json
{
  "version": "1.0.0",
  "updated": "2026-01-19",
  "description": "Generic names (code) → Aliases (display)",
  
  "agents": {
    "GAIA": {
      "orchestrator": {
        "alias": "GAIA",
        "ports": [5678, 5679, 5680],
        "domain": "GAIA",
        "function": "Workflow automation via n8n",
        "status": "active"
      },
      "builder": {
        "alias": "HEPHAESTUS",
        "ports": [8011, 8207],
        "domain": "GAIA",
        "function": "File ops, code generation, builds everything",
        "status": "active"
      },
      "pipeline_engine": {
        "alias": "ATLAS",
        "ports": [8208],
        "domain": "GAIA",
        "function": "Pipeline orchestration and execution",
        "status": "active"
      },
      "event_bus": {
        "alias": "EVENT_BUS",
        "ports": [8099],
        "domain": "GAIA",
        "function": "Inter-agent pub/sub messaging",
        "status": "active"
      },
      "knowledge_ingest": {
        "alias": "LIBRARIAN",
        "ports": [8050],
        "domain": "GAIA",
        "function": "LCIS knowledge ingestion",
        "status": "active"
      },
      "knowledge_query": {
        "alias": "ORACLE",
        "ports": [8052],
        "domain": "GAIA",
        "function": "LCIS knowledge consultation",
        "status": "active"
      }
    },
    
    "THE_KEEP": {
      "backup": {
        "alias": "CHRONOS",
        "ports": [8010],
        "domain": "THE_KEEP",
        "function": "Automated backups and scheduling",
        "status": "active"
      },
      "recovery": {
        "alias": "HADES",
        "ports": [8008],
        "domain": "THE_KEEP",
        "function": "Disaster recovery and rollback",
        "status": "active"
      },
      "credentials": {
        "alias": "AEGIS",
        "ports": [8012],
        "domain": "THE_KEEP",
        "function": "Secrets and credential management",
        "status": "active"
      },
      "notifications": {
        "alias": "HERMES",
        "ports": [8014],
        "domain": "THE_KEEP",
        "function": "Alerts, notifications, communications",
        "status": "active"
      },
      "auth_gateway": {
        "alias": "CERBERUS",
        "ports": [8022],
        "domain": "THE_KEEP",
        "function": "Authentication gateway",
        "status": "active"
      },
      "port_manager": {
        "alias": "PORT_MANAGER",
        "ports": [8021],
        "domain": "THE_KEEP",
        "function": "Port allocation tracking",
        "status": "active"
      }
    },
    
    "SENTINELS": {
      "monitoring": {
        "alias": "PANOPTES",
        "ports": [8023],
        "domain": "SENTINELS",
        "function": "Real-time system monitoring",
        "status": "active"
      },
      "diagnostics": {
        "alias": "ASCLEPIUS",
        "ports": [8024],
        "domain": "SENTINELS",
        "function": "Health diagnostics and healing",
        "status": "active"
      },
      "security": {
        "alias": "ARGUS",
        "ports": [8016],
        "domain": "SENTINELS",
        "function": "Security scanning",
        "status": "active"
      },
      "evaluation": {
        "alias": "ALOY",
        "ports": [8015],
        "domain": "SENTINELS",
        "function": "Performance evaluation",
        "status": "active"
      }
    },
    
    "CHANCERY": {
      "project_manager": {
        "alias": "MAGNUS",
        "ports": [8019],
        "domain": "CHANCERY",
        "function": "Universal project management (7 PM tools)",
        "status": "active"
      },
      "intelligence": {
        "alias": "VARYS",
        "ports": [8018],
        "domain": "CHANCERY",
        "function": "Intelligence gathering, portfolio tracking",
        "status": "active"
      },
      "finance": {
        "alias": "LITTLEFINGER",
        "ports": [8020],
        "domain": "CHANCERY",
        "function": "Invoicing, expenses, MRR tracking",
        "status": "active"
      },
      "research": {
        "alias": "SCHOLAR",
        "ports": [8030],
        "domain": "CHANCERY",
        "function": "Deep research and analysis",
        "status": "active"
      },
      "planning": {
        "alias": "CHIRON",
        "ports": [8031],
        "domain": "CHANCERY",
        "function": "Strategic planning and guidance",
        "status": "active"
      },
      "documentation": {
        "alias": "ATHENA",
        "ports": [8013],
        "domain": "CHANCERY",
        "function": "Documentation, knowledge, compliance",
        "status": "active"
      }
    },
    
    "ARIA_SANCTUM": {
      "assistant": {
        "alias": "ARIA",
        "ports": [8114, 8115],
        "domain": "ARIA_SANCTUM",
        "function": "Personal AI assistant",
        "status": "active"
      },
      "council": {
        "alias": "CONVENER",
        "ports": [8025],
        "domain": "ARIA_SANCTUM",
        "function": "Council meeting facilitation",
        "status": "active"
      }
    },
    
    "PERSONAL": {
      "nutrition": {
        "alias": "NUTRITIONIST",
        "ports": [8101],
        "domain": "PERSONAL",
        "function": "Nutrition guidance",
        "status": "active"
      },
      "meals": {
        "alias": "MEAL_PLANNER",
        "ports": [8102],
        "domain": "PERSONAL",
        "function": "Recipe and meal suggestions",
        "status": "active"
      },
      "learning": {
        "alias": "ACADEMIC_GUIDE",
        "ports": [8103],
        "domain": "PERSONAL",
        "function": "Study assistance",
        "status": "active"
      },
      "relationships": {
        "alias": "EROS",
        "ports": [8104],
        "domain": "PERSONAL",
        "function": "Relationship coaching",
        "status": "active"
      },
      "fitness": {
        "alias": "GYM_COACH",
        "ports": [8110],
        "domain": "PERSONAL",
        "function": "Fitness training",
        "status": "active"
      }
    }
  },
  
  "freed_ports": {
    "8200": "Available (was HERACLES)",
    "8201": "Available (was LIBRARIAN duplicate)",
    "8202": "Available (was WORKFLOW-BUILDER)",
    "8203": "Available (was THEMIS)",
    "8204": "Available (was MENTOR)",
    "8205": "Available (was PLUTUS)",
    "8206": "Available (was PROCUREMENT)",
    "8209": "Available (was IRIS)"
  },
  
  "port_ranges": {
    "8000-8099": "GAIA / Core Infrastructure",
    "8100-8199": "ARIA_SANCTUM / Personal",
    "8200-8299": "RESERVED (freed from OLYMPUS)",
    "5678-5680": "n8n instances"
  }
}
```

---

## PHASE 3: CREATE ALIAS HELPER

Create `/opt/leveredge/shared/agent_aliases.py`:

```python
"""
Agent Alias System
==================
Generic names in code, display aliases in UI.

Usage:
    from agent_aliases import get_alias, get_generic, list_agents
    
    get_alias("builder")  # Returns "HEPHAESTUS"
    get_generic("HEPHAESTUS")  # Returns "builder"
"""

import json
import os
from typing import Optional, Dict, List

ALIAS_FILE = "/opt/leveredge/config/agent-aliases.json"

_registry = None

def _load_registry() -> dict:
    global _registry
    if _registry is None:
        with open(ALIAS_FILE, 'r') as f:
            _registry = json.load(f)
    return _registry

def get_alias(generic_name: str) -> Optional[str]:
    """Get display alias from generic name."""
    registry = _load_registry()
    for domain, agents in registry.get("agents", {}).items():
        if generic_name in agents:
            return agents[generic_name].get("alias")
    return None

def get_generic(alias: str) -> Optional[str]:
    """Get generic name from display alias."""
    registry = _load_registry()
    alias_upper = alias.upper()
    for domain, agents in registry.get("agents", {}).items():
        for generic, info in agents.items():
            if info.get("alias", "").upper() == alias_upper:
                return generic
    return None

def get_agent_info(name: str) -> Optional[dict]:
    """Get full agent info by generic name or alias."""
    registry = _load_registry()
    name_upper = name.upper()
    
    for domain, agents in registry.get("agents", {}).items():
        # Check generic name
        if name in agents:
            return {**agents[name], "generic": name, "domain": domain}
        # Check alias
        for generic, info in agents.items():
            if info.get("alias", "").upper() == name_upper:
                return {**info, "generic": generic, "domain": domain}
    return None

def get_port(name: str) -> Optional[int]:
    """Get primary port for an agent."""
    info = get_agent_info(name)
    if info and info.get("ports"):
        return info["ports"][0]
    return None

def list_agents(domain: str = None, status: str = "active") -> List[dict]:
    """List all agents, optionally filtered by domain and status."""
    registry = _load_registry()
    agents = []
    
    for dom, dom_agents in registry.get("agents", {}).items():
        if domain and dom != domain:
            continue
        for generic, info in dom_agents.items():
            if status and info.get("status") != status:
                continue
            agents.append({
                "generic": generic,
                "alias": info.get("alias"),
                "ports": info.get("ports", []),
                "domain": dom,
                "function": info.get("function"),
                "status": info.get("status")
            })
    
    return agents

def list_domains() -> List[str]:
    """List all domains."""
    registry = _load_registry()
    return list(registry.get("agents", {}).keys())

def get_freed_ports() -> Dict[str, str]:
    """Get list of freed ports available for reuse."""
    registry = _load_registry()
    return registry.get("freed_ports", {})

# Quick lookup tables
ALIAS_TO_GENERIC = {}
GENERIC_TO_ALIAS = {}

def _build_lookup_tables():
    global ALIAS_TO_GENERIC, GENERIC_TO_ALIAS
    registry = _load_registry()
    for domain, agents in registry.get("agents", {}).items():
        for generic, info in agents.items():
            alias = info.get("alias", "")
            ALIAS_TO_GENERIC[alias.upper()] = generic
            GENERIC_TO_ALIAS[generic] = alias

_build_lookup_tables()
```

---

## PHASE 4: UPDATE FLEET DASHBOARD

Update `/opt/leveredge/control-plane/dashboards/fleet/dashboard.py`:

```python
# Replace AGENTS dict with:

import json

def load_agents_from_registry():
    """Load agents from alias registry."""
    with open("/opt/leveredge/config/agent-aliases.json", 'r') as f:
        registry = json.load(f)
    
    agents = {}
    for domain, domain_agents in registry.get("agents", {}).items():
        for generic, info in domain_agents.items():
            if info.get("status") != "active":
                continue
            
            alias = info.get("alias", generic.upper())
            primary_port = info["ports"][0] if info.get("ports") else None
            
            if primary_port:
                agents[alias] = {
                    "port": primary_port,
                    "category": domain.lower(),
                    "description": info.get("function", ""),
                    "generic": generic
                }
    
    return agents

AGENTS = load_agents_from_registry()
```

---

## PHASE 5: UPDATE AGENT REGISTRY DOC

Replace `/opt/leveredge/docs-site/docs/AGENT-REGISTRY.md` with accurate list:

```markdown
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

### THE_KEEP (6 agents)
System maintenance and protection.

### SENTINELS (4 agents)
Security and monitoring.

### CHANCERY (6 agents)
Business operations.

### ARIA_SANCTUM (2 agents)
Personal AI ecosystem.

### PERSONAL (5 agents)
Life management.

---

*"Lean fleet. Clear purpose. No redundancy."*
```

---

## PHASE 6: VERIFY & COMMIT

```bash
# Verify redundant containers are stopped
docker ps --format "{{.Names}}" | wc -l  # Should be ~77 (was 85)

# Test alias system
cd /opt/leveredge
python3 -c "from shared.agent_aliases import get_alias; print(get_alias('builder'))"
# Should print: HEPHAESTUS

# Commit
git add .
git commit -m "Agent Fleet Cleanup: Kill 8 redundant agents

KILLED:
- WORKFLOW-BUILDER (8202) → HEPHAESTUS builds
- PLUTUS (8205) → LITTLEFINGER handles finance
- IRIS (8209) → HERMES handles comms
- LIBRARIAN (8201) → LCIS LIBRARIAN (8050)
- HERACLES (8200) → MAGNUS/VARYS
- THEMIS (8203) → ATHENA
- MENTOR (8204) → CHIRON
- PROCUREMENT (8206) → LITTLEFINGER

ADDED:
- /config/agent-aliases.json - Alias registry
- /shared/agent_aliases.py - Alias helper library
- Updated Fleet Dashboard to use registry
- Updated AGENT-REGISTRY.md with truth

27 active agents. 8 ports freed. No redundancy."
```

---

## SUMMARY

**Before:** 35+ agents with overlap and confusion
**After:** 27 agents with clear responsibilities

**Naming Convention:**
- Code uses generic names: `builder`, `finance`, `notifications`
- UI displays aliases: `HEPHAESTUS`, `LITTLEFINGER`, `HERMES`
- Registry maps between them

**Freed Ports:** 8200-8206, 8209 (8 ports for future use)

---

*"Lean fleet. Clear purpose. No redundancy."*
