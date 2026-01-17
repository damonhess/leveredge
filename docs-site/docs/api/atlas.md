# ATLAS API Reference

ATLAS is the orchestration engine that coordinates multi-agent workflows and chain execution.

**Base URL:** `http://localhost:8007`

---

## Health Check

Check ATLAS service health and status.

### Request

```http
GET /health
```

### Response

```json
{
  "status": "healthy",
  "agent": "ATLAS",
  "version": "2.0",
  "uptime_seconds": 86400,
  "chains_available": 7,
  "active_executions": 0
}
```

---

## Orchestrate Chain

Execute a predefined multi-agent chain.

### Request

```http
POST /orchestrate
Content-Type: application/json
```

```json
{
  "chain_name": "research-and-plan",
  "input": {
    "topic": "Compliance automation market analysis"
  },
  "options": {
    "timeout_ms": 120000,
    "notify_on_complete": true
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `chain_name` | string | Yes | Name of the chain to execute |
| `input` | object | Yes | Input data for the chain |
| `options.timeout_ms` | integer | No | Execution timeout (default: 120000) |
| `options.notify_on_complete` | boolean | No | Send notification on completion |

### Response

```json
{
  "execution_id": "exec_abc123",
  "chain_name": "research-and-plan",
  "status": "running",
  "started_at": "2026-01-17T12:00:00Z",
  "steps": [
    {
      "step": 1,
      "agent": "scholar",
      "action": "deep-research",
      "status": "running"
    },
    {
      "step": 2,
      "agent": "chiron",
      "action": "sprint-plan",
      "status": "pending"
    }
  ]
}
```

### Available Chains

| Chain Name | Description | Steps |
|------------|-------------|-------|
| `research-and-plan` | Research topic, create action plan | SCHOLAR -> CHIRON |
| `validate-and-decide` | Validate assumption, decide next steps | SCHOLAR -> CHIRON |
| `comprehensive-market-analysis` | Parallel research, strategic synthesis | SCHOLAR (x3) -> CHIRON |
| `niche-evaluation` | Compare niches, recommend best | SCHOLAR -> CHIRON |
| `weekly-planning` | Review, research blockers, plan sprint | CHIRON -> SCHOLAR -> CHIRON |
| `fear-to-action` | Analyze fear, find evidence, create plan | CHIRON -> SCHOLAR -> CHIRON |
| `safe-deployment` | Backup, deploy, verify, rollback if needed | CHRONOS -> HERMES -> ARGUS -> HADES |

---

## List Chains

Get all available orchestration chains.

### Request

```http
GET /chains
```

### Response

```json
{
  "chains": [
    {
      "name": "research-and-plan",
      "description": "Research a topic, create action plan",
      "steps": [
        {
          "agent": "scholar",
          "action": "deep-research"
        },
        {
          "agent": "chiron",
          "action": "sprint-plan"
        }
      ],
      "estimated_duration_ms": 60000,
      "cost_estimate": 0.15
    }
  ],
  "total": 7
}
```

---

## Get Execution Status

Get the status of a running or completed chain execution.

### Request

```http
GET /status/{execution_id}
```

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `execution_id` | string | The execution ID |

### Response

```json
{
  "execution_id": "exec_abc123",
  "chain_name": "research-and-plan",
  "status": "completed",
  "started_at": "2026-01-17T12:00:00Z",
  "completed_at": "2026-01-17T12:01:30Z",
  "duration_ms": 90000,
  "steps": [
    {
      "step": 1,
      "agent": "scholar",
      "action": "deep-research",
      "status": "completed",
      "started_at": "2026-01-17T12:00:00Z",
      "completed_at": "2026-01-17T12:00:45Z",
      "output": {
        "summary": "Research findings..."
      }
    },
    {
      "step": 2,
      "agent": "chiron",
      "action": "sprint-plan",
      "status": "completed",
      "started_at": "2026-01-17T12:00:45Z",
      "completed_at": "2026-01-17T12:01:30Z",
      "output": {
        "plan": "Sprint plan..."
      }
    }
  ],
  "final_output": {
    "research": "...",
    "plan": "..."
  },
  "total_cost": 0.12
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `pending` | Execution queued |
| `running` | Currently executing |
| `completed` | Successfully completed |
| `failed` | Execution failed |
| `cancelled` | Execution cancelled |
| `timeout` | Execution timed out |

---

## Call Single Agent

Call a single agent directly without a chain.

### Request

```http
POST /agent/call
Content-Type: application/json
```

```json
{
  "agent": "scholar",
  "action": "deep-research",
  "payload": {
    "question": "What are the top compliance software companies in 2026?"
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent` | string | Yes | Agent name (lowercase) |
| `action` | string | Yes | Action/endpoint to call |
| `payload` | object | Yes | Request payload for the agent |

### Response

```json
{
  "agent": "scholar",
  "action": "deep-research",
  "status": "success",
  "duration_ms": 12500,
  "response": {
    "findings": "...",
    "sources": ["..."],
    "confidence": "high"
  },
  "cost": 0.08
}
```

---

## List Agents

Get all registered agents and their status.

### Request

```http
GET /agents
```

### Response

```json
{
  "agents": [
    {
      "name": "ATLAS",
      "port": 8007,
      "type": "orchestrator",
      "status": "healthy",
      "last_health_check": "2026-01-17T12:00:00Z",
      "actions": ["orchestrate", "chains", "agent/call"]
    },
    {
      "name": "SCHOLAR",
      "port": 8018,
      "type": "llm",
      "status": "healthy",
      "last_health_check": "2026-01-17T12:00:00Z",
      "actions": ["deep-research", "competitors", "market-size"]
    }
  ],
  "total": 15,
  "healthy": 15,
  "unhealthy": 0
}
```

---

## Cancel Execution

Cancel a running chain execution.

### Request

```http
POST /cancel/{execution_id}
```

### Response

```json
{
  "execution_id": "exec_abc123",
  "status": "cancelled",
  "cancelled_at": "2026-01-17T12:01:00Z",
  "completed_steps": 1,
  "cancelled_steps": 1
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "error": "bad_request",
  "message": "Invalid chain name: unknown-chain",
  "details": {
    "available_chains": ["research-and-plan", "validate-and-decide"]
  }
}
```

### 404 Not Found

```json
{
  "error": "not_found",
  "message": "Execution not found: exec_xyz789"
}
```

### 500 Internal Server Error

```json
{
  "error": "internal_error",
  "message": "Agent communication failed",
  "details": {
    "agent": "scholar",
    "reason": "connection timeout"
  }
}
```

### 504 Gateway Timeout

```json
{
  "error": "timeout",
  "message": "Chain execution timed out",
  "execution_id": "exec_abc123",
  "timeout_ms": 120000
}
```

---

## Webhooks

ATLAS can send webhooks on chain completion.

### Configuration

Set webhook URL in chain options:

```json
{
  "chain_name": "research-and-plan",
  "input": {"topic": "..."},
  "options": {
    "webhook_url": "https://your-server.com/webhook",
    "webhook_secret": "your-secret"
  }
}
```

### Webhook Payload

```json
{
  "event": "chain_completed",
  "execution_id": "exec_abc123",
  "chain_name": "research-and-plan",
  "status": "completed",
  "final_output": {...},
  "duration_ms": 90000,
  "timestamp": "2026-01-17T12:01:30Z"
}
```

### Webhook Headers

```http
X-Atlas-Signature: sha256=...
X-Atlas-Timestamp: 1705488090
Content-Type: application/json
```

---

## Rate Limits

| Endpoint | Rate Limit |
|----------|------------|
| `/orchestrate` | 10 requests/minute |
| `/agent/call` | 30 requests/minute |
| Other endpoints | 60 requests/minute |

Rate limit headers:

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1705488090
```
