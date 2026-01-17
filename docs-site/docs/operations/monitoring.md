# Monitoring Guide

This guide covers monitoring the LeverEdge infrastructure using ARGUS, Prometheus, and Grafana.

## Overview

```
+------------------------------------------------------------------+
|                    MONITORING STACK                               |
|                                                                   |
|  Agents                                                           |
|      |                                                            |
|      | /metrics, /health                                          |
|      v                                                            |
|  +------------------+     +------------------+                    |
|  |     ARGUS        |---->|   Prometheus     |                    |
|  |   Aggregator     |     |   Time Series    |                    |
|  +------------------+     +--------+---------+                    |
|                                    |                              |
|                                    v                              |
|                           +------------------+                    |
|                           |    Grafana       |                    |
|                           |   Dashboards     |                    |
|                           +------------------+                    |
|                                    |                              |
|                                    v                              |
|                           grafana.leveredgeai.com                 |
|                                                                   |
+------------------------------------------------------------------+
```

## ARGUS - Monitoring Agent

ARGUS (Port 8016) is the central monitoring agent that aggregates health data from all agents.

### Health Check All Agents

```bash
curl http://localhost:8016/health/all
```

```json
{
  "status": "healthy",
  "agents": {
    "ATLAS": {"status": "healthy", "port": 8007, "response_time_ms": 12},
    "HEPHAESTUS": {"status": "healthy", "port": 8011, "response_time_ms": 8},
    "AEGIS": {"status": "healthy", "port": 8012, "response_time_ms": 15},
    "CHRONOS": {"status": "healthy", "port": 8010, "response_time_ms": 10},
    "SCHOLAR": {"status": "healthy", "port": 8018, "response_time_ms": 22}
  },
  "healthy_count": 15,
  "unhealthy_count": 0,
  "checked_at": "2026-01-17T12:00:00Z"
}
```

### Get Prometheus Metrics

```bash
curl http://localhost:8016/metrics
```

```
# HELP agent_health_status Agent health status (1=healthy, 0=unhealthy)
# TYPE agent_health_status gauge
agent_health_status{agent="ATLAS"} 1
agent_health_status{agent="HEPHAESTUS"} 1
agent_health_status{agent="AEGIS"} 1

# HELP agent_response_time_ms Agent response time in milliseconds
# TYPE agent_response_time_ms gauge
agent_response_time_ms{agent="ATLAS"} 12
agent_response_time_ms{agent="HEPHAESTUS"} 8

# HELP agent_requests_total Total requests processed
# TYPE agent_requests_total counter
agent_requests_total{agent="SCHOLAR"} 15420
agent_requests_total{agent="CHIRON"} 8520
```

### Cost Monitoring

```bash
curl http://localhost:8016/costs?days=7
```

```json
{
  "period_days": 7,
  "costs_by_agent": [
    {"agent": "SCHOLAR", "total_cost": 52.50},
    {"agent": "CHIRON", "total_cost": 33.60},
    {"agent": "ARIA", "total_cost": 25.80}
  ],
  "total_cost": 111.90
}
```

---

## Health Check Endpoints

Every agent exposes a `/health` endpoint:

### Standard Health Response

```json
{
  "status": "healthy",
  "agent": "ATLAS",
  "version": "2.0",
  "uptime_seconds": 86400,
  "last_activity": "2026-01-17T11:55:00Z"
}
```

### Quick Health Checks

```bash
# Core agents
curl -s http://localhost:8007/health | jq .status  # ATLAS
curl -s http://localhost:8011/health | jq .status  # HEPHAESTUS
curl -s http://localhost:8012/health | jq .status  # AEGIS
curl -s http://localhost:8010/health | jq .status  # CHRONOS
curl -s http://localhost:8099/health | jq .status  # Event Bus

# LLM agents
curl -s http://localhost:8017/health | jq .status  # CHIRON
curl -s http://localhost:8018/health | jq .status  # SCHOLAR
```

### Batch Health Check Script

```bash
#!/bin/bash
# /opt/leveredge/shared/scripts/check-health.sh

AGENTS=(
  "GAIA:8000"
  "ATLAS:8007"
  "HADES:8008"
  "CHRONOS:8010"
  "HEPHAESTUS:8011"
  "AEGIS:8012"
  "ATHENA:8013"
  "HERMES:8014"
  "ALOY:8015"
  "ARGUS:8016"
  "CHIRON:8017"
  "SCHOLAR:8018"
  "SENTINEL:8019"
  "EVENT-BUS:8099"
)

echo "Agent Health Check - $(date)"
echo "================================"

for agent_port in "${AGENTS[@]}"; do
  IFS=':' read -r agent port <<< "$agent_port"
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null)

  if [ "$status" == "200" ]; then
    echo "$agent ($port): HEALTHY"
  else
    echo "$agent ($port): UNHEALTHY (HTTP $status)"
  fi
done
```

---

## Prometheus Configuration

### prometheus.yml

```yaml
global:
  scrape_interval: 30s
  evaluation_interval: 30s

scrape_configs:
  - job_name: 'argus'
    static_configs:
      - targets: ['localhost:8016']
    metrics_path: /metrics

  - job_name: 'agents'
    static_configs:
      - targets:
        - 'localhost:8007'   # ATLAS
        - 'localhost:8008'   # HADES
        - 'localhost:8010'   # CHRONOS
        - 'localhost:8011'   # HEPHAESTUS
        - 'localhost:8012'   # AEGIS
        - 'localhost:8017'   # CHIRON
        - 'localhost:8018'   # SCHOLAR
        - 'localhost:8099'   # Event Bus
    metrics_path: /metrics

  - job_name: 'n8n'
    static_configs:
      - targets:
        - 'localhost:5678'   # PROD n8n
        - 'localhost:5679'   # Control n8n
        - 'localhost:5680'   # DEV n8n
```

---

## Grafana Dashboards

Access at: `grafana.leveredgeai.com`

### Dashboard: Agent Overview

Panels:
- Agent health status (all agents)
- Response time trends
- Request counts
- Error rates

### Dashboard: Cost Tracking

Panels:
- Daily cost by agent
- Cost trend (30 days)
- Top endpoints by cost
- Budget vs actual

### Dashboard: Event Bus

Panels:
- Events per minute
- Events by type
- Delivery success rate
- Subscriber health

---

## Alerting

### HERMES Alert Integration

Alerts are sent via HERMES to Telegram.

### Alert Rules

```yaml
# /opt/leveredge/monitoring/alerts.yml

groups:
  - name: agent_health
    rules:
      - alert: AgentDown
        expr: agent_health_status == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Agent {{ $labels.agent }} is down"

      - alert: AgentSlowResponse
        expr: agent_response_time_ms > 5000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Agent {{ $labels.agent }} responding slowly"

  - name: cost_alerts
    rules:
      - alert: DailyBudgetExceeded
        expr: sum(increase(agent_cost_total[24h])) > 50
        labels:
          severity: warning
        annotations:
          summary: "Daily cost budget exceeded"

      - alert: CostSpike
        expr: rate(agent_cost_total[1h]) > 10
        labels:
          severity: warning
        annotations:
          summary: "Unusual cost spike detected"
```

### Alert Flow

```
Prometheus detects condition
         |
         v
Alertmanager receives alert
         |
         v
HTTP POST to ARGUS /alert
         |
         v
ARGUS publishes to Event Bus
         |
         v
HERMES receives, sends Telegram
```

---

## Logging

### Agent Logs

Agent logs are written to `/tmp/`:

```bash
# View logs
tail -f /tmp/atlas.log
tail -f /tmp/hephaestus.log
tail -f /tmp/scholar.log

# Search logs
grep -i error /tmp/atlas.log
grep -i "500" /tmp/*.log
```

### Docker Logs

```bash
# Control n8n
cd /opt/leveredge/control-plane/n8n && docker compose logs -f

# PROD n8n
cd /opt/leveredge/data-plane/prod/n8n && docker compose logs -f

# Supabase
cd /opt/leveredge/data-plane/prod/supabase && docker compose logs -f supabase-db
```

### Log Aggregation

For production, consider:

- Loki + Promtail for log aggregation
- Grafana for log visualization
- Log retention policies

---

## Systemd Services

Convert agents to systemd for better management:

### Example Service File

```ini
# /etc/systemd/system/atlas.service

[Unit]
Description=ATLAS Orchestration Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/leveredge/control-plane/agents/atlas
ExecStart=/usr/local/bin/python3.11 -m uvicorn atlas:app --host 0.0.0.0 --port 8007
Restart=always
RestartSec=5
Environment="SUPABASE_URL=http://localhost:8000"
Environment="EVENT_BUS_URL=http://localhost:8099"

[Install]
WantedBy=multi-user.target
```

### Managing Services

```bash
# Enable and start
sudo systemctl enable atlas
sudo systemctl start atlas

# Check status
sudo systemctl status atlas

# View logs
sudo journalctl -u atlas -f

# Restart
sudo systemctl restart atlas
```

---

## Troubleshooting Quick Reference

### Agent Not Responding

1. Check if running: `ps aux | grep "uvicorn.*8007"`
2. Check logs: `tail -50 /tmp/atlas.log`
3. Check port: `sudo lsof -i :8007`
4. Restart: See restart commands in OPS-RUNBOOK

### High Response Time

1. Check agent logs for errors
2. Check database connectivity
3. Check external API status
4. Monitor resource usage: `top`, `htop`

### Cost Spike

1. Check ARGUS /costs endpoint
2. Review recent agent_usage_logs
3. Identify expensive endpoints
4. Check for infinite loops or retries

---

## Related Documentation

- [OPS Runbook](troubleshooting.md)
- [Backup & Restore](backup-restore.md)
- [Cost Tracking Architecture](../architecture/cost-tracking.md)
