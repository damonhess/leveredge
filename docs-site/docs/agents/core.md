# Core Agents

The core agents form the foundation of LeverEdge infrastructure, providing orchestration, backup, security, and monitoring capabilities.

## Agent Overview

| Agent | Port | Purpose | Type |
|-------|------|---------|------|
| GAIA | 8000 | Emergency bootstrap/rebuild | FastAPI |
| ATLAS | 8007 | Orchestration engine | FastAPI |
| HADES | 8008 | Rollback/recovery | FastAPI |
| CHRONOS | 8010 | Backup management | FastAPI |
| HEPHAESTUS | 8011 | Builder/MCP server | FastAPI |
| AEGIS | 8012 | Credential vault | FastAPI |
| ATHENA | 8013 | Documentation | FastAPI |
| HERMES | 8014 | Notifications | FastAPI |
| ALOY | 8015 | Audit/anomalies | FastAPI |
| ARGUS | 8016 | Monitoring | FastAPI |
| CHIRON | 8017 | Business mentor (LLM) | FastAPI |
| SCHOLAR | 8018 | Market research (LLM) | FastAPI |
| SENTINEL | 8019 | Smart router | FastAPI |
| Event Bus | 8099 | Inter-agent communication | FastAPI |

---

## GAIA - Emergency Bootstrap

**Port:** 8000 | **Type:** Executor

GAIA is the Tier 0 emergency system capable of rebuilding the entire infrastructure from scratch.

!!! warning "Emergency Use Only"
    GAIA should only be triggered manually by a human operator. It is designed for disaster recovery scenarios.

### Capabilities

- Complete system rebuild
- Disaster recovery
- Bootstrap from backup
- Infrastructure provisioning

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/rebuild` | POST | Initiate full rebuild |
| `/status` | GET | Current rebuild status |

---

## ATLAS - Orchestration Engine

**Port:** 8007 | **Type:** Orchestrator

ATLAS is the central orchestration engine that executes multi-agent chains and coordinates complex workflows.

### Capabilities

- Execute predefined agent chains
- Coordinate parallel agent calls
- Handle step dependencies
- Manage execution context
- Track chain progress

### Available Chains

| Chain | Description | Agents |
|-------|-------------|--------|
| `research-and-plan` | Research a topic, create action plan | SCHOLAR -> CHIRON |
| `validate-and-decide` | Validate assumption, decide next steps | SCHOLAR -> CHIRON |
| `comprehensive-market-analysis` | Parallel research, strategic synthesis | SCHOLAR (parallel) -> CHIRON |
| `niche-evaluation` | Compare niches, recommend best | SCHOLAR -> CHIRON |
| `weekly-planning` | Review week, research blockers, plan sprint | CHIRON -> SCHOLAR -> CHIRON |
| `fear-to-action` | Analyze fear, find evidence, create plan | CHIRON -> SCHOLAR -> CHIRON |
| `safe-deployment` | Backup, deploy, verify, rollback if needed | CHRONOS -> HERMES -> ARGUS -> HADES |

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/orchestrate` | POST | Execute a chain |
| `/chains` | GET | List available chains |
| `/status/{execution_id}` | GET | Get execution status |
| `/agent/call` | POST | Call single agent |

### Example Usage

```bash
# Execute a chain
curl -X POST http://localhost:8007/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "chain_name": "research-and-plan",
    "input": {
      "topic": "Compliance automation market"
    }
  }'

# Call single agent
curl -X POST http://localhost:8007/agent/call \
  -H "Content-Type: application/json" \
  -d '{
    "agent": "scholar",
    "action": "deep-research",
    "payload": {
      "question": "What are the top compliance software companies?"
    }
  }'
```

---

## HEPHAESTUS - Builder/MCP Server

**Port:** 8011 | **Type:** Executor

HEPHAESTUS provides file operations and command execution for Claude Web and Claude Code integration.

### Capabilities

- Read/write files in `/opt/leveredge/`
- Execute whitelisted commands
- Git operations
- Docker status queries
- Directory listing

### Whitelisted Commands

- `git status`, `git log`, `git diff`, `git commit`
- `docker ps`, `docker logs`
- `ls`, `cat` (limited paths)
- System health commands

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/read` | POST | Read file |
| `/write` | POST | Write file |
| `/list` | POST | List directory |
| `/execute` | POST | Execute command |
| `/git/{operation}` | POST | Git operations |

### MCP Integration

HEPHAESTUS exposes tools for Claude MCP integration:

```json
{
  "tools": [
    "read_file",
    "write_file",
    "list_directory",
    "execute_command",
    "git_status",
    "git_commit"
  ]
}
```

---

## CHRONOS - Backup Manager

**Port:** 8010 | **Type:** Executor

CHRONOS manages backups, scheduled snapshots, and restore point creation.

!!! important "Pre-Change Backups"
    Always call CHRONOS before destructive operations like database migrations, workflow changes, or container modifications.

### Capabilities

- Pre-change backups
- Scheduled backup verification
- Backup listing and status
- Restore point creation

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/backup` | POST | Create backup |
| `/list` | GET | List backups |
| `/restore` | POST | Restore from backup |
| `/verify` | POST | Verify backup integrity |

### Example Usage

```bash
# Create pre-deployment backup
curl -X POST http://localhost:8010/backup \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pre-deploy",
    "component": "prod-n8n",
    "reason": "Before workflow update"
  }'
```

---

## HADES - Rollback/Recovery

**Port:** 8008 | **Type:** Executor

HADES handles rollback operations and recovery from CHRONOS backups.

### Capabilities

- Rolling back failed deployments
- Restoring from CHRONOS backups
- Emergency recovery
- Version rollback in n8n

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/rollback` | POST | Rollback to backup |
| `/recover` | POST | Emergency recovery |
| `/versions` | GET | List available versions |

### Example Usage

```bash
# Rollback to specific backup
curl -X POST http://localhost:8008/rollback \
  -H "Content-Type: application/json" \
  -d '{
    "backup_id": "backup_20260117_120000",
    "component": "prod-n8n"
  }'
```

---

## AEGIS - Credential Vault

**Port:** 8012 | **Type:** Executor

AEGIS manages credentials with encryption, rotation, and health monitoring.

### Capabilities

- Create/manage credentials in n8n
- Sync credential inventory
- Track expiration
- Auto-rotation (V2)
- AES-256 encryption at rest (V2)
- Health monitoring (V2)

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check with stats |
| `/credentials` | GET | List credentials |
| `/credentials/{name}` | GET | Get credential details |
| `/credentials` | POST | Create credential |
| `/sync` | POST | Sync from n8n |
| `/credentials/{name}/apply` | POST | Apply to workflow |
| `/credentials/{name}/rotate` | POST | Rotate credential |
| `/audit` | GET | Audit log |

### Security Principles

!!! danger "Never Expose Credentials"
    - Only AEGIS can decrypt credential values
    - Other agents request by name, never see values
    - All access is logged with actor identity

---

## HERMES - Notifications

**Port:** 8014 | **Type:** Executor

HERMES handles notifications across multiple channels.

### Capabilities

- Telegram notifications
- Event Bus publishing
- Alert routing
- Priority-based delivery

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/notify` | POST | Send notification |
| `/channels` | GET | List channels |

### Example Usage

```bash
# Send Telegram notification
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "message": "Deployment completed successfully",
    "priority": "normal"
  }'
```

---

## CHIRON - Business Mentor (LLM)

**Port:** 8017 | **Type:** LLM-Powered

CHIRON is an elite business mentor with ADHD-optimized planning and strategic decision frameworks.

### Capabilities

- Strategic business decisions
- ADHD-optimized sprint planning
- Pricing strategy
- Fear analysis and reframing
- Weekly accountability reviews
- Sales psychology guidance

### Embedded Frameworks

- OODA Loop, Eisenhower Matrix, 10X Thinking
- Inversion, First Principles
- ADHD Launch Framework
- Pricing psychology (anchoring, three-tier, ROI framing)
- Trust Equation, objection reframes

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health + time context |
| `/chat` | POST | General conversation |
| `/decide` | POST | Decision framework |
| `/accountability` | POST | Accountability check |
| `/challenge` | POST | Challenge assumptions |
| `/hype` | POST | Evidence-based motivation |
| `/sprint-plan` | POST | ADHD-optimized planning |
| `/pricing-help` | POST | Pricing strategy |
| `/fear-check` | POST | Fear analysis |
| `/weekly-review` | POST | Weekly accountability |
| `/framework/{type}` | GET | Get framework |

### Example Usage

```bash
# Create ADHD-optimized sprint plan
curl -X POST http://localhost:8017/sprint-plan \
  -H "Content-Type: application/json" \
  -d '{
    "goals": ["10 outreach messages", "1 demo call"],
    "time_available": "this weekend",
    "energy_level": "high"
  }'
```

---

## SCHOLAR - Market Research (LLM)

**Port:** 8018 | **Type:** LLM-Powered

SCHOLAR provides elite market research with live web search capabilities.

### Capabilities

- Deep market research with web search
- TAM/SAM/SOM market sizing
- Structured competitor profiling
- Niche analysis and evaluation
- ICP development
- Pain point discovery
- Business assumption validation

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health + time context |
| `/deep-research` | POST | Multi-source research |
| `/competitors` | POST | Competitive intelligence |
| `/market-size` | POST | TAM/SAM/SOM calculation |
| `/pain-discovery` | POST | Pain point research |
| `/validate-assumption` | POST | Test assumptions |
| `/niche` | POST | Niche analysis |
| `/compare` | POST | Compare niches |
| `/icp` | POST | Ideal Customer Profile |
| `/lead` | POST | Company research |

### Example Usage

```bash
# Deep research with web search
curl -X POST http://localhost:8018/deep-research \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the top 5 compliance automation software companies in 2026?"
  }'

# Market sizing
curl -X POST http://localhost:8018/market-size \
  -H "Content-Type: application/json" \
  -d '{
    "market": "compliance automation software",
    "geography": "United States",
    "segment": "water utilities"
  }'
```

---

## Event Bus

**Port:** 8099 | **Type:** Infrastructure

The Event Bus provides inter-agent communication via a SQLite-backed message queue.

### Capabilities

- Publish events
- Subscribe to event types
- Event history
- Agent coordination

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/publish` | POST | Publish event |
| `/subscribe` | POST | Subscribe to events |
| `/events` | GET | Get recent events |

### Example Usage

```bash
# Publish event
curl -X POST http://localhost:8099/publish \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "deployment_completed",
    "source": "HEPHAESTUS",
    "data": {
      "component": "prod-n8n",
      "version": "1.0.5"
    }
  }'
```
