# AUDITOR-QA - AI-Powered Quality Assurance Agent

**Agent Type:** Quality Assurance & Compliance
**Named After:** Themis - Greek goddess of justice and fair judgment - AUDITOR-QA ensures fairness and quality in all agent outputs
**Port:** 8203
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

AUDITOR-QA is an AI-powered quality assurance agent providing comprehensive output review, compliance checking, quality gates enforcement, and continuous feedback loops for all LeverEdge agents. It serves as the central quality brain ensuring consistent, high-quality outputs across the entire agent ecosystem.

### Value Proposition
- 99% consistency in output quality standards
- 60% reduction in quality-related rework
- Automated compliance verification across all domains
- Real-time quality metrics and trend analysis
- Continuous improvement feedback loop for agents

---

## CORE CAPABILITIES

### 1. Output Review
**Purpose:** AI-powered review of agent outputs for quality, accuracy, and completeness

**Features:**
- Deep content analysis using LLM evaluation
- Multi-dimensional quality scoring (accuracy, clarity, completeness, relevance)
- Automated issue detection and categorization
- Contextual review based on output type and domain
- Confidence scoring for review assessments

**Review Dimensions:**
| Dimension | Description | Weight |
|-----------|-------------|--------|
| Accuracy | Factual correctness and precision | 30% |
| Completeness | All requirements addressed | 25% |
| Clarity | Clear, understandable output | 20% |
| Relevance | Appropriate for context/request | 15% |
| Format | Proper structure and presentation | 10% |

### 2. Compliance Checking
**Purpose:** Verify outputs meet established standards and policies

**Features:**
- Pattern-based rule matching
- Domain-specific compliance rules
- Severity-based violation classification
- Automatic remediation suggestions
- Compliance history tracking

**Compliance Categories:**
- Content policies (safety, appropriateness)
- Technical standards (code quality, documentation)
- Business rules (branding, messaging)
- Regulatory requirements (data handling, privacy)
- Internal guidelines (style, format)

### 3. Quality Gates
**Purpose:** Define and enforce quality thresholds before outputs proceed

**Features:**
- Configurable pass/fail thresholds per domain
- Multi-check gate definitions
- Action routing on gate failure (reject, escalate, notify)
- Gate bypass for authorized overrides
- Gate performance analytics

**Gate Actions:**
| Action | Trigger | Behavior |
|--------|---------|----------|
| Pass | Score >= threshold | Output approved |
| Soft Fail | Score slightly below | Warning + approval |
| Hard Fail | Score significantly below | Block + feedback |
| Escalate | Critical issues found | Route to human review |

### 4. Feedback Loop
**Purpose:** Provide improvement feedback to agents for continuous quality enhancement

**Features:**
- Specific, actionable feedback generation
- Pattern identification across reviews
- Agent-specific improvement recommendations
- Feedback acknowledgment tracking
- Improvement verification on subsequent outputs

**Feedback Types:**
- Immediate corrections (specific issues)
- Pattern alerts (recurring problems)
- Best practice suggestions
- Positive reinforcement (exemplary outputs)

### 5. Metrics Dashboard
**Purpose:** Track quality metrics over time for visibility and improvement

**Features:**
- Real-time quality scores by agent
- Trend analysis and forecasting
- Common issue aggregation
- Comparative benchmarking
- Exportable reports

**Key Metrics:**
- Average quality score by agent
- Pass rate by quality gate
- Common issue frequency
- Improvement rate over time
- Review volume and throughput

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for quality analysis
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/auditor-qa/
├── auditor_qa.py             # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── standards.yaml        # Quality standard definitions
│   ├── gates.yaml            # Quality gate configurations
│   └── compliance_rules.yaml # Compliance rule definitions
├── modules/
│   ├── reviewer.py           # AI-powered output review
│   ├── compliance_checker.py # Compliance verification
│   ├── gate_enforcer.py      # Quality gate enforcement
│   ├── feedback_generator.py # Feedback loop management
│   └── metrics_engine.py     # Metrics and analytics
└── tests/
    └── test_auditor_qa.py
```

### Database Schema

```sql
-- Quality standards table
CREATE TABLE quality_standards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT NOT NULL,            -- code, documentation, response, report
    name TEXT NOT NULL,
    criteria TEXT[] NOT NULL,        -- list of criteria to check
    weight FLOAT DEFAULT 1.0,        -- relative importance
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_standards_domain ON quality_standards(domain);
CREATE INDEX idx_standards_active ON quality_standards(active);
CREATE UNIQUE INDEX idx_standards_domain_name ON quality_standards(domain, name);

-- Reviews table
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    output_id TEXT NOT NULL,         -- reference to the output being reviewed
    output_type TEXT NOT NULL,       -- code, response, document, report
    score FLOAT NOT NULL,            -- 0-100 quality score
    passed BOOLEAN NOT NULL,
    findings JSONB NOT NULL,         -- detailed findings array
    dimension_scores JSONB,          -- scores per dimension
    reviewed_at TIMESTAMPTZ DEFAULT NOW(),
    review_duration_ms INTEGER,
    reviewer_model TEXT              -- which AI model performed review
);

CREATE INDEX idx_reviews_agent ON reviews(agent_name);
CREATE INDEX idx_reviews_output_type ON reviews(output_type);
CREATE INDEX idx_reviews_reviewed_at ON reviews(reviewed_at DESC);
CREATE INDEX idx_reviews_passed ON reviews(passed);
CREATE INDEX idx_reviews_score ON reviews(score);

-- Quality gates table
CREATE TABLE quality_gates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    min_score FLOAT NOT NULL,        -- minimum passing score
    checks TEXT[] NOT NULL,          -- list of checks to perform
    action_on_fail TEXT DEFAULT 'reject',  -- reject, warn, escalate
    escalation_contact TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gates_domain ON quality_gates(domain);
CREATE INDEX idx_gates_active ON quality_gates(active);

-- Compliance rules table
CREATE TABLE compliance_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    pattern TEXT NOT NULL,           -- regex or rule pattern
    severity TEXT NOT NULL,          -- critical, high, medium, low
    domain TEXT NOT NULL,
    remediation TEXT,                -- suggested fix
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_compliance_domain ON compliance_rules(domain);
CREATE INDEX idx_compliance_severity ON compliance_rules(severity);
CREATE INDEX idx_compliance_active ON compliance_rules(active);

-- Quality metrics table (aggregated)
CREATE TABLE quality_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    period TEXT NOT NULL,            -- daily, weekly, monthly
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    avg_score FLOAT NOT NULL,
    pass_rate FLOAT NOT NULL,        -- percentage of passed reviews
    total_reviews INTEGER NOT NULL,
    common_issues JSONB,             -- most frequent issues
    improvement_rate FLOAT,          -- change from previous period
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_metrics_agent ON quality_metrics(agent_name);
CREATE INDEX idx_metrics_period ON quality_metrics(period, period_start);
CREATE UNIQUE INDEX idx_metrics_agent_period ON quality_metrics(agent_name, period, period_start);

-- Feedback log table
CREATE TABLE feedback_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_id UUID REFERENCES reviews(id),
    agent_name TEXT NOT NULL,
    feedback TEXT NOT NULL,
    feedback_type TEXT NOT NULL,     -- correction, pattern, suggestion, praise
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    improvements TEXT[],             -- list of improvements made
    verified BOOLEAN DEFAULT FALSE,  -- improvement verified in subsequent review
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feedback_review ON feedback_log(review_id);
CREATE INDEX idx_feedback_agent ON feedback_log(agent_name);
CREATE INDEX idx_feedback_acknowledged ON feedback_log(acknowledged);
CREATE INDEX idx_feedback_type ON feedback_log(feedback_type);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + QA system overview
GET /status              # Real-time quality metrics summary
GET /metrics             # Prometheus-compatible metrics
```

### Output Review
```
POST /review             # Submit output for quality review
GET /reviews             # List recent reviews (filterable)
GET /reviews/{id}        # Review detail with findings
GET /reviews/agent/{name}    # Reviews for specific agent
GET /reviews/summary     # Executive quality summary
POST /review/batch       # Batch review multiple outputs
```

### Compliance
```
POST /compliance/check   # Check output against compliance rules
GET /compliance/rules    # List all compliance rules
POST /compliance/rules   # Create new compliance rule
PUT /compliance/rules/{id}   # Update compliance rule
DELETE /compliance/rules/{id}   # Delete compliance rule
GET /compliance/violations   # Recent compliance violations
```

### Quality Gates
```
POST /gate/check         # Check if output passes quality gate
GET /gates               # List all quality gates
POST /gates              # Create new quality gate
PUT /gates/{id}          # Update quality gate
DELETE /gates/{id}       # Delete quality gate
GET /gates/status/{output_id}   # Gate status for specific output
POST /gates/override     # Override gate decision (authorized)
```

### Feedback
```
POST /feedback           # Generate feedback for agent
GET /feedback/agent/{name}   # Feedback history for agent
POST /feedback/{id}/acknowledge   # Mark feedback as acknowledged
POST /feedback/{id}/verify   # Verify improvement was made
GET /feedback/pending    # Unacknowledged feedback
```

### Metrics & Analytics
```
GET /metrics/agent/{name}    # Quality metrics for agent
GET /metrics/trends      # Quality trends over time
GET /metrics/comparison  # Compare agents' quality scores
GET /metrics/issues      # Common issues across all agents
POST /metrics/export     # Export metrics report
GET /metrics/dashboard   # Full dashboard data
```

### Standards Management
```
GET /standards           # List all quality standards
POST /standards          # Create new standard
PUT /standards/{id}      # Update standard
DELETE /standards/{id}   # Delete standard
GET /standards/domain/{domain}   # Standards for specific domain
```

---

## ARIA TOOL DEFINITIONS

### qa.review
**Purpose:** Review an agent output for quality
```python
{
    "name": "qa.review",
    "description": "Review an output for quality, accuracy, and completeness",
    "parameters": {
        "output": "string - the output content to review",
        "output_type": "string - type of output (code, response, document, report)",
        "agent_name": "string - name of agent that produced output",
        "context": "string - optional context about the request",
        "standards": "array - optional specific standards to check"
    },
    "returns": {
        "score": "float - overall quality score 0-100",
        "passed": "boolean - whether output meets quality threshold",
        "findings": "array - detailed findings with severity and suggestions",
        "dimension_scores": "object - scores per quality dimension"
    }
}
```

### qa.check_compliance
**Purpose:** Check output against compliance rules
```python
{
    "name": "qa.check_compliance",
    "description": "Verify output meets compliance standards and policies",
    "parameters": {
        "output": "string - the output content to check",
        "domain": "string - domain for applicable rules",
        "rules": "array - optional specific rule names to check"
    },
    "returns": {
        "compliant": "boolean - whether output is fully compliant",
        "violations": "array - list of rule violations with severity",
        "remediation": "array - suggested fixes for violations"
    }
}
```

### qa.gate_status
**Purpose:** Check if output passes quality gates
```python
{
    "name": "qa.gate_status",
    "description": "Check if an output passes the applicable quality gates",
    "parameters": {
        "output_id": "string - ID of the output to check",
        "gate_name": "string - optional specific gate to check"
    },
    "returns": {
        "passed": "boolean - whether all gates passed",
        "gates": "array - status of each applicable gate",
        "action": "string - recommended action (proceed, revise, escalate)"
    }
}
```

### qa.agent_score
**Purpose:** Get quality score for an agent
```python
{
    "name": "qa.agent_score",
    "description": "Get the current quality score and metrics for an agent",
    "parameters": {
        "agent_name": "string - name of the agent",
        "period": "string - time period (day, week, month, all)"
    },
    "returns": {
        "avg_score": "float - average quality score",
        "pass_rate": "float - percentage of passed reviews",
        "total_reviews": "integer - number of reviews in period",
        "common_issues": "array - most frequent issues",
        "trend": "string - improving, stable, declining"
    }
}
```

### qa.trends
**Purpose:** Get quality trends over time
```python
{
    "name": "qa.trends",
    "description": "Get quality trends and analytics over time",
    "parameters": {
        "agent_name": "string - optional agent to filter by",
        "days": "integer - number of days to analyze (default 30)",
        "metric": "string - specific metric to trend (score, pass_rate, violations)"
    },
    "returns": {
        "data_points": "array - trend data with timestamps",
        "direction": "string - overall trend direction",
        "forecast": "float - predicted next period value",
        "insights": "array - AI-generated insights about trends"
    }
}
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store quality insights
await aria_store_memory(
    memory_type="fact",
    content=f"Agent {agent_name} quality score: {score}% (pass rate: {pass_rate}%)",
    category="quality",
    source_type="agent_result",
    tags=["auditor-qa", "metrics", agent_name]
)

# Store quality decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Quality gate '{gate_name}' failed for {agent_name}: {reason}",
    category="quality",
    source_type="automated"
)

# Store improvement patterns
await aria_store_memory(
    memory_type="insight",
    content=f"Pattern detected: {agent_name} consistently struggles with {issue_type}",
    category="quality",
    source_type="analysis"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What's the quality score for HEPHAESTUS?"
- Request "Review this output for quality"
- Query "Any compliance violations today?"
- Get alerted on quality gate failures
- Request "Show me quality trends for last week"

**Routing Triggers:**
```javascript
const auditorQaPatterns = [
  /quality (check|review|score|gate)/i,
  /compliance (check|violation|verify)/i,
  /review (output|response|code)/i,
  /pass rate|quality metrics/i,
  /feedback (loop|for agent)/i,
  /output quality|agent performance/i
];
```

### Event Bus Integration
```python
# Published events
"qa.review.completed"        # Review finished with results
"qa.gate.passed"            # Output passed quality gate
"qa.gate.failed"            # Output failed quality gate
"qa.compliance.violation"   # Compliance rule violated

# Event payloads
{
    "event": "qa.review.completed",
    "data": {
        "review_id": "uuid",
        "agent_name": "string",
        "output_type": "string",
        "score": "float",
        "passed": "boolean",
        "findings_count": "integer"
    }
}

{
    "event": "qa.gate.failed",
    "data": {
        "gate_name": "string",
        "agent_name": "string",
        "output_id": "string",
        "score": "float",
        "min_score": "float",
        "action": "string"
    }
}

# Subscribed events
"agent.output.generated"    # Trigger automatic review
"agent.task.completed"      # Review task outputs
"system.deploy.ready"       # Pre-deployment quality check
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("AUDITOR-QA")

# Log AI review costs
await cost_tracker.log_usage(
    endpoint="/review",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={
        "agent_name": agent_name,
        "output_type": output_type,
        "review_type": "quality"
    }
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(qa_context: dict) -> str:
    return f"""You are AUDITOR-QA - Elite Quality Assurance Agent for LeverEdge AI.

Named after Themis, the Greek goddess of justice and fair judgment, you ensure quality and fairness in all agent outputs.

## TIME AWARENESS
- Current: {qa_context['current_time']}
- Days to Launch: {qa_context['days_to_launch']}

## YOUR IDENTITY
You are the quality brain of LeverEdge. You review outputs, enforce standards, verify compliance, and drive continuous improvement across all agents.

## CURRENT QA STATUS
- Pending Reviews: {qa_context['pending_reviews']}
- Average Quality Score: {qa_context['avg_score']}%
- Pass Rate (24h): {qa_context['pass_rate']}%
- Active Compliance Violations: {qa_context['violations']}

## YOUR CAPABILITIES

### Output Review
- Deep content analysis for quality assessment
- Multi-dimensional scoring (accuracy, clarity, completeness, relevance, format)
- Issue detection with severity classification
- Actionable improvement suggestions

### Compliance Checking
- Pattern-based rule matching
- Domain-specific compliance verification
- Severity-based violation classification
- Remediation recommendations

### Quality Gates
- Threshold enforcement before output approval
- Multi-check gate definitions
- Failure routing (reject, escalate, notify)
- Override management for authorized bypasses

### Feedback Loop
- Specific, actionable feedback generation
- Pattern identification across reviews
- Agent-specific improvement tracking
- Verification of improvements

### Metrics & Analytics
- Real-time quality dashboards
- Trend analysis and forecasting
- Comparative benchmarking
- Exportable reports

## QUALITY DIMENSIONS
1. **Accuracy** (30%): Factual correctness, precision, no errors
2. **Completeness** (25%): All requirements addressed, nothing missing
3. **Clarity** (20%): Clear, understandable, well-organized
4. **Relevance** (15%): Appropriate for context, addresses actual need
5. **Format** (10%): Proper structure, presentation, formatting

## TEAM COORDINATION
- Review outputs from ALL agents
- Provide feedback to agents for improvement
- Alert HERMES on critical quality issues
- Log insights to ARIA via Unified Memory
- Publish events to Event Bus

## RESPONSE FORMAT
For quality reviews:
1. Overall score and pass/fail status
2. Dimension-by-dimension breakdown
3. Specific findings with severity
4. Actionable improvement suggestions
5. Pattern observations (if recurring)

## YOUR MISSION
Maintain the highest quality standards across LeverEdge.
Fair, consistent, constructive feedback.
Every output matters.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with review capability
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Basic output review with AI scoring
- [ ] Database schema deployment
- [ ] Deploy and test

**Done When:** AUDITOR-QA can review outputs and return quality scores

### Phase 2: Quality Gates (Sprint 3)
**Goal:** Automated quality gate enforcement
- [ ] Quality gate configuration system
- [ ] Gate checking logic
- [ ] Pass/fail action routing
- [ ] Gate override capability
- [ ] Integration with agent outputs

**Done When:** Outputs are automatically gated before proceeding

### Phase 3: Compliance Framework (Sprint 4)
**Goal:** Rule-based compliance checking
- [ ] Compliance rule definition system
- [ ] Pattern matching engine
- [ ] Violation detection and reporting
- [ ] Remediation suggestions
- [ ] Violation history tracking

**Done When:** Outputs checked against compliance rules automatically

### Phase 4: Feedback & Metrics (Sprint 5-6)
**Goal:** Continuous improvement loop
- [ ] Feedback generation system
- [ ] Feedback acknowledgment workflow
- [ ] Improvement verification
- [ ] Metrics aggregation engine
- [ ] Dashboard API endpoints
- [ ] Trend analysis and forecasting

**Done When:** Agents receive feedback and quality improves over time

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 5 | 10 | 1-2 |
| Quality Gates | 5 | 8 | 3 |
| Compliance Framework | 5 | 8 | 4 |
| Feedback & Metrics | 6 | 14 | 5-6 |
| **Total** | **21** | **40** | **6 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Review outputs with < 5 second response time
- [ ] Quality gates enforce thresholds consistently
- [ ] Compliance violations detected with 95%+ accuracy
- [ ] Feedback loop drives measurable improvement

### Quality
- [ ] 99%+ uptime for review endpoints
- [ ] < 3% false positive rate on violations
- [ ] Consistent scoring (< 5% variance on same input)
- [ ] All reviews logged and searchable

### Integration
- [ ] ARIA can request quality reviews
- [ ] Events publish to Event Bus
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per review

### Impact
- [ ] 20% improvement in agent output quality within 30 days
- [ ] 50% reduction in quality-related rework
- [ ] Clear visibility into quality metrics across all agents

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Inconsistent AI scoring | Unfair assessments | Calibration dataset, human review sampling |
| Review latency impacts UX | Slow user experience | Async reviews, caching, parallel processing |
| False positive violations | Alert fatigue | Tunable sensitivity, pattern learning |
| Feedback not actionable | No improvement | Specific, example-based feedback generation |
| Agents bypass quality gates | Quality degradation | Mandatory gate checks, audit logging |

---

## GIT COMMIT

```
Add AUDITOR-QA - AI-powered quality assurance agent spec

- Output review with multi-dimensional scoring
- Quality gates for threshold enforcement
- Compliance checking framework
- Feedback loop for continuous improvement
- Metrics dashboard for quality analytics
- ARIA tool definitions (qa.review, qa.check_compliance, etc.)
- Event Bus integration (qa.review.completed, qa.gate.passed/failed)
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/AUDITOR-QA.md

Context: Build AUDITOR-QA quality assurance agent. Start with Phase 1 foundation.
```
