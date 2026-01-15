# Leveredge Control Plane Architecture

## Overview

The Leveredge control plane is a multi-agent system built on n8n workflows with FastAPI agent backends. All agents communicate through a central Event Bus.

## Architecture Diagram

```
+-----------------------------------------------------------------------------+
|                              CONTROL PLANE                                   |
|                                                                              |
|  +---------------------------+      +----------------------------------+    |
|  |     n8n Workflows         |      |         FastAPI Agents           |    |
|  |                           |      |                                  |    |
|  |  +-----+ +-----+ +-----+ |      | +------+ +--------+ +--------+  |    |
|  |  |ATLAS| |ATHE | |HERM | |<---->| |ATLAS | |HEPHAES| | ATHENA |  |    |
|  |  +-----+ +-----+ +-----+ |      | |:8007 | | :8008  | | :8009  |  |    |
|  |  +-----+ +-----+ +-----+ |      | +------+ +--------+ +--------+  |    |
|  |  |CHRON| |HADES| |ARGUS| |      | +------+ +--------+ +--------+  |    |
|  |  +-----+ +-----+ +-----+ |      | |AEGIS | |CHRONOS | | HADES  |  |    |
|  |  +-----+ +-----+ +-----+ |      | |:8012 | | :8010  | | :8011  |  |    |
|  |  |AEGIS| |ALOY | |ARIA | |      | +------+ +--------+ +--------+  |    |
|  |  +-----+ +-----+ +-----+ |      | +------+ +--------+ +--------+  |    |
|  +---------------------------+      | |HERMES| | ARGUS  | |  ALOY  |  |    |
|                |                    | |:8013 | | :8014  | | :8015  |  |    |
|                v                    | +------+ +--------+ +--------+  |    |
|  +---------------------------+      +----------------------------------+    |
|  |        EVENT BUS          |<-----------------------------------------+   |
|  |       (Port 8099)         |                                              |
|  |                           |                                              |
|  |  Events Table             |                                              |
|  |  Agent Subscriptions      |                                              |
|  |  Human Input Requests     |                                              |
|  +---------------------------+                                              |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                              DATA PLANE                                      |
|                                                                              |
|  +----------------------------------+  +----------------------------------+ |
|  |           PRODUCTION             |  |          DEVELOPMENT             | |
|  |                                  |  |                                  | |
|  |  n8n (Port 5678)                |  |  n8n (Port 5680)                | |
|  |  Supabase                       |  |  Supabase                       | |
|  |                                  |  |                                  | |
|  +----------------------------------+  +----------------------------------+ |
+-----------------------------------------------------------------------------+
                                      |
                                      v
+-----------------------------------------------------------------------------+
|                                 GAIA                                         |
|                       (Emergency Recovery System)                            |
|                                                                              |
|  - Runs outside n8n/Docker ecosystem                                        |
|  - Can restore entire system from backups                                   |
|  - Emergency Telegram bot with 2FA                                          |
+-----------------------------------------------------------------------------+
```

## Agent Descriptions

### ATLAS (The Commander)
- **Role**: Central orchestrator and coordinator
- **Port**: 8007
- **Responsibilities**:
  - Route requests to appropriate agents
  - Coordinate multi-agent tasks
  - Provide system status

### HEPHAESTUS (The Builder)
- **Role**: Build and deployment automation
- **Port**: 8008
- **Responsibilities**:
  - Build Docker images
  - Deploy containers
  - Manage infrastructure

### ATHENA (The Scribe)
- **Role**: Documentation and knowledge management
- **Port**: 8009
- **Responsibilities**:
  - Generate documentation
  - Maintain knowledge base
  - Track changes

### AEGIS (The Guardian)
- **Role**: Security and credential management
- **Port**: 8012
- **Responsibilities**:
  - Manage API credentials
  - Monitor for security issues
  - Rotate expiring credentials

### CHRONOS (The Timekeeper)
- **Role**: Backup and scheduling
- **Port**: 8010
- **Responsibilities**:
  - Automated backups
  - Scheduled tasks
  - Backup verification

### HADES (The Rollback)
- **Role**: Rollback and recovery
- **Port**: 8011
- **Responsibilities**:
  - Rollback deployments
  - Disaster recovery
  - State restoration

### HERMES (The Messenger)
- **Role**: Notifications and communication
- **Port**: 8013
- **Responsibilities**:
  - Send notifications (Telegram, Email, Slack)
  - Alert on critical events
  - Relay human requests

### ARGUS (The Watcher)
- **Role**: Monitoring and observability
- **Port**: 8014
- **Responsibilities**:
  - Health monitoring
  - Performance metrics
  - Anomaly detection

### ALOY (The Auditor)
- **Role**: Audit and compliance
- **Port**: 8015
- **Responsibilities**:
  - Audit logging
  - Compliance checks
  - Change tracking

### ARIA (The Assistant)
- **Role**: Human interface
- **External**: Telegram bot
- **Responsibilities**:
  - Relay human requests
  - Provide status updates
  - Handle human input requests

## Event Bus

The Event Bus is the nervous system connecting all agents.

### Event Schema
```json
{
  "id": "uuid",
  "timestamp": "datetime",
  "source_agent": "AGENT_NAME",
  "action": "action_type",
  "target": "target_resource",
  "details": {},
  "requires_human": false,
  "status": "pending|acknowledged|completed|failed"
}
```

### Agent Subscriptions
Each agent subscribes to specific event patterns:

| Agent | Subscriptions |
|-------|--------------|
| AEGIS | workflow_created, workflow_modified, credential_*, config_changed |
| CHRONOS | build_started, deploy_started, upgrade_started, config_changed |
| HADES | *_failed, audit_failed, health_check_failed |
| ALOY | workflow_deployed, container_started, restore_completed |
| ATHENA | * (all events) |
| ARIA | *, human_input_required |
| HERMES | *_completed, *_failed, human_input_required, credential_expiring |
| ARGUS | health_*, *_started, *_completed |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /health | GET | Health check |
| /events | GET | List events |
| /events | POST | Publish event |
| /events/{id} | GET | Get specific event |
| /events/{id}/acknowledge | POST | Acknowledge event |
| /events/{id}/respond | POST | Respond to human request |
| /events/pending/human | GET | Get pending human requests |
| /agents/{agent}/events | GET | Get events for agent |

## Interaction Channels

### 1. Control Plane n8n (Primary)
- URL: control.n8n.leveredgeai.com
- Direct workflow editing
- Chat triggers for each agent
- Execution history

### 2. Telegram
- @LeveredgeControlBot: Routes to ATLAS
- @GaiaEmergencyBot: Emergency restores with 2FA
- ARIA: Notifications and human requests

### 3. Web Dashboards
- aegis.leveredgeai.com: Credential management
- chronos.leveredgeai.com: Backup management
- hades.leveredgeai.com: Rollback management
- aloy.leveredgeai.com: Audit history
- grafana.leveredgeai.com: System monitoring

### 4. CLI (Server-side)
```bash
gaia restore full          # Full system restore
atlas "check health"       # Talk to ATLAS
aegis list                 # List credentials
chronos list               # List backups
hades rollback dev         # Rollback environment
```

### 5. MCP (Programmatic)
- Instance-level MCP on control n8n
- MCP Trigger (Server mode)
- Claude Desktop integration

## Monitoring

All interactions are logged to the Event Bus:
- Workflow executions
- Workflow modifications
- Credential access
- Chat messages
- Webhook calls
- Login attempts
- Configuration changes

ARGUS monitors in real-time for anomalies.
HERMES sends alerts on suspicious activity.
ALOY maintains complete audit trail.
ATHENA documents all changes.
CHRONOS backs up event database.
