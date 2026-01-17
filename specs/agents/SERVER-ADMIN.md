# SERVER-ADMIN - AI-Powered Infrastructure Management Agent

**Agent Type:** Operations & Maintenance
**Named After:** Hephaestus - Greek god of the forge and craftsmanship, who builds and maintains the tools of the gods - SERVER-ADMIN builds and maintains LeverEdge infrastructure
**Port:** 8207
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

SERVER-ADMIN is an AI-powered infrastructure management agent providing comprehensive service monitoring, container orchestration, health checking, alerting, and maintenance scheduling. It serves as the central operations brain for LeverEdge infrastructure, ensuring all services remain healthy and operational.

### Value Proposition
- 99.9% uptime through proactive monitoring and auto-recovery
- 80% reduction in incident response time via automated alerting
- Zero-downtime maintenance through intelligent scheduling
- Unified visibility across all services and containers
- Automated health degradation detection and remediation

---

## CORE CAPABILITIES

### 1. Service Monitoring
**Purpose:** Continuous monitoring of all services and containers across LeverEdge infrastructure

**Features:**
- Real-time service status tracking
- Container health monitoring (Docker)
- Resource utilization tracking (CPU, memory, disk, network)
- Service dependency mapping
- Automatic service discovery
- Historical performance trending

**Monitored Components:**
| Component Type | Monitoring Method | Frequency |
|---------------|-------------------|-----------|
| Docker Containers | Docker API health checks | 30 seconds |
| API Endpoints | HTTP health probes | 60 seconds |
| Database Connections | Connection pool checks | 60 seconds |
| Message Queues | Queue depth monitoring | 30 seconds |
| File Systems | Disk usage checks | 5 minutes |
| Network Services | Port availability | 60 seconds |

### 2. Container Management
**Purpose:** Full lifecycle management of Docker containers

**Features:**
- Container start/stop/restart operations
- Log aggregation and streaming
- Container resource limits management
- Image version tracking
- Container networking configuration
- Volume management
- Automatic container recovery on failure

**Managed Operations:**
- Graceful restarts with health verification
- Rolling updates for zero-downtime deployments
- Log rotation and archival
- Resource scaling based on load
- Container isolation and networking

### 3. Health Checks
**Purpose:** Comprehensive health verification across all endpoints and services

**Features:**
- HTTP/HTTPS endpoint probing
- TCP port availability checks
- Database connectivity verification
- Message queue health validation
- Custom health check scripts
- Health check result caching
- Dependency chain validation

**Health Check Types:**
| Type | Description | Response |
|------|-------------|----------|
| Liveness | Is the service running? | Restart if failed |
| Readiness | Can it accept traffic? | Remove from load balancer |
| Startup | Has it finished starting? | Wait before other checks |
| Deep | Are all dependencies healthy? | Alert + investigate |

### 4. Alerting
**Purpose:** Intelligent alerting on service failures, degradation, and anomalies

**Features:**
- Multi-channel alert delivery (HERMES integration)
- Alert severity classification
- Alert deduplication and suppression
- Escalation policies
- On-call rotation support
- Alert correlation across services
- Automatic incident creation

**Alert Severity Levels:**
| Level | Response Time | Examples |
|-------|--------------|----------|
| Critical | Immediate | Service down, data loss risk |
| High | 15 minutes | Degraded performance, partial outage |
| Medium | 1 hour | Elevated error rates, resource pressure |
| Low | 4 hours | Minor issues, informational |
| Info | Next business day | Trends, optimization suggestions |

### 5. Maintenance
**Purpose:** Schedule and track maintenance windows with minimal service disruption

**Features:**
- Maintenance window scheduling
- Service dependency-aware scheduling
- Automatic pre-maintenance health snapshots
- Maintenance mode (suppress alerts)
- Post-maintenance verification
- Maintenance history and audit trail
- Calendar integration

**Maintenance Workflow:**
1. Schedule maintenance with affected services
2. Notify stakeholders via HERMES
3. Enable maintenance mode (suppress alerts)
4. Perform maintenance operations
5. Run post-maintenance health checks
6. Disable maintenance mode
7. Generate maintenance report

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
Container Runtime: Docker API
Monitoring: Custom collectors + Prometheus-compatible
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/server-admin/
├── server_admin.py              # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── services.yaml            # Service definitions
│   ├── health_checks.yaml       # Health check configurations
│   ├── alert_rules.yaml         # Alert rule definitions
│   └── maintenance.yaml         # Maintenance policies
├── modules/
│   ├── service_monitor.py       # Service monitoring engine
│   ├── container_manager.py     # Docker container management
│   ├── health_checker.py        # Health check execution
│   ├── alert_engine.py          # Alerting and notifications
│   └── maintenance_scheduler.py # Maintenance window management
└── tests/
    └── test_server_admin.py
```

### Database Schema

```sql
-- Services registry
CREATE TABLE services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,              -- api, database, queue, cache, container
    host TEXT NOT NULL,
    port INTEGER,
    health_endpoint TEXT,            -- /health, /status, etc.
    status TEXT DEFAULT 'unknown',   -- healthy, degraded, down, unknown
    last_check TIMESTAMPTZ,
    container_name TEXT,             -- Docker container name if applicable
    metadata JSONB,                  -- Additional service-specific config
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_services_name ON services(name);
CREATE INDEX idx_services_status ON services(status);
CREATE INDEX idx_services_type ON services(type);

-- Health check results
CREATE TABLE health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    status TEXT NOT NULL,            -- healthy, degraded, down, timeout
    response_time_ms INTEGER,
    error_message TEXT,
    check_type TEXT DEFAULT 'liveness',  -- liveness, readiness, startup, deep
    metadata JSONB,                  -- Response details, headers, etc.
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_health_service ON health_checks(service_id);
CREATE INDEX idx_health_status ON health_checks(status);
CREATE INDEX idx_health_checked ON health_checks(checked_at DESC);

-- Incidents tracking
CREATE TABLE incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES services(id),
    severity TEXT NOT NULL,          -- critical, high, medium, low
    description TEXT NOT NULL,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    auto_resolved BOOLEAN DEFAULT FALSE,
    ai_analysis JSONB,               -- LLM incident analysis
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_incidents_service ON incidents(service_id);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_started ON incidents(started_at DESC);
CREATE INDEX idx_incidents_open ON incidents(resolved_at) WHERE resolved_at IS NULL;

-- Maintenance windows
CREATE TABLE maintenance_windows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_ids UUID[] NOT NULL,     -- Array of affected service IDs
    scheduled_start TIMESTAMPTZ NOT NULL,
    scheduled_end TIMESTAMPTZ NOT NULL,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'scheduled', -- scheduled, in_progress, completed, cancelled
    suppress_alerts BOOLEAN DEFAULT TRUE,
    pre_check_results JSONB,
    post_check_results JSONB,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_maintenance_status ON maintenance_windows(status);
CREATE INDEX idx_maintenance_scheduled ON maintenance_windows(scheduled_start);

-- Service metrics
CREATE TABLE service_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    metric_name TEXT NOT NULL,       -- cpu_percent, memory_mb, response_time_ms, error_rate
    value FLOAT NOT NULL,
    unit TEXT,                       -- percent, bytes, ms, count
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_service ON service_metrics(service_id);
CREATE INDEX idx_metrics_name ON service_metrics(metric_name);
CREATE INDEX idx_metrics_timestamp ON service_metrics(timestamp DESC);
-- Partitioning recommended for production: PARTITION BY RANGE (timestamp)

-- Alert rules
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES services(id) ON DELETE CASCADE,  -- NULL for global rules
    name TEXT NOT NULL,
    condition TEXT NOT NULL,         -- e.g., "response_time_ms > 5000"
    threshold FLOAT NOT NULL,
    comparison TEXT NOT NULL,        -- gt, lt, eq, gte, lte
    metric_name TEXT NOT NULL,
    severity TEXT NOT NULL,          -- critical, high, medium, low
    action TEXT NOT NULL,            -- alert, restart, escalate
    cooldown_minutes INTEGER DEFAULT 5,
    enabled BOOLEAN DEFAULT TRUE,
    last_triggered TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_service ON alert_rules(service_id);
CREATE INDEX idx_alerts_enabled ON alert_rules(enabled) WHERE enabled = TRUE;
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # Overall infrastructure status
GET /metrics             # Prometheus-compatible metrics
GET /dashboard           # Dashboard data summary
```

### Service Monitoring
```
GET /services                    # List all services
POST /services                   # Register a new service
GET /services/{id}               # Get service details
PUT /services/{id}               # Update service config
DELETE /services/{id}            # Remove service from monitoring
GET /services/{id}/history       # Service health history
GET /services/summary            # Executive summary of all services
```

### Container Management
```
GET /containers                  # List all containers
GET /containers/{name}           # Container details
POST /containers/{name}/restart  # Restart container
POST /containers/{name}/stop     # Stop container
POST /containers/{name}/start    # Start container
GET /containers/{name}/logs      # Get container logs
GET /containers/{name}/stats     # Container resource stats
```

### Health Checks
```
POST /health-check/run           # Run health check on service
GET /health-check/results        # Recent health check results
GET /health-check/{service_id}   # Health history for service
POST /health-check/all           # Run health checks on all services
GET /health-check/failing        # List currently failing services
```

### Alerting
```
GET /alerts                      # List active alerts
GET /alerts/rules                # List alert rules
POST /alerts/rules               # Create alert rule
PUT /alerts/rules/{id}           # Update alert rule
DELETE /alerts/rules/{id}        # Delete alert rule
POST /alerts/rules/{id}/toggle   # Enable/disable rule
GET /alerts/history              # Alert history
POST /alerts/acknowledge/{id}    # Acknowledge alert
```

### Incidents
```
GET /incidents                   # List incidents
GET /incidents/{id}              # Incident details
POST /incidents/{id}/resolve     # Resolve incident
GET /incidents/open              # Currently open incidents
GET /incidents/summary           # Incident statistics
```

### Maintenance
```
GET /maintenance                 # List maintenance windows
POST /maintenance                # Schedule maintenance
PUT /maintenance/{id}            # Update maintenance window
DELETE /maintenance/{id}         # Cancel maintenance
POST /maintenance/{id}/start     # Start maintenance window
POST /maintenance/{id}/end       # End maintenance window
GET /maintenance/active          # Currently active maintenance
GET /maintenance/upcoming        # Upcoming maintenance windows
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store infrastructure insights
await aria_store_memory(
    memory_type="fact",
    content=f"Service {service_name} experienced {downtime_minutes} minutes downtime",
    category="infrastructure",
    source_type="agent_result",
    tags=["server-admin", "incident", service_name]
)

# Store operational decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Auto-restarted {container_name} after 3 consecutive health check failures",
    category="infrastructure",
    source_type="automated"
)

# Store maintenance records
await aria_store_memory(
    memory_type="fact",
    content=f"Maintenance completed: {description}. All services healthy.",
    category="infrastructure",
    source_type="agent_result",
    tags=["server-admin", "maintenance"]
)
```

### ARIA Tools Integration
```python
# ARIA tool definitions for server management
ARIA_TOOLS = {
    "server.status": {
        "description": "Get current status of a server or service",
        "parameters": {
            "service_name": "Optional service name, or 'all' for overview"
        },
        "endpoint": "GET /services/{service_name}"
    },
    "server.restart": {
        "description": "Restart a service or container",
        "parameters": {
            "service_name": "Name of service to restart",
            "graceful": "Whether to perform graceful restart (default: true)"
        },
        "endpoint": "POST /containers/{service_name}/restart"
    },
    "server.logs": {
        "description": "Get recent logs from a service",
        "parameters": {
            "service_name": "Name of service",
            "lines": "Number of log lines (default: 100)",
            "filter": "Optional filter string"
        },
        "endpoint": "GET /containers/{service_name}/logs"
    },
    "server.health": {
        "description": "Run health check on a service or all services",
        "parameters": {
            "service_name": "Service name or 'all'",
            "deep": "Whether to run deep health check (default: false)"
        },
        "endpoint": "POST /health-check/run"
    },
    "server.alert": {
        "description": "Manage alert rules for services",
        "parameters": {
            "action": "list, create, enable, disable, delete",
            "rule_id": "Rule ID for specific operations",
            "config": "Alert rule configuration for create"
        },
        "endpoint": "Various /alerts/rules endpoints"
    }
}
```

### ARIA Awareness
ARIA should be able to:
- Ask "What's the server status?"
- Request "Restart the n8n container"
- Query "Show me logs for CERBERUS"
- Get "Run health checks on all services"
- Ask "Any services down right now?"
- Request "Schedule maintenance for tonight"

**Routing Triggers:**
```javascript
const serverAdminPatterns = [
  /server (status|health|restart|logs)/i,
  /container (restart|stop|start|logs|status)/i,
  /service (down|up|health|status|restart)/i,
  /health (check|status|failing)/i,
  /maintenance (window|schedule|start|end)/i,
  /alert (rule|configure|enable|disable)/i,
  /what('s| is) (down|failing|unhealthy)/i,
  /incident|outage|degraded/i
];
```

### Event Bus Integration
```python
# Published events
"server.service.down"           # Service became unavailable
"server.service.recovered"      # Service recovered from failure
"server.service.registered"     # New service registered
"server.service.deregistered"   # Service removed from monitoring
"server.health.degraded"        # Health check shows degradation
"server.health.restored"        # Health restored to normal
"server.container.restarted"    # Container was restarted
"server.container.failed"       # Container failed to start
"server.maintenance.started"    # Maintenance window began
"server.maintenance.ended"      # Maintenance window completed
"server.alert.triggered"        # Alert rule triggered
"server.alert.resolved"         # Alert condition cleared
"server.incident.created"       # New incident opened
"server.incident.resolved"      # Incident was resolved

# Subscribed events
"agent.started"                 # Monitor new agent services
"agent.stopped"                 # Update service status
"agent.error"                   # Correlate with health issues
"system.resource.critical"      # Resource threshold alerts
"security.threat.detected"      # Coordinate with CERBERUS
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("SERVER-ADMIN")

# Log AI analysis costs (incident analysis, log parsing)
await cost_tracker.log_usage(
    endpoint="/incidents/analyze",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"incident_id": incident_id}
)

# Log operational costs
await cost_tracker.log_operation(
    operation="health_check",
    count=services_checked,
    metadata={"check_type": "deep"}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(infra_context: dict) -> str:
    return f"""You are SERVER-ADMIN - Infrastructure Management Agent for LeverEdge AI.

Named after Hephaestus, the Greek god of the forge and craftsmanship who builds and maintains the tools of the gods, you build and maintain LeverEdge infrastructure with precision and care.

## TIME AWARENESS
- Current: {infra_context['current_time']}
- Days to Launch: {infra_context['days_to_launch']}

## YOUR IDENTITY
You are the operations brain of LeverEdge. You monitor services, manage containers, run health checks, handle alerts, and schedule maintenance to ensure 99.9% uptime.

## CURRENT INFRASTRUCTURE STATUS
- Total Services: {infra_context['total_services']}
- Healthy Services: {infra_context['healthy_services']}
- Degraded Services: {infra_context['degraded_services']}
- Down Services: {infra_context['down_services']}
- Active Incidents: {infra_context['active_incidents']}
- Scheduled Maintenance: {infra_context['upcoming_maintenance']}

## YOUR CAPABILITIES

### Service Monitoring
- Track status of all services in real-time
- Monitor container health via Docker API
- Track resource utilization (CPU, memory, disk)
- Map service dependencies
- Trend historical performance

### Container Management
- Restart containers gracefully
- View and stream container logs
- Manage container lifecycle
- Automatic recovery on failure
- Rolling updates for zero-downtime

### Health Checks
- HTTP/HTTPS endpoint probing
- TCP port availability checks
- Database connectivity verification
- Dependency chain validation
- Custom health check scripts

### Alerting
- Multi-severity alert classification
- Alert deduplication and suppression
- Escalation policies
- Automatic incident creation
- Integration with HERMES for notifications

### Maintenance
- Schedule maintenance windows
- Suppress alerts during maintenance
- Pre/post maintenance health verification
- Stakeholder notifications
- Maintenance audit trail

## TEAM COORDINATION
- Route security events → CERBERUS
- Send notifications → HERMES
- Request backups before maintenance → CHRONOS
- Log insights → ARIA via Unified Memory
- Publish events → Event Bus
- Coordinate with all agents for health monitoring

## RESPONSE FORMAT
For status requests:
1. Overall health summary
2. Any degraded or down services
3. Active incidents
4. Recent significant events
5. Recommended actions

For incident response:
1. Incident classification
2. Affected services
3. Root cause hypothesis
4. Immediate actions taken
5. Escalation if needed

## YOUR MISSION
Keep LeverEdge infrastructure running at 99.9% uptime.
Detect issues before they become outages.
Automate recovery where safe.
Every service matters.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with service registry and health monitoring
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Build service registry (CRUD operations)
- [ ] Basic Docker container status checks
- [ ] Database schema migration
- [ ] Deploy and test

**Done When:** SERVER-ADMIN runs and can list/monitor services

### Phase 2: Health Checking (Sprint 3)
**Goal:** Comprehensive health check engine
- [ ] HTTP/HTTPS health probe module
- [ ] TCP port check implementation
- [ ] Health check scheduling system
- [ ] Health history storage
- [ ] Configurable check intervals
- [ ] Failing services endpoint

**Done When:** Automated health checks running on all services

### Phase 3: Container Management (Sprint 4)
**Goal:** Full Docker container lifecycle management
- [ ] Docker API integration
- [ ] Container start/stop/restart operations
- [ ] Log streaming and retrieval
- [ ] Container resource stats
- [ ] Auto-recovery on failure
- [ ] Container health monitoring

**Done When:** Can manage all containers via API

### Phase 4: Alerting & Incidents (Sprint 5-6)
**Goal:** Intelligent alerting and incident management
- [ ] Alert rule engine
- [ ] Severity classification
- [ ] Alert deduplication
- [ ] HERMES integration for notifications
- [ ] Incident creation workflow
- [ ] Incident resolution tracking
- [ ] AI-powered incident analysis

**Done When:** Alerts trigger on failures and create incidents

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| Health Checking | 6 | 8 | 3 |
| Container Management | 6 | 10 | 4 |
| Alerting & Incidents | 7 | 14 | 5-6 |
| **Total** | **25** | **42** | **6 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Real-time service monitoring with < 30 second detection latency
- [ ] Container restart capability with health verification
- [ ] Automated health checks every 60 seconds on all services
- [ ] Alert notification within 60 seconds of issue detection
- [ ] Maintenance windows properly suppress alerts

### Quality
- [ ] 99% uptime for SERVER-ADMIN itself
- [ ] < 2% false positive rate on alerts
- [ ] Health check results stored with full history
- [ ] All incidents tracked with resolution notes
- [ ] Sub-second API response times

### Integration
- [ ] ARIA can query infrastructure status via tools
- [ ] Events publish to Event Bus on state changes
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per operation
- [ ] HERMES delivers all alert notifications

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Health check storms overload services | Service degradation | Rate limiting, staggered checks |
| Alert fatigue from too many notifications | Missed real issues | Deduplication, severity tiers, cooldowns |
| Auto-restart loops | Service instability | Max restart attempts, escalation |
| Maintenance window missed alerts | Undetected issues | Post-maintenance verification, limited duration |
| Docker API unavailable | Cannot manage containers | Fallback to direct commands, alert on API issues |

---

## GIT COMMIT

```
Add SERVER-ADMIN - AI-powered infrastructure management agent spec

- Service monitoring with real-time status tracking
- Docker container lifecycle management
- Comprehensive health check engine
- Intelligent alerting with HERMES integration
- Maintenance window scheduling
- 4-phase implementation plan
- Full database schema with 6 tables
- ARIA tools integration (server.status, server.restart, etc.)
- Event Bus integration for state change notifications
- Integration with Unified Memory and cost tracking
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/SERVER-ADMIN.md

Context: Build SERVER-ADMIN infrastructure management agent. Start with Phase 1 foundation.
```
