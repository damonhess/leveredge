# PORT MANAGER - Port Allocation & Registry Agent

**Agent Type:** Security & Operations
**Named After:** Harbor Master - managing the ports where all traffic flows
**Port:** 8021
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

PORT MANAGER is a utility agent that maintains a central registry of all port allocations across LeverEdge infrastructure, detects conflicts, manages dynamic port assignment, and ensures no service collisions. Essential for a growing agent ecosystem where port management complexity increases exponentially.

### Value Proposition
- Prevent service startup failures due to port conflicts
- Single source of truth for port allocations
- Automatic conflict detection before deployment
- Dynamic port assignment for new services
- Documentation auto-generation for infrastructure

---

## CORE CAPABILITIES

### 1. Port Registry
**Purpose:** Central database of all port allocations

**Features:**
- Complete port inventory (1-65535 tracking)
- Service-to-port mapping
- Environment separation (DEV/PROD)
- Reserved ranges for agent categories
- Historical allocation tracking

**Port Allocation Scheme:**
| Range | Purpose | Examples |
|-------|---------|----------|
| 5678-5699 | n8n instances | 5678 PROD, 5680 DEV |
| 8000-8019 | Core infrastructure | Supabase, GAIA, CHRONOS |
| 8020-8049 | Control plane agents | CERBERUS (8020), etc. |
| 8050-8079 | Data plane services | ARIA, etc. |
| 8080-8099 | Integration services | Event Bus (8099) |
| 8100-8199 | Personal life agents | GYM COACH, etc. |
| 8200-8299 | Business agents | PROJECT MANAGER, etc. |
| 8300-8399 | Client deployments | Reserved |
| 3000-3999 | Development/testing | Temporary allocations |

### 2. Conflict Detection
**Purpose:** Prevent port collisions before they cause outages

**Features:**
- Pre-deployment port scan
- Docker compose validation
- Real-time listening port detection
- Conflict alert with resolution suggestions
- "What-if" analysis for new deployments

### 3. Dynamic Allocation
**Purpose:** Automatically assign ports for new services

**Features:**
- Request port from category range
- Guarantee no conflicts
- Reservation system (hold port for future use)
- Expiring reservations for temp services
- Bulk allocation for multi-container deployments

### 4. Health Monitoring
**Purpose:** Verify services are actually running on assigned ports

**Features:**
- Periodic port health checks
- Zombie port detection (assigned but not listening)
- Orphan port detection (listening but not registered)
- Service crash detection via port monitoring
- Integration with ARGUS for metrics

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Scanning: Socket operations, nmap integration
Container: Docker (lightweight)
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/port-manager/
├── port_manager.py          # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── modules/
│   ├── registry.py          # Port registration logic
│   ├── scanner.py           # Port scanning utilities
│   ├── allocator.py         # Dynamic port allocation
│   └── health_checker.py    # Port health monitoring
└── tests/
    └── test_port_manager.py
```

### Database Schema

```sql
-- Port registry
CREATE TABLE port_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    port INTEGER UNIQUE NOT NULL,
    service_name TEXT NOT NULL,
    agent_name TEXT,                 -- Which agent uses this
    environment TEXT NOT NULL,       -- dev, prod, test
    category TEXT NOT NULL,          -- infrastructure, control, data, personal, business
    protocol TEXT DEFAULT 'tcp',     -- tcp, udp, both
    description TEXT,
    status TEXT DEFAULT 'active',    -- active, reserved, deprecated
    container_name TEXT,             -- Docker container name
    host TEXT DEFAULT 'localhost',   -- For remote services
    allocated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,          -- For temporary allocations
    last_health_check TIMESTAMPTZ,
    health_status TEXT DEFAULT 'unknown',  -- healthy, unhealthy, unknown
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_ports_port ON port_registry(port);
CREATE INDEX idx_ports_service ON port_registry(service_name);
CREATE INDEX idx_ports_agent ON port_registry(agent_name);
CREATE INDEX idx_ports_env ON port_registry(environment);
CREATE INDEX idx_ports_status ON port_registry(status);

-- Port allocation history
CREATE TABLE port_allocation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    port INTEGER NOT NULL,
    action TEXT NOT NULL,            -- allocated, released, reserved, conflict_detected
    previous_service TEXT,
    new_service TEXT,
    reason TEXT,
    performed_by TEXT,               -- agent or user
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_port_history_port ON port_allocation_history(port);
CREATE INDEX idx_port_history_created ON port_allocation_history(created_at DESC);

-- Port ranges configuration
CREATE TABLE port_ranges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT UNIQUE NOT NULL,
    start_port INTEGER NOT NULL,
    end_port INTEGER NOT NULL,
    description TEXT,
    auto_allocate BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health
GET /status              # Port allocation overview
GET /metrics             # Prometheus metrics
```

### Port Registry
```
GET /ports               # List all registered ports
GET /ports/{port}        # Get port details
POST /ports/register     # Register new port allocation
PUT /ports/{port}        # Update port registration
DELETE /ports/{port}     # Release port
GET /ports/service/{name} # Find port by service name
GET /ports/agent/{name}  # List ports for agent
GET /ports/available/{category}  # List available ports in range
```

### Conflict Detection
```
POST /check              # Check if port(s) available
POST /scan               # Scan system for listening ports
GET /conflicts           # List detected conflicts
POST /validate/compose   # Validate docker-compose file
```

### Dynamic Allocation
```
POST /allocate           # Request port from category
POST /reserve            # Reserve port for future use
DELETE /reserve/{port}   # Cancel reservation
POST /bulk-allocate      # Allocate multiple ports
```

### Health Monitoring
```
GET /health-report       # Full health report
POST /health-check       # Trigger health check
GET /orphans            # Unregistered listening ports
GET /zombies            # Registered but not listening
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store port allocation facts
await aria_store_memory(
    memory_type="fact",
    content=f"Port {port} allocated to {service} for {agent}",
    category="infrastructure",
    tags=["port-manager", "allocation"]
)
```

### ARIA Awareness
**Routing Triggers:**
```javascript
const portManagerPatterns = [
  /port (allocation|conflict|registry)/i,
  /what (port|service) (is|runs)/i,
  /allocate (a )?port/i,
  /check port (availability|conflicts)/i
];
```

### Event Bus Integration
```python
# Published events
"ports.allocated"
"ports.released"
"ports.conflict.detected"
"ports.health.unhealthy"
"ports.orphan.detected"

# Subscribed events
"agent.deployed"         # Register new agent ports
"agent.stopped"          # Mark ports as inactive
"container.started"      # Verify port allocation
```

### Cost Tracking
```python
# PORT MANAGER is lightweight - minimal LLM usage
# Track only operational metrics
```

### Integration with Other Agents
- **CERBERUS**: Report unusual port activity (security)
- **ARGUS**: Feed port metrics into monitoring
- **ATLAS**: Validate port allocations during orchestration
- **HEPHAESTUS**: Update docker-compose files with allocations

---

## CURRENT PORT ALLOCATIONS

```yaml
# Seed data for port_registry

infrastructure:
  - port: 5678
    service: n8n-prod
    environment: prod

  - port: 5679
    service: n8n-control
    environment: prod

  - port: 5680
    service: n8n-dev
    environment: dev

  - port: 8000
    service: supabase-kong
    environment: prod

  - port: 8007
    service: atlas
    environment: prod

  - port: 8008
    service: hades
    environment: prod

  - port: 8009
    service: argus
    environment: prod

  - port: 8010
    service: chronos
    environment: prod

  - port: 8011
    service: hephaestus
    environment: prod

  - port: 8012
    service: aegis
    environment: prod

  - port: 8013
    service: athena
    environment: prod

  - port: 8014
    service: hermes
    environment: prod

  - port: 8015
    service: aloy
    environment: prod

  - port: 8016
    service: argus-metrics
    environment: prod

  - port: 8017
    service: chiron
    environment: prod

  - port: 8018
    service: scholar
    environment: prod

  - port: 8099
    service: event-bus
    environment: prod

control_plane_agents:
  - port: 8020
    service: cerberus
    environment: prod
    status: planned

  - port: 8021
    service: port-manager
    environment: prod
    status: planned
```

---

## IMPLEMENTATION PHASES

### Phase 1: Core Registry (Sprint 1)
**Goal:** Basic port registration and lookup
- [ ] Create FastAPI agent structure
- [ ] Implement database schema
- [ ] Seed current port allocations
- [ ] Basic CRUD endpoints
- [ ] Deploy to port 8021

**Done When:** Can register and query port allocations

### Phase 2: Conflict Detection (Sprint 2)
**Goal:** Prevent port collisions
- [ ] Port scanning module
- [ ] Docker compose validation
- [ ] Conflict detection logic
- [ ] Alert integration via HERMES

**Done When:** Conflicts detected before deployment

### Phase 3: Dynamic Allocation (Sprint 3)
**Goal:** Automatic port assignment
- [ ] Allocation by category
- [ ] Reservation system
- [ ] Bulk allocation
- [ ] Expiring reservations

**Done When:** New services get ports automatically

### Phase 4: Health Monitoring (Sprint 4)
**Goal:** Continuous port health verification
- [ ] Periodic health checks
- [ ] Zombie/orphan detection
- [ ] ARGUS integration
- [ ] Dashboard metrics

**Done When:** Port health visible in monitoring

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Core Registry | 5 | 6 | 1 |
| Conflict Detection | 4 | 6 | 2 |
| Dynamic Allocation | 4 | 5 | 3 |
| Health Monitoring | 4 | 5 | 4 |
| **Total** | **17** | **22** | **4 sprints** |

---

## SUCCESS CRITERIA

- [ ] All current services registered in port registry
- [ ] Conflict detection catches 100% of collisions
- [ ] Port health checks run every 5 minutes
- [ ] New agent deployments get ports automatically
- [ ] Zero port conflicts in production

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/PORT-MANAGER.md

Context: Build PORT MANAGER utility agent. Start with Phase 1 core registry.
```
