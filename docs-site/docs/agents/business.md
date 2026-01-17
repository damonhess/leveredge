# Business Fleet

The Business Fleet provides professional services including project management, legal guidance, financial analysis, and infrastructure advisory.

## Fleet Overview

| Agent | Port | Purpose | Type |
|-------|------|---------|------|
| HERACLES | 8200 | Project Manager | FastAPI (LLM) |
| LIBRARIAN | 8201 | Knowledge Manager | FastAPI (LLM) |
| DAEDALUS | 8202 | Workflow Builder | FastAPI (LLM) |
| THEMIS | 8203 | Legal Advisor | FastAPI (LLM) |
| MENTOR | 8204 | Business Coach | FastAPI (LLM) |
| PLUTUS | 8205 | Financial Analyst | FastAPI (LLM) |
| PROCUREMENT | 8206 | Procurement Expert | FastAPI (LLM) |
| HEPHAESTUS-SERVER | 8207 | Server Admin | FastAPI (LLM) |
| ATLAS-INFRA | 8208 | Infrastructure Advisor | FastAPI (LLM) |
| IRIS | 8209 | World Events Reporter | FastAPI (LLM) |

---

## HERACLES - Project Manager

**Port:** 8200 | **Type:** LLM-Powered

HERACLES provides project planning, task management, and team coordination capabilities.

### Capabilities

- Project planning and tracking
- Task breakdown and estimation
- Sprint management
- Resource allocation
- Timeline creation
- Risk assessment
- Milestone tracking
- Team workload balancing

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/project/create` | POST | Create project plan |
| `/task/breakdown` | POST | Break down task |
| `/sprint/plan` | POST | Plan sprint |
| `/timeline` | POST | Generate timeline |
| `/risks/assess` | POST | Assess project risks |
| `/status` | GET | Project status overview |

### Example Usage

```bash
# Create project plan
curl -X POST http://localhost:8200/project/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Website Redesign",
    "description": "Complete redesign of company website",
    "deadline": "2026-03-15",
    "team_size": 3,
    "constraints": ["budget: $10k", "must maintain SEO"]
  }'

# Break down task
curl -X POST http://localhost:8200/task/breakdown \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Implement user authentication",
    "complexity": "medium",
    "include_estimates": true
  }'
```

---

## LIBRARIAN - Knowledge Manager

**Port:** 8201 | **Type:** LLM-Powered

LIBRARIAN manages document organization, knowledge base curation, and information retrieval.

### Capabilities

- Document organization
- Knowledge base management
- Information retrieval
- Content categorization
- Tag management
- Search optimization
- Archive management
- Documentation generation

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/organize` | POST | Organize documents |
| `/search` | POST | Search knowledge base |
| `/categorize` | POST | Categorize content |
| `/tags/suggest` | POST | Suggest tags |
| `/archive` | POST | Archive old content |
| `/summary` | POST | Generate summary |

### Example Usage

```bash
# Search knowledge base
curl -X POST http://localhost:8201/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "compliance workflow setup",
    "filters": {"category": "technical"},
    "limit": 10
  }'

# Organize documents
curl -X POST http://localhost:8201/organize \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/opt/leveredge/docs",
    "strategy": "by_topic",
    "create_index": true
  }'
```

---

## DAEDALUS - Workflow Builder

**Port:** 8202 | **Type:** LLM-Powered

DAEDALUS designs workflows, automation processes, and integration architectures.

### Capabilities

- Workflow design and automation
- Process optimization
- Integration planning
- n8n workflow creation
- API integration design
- Automation recommendations
- Workflow documentation

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/workflow/design` | POST | Design workflow |
| `/workflow/optimize` | POST | Optimize existing workflow |
| `/integration/plan` | POST | Plan integration |
| `/n8n/generate` | POST | Generate n8n workflow |
| `/automation/recommend` | POST | Recommend automations |

### Example Usage

```bash
# Design workflow
curl -X POST http://localhost:8202/workflow/design \
  -H "Content-Type: application/json" \
  -d '{
    "process": "customer onboarding",
    "steps": [
      "receive signup",
      "verify email",
      "collect info",
      "setup account",
      "send welcome"
    ],
    "integrations_available": ["email", "database", "crm"]
  }'
```

---

## THEMIS - Legal Advisor

**Port:** 8203 | **Type:** LLM-Powered

THEMIS provides legal guidance, contract analysis, and compliance recommendations.

!!! warning "Disclaimer"
    THEMIS provides general legal guidance and information. For binding legal advice, consult a licensed attorney.

### Capabilities

- Contract review and analysis
- Legal compliance guidance
- Risk assessment
- Policy recommendations
- Terms of service review
- Privacy policy analysis
- Regulatory guidance

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/contract/review` | POST | Review contract |
| `/compliance/check` | POST | Compliance assessment |
| `/risk/assess` | POST | Legal risk assessment |
| `/policy/recommend` | POST | Policy recommendations |
| `/terms/analyze` | POST | Analyze terms of service |

### Example Usage

```bash
# Review contract
curl -X POST http://localhost:8203/contract/review \
  -H "Content-Type: application/json" \
  -d '{
    "contract_text": "...",
    "contract_type": "service_agreement",
    "focus_areas": ["liability", "termination", "ip_rights"]
  }'
```

---

## MENTOR - Business Coach

**Port:** 8204 | **Type:** LLM-Powered

MENTOR provides business coaching, career guidance, and leadership development.

### Capabilities

- Business mentorship
- Career guidance
- Leadership development
- Professional growth planning
- Skill assessment
- Goal setting
- Performance improvement

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/coach` | POST | Coaching session |
| `/career/plan` | POST | Career planning |
| `/leadership` | POST | Leadership advice |
| `/goals/set` | POST | Goal setting |
| `/feedback` | POST | Performance feedback |

### Example Usage

```bash
# Coaching session
curl -X POST http://localhost:8204/coach \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "transitioning to management",
    "current_role": "senior developer",
    "challenges": ["delegation", "time management"],
    "goals": ["effective team leadership"]
  }'
```

---

## PLUTUS - Financial Analyst

**Port:** 8205 | **Type:** LLM-Powered

PLUTUS provides financial analysis, budgeting, and investment guidance.

### Capabilities

- Financial analysis
- Budget planning
- Investment guidance
- ROI calculations
- Cash flow projections
- Pricing strategy
- Cost optimization
- Financial reporting

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/analyze` | POST | Financial analysis |
| `/budget/create` | POST | Create budget |
| `/roi/calculate` | POST | Calculate ROI |
| `/cashflow/project` | POST | Cash flow projection |
| `/pricing/strategy` | POST | Pricing strategy |
| `/costs/optimize` | POST | Cost optimization |

### Example Usage

```bash
# Calculate ROI
curl -X POST http://localhost:8205/roi/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "investment": 50000,
    "expected_return": 75000,
    "time_period_months": 12,
    "include_opportunity_cost": true
  }'

# Create budget
curl -X POST http://localhost:8205/budget/create \
  -H "Content-Type: application/json" \
  -d '{
    "period": "quarterly",
    "categories": ["engineering", "marketing", "operations"],
    "total_available": 100000,
    "priorities": ["product development", "customer acquisition"]
  }'
```

---

## PROCUREMENT - Procurement Expert

**Port:** 8206 | **Type:** LLM-Powered

PROCUREMENT handles vendor evaluation, purchase recommendations, and cost negotiations.

### Capabilities

- Vendor evaluation
- Purchase recommendations
- Contract negotiation support
- Cost optimization
- Supplier comparison
- RFP creation
- Vendor management

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/vendor/evaluate` | POST | Evaluate vendor |
| `/purchase/recommend` | POST | Purchase recommendation |
| `/compare` | POST | Compare suppliers |
| `/rfp/create` | POST | Create RFP |
| `/negotiate/strategy` | POST | Negotiation strategy |

### Example Usage

```bash
# Evaluate vendor
curl -X POST http://localhost:8206/vendor/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_name": "CloudProvider Inc",
    "product_category": "cloud hosting",
    "criteria": ["cost", "reliability", "support", "scalability"],
    "budget_range": {"min": 500, "max": 2000}
  }'
```

---

## HEPHAESTUS-SERVER - Server Admin

**Port:** 8207 | **Type:** LLM-Powered

HEPHAESTUS-SERVER provides server administration guidance and infrastructure management recommendations.

### Capabilities

- Server management guidance
- Infrastructure recommendations
- DevOps best practices
- System administration tasks
- Performance tuning
- Security hardening
- Monitoring setup

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/diagnose` | POST | Diagnose server issues |
| `/optimize` | POST | Optimization recommendations |
| `/security/harden` | POST | Security hardening guide |
| `/monitoring/setup` | POST | Monitoring recommendations |
| `/backup/strategy` | POST | Backup strategy |

---

## ATLAS-INFRA - Infrastructure Advisor

**Port:** 8208 | **Type:** LLM-Powered

ATLAS-INFRA provides cloud architecture guidance, scaling recommendations, and infrastructure cost optimization.

### Capabilities

- Cloud architecture guidance
- Infrastructure planning
- Scaling recommendations
- Cost optimization
- Migration planning
- Multi-cloud strategy
- Disaster recovery planning

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/architecture/design` | POST | Design architecture |
| `/scale/plan` | POST | Scaling plan |
| `/costs/optimize` | POST | Cost optimization |
| `/migrate/plan` | POST | Migration planning |
| `/dr/plan` | POST | Disaster recovery plan |

### Example Usage

```bash
# Design architecture
curl -X POST http://localhost:8208/architecture/design \
  -H "Content-Type: application/json" \
  -d '{
    "workload": "web application",
    "expected_traffic": "10k requests/minute",
    "budget": "moderate",
    "requirements": ["high availability", "auto-scaling"],
    "cloud_provider": "aws"
  }'
```

---

## IRIS - World Events Reporter

**Port:** 8209 | **Type:** LLM-Powered

IRIS monitors and reports on current events, industry trends, and market news.

### Capabilities

- News and current events
- Industry trend analysis
- Market updates
- Competitive intelligence
- Event summarization
- Alert monitoring
- Report generation

### Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/news/latest` | GET | Latest news |
| `/trends/industry` | POST | Industry trends |
| `/market/update` | GET | Market updates |
| `/intelligence` | POST | Competitive intelligence |
| `/summary` | POST | Event summary |
| `/alerts` | GET | Active alerts |

### Example Usage

```bash
# Get industry trends
curl -X POST http://localhost:8209/trends/industry \
  -H "Content-Type: application/json" \
  -d '{
    "industry": "compliance software",
    "timeframe": "last 30 days",
    "focus_areas": ["regulations", "technology", "market"]
  }'

# Competitive intelligence
curl -X POST http://localhost:8209/intelligence \
  -H "Content-Type: application/json" \
  -d '{
    "competitors": ["Hyperproof", "Vanta", "Drata"],
    "aspects": ["pricing", "features", "funding"]
  }'
```

---

## Fleet Integration

All Business Fleet agents integrate through the Event Bus for coordinated operations:

```
HERACLES (Project) → PLUTUS (Budget) → PROCUREMENT (Vendors) → DAEDALUS (Workflows)
         ↓
    LIBRARIAN (Documentation) → THEMIS (Compliance)
```

### Cross-Agent Workflows

| Workflow | Agents | Purpose |
|----------|--------|---------|
| Project Kickoff | HERACLES → PLUTUS → PROCUREMENT | Plan, budget, vendor selection |
| Compliance Audit | THEMIS → LIBRARIAN → IRIS | Review, document, monitor |
| Infrastructure Scaling | ATLAS-INFRA → HEPHAESTUS-SERVER → PLUTUS | Plan, implement, cost |
