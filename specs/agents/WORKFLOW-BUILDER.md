# WORKFLOW BUILDER - AI-Powered Workflow Generation Agent

**Agent Type:** Automation & Development
**Named After:** Daedalus - the master craftsman and inventor of Greek mythology who built the Labyrinth and crafted wings of wax and feathers
**Port:** 8202
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

WORKFLOW BUILDER is an AI-powered agent that transforms natural language specifications into fully functional n8n workflows. It serves as the automation architect for LeverEdge, enabling rapid workflow development, testing, and deployment without manual node configuration.

### Value Proposition
- 80% reduction in workflow development time
- Consistent, tested workflow patterns across all deployments
- Natural language to automation - no n8n expertise required
- Reusable template library for common patterns
- Automated validation prevents deployment failures

---

## CORE CAPABILITIES

### 1. Spec to Workflow Conversion
**Purpose:** Transform natural language specifications into complete n8n workflows with proper node configuration and connections

**Features:**
- Natural language parsing and intent extraction
- Requirement decomposition into discrete nodes
- Automatic connection mapping between nodes
- Variable and credential placeholder injection
- Multi-step workflow generation with branching logic

**Conversion Pipeline:**
| Stage | Process | Output |
|-------|---------|--------|
| Parse | Extract intent and requirements | Structured spec |
| Design | Map to n8n node types | Node blueprint |
| Generate | Create node configurations | JSON nodes |
| Connect | Build connection graph | Workflow JSON |
| Validate | Check structure integrity | Validation report |

### 2. Node Generation
**Purpose:** Create properly configured n8n nodes from high-level requirements

**Features:**
- Support for all core n8n node types
- Parameter inference from context
- Credential reference binding
- Expression and variable injection
- Error handling node insertion
- Retry logic configuration

**Supported Node Categories:**
- Triggers (Webhook, Schedule, Event)
- HTTP/API nodes (REST, GraphQL, SOAP)
- Database nodes (PostgreSQL, MongoDB, Redis)
- Messaging nodes (Slack, Email, SMS)
- AI nodes (OpenAI, Anthropic, Custom LLM)
- Logic nodes (IF, Switch, Merge, Loop)
- Transform nodes (Set, Code, Function)

### 3. Workflow Testing
**Purpose:** Validate workflows before deployment through automated testing

**Features:**
- Dry-run execution with mock data
- Node-by-node execution tracing
- Output validation against expected schemas
- Error path testing
- Performance benchmarking
- Integration test generation

**Test Types:**
| Test Type | Description | Scope |
|-----------|-------------|-------|
| Unit | Individual node behavior | Single node |
| Integration | Node-to-node data flow | Connected nodes |
| End-to-End | Full workflow execution | Complete workflow |
| Load | Performance under stress | Throughput |
| Regression | Compare against baseline | Version changes |

### 4. Template Library
**Purpose:** Maintain reusable workflow patterns for common automation scenarios

**Features:**
- Categorized template repository
- Variable substitution placeholders
- Template composition and inheritance
- Usage analytics and recommendations
- Version control for templates
- Import/export capabilities

**Template Categories:**
- Data Sync (API to Database, DB to DB)
- Notifications (Multi-channel alerting)
- Webhooks (Receive and process)
- Scheduled Jobs (Cron-based automation)
- AI Pipelines (LLM processing chains)
- ETL (Extract, Transform, Load)

### 5. Workflow Validation
**Purpose:** Ensure workflow structure and configuration integrity before deployment

**Features:**
- Schema validation for all nodes
- Connection graph integrity check
- Credential reference validation
- Expression syntax verification
- Circular dependency detection
- Best practice enforcement

**Validation Rules:**
- All nodes must have required parameters
- Connections must reference existing nodes
- Credentials must exist in n8n
- No orphaned nodes allowed
- Error handlers recommended for production
- Timeout configurations required

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for spec parsing and generation
Container: Docker
n8n Integration: REST API (Port 5678)
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/workflow-builder/
├── workflow_builder.py         # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── node_types.yaml         # Supported n8n node definitions
│   ├── templates.yaml          # Template configurations
│   └── validation_rules.yaml   # Validation rule definitions
├── modules/
│   ├── spec_parser.py          # Natural language spec parsing
│   ├── node_generator.py       # n8n node generation
│   ├── workflow_assembler.py   # Workflow construction
│   ├── test_runner.py          # Workflow testing engine
│   ├── template_manager.py     # Template library management
│   └── validator.py            # Workflow validation
└── tests/
    └── test_workflow_builder.py
```

### Database Schema

```sql
-- Workflow specifications table
CREATE TABLE workflow_specs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    requirements TEXT[] NOT NULL,      -- Array of requirement strings
    status TEXT DEFAULT 'draft',       -- draft, generating, generated, deployed, failed
    generated_workflow_id TEXT,        -- n8n workflow ID after deployment
    spec_hash TEXT,                    -- Hash for change detection
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_specs_status ON workflow_specs(status);
CREATE INDEX idx_specs_created ON workflow_specs(created_at DESC);
CREATE INDEX idx_specs_workflow_id ON workflow_specs(generated_workflow_id);

-- Workflow templates table
CREATE TABLE workflow_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,            -- data_sync, notifications, webhooks, etc.
    description TEXT,
    nodes JSONB NOT NULL,              -- Array of node configurations
    connections JSONB NOT NULL,        -- Connection mappings
    variables TEXT[],                  -- Placeholder variables
    usage_count INTEGER DEFAULT 0,
    rating FLOAT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON workflow_templates(category);
CREATE INDEX idx_templates_usage ON workflow_templates(usage_count DESC);

-- Node patterns table
CREATE TABLE node_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type TEXT NOT NULL,           -- n8n node type identifier
    pattern_name TEXT NOT NULL,
    config_template JSONB NOT NULL,    -- Default configuration template
    description TEXT,
    parameters JSONB,                  -- Parameter definitions
    examples JSONB,                    -- Usage examples
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_patterns_type_name ON node_patterns(node_type, pattern_name);

-- Generation logs table
CREATE TABLE generation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spec_id UUID REFERENCES workflow_specs(id),
    attempt INTEGER NOT NULL,
    result TEXT NOT NULL,              -- success, partial, failed
    workflow_json JSONB,               -- Generated workflow
    errors TEXT[],                     -- Error messages if any
    tokens_used INTEGER,
    model TEXT,                        -- Claude model used
    generation_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gen_logs_spec ON generation_logs(spec_id);
CREATE INDEX idx_gen_logs_result ON generation_logs(result);

-- Test runs table
CREATE TABLE test_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id TEXT NOT NULL,         -- n8n workflow ID
    spec_id UUID REFERENCES workflow_specs(id),
    status TEXT NOT NULL,              -- pending, running, passed, failed
    test_type TEXT DEFAULT 'e2e',      -- unit, integration, e2e, load
    input JSONB,                       -- Test input data
    output JSONB,                      -- Actual output
    expected_output JSONB,             -- Expected output for comparison
    duration_ms INTEGER,
    errors TEXT[],
    node_traces JSONB,                 -- Node-by-node execution trace
    run_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_test_runs_workflow ON test_runs(workflow_id);
CREATE INDEX idx_test_runs_status ON test_runs(status);
CREATE INDEX idx_test_runs_run_at ON test_runs(run_at DESC);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # Generation queue status
GET /metrics             # Prometheus-compatible metrics
```

### Spec to Workflow
```
POST /specs                    # Create new workflow spec
GET /specs                     # List all specs
GET /specs/{id}                # Get spec details
PUT /specs/{id}                # Update spec
DELETE /specs/{id}             # Delete spec
POST /specs/{id}/generate      # Generate workflow from spec
GET /specs/{id}/preview        # Preview generated workflow without saving
```

### Node Generation
```
POST /nodes/generate           # Generate single node from description
GET /nodes/types               # List supported node types
GET /nodes/types/{type}        # Get node type details and parameters
POST /nodes/validate           # Validate node configuration
```

### Workflow Testing
```
POST /test/run                 # Run workflow test
GET /test/runs                 # List test runs
GET /test/runs/{id}            # Get test run details
POST /test/dry-run             # Dry run without saving
POST /test/generate-cases      # AI-generate test cases for workflow
GET /test/coverage/{workflow_id}  # Get test coverage report
```

### Template Library
```
GET /templates                 # List all templates
GET /templates/{id}            # Get template details
POST /templates                # Create new template
PUT /templates/{id}            # Update template
DELETE /templates/{id}         # Delete template
POST /templates/{id}/apply     # Apply template with variables
GET /templates/categories      # List template categories
GET /templates/recommend       # Get recommended templates for use case
```

### Validation
```
POST /validate                 # Validate workflow JSON
POST /validate/connections     # Validate connection graph
POST /validate/credentials     # Validate credential references
GET /validate/rules            # List validation rules
```

### Deployment
```
POST /deploy                   # Deploy workflow to n8n
POST /deploy/preview           # Preview deployment changes
GET /deploy/status/{id}        # Check deployment status
POST /deploy/rollback/{id}     # Rollback deployment
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store workflow generation insights
await aria_store_memory(
    memory_type="fact",
    content=f"Generated workflow '{name}' with {node_count} nodes",
    category="automation",
    source_type="agent_result",
    tags=["workflow-builder", "generation"]
)

# Store template usage patterns
await aria_store_memory(
    memory_type="fact",
    content=f"Template '{template_name}' used {usage_count} times this month",
    category="automation",
    source_type="analytics"
)

# Store generation decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Selected {node_type} for requirement: {requirement}",
    category="automation",
    source_type="ai_decision"
)
```

### ARIA Tool Integration
```python
# Tools exposed to ARIA
tools = [
    {
        "name": "workflow.generate",
        "description": "Generate an n8n workflow from a natural language specification",
        "parameters": {
            "name": "string - workflow name",
            "description": "string - what the workflow does",
            "requirements": "array - list of requirements"
        }
    },
    {
        "name": "workflow.test",
        "description": "Test a workflow with sample data",
        "parameters": {
            "workflow_id": "string - n8n workflow ID",
            "test_data": "object - input data for testing"
        }
    },
    {
        "name": "workflow.template",
        "description": "Get a workflow template by category or name",
        "parameters": {
            "category": "string - template category",
            "name": "string - optional specific template name"
        }
    },
    {
        "name": "workflow.validate",
        "description": "Validate a workflow structure and configuration",
        "parameters": {
            "workflow_json": "object - workflow to validate"
        }
    },
    {
        "name": "workflow.deploy",
        "description": "Deploy a generated workflow to n8n",
        "parameters": {
            "spec_id": "string - spec ID to deploy",
            "activate": "boolean - activate after deploy"
        }
    }
]
```

**Routing Triggers:**
```javascript
const workflowBuilderPatterns = [
  /create (a )?workflow/i,
  /generate (a )?workflow/i,
  /build (a |an )?automation/i,
  /n8n workflow/i,
  /workflow template/i,
  /test (the )?workflow/i,
  /validate workflow/i,
  /deploy workflow/i
];
```

### Event Bus Integration
```python
# Published events
"workflow.generated"          # Workflow successfully generated
"workflow.generation.failed"  # Generation failed
"workflow.deployed"           # Workflow deployed to n8n
"workflow.deployment.failed"  # Deployment failed
"workflow.test.passed"        # Workflow test passed
"workflow.test.failed"        # Workflow test failed
"workflow.validated"          # Workflow validation complete
"template.created"            # New template added
"template.used"               # Template was applied

# Subscribed events
"spec.created"                # New spec to process
"workflow.updated"            # Workflow changed externally
"n8n.workflow.error"          # n8n reported workflow error
"agent.request.automation"    # Automation request from other agent
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("WORKFLOW_BUILDER")

# Log workflow generation costs
await cost_tracker.log_usage(
    endpoint="/specs/{id}/generate",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={
        "spec_id": spec_id,
        "node_count": len(generated_nodes),
        "attempt": attempt_number
    }
)

# Log test generation costs
await cost_tracker.log_usage(
    endpoint="/test/generate-cases",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"workflow_id": workflow_id}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(builder_context: dict) -> str:
    return f"""You are WORKFLOW BUILDER - Master Automation Architect for LeverEdge AI.

Named after Daedalus, the legendary Greek craftsman who built the Labyrinth and invented wondrous devices, you craft intricate automation workflows with precision and ingenuity.

## TIME AWARENESS
- Current: {builder_context['current_time']}
- Days to Launch: {builder_context['days_to_launch']}

## YOUR IDENTITY
You are the automation architect of LeverEdge. You transform ideas into working n8n workflows, turning natural language specifications into precise, tested automation.

## CURRENT STATUS
- Specs in Queue: {builder_context['specs_pending']}
- Workflows Generated Today: {builder_context['generated_today']}
- Templates Available: {builder_context['template_count']}
- Test Pass Rate: {builder_context['test_pass_rate']}%

## YOUR CAPABILITIES

### Spec to Workflow Conversion
- Parse natural language requirements
- Design optimal node configurations
- Generate complete workflow JSON
- Handle complex branching logic
- Support error handling patterns

### Node Generation
- Support all n8n node types
- Configure parameters from context
- Bind credentials appropriately
- Add retry and error handling
- Optimize for performance

### Workflow Testing
- Generate test cases automatically
- Run dry-run validations
- Trace node-by-node execution
- Compare outputs to expectations
- Report coverage metrics

### Template Library
- Maintain reusable patterns
- Recommend templates for use cases
- Support template composition
- Track usage analytics

### Validation
- Check structural integrity
- Validate all connections
- Verify credential references
- Enforce best practices
- Detect circular dependencies

## GENERATION GUIDELINES

When generating workflows:
1. Start with a clear trigger node
2. Add error handling for external calls
3. Use Set nodes to transform data between steps
4. Add logging nodes for debugging
5. End with appropriate output or notification

Node naming conventions:
- Use descriptive names: "Fetch User Data" not "HTTP Request"
- Prefix with action: "Parse JSON Response"
- Include target: "Send Slack Notification"

## TEAM COORDINATION
- Request security review -> CERBERUS
- Store workflow insights -> Unified Memory
- Send deployment alerts -> HERMES
- Publish events -> Event Bus
- Log all costs -> Cost Tracker

## RESPONSE FORMAT
For workflow generation:
1. Requirement analysis
2. Node design rationale
3. Connection mapping
4. Credential requirements
5. Testing recommendations

## YOUR MISSION
Transform automation ideas into reality.
Every workflow must be tested, validated, and production-ready.
Build with the precision of a master craftsman.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with spec management and simple generation

- [ ] Create FastAPI agent structure with health endpoints
- [ ] Implement database schema and migrations
- [ ] Build spec CRUD operations
- [ ] Simple single-node generation from description
- [ ] Basic workflow JSON assembly
- [ ] Deploy and test basic functionality

**Done When:** Can create a spec and generate a simple 2-3 node workflow

### Phase 2: Advanced Generation (Sprint 3-4)
**Goal:** Full multi-node workflow generation with connections

- [ ] Natural language requirement parser
- [ ] Multi-node workflow generation
- [ ] Connection graph builder
- [ ] Expression and variable injection
- [ ] Error handling node insertion
- [ ] Credential placeholder system

**Done When:** Can generate complex workflows with 10+ nodes from specs

### Phase 3: Testing Framework (Sprint 5-6)
**Goal:** Automated workflow testing before deployment

- [ ] Dry-run execution engine
- [ ] Mock data generation
- [ ] Node-by-node tracing
- [ ] Output validation system
- [ ] Test case auto-generation
- [ ] Coverage reporting

**Done When:** All generated workflows pass automated tests before deployment

### Phase 4: Template Library & Deployment (Sprint 7-8)
**Goal:** Reusable templates and production deployment

- [ ] Template CRUD and categories
- [ ] Template recommendation engine
- [ ] Template composition system
- [ ] n8n deployment integration
- [ ] Rollback capability
- [ ] Usage analytics

**Done When:** Templates reduce generation time by 50%, deployments are automated

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 12 | 1-2 |
| Advanced Generation | 6 | 16 | 3-4 |
| Testing Framework | 6 | 14 | 5-6 |
| Template & Deploy | 6 | 12 | 7-8 |
| **Total** | **24** | **54** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Generate valid n8n workflows from natural language specs
- [ ] Support all major n8n node types (HTTP, Database, AI, Logic)
- [ ] Automated testing catches 95%+ of issues before deployment
- [ ] Template library covers 80% of common automation patterns
- [ ] Deployment to n8n completes in < 30 seconds

### Quality
- [ ] 95%+ uptime for agent
- [ ] Generated workflows pass validation 90%+ on first attempt
- [ ] < 2% of deployed workflows fail in production
- [ ] All generated workflows include error handling

### Integration
- [ ] ARIA can request workflow generation via tools
- [ ] Events publish to Event Bus for all state changes
- [ ] Generation insights stored in Unified Memory
- [ ] All LLM costs tracked per generation

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Complex specs fail to generate | User frustration | Iterative generation with clarification requests |
| Generated workflows have bugs | Production failures | Mandatory testing before deployment |
| n8n API changes break integration | Agent dysfunction | Version-locked n8n API, compatibility layer |
| Templates become outdated | Poor recommendations | Usage analytics, regular template audits |
| High token costs for generation | Budget overrun | Caching, template reuse, model tier selection |

---

## GIT COMMIT

```
Add WORKFLOW BUILDER - AI-powered workflow generation agent spec

- Spec to workflow conversion with AI parsing
- Node generation for all n8n node types
- Automated workflow testing framework
- Reusable template library
- Validation and deployment pipeline
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/WORKFLOW-BUILDER.md

Context: Build WORKFLOW BUILDER automation agent. Start with Phase 1 foundation.
```
