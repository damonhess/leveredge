# Configuration Guide

This guide covers configuring LeverEdge agents and services.

## Agent Registry

The central configuration file is `/opt/leveredge/config/agent-registry.yaml`. This file defines all agents, their endpoints, and orchestration chains.

### Global Configuration

```yaml
config:
  default_timeout_ms: 60000
  max_chain_depth: 10
  max_parallel_calls: 5
  retry_attempts: 2
  retry_delay_ms: 1000
  circuit_breaker_threshold: 5
  circuit_breaker_reset_ms: 30000

  # Cost tracking
  cost_tracking_enabled: true
  cost_log_table: agent_usage_logs

  # Event bus
  event_bus_url: http://event-bus:8099
  publish_events: true

  # Health check intervals
  health_check_interval_ms: 30000
  health_check_timeout_ms: 5000
```

### Agent Definition Example

```yaml
agents:
  atlas:
    name: ATLAS
    port: 8007
    type: orchestrator
    description: "Orchestration engine, chain execution"
    endpoints:
      health:
        path: /health
        method: GET
      orchestrate:
        path: /orchestrate
        method: POST
        timeout_ms: 120000
    dependencies:
      - event-bus
    tags:
      - core
      - orchestration
```

## Environment Variables

### Control Plane n8n

```bash
# /opt/leveredge/control-plane/n8n/.env

N8N_HOST=0.0.0.0
N8N_PORT=5679
N8N_PROTOCOL=https
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=<secure-password>

# Database
DB_TYPE=postgresdb
DB_POSTGRESDB_HOST=control-n8n-postgres
DB_POSTGRESDB_PORT=5432
DB_POSTGRESDB_DATABASE=n8n
DB_POSTGRESDB_USER=n8n
DB_POSTGRESDB_PASSWORD=<secure-password>

# Webhook URL
WEBHOOK_URL=https://control.n8n.leveredgeai.com/

# Execution
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=168
```

### Agent Environment Variables

Common environment variables for FastAPI agents:

```bash
# Supabase connection
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_SERVICE_KEY=<service-role-key>

# Event Bus
EVENT_BUS_URL=http://event-bus:8099

# Anthropic API (for LLM-powered agents)
ANTHROPIC_API_KEY=<api-key>

# Logging
LOG_LEVEL=INFO
```

## Network Configuration

### Docker Networks

| Network | Purpose | Services |
|---------|---------|----------|
| `control-plane-net` | Control plane internal | All agents, control n8n |
| `data-plane-net` | PROD internal | prod-n8n, prod-n8n-postgres |
| `data-plane-dev-net` | DEV internal | dev-n8n, dev-n8n-postgres |
| `stack_net` | Shared services | Caddy, Supabase |

### External Domains

Configure your reverse proxy (Caddy, nginx) to route these domains:

| Domain | Target | Port |
|--------|--------|------|
| control.n8n.leveredgeai.com | Control n8n | 5679 |
| n8n.leveredgeai.com | PROD n8n | 5678 |
| dev.n8n.leveredgeai.com | DEV n8n | 5680 |
| aria.leveredgeai.com | ARIA frontend | - |
| api.leveredgeai.com | Supabase Kong | 8000 |
| studio.leveredgeai.com | Supabase Studio | 3000 |
| grafana.leveredgeai.com | Grafana | 3001 |

### Caddy Configuration Example

```caddyfile
control.n8n.leveredgeai.com {
    reverse_proxy localhost:5679
}

n8n.leveredgeai.com {
    reverse_proxy localhost:5678
}

api.leveredgeai.com {
    reverse_proxy localhost:8000
}
```

## Agent-Specific Configuration

### CHRONOS (Backup)

Configure backup destinations and schedules:

```yaml
# In agent-registry.yaml
chronos:
  config:
    backup_destination: /opt/leveredge/shared/backups
    retention_days: 30
    schedule:
      daily: "0 2 * * *"  # 2 AM UTC
      weekly: "0 3 * * 0"  # 3 AM Sunday
```

### AEGIS (Credentials)

Configure encryption and rotation:

```yaml
aegis:
  config:
    master_key_path: /opt/leveredge/secrets/aegis_master.key
    encryption_algorithm: AES-256
    rotation:
      default_interval_hours: 720  # 30 days
      alert_threshold_hours: 168   # 7 days before expiry
```

### CHIRON (Business Mentor)

Configure LLM settings:

```yaml
chiron:
  config:
    model: claude-sonnet-4-20250514
    max_tokens: 4096
    temperature: 0.7
    system_prompt_path: /opt/leveredge/config/prompts/chiron.txt
```

### SCHOLAR (Market Research)

Configure web search and research settings:

```yaml
scholar:
  config:
    model: claude-sonnet-4-20250514
    max_tokens: 8192
    web_search_enabled: true
    cache_duration_hours: 24
```

## Cost Tracking Configuration

Enable cost tracking for all LLM-powered agents:

```python
# /opt/leveredge/control-plane/shared/cost_tracker.py

PRICING = {
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
}

FEATURE_COSTS = {
    "web_search": 0.01,
    "pdf_processing": 0.02,
    "image_processing": 0.01,
}
```

## Orchestration Chains

Define multi-agent chains in the registry:

```yaml
chains:
  research-and-plan:
    description: "Research a topic, create action plan"
    steps:
      - agent: scholar
        action: deep-research
        output_key: research_results
      - agent: chiron
        action: sprint-plan
        input_from: research_results

  safe-deployment:
    description: "Backup, deploy, verify, rollback if needed"
    steps:
      - agent: chronos
        action: backup
      - agent: hermes
        action: notify
        params:
          message: "Deployment starting"
      - agent: argus
        action: verify
      - agent: hades
        action: rollback
        condition: "previous_step.failed"
```

## MCP Server Configuration

Configure MCP servers for Claude integration:

```json
// .mcp.json
{
  "servers": {
    "n8n-control": {
      "type": "http",
      "url": "http://localhost:5679",
      "description": "Control plane n8n"
    },
    "hephaestus": {
      "type": "http",
      "url": "http://localhost:8011",
      "description": "File operations and commands"
    }
  }
}
```

## Validation

After configuration changes, validate the setup:

```bash
# Validate agent registry
curl http://localhost:8019/validate-registry

# Check all agent health
curl http://localhost:8019/fleet-health

# Test orchestration chain
curl -X POST http://localhost:8007/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"chain_name": "research-and-plan", "input": {"topic": "test"}}'
```

## Next Steps

- [Explore Core Agents](../agents/core.md)
- [Set up Monitoring](../operations/monitoring.md)
- [Review API Reference](../api/atlas.md)
