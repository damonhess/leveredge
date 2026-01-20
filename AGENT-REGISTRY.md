# LeverEdge Agent Fleet Registry

**Last Updated:** 2026-01-20
**Total Agents:** 59 directories, 30 deployed
**Status:** Production-ready

---

## Quick Reference (Deployed Agents)

| Agent | Port | Category | Status | Purpose |
|-------|------|----------|--------|---------|
| EVENT-BUS | 8099 | Core | ✅ | Central event pub/sub system |
| ATLAS | 8007 | Core | ✅ | Orchestration engine for chains and batch execution |
| HEPHAESTUS | 8011 | Core | ✅ | MCP server - file ops, commands, deployment |
| CHRONOS | 8010 | Infrastructure | ✅ | Backup and snapshot management |
| HADES | 8008 | Infrastructure | ✅ | Rollback and disaster recovery |
| AEGIS | 8012 | Infrastructure | ✅ | Credential vault and secret management |
| HERMES | 8014 | Infrastructure | ✅ | Multi-channel notifications |
| ATHENA | 8013 | Infrastructure | ✅ | Automated documentation |
| ARGUS | 8016 | Security | ✅ | System monitoring and metrics |
| ALOY | 8015 | Security | ✅ | Audit logging and anomaly detection |
| CERBERUS | 8025 | Security | ✅ | Security gateway and auth |
| PANOPTES | 8023 | Security | ✅ | System integrity verification |
| ASCLEPIUS | 8024 | Security | ✅ | Automated healing and remediation |
| VARYS | 8020 | Intelligence | ✅ | Mission Guardian - accountability, drift detection |
| LCIS-LIBRARIAN | 8050 | Knowledge | ✅ | Knowledge ingestion |
| LCIS-ORACLE | 8052 | Knowledge | ✅ | Knowledge consultation |
| SCHOLAR | 8018 | Business | ✅ | Market research with web search |
| CHIRON | 8017 | Business | ✅ | Business advisor with ADHD optimization |
| PLUTUS | 8205 | Business | ✅ | Financial analysis |
| SOLON | 8203 | Business | ✅ | Legal advisor |
| STEWARD | 8204 | Business | ✅ | Business coach and mentorship |
| CONVENER | 8025 | ARIA | ✅ | Council meeting facilitation |
| ARIA-OMNISCIENCE | 8112 | ARIA | ✅ | Real-time awareness aggregation |
| MUSE | 8030 | Creative | ✅ | Creative Director |
| CALLIOPE | 8031 | Creative | ✅ | Elite Writer |
| THALIA | 8032 | Creative | ✅ | Designer |
| ERATO | 8033 | Creative | ✅ | Media Producer |
| CLIO | 8034 | Creative | ✅ | Reviewer and QA |
| SCRIBE | - | Creative | ✅ | Documentation scribe |
| GYM-COACH | 8100 | Personal | ✅ | Fitness coaching |
| ACADEMIC-GUIDE | 8103 | Personal | ✅ | Education coaching |

**Legend:**
- ✅ Deployed in docker-compose.fleet.yml
- ⏳ Directory exists, not yet deployed
- ❌ Removed or deprecated

---

## Domains

### 🏔️ GAIA (Foundation)

Core infrastructure and orchestration.

| Agent | Port | Purpose |
|-------|------|---------|
| ATLAS | 8007 | Orchestration engine |
| HEPHAESTUS | 8011 | MCP server, file/command ops |
| ATHENA | 8013 | Documentation generation |
| EVENT-BUS | 8099 | Central pub/sub |
| LCIS-LIBRARIAN | 8050 | Knowledge ingestion |
| LCIS-ORACLE | 8052 | Knowledge consultation |

### 🏰 THE_KEEP (Infrastructure)

System maintenance and protection.

| Agent | Port | Purpose |
|-------|------|---------|
| CHRONOS | 8010 | Backup scheduling |
| HADES | 8008 | Disaster recovery |
| AEGIS | 8012 | Credential management |
| HERMES | 8014 | Notifications |

### 👁️ SENTINELS (Security/Monitoring)

System observation and protection.

| Agent | Port | Purpose |
|-------|------|---------|
| PANOPTES | 8023 | Integrity verification |
| ASCLEPIUS | 8024 | Automated healing |
| ARGUS | 8016 | Monitoring and metrics |
| ALOY | 8015 | Audit and anomaly detection |
| CERBERUS | 8025 | Security gateway |

### 📊 CHANCERY (Business Operations)

Business logic and decision support.

| Agent | Port | Purpose |
|-------|------|---------|
| VARYS | 8020 | Intelligence and drift detection |
| CHIRON | 8017 | Business planning |
| SCHOLAR | 8018 | Market research |
| PLUTUS | 8205 | Financial analysis |
| SOLON | 8203 | Legal advisor |
| STEWARD | 8204 | Business coaching |

### 🎭 ALCHEMY (Creative)

Content creation and transformation.

| Agent | Port | Purpose |
|-------|------|---------|
| MUSE | 8030 | Creative Director |
| CALLIOPE | 8031 | Elite Writer |
| THALIA | 8032 | Designer |
| ERATO | 8033 | Media Producer |
| CLIO | 8034 | Reviewer/QA |
| SCRIBE | - | Documentation |

### ⚔️ ARIA_SANCTUM (Personal AI)

Damon's personal AI ecosystem.

| Agent | Port | Purpose |
|-------|------|---------|
| ARIA | 8111 | Personal AI assistant |
| ARIA-OMNISCIENCE | 8112 | Real-time awareness |
| CONVENER | 8025 | Council facilitation |

### 🏋️ PERSONAL (Coaching)

Personal development and lifestyle.

| Agent | Port | Purpose |
|-------|------|---------|
| GYM-COACH | 8100 | Fitness planning |
| ACADEMIC-GUIDE | 8103 | Education coaching |

---

## Agent Directories (All 59)

```
/opt/leveredge/control-plane/agents/
├── academic-guide/    ✅ Deployed
├── aegis/             ✅ Deployed
├── aloy/              ✅ Deployed
├── argus/             ✅ Deployed
├── aria-chat/         (Separate deployment)
├── aria-omniscience/  ✅ Deployed
├── arwen/             ⏳ Not deployed
├── asclepius/         ✅ Deployed
├── athena/            ✅ Deployed
├── atlas-infra/       ⏳ Not deployed
├── atlas-orchestrator/ ⏳ Not deployed
├── bombadil/          ⏳ Not deployed
├── bronn/             ⏳ Not deployed
├── calliope/          ✅ Deployed
├── cerberus/          ✅ Deployed
├── chiron/            ✅ Deployed
├── chronos/           ✅ Deployed
├── clio/              ✅ Deployed
├── coach-channel/     ⏳ Not deployed
├── convener/          ✅ Deployed
├── creative-fleet/    ⏳ Not deployed
├── daedalus/          ⏳ Not deployed
├── davos/             ⏳ Not deployed
├── erato/             ✅ Deployed
├── file-processor/    ⏳ Not deployed
├── gateway/           ⏳ Not deployed
├── griffin/           ⏳ Not deployed
├── gym-coach/         ✅ Deployed
├── hades/             ✅ Deployed
├── hephaestus/        ✅ Deployed (as hephaestus-mcp)
├── hephaestus-server/ ✅ Deployed
├── hermes/            ✅ Deployed
├── lcis-librarian/    ✅ Deployed
├── lcis-oracle/       ✅ Deployed
├── littlefinger/      ⏳ (Alias: PLUTUS deployed)
├── magnus/            ⏳ Not deployed
├── memory-v2/         ⏳ Not deployed
├── midas/             ⏳ Not deployed
├── muse/              ✅ Deployed
├── panoptes/          ⏳ Not deployed
├── plutus/            ✅ Deployed
├── quaestor/          ⏳ Not deployed
├── raven/             ⏳ Not deployed
├── reminders-v2/      ⏳ Not deployed
├── samwell-tarly/     ⏳ Not deployed
├── samwise/           ⏳ Not deployed
├── satoshi/           ⏳ Not deployed
├── scholar/           ✅ Deployed
├── scribe/            ✅ Deployed
├── shield-sword/      ⏳ Not deployed
├── solon/             ✅ Deployed
├── sphinx/            ⏳ Not deployed
├── stannis/           ⏳ Not deployed
├── steward/           ✅ Deployed
├── thalia/            ✅ Deployed
├── tyrion/            ⏳ Not deployed
├── varys/             ✅ Deployed
├── voice/             ⏳ Not deployed
```

---

## Communication Patterns

### Event Bus (Port 8099)

All agents can publish/subscribe to events.

```bash
# Publish event
curl -X POST http://localhost:8099/publish \
  -H "Content-Type: application/json" \
  -d '{"event": "type", "agent": "name", "data": {...}}'

# Subscribe (in agent code)
await event_bus.subscribe("event.type", callback)
```

### Direct HTTP

Agents call each other via REST APIs.

```bash
curl http://localhost:PORT/endpoint
```

### MCP Integration

HEPHAESTUS (8011) exposes agent tools via MCP protocol.

---

## Network Configuration

All agents run on Docker networks:
- `leveredge-fleet-net` - Fleet internal network
- `control-plane-net` - Control plane network
- `stack_net` - Data plane network

Internal communication uses container names:
- `http://event-bus:8099`
- `http://chronos:8010`
- `http://aegis:8012`

External access via Caddy reverse proxy:
- `https://aria.leveredgeai.com`
- `https://api.leveredgeai.com`

---

## Starting the Fleet

```bash
# Start with env file
docker compose -f docker-compose.fleet.yml --env-file .env.fleet up -d

# Start specific profile
docker compose -f docker-compose.fleet.yml --env-file .env.fleet --profile core up -d
docker compose -f docker-compose.fleet.yml --env-file .env.fleet --profile creative up -d

# Start everything
docker compose -f docker-compose.fleet.yml --env-file .env.fleet --profile all up -d

# Check status
docker compose -f docker-compose.fleet.yml ps
```

---

## Configuration Files

| File | Purpose |
|------|---------|
| `/opt/leveredge/config/agent-registry.yaml` | Full agent definitions |
| `/opt/leveredge/.env.fleet` | Environment variables |
| `/opt/leveredge/docker-compose.fleet.yml` | Fleet orchestration |

---

*Last updated: 2026-01-20*
