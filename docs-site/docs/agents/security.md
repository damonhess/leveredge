# Security Fleet

The Security Fleet provides authentication, authorization, and network security for the LeverEdge infrastructure.

## Fleet Overview

| Agent | Port | Purpose | Type |
|-------|------|---------|------|
| CERBERUS | 8020 | Security Gateway | FastAPI |
| PORT-MANAGER | 8021 | Port allocation and management | FastAPI |

---

## CERBERUS - Security Gateway

**Port:** 8020 | **Type:** Executor

CERBERUS guards the gates of LeverEdge infrastructure, handling authentication, authorization, and security policy enforcement.

### Capabilities

- Authentication and authorization
- Rate limiting and abuse prevention
- Security policy enforcement
- Access control decisions
- JWT token validation
- API key management
- IP whitelist/blacklist
- Request filtering

### Security Features

#### Rate Limiting

| Tier | Requests/minute | Burst |
|------|-----------------|-------|
| Standard | 60 | 10 |
| Premium | 300 | 50 |
| Internal | Unlimited | - |

#### Authentication Methods

- JWT Bearer tokens
- API keys (header-based)
- Basic authentication (internal)
- mTLS (service-to-service)

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/auth/validate` | POST | Validate token/key |
| `/auth/refresh` | POST | Refresh token |
| `/rate-limit/status` | GET | Current rate limit status |
| `/access/check` | POST | Check access permissions |
| `/policy/evaluate` | POST | Evaluate security policy |

### Example Usage

```bash
# Validate token
curl -X POST http://localhost:8020/auth/validate \
  -H "Content-Type: application/json" \
  -d '{
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "required_scopes": ["read", "write"]
  }'

# Check rate limit status
curl http://localhost:8020/rate-limit/status \
  -H "X-API-Key: your-api-key"
```

### Security Policies

```yaml
policies:
  # Block requests without authentication
  require_auth:
    match: "/api/*"
    require: ["valid_token"]

  # Rate limit external requests
  rate_limit_external:
    match: "/api/*"
    source: "external"
    limit: 60
    window: "1m"

  # Allow internal traffic
  allow_internal:
    match: "*"
    source: ["10.0.0.0/8", "172.16.0.0/12"]
    allow: true
```

### Integration with Other Agents

CERBERUS integrates with:

- **AEGIS**: Credential validation
- **ALOY**: Security audit logging
- **HERMES**: Security alert notifications
- **Event Bus**: Security event publishing

---

## PORT-MANAGER - Network Manager

**Port:** 8021 | **Type:** Executor

PORT-MANAGER handles port allocation, service discovery, and network health monitoring.

### Capabilities

- Port allocation and tracking
- Service discovery
- Network health monitoring
- Port conflict resolution
- Service registration
- DNS-like service lookup

### Port Registry

LeverEdge uses a structured port allocation scheme:

| Range | Purpose |
|-------|---------|
| 5678-5680 | n8n instances |
| 8000-8099 | Core infrastructure agents |
| 8020-8029 | Security fleet |
| 8030-8039 | Creative fleet |
| 8100-8109 | Personal fleet |
| 8200-8209 | Business fleet |

### Current Port Map

```
Core Infrastructure (8000-8099):
  8000: GAIA (Emergency rebuild)
  8007: ATLAS (Orchestration)
  8008: HADES (Rollback)
  8010: CHRONOS (Backup)
  8011: HEPHAESTUS (Builder/MCP)
  8012: AEGIS (Credentials)
  8013: ATHENA (Documentation)
  8014: HERMES (Notifications)
  8015: ALOY (Audit)
  8016: ARGUS (Monitoring)
  8017: CHIRON (Business mentor)
  8018: SCHOLAR (Research)
  8019: SENTINEL (Router)
  8099: Event Bus

Security Fleet (8020-8021):
  8020: CERBERUS
  8021: PORT-MANAGER

Creative Fleet (8030-8034):
  8030: MUSE
  8031: CALLIOPE
  8032: THALIA
  8033: ERATO
  8034: CLIO

Personal Fleet (8100-8110):
  8110: GYM-COACH (Note: 8110 due to port conflict)
  8101: NUTRITIONIST
  8102: MEAL-PLANNER
  8103: ACADEMIC-GUIDE
  8104: EROS

Business Fleet (8200-8209):
  8200: HERACLES
  8201: LIBRARIAN
  8202: DAEDALUS
  8203: THEMIS
  8204: MENTOR
  8205: PLUTUS
  8206: PROCUREMENT
  8207: HEPHAESTUS-SERVER
  8208: ATLAS-INFRA
  8209: IRIS
```

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/ports` | GET | List all port allocations |
| `/ports/allocate` | POST | Allocate new port |
| `/ports/release` | POST | Release port |
| `/services` | GET | List registered services |
| `/services/register` | POST | Register service |
| `/services/lookup` | GET | Lookup service by name |
| `/conflicts` | GET | Check for port conflicts |
| `/network/health` | GET | Network health status |

### Example Usage

```bash
# List all ports
curl http://localhost:8021/ports

# Allocate new port
curl -X POST http://localhost:8021/ports/allocate \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "new-agent",
    "preferred_port": 8040,
    "fleet": "custom"
  }'

# Check for conflicts
curl http://localhost:8021/conflicts

# Lookup service
curl "http://localhost:8021/services/lookup?name=ATLAS"
```

### Service Registration

When a new agent starts, it should register with PORT-MANAGER:

```python
import httpx

async def register_service():
    async with httpx.AsyncClient() as client:
        await client.post(
            "http://localhost:8021/services/register",
            json={
                "name": "MY-AGENT",
                "port": 8040,
                "health_endpoint": "/health",
                "fleet": "custom",
                "metadata": {
                    "version": "1.0.0",
                    "type": "FastAPI"
                }
            }
        )
```

### Network Health Monitoring

PORT-MANAGER periodically checks health of all registered services:

```yaml
health_check:
  interval: 30s
  timeout: 5s
  failure_threshold: 3

alerts:
  service_down:
    channel: hermes
    priority: high
  port_conflict:
    channel: hermes
    priority: critical
```

---

## Security Best Practices

### Authentication Flow

```
Client Request
      |
      v
+------------+
|  CERBERUS  |  <-- Validate token/key
+------------+
      |
      | (if valid)
      v
+------------+
|   Agent    |  <-- Process request
+------------+
      |
      v
+------------+
|   ALOY     |  <-- Log access
+------------+
```

### Network Isolation

- Control plane agents communicate on `control-plane-net`
- Data plane services use `data-plane-net`
- External access only through Caddy reverse proxy
- Internal agent communication uses hostname resolution

### Credential Security

1. **Never hardcode credentials** - Use AEGIS
2. **Rotate regularly** - AEGIS V2 auto-rotation
3. **Encrypt at rest** - AES-256 encryption
4. **Audit all access** - Full logging to ALOY

### Incident Response

1. CERBERUS detects anomaly
2. HERMES sends alert
3. ALOY logs incident details
4. HADES ready for rollback if needed
