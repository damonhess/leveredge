# Event Bus API Reference

The Event Bus provides inter-agent communication via a SQLite-backed message queue, enabling loosely coupled agent coordination.

**Base URL:** `http://localhost:8099`

---

## Overview

The Event Bus is the communication backbone of LeverEdge, allowing agents to:

- Publish events about their actions
- Subscribe to events from other agents
- Create audit trails
- Enable loose coupling between agents

### Event Types

| Event Type | Description | Publishers |
|------------|-------------|------------|
| `deployment_started` | Deployment initiated | HEPHAESTUS |
| `deployment_completed` | Deployment finished | HEPHAESTUS |
| `backup_created` | Backup completed | CHRONOS |
| `credential_rotated` | Credential rotated | AEGIS |
| `agent_usage` | LLM/API usage logged | All LLM agents |
| `alert_triggered` | Alert condition met | ARGUS |
| `workflow_executed` | Workflow completed | ATLAS |
| `notification_sent` | Notification delivered | HERMES |
| `health_check_failed` | Agent unhealthy | SENTINEL |
| `creative_project_completed` | Creative output ready | MUSE |

---

## Health Check

Check Event Bus service health.

### Request

```http
GET /health
```

### Response

```json
{
  "status": "healthy",
  "service": "event-bus",
  "version": "1.0",
  "events_total": 152340,
  "events_last_hour": 523,
  "subscribers": 12,
  "database_size_mb": 45.2,
  "uptime_seconds": 864000
}
```

---

## Publish Event

Publish an event to the bus.

### Request

```http
POST /publish
Content-Type: application/json
```

```json
{
  "event_type": "deployment_completed",
  "source": "HEPHAESTUS",
  "data": {
    "component": "prod-n8n",
    "version": "1.0.5",
    "duration_ms": 12500,
    "success": true
  },
  "priority": "normal",
  "metadata": {
    "correlation_id": "deploy_abc123",
    "triggered_by": "ATLAS"
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `event_type` | string | Yes | Type of event |
| `source` | string | Yes | Publishing agent name |
| `data` | object | Yes | Event payload |
| `priority` | string | No | Priority (low, normal, high, critical) |
| `metadata` | object | No | Additional metadata |

### Response

```json
{
  "event_id": "evt_xyz789",
  "event_type": "deployment_completed",
  "source": "HEPHAESTUS",
  "published_at": "2026-01-17T12:00:00Z",
  "subscribers_notified": 3
}
```

---

## Subscribe to Events

Register a subscription for specific event types.

### Request

```http
POST /subscribe
Content-Type: application/json
```

```json
{
  "subscriber": "HERMES",
  "event_types": ["deployment_completed", "alert_triggered", "credential_rotated"],
  "callback_url": "http://localhost:8014/webhook/events",
  "filter": {
    "priority": ["high", "critical"]
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `subscriber` | string | Yes | Subscribing agent name |
| `event_types` | array | Yes | Event types to subscribe to |
| `callback_url` | string | No | Webhook URL for push delivery |
| `filter` | object | No | Filter criteria |

### Response

```json
{
  "subscription_id": "sub_abc123",
  "subscriber": "HERMES",
  "event_types": ["deployment_completed", "alert_triggered", "credential_rotated"],
  "created_at": "2026-01-17T12:00:00Z",
  "delivery_method": "webhook"
}
```

---

## Unsubscribe

Remove a subscription.

### Request

```http
DELETE /subscribe/{subscription_id}
```

### Response

```json
{
  "subscription_id": "sub_abc123",
  "status": "unsubscribed",
  "removed_at": "2026-01-17T12:00:00Z"
}
```

---

## Get Recent Events

Retrieve recent events from the bus.

### Request

```http
GET /events
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_type` | string | Filter by event type |
| `source` | string | Filter by source agent |
| `priority` | string | Filter by priority |
| `since` | datetime | Events after this time |
| `limit` | integer | Max results (default: 100) |
| `offset` | integer | Pagination offset |

### Response

```json
{
  "events": [
    {
      "event_id": "evt_xyz789",
      "event_type": "deployment_completed",
      "source": "HEPHAESTUS",
      "data": {
        "component": "prod-n8n",
        "version": "1.0.5",
        "success": true
      },
      "priority": "normal",
      "metadata": {
        "correlation_id": "deploy_abc123"
      },
      "published_at": "2026-01-17T12:00:00Z"
    }
  ],
  "total": 152340,
  "limit": 100,
  "offset": 0
}
```

---

## Get Event by ID

Retrieve a specific event.

### Request

```http
GET /events/{event_id}
```

### Response

```json
{
  "event_id": "evt_xyz789",
  "event_type": "deployment_completed",
  "source": "HEPHAESTUS",
  "data": {
    "component": "prod-n8n",
    "version": "1.0.5",
    "duration_ms": 12500,
    "success": true
  },
  "priority": "normal",
  "metadata": {
    "correlation_id": "deploy_abc123",
    "triggered_by": "ATLAS"
  },
  "published_at": "2026-01-17T12:00:00Z",
  "deliveries": [
    {
      "subscriber": "HERMES",
      "delivered_at": "2026-01-17T12:00:01Z",
      "status": "success"
    },
    {
      "subscriber": "ARGUS",
      "delivered_at": "2026-01-17T12:00:01Z",
      "status": "success"
    }
  ]
}
```

---

## Poll Events

Poll for new events (for subscribers without webhook).

### Request

```http
GET /poll/{subscriber}
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `since_event_id` | string | Get events after this ID |
| `limit` | integer | Max events (default: 50) |
| `timeout_ms` | integer | Long-poll timeout (max: 30000) |

### Response

```json
{
  "events": [
    {
      "event_id": "evt_xyz789",
      "event_type": "deployment_completed",
      "source": "HEPHAESTUS",
      "data": {...},
      "published_at": "2026-01-17T12:00:00Z"
    }
  ],
  "next_cursor": "evt_xyz790",
  "has_more": false
}
```

---

## Acknowledge Events

Acknowledge receipt of events (for delivery tracking).

### Request

```http
POST /ack
Content-Type: application/json
```

```json
{
  "subscriber": "HERMES",
  "event_ids": ["evt_xyz789", "evt_xyz790"]
}
```

### Response

```json
{
  "acknowledged": 2,
  "subscriber": "HERMES",
  "acknowledged_at": "2026-01-17T12:00:00Z"
}
```

---

## Get Event Statistics

Get event bus statistics.

### Request

```http
GET /stats
```

### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | Time period (hour, day, week) |

### Response

```json
{
  "period": "day",
  "total_events": 15234,
  "by_type": {
    "agent_usage": 8500,
    "workflow_executed": 3200,
    "deployment_completed": 45,
    "backup_created": 24,
    "notification_sent": 2800,
    "other": 665
  },
  "by_source": {
    "SCHOLAR": 3500,
    "CHIRON": 2800,
    "ARIA": 5000,
    "ATLAS": 1500,
    "HERMES": 1200,
    "other": 1234
  },
  "by_priority": {
    "low": 2500,
    "normal": 12000,
    "high": 700,
    "critical": 34
  },
  "delivery_stats": {
    "total_deliveries": 45000,
    "successful": 44950,
    "failed": 50,
    "success_rate": 99.89
  }
}
```

---

## List Subscriptions

Get all active subscriptions.

### Request

```http
GET /subscriptions
```

### Response

```json
{
  "subscriptions": [
    {
      "subscription_id": "sub_abc123",
      "subscriber": "HERMES",
      "event_types": ["deployment_completed", "alert_triggered"],
      "callback_url": "http://localhost:8014/webhook/events",
      "created_at": "2026-01-15T00:00:00Z",
      "events_delivered": 523,
      "last_delivery": "2026-01-17T11:55:00Z"
    }
  ],
  "total": 12
}
```

---

## Replay Events

Replay historical events (for recovery or debugging).

### Request

```http
POST /replay
Content-Type: application/json
```

```json
{
  "subscriber": "HERMES",
  "start_time": "2026-01-17T10:00:00Z",
  "end_time": "2026-01-17T11:00:00Z",
  "event_types": ["deployment_completed"]
}
```

### Response

```json
{
  "replayed": 5,
  "subscriber": "HERMES",
  "time_range": {
    "start": "2026-01-17T10:00:00Z",
    "end": "2026-01-17T11:00:00Z"
  },
  "replay_started_at": "2026-01-17T12:00:00Z"
}
```

---

## Webhook Payload Format

When events are delivered via webhook, the payload format:

```json
{
  "delivery_id": "del_xyz123",
  "events": [
    {
      "event_id": "evt_xyz789",
      "event_type": "deployment_completed",
      "source": "HEPHAESTUS",
      "data": {...},
      "priority": "normal",
      "published_at": "2026-01-17T12:00:00Z"
    }
  ],
  "subscription_id": "sub_abc123",
  "delivered_at": "2026-01-17T12:00:01Z"
}
```

### Webhook Headers

```http
X-EventBus-Delivery-ID: del_xyz123
X-EventBus-Subscription-ID: sub_abc123
X-EventBus-Timestamp: 1705488001
X-EventBus-Signature: sha256=...
Content-Type: application/json
```

---

## Event Retention

Events are retained based on priority:

| Priority | Retention |
|----------|-----------|
| critical | 90 days |
| high | 30 days |
| normal | 7 days |
| low | 1 day |

---

## Error Responses

### 400 Bad Request

```json
{
  "error": "bad_request",
  "message": "Invalid event type: unknown_event"
}
```

### 404 Not Found

```json
{
  "error": "not_found",
  "message": "Event not found: evt_unknown"
}
```

### 429 Too Many Requests

```json
{
  "error": "rate_limited",
  "message": "Too many publish requests",
  "retry_after_ms": 1000
}
```

---

## Rate Limits

| Operation | Rate Limit |
|-----------|------------|
| Publish | 100 events/second |
| Subscribe | 10 requests/minute |
| Poll | 60 requests/minute |
| Query | 120 requests/minute |
