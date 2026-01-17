# AEGIS API Reference

AEGIS is the credential vault providing secure credential management, encryption, rotation, and health monitoring.

**Base URL:** `http://localhost:8012`

---

## Health Check

Check AEGIS service health and credential statistics.

### Request

```http
GET /health
```

### Response

```json
{
  "status": "healthy",
  "agent": "AEGIS",
  "version": "2.0",
  "credentials_count": 25,
  "healthy_count": 23,
  "expiring_count": 2,
  "expired_count": 0,
  "encryption": "enabled",
  "last_rotation_check": "2026-01-17T11:30:00Z"
}
```

---

## List Credentials

Get all registered credentials.

### Request

```http
GET /credentials
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status (active, expiring, expired) |
| `provider` | string | Filter by provider (n8n, supabase, api, env) |
| `type` | string | Filter by credential type |
| `limit` | integer | Max results (default: 100) |
| `offset` | integer | Pagination offset |

### Response

```json
{
  "credentials": [
    {
      "id": "cred_abc123",
      "name": "openai-api-key",
      "credential_type": "api_key",
      "provider": "api",
      "status": "active",
      "description": "OpenAI API key for LLM calls",
      "expires_at": "2026-06-01T00:00:00Z",
      "last_used_at": "2026-01-17T10:30:00Z",
      "rotation_enabled": true,
      "rotation_interval_hours": 720,
      "next_rotation_at": "2026-02-16T00:00:00Z",
      "tags": ["llm", "production"]
    }
  ],
  "total": 25,
  "healthy": 23,
  "expiring": 2,
  "expired": 0
}
```

---

## Get Credential Details

Get detailed information about a specific credential.

### Request

```http
GET /credentials/{name}
```

### Response

```json
{
  "id": "cred_abc123",
  "name": "openai-api-key",
  "credential_type": "api_key",
  "provider": "api",
  "status": "active",
  "description": "OpenAI API key for LLM calls",
  "provider_credential_id": "cred_n8n_456",
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2026-01-15T00:00:00Z",
  "expires_at": "2026-06-01T00:00:00Z",
  "last_used_at": "2026-01-17T10:30:00Z",
  "last_rotated_at": "2026-01-15T00:00:00Z",
  "last_health_check": "2026-01-17T11:00:00Z",
  "rotation_enabled": true,
  "rotation_interval_hours": 720,
  "rotation_strategy": "scheduled",
  "next_rotation_at": "2026-02-16T00:00:00Z",
  "alert_threshold_hours": 168,
  "tags": ["llm", "production"],
  "metadata": {
    "environment": "production",
    "owner": "platform-team"
  },
  "usage_stats": {
    "total_uses": 15420,
    "uses_last_24h": 523,
    "uses_last_7d": 3650
  },
  "version": 3,
  "version_history": [
    {"version": 3, "created_at": "2026-01-15T00:00:00Z", "reason": "rotation"},
    {"version": 2, "created_at": "2025-12-15T00:00:00Z", "reason": "rotation"},
    {"version": 1, "created_at": "2025-12-01T00:00:00Z", "reason": "initial"}
  ]
}
```

---

## Create Credential

Register a new credential with AEGIS.

### Request

```http
POST /credentials
Content-Type: application/json
```

```json
{
  "name": "anthropic-api-key",
  "credential_type": "api_key",
  "provider": "api",
  "description": "Anthropic API key for Claude",
  "value": "sk-ant-...",
  "expires_at": "2026-12-31T00:00:00Z",
  "rotation_enabled": true,
  "rotation_interval_hours": 720,
  "rotation_strategy": "scheduled",
  "alert_threshold_hours": 168,
  "tags": ["llm", "production"],
  "metadata": {
    "environment": "production"
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Unique credential name |
| `credential_type` | string | Yes | Type (api_key, oauth, database, etc.) |
| `provider` | string | Yes | Provider (n8n, supabase, api, env) |
| `description` | string | No | Human-readable description |
| `value` | string | No | Credential value (encrypted at rest) |
| `provider_credential_id` | string | No | n8n credential ID |
| `expires_at` | datetime | No | Expiration date |
| `rotation_enabled` | boolean | No | Enable auto-rotation |
| `rotation_interval_hours` | integer | No | Rotation interval (default: 720) |
| `rotation_strategy` | string | No | Strategy (manual, scheduled, on_expiry) |
| `alert_threshold_hours` | integer | No | Alert before expiry (default: 168) |
| `tags` | array | No | Tags for categorization |
| `metadata` | object | No | Custom metadata |

### Response

```json
{
  "id": "cred_xyz789",
  "name": "anthropic-api-key",
  "status": "active",
  "created_at": "2026-01-17T12:00:00Z",
  "encrypted": true
}
```

---

## Update Credential

Update credential metadata and settings.

### Request

```http
PATCH /credentials/{name}
Content-Type: application/json
```

```json
{
  "description": "Updated description",
  "expires_at": "2027-06-01T00:00:00Z",
  "rotation_enabled": true,
  "rotation_interval_hours": 360,
  "tags": ["llm", "production", "critical"]
}
```

### Response

```json
{
  "id": "cred_abc123",
  "name": "openai-api-key",
  "status": "active",
  "updated_at": "2026-01-17T12:00:00Z",
  "updated_fields": ["description", "expires_at", "rotation_interval_hours", "tags"]
}
```

---

## Delete (Retire) Credential

Retire a credential. Does not delete immediately; marks as retired.

### Request

```http
DELETE /credentials/{name}
```

### Response

```json
{
  "status": "retired",
  "credential_name": "old-api-key",
  "retired_at": "2026-01-17T12:00:00Z"
}
```

---

## Apply Credential to Workflow

Apply a credential to an n8n workflow node.

### Request

```http
POST /credentials/{name}/apply
Content-Type: application/json
```

```json
{
  "workflow_id": "workflow_123",
  "node_name": "HTTP Request",
  "requested_by": "HEPHAESTUS"
}
```

### Response

```json
{
  "status": "applied",
  "credential": "openai-api-key",
  "workflow_id": "workflow_123",
  "node": "HTTP Request",
  "applied_at": "2026-01-17T12:00:00Z"
}
```

---

## Rotate Credential

Manually trigger credential rotation.

### Request

```http
POST /credentials/{name}/rotate
Content-Type: application/json
```

```json
{
  "trigger": "manual",
  "reason": "Security audit requirement"
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `trigger` | string | Yes | Trigger type (manual, emergency) |
| `reason` | string | No | Reason for rotation |

### Response

```json
{
  "status": "rotated",
  "credential": "openai-api-key",
  "previous_version": 2,
  "new_version": 3,
  "duration_ms": 1250,
  "rotated_at": "2026-01-17T12:00:00Z"
}
```

---

## Rollback Credential

Rollback to a previous credential version.

### Request

```http
POST /credentials/{name}/rollback
Content-Type: application/json
```

```json
{
  "version": 2
}
```

### Response

```json
{
  "status": "rolled_back",
  "credential": "openai-api-key",
  "from_version": 3,
  "to_version": 2,
  "rolled_back_at": "2026-01-17T12:00:00Z"
}
```

---

## Test Credential

Test credential connectivity and validity.

### Request

```http
POST /credentials/{name}/test
```

### Response

```json
{
  "status": "healthy",
  "credential": "openai-api-key",
  "response_time_ms": 125,
  "details": {
    "authenticated": true,
    "rate_limit_remaining": 9500,
    "quota_remaining": 95
  },
  "tested_at": "2026-01-17T12:00:00Z"
}
```

---

## Health Dashboard

Get comprehensive health overview of all credentials.

### Request

```http
GET /health/dashboard
```

### Response

```json
{
  "summary": {
    "total": 25,
    "healthy": 23,
    "expiring": 2,
    "expired": 0,
    "failed": 0
  },
  "credentials": [
    {
      "name": "openai-api-key",
      "status": "active",
      "health": "healthy",
      "expires_in_hours": 4320,
      "last_used": "2026-01-17T10:30:00Z"
    },
    {
      "name": "supabase-service-key",
      "status": "expiring",
      "health": "healthy",
      "expires_in_hours": 120,
      "last_used": "2026-01-17T11:00:00Z"
    }
  ],
  "alerts": [
    {
      "credential": "supabase-service-key",
      "alert_type": "expiring",
      "message": "Credential expires in 5 days",
      "created_at": "2026-01-17T08:00:00Z"
    }
  ],
  "generated_at": "2026-01-17T12:00:00Z"
}
```

---

## Get Expiring Credentials

Get credentials expiring within threshold.

### Request

```http
GET /health/expiring?threshold_hours=168
```

### Response

```json
{
  "credentials": [
    {
      "name": "supabase-service-key",
      "expires_at": "2026-01-22T00:00:00Z",
      "expires_in_hours": 120,
      "rotation_enabled": true
    }
  ],
  "count": 1,
  "threshold_hours": 168
}
```

---

## Check All Credentials Health

Run health check on all credentials.

### Request

```http
POST /health/check-all
```

### Response

```json
{
  "checked": 25,
  "healthy": 24,
  "unhealthy": 1,
  "details": [
    {
      "name": "deprecated-api-key",
      "status": "unhealthy",
      "error": "Authentication failed",
      "response_time_ms": 0
    }
  ],
  "checked_at": "2026-01-17T12:00:00Z",
  "duration_ms": 5250
}
```

---

## Sync from n8n

Synchronize credentials from n8n.

### Request

```http
POST /sync/n8n
```

### Response

```json
{
  "synced": 15,
  "new": [
    {"name": "new-credential", "id": "cred_new123"}
  ],
  "updated": [
    {"name": "existing-credential", "changes": ["description"]}
  ],
  "synced_at": "2026-01-17T12:00:00Z"
}
```

---

## Audit Log

Get credential access audit log.

### Request

```http
GET /audit/log
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `credential_name` | string | Filter by credential |
| `action` | string | Filter by action |
| `actor` | string | Filter by actor |
| `start_date` | datetime | Start of time range |
| `end_date` | datetime | End of time range |
| `limit` | integer | Max results (default: 100) |

### Response

```json
{
  "log": [
    {
      "id": "log_abc123",
      "timestamp": "2026-01-17T12:00:00Z",
      "credential_name": "openai-api-key",
      "action": "applied",
      "actor": "HEPHAESTUS",
      "target": "workflow_123/HTTP Request",
      "success": true
    }
  ],
  "total": 1520
}
```

---

## Rotation Schedule

Get upcoming rotation schedule.

### Request

```http
GET /rotation/schedule
```

### Response

```json
{
  "upcoming_rotations": [
    {
      "credential": "openai-api-key",
      "scheduled_at": "2026-02-16T00:00:00Z",
      "strategy": "scheduled"
    }
  ],
  "overdue_rotations": [],
  "generated_at": "2026-01-17T12:00:00Z"
}
```

---

## Error Responses

### 400 Bad Request

```json
{
  "error": "bad_request",
  "message": "Credential name already exists",
  "credential": "duplicate-name"
}
```

### 403 Forbidden

```json
{
  "error": "forbidden",
  "message": "Credential access denied",
  "required_permission": "credential:rotate"
}
```

### 404 Not Found

```json
{
  "error": "not_found",
  "message": "Credential not found: unknown-credential"
}
```

### 409 Conflict

```json
{
  "error": "conflict",
  "message": "Credential is currently being rotated",
  "retry_after_ms": 5000
}
```
