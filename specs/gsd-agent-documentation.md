# GSD: Agent Fleet Documentation

**Priority:** LOW (but important)
**Estimated Time:** 4 hours
**Output:** Complete documentation for all agents

---

## OVERVIEW

Document every agent in the LeverEdge fleet:
- Identity and purpose
- Port and domain
- API endpoints
- MCP tools
- Database tables
- Integration points

---

## DELIVERABLES

### 1. AGENT-REGISTRY.md

Master list of all agents with quick reference.

### 2. Individual Agent Docs

One markdown file per agent with full API documentation.

### 3. Architecture Diagram

Visual showing agent relationships and communication.

---

## AGENT REGISTRY TEMPLATE

Create `/opt/leveredge/docs/AGENT-REGISTRY.md`:

```markdown
# LeverEdge Agent Fleet Registry

**Last Updated:** 2026-01-19
**Total Agents:** 38+
**Status:** Production-ready

---

## Quick Reference

| Agent | Port | Domain | Status | Purpose |
|-------|------|--------|--------|---------|
| GAIA | 8000 | GAIA | ✅ | Core orchestration |
| ATLAS | n8n | GAIA | ✅ | Workflow automation |
| HEPHAESTUS | 8011 | GAIA | ✅ | MCP server, file ops |
| CHRONOS | 8010 | THE_KEEP | ✅ | Backup & scheduling |
| HADES | 8008 | THE_KEEP | ✅ | Disaster recovery |
| AEGIS | 8012 | THE_KEEP | ✅ | Credential management |
| HERMES | 8014 | THE_KEEP | ✅ | Notifications |
| DAEDALUS | 8026 | THE_KEEP | ⏳ | Infrastructure architect |
| PANOPTES | 8023 | SENTINELS | ✅ | System monitoring |
| ASCLEPIUS | 8024 | SENTINELS | ✅ | Health diagnostics |
| ARGUS | 8016 | SENTINELS | ✅ | Security scanning |
| ALOY | 8015 | SENTINELS | ✅ | Performance evaluation |
| ARIA | 8111 | ARIA_SANCTUM | ✅ | Personal AI assistant |
| CONVENER | 8025 | ARIA_SANCTUM | ✅ | Council facilitation |
| MAGNUS | 8019 | CHANCERY | ✅ | Project management |
| VARYS | 8018 | CHANCERY | ✅ | Intelligence gathering |
| LITTLEFINGER | 8020 | CHANCERY | ✅ | Finance management |
| SCHOLAR | 8030 | CHANCERY | ⏳ | Research agent |
| CHIRON | 8031 | CHANCERY | ⏳ | Planning agent |
| MUSE | 8032 | ALCHEMY | ⏳ | Creative ideation |
| QUILL | 8033 | ALCHEMY | ⏳ | Content writing |
| STAGE | 8034 | ALCHEMY | ⏳ | Visual design |
| REEL | 8035 | ALCHEMY | ⏳ | Video production |
| CRITIC | 8036 | ALCHEMY | ⏳ | Content review |
| LCIS_LIBRARIAN | 8050 | GAIA | ✅ | Knowledge ingestion |
| LCIS_ORACLE | 8052 | GAIA | ✅ | Knowledge consultation |

**Legend:**
- ✅ Deployed and operational
- ⏳ Planned or in development
- ❌ Down or disabled

---

## Domains

### 🏔️ GAIA (Foundation)
Core infrastructure and orchestration.

| Agent | Role |
|-------|------|
| GAIA | Main API gateway and orchestration |
| ATLAS | n8n workflow automation |
| HEPHAESTUS | MCP server, file and command operations |
| LCIS | Collective intelligence (LIBRARIAN + ORACLE) |

### 🏰 THE_KEEP (Infrastructure)
System maintenance and protection.

| Agent | Role |
|-------|------|
| CHRONOS | Automated backups and scheduling |
| HADES | Disaster recovery and rollback |
| AEGIS | Credential and secrets management |
| HERMES | Notifications and alerts |
| DAEDALUS | Infrastructure architecture |

### 👁️ SENTINELS (Security/Monitoring)
System observation and protection.

| Agent | Role |
|-------|------|
| PANOPTES | Real-time system monitoring |
| ASCLEPIUS | Health diagnostics and healing |
| ARGUS | Security scanning |
| ALOY | Performance evaluation |

### 🏛️ CHANCERY (Business Operations)
Business logic and decision support.

| Agent | Role |
|-------|------|
| MAGNUS | Universal project management |
| VARYS | Intelligence and portfolio tracking |
| LITTLEFINGER | Financial management |
| SCHOLAR | Deep research |
| CHIRON | Strategic planning |

### 🎭 ALCHEMY (Creative)
Content creation and transformation.

| Agent | Role |
|-------|------|
| MUSE | Creative ideation |
| QUILL | Content writing |
| STAGE | Visual design |
| REEL | Video production |
| CRITIC | Quality review |

### ⚔️ ARIA_SANCTUM (Personal AI)
Damon's personal AI ecosystem.

| Agent | Role |
|-------|------|
| ARIA | Personal AI assistant |
| CONVENER | Council meeting facilitation |

---

## Communication Patterns

### Event Bus (Port 8099)
All agents can publish/subscribe to events.

### Direct HTTP
Agents call each other via REST APIs.

### MCP Integration
HEPHAESTUS exposes agent tools via MCP.

---

## Network Configuration

All agents run on `leveredge-network` Docker network.

Internal communication uses container names:
- `http://gaia:8000`
- `http://magnus:8017`
- etc.

External access via Caddy reverse proxy:
- `https://gaia.leveredgeai.com`
- `https://magnus.leveredgeai.com`
- etc.
```

---

## INDIVIDUAL AGENT DOC TEMPLATE

Create `/opt/leveredge/docs/agents/AGENT_NAME.md`:

```markdown
# AGENT_NAME

**Port:** XXXX
**Domain:** DOMAIN_NAME
**Status:** ✅ Operational

---

## Identity

**Name:** AGENT_NAME
**Title:** Title
**Tagline:** "Tagline here"

## Purpose

Brief description of what this agent does.

---

## API Endpoints

### Health

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "AGENT_NAME",
  "port": XXXX
}
```

### [Endpoint Name]

```
POST /endpoint
```

Request:
```json
{
  "param1": "value1"
}
```

Response:
```json
{
  "result": "value"
}
```

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `agent_tool_1` | Description |
| `agent_tool_2` | Description |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `agent_table_1` | Description |
| `agent_table_2` | Description |

---

## Configuration

Environment variables:
- `DATABASE_URL` - Database connection string
- `OTHER_VAR` - Description

---

## Integration Points

### Calls To
- AGENT_X for purpose
- AGENT_Y for purpose

### Called By
- AGENT_Z for purpose

---

## Deployment

```bash
docker run -d --name agent_name \
  --network leveredge-network \
  -p XXXX:XXXX \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  agent_name:dev
```

---

## Changelog

- 2026-01-19: Initial deployment
```

---

## ARCHITECTURE DIAGRAM

Create `/opt/leveredge/docs/ARCHITECTURE.md`:

```markdown
# LeverEdge System Architecture

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
         │  │  │  8111   │  │  8019   │  │ 8000  │  │  8018   │  │  8020   │ │ │
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
         │  │  ┌─────────┐  ┌─────────┐│                                      │ │
         │  │  │  LCIS   │  │  LCIS   ││                                      │ │
         │  │  │LIBRARIAN│  │ ORACLE  ││                                      │ │
         │  │  │  8050   │  │  8052   ││                                      │ │
         │  │  └─────────┘  └─────────┘│                                      │ │
         │  │                          │                                       │ │
         │  └──────────────────────────┼───────────────────────────────────────┘ │
         │                             │                                         │
         │                    ┌────────▼────────┐                               │
         │                    │    SUPABASE     │                               │
         │                    │   (Database)    │                               │
         │                    │   DEV + PROD    │                               │
         │                    └─────────────────┘                               │
         │                                                                       │
         └───────────────────────────────────────────────────────────────────────┘
```

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
Agent A → Event Bus → Interested Agents
              ↓
         LCIS (learning)
```

## Database Architecture

### DEV Supabase
- Development and testing
- All agent tables
- Migrations applied here first

### PROD Supabase  
- Production data
- ARIA conversations
- Real client data

### Migration Pattern
```
DEV → Test → PROD
```

## Security Layers

1. **Cloudflare** - DDoS protection, WAF
2. **Caddy** - TLS termination, rate limiting
3. **AEGIS** - Credential management
4. **ARGUS** - Security scanning
5. **Container isolation** - Docker network
```

---

## DOCUMENTATION SCRIPT

Create a script to generate docs for all agents:

```python
#!/usr/bin/env python3
"""
Generate documentation for all agents
"""

import os
import httpx
import asyncio

AGENTS = [
    {"name": "GAIA", "port": 8000, "domain": "GAIA"},
    {"name": "HEPHAESTUS", "port": 8011, "domain": "GAIA"},
    {"name": "CHRONOS", "port": 8010, "domain": "THE_KEEP"},
    {"name": "HADES", "port": 8008, "domain": "THE_KEEP"},
    {"name": "AEGIS", "port": 8012, "domain": "THE_KEEP"},
    {"name": "HERMES", "port": 8014, "domain": "THE_KEEP"},
    {"name": "PANOPTES", "port": 8023, "domain": "SENTINELS"},
    {"name": "ASCLEPIUS", "port": 8024, "domain": "SENTINELS"},
    {"name": "ARGUS", "port": 8016, "domain": "SENTINELS"},
    {"name": "ALOY", "port": 8015, "domain": "SENTINELS"},
    {"name": "ARIA", "port": 8111, "domain": "ARIA_SANCTUM"},
    {"name": "CONVENER", "port": 8025, "domain": "ARIA_SANCTUM"},
    {"name": "MAGNUS", "port": 8019, "domain": "CHANCERY"},
    {"name": "VARYS", "port": 8018, "domain": "CHANCERY"},
    {"name": "LITTLEFINGER", "port": 8020, "domain": "CHANCERY"},
    {"name": "LCIS_LIBRARIAN", "port": 8050, "domain": "GAIA"},
    {"name": "LCIS_ORACLE", "port": 8052, "domain": "GAIA"},
]

TEMPLATE = '''# {name}

**Port:** {port}
**Domain:** {domain}
**Status:** {status}

---

## Identity

**Name:** {name}
**Tagline:** "{tagline}"

---

## Health Check

```
GET /health
```

Response:
```json
{health_response}
```

---

## API Endpoints

{endpoints}

---

## MCP Tools

{mcp_tools}

---

## Database Tables

{tables}

---

## Configuration

- `DATABASE_URL` - Database connection

---

## Deployment

```bash
docker run -d --name {name_lower} \\
  --network leveredge-network \\
  -p {port}:{port} \\
  -e DATABASE_URL="$DEV_DATABASE_URL" \\
  {name_lower}:dev
```
'''

async def check_agent(agent):
    """Check agent health and gather info"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://localhost:{agent['port']}/health")
            if response.status_code == 200:
                return {**agent, "status": "✅ Operational", "health": response.json()}
    except:
        pass
    return {**agent, "status": "❌ Down", "health": {}}

async def generate_docs():
    """Generate documentation for all agents"""
    os.makedirs("/opt/leveredge/docs/agents", exist_ok=True)
    
    for agent in AGENTS:
        info = await check_agent(agent)
        
        doc = TEMPLATE.format(
            name=info["name"],
            port=info["port"],
            domain=info["domain"],
            status=info["status"],
            tagline=info.get("health", {}).get("tagline", ""),
            health_response=str(info.get("health", {})),
            name_lower=info["name"].lower(),
            endpoints="*To be documented*",
            mcp_tools="*To be documented*",
            tables="*To be documented*",
        )
        
        filepath = f"/opt/leveredge/docs/agents/{info['name']}.md"
        with open(filepath, "w") as f:
            f.write(doc)
        
        print(f"Generated: {filepath}")

if __name__ == "__main__":
    asyncio.run(generate_docs())
```

---

## BUILD STEPS

```bash
# 1. Create docs directory
mkdir -p /opt/leveredge/docs/agents

# 2. Create AGENT-REGISTRY.md manually or via script

# 3. Create ARCHITECTURE.md

# 4. Run doc generator for individual agents
python3 /opt/leveredge/scripts/generate-agent-docs.py

# 5. Review and enhance each doc manually

# 6. Commit
git add docs/
git commit -m "Agent Fleet Documentation

- AGENT-REGISTRY.md: Complete agent listing
- ARCHITECTURE.md: System architecture diagrams
- Individual agent docs in docs/agents/
- Auto-generation script

Every agent documented."
```

---

## GIT COMMIT

```bash
git add .
git commit -m "Agent Fleet Documentation

- Complete registry of 38+ agents
- Architecture diagrams
- Individual agent API docs
- MCP tool documentation
- Deployment instructions

Knowledge preserved."
```

---

*"Documentation is love. Documentation is life."*
