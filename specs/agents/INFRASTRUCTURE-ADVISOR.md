# ATLAS - AI-Powered Infrastructure Advisory Agent

**Agent Type:** Infrastructure & Architecture
**Named After:** Atlas - The Titan who holds up the celestial heavens - ATLAS holds up and supports the infrastructure
**Port:** 8208
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

ATLAS is an AI-powered infrastructure advisory agent providing architecture decisions, scaling guidance, cost optimization, technology selection, and capacity planning. It serves as the strategic infrastructure brain for LeverEdge, ensuring systems are architected for performance, reliability, and cost efficiency.

### Value Proposition
- 40% reduction in infrastructure costs through optimization recommendations
- Prevent scaling incidents with proactive capacity forecasting
- Data-driven architecture decisions with documented rationale
- Technology selection backed by evaluation frameworks
- Premium consulting tier ($10K-50K engagements)

---

## CORE CAPABILITIES

### 1. Architecture Decisions
**Purpose:** AI-powered architectural guidance and decision documentation

**Features:**
- Architecture decision records (ADR) management
- Trade-off analysis for architectural choices
- Pattern recommendation based on requirements
- Decision impact assessment
- Historical decision tracking and learning

**Decision Categories:**
| Category | Scope | Output |
|----------|-------|--------|
| Data Architecture | Storage, schemas, replication | ADR + implementation guide |
| Service Architecture | Microservices, monolith, hybrid | ADR + migration path |
| Network Architecture | Load balancing, CDN, DNS | ADR + configuration |
| Security Architecture | Auth, encryption, compliance | ADR + security controls |
| Integration Architecture | APIs, messaging, sync | ADR + integration patterns |
| Deployment Architecture | Containers, serverless, VMs | ADR + deployment strategy |

### 2. Scaling Guidance
**Purpose:** Intelligent scaling recommendations and automation triggers

**Features:**
- Horizontal vs vertical scaling analysis
- Auto-scaling policy recommendations
- Load pattern recognition and prediction
- Scaling event impact analysis
- Cost-aware scaling decisions

**Scaling Triggers:**
| Metric | Threshold | Recommendation |
|--------|-----------|----------------|
| CPU Utilization | >75% sustained | Scale out/up |
| Memory Usage | >80% sustained | Scale up + optimize |
| Request Latency | >500ms P95 | Scale out + cache |
| Queue Depth | >1000 items | Add workers |
| Error Rate | >1% | Investigate + scale |
| Connection Pool | >90% used | Scale + optimize |

### 3. Cost Optimization
**Purpose:** Continuous infrastructure cost analysis and savings identification

**Features:**
- Resource utilization analysis
- Right-sizing recommendations
- Reserved instance/commitment planning
- Idle resource detection
- Cost allocation and chargeback
- Multi-cloud cost comparison

**Optimization Categories:**
- Compute: Instance right-sizing, spot/preemptible usage
- Storage: Tier optimization, lifecycle policies
- Network: Data transfer optimization, CDN placement
- Database: Query optimization, read replica tuning
- Licensing: Software license consolidation

### 4. Technology Selection
**Purpose:** Structured technology evaluation and recommendation framework

**Features:**
- Multi-criteria evaluation matrices
- Proof of concept guidance
- Vendor comparison frameworks
- Migration effort estimation
- Risk assessment for new technologies
- Technology radar maintenance

**Evaluation Criteria:**
- Performance benchmarks
- Operational complexity
- Community and support
- Cost (license + operational)
- Security posture
- Integration capabilities
- Learning curve

### 5. Capacity Planning
**Purpose:** Predictive resource planning and demand forecasting

**Features:**
- Usage trend analysis and extrapolation
- Seasonal pattern recognition
- Growth modeling based on business metrics
- Runway estimation (time until capacity exceeded)
- Budget forecasting for infrastructure
- What-if scenario modeling

**Forecast Horizons:**
- Short-term: 7-30 days (operational)
- Medium-term: 1-3 months (budget)
- Long-term: 6-12 months (strategic)

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis, local forecasting models
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/atlas/
├── atlas.py                 # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── scaling_rules.yaml   # Scaling thresholds and policies
│   ├── cost_thresholds.yaml # Cost alerting configuration
│   └── evaluation_criteria.yaml  # Technology evaluation weights
├── modules/
│   ├── architecture_advisor.py   # ADR management and guidance
│   ├── scaling_engine.py         # Scaling analysis and recommendations
│   ├── cost_optimizer.py         # Cost analysis and optimization
│   ├── tech_evaluator.py         # Technology selection framework
│   └── capacity_planner.py       # Forecasting and capacity planning
└── tests/
    └── test_atlas.py
```

### Database Schema

```sql
-- Architecture Decision Records
CREATE TABLE architecture_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    context TEXT NOT NULL,              -- Background and problem statement
    decision TEXT NOT NULL,             -- The actual decision made
    alternatives TEXT[],                -- Options that were considered
    consequences TEXT[],                -- Expected outcomes and trade-offs
    status TEXT DEFAULT 'proposed',     -- proposed, accepted, deprecated, superseded
    decided_at TIMESTAMPTZ,
    decided_by TEXT,
    superseded_by UUID REFERENCES architecture_decisions(id),
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_adr_status ON architecture_decisions(status);
CREATE INDEX idx_adr_created ON architecture_decisions(created_at DESC);
CREATE INDEX idx_adr_tags ON architecture_decisions USING GIN(tags);

-- Infrastructure Inventory
CREATE TABLE infrastructure_inventory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resource_type TEXT NOT NULL,        -- compute, storage, database, network, service
    name TEXT NOT NULL,
    provider TEXT NOT NULL,             -- aws, gcp, azure, digitalocean, self-hosted
    region TEXT,
    specs JSONB NOT NULL,               -- CPU, memory, storage, etc.
    monthly_cost DECIMAL(10,2),
    utilization JSONB,                  -- Current usage metrics
    tags TEXT[],
    status TEXT DEFAULT 'active',       -- active, stopped, terminated
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_inventory_type ON infrastructure_inventory(resource_type);
CREATE INDEX idx_inventory_provider ON infrastructure_inventory(provider);
CREATE INDEX idx_inventory_status ON infrastructure_inventory(status);

-- Cost Analysis Reports
CREATE TABLE cost_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period TEXT NOT NULL,               -- 2024-01, 2024-Q1, etc.
    breakdown JSONB NOT NULL,           -- By service, by type, by tag
    total_cost DECIMAL(12,2) NOT NULL,
    previous_period_cost DECIMAL(12,2),
    change_percentage DECIMAL(5,2),
    recommendations TEXT[],
    savings_potential DECIMAL(10,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cost_period ON cost_analysis(period);
CREATE INDEX idx_cost_created ON cost_analysis(created_at DESC);

-- Scaling Events
CREATE TABLE scaling_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES infrastructure_inventory(id),
    service_name TEXT NOT NULL,
    trigger TEXT NOT NULL,              -- manual, auto, recommendation
    trigger_metric TEXT,                -- cpu, memory, requests, queue
    trigger_value DECIMAL(10,2),
    from_config JSONB NOT NULL,         -- Previous configuration
    to_config JSONB NOT NULL,           -- New configuration
    result TEXT DEFAULT 'pending',      -- pending, success, failed, rolled_back
    cost_impact DECIMAL(10,2),          -- Monthly cost change
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_scaling_service ON scaling_events(service_name);
CREATE INDEX idx_scaling_result ON scaling_events(result);
CREATE INDEX idx_scaling_created ON scaling_events(created_at DESC);

-- Technology Evaluations
CREATE TABLE technology_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,             -- database, messaging, cache, framework, etc.
    requirement TEXT NOT NULL,          -- What problem are we solving
    options JSONB NOT NULL,             -- Array of evaluated options with scores
    recommendation TEXT NOT NULL,
    rationale TEXT NOT NULL,
    risks TEXT[],
    migration_effort TEXT,              -- low, medium, high
    evaluated_by TEXT,
    evaluated_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'active'        -- active, superseded, archived
);

CREATE INDEX idx_eval_category ON technology_evaluations(category);
CREATE INDEX idx_eval_created ON technology_evaluations(evaluated_at DESC);

-- Capacity Forecasts
CREATE TABLE capacity_forecasts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id UUID REFERENCES infrastructure_inventory(id),
    service_name TEXT NOT NULL,
    metric TEXT NOT NULL,               -- cpu, memory, storage, connections, etc.
    current_usage DECIMAL(10,2) NOT NULL,
    current_capacity DECIMAL(10,2) NOT NULL,
    utilization_pct DECIMAL(5,2),
    projected_usage JSONB NOT NULL,     -- {7d, 30d, 90d} forecasts
    days_until_threshold INTEGER,       -- Days until 80% capacity
    recommendation TEXT NOT NULL,
    confidence DECIMAL(3,2),            -- Forecast confidence 0-1
    forecast_date TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_forecast_service ON capacity_forecasts(service_name);
CREATE INDEX idx_forecast_metric ON capacity_forecasts(metric);
CREATE INDEX idx_forecast_date ON capacity_forecasts(forecast_date DESC);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + infrastructure overview
GET /status              # Real-time infrastructure status
GET /metrics             # Prometheus-compatible metrics
```

### Architecture Decisions
```
POST /architecture/advise     # Get architectural advice for a scenario
GET /architecture/decisions   # List all ADRs
POST /architecture/decisions  # Create new ADR
GET /architecture/decisions/{id}  # Get specific ADR
PUT /architecture/decisions/{id}  # Update ADR status
GET /architecture/patterns    # Get recommended patterns for use case
```

### Scaling
```
POST /scaling/analyze         # Analyze current scaling needs
GET /scaling/recommendations  # Get pending scaling recommendations
POST /scaling/apply          # Apply scaling recommendation
GET /scaling/events          # List scaling history
GET /scaling/policies        # Get configured auto-scaling policies
PUT /scaling/policies        # Update scaling policies
```

### Cost Optimization
```
GET /cost/analysis           # Get current cost analysis
POST /cost/analyze           # Trigger new cost analysis
GET /cost/recommendations    # Get cost optimization recommendations
GET /cost/trends             # Cost trends over time
GET /cost/forecast           # Projected costs
GET /cost/breakdown          # Cost breakdown by service/tag
POST /cost/alert             # Configure cost alerts
```

### Technology Evaluation
```
POST /technology/evaluate    # Evaluate technology options
GET /technology/evaluations  # List all evaluations
GET /technology/evaluations/{id}  # Get specific evaluation
GET /technology/radar        # Get technology radar
POST /technology/compare     # Compare specific technologies
```

### Capacity Planning
```
GET /capacity/forecasts      # Get all capacity forecasts
POST /capacity/forecast      # Generate new forecast
GET /capacity/alerts         # Services approaching capacity
GET /capacity/runway         # Days until capacity for each service
POST /capacity/scenario      # Run what-if scenario
```

### Inventory
```
GET /inventory               # List all infrastructure
POST /inventory              # Add resource to inventory
PUT /inventory/{id}          # Update resource
DELETE /inventory/{id}       # Remove resource
GET /inventory/summary       # Infrastructure summary
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store architecture decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Architecture decision: {title} - {decision}",
    category="infrastructure",
    source_type="agent_result",
    tags=["atlas", "architecture", "adr"]
)

# Store cost insights
await aria_store_memory(
    memory_type="fact",
    content=f"Monthly infrastructure cost: ${total_cost}. Savings potential: ${savings}",
    category="infrastructure",
    source_type="agent_result",
    tags=["atlas", "cost", "optimization"]
)

# Store capacity warnings
await aria_store_memory(
    memory_type="alert",
    content=f"Service {service} will exceed capacity in {days} days",
    category="infrastructure",
    source_type="automated",
    tags=["atlas", "capacity", "warning"]
)
```

### ARIA Tools (Routing)
ARIA should be able to invoke ATLAS through natural language:

```python
# ARIA tool definitions for routing
aria_tools = {
    "infra.advise": {
        "description": "Get infrastructure architecture advice",
        "endpoint": "/architecture/advise",
        "method": "POST"
    },
    "infra.cost": {
        "description": "Analyze infrastructure costs and get optimization recommendations",
        "endpoint": "/cost/analyze",
        "method": "POST"
    },
    "infra.scale": {
        "description": "Get scaling recommendations for a service",
        "endpoint": "/scaling/analyze",
        "method": "POST"
    },
    "infra.evaluate": {
        "description": "Evaluate technology options for a requirement",
        "endpoint": "/technology/evaluate",
        "method": "POST"
    },
    "infra.forecast": {
        "description": "Get capacity forecast for infrastructure",
        "endpoint": "/capacity/forecast",
        "method": "POST"
    }
}
```

**Routing Triggers:**
```javascript
const atlasPatterns = [
  /infrastructure (advice|recommendation|decision)/i,
  /architect(ure)?|design|pattern/i,
  /scal(e|ing)|capacity|performance/i,
  /cost (optim|analy|reduc|sav)/i,
  /technology (select|evaluat|compar)/i,
  /forecast|predict|capacity plan/i,
  /right[- ]?siz(e|ing)/i
];
```

### Event Bus Integration
```python
# Published events
"infra.decision.made"           # New architecture decision recorded
"infra.decision.superseded"     # ADR superseded by newer decision
"infra.cost.alert"              # Cost threshold exceeded
"infra.cost.savings.identified" # New savings opportunity found
"infra.scaling.recommended"     # Scaling recommendation generated
"infra.scaling.applied"         # Scaling change applied
"infra.capacity.warning"        # Approaching capacity limit
"infra.capacity.critical"       # Capacity critically low
"infra.technology.evaluated"    # Technology evaluation completed

# Subscribed events
"system.metrics.updated"        # New metrics available
"system.service.deployed"       # New service to monitor
"system.cost.reported"          # Cost data from providers
"agent.scaling.requested"       # Another agent needs scaling advice
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("ATLAS")

# Log AI analysis costs
await cost_tracker.log_usage(
    endpoint="/architecture/advise",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"advice_type": advice_type}
)

# Log cost analysis costs
await cost_tracker.log_usage(
    endpoint="/cost/analyze",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"period": period, "services_analyzed": count}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(infrastructure_context: dict) -> str:
    return f"""You are ATLAS - Elite Infrastructure Advisory Agent for LeverEdge AI.

Named after the Titan who holds up the celestial heavens, you hold up and support all LeverEdge infrastructure with wisdom and foresight.

## TIME AWARENESS
- Current: {infrastructure_context['current_time']}
- Days to Launch: {infrastructure_context['days_to_launch']}

## YOUR IDENTITY
You are the strategic infrastructure brain of LeverEdge. You advise on architecture, guide scaling decisions, optimize costs, evaluate technologies, and plan capacity. Your recommendations are data-driven, cost-aware, and aligned with business objectives.

## CURRENT INFRASTRUCTURE STATUS
- Total Resources: {infrastructure_context['total_resources']}
- Monthly Cost: ${infrastructure_context['monthly_cost']}
- Cost Trend: {infrastructure_context['cost_trend']}
- Services Near Capacity: {infrastructure_context['capacity_warnings']}
- Pending Recommendations: {infrastructure_context['pending_recommendations']}

## YOUR CAPABILITIES

### Architecture Decisions
- Create and manage Architecture Decision Records (ADRs)
- Analyze trade-offs between architectural options
- Recommend patterns based on requirements
- Document decisions with rationale and consequences
- Track decision history and supersession

### Scaling Guidance
- Analyze current resource utilization
- Recommend horizontal vs vertical scaling
- Configure auto-scaling policies
- Predict scaling needs based on trends
- Calculate cost impact of scaling decisions

### Cost Optimization
- Analyze infrastructure spending by service, type, tag
- Identify unused and underutilized resources
- Recommend right-sizing opportunities
- Suggest reserved instance purchases
- Track savings from implemented recommendations

### Technology Selection
- Evaluate technologies against weighted criteria
- Compare vendors and open-source options
- Assess migration effort and risks
- Provide proof-of-concept guidance
- Maintain technology radar

### Capacity Planning
- Forecast resource needs across time horizons
- Calculate runway until capacity limits
- Model growth based on business metrics
- Run what-if scenarios
- Alert on approaching limits

## DECISION FRAMEWORK

When making recommendations:
1. **Understand Context**: What's the business goal? What constraints exist?
2. **Gather Data**: Current metrics, trends, costs, dependencies
3. **Analyze Options**: Trade-offs, risks, costs, complexity
4. **Recommend**: Clear recommendation with rationale
5. **Document**: Create ADR for significant decisions

## COST AWARENESS
Always consider cost implications:
- What's the monthly cost impact?
- Is there a cheaper alternative with acceptable trade-offs?
- Can we use reserved/committed pricing?
- Are there idle resources to reclaim?

## TEAM COORDINATION
- Route implementation tasks to HEPHAESTUS
- Request backup before infrastructure changes via CHRONOS
- Send infrastructure alerts via HERMES
- Log insights to ARIA via Unified Memory
- Publish events to Event Bus

## RESPONSE FORMAT
For infrastructure advice:
1. **Context Understanding**: Restate the problem/requirement
2. **Current State**: Relevant metrics and observations
3. **Analysis**: Trade-offs and considerations
4. **Recommendation**: Clear, actionable guidance
5. **Cost Impact**: Expected cost change
6. **Next Steps**: Implementation path

## YOUR MISSION
Ensure LeverEdge infrastructure is:
- Performant: Fast and responsive
- Reliable: Highly available, fault tolerant
- Cost-efficient: No waste, optimized spending
- Scalable: Ready for growth
- Well-documented: Decisions tracked and rationale preserved
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with inventory and health monitoring
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Infrastructure inventory management
- [ ] Basic metrics collection
- [ ] Deploy and test

**Done When:** ATLAS runs and can track infrastructure inventory

### Phase 2: Architecture Decisions (Sprint 3-4)
**Goal:** ADR management and architectural guidance
- [ ] Architecture decision record CRUD
- [ ] AI-powered architecture advice endpoint
- [ ] Pattern recommendation engine
- [ ] Decision search and history
- [ ] Integration with Unified Memory

**Done When:** Can create ADRs and get AI architecture advice

### Phase 3: Cost Optimization (Sprint 5-6)
**Goal:** Cost analysis and optimization recommendations
- [ ] Cost data ingestion from providers
- [ ] Cost breakdown analysis
- [ ] Utilization-based recommendations
- [ ] Savings tracking
- [ ] Cost alerting

**Done When:** Generating actionable cost optimization recommendations

### Phase 4: Scaling & Capacity (Sprint 7-8)
**Goal:** Scaling guidance and capacity forecasting
- [ ] Scaling analysis engine
- [ ] Auto-scaling policy management
- [ ] Capacity forecasting models
- [ ] Runway calculations
- [ ] Capacity alerting

**Done When:** Proactive scaling recommendations and capacity warnings

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 5 | 10 | 1-2 |
| Architecture Decisions | 5 | 12 | 3-4 |
| Cost Optimization | 5 | 14 | 5-6 |
| Scaling & Capacity | 5 | 12 | 7-8 |
| **Total** | **20** | **48** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Architecture advice with < 30 second response time
- [ ] Cost analysis updated daily with actionable recommendations
- [ ] Scaling recommendations generated within 60 seconds
- [ ] Capacity forecasts accurate within 20% over 30-day horizon
- [ ] Technology evaluations with multi-criteria scoring

### Quality
- [ ] 95%+ uptime
- [ ] < 10% deviation between forecasted and actual costs
- [ ] Zero capacity-related outages with ATLAS warnings
- [ ] All architecture decisions documented with ADRs

### Integration
- [ ] ARIA can query infrastructure status and get advice
- [ ] Events publish to Event Bus
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per request
- [ ] ARIA tools (infra.*) routing functional

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Inaccurate cost data | Wrong recommendations | Multiple data sources, validation checks |
| Forecast model drift | Capacity surprises | Regular model retraining, confidence scores |
| Recommendation fatigue | Ignored advice | Prioritization, impact scoring, digest format |
| Stale architecture decisions | Outdated guidance | Regular ADR review process, supersession tracking |
| Over-optimization | Service degradation | Always maintain performance thresholds |

---

## GIT COMMIT

```
Add ATLAS - AI-powered infrastructure advisory agent spec

- Architecture decision records (ADR) management
- Scaling guidance and auto-scaling policies
- Cost optimization with savings tracking
- Technology evaluation framework
- Capacity planning and forecasting
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
- ARIA tools: infra.advise, infra.cost, infra.scale, infra.evaluate, infra.forecast
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/INFRASTRUCTURE-ADVISOR.md

Context: Build ATLAS infrastructure advisory agent. Start with Phase 1 foundation.
```
