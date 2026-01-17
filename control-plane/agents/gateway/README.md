# API Gateway

Rate limiter and API gateway for all external API calls in the LeverEdge system.

**Port:** 8070

## Overview

The API Gateway provides:
- **Rate Limiting**: Token bucket algorithm for TPM (tokens per minute) and RPM (requests per minute)
- **Service Support**: OpenAI (10K TPM default), Anthropic (40K TPM), Google (32K TPM)
- **Per-Agent Quotas**: Each agent limited to 20% of daily allocation by default
- **Request Queuing**: Automatic queuing when approaching rate limits
- **Cost Tracking**: Real-time cost calculation and usage statistics

## Endpoints

### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check with queue status |
| `/limits` | GET | Current rate limit status for all services |
| `/limits/{service}` | GET | Detailed limits for specific service (openai, anthropic, google) |
| `/stats` | GET | Usage statistics (requests, tokens, costs) |
| `/stats/agent/{agent_id}` | GET | Statistics for specific agent |
| `/queue/{service}` | GET | Queue status for a service |

### Request Proxying

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/request` | POST | Proxy a request through the gateway |
| `/reset/daily` | POST | Manually reset daily counters (admin) |

## Usage

### Proxying a Request

```python
import httpx

response = await httpx.post(
    "http://gateway:8070/request",
    json={
        "service": "openai",
        "endpoint": "/v1/chat/completions",
        "method": "POST",
        "headers": {
            "Authorization": "Bearer sk-...",
            "Content-Type": "application/json"
        },
        "body": {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Hello"}]
        },
        "agent_id": "chiron",
        "estimated_tokens": 500,
        "priority": 5
    }
)

result = response.json()
# {
#     "success": true,
#     "status_code": 200,
#     "data": {...},
#     "tokens_used": 450,
#     "cost": 0.001125,
#     "queue_time_ms": 0,
#     "request_time_ms": 1234
# }
```

### Checking Limits

```python
# All services
limits = await httpx.get("http://gateway:8070/limits")

# Specific service
openai_limits = await httpx.get("http://gateway:8070/limits/openai")
# {
#     "service": "openai",
#     "limits": {
#         "tpm_available": 8500.5,
#         "tpm_limit": 10000,
#         "rpm_available": 495.0,
#         "rpm_limit": 500,
#         "daily_tokens_used": 15000,
#         "daily_limit": 1000000,
#         "daily_percent_used": 1.5,
#         "queue_size": 0
#     },
#     "agent_usage": {
#         "chiron": {"tokens_today": 5000, "requests_today": 10, "cost_today": 0.05}
#     }
# }
```

## Configuration

Environment variables for customization:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_TPM_LIMIT` | 10000 | OpenAI tokens per minute |
| `OPENAI_RPM_LIMIT` | 500 | OpenAI requests per minute |
| `OPENAI_DAILY_LIMIT` | 1000000 | OpenAI daily token limit |
| `ANTHROPIC_TPM_LIMIT` | 40000 | Anthropic tokens per minute |
| `ANTHROPIC_RPM_LIMIT` | 1000 | Anthropic requests per minute |
| `ANTHROPIC_DAILY_LIMIT` | 2000000 | Anthropic daily token limit |
| `GOOGLE_TPM_LIMIT` | 32000 | Google tokens per minute |
| `GOOGLE_RPM_LIMIT` | 360 | Google requests per minute |
| `GOOGLE_DAILY_LIMIT` | 1500000 | Google daily token limit |
| `AGENT_QUOTA_PERCENT` | 20 | Max % of daily limit per agent |
| `MAX_QUEUE_SIZE` | 100 | Maximum queued requests per service |
| `QUEUE_TIMEOUT` | 30 | Queue timeout in seconds |
| `EVENT_BUS_URL` | http://event-bus:8099 | Event bus for logging |

## Rate Limiting Algorithm

The gateway uses a **token bucket** algorithm:
1. Each service has TPM and RPM buckets
2. Buckets refill continuously at the configured rate
3. Requests consume tokens from both buckets
4. When buckets are depleted, requests are queued
5. Queued requests are processed FIFO with priority support

## Cost Tracking

Costs are calculated in real-time using current pricing:

| Service | Model | Input (per 1M) | Output (per 1M) |
|---------|-------|----------------|-----------------|
| OpenAI | gpt-4o | $2.50 | $10.00 |
| OpenAI | gpt-4o-mini | $0.15 | $0.60 |
| Anthropic | claude-sonnet | $3.00 | $15.00 |
| Anthropic | claude-opus | $15.00 | $75.00 |
| Anthropic | claude-haiku | $0.25 | $1.25 |
| Google | gemini-1.5-pro | $1.25 | $5.00 |
| Google | gemini-1.5-flash | $0.075 | $0.30 |

## Running

### Standalone

```bash
cd /opt/leveredge/control-plane/agents/gateway
pip install -r requirements.txt
python gateway.py
```

### Docker

```bash
docker build -t gateway .
docker run -p 8070:8070 gateway
```

## Integration with Other Agents

Agents should route ALL external LLM API calls through this gateway:

```python
# Instead of direct API call:
# response = await anthropic.messages.create(...)

# Use the gateway:
gateway_response = await httpx.post(
    "http://gateway:8070/request",
    json={
        "service": "anthropic",
        "endpoint": "/v1/messages",
        "headers": {"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        "body": {...},
        "agent_id": "my-agent",
        "estimated_tokens": 2000
    }
)
```

## Data Storage

All data is stored in memory. For persistence:
- Stats are logged to the event bus
- Future enhancement: Redis integration for distributed state
- Daily counters auto-reset at midnight UTC

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 408 | Request timed out in queue |
| 429 | Rate limit or quota exceeded |
| 500 | Upstream API error |
| 503 | Gateway not initialized or queue full |
