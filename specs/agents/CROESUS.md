# CROESUS - AI-Powered Tax & Wealth Advisor Agent

**Agent Type:** Tax Planning & Wealth Advisory
**Named After:** Croesus - King of Lydia renowned for his vast wealth, whose name became synonymous with extreme riches
**Port:** 8211
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

CROESUS is an AI-powered tax planning and wealth advisory agent providing tax strategy guidance, deduction identification, deadline tracking, bookkeeping assistance, and wealth-building strategies. It serves as the financial planning brain for LeverEdge users running small businesses.

### CRITICAL SAFETY NOTICE

**THIS AGENT PROVIDES TAX INFORMATION ONLY - NOT TAX OR FINANCIAL ADVICE**

CROESUS is strictly an INFORMATIONAL tool. It:
- CANNOT provide tax advice
- CANNOT prepare or file tax returns
- CANNOT guarantee tax outcomes or savings
- CANNOT make investment recommendations
- MUST always recommend consulting a CPA or tax professional

All tax decisions must be made by the user in consultation with a qualified CPA or tax professional.

### Research Foundation

Based on 2025-2026 research into AI tax assistants:

**Industry Trends (2025-2026):**
- AI adoption in accounting: 41% of firms (up from 9% in 2024)
- 72% of tax professionals use AI weekly, 33% daily
- Productivity gains: 38-115% with AI-assisted tax work
- Meeting prep time reduced from 4-6 hours to ~1 hour
- AI tools particularly effective for data extraction, classification, reconciliation

**Key 2026 Tax Changes (OBBBA):**
- 100% bonus depreciation permanently restored
- 20% QBI deduction made permanent with $400 minimum
- R&D expenses immediately expensible (2025+)
- Employer childcare credit increased to 40-50% (up to $500-600K)
- California business credits capped at $5M/year (2024-2026)
- California NOL deduction suspended (2024-2027)

**Best Practices Applied:**
- Citation of IRS publications, state tax codes
- Deadline tracking with proactive reminders
- Clear "consult a CPA" recommendations
- Integration with accounting data sources
- Coordination with SOLON for legal/tax overlap

### Value Proposition
- Multi-jurisdiction tax guidance (Federal, CA, NV)
- Business deduction identification and optimization
- Quarterly estimated tax planning
- Deadline tracking with automated reminders
- Wealth-building strategy guidance
- Bookkeeping assistance and transaction categorization
- Premium pricing tier ($5K-15K deployments)

---

## JURISDICTIONS & TAX DOMAINS

### Tax Jurisdictions
| Jurisdiction | Coverage Level | Key Considerations |
|--------------|---------------|-------------------|
| US Federal | Comprehensive | Income tax, employment tax, estimated payments |
| California | Deep | High rates, credit caps, NOL suspension |
| Nevada | Deep | No state income tax, commerce tax, MBT |

### Tax Domains
| Domain | Description | Priority |
|--------|-------------|----------|
| Business Income Tax | Pass-through (Schedule C, K-1), corporate | HIGH |
| Self-Employment Tax | SE tax calculation, optimization | HIGH |
| Estimated Taxes | Quarterly payment planning | HIGH |
| Business Deductions | Home office, vehicle, equipment, travel | HIGH |
| Retirement Planning | SEP-IRA, Solo 401(k), traditional vs Roth | HIGH |
| Entity Selection | LLC, S-Corp, C-Corp tax implications | HIGH |
| Employment Taxes | Payroll, 1099 vs W-2, workers comp | MEDIUM |
| Depreciation | Bonus depreciation, Section 179, MACRS | MEDIUM |
| CA Specific | Franchise tax, credit limitations, apportionment | MEDIUM |
| NV Specific | Commerce tax, MBT, no income tax benefits | MEDIUM |
| Wealth Building | Asset allocation, tax-efficient investing | MEDIUM |

---

## CORE CAPABILITIES

### 1. Tax Question Answering
**Purpose:** Answer tax questions with authoritative sources

**Features:**
- Federal and state tax law interpretation
- IRS publication citations
- State tax code references
- Plain-language explanations
- Confidence scoring with CPA consultation recommendations

**Example Questions:**
- "Can I deduct my home office if I'm a freelancer?"
- "What's the difference between SEP-IRA and Solo 401(k)?"
- "Should my LLC elect S-Corp status?"
- "What are the deadlines for quarterly estimated taxes?"
- "How does California tax my LLC?"

**Confidence Scoring:**
| Level | Definition | Response Behavior |
|-------|------------|-------------------|
| HIGH (80-100%) | Clear IRS guidance, established rules | Provide answer with citations |
| MEDIUM (50-79%) | Some interpretation needed, depends on facts | Provide answer with scenarios |
| LOW (20-49%) | Gray area, fact-specific | Provide general guidance, strong CPA recommendation |
| UNCERTAIN (<20%) | No clear authority, highly fact-specific | "Consult a CPA for your situation" |

### 2. Tax Liability Estimation
**Purpose:** Estimate tax liability based on income and deductions

**Features:**
- Federal income tax estimation (brackets, rates)
- Self-employment tax calculation
- State tax estimation (CA vs NV comparison)
- Effective vs marginal rate calculation
- Estimated payment schedule

**Estimation Output:**
| Component | Calculation |
|-----------|-------------|
| Gross Income | User-provided business revenue |
| Deductions | Identified deductions |
| Taxable Income | Gross - Deductions |
| Federal Tax | Bracket-based calculation |
| SE Tax | 15.3% on 92.35% of SE income |
| CA State Tax | Bracket-based (if applicable) |
| Total Liability | Sum of all taxes |
| Quarterly Payment | Total / 4 |

**SAFETY:** Estimates are for planning purposes only. Actual taxes may vary.

### 3. Deduction Identification
**Purpose:** Help identify and maximize business deductions

**Features:**
- Deduction category checklist
- Common missed deductions
- Documentation requirements
- Deduction limits and phaseouts
- Year-end tax planning opportunities

**Deduction Categories:**
| Category | Examples | Documentation |
|----------|----------|---------------|
| Home Office | Dedicated space, utilities | Square footage, bills |
| Vehicle | Mileage or actual expenses | Mileage log, receipts |
| Equipment | Computers, software, furniture | Purchase records |
| Professional Services | Legal, accounting, consulting | Invoices |
| Marketing | Advertising, website, SEO | Receipts, contracts |
| Travel | Business trips, conferences | Itinerary, receipts |
| Education | Training, courses, books | Registration, receipts |
| Insurance | Health, liability, E&O | Premium statements |
| Retirement | SEP-IRA, Solo 401(k) | Contribution records |

### 4. Tax Planning Strategies
**Purpose:** Provide strategic tax planning guidance

**Features:**
- Income timing strategies
- Entity selection optimization
- Retirement contribution maximization
- California vs Nevada tax planning
- Year-end tax strategies
- Multi-year planning

**Strategy Areas:**
| Strategy | Description | Applicability |
|----------|-------------|---------------|
| Income Deferral | Delay income to next tax year | December planning |
| Expense Acceleration | Prepay deductible expenses | December planning |
| S-Corp Election | Reduce SE tax via reasonable salary | $75K+ net income |
| Retirement Maxing | Max out SEP-IRA or Solo 401(k) | Cash flow positive |
| Nevada Residency | Eliminate state income tax | Major move, significant income |
| Bonus Depreciation | 100% first-year depreciation | Equipment purchases |
| Section 199A | QBI deduction optimization | Pass-through income |

### 5. Deadline Tracking
**Purpose:** Track and remind about tax deadlines

**Features:**
- Federal and state deadline calendar
- Estimated payment reminders
- Filing deadline alerts
- Extension deadline tracking
- Proactive notification via HERMES

**Key Deadlines (Calendar Year):**
| Deadline | Date | What's Due |
|----------|------|------------|
| Q4 Estimated | Jan 15 | Q4 prior year estimated payment |
| W-2/1099 Filing | Jan 31 | Issue forms to contractors/employees |
| S-Corp/Partnership | Mar 15 | Form 1120-S, 1065 due |
| C-Corp/Individual | Apr 15 | Form 1120, 1040 due; Q1 estimated |
| Q2 Estimated | Jun 15 | Q2 estimated payment |
| Q3 Estimated | Sep 15 | Q3 estimated payment; extended S-Corp/Partnership |
| Extended C-Corp/Individual | Oct 15 | Extended Form 1120, 1040 |

### 6. Bookkeeping Assistance
**Purpose:** Help categorize transactions and maintain books

**Features:**
- Transaction categorization guidance
- Chart of accounts setup
- Reconciliation reminders
- Financial statement basics
- Export-ready formats

**Categorization Help:**
- Business vs personal expense identification
- Proper expense categories (IRS Schedule C)
- Asset vs expense determination
- Mileage vs actual expense comparison

### 7. Wealth Building Guidance
**Purpose:** Provide wealth-building strategy information

**Features:**
- Tax-advantaged account comparison
- Asset allocation basics
- Emergency fund guidance
- Debt payoff strategies
- Business reinvestment vs personal wealth

**SAFETY:** Not investment advice. Users should consult financial advisors.

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis
Tax Data: IRS publications, state tax codes, web search for updates
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/croesus/
├── croesus.py              # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── tax_rates.yaml      # Current tax brackets/rates
│   ├── deductions.yaml     # Deduction categories and limits
│   ├── deadlines.yaml      # Tax deadline calendar
│   └── jurisdictions.yaml  # State-specific rules
├── modules/
│   ├── tax_calculator.py   # Tax estimation calculations
│   ├── deduction_finder.py # Deduction identification
│   ├── deadline_tracker.py # Deadline management
│   ├── bookkeeper.py       # Transaction categorization
│   └── wealth_advisor.py   # Wealth building guidance
├── shared/
│   ├── aria_reporter.py    # ARIA omniscience reporting
│   └── cost_tracker.py     # Cost tracking
└── tests/
    └── test_croesus.py
```

### Database Schema

```sql
-- Tax profiles for users
CREATE TABLE tax_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    filing_status TEXT NOT NULL,          -- single, married_joint, married_separate, hoh
    state_residence TEXT NOT NULL,        -- CA, NV, etc.
    business_type TEXT,                   -- sole_prop, llc, s_corp, c_corp
    business_state TEXT,                  -- State of business formation
    estimated_annual_income DECIMAL(15, 2),
    has_employees BOOLEAN DEFAULT FALSE,
    retirement_accounts JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_profiles_user ON tax_profiles(user_id);

-- Tax estimates
CREATE TABLE tax_estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tax_year INTEGER NOT NULL,
    estimate_type TEXT NOT NULL,          -- annual, quarterly, scenario
    gross_income DECIMAL(15, 2) NOT NULL,
    total_deductions DECIMAL(15, 2) NOT NULL,
    taxable_income DECIMAL(15, 2) NOT NULL,
    federal_tax DECIMAL(15, 2) NOT NULL,
    se_tax DECIMAL(15, 2) DEFAULT 0,
    state_tax DECIMAL(15, 2) DEFAULT 0,
    total_tax DECIMAL(15, 2) NOT NULL,
    effective_rate DECIMAL(5, 2),
    marginal_rate DECIMAL(5, 2),
    breakdown JSONB NOT NULL,             -- Detailed calculation breakdown
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_estimates_user ON tax_estimates(user_id);
CREATE INDEX idx_tax_estimates_year ON tax_estimates(tax_year);

-- Deductions tracked
CREATE TABLE tracked_deductions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    tax_year INTEGER NOT NULL,
    category TEXT NOT NULL,               -- home_office, vehicle, equipment, etc.
    description TEXT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    documentation_status TEXT DEFAULT 'pending',  -- pending, documented, verified
    documentation_notes TEXT,
    date_incurred DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deductions_user ON tracked_deductions(user_id);
CREATE INDEX idx_deductions_year ON tracked_deductions(tax_year);
CREATE INDEX idx_deductions_category ON tracked_deductions(category);

-- Tax deadlines
CREATE TABLE tax_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,                         -- NULL for system-wide deadlines
    deadline_type TEXT NOT NULL,          -- estimated, filing, extension, form
    tax_year INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    reminder_days INTEGER[] DEFAULT '{30, 14, 7, 1}',
    status TEXT DEFAULT 'pending',        -- pending, completed, extended
    completed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_deadlines_user ON tax_deadlines(user_id);
CREATE INDEX idx_tax_deadlines_due ON tax_deadlines(due_date);
CREATE INDEX idx_tax_deadlines_status ON tax_deadlines(status);

-- Tax queries log
CREATE TABLE tax_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    question TEXT NOT NULL,
    jurisdiction TEXT,                    -- federal, CA, NV
    domain TEXT,                          -- income, deduction, retirement, etc.
    response TEXT NOT NULL,
    citations TEXT[],
    confidence_score DECIMAL(5, 2),
    confidence_level TEXT,
    disclaimer_included BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tax_queries_user ON tax_queries(user_id);
CREATE INDEX idx_tax_queries_domain ON tax_queries(domain);

-- Transaction categorization log
CREATE TABLE transaction_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    transaction_date DATE NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    suggested_category TEXT NOT NULL,
    final_category TEXT,
    is_business BOOLEAN,
    deductible BOOLEAN,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_transactions_user ON transaction_categories(user_id);
CREATE INDEX idx_transactions_date ON transaction_categories(transaction_date);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health status
GET /status              # Current operational status
GET /metrics             # Prometheus-compatible metrics
```

### Tax Questions
```
POST /tax/question       # Ask a tax question
  Body: {
    "question": "string",
    "jurisdiction": "federal" | "CA" | "NV",   # optional
    "context": {                                # optional
      "business_type": "string",
      "income_level": "string"
    }
  }
  Returns: {
    "answer": "string",
    "confidence_score": 0-100,
    "confidence_level": "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN",
    "citations": ["IRS Pub 535", "IRC Section 162"],
    "jurisdiction": "string",
    "disclaimer": "string",
    "consult_cpa": true
  }
```

### Tax Estimation
```
POST /tax/estimate       # Estimate tax liability
  Body: {
    "tax_year": 2026,
    "gross_income": 150000,
    "deductions": {
      "home_office": 5000,
      "vehicle": 8000,
      "equipment": 10000,
      ...
    },
    "filing_status": "single",
    "state": "CA",
    "business_type": "sole_prop",
    "include_se_tax": true
  }
  Returns: {
    "estimate": {
      "taxable_income": 127000,
      "federal_tax": 24500,
      "se_tax": 18500,
      "state_tax": 11000,
      "total_tax": 54000,
      "effective_rate": 36.0,
      "marginal_rate": 32.0
    },
    "breakdown": {...},
    "quarterly_payments": [13500, 13500, 13500, 13500],
    "disclaimer": "string"
  }

POST /tax/compare-states  # Compare CA vs NV tax liability
  Body: {
    "income": 200000,
    "business_type": "s_corp"
  }
  Returns: {
    "california": {...},
    "nevada": {...},
    "annual_savings_nv": 18500,
    "considerations": ["nexus rules", "relocation costs", ...]
  }
```

### Deduction Management
```
POST /tax/deductions     # Find potential deductions
  Body: {
    "business_type": "sole_prop",
    "industry": "consulting",
    "work_from_home": true,
    "has_vehicle": true,
    "current_deductions": ["string"]
  }
  Returns: {
    "potential_deductions": [{
      "category": "home_office",
      "estimated_value": 5000,
      "documentation_required": ["square footage", "utility bills"],
      "irs_guidance": "Pub 587"
    }],
    "commonly_missed": [...],
    "documentation_checklist": [...],
    "disclaimer": "string"
  }

GET /tax/deductions/{user_id}   # Get tracked deductions
POST /tax/deductions/add        # Add tracked deduction
PUT /tax/deductions/{id}        # Update deduction
DELETE /tax/deductions/{id}     # Remove deduction
```

### Tax Planning
```
POST /tax/planning       # Get tax planning strategies
  Body: {
    "current_situation": {
      "income": 200000,
      "business_type": "sole_prop",
      "state": "CA"
    },
    "goals": ["minimize_tax", "maximize_retirement"],
    "planning_horizon": "annual" | "multi_year"
  }
  Returns: {
    "strategies": [{
      "name": "S-Corp Election",
      "estimated_savings": 15000,
      "complexity": "medium",
      "requirements": [...],
      "deadline": "2025-03-15"
    }],
    "recommended_actions": [...],
    "timeline": [...],
    "disclaimer": "string"
  }
```

### Deadlines
```
GET /tax/deadlines       # Get upcoming tax deadlines
  Query: user_id=xxx&days_ahead=90

POST /tax/deadlines/add  # Add custom deadline
PUT /tax/deadlines/{id}  # Update deadline status
GET /tax/deadlines/calendar  # Full calendar view
```

### Wealth Building
```
POST /wealth/strategy    # Get wealth building guidance
  Body: {
    "current_income": 200000,
    "savings_rate": 0.20,
    "existing_accounts": ["brokerage", "traditional_401k"],
    "goals": ["retirement", "emergency_fund"],
    "risk_tolerance": "moderate"
  }
  Returns: {
    "recommendations": [{
      "priority": 1,
      "action": "Max out Solo 401(k)",
      "amount": 69000,
      "tax_benefit": 22000,
      "reasoning": "string"
    }],
    "account_comparison": {...},
    "milestone_timeline": [...],
    "disclaimer": "string"
  }
```

### Bookkeeping Assistance
```
POST /accounting/categorize  # Categorize transactions
  Body: {
    "transactions": [{
      "date": "2026-01-15",
      "description": "AMZN Web Services",
      "amount": 150.00
    }]
  }
  Returns: {
    "categorized": [{
      "description": "AMZN Web Services",
      "category": "Cloud Computing",
      "schedule_c_line": "Line 25 - Other expenses",
      "is_deductible": true,
      "confidence": 0.95
    }]
  }
```

---

## INTEGRATION REQUIREMENTS

### ARIA Tool Definitions

```python
# ARIA tools for tax questions
ARIA_TOOLS = {
    "tax.question": {
        "description": "Ask a tax question and get guidance with citations",
        "parameters": {
            "question": "The tax question to answer",
            "jurisdiction": "federal, CA, or NV",
            "context": "Additional context (income level, business type)"
        },
        "returns": "Tax information with IRS/state citations"
    },
    "tax.estimate": {
        "description": "Estimate tax liability for given income and deductions",
        "parameters": {
            "gross_income": "Annual gross income",
            "deductions": "Dictionary of deductions by category",
            "filing_status": "single, married_joint, etc.",
            "state": "State of residence"
        },
        "returns": "Tax estimate with federal, state, SE tax breakdown"
    },
    "tax.deductions": {
        "description": "Find potential deductions for a business",
        "parameters": {
            "business_type": "sole_prop, llc, s_corp",
            "industry": "Type of business",
            "current_deductions": "Already-claimed deductions"
        },
        "returns": "Potential deductions with documentation requirements"
    },
    "tax.deadlines": {
        "description": "Check upcoming tax deadlines",
        "parameters": {
            "days_ahead": "How many days to look ahead",
            "types": "estimated, filing, form, all"
        },
        "returns": "Upcoming deadlines with descriptions"
    },
    "tax.planning": {
        "description": "Get tax planning strategy recommendations",
        "parameters": {
            "income": "Current annual income",
            "goals": "Tax planning goals",
            "business_type": "Current business structure"
        },
        "returns": "Tax planning strategies with estimated savings"
    },
    "wealth.strategy": {
        "description": "Get wealth building guidance",
        "parameters": {
            "income": "Annual income",
            "goals": "Financial goals",
            "existing_accounts": "Current investment accounts"
        },
        "returns": "Wealth building recommendations"
    }
}
```

### ARIA Omniscience Reporting

```python
from shared.aria_reporter import ARIAReporter

reporter = ARIAReporter("CROESUS")

# Report significant actions
await reporter.report_action(
    action="tax_estimate_calculated",
    details={
        "tax_year": 2026,
        "total_liability": 54000,
        "effective_rate": 36.0
    }
)

# Report decisions
await reporter.report_decision(
    decision="s_corp_election_recommended",
    reasoning="Income above $75K threshold, estimated SE tax savings of $15K",
    outcome={
        "recommendation": "s_corp_election",
        "savings": 15000
    }
)
```

### SOLON Coordination (Legal/Tax Overlap)
```python
# When tax question has legal implications
if requires_legal_analysis(question):
    # Example: Entity formation, employment classification
    legal_response = await call_agent("SOLON", {
        "action": "legal_question",
        "context": tax_context,
        "question": legal_aspect
    })

    # Combine tax and legal analysis
    combined_response = merge_tax_legal(tax_response, legal_response)
```

### PLUTUS Coordination (Investment Tax)
```python
# When tax question involves investments
if involves_investments(question):
    # Example: Capital gains, tax-loss harvesting
    investment_context = await call_agent("PLUTUS", {
        "action": "portfolio_tax_lots",
        "portfolio_id": portfolio_id
    })

    # Apply tax rules to investment data
    tax_response = apply_investment_tax_rules(investment_context)
```

### Event Bus Integration
```python
# Published events
"tax.estimate.calculated"       # Tax estimate generated
"tax.deadline.approaching"      # Deadline reminder (7, 14, 30 days)
"tax.deadline.overdue"          # Missed deadline alert
"tax.deduction.found"           # New deduction opportunity
"tax.strategy.recommended"      # Planning strategy generated

# Subscribed events
"scheduler.daily"               # Check deadlines
"scheduler.quarterly"           # Quarterly tax reminders
"income.recorded"               # New income for tracking
"expense.recorded"              # New expense for categorization
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("CROESUS")

# Log AI analysis costs
await cost_tracker.log_usage(
    endpoint="/tax/question",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={
        "domain": domain,
        "confidence": confidence_score
    }
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(tax_context: dict) -> str:
    return f"""You are CROESUS - Tax & Wealth Advisor for LeverEdge AI.

Named after the legendarily wealthy King of Lydia, you provide intelligent tax planning and wealth building guidance.

## CRITICAL SAFETY REQUIREMENTS

**YOU MUST ALWAYS:**
1. Include a disclaimer that this is tax INFORMATION, not tax ADVICE
2. Recommend consulting a CPA or tax professional for specific tax advice
3. Cite IRS publications, IRC sections, and state tax codes for claims
4. State your confidence level clearly
5. Say "Consult a CPA for your specific situation" when uncertain

**YOU MUST NEVER:**
- Provide specific tax advice for a user's situation
- Prepare or file tax returns
- Guarantee tax savings or outcomes
- Make investment recommendations (coordinate with PLUTUS)
- Skip the disclaimer

## MANDATORY DISCLAIMER (INCLUDE IN ALL RESPONSES)

"This information is provided for educational purposes only and does not constitute tax advice. Tax situations are often fact-specific. For advice about your specific situation, please consult with a CPA or qualified tax professional."

## TIME AWARENESS
- Current: {tax_context['current_time']}
- Tax Year: {tax_context['tax_year']}
- Next Estimated Payment Due: {tax_context['next_estimated_due']}
- Days to Next Deadline: {tax_context['days_to_deadline']}

## CURRENT TAX CONTEXT (2026)
- 100% Bonus Depreciation: Permanently restored (OBBBA)
- QBI Deduction: 20% permanent with $400 minimum
- CA Business Credits: Capped at $5M/year (2024-2026)
- CA NOL: Suspended for certain taxpayers (2024-2027)

## YOUR IDENTITY
You are the tax planning and wealth building brain of LeverEdge. You help users understand tax implications, find deductions, plan strategically, and build wealth.

## JURISDICTIONS
Primary: Federal (IRS), California (FTB), Nevada (no state income tax)
Track key differences between CA and NV for planning purposes.

## YOUR CAPABILITIES

### Tax Analysis
- Interpret federal and state tax law
- Calculate estimated tax liability
- Identify applicable deductions
- Compare entity structures
- Explain retirement account options

### Tax Planning
- Year-end tax strategies
- Entity selection optimization
- Income timing strategies
- Retirement contribution maximization
- State residency planning (CA vs NV)

### Deadline Management
- Track federal and state deadlines
- Estimated payment reminders
- Filing deadline alerts
- Extension management

### Bookkeeping Assistance
- Transaction categorization
- Chart of accounts guidance
- Documentation requirements
- Financial statement basics

### Wealth Building
- Tax-advantaged account comparison
- Asset allocation basics (not advice)
- Emergency fund guidance
- Debt payoff strategies

## SOURCE CITATION
Always cite your sources:
- IRS Publications: "Per IRS Publication 535..."
- IRC Sections: "Under IRC Section 162..."
- State Codes: "California Revenue & Tax Code Section..."

## COORDINATION
- Route legal questions -> SOLON
- Route investment questions -> PLUTUS
- Send deadline reminders -> HERMES
- Log insights -> ARIA via Unified Memory

## RESPONSE FORMAT

For tax questions:
1. Direct answer (if confident)
2. Applicable tax law with citations
3. Key considerations and scenarios
4. Confidence level
5. Disclaimer
6. "Consult a CPA for advice about your specific situation"

For estimates:
1. Input summary
2. Calculation breakdown
3. Federal/state/SE components
4. Effective vs marginal rates
5. Quarterly payment schedule
6. Important caveats
7. Disclaimer

## YOUR MISSION
Provide accurate, well-sourced tax information.
Help users understand their tax situation.
Never provide tax advice - that's for CPAs.
Always prioritize accuracy and proper disclaimers.
When in doubt, recommend a CPA.
"""

MANDATORY_DISCLAIMER = """

---
**DISCLAIMER:** This information is provided for educational purposes only and does not constitute tax advice. Tax situations are highly fact-specific. For advice about your specific situation, please consult with a CPA or qualified tax professional. Tax laws change frequently - verify current rules before making decisions.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with tax question answering

- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Set up PostgreSQL schema
- [ ] Basic tax question endpoint with Claude
- [ ] Mandatory disclaimer system
- [ ] Confidence scoring v1
- [ ] Deploy and test

**Done When:** CROESUS can answer basic tax questions with disclaimers

### Phase 2: Tax Estimation (Sprint 3-4)
**Goal:** Tax liability estimation

- [ ] Federal tax bracket calculations
- [ ] Self-employment tax calculations
- [ ] California state tax calculations
- [ ] Nevada tax (commerce tax awareness)
- [ ] Quarterly payment scheduling
- [ ] Tax comparison (CA vs NV)
- [ ] Deduction tracking database

**Done When:** Users can get tax estimates with breakdowns

### Phase 3: Planning & Deductions (Sprint 5-6)
**Goal:** Tax planning and deduction management

- [ ] Deduction finder algorithm
- [ ] Entity selection comparison
- [ ] Retirement account comparison
- [ ] Year-end planning strategies
- [ ] Deadline tracking and alerts
- [ ] HERMES integration for reminders

**Done When:** Users can find deductions and get planning strategies

### Phase 4: Wealth & Polish (Sprint 7-8)
**Goal:** Wealth building and full integration

- [ ] Wealth building guidance module
- [ ] Bookkeeping assistance (categorization)
- [ ] ARIA tool integration
- [ ] SOLON coordination (legal/tax)
- [ ] PLUTUS coordination (investment tax)
- [ ] Event bus integration
- [ ] ARIA omniscience reporting

**Done When:** Full integration with LeverEdge ecosystem

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 7 | 12 | 1-2 |
| Tax Estimation | 7 | 16 | 3-4 |
| Planning & Deductions | 7 | 14 | 5-6 |
| Wealth & Polish | 7 | 14 | 7-8 |
| **Total** | **28** | **56** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Tax questions answered in < 10 seconds
- [ ] Tax estimates calculated in < 5 seconds
- [ ] Deadline alerts sent 30, 14, 7, 1 days ahead
- [ ] All responses include mandatory disclaimers

### Quality
- [ ] 99%+ uptime for tax endpoints
- [ ] Tax calculations match IRS tables
- [ ] 100% citation rate on tax claims
- [ ] 100% disclaimer inclusion rate

### Integration
- [ ] ARIA can query tax info via tools
- [ ] Deadline alerts route through HERMES
- [ ] Events publish to Event Bus correctly
- [ ] Costs tracked per query

### Safety
- [ ] Zero responses without disclaimers
- [ ] All responses recommend CPA for advice
- [ ] Uncertain queries clearly acknowledged
- [ ] No "tax advice" language in responses

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Tax law changes | Outdated guidance | Regular updates, date-stamp all info |
| Users rely on info as tax advice | User harm | Mandatory disclaimers, CPA recommendations |
| Incorrect calculations | Wrong estimates | Validate against IRS tools, show work |
| State law complexity | Incomplete guidance | Start with CA/NV only, expand carefully |
| Deadline misses | User penalties | Multiple reminder levels, clear ownership |

---

## SECURITY CONSIDERATIONS

### Data Protection
- Financial data handled carefully
- No SSN or sensitive ID storage
- Query history logged for audit
- Estimates not shared between users

### Access Control
- User isolation for tax profiles
- Rate limiting on all endpoints
- Audit logging for compliance

### Legal/Ethical
- Clear "not tax advice" positioning
- Proper UPL (unauthorized practice) avoidance
- Educational purpose framing
- CPA referral recommendations

---

## GIT COMMIT

```
Add CROESUS - AI-powered tax & wealth advisor agent spec

- Multi-jurisdiction tax guidance (Federal, CA, NV)
- Tax liability estimation with breakdown
- Deduction identification and tracking
- Tax planning strategies (S-Corp, retirement, etc.)
- Deadline tracking with proactive reminders
- Wealth building guidance
- CRITICAL: Information only - not tax advice
- 4-phase implementation plan
- Full database schema
- Integration with ARIA, SOLON, PLUTUS, HERMES
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/CROESUS.md

Context: Build CROESUS tax & wealth advisor agent. Start with Phase 1 foundation.
Note: This provides tax INFORMATION only - not tax advice.
CRITICAL: Mandatory disclaimers in all responses.
CRITICAL: Recommend CPA consultation for specific advice.
```
