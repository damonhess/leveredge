# Event Bus Architecture

The Event Bus is the communication backbone of LeverEdge, providing asynchronous inter-agent communication with full audit capabilities.

## Overview

```
+------------------------------------------------------------------+
|                         EVENT BUS                                 |
|                                                                   |
|  +------------------+     +------------------+     +------------+ |
|  |    Publishers    |     |     SQLite       |     | Subscribers| |
|  |                  |     |    Database      |     |            | |
|  |  ATLAS           |     |                  |     | HERMES     | |
|  |  HEPHAESTUS      |---->|  events table    |---->| ARGUS      | |
|  |  CHRONOS         |     |  subs table      |     | ALOY       | |
|  |  AEGIS           |     |  deliveries      |     | ARIA       | |
|  |  SCHOLAR         |     |                  |     |            | |
|  |  CHIRON          |     +------------------+     +------------+ |
|  |  ...             |                                            |
|  +------------------+                                            |
|                                                                   |
+------------------------------------------------------------------+
```

## Design Principles

### 1. Loose Coupling

Agents don't need to know about each other. They publish events to the bus, and interested subscribers receive them automatically.

### 2. Guaranteed Delivery

Events are persisted to SQLite before acknowledgment, ensuring no events are lost even if subscribers are temporarily unavailable.

### 3. Complete Audit Trail

Every event is stored with metadata, enabling:
- Debugging and troubleshooting
- Compliance auditing
- Usage analytics
- Anomaly detection

### 4. Priority-Based Processing

Events are processed based on priority:

| Priority | Description | Retention |
|----------|-------------|-----------|
| `critical` | System failures, security alerts | 90 days |
| `high` | Important operations | 30 days |
| `normal` | Standard events | 7 days |
| `low` | Debug, informational | 1 day |

---

## Event Structure

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
    "triggered_by": "ATLAS",
    "chain_execution_id": "exec_456"
  },
  "published_at": "2026-01-17T12:00:00Z"
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | string | Unique event identifier |
| `event_type` | string | Type of event (see Event Types) |
| `source` | string | Publishing agent name |
| `data` | object | Event payload (schema varies by type) |
| `priority` | string | Priority level |
| `metadata` | object | Additional context |
| `published_at` | datetime | Publication timestamp |

---

## Event Types

### Infrastructure Events

| Event Type | Description | Publishers |
|------------|-------------|------------|
| `deployment_started` | Deployment initiated | HEPHAESTUS |
| `deployment_completed` | Deployment finished | HEPHAESTUS |
| `deployment_failed` | Deployment failed | HEPHAESTUS |
| `backup_created` | Backup completed | CHRONOS |
| `backup_failed` | Backup failed | CHRONOS |
| `rollback_initiated` | Rollback started | HADES |
| `rollback_completed` | Rollback finished | HADES |

### Security Events

| Event Type | Description | Publishers |
|------------|-------------|------------|
| `credential_created` | New credential registered | AEGIS |
| `credential_rotated` | Credential rotated | AEGIS |
| `credential_expired` | Credential expired | AEGIS |
| `credential_accessed` | Credential used | AEGIS |
| `security_alert` | Security issue detected | CERBERUS |

### Operational Events

| Event Type | Description | Publishers |
|------------|-------------|------------|
| `agent_started` | Agent came online | Any agent |
| `agent_stopped` | Agent went offline | SENTINEL |
| `health_check_failed` | Health check failure | SENTINEL |
| `alert_triggered` | Alert condition met | ARGUS |
| `notification_sent` | Notification delivered | HERMES |

### Usage Events

| Event Type | Description | Publishers |
|------------|-------------|------------|
| `agent_usage` | LLM/API usage logged | All LLM agents |
| `workflow_executed` | Workflow completed | ATLAS |
| `chain_executed` | Chain completed | ATLAS |

### Creative Events

| Event Type | Description | Publishers |
|------------|-------------|------------|
| `creative_project_started` | Project initiated | MUSE |
| `creative_project_completed` | Project finished | MUSE |
| `content_generated` | Content created | CALLIOPE, ERATO |
| `review_completed` | Review finished | CLIO |

---

## Subscription Model

### Pull Model (Polling)

Subscribers poll for new events:

```
Subscriber                 Event Bus
    |                          |
    |-- GET /poll/HERMES ----->|
    |                          |
    |<-- events[] -------------|
    |                          |
    |-- POST /ack ------------>|
    |                          |
```

### Push Model (Webhooks)

Events are pushed to subscriber endpoints:

```
Event Bus                 Subscriber (HERMES)
    |                          |
    |-- POST /webhook -------->|
    |                          |
    |<-- 200 OK ---------------|
    |                          |
```

### Subscription Configuration

```json
{
  "subscriber": "HERMES",
  "event_types": [
    "deployment_completed",
    "deployment_failed",
    "credential_expired",
    "security_alert"
  ],
  "callback_url": "http://localhost:8014/webhook/events",
  "filter": {
    "priority": ["high", "critical"],
    "source": ["AEGIS", "HEPHAESTUS", "CERBERUS"]
  },
  "retry_policy": {
    "max_retries": 3,
    "backoff_ms": [1000, 5000, 15000]
  }
}
```

---

## Database Schema

```sql
-- Events table
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    data TEXT NOT NULL,  -- JSON
    priority TEXT DEFAULT 'normal',
    metadata TEXT,  -- JSON
    published_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_published ON events(published_at);
CREATE INDEX idx_events_expires ON events(expires_at);

-- Subscriptions table
CREATE TABLE subscriptions (
    subscription_id TEXT PRIMARY KEY,
    subscriber TEXT NOT NULL,
    event_types TEXT NOT NULL,  -- JSON array
    callback_url TEXT,
    filter TEXT,  -- JSON
    created_at TEXT NOT NULL,
    last_delivery TEXT
);

CREATE INDEX idx_subs_subscriber ON subscriptions(subscriber);

-- Deliveries table (for tracking)
CREATE TABLE deliveries (
    delivery_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    subscription_id TEXT NOT NULL,
    subscriber TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    delivered_at TEXT,
    acknowledged_at TEXT,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);

CREATE INDEX idx_del_event ON deliveries(event_id);
CREATE INDEX idx_del_subscriber ON deliveries(subscriber);
CREATE INDEX idx_del_status ON deliveries(status);
```

---

## Delivery Guarantees

### At-Least-Once Delivery

Events are delivered at least once. Subscribers must be idempotent.

### Retry Policy

Failed deliveries are retried with exponential backoff:

| Retry | Delay |
|-------|-------|
| 1 | 1 second |
| 2 | 5 seconds |
| 3 | 15 seconds |
| 4+ | Manual intervention |

### Dead Letter Queue

Events that fail all retries are moved to a dead letter queue for manual review.

---

## Usage Patterns

### Pattern 1: Notification on Completion

```
HEPHAESTUS deploys
      |
      v
Event Bus (deployment_completed)
      |
      v
HERMES receives
      |
      v
Send Telegram notification
```

### Pattern 2: Audit Logging

```
AEGIS rotates credential
      |
      v
Event Bus (credential_rotated)
      |
      v
ALOY receives
      |
      v
Log to audit database
```

### Pattern 3: Chain Coordination

```
ATLAS executes chain
      |
      +-- Step 1: SCHOLAR research
      |        |
      |        v
      |   Event Bus (research_completed)
      |        |
      |        v
      +-- Step 2: CHIRON planning (triggered by event)
```

---

## Best Practices

### 1. Use Correlation IDs

Include correlation IDs in metadata to trace related events:

```json
{
  "metadata": {
    "correlation_id": "deploy_abc123",
    "chain_execution_id": "exec_456"
  }
}
```

### 2. Keep Payloads Small

Store large data elsewhere and include references:

```json
{
  "data": {
    "report_id": "report_xyz",
    "summary": "Brief summary",
    "full_report_url": "/api/reports/report_xyz"
  }
}
```

### 3. Use Appropriate Priorities

- `critical`: Security breaches, system failures
- `high`: Failed operations, expiring credentials
- `normal`: Standard operations
- `low`: Debug information, metrics

### 4. Handle Duplicates

Subscribers should be idempotent since events may be delivered multiple times:

```python
async def handle_event(event):
    # Check if already processed
    if await is_processed(event["event_id"]):
        return

    # Process event
    await process(event)

    # Mark as processed
    await mark_processed(event["event_id"])
```

---

## Monitoring

### Metrics Available

| Metric | Description |
|--------|-------------|
| `events_published_total` | Total events published |
| `events_delivered_total` | Total successful deliveries |
| `events_failed_total` | Total failed deliveries |
| `delivery_latency_ms` | Time from publish to delivery |
| `subscription_count` | Active subscriptions |
| `dead_letter_count` | Events in dead letter queue |

### Health Check

```bash
curl http://localhost:8099/health
```

```json
{
  "status": "healthy",
  "events_total": 152340,
  "events_last_hour": 523,
  "subscribers": 12,
  "delivery_success_rate": 99.89
}
```

---

## Related Documentation

- [Event Bus API Reference](../api/event-bus.md)
- [Architecture Overview](overview.md)
- [Monitoring Guide](../operations/monitoring.md)
