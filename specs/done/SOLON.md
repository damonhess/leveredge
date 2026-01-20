# SOLON - AI-Powered Legal Advisor Agent

**Agent Type:** Legal Research & Compliance Advisory
**Named After:** Solon - Athenian statesman, lawmaker, and poet credited with laying the foundations of Athenian democracy
**Port:** 8210
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

SOLON is an AI-powered legal research and advisory agent providing jurisdiction-specific legal information, contract analysis, compliance checking, and general legal research. It serves as the legal intelligence brain for LeverEdge users requiring legal information and guidance.

### CRITICAL SAFETY NOTICE

**THIS AGENT PROVIDES LEGAL INFORMATION ONLY - NOT LEGAL ADVICE**

SOLON is strictly an INFORMATIONAL tool. It:
- CANNOT provide legal advice
- CANNOT establish attorney-client privilege
- CANNOT represent you in legal proceedings
- CANNOT guarantee legal outcomes
- MUST always recommend consulting a licensed attorney

All legal decisions must be made by the user in consultation with a qualified attorney.

### Research Foundation

Based on 2025-2026 research into AI legal assistants:

**Hallucination Rates:**
- General-purpose LLMs (GPT-4): 58-82% error rate on legal queries
- Specialized legal RAG systems (Lexis+ AI): 17-33% hallucination rate, 65% accuracy
- Combined RAG + RLHF + guardrails: up to 96% hallucination reduction vs baseline

**Best Practices Applied:**
- RAG architecture with authoritative legal sources
- Mandatory source citation for all claims
- Confidence scoring with explicit uncertainty acknowledgment
- "I don't know, consult an attorney" default for uncertain queries
- Multi-layer verification: retrieval validation, source checking, consistency analysis

**Legal Data Sources:**
- [CourtListener / Free Law Project](https://www.courtlistener.com/) - 99% of US precedential case law
- [Cornell Legal Information Institute](https://www.law.cornell.edu/) - USC, CFR, Supreme Court
- [GovInfo](https://www.govinfo.gov/) - Authenticated federal documents
- State-specific legal databases (California, Nevada)
- Web search for current law updates

### Value Proposition
- Multi-jurisdiction legal research (CA, NV, Federal)
- Contract analysis and clause review
- Business compliance checking
- AI-assisted legal document drafting
- Mandatory disclaimers and source citations
- Premium pricing tier ($5K-15K deployments)

---

## JURISDICTIONS COVERED

### Primary Jurisdictions
| Jurisdiction | Coverage Level | Sources |
|--------------|---------------|---------|
| California | Deep | CA Codes, CA Courts, CA Regulations |
| Nevada | Deep | NRS, NV Courts, NV Administrative Code |
| US Federal | Comprehensive | USC, CFR, Federal Courts |

### Legal Domains
| Domain | Description | Priority |
|--------|-------------|----------|
| Business Organizations | LLC, Corp, Partnership formation/compliance | HIGH |
| Contract Law | Contract review, common clauses, enforceability | HIGH |
| Employment Law | CA/NV employment regulations, HR compliance | HIGH |
| AI & Technology Law | AI regulations, data privacy, CCPA/CPRA | HIGH |
| Tax Law | Tax-related legal questions (coordinate with CROESUS) | MEDIUM |
| Intellectual Property | Trademark, copyright, trade secrets basics | MEDIUM |
| Wills & Estates | Basic estate planning information | MEDIUM |
| Insurance Law | Policy interpretation, coverage basics | MEDIUM |
| Real Estate | Basic property law, lease review | LOWER |

---

## CORE CAPABILITIES

### 1. Legal Question Answering
**Purpose:** Answer general legal questions with authoritative sources

**Features:**
- Multi-jurisdiction awareness (automatically detects or asks for jurisdiction)
- Statute and case law citation
- Plain-language explanations
- Confidence scoring (HIGH/MEDIUM/LOW/UNCERTAIN)
- Automatic "consult an attorney" recommendations for complex matters

**Confidence Scoring:**
| Level | Definition | Response Behavior |
|-------|------------|-------------------|
| HIGH (80-100%) | Clear statutory text, established case law | Provide answer with citations |
| MEDIUM (50-79%) | Some ambiguity, multiple interpretations | Provide answer with caveats |
| LOW (20-49%) | Limited sources, evolving law | Provide tentative answer, strong attorney recommendation |
| UNCERTAIN (<20%) | No clear authority, fact-specific | "I don't know - please consult an attorney" |

**SAFETY:** Always includes disclaimer and attorney consultation recommendation.

### 2. Contract Review
**Purpose:** Analyze contracts and identify key terms, risks, and missing provisions

**Features:**
- Clause identification and explanation
- Risk flagging (high-risk terms, unusual provisions)
- Missing provision detection
- Comparison to standard templates
- Plain-language summary

**Analysis Output:**
| Section | Analysis |
|---------|----------|
| Parties | Who is bound by this agreement |
| Term/Duration | How long the contract lasts |
| Obligations | What each party must do |
| Payment Terms | Financial obligations |
| Termination | How to end the contract |
| Liability Caps | Limits on damages |
| Indemnification | Who pays for what |
| IP Assignment | Intellectual property provisions |
| Non-Compete/Non-Solicit | Restrictive covenants |
| Risk Assessment | Overall risk rating with explanations |

**SAFETY:** Contract review is informational. User should have attorney review before signing.

### 3. Compliance Checking
**Purpose:** Check business activities against regulatory requirements

**Features:**
- Business formation compliance (registered agent, annual filings)
- Employment law compliance (CA wage/hour, meal breaks, PTO)
- Data privacy compliance (CCPA/CPRA, privacy policies)
- AI compliance (emerging AI regulations)
- Industry-specific compliance checks

**Compliance Domains:**
| Domain | Requirements Tracked |
|--------|---------------------|
| Business Formation | Annual statements, registered agent, franchise tax |
| Employment (CA) | Meal/rest breaks, OT rules, pay stub requirements |
| Employment (NV) | Minimum wage, OT, unemployment insurance |
| Data Privacy (CA) | CCPA notices, opt-out mechanisms, data inventory |
| AI Regulations | SB 1047 (if applicable), AI disclosure requirements |

### 4. Legal Research
**Purpose:** Deep research on specific legal topics

**Features:**
- Multi-source research (statutes, cases, regulations, secondary sources)
- Timeline of legal developments
- Conflicting authority identification
- Trend analysis (how courts have ruled recently)
- Comprehensive research memos

**Research Output:**
- Executive summary
- Applicable statutes with text
- Relevant case law with holdings
- Regulatory requirements
- Practical implications
- Remaining uncertainties
- Recommended next steps

### 5. Document Assistance
**Purpose:** Help draft basic legal documents

**Features:**
- Template-based document generation
- Clause customization guidance
- Form filling assistance
- Document review checklist

**SAFETY:** All generated documents require attorney review before use.

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Vector Store: Supabase pgvector for legal_knowledge embeddings
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis with RAG
Legal Data: CourtListener API, Cornell LII, GovInfo, web search
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/solon/
├── solon.py                # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── jurisdictions.yaml  # Jurisdiction configurations
│   ├── disclaimer_templates.yaml  # Legal disclaimers
│   └── sources.yaml        # Legal data source configs
├── modules/
│   ├── legal_search.py     # Legal database queries
│   ├── contract_analyzer.py # Contract analysis
│   ├── compliance_checker.py # Compliance checks
│   ├── source_validator.py # Citation verification
│   ├── confidence_scorer.py # Confidence scoring
│   └── rag_pipeline.py     # RAG implementation
├── shared/
│   ├── aria_reporter.py    # ARIA omniscience reporting
│   └── cost_tracker.py     # Cost tracking
└── tests/
    └── test_solon.py
```

### Database Schema

```sql
-- Legal knowledge base with embeddings
CREATE TABLE legal_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jurisdiction TEXT NOT NULL,       -- 'CA', 'NV', 'US', 'FEDERAL'
    domain TEXT NOT NULL,             -- 'contracts', 'employment', 'business', etc.
    source_type TEXT NOT NULL,        -- 'statute', 'case', 'regulation', 'secondary'
    citation TEXT NOT NULL,           -- Full legal citation
    title TEXT NOT NULL,
    content TEXT NOT NULL,            -- Full text or summary
    effective_date DATE,              -- When law became effective
    last_updated DATE,                -- When we last verified
    url TEXT,                         -- Source URL
    embedding VECTOR(1536),           -- OpenAI embeddings for search
    metadata JSONB DEFAULT '{}',      -- Additional metadata
    verified BOOLEAN DEFAULT FALSE,   -- Human-verified accuracy
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_legal_knowledge_jurisdiction ON legal_knowledge(jurisdiction);
CREATE INDEX idx_legal_knowledge_domain ON legal_knowledge(domain);
CREATE INDEX idx_legal_knowledge_source_type ON legal_knowledge(source_type);
CREATE INDEX idx_legal_knowledge_embedding ON legal_knowledge USING ivfflat (embedding vector_cosine_ops);

-- Legal queries log (for learning and audit)
CREATE TABLE legal_queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    question TEXT NOT NULL,
    jurisdiction TEXT,
    domain TEXT,
    response TEXT NOT NULL,
    citations TEXT[],                 -- Citations provided
    confidence_score DECIMAL(5, 2),   -- 0-100 confidence
    confidence_level TEXT,            -- HIGH, MEDIUM, LOW, UNCERTAIN
    disclaimer_included BOOLEAN DEFAULT TRUE,
    sources_verified BOOLEAN DEFAULT FALSE,
    feedback TEXT,                    -- User feedback
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_legal_queries_user ON legal_queries(user_id);
CREATE INDEX idx_legal_queries_domain ON legal_queries(domain);
CREATE INDEX idx_legal_queries_created ON legal_queries(created_at DESC);

-- Contract analyses log
CREATE TABLE contract_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    contract_type TEXT NOT NULL,      -- 'employment', 'service', 'nda', etc.
    file_hash TEXT,                   -- Hash of analyzed document
    analysis_result JSONB NOT NULL,   -- Full analysis
    risk_score DECIMAL(5, 2),         -- 0-100 risk score
    risk_level TEXT,                  -- LOW, MEDIUM, HIGH, CRITICAL
    flagged_clauses JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contract_analyses_user ON contract_analyses(user_id);
CREATE INDEX idx_contract_analyses_type ON contract_analyses(contract_type);

-- Compliance checks log
CREATE TABLE compliance_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    business_id UUID,
    check_type TEXT NOT NULL,         -- 'formation', 'employment', 'privacy', etc.
    jurisdiction TEXT NOT NULL,
    status TEXT NOT NULL,             -- 'compliant', 'non_compliant', 'needs_review'
    findings JSONB NOT NULL,          -- Compliance findings
    action_items JSONB DEFAULT '[]',  -- Required actions
    next_check_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_compliance_checks_user ON compliance_checks(user_id);
CREATE INDEX idx_compliance_checks_status ON compliance_checks(status);

-- Legal deadlines/calendar
CREATE TABLE legal_deadlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    business_id UUID,
    deadline_type TEXT NOT NULL,      -- 'filing', 'renewal', 'response', etc.
    jurisdiction TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    reminder_days INTEGER[] DEFAULT '{30, 7, 1}',
    status TEXT DEFAULT 'pending',    -- 'pending', 'completed', 'overdue'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_legal_deadlines_user ON legal_deadlines(user_id);
CREATE INDEX idx_legal_deadlines_due ON legal_deadlines(due_date);
CREATE INDEX idx_legal_deadlines_status ON legal_deadlines(status);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + legal DB status
GET /status              # Current operational status
GET /metrics             # Prometheus-compatible metrics
GET /jurisdictions       # List covered jurisdictions
```

### Legal Questions
```
POST /legal/question     # Ask a legal question
  Body: {
    "question": "string",
    "jurisdiction": "CA" | "NV" | "US",    # optional, will ask if needed
    "domain": "string",                     # optional
    "context": "string"                     # optional additional context
  }
  Returns: {
    "answer": "string",
    "confidence_score": 0-100,
    "confidence_level": "HIGH" | "MEDIUM" | "LOW" | "UNCERTAIN",
    "citations": ["citation1", "citation2"],
    "jurisdiction": "string",
    "domain": "string",
    "disclaimer": "string",
    "consult_attorney": true,
    "next_steps": ["step1", "step2"]
  }
```

### Contract Review
```
POST /legal/contract-review    # Analyze a contract
  Body: {
    "contract_text": "string",     # or file upload
    "contract_type": "string",     # optional - will detect
    "focus_areas": ["string"],     # optional - specific concerns
    "jurisdiction": "string"       # for enforceability analysis
  }
  Returns: {
    "summary": "string",
    "contract_type": "string",
    "parties": ["party1", "party2"],
    "key_terms": {...},
    "risk_assessment": {
      "score": 0-100,
      "level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "risk_factors": [...]
    },
    "flagged_clauses": [...],
    "missing_provisions": [...],
    "recommendations": [...],
    "disclaimer": "string"
  }
```

### Compliance Checking
```
POST /legal/compliance-check   # Check business compliance
  Body: {
    "business_type": "LLC" | "Corp" | "Sole Prop",
    "jurisdiction": "CA" | "NV",
    "check_types": ["formation", "employment", "privacy"],
    "business_details": {...}
  }
  Returns: {
    "overall_status": "compliant" | "non_compliant" | "needs_review",
    "checks": [{
      "type": "string",
      "status": "string",
      "findings": [...],
      "action_required": true/false,
      "actions": [...],
      "deadlines": [...]
    }],
    "disclaimer": "string"
  }
```

### Legal Research
```
POST /legal/research           # Deep legal research
  Body: {
    "topic": "string",
    "jurisdiction": "string",
    "research_depth": "quick" | "standard" | "comprehensive",
    "specific_questions": ["string"]
  }
  Returns: {
    "executive_summary": "string",
    "research_memo": {
      "question_presented": "string",
      "brief_answer": "string",
      "statement_of_facts": "string",
      "analysis": "string",
      "conclusion": "string"
    },
    "statutes": [{
      "citation": "string",
      "text": "string",
      "relevance": "string"
    }],
    "cases": [{
      "citation": "string",
      "holding": "string",
      "relevance": "string"
    }],
    "regulations": [...],
    "uncertainties": [...],
    "confidence_score": 0-100,
    "disclaimer": "string"
  }
```

### Document Assistance
```
POST /legal/draft              # Get drafting assistance
  Body: {
    "document_type": "string",  # 'nda', 'contractor_agreement', etc.
    "parameters": {...},        # Document-specific parameters
    "jurisdiction": "string"
  }
  Returns: {
    "document_draft": "string",
    "key_provisions": [...],
    "customization_notes": [...],
    "review_checklist": [...],
    "disclaimer": "MUST HAVE ATTORNEY REVIEW BEFORE USE"
  }

GET /legal/templates           # List available templates
GET /legal/templates/{id}      # Get specific template
```

### Knowledge Management
```
GET /legal/knowledge/search    # Search legal knowledge base
  Query: q=search_term&jurisdiction=CA&domain=contracts

POST /legal/knowledge/add      # Add verified legal knowledge (admin)
POST /legal/knowledge/update   # Update existing entry (admin)
POST /legal/knowledge/verify   # Mark entry as verified (admin)
```

---

## INTEGRATION REQUIREMENTS

### ARIA Tool Definitions

```python
# ARIA tools for legal questions
ARIA_TOOLS = {
    "legal.question": {
        "description": "Ask a legal question and get jurisdiction-specific information",
        "parameters": {
            "question": "The legal question to research",
            "jurisdiction": "CA, NV, or US (optional - will ask if needed)",
            "context": "Additional context for the question"
        },
        "returns": "Legal information with citations and confidence score"
    },
    "legal.contract_review": {
        "description": "Analyze a contract for key terms, risks, and issues",
        "parameters": {
            "contract_text": "The contract text to analyze",
            "contract_type": "Type of contract (employment, service, nda, etc.)",
            "focus_areas": "Specific areas of concern"
        },
        "returns": "Contract analysis with risk assessment and recommendations"
    },
    "legal.compliance": {
        "description": "Check business compliance with legal requirements",
        "parameters": {
            "business_type": "LLC, Corp, or Sole Prop",
            "jurisdiction": "CA or NV",
            "check_types": "formation, employment, privacy, etc."
        },
        "returns": "Compliance status with action items"
    },
    "legal.research": {
        "description": "Deep research on a legal topic",
        "parameters": {
            "topic": "The legal topic to research",
            "jurisdiction": "Applicable jurisdiction",
            "depth": "quick, standard, or comprehensive"
        },
        "returns": "Research memo with statutes, cases, and analysis"
    },
    "legal.deadline": {
        "description": "Check or set legal deadlines",
        "parameters": {
            "action": "list, add, complete",
            "deadline_type": "Type of deadline",
            "details": "Deadline details"
        },
        "returns": "Deadline information"
    }
}
```

### ARIA Omniscience Reporting

```python
from shared.aria_reporter import ARIAReporter

reporter = ARIAReporter("SOLON")

# Report significant actions
await reporter.report_action(
    action="legal_question_answered",
    details={
        "domain": "employment",
        "jurisdiction": "CA",
        "confidence": confidence_score,
        "citations_count": len(citations)
    }
)

# Report decisions
await reporter.report_decision(
    decision="compliance_check_result",
    reasoning=f"Business found {status} for {check_type}",
    outcome={
        "status": status,
        "action_items": action_items
    }
)
```

### CROESUS Coordination (Tax/Legal Overlap)
```python
# When legal question has tax implications
if domain == "tax" or has_tax_implications(question):
    # Route to CROESUS for tax-specific analysis
    tax_response = await call_agent("CROESUS", {
        "action": "tax_analysis",
        "context": legal_context,
        "question": tax_aspect
    })

    # Combine legal and tax analysis
    combined_response = merge_legal_tax(legal_response, tax_response)
```

### Event Bus Integration
```python
# Published events
"legal.question.answered"       # Legal question answered
"legal.contract.analyzed"       # Contract analysis completed
"legal.compliance.checked"      # Compliance check completed
"legal.deadline.approaching"    # Legal deadline reminder
"legal.knowledge.updated"       # Knowledge base updated

# Subscribed events
"scheduler.daily"               # Check deadlines
"document.uploaded"             # Auto-analyze uploaded contracts
"business.created"              # Initial compliance check for new business
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("SOLON")

# Log AI analysis costs
await cost_tracker.log_usage(
    endpoint="/legal/question",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={
        "jurisdiction": jurisdiction,
        "domain": domain,
        "confidence": confidence_score
    }
)

# Log external API costs (CourtListener, etc.)
await cost_tracker.log_external_api(
    service="courtlistener",
    endpoint="/search",
    cost=0,  # Free tier
    metadata={"queries": query_count}
)
```

---

## HALLUCINATION PREVENTION

### Multi-Layer Verification Pipeline

```python
class LegalRAGPipeline:
    async def process_question(self, question: str, jurisdiction: str) -> dict:
        # Step 1: Retrieve relevant legal sources
        sources = await self.retrieve_sources(question, jurisdiction)

        # Step 2: Validate source authority
        validated_sources = await self.validate_sources(sources)
        if len(validated_sources) == 0:
            return self.uncertain_response(question)

        # Step 3: Generate response with citations
        response = await self.generate_response(question, validated_sources)

        # Step 4: Verify citations exist in response
        citations_valid = await self.verify_citations(response)
        if not citations_valid:
            response = await self.regenerate_with_citation_check(question, validated_sources)

        # Step 5: Check for consistency
        consistency_check = await self.check_consistency(response, validated_sources)
        if not consistency_check['consistent']:
            response = await self.resolve_inconsistency(response, consistency_check)

        # Step 6: Calculate confidence score
        confidence = self.calculate_confidence(validated_sources, citations_valid, consistency_check)

        # Step 7: Add mandatory disclaimer
        response = self.add_disclaimer(response, confidence)

        return response

    def uncertain_response(self, question: str) -> dict:
        return {
            "answer": f"I don't have sufficient authoritative sources to answer this question about {question}. This is an area where you should consult with a licensed attorney who can provide jurisdiction-specific advice.",
            "confidence_score": 0,
            "confidence_level": "UNCERTAIN",
            "citations": [],
            "disclaimer": MANDATORY_DISCLAIMER,
            "consult_attorney": True
        }
```

### Confidence Scoring Algorithm

```python
def calculate_confidence(self, sources: list, citations_valid: bool, consistency: dict) -> dict:
    score = 0
    factors = []

    # Source quality (40 points max)
    source_score = 0
    for source in sources:
        if source['type'] == 'statute':
            source_score += 10
        elif source['type'] == 'case':
            source_score += 8
        elif source['type'] == 'regulation':
            source_score += 7
        elif source['type'] == 'secondary':
            source_score += 3
    source_score = min(40, source_score)
    score += source_score
    factors.append(f"Source quality: {source_score}/40")

    # Citation verification (20 points)
    if citations_valid:
        score += 20
        factors.append("Citations verified: 20/20")
    else:
        factors.append("Citations need verification: 0/20")

    # Consistency check (20 points)
    if consistency['consistent']:
        score += 20
        factors.append("Analysis consistent: 20/20")
    else:
        score += 5
        factors.append(f"Some inconsistency: 5/20 - {consistency['notes']}")

    # Recency of sources (10 points)
    recency_score = self.calculate_recency_score(sources)
    score += recency_score
    factors.append(f"Source recency: {recency_score}/10")

    # Jurisdiction specificity (10 points)
    jurisdiction_score = self.calculate_jurisdiction_score(sources)
    score += jurisdiction_score
    factors.append(f"Jurisdiction match: {jurisdiction_score}/10")

    # Determine confidence level
    if score >= 80:
        level = "HIGH"
    elif score >= 50:
        level = "MEDIUM"
    elif score >= 20:
        level = "LOW"
    else:
        level = "UNCERTAIN"

    return {
        "score": score,
        "level": level,
        "factors": factors
    }
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(legal_context: dict) -> str:
    return f"""You are SOLON - Legal Information Agent for LeverEdge AI.

Named after the Athenian lawmaker who codified Athenian law, you provide accurate legal information with authoritative citations.

## CRITICAL SAFETY REQUIREMENTS

**YOU MUST ALWAYS:**
1. Include a disclaimer that this is legal INFORMATION, not legal ADVICE
2. Recommend consulting a licensed attorney for specific legal advice
3. Cite authoritative sources (statutes, cases, regulations) for all legal claims
4. State your confidence level clearly
5. Say "I don't know - please consult an attorney" when uncertain

**YOU MUST NEVER:**
- Provide specific legal advice for a user's situation
- Claim attorney-client privilege exists
- Guarantee legal outcomes
- Make representations about case results
- Skip the disclaimer

## MANDATORY DISCLAIMER (INCLUDE IN ALL RESPONSES)

"This information is provided for educational purposes only and does not constitute legal advice. Legal matters are often fact-specific and jurisdiction-specific. For advice about your specific situation, please consult with a licensed attorney in your jurisdiction."

## TIME AWARENESS
- Current: {legal_context['current_time']}
- Jurisdiction Context: {legal_context.get('default_jurisdiction', 'Ask user')}

## YOUR IDENTITY
You are the legal research brain of LeverEdge. You research legal questions, analyze contracts, check compliance, and provide well-sourced legal information.

## JURISDICTIONS
Primary: California, Nevada, US Federal
You can research other jurisdictions but should clearly note if you have less comprehensive coverage.

## YOUR CAPABILITIES

### Legal Research
- Research statutes (USC, CA Codes, NRS)
- Find relevant case law
- Identify applicable regulations
- Synthesize legal information
- Track legal developments

### Contract Analysis
- Identify key terms and provisions
- Flag high-risk clauses
- Compare to standard templates
- Identify missing provisions
- Explain terms in plain language

### Compliance Checking
- Business formation requirements
- Employment law compliance
- Data privacy requirements
- Industry-specific regulations

### Source Citation
ALWAYS cite your sources. Use standard legal citation format:
- Statutes: Cal. Civ. Code § 1234
- Cases: Smith v. Jones, 123 Cal. App. 4th 567 (2023)
- Regulations: 29 C.F.R. § 825.100

## CONFIDENCE LEVELS

When answering, assess and state your confidence:
- HIGH (80-100%): Clear statutory text, established case law, well-settled area
- MEDIUM (50-79%): Some ambiguity, multiple interpretations possible
- LOW (20-49%): Limited sources, evolving area of law
- UNCERTAIN (<20%): No clear authority - recommend attorney consultation

## RESPONSE FORMAT

For legal questions:
1. Direct answer (if confident)
2. Applicable law with citations
3. Key considerations
4. Confidence level
5. Disclaimer
6. "Consult an attorney for advice about your specific situation"

## COORDINATION WITH CROESUS
For questions involving tax implications, coordinate with CROESUS (Tax Advisor).
Tax law often intersects with business law, estate planning, and entity formation.

## YOUR MISSION
Provide accurate, well-sourced legal information.
Empower users to understand the law.
Never provide legal advice - that's for licensed attorneys.
Always prioritize safety and proper disclaimers.
When in doubt, recommend an attorney.
"""

MANDATORY_DISCLAIMER = """

---
**DISCLAIMER:** This information is provided for educational purposes only and does not constitute legal advice. Legal matters are often fact-specific and jurisdiction-specific. For advice about your specific situation, please consult with a licensed attorney in your jurisdiction. No attorney-client relationship is created by using this service.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with health endpoints and legal question answering

- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Set up PostgreSQL schema
- [ ] Basic legal question endpoint with Claude
- [ ] Mandatory disclaimer system
- [ ] Confidence scoring v1
- [ ] Deploy and test

**Done When:** SOLON can answer basic legal questions with disclaimers and confidence scores

### Phase 2: RAG Implementation (Sprint 3-4)
**Goal:** Legal knowledge base with RAG retrieval

- [ ] Set up pgvector for embeddings
- [ ] Integrate CourtListener API
- [ ] Integrate Cornell LII
- [ ] Implement RAG pipeline
- [ ] Source citation verification
- [ ] Knowledge base seeding (CA, NV, Federal basics)
- [ ] Confidence scoring v2 with source quality

**Done When:** Responses cite authoritative sources from knowledge base

### Phase 3: Contract Analysis (Sprint 5-6)
**Goal:** Contract review and analysis capability

- [ ] Contract parsing (text extraction)
- [ ] Clause identification
- [ ] Risk scoring algorithm
- [ ] Template comparison
- [ ] Missing provision detection
- [ ] Plain-language explanations

**Done When:** Users can upload contracts and receive analysis

### Phase 4: Compliance & Polish (Sprint 7-8)
**Goal:** Compliance checking and ARIA integration

- [ ] Compliance check endpoints
- [ ] Business formation compliance
- [ ] Employment compliance (CA/NV)
- [ ] Deadline tracking
- [ ] ARIA tool integration
- [ ] Event bus integration
- [ ] ARIA omniscience reporting

**Done When:** Full integration with LeverEdge ecosystem

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 7 | 12 | 1-2 |
| RAG Implementation | 7 | 18 | 3-4 |
| Contract Analysis | 6 | 14 | 5-6 |
| Compliance & Polish | 7 | 14 | 7-8 |
| **Total** | **27** | **58** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Legal questions answered in < 15 seconds
- [ ] Contract analysis completed in < 30 seconds
- [ ] Compliance checks completed in < 20 seconds
- [ ] All responses include mandatory disclaimers

### Quality
- [ ] 99%+ uptime for legal endpoints
- [ ] < 5% "I don't know" rate for well-established areas
- [ ] 100% citation rate on legal claims
- [ ] 100% disclaimer inclusion rate

### Integration
- [ ] ARIA can query legal info via tools
- [ ] Events publish to Event Bus correctly
- [ ] Insights stored in ARIA knowledge base
- [ ] Costs tracked per query

### Safety
- [ ] Zero responses without disclaimers
- [ ] All responses recommend attorney for advice
- [ ] Uncertain queries clearly acknowledged
- [ ] No "legal advice" language in responses

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Hallucinated citations | Legal liability, user harm | RAG with verified sources, citation checking |
| Users rely on info as legal advice | User harm | Mandatory disclaimers, attorney recommendations |
| Outdated legal information | Incorrect guidance | Regular source updates, recency tracking |
| Jurisdiction confusion | Wrong law applied | Explicit jurisdiction detection, confirmation |
| Misinterpreted contracts | User harm | Clear risk flagging, attorney review recommendation |

---

## SECURITY CONSIDERATIONS

### Data Protection
- Contract text processed but not stored long-term
- Query history logged for audit purposes
- No PII extraction from contracts
- Embeddings stored, not raw contract text

### Access Control
- User isolation for query history
- Rate limiting on all endpoints
- Audit logging for compliance

### Legal/Ethical
- Clear "not legal advice" positioning
- No attorney-client privilege claims
- Proper UPL (unauthorized practice of law) avoidance
- Educational purpose framing

---

## GIT COMMIT

```
Add SOLON - AI-powered legal advisor agent spec

- Multi-jurisdiction legal research (CA, NV, Federal)
- Contract analysis with risk scoring
- Compliance checking for business/employment/privacy
- RAG architecture with hallucination prevention
- Mandatory disclaimers and source citations
- Confidence scoring with uncertainty acknowledgment
- CRITICAL: Information only - not legal advice
- 4-phase implementation plan
- Full database schema with pgvector
- Integration with ARIA, Event Bus, CROESUS
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/SOLON.md

Context: Build SOLON legal advisor agent. Start with Phase 1 foundation.
Note: This provides legal INFORMATION only - not legal advice.
CRITICAL: Mandatory disclaimers in all responses.
```
