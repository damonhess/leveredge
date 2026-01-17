# Log Aggregation System

Central log collection, search, and alerting system for LeverEdge agents.

## Overview

This system aggregates logs from all agents, provides search capabilities, and sends error alerts to HERMES for critical issues.

## Components

### aggregator.py
Main FastAPI application running on port 8062. Provides REST API endpoints and serves the web UI.

### log_collector.py
Background task that monitors `/tmp/*.log` files where agents write their logs. Parses various log formats and stores them in the aggregated directory.

### search.py
Search functionality supporting:
- Filtered queries (by agent, level, time range)
- Full-text regex search
- Log context retrieval
- Time-based aggregation
- Error summaries

### alerter.py
Error detection and alerting:
- Immediate alerts for CRITICAL/FATAL errors
- Threshold-based alerts for ERROR (5+ in 5 minutes)
- Cooldown period to prevent alert spam
- Pattern matching for known issue types
- Daily error summaries

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/` | GET | Web UI for viewing logs |
| `/api/logs` | GET | Get recent logs with filters |
| `/api/logs` | POST | Ingest a log entry |
| `/api/logs/search?q=error` | GET | Search logs by text |
| `/api/logs/agent/{agent_name}` | GET | Get logs for specific agent |
| `/api/agents` | GET | List all agents with logs |
| `/api/stats` | GET | Get log statistics |

## Query Parameters

### GET /api/logs
- `agent` - Filter by agent name
- `level` - Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `start_time` - ISO timestamp for start of range
- `end_time` - ISO timestamp for end of range
- `limit` - Maximum results (default: 100, max: 1000)
- `offset` - Skip N results for pagination

### GET /api/logs/search
- `q` - Search query (supports regex)
- `agent` - Optional agent filter
- `level` - Optional level filter
- `limit` - Maximum results

## Log Entry Format

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "agent": "CERBERUS",
  "message": "Authentication successful for user@example.com",
  "source": "/tmp/cerberus.log",
  "metadata": {}
}
```

## Supported Log Formats

The collector automatically parses these formats:

1. **JSON**: `{"timestamp": "...", "level": "INFO", "agent": "...", "message": "..."}`
2. **Standard**: `2024-01-15 10:30:00 - INFO - AGENT - Message`
3. **Bracketed**: `[INFO] AGENT: Message`
4. **Simple**: `INFO - Message` (agent extracted from filename)
5. **Plain text**: Entire line as message

## Log Rotation

- Logs are automatically rotated after 7 days
- Rotation runs daily at startup and every 24 hours
- Old log files are deleted, not archived

## Alerting

Alerts are sent to HERMES at the configured URL (default: `http://localhost:8060`).

### Alert Triggers
- **CRITICAL/FATAL**: Immediate alert
- **ERROR**: Alert after 5+ errors in 5 minutes for same agent/message pattern
- **Pattern Match**: Known patterns (database issues, memory, auth failures, etc.)

### Cooldown
Each alert pattern has a 10-minute cooldown to prevent spam.

## Configuration

Environment variables:
- `HERMES_URL` - HERMES endpoint for alerts (default: `http://localhost:8060`)

Constants in `aggregator.py`:
- `AGGREGATED_DIR` - Storage location (default: `/opt/leveredge/monitoring/logs/aggregated`)
- `LOG_SOURCES` - Glob patterns for log files (default: `/tmp/*.log`)
- `RETENTION_DAYS` - Days to keep logs (default: 7)
- `COLLECT_INTERVAL` - Seconds between collection cycles (default: 30)

## Installation

```bash
cd /opt/leveredge/monitoring/logs
pip install -r requirements.txt
```

## Running

### Direct
```bash
python aggregator.py
```

### With Uvicorn
```bash
uvicorn aggregator:app --host 0.0.0.0 --port 8062 --reload
```

### As a Service
```bash
# Create systemd service file at /etc/systemd/system/log-aggregator.service
[Unit]
Description=LeverEdge Log Aggregator
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/leveredge/monitoring/logs
ExecStart=/usr/bin/python3 /opt/leveredge/monitoring/logs/aggregator.py
Restart=always
RestartSec=5
Environment=HERMES_URL=http://localhost:8060

[Install]
WantedBy=multi-user.target
```

## Web UI

Access the web interface at `http://localhost:8062/`

Features:
- Real-time log viewing with auto-refresh
- Filter by agent and log level
- Full-text search with regex support
- Pagination for large log sets
- Statistics dashboard

## Agent Integration

Agents should write logs to `/tmp/{agent_name}.log` in any supported format:

```python
import json
from datetime import datetime

def log(level, message, metadata=None):
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "agent": "MY_AGENT",
        "message": message,
        "metadata": metadata or {}
    }
    with open("/tmp/my_agent.log", "a") as f:
        f.write(json.dumps(entry) + "\n")
```

Or use the API directly:

```python
import httpx

async def log_to_aggregator(level, message):
    await httpx.post("http://localhost:8062/api/logs", json={
        "level": level,
        "agent": "MY_AGENT",
        "message": message
    })
```
