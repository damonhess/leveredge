# Cost Tracking Architecture

LeverEdge implements universal cost tracking across all LLM-powered agents to monitor and optimize AI spending.

## Overview

```
+------------------------------------------------------------------+
|                     COST TRACKING FLOW                            |
|                                                                   |
|  Agent (SCHOLAR, CHIRON, etc.)                                   |
|      |                                                            |
|      | LLM Call                                                   |
|      v                                                            |
|  +------------------+                                             |
|  | CostTracker      |                                             |
|  | Module           |                                             |
|  +--------+---------+                                             |
|           |                                                       |
|           +------------------------+                              |
|           |                        |                              |
|           v                        v                              |
|  +------------------+     +------------------+                    |
|  | Supabase         |     | Event Bus        |                    |
|  | agent_usage_logs |     | agent_usage      |                    |
|  +------------------+     +------------------+                    |
|           |                        |                              |
|           v                        v                              |
|  +------------------+     +------------------+                    |
|  | ARGUS Dashboard  |     | ALOY Analysis    |                    |
|  | /costs endpoint  |     | Anomaly detect   |                    |
|  +------------------+     +------------------+                    |
|                                                                   |
+------------------------------------------------------------------+
```

## Why Track Costs?

1. **Visibility**: Know exactly where money is spent
2. **Optimization**: Identify expensive operations to optimize
3. **Budgeting**: Set alerts and limits
4. **Accountability**: Track usage by agent, endpoint, user
5. **Compliance**: Audit trail for financial reporting

---

## Cost Model

### LLM Pricing (as of January 2026)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| claude-sonnet-4-20250514 | $3.00 | $15.00 |
| claude-opus-4-20250514 | $15.00 | $75.00 |
| claude-haiku-4-20250514 | $0.25 | $1.25 |
| gpt-4o | $2.50 | $10.00 |
| gpt-4o-mini | $0.15 | $0.60 |
| gemini-1.5-pro | $1.25 | $5.00 |

### Feature Costs (Estimated)

| Feature | Cost per Use |
|---------|-------------|
| Web search | $0.01 |
| PDF processing | $0.02/page |
| Image processing | $0.01 |

---

## Database Schema

```sql
-- Agent usage logs table
CREATE TABLE IF NOT EXISTS agent_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    web_searches INTEGER NOT NULL DEFAULT 0,
    other_features JSONB DEFAULT '{}',
    input_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    output_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    feature_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    total_cost DECIMAL(10, 6) NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_usage_agent ON agent_usage_logs(agent);
CREATE INDEX idx_usage_timestamp ON agent_usage_logs(timestamp);
CREATE INDEX idx_usage_agent_timestamp ON agent_usage_logs(agent, timestamp);

-- Summary view
CREATE OR REPLACE VIEW agent_cost_summary AS
SELECT
    agent,
    DATE(timestamp) as date,
    COUNT(*) as request_count,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(web_searches) as total_web_searches,
    ROUND(SUM(total_cost)::numeric, 4) as total_cost
FROM agent_usage_logs
GROUP BY agent, DATE(timestamp)
ORDER BY date DESC, agent;
```

---

## Shared Cost Tracker Module

Location: `/opt/leveredge/control-plane/shared/cost_tracker.py`

```python
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class UsageRecord:
    agent: str
    endpoint: str
    model: str
    input_tokens: int
    output_tokens: int
    web_searches: int = 0
    other_features: Dict[str, int] = None

    @property
    def input_cost(self) -> float:
        pricing = PRICING.get(self.model, PRICING["claude-sonnet"])
        return (self.input_tokens / 1_000_000) * pricing["input"]

    @property
    def output_cost(self) -> float:
        pricing = PRICING.get(self.model, PRICING["claude-sonnet"])
        return (self.output_tokens / 1_000_000) * pricing["output"]

    @property
    def total_cost(self) -> float:
        return self.input_cost + self.output_cost + self.feature_cost


class CostTracker:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name

    async def log_usage(
        self,
        endpoint: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        web_searches: int = 0,
        metadata: Dict[str, Any] = None
    ) -> dict:
        # Calculate costs
        record = UsageRecord(...)

        # Log to database
        await self._log_to_database(log_entry)

        # Publish to Event Bus
        await self._log_to_event_bus(log_entry)

        return log_entry
```

---

## Agent Integration

### Example: SCHOLAR Integration

```python
import sys
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

# Initialize tracker
cost_tracker = CostTracker("SCHOLAR")

async def call_llm_with_search(messages, enable_search=True):
    # Make LLM call
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        messages=messages,
        tools=[{"type": "web_search_20250305"}] if enable_search else None
    )

    # Count web searches
    web_search_count = cost_tracker.count_web_searches(response)

    # Log usage
    await log_llm_usage(
        agent="SCHOLAR",
        endpoint="deep-research",
        model="claude-sonnet-4-20250514",
        response=response,
        web_searches=web_search_count
    )

    return response
```

---

## Monitoring Endpoints

### ARGUS Cost Dashboard

```http
GET /costs?days=30
```

```json
{
  "period_days": 30,
  "costs_by_agent": [
    {
      "agent": "SCHOLAR",
      "request_count": 1250,
      "total_input_tokens": 5000000,
      "total_output_tokens": 2500000,
      "total_web_searches": 850,
      "total_cost": 52.50
    },
    {
      "agent": "CHIRON",
      "request_count": 800,
      "total_input_tokens": 3200000,
      "total_output_tokens": 1600000,
      "total_web_searches": 0,
      "total_cost": 33.60
    }
  ],
  "total_cost": 86.10,
  "generated_at": "2026-01-17T12:00:00Z"
}
```

### Daily Cost Trend

```http
GET /costs/daily?days=7
```

```json
{
  "daily_costs": [
    {"date": "2026-01-17", "total_cost": 12.50, "request_count": 320},
    {"date": "2026-01-16", "total_cost": 15.20, "request_count": 410},
    {"date": "2026-01-15", "total_cost": 8.90, "request_count": 220}
  ],
  "generated_at": "2026-01-17T12:00:00Z"
}
```

---

## SQL Functions

### Get Agent Costs

```sql
CREATE OR REPLACE FUNCTION get_agent_costs(
    start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    agent TEXT,
    request_count BIGINT,
    total_input_tokens BIGINT,
    total_output_tokens BIGINT,
    total_web_searches BIGINT,
    total_cost DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.agent,
        COUNT(*)::BIGINT,
        SUM(l.input_tokens)::BIGINT,
        SUM(l.output_tokens)::BIGINT,
        SUM(l.web_searches)::BIGINT,
        ROUND(SUM(l.total_cost)::numeric, 4)::DECIMAL
    FROM agent_usage_logs l
    WHERE l.timestamp BETWEEN start_date AND end_date
    GROUP BY l.agent
    ORDER BY SUM(l.total_cost) DESC;
END;
$$ LANGUAGE plpgsql;
```

### Get Daily Costs

```sql
CREATE OR REPLACE FUNCTION get_daily_costs(days INTEGER DEFAULT 30)
RETURNS TABLE (
    date DATE,
    total_cost DECIMAL,
    request_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        DATE(timestamp),
        ROUND(SUM(total_cost)::numeric, 4)::DECIMAL,
        COUNT(*)::BIGINT
    FROM agent_usage_logs
    WHERE timestamp > NOW() - (days || ' days')::INTERVAL
    GROUP BY DATE(timestamp)
    ORDER BY DATE(timestamp) DESC;
END;
$$ LANGUAGE plpgsql;
```

---

## Alerting

### Budget Alerts

Configure alerts in ARGUS:

```yaml
cost_alerts:
  daily_budget:
    threshold: 50.00
    action: notify_hermes
    priority: high

  weekly_budget:
    threshold: 300.00
    action: notify_hermes
    priority: critical

  agent_anomaly:
    threshold: 3x_average
    action: notify_hermes
    priority: high
```

### Alert Flow

```
agent_usage event
      |
      v
ARGUS monitors
      |
      | (threshold exceeded)
      v
Event Bus (alert_triggered)
      |
      v
HERMES receives
      |
      v
Send Telegram: "Daily budget exceeded: $52.30 / $50.00"
```

---

## Optimization Strategies

### 1. Model Selection

Use appropriate models for tasks:

| Task | Recommended Model | Cost/1K tokens |
|------|-------------------|----------------|
| Simple queries | claude-haiku | $0.0015 |
| Research | claude-sonnet | $0.018 |
| Complex analysis | claude-opus | $0.090 |

### 2. Caching

Cache repeated queries:

```python
@cache(ttl=3600)  # 1 hour
async def cached_research(query: str):
    return await scholar.research(query)
```

### 3. Prompt Optimization

- Keep prompts concise
- Use structured outputs
- Batch similar requests

### 4. Web Search Limits

Limit web searches per request:

```python
max_searches_per_request = 5
```

---

## Reporting

### Monthly Cost Report

```sql
SELECT
    agent,
    COUNT(*) as requests,
    ROUND(SUM(total_cost)::numeric, 2) as cost,
    ROUND(AVG(total_cost)::numeric, 4) as avg_cost_per_request
FROM agent_usage_logs
WHERE timestamp >= DATE_TRUNC('month', NOW())
GROUP BY agent
ORDER BY cost DESC;
```

### Cost by Endpoint

```sql
SELECT
    agent,
    endpoint,
    COUNT(*) as calls,
    ROUND(SUM(total_cost)::numeric, 2) as total_cost
FROM agent_usage_logs
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY agent, endpoint
ORDER BY total_cost DESC
LIMIT 20;
```

---

## Related Documentation

- [Architecture Overview](overview.md)
- [ARGUS Monitoring](../operations/monitoring.md)
- [API Reference](../api/atlas.md)
