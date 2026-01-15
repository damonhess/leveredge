# PHASE 1: Control Plane n8n + ATLAS

*Created: January 15, 2026*
*Prerequisite: Phase 0 complete (Event Bus running on 8099)*
*Estimated Time: 2-3 hours*

---

## Objective

Deploy a dedicated n8n instance for agent workflows at `control.n8n.leveredgeai.com`.

This is NOT the production n8n (data plane). This is the control plane - where agents live and operate.

---

## Architecture Context

```
EXISTING (don't touch):
├── /home/damon/stack/           # Main infrastructure
│   ├── docker-compose.yml       # Supabase, prod n8n, Caddy
│   └── Caddyfile                # Reverse proxy (ADD route here)

NEW (Phase 1):
├── /opt/leveredge/
│   ├── control-plane/
│   │   ├── n8n/                 # ← NEW: Control plane n8n
│   │   │   ├── docker-compose.yml
│   │   │   ├── .env
│   │   │   └── data/
│   │   └── event-bus/           # ← EXISTS from Phase 0
```

---

## Components

| Component | Purpose | Port |
|-----------|---------|------|
| control-n8n | Agent workflow engine | 5679 (internal) |
| control-n8n-postgres | n8n database | 5433 (internal) |
| Event Bus | Agent communication | 8099 (exists) |
| ATLAS workflow | Master orchestrator | via n8n |

---

## Build Specification

### Step 1: Create Control Plane n8n Directory

```bash
mkdir -p /opt/leveredge/control-plane/n8n/data
```

### Step 2: Create Environment File

Create `/opt/leveredge/control-plane/n8n/.env`:

```env
# Control Plane n8n Configuration
POSTGRES_USER=n8n_control
POSTGRES_PASSWORD=GENERATE_SECURE_PASSWORD_HERE
POSTGRES_DB=n8n_control

N8N_HOST=control.n8n.leveredgeai.com
N8N_PROTOCOL=https
N8N_PORT=5678
WEBHOOK_URL=https://control.n8n.leveredgeai.com/

# Encryption key (generate with: openssl rand -hex 32)
N8N_ENCRYPTION_KEY=GENERATE_WITH_OPENSSL_RAND_HEX_32

# Basic auth for n8n UI (temporary until Cloudflare Access)
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=GENERATE_SECURE_PASSWORD_HERE

# Execution settings
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168

# Timezone
GENERIC_TIMEZONE=America/Los_Angeles

# Event Bus connection
EVENT_BUS_URL=http://host.docker.internal:8099
```

**IMPORTANT:** Generate actual passwords before deployment:
```bash
# PostgreSQL password
openssl rand -base64 24

# N8N encryption key
openssl rand -hex 32

# Basic auth password
openssl rand -base64 16
```

### Step 3: Create Docker Compose

Create `/opt/leveredge/control-plane/n8n/docker-compose.yml`:

```yaml
version: '3.8'

services:
  control-n8n-postgres:
    image: postgres:15-alpine
    container_name: control-n8n-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - control-plane-net

  control-n8n:
    image: n8nio/n8n:latest
    container_name: control-n8n
    restart: unless-stopped
    depends_on:
      control-n8n-postgres:
        condition: service_healthy
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=control-n8n-postgres
      - DB_POSTGRESDB_PORT=5432
      - DB_POSTGRESDB_DATABASE=${POSTGRES_DB}
      - DB_POSTGRESDB_USER=${POSTGRES_USER}
      - DB_POSTGRESDB_PASSWORD=${POSTGRES_PASSWORD}
      - N8N_HOST=${N8N_HOST}
      - N8N_PROTOCOL=${N8N_PROTOCOL}
      - N8N_PORT=${N8N_PORT}
      - WEBHOOK_URL=${WEBHOOK_URL}
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_BASIC_AUTH_ACTIVE=${N8N_BASIC_AUTH_ACTIVE}
      - N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}
      - N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}
      - EXECUTIONS_DATA_PRUNE=${EXECUTIONS_DATA_PRUNE}
      - EXECUTIONS_DATA_MAX_AGE=${EXECUTIONS_DATA_MAX_AGE}
      - GENERIC_TIMEZONE=${GENERIC_TIMEZONE}
      - N8N_RUNNERS_ENABLED=true
    volumes:
      - ./data/n8n:/home/node/.n8n
    ports:
      - "5679:5678"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - control-plane-net
      - stack_net

networks:
  control-plane-net:
    name: control-plane-net
  stack_net:
    external: true
```

### Step 4: Add Caddy Route

Append to `/home/damon/stack/Caddyfile`:

```caddyfile
control.n8n.leveredgeai.com {
    encode gzip
    reverse_proxy localhost:5679
}
```

### Step 5: Add DNS Record

In Cloudflare, add:

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | control.n8n | [server IP] | Proxied |

### Step 6: Deploy

```bash
# Generate credentials
cd /opt/leveredge/control-plane/n8n

# Edit .env with generated passwords
nano .env

# Start services
docker compose up -d

# Wait for health
sleep 10

# Check status
docker compose ps
docker compose logs --tail=50

# Reload Caddy
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Step 7: Verify

```bash
# Check n8n is running
curl -s http://localhost:5679/healthz

# Check external access (after DNS propagates)
curl -I https://control.n8n.leveredgeai.com
```

---

## ATLAS Workflow

After n8n is running, create the ATLAS orchestrator workflow.

### ATLAS Purpose

ATLAS receives all control plane requests and routes them to the appropriate agent or handles them directly.

### ATLAS Workflow Definition

Import this workflow into control plane n8n:

```json
{
  "name": "ATLAS - Master Orchestrator",
  "nodes": [
    {
      "parameters": {
        "httpMethod": "POST",
        "path": "atlas",
        "responseMode": "responseNode",
        "options": {}
      },
      "id": "webhook-trigger",
      "name": "ATLAS Webhook",
      "type": "n8n-nodes-base.webhook",
      "typeVersion": 2,
      "position": [200, 300],
      "webhookId": "atlas-main"
    },
    {
      "parameters": {
        "method": "POST",
        "url": "http://host.docker.internal:8099/events",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ source_agent: 'ATLAS', action: 'request_received', target: $json.body.target || 'unknown', details: { request_type: $json.body.type || 'unknown', timestamp: new Date().toISOString() } }) }}"
      },
      "id": "log-to-eventbus",
      "name": "Log to Event Bus",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.2,
      "position": [400, 300]
    },
    {
      "parameters": {
        "rules": {
          "rules": [
            {
              "outputKey": "health_check",
              "conditions": {
                "options": { "version": 2 },
                "conditions": [
                  {
                    "leftValue": "={{ $json.body.type }}",
                    "rightValue": "health",
                    "operator": { "type": "string", "operation": "equals" }
                  }
                ],
                "combinator": "and"
              }
            },
            {
              "outputKey": "status_request",
              "conditions": {
                "options": { "version": 2 },
                "conditions": [
                  {
                    "leftValue": "={{ $json.body.type }}",
                    "rightValue": "status",
                    "operator": { "type": "string", "operation": "equals" }
                  }
                ],
                "combinator": "and"
              }
            },
            {
              "outputKey": "agent_request",
              "conditions": {
                "options": { "version": 2 },
                "conditions": [
                  {
                    "leftValue": "={{ $json.body.target }}",
                    "rightValue": "",
                    "operator": { "type": "string", "operation": "notEmpty" }
                  }
                ],
                "combinator": "and"
              }
            }
          ],
          "fallbackOutput": "unknown_request"
        },
        "options": {}
      },
      "id": "router",
      "name": "Route Request",
      "type": "n8n-nodes-base.switch",
      "typeVersion": 3.2,
      "position": [600, 300]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ status: 'healthy', agent: 'ATLAS', timestamp: new Date().toISOString(), event_bus: 'connected' }) }}"
      },
      "id": "health-response",
      "name": "Health Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [850, 150]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ status: 'operational', agents: { ATLAS: { port: 8007, status: 'active' }, HADES: { port: 8008, status: 'pending' }, ARGUS: { port: 8009, status: 'pending' }, CHRONOS: { port: 8010, status: 'pending' }, HEPHAESTUS: { port: 8011, status: 'pending' }, AEGIS: { port: 8012, status: 'pending' }, ATHENA: { port: 8013, status: 'pending' }, HERMES: { port: 8014, status: 'pending' }, ALOY: { port: 8015, status: 'pending' } }, event_bus: { port: 8099, status: 'active' } }) }}"
      },
      "id": "status-response",
      "name": "Status Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [850, 300]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ status: 'received', message: 'Agent routing not yet implemented', target: $json.body.target, queued: true }) }}"
      },
      "id": "agent-response",
      "name": "Agent Request Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [850, 450]
    },
    {
      "parameters": {
        "respondWith": "json",
        "responseBody": "={{ JSON.stringify({ status: 'error', message: 'Unknown request type', received: $json.body }) }}",
        "options": { "responseCode": 400 }
      },
      "id": "unknown-response",
      "name": "Unknown Response",
      "type": "n8n-nodes-base.respondToWebhook",
      "typeVersion": 1.1,
      "position": [850, 600]
    }
  ],
  "connections": {
    "ATLAS Webhook": {
      "main": [[{ "node": "Log to Event Bus", "type": "main", "index": 0 }]]
    },
    "Log to Event Bus": {
      "main": [[{ "node": "Route Request", "type": "main", "index": 0 }]]
    },
    "Route Request": {
      "main": [
        [{ "node": "Health Response", "type": "main", "index": 0 }],
        [{ "node": "Status Response", "type": "main", "index": 0 }],
        [{ "node": "Agent Request Response", "type": "main", "index": 0 }],
        [{ "node": "Unknown Response", "type": "main", "index": 0 }]
      ]
    }
  },
  "settings": {
    "executionOrder": "v1"
  },
  "tags": [{ "name": "control-plane" }, { "name": "atlas" }]
}
```

### Import Workflow

Save the JSON above to `/opt/leveredge/control-plane/workflows/atlas-orchestrator.json`

Then import via n8n UI at `https://control.n8n.leveredgeai.com`:
1. Login with basic auth credentials
2. Click "Add workflow" → "Import from file"
3. Select the JSON file
4. Activate the workflow

### Verify ATLAS

```bash
# Health check
curl -X POST https://control.n8n.leveredgeai.com/webhook/atlas \
  -H "Content-Type: application/json" \
  -d '{"type": "health"}'

# Status check
curl -X POST https://control.n8n.leveredgeai.com/webhook/atlas \
  -H "Content-Type: application/json" \
  -d '{"type": "status"}'

# Check Event Bus received the events
curl http://localhost:8099/events | jq '.events | .[-2:]'
```

---

## Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| n8n container running | `docker ps \| grep control-n8n` | control-n8n Up |
| Postgres healthy | `docker compose ps` | control-n8n-postgres healthy |
| Local health | `curl localhost:5679/healthz` | {"status":"ok"} |
| External access | `curl -I https://control.n8n.leveredgeai.com` | 200 OK |
| ATLAS health | POST to /webhook/atlas with {"type":"health"} | {"status":"healthy",...} |
| Event Bus logging | `curl localhost:8099/events` | ATLAS events present |

---

## Output Required

After completion, provide:

1. `docker compose ps` output
2. `curl localhost:5679/healthz` output
3. External URL test result
4. ATLAS health check result
5. Event Bus showing ATLAS events

---

## Pinned for Later

- Cloudflare Access (replace basic auth)
- ATLAS FastAPI backend (for complex operations)
- Agent routing implementation
- n8n workflow versioning/backup

---

## Next Phase

Phase 2: HEPHAESTUS + AEGIS (Builder + Credential Vault)
