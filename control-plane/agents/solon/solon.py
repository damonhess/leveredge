#!/usr/bin/env python3
"""
SOLON - AI-Powered Legal Advisor Agent
Port: 8210

Named after Solon, the Athenian lawmaker who codified Athenian law.
Provides legal INFORMATION (not advice) with authoritative citations.

CRITICAL SAFETY:
- Always includes disclaimers
- Never provides legal advice
- Cites sources for all claims
- Says "I don't know" when uncertain
- Recommends attorney consultation

V1 CAPABILITIES:
- Multi-jurisdiction legal questions (CA, NV, Federal)
- Contract review and risk analysis
- Compliance checking
- Legal research with citations
- Confidence scoring

JURISDICTIONS:
- California (primary)
- Nevada (primary)
- US Federal (comprehensive)
"""

import os
import sys
import json
import hashlib
import httpx
import asyncpg
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.insert(0, '/opt/leveredge/shared')
from aria_reporter import ARIAReporter
from cost_tracker import CostTracker

app = FastAPI(
    title="SOLON",
    description="AI-Powered Legal Advisor - Legal Information Only",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize clients
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Database pool
pool: asyncpg.Pool = None


@app.on_event("startup")
async def startup():
    global pool
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


cost_tracker = CostTracker("SOLON")
aria_reporter = ARIAReporter("SOLON")

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Mandatory disclaimer
MANDATORY_DISCLAIMER = """

---
**DISCLAIMER:** This information is provided for educational purposes only and does not constitute legal advice. Legal matters are often fact-specific and jurisdiction-specific. For advice about your specific situation, please consult with a licensed attorney in your jurisdiction. No attorney-client relationship is created by using this service.
"""

# =============================================================================
# MODELS
# =============================================================================

class LegalQuestionRequest(BaseModel):
    question: str = Field(..., description="The legal question to research")
    jurisdiction: Optional[str] = Field(None, description="CA, NV, US, or FEDERAL")
    context: Optional[str] = Field(None, description="Additional context")
    domain: Optional[str] = Field(None, description="Legal domain hint")

class ContractReviewRequest(BaseModel):
    contract_text: str = Field(..., description="The contract text to analyze")
    contract_type: Optional[str] = Field(None, description="Type of contract")
    focus_areas: Optional[List[str]] = Field(None, description="Specific areas of concern")
    jurisdiction: Optional[str] = Field("CA", description="Jurisdiction for enforceability")

class ComplianceCheckRequest(BaseModel):
    business_type: str = Field(..., description="LLC, Corp, or Sole_Prop")
    jurisdiction: str = Field(..., description="CA or NV")
    check_types: List[str] = Field(..., description="formation, employment, privacy, etc.")
    business_details: Optional[Dict[str, Any]] = Field(None, description="Additional business details")

class LegalResearchRequest(BaseModel):
    topic: str = Field(..., description="The legal topic to research")
    jurisdiction: Optional[str] = Field(None, description="Applicable jurisdiction")
    research_depth: str = Field("standard", description="quick, standard, or comprehensive")
    specific_questions: Optional[List[str]] = Field(None, description="Specific questions to answer")

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "days_to_launch": days_to_launch
    }

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(time_context: dict) -> str:
    """Build SOLON system prompt with safety requirements"""

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

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}

## JURISDICTIONS
Primary: California, Nevada, US Federal
You can research other jurisdictions but should clearly note if you have less comprehensive coverage.

## CONFIDENCE LEVELS

When answering, assess and state your confidence:
- HIGH (80-100%): Clear statutory text, established case law, well-settled area
- MEDIUM (50-79%): Some ambiguity, multiple interpretations possible
- LOW (20-49%): Limited sources, evolving area of law
- UNCERTAIN (<20%): No clear authority - recommend attorney consultation

## SOURCE CITATION
ALWAYS cite your sources. Use standard legal citation format:
- Statutes: Cal. Civ. Code § 1234
- Cases: Smith v. Jones, 123 Cal. App. 4th 567 (2023)
- Regulations: 29 C.F.R. § 825.100
- CA Codes: Cal. Bus. & Prof. Code § 17200

## LEGAL DOMAINS
- Business Organizations (LLC, Corp, Partnership)
- Contract Law (formation, breach, remedies)
- Employment Law (CA wage/hour, harassment, termination)
- Intellectual Property (copyright, trademark, trade secrets)
- Data Privacy (CCPA/CPRA, HIPAA basics)
- AI Regulations (emerging state/federal AI laws)
- Tax Law (basic, coordinate with CROESUS for details)
- Wills & Estates (basic information)

## RESPONSE FORMAT

For legal questions:
1. Direct answer (if confident) with applicable law
2. Relevant statutes/cases with citations
3. Key considerations and caveats
4. Confidence level with reasoning
5. MANDATORY DISCLAIMER
6. "For advice about your specific situation, please consult with a licensed attorney."

## YOUR MISSION
Provide accurate, well-sourced legal information.
Empower users to understand the law.
Never provide legal advice - that's for licensed attorneys.
Always prioritize safety and proper disclaimers.
When in doubt, recommend an attorney.
"""

# =============================================================================
# CONFIDENCE SCORING
# =============================================================================

def calculate_confidence(response_text: str, has_citations: bool, domain: str) -> dict:
    """Calculate confidence score based on response quality"""

    score = 50  # Base score
    factors = []

    # Citation quality
    if has_citations:
        citation_count = response_text.count("§") + response_text.count("v.") + response_text.count("C.F.R.")
        if citation_count >= 3:
            score += 25
            factors.append(f"Multiple citations found ({citation_count})")
        elif citation_count >= 1:
            score += 15
            factors.append(f"Citations found ({citation_count})")
    else:
        score -= 20
        factors.append("No citations found")

    # Uncertainty markers
    uncertainty_markers = ["may", "might", "unclear", "depends", "varies", "consult", "uncertain"]
    uncertainty_count = sum(1 for marker in uncertainty_markers if marker.lower() in response_text.lower())
    if uncertainty_count > 3:
        score -= 15
        factors.append("High uncertainty in response")

    # Domain confidence
    well_settled_domains = ["business_formation", "contract_basics", "employment_basics"]
    complex_domains = ["ai_regulations", "emerging_law", "cross_jurisdiction"]

    if domain in complex_domains:
        score -= 10
        factors.append(f"Complex/evolving domain: {domain}")

    # Clamp score
    score = max(0, min(100, score))

    # Determine level
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

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SOLON",
        "version": "1.0.0",
        "port": 8210,
        "capabilities": ["legal_questions", "contract_review", "compliance_check", "legal_research"]
    }

@app.get("/jurisdictions")
async def get_jurisdictions():
    """List covered jurisdictions"""
    return {
        "primary": ["CA", "NV", "US"],
        "coverage": {
            "CA": {
                "name": "California",
                "level": "deep",
                "domains": ["business", "employment", "privacy", "contracts"]
            },
            "NV": {
                "name": "Nevada",
                "level": "deep",
                "domains": ["business", "contracts", "gaming"]
            },
            "US": {
                "name": "US Federal",
                "level": "comprehensive",
                "domains": ["constitutional", "employment", "tax", "ip"]
            }
        }
    }

@app.post("/legal/question")
async def answer_legal_question(request: LegalQuestionRequest, background_tasks: BackgroundTasks):
    """
    Answer a legal question with citations and confidence scoring.

    ALWAYS includes disclaimer and recommends attorney consultation.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    # Build user prompt
    user_prompt = f"""Please answer the following legal question:

**Question:** {request.question}

**Jurisdiction:** {request.jurisdiction or "Please determine the most relevant jurisdiction and ask if needed"}

{"**Additional Context:** " + request.context if request.context else ""}

Remember to:
1. Cite specific statutes, cases, or regulations
2. State your confidence level
3. Include the mandatory disclaimer
4. Recommend consulting an attorney for specific advice
"""

    try:
        # Make API call with web search for current law
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            tools=[{"type": "web_search_20250305"}],
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Extract response text
        response_text = ""
        citations = []
        web_searches = 0

        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text
            elif hasattr(block, 'type') and block.type == 'tool_use':
                if block.name == 'web_search':
                    web_searches += 1

        # Ensure disclaimer is included
        if "DISCLAIMER" not in response_text and "disclaimer" not in response_text.lower():
            response_text += MANDATORY_DISCLAIMER

        # Extract citations (simple pattern matching)
        import re
        citation_patterns = [
            r'Cal\. [A-Za-z\. &]+Code §\s*\d+',
            r'\d+ [A-Z][a-z]+\. [A-Z][a-z]+\. \d+[a-z]* \d+',
            r'\d+ C\.F\.R\. §\s*[\d\.]+',
            r'\d+ U\.S\.C\. §\s*\d+',
        ]
        for pattern in citation_patterns:
            found = re.findall(pattern, response_text)
            citations.extend(found)

        # Calculate confidence
        domain = request.domain or "general"
        confidence = calculate_confidence(response_text, len(citations) > 0, domain)

        # Log usage
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        await cost_tracker.log_usage(
            endpoint="/legal/question",
            model="claude-sonnet-4-20250514",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            web_searches=web_searches,
            metadata={
                "jurisdiction": request.jurisdiction,
                "domain": domain,
                "confidence": confidence["score"]
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="answered_legal_question",
            target=request.question[:100],
            details={
                "jurisdiction": request.jurisdiction,
                "confidence_score": confidence["score"],
                "confidence_level": confidence["level"],
                "citations_count": len(citations),
                "web_searches": web_searches
            },
            domain="legal",
            importance="medium"
        )

        return {
            "answer": response_text,
            "confidence_score": confidence["score"],
            "confidence_level": confidence["level"],
            "confidence_factors": confidence["factors"],
            "citations": list(set(citations)),
            "jurisdiction": request.jurisdiction,
            "domain": domain,
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "consult_attorney": True,
            "web_searches_performed": web_searches
        }

    except Exception as e:
        # Report error to ARIA
        await aria_reporter.report_error(
            error_type="legal_question_failure",
            error_message=str(e),
            context={"question": request.question[:100]}
        )
        raise HTTPException(status_code=500, detail=f"Error processing legal question: {str(e)}")

@app.post("/legal/contract-review")
async def review_contract(request: ContractReviewRequest, background_tasks: BackgroundTasks):
    """
    Analyze a contract for key terms, risks, and issues.

    Returns risk assessment and recommendations, NOT legal advice.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    # Hash contract for logging (don't store full text)
    contract_hash = hashlib.sha256(request.contract_text.encode()).hexdigest()[:16]

    user_prompt = f"""Please review and analyze the following contract:

**Contract Type:** {request.contract_type or "Please identify"}
**Jurisdiction:** {request.jurisdiction}
{"**Focus Areas:** " + ", ".join(request.focus_areas) if request.focus_areas else ""}

---
CONTRACT TEXT:
---
{request.contract_text}
---

Please provide:
1. **Summary**: Brief overview of the contract
2. **Key Terms**: Important terms and their implications
3. **Risk Assessment**: Identify high-risk clauses with severity ratings
4. **Missing Provisions**: Standard provisions that are missing
5. **Plain Language Explanation**: Explain complex terms simply
6. **Recommendations**: What to consider (NOT legal advice)

Remember: This is analysis for INFORMATIONAL purposes only. The user MUST have an attorney review before signing.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=6000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text

        # Ensure disclaimer
        if "DISCLAIMER" not in response_text:
            response_text += MANDATORY_DISCLAIMER

        # Attempt to extract risk score from response
        risk_score = 50  # Default medium risk
        risk_level = "MEDIUM"

        if "high risk" in response_text.lower() or "significant risk" in response_text.lower():
            risk_score = 75
            risk_level = "HIGH"
        elif "critical" in response_text.lower() or "dangerous" in response_text.lower():
            risk_score = 90
            risk_level = "CRITICAL"
        elif "low risk" in response_text.lower() or "standard" in response_text.lower():
            risk_score = 25
            risk_level = "LOW"

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/legal/contract-review",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            metadata={
                "contract_type": request.contract_type,
                "jurisdiction": request.jurisdiction,
                "risk_level": risk_level
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="contract_analyzed",
            target=f"{request.contract_type or 'contract'}_{contract_hash}",
            details={
                "contract_type": request.contract_type,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "jurisdiction": request.jurisdiction
            },
            domain="legal",
            importance="high"
        )

        return {
            "analysis": response_text,
            "contract_type": request.contract_type,
            "risk_assessment": {
                "score": risk_score,
                "level": risk_level
            },
            "jurisdiction": request.jurisdiction,
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "must_have_attorney_review": True
        }

    except Exception as e:
        await aria_reporter.report_error(
            error_type="contract_review_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error reviewing contract: {str(e)}")

@app.post("/legal/compliance-check")
async def check_compliance(request: ComplianceCheckRequest, background_tasks: BackgroundTasks):
    """
    Check business compliance with legal requirements.

    Returns compliance status and action items.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    user_prompt = f"""Please perform a compliance check for the following business:

**Business Type:** {request.business_type}
**Jurisdiction:** {request.jurisdiction}
**Check Types:** {", ".join(request.check_types)}
{"**Business Details:** " + json.dumps(request.business_details) if request.business_details else ""}

For each check type, please provide:
1. **Compliance Status**: COMPLIANT, NON_COMPLIANT, or NEEDS_REVIEW
2. **Requirements**: What the law requires
3. **Current State**: Assessment based on provided information
4. **Action Items**: What needs to be done (if any)
5. **Deadlines**: Any relevant filing or compliance deadlines
6. **Citations**: Relevant statutes or regulations

Common check areas:
- Business formation (registered agent, annual filings, franchise tax)
- Employment compliance (CA meal/rest breaks, wage requirements)
- Data privacy (CCPA notices, privacy policy requirements)
- Tax compliance (basic requirements, coordinate with CROESUS for details)

Remember: This is an informational compliance overview, NOT legal advice.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            tools=[{"type": "web_search_20250305"}],
            messages=[{"role": "user", "content": user_prompt}]
        )

        response_text = ""
        web_searches = 0
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text
            elif hasattr(block, 'type') and block.type == 'tool_use':
                if block.name == 'web_search':
                    web_searches += 1

        if "DISCLAIMER" not in response_text:
            response_text += MANDATORY_DISCLAIMER

        # Determine overall status
        overall_status = "needs_review"
        if "non_compliant" in response_text.lower() or "non-compliant" in response_text.lower():
            overall_status = "non_compliant"
        elif "compliant" in response_text.lower() and "non" not in response_text.lower()[:response_text.lower().find("compliant")]:
            overall_status = "compliant"

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/legal/compliance-check",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            web_searches=web_searches,
            metadata={
                "business_type": request.business_type,
                "jurisdiction": request.jurisdiction,
                "check_types": request.check_types,
                "overall_status": overall_status
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="compliance_check_performed",
            target=f"{request.business_type}_{request.jurisdiction}",
            details={
                "check_types": request.check_types,
                "overall_status": overall_status
            },
            domain="legal",
            importance="high"
        )

        return {
            "overall_status": overall_status,
            "analysis": response_text,
            "business_type": request.business_type,
            "jurisdiction": request.jurisdiction,
            "check_types": request.check_types,
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "consult_attorney": True
        }

    except Exception as e:
        await aria_reporter.report_error(
            error_type="compliance_check_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error checking compliance: {str(e)}")

@app.post("/legal/research")
async def legal_research(request: LegalResearchRequest, background_tasks: BackgroundTasks):
    """
    Deep legal research on a topic.

    Returns research memo with statutes, cases, and analysis.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    depth_instructions = {
        "quick": "Provide a brief overview with key statutes and 1-2 cases.",
        "standard": "Provide thorough research with multiple statutes, relevant cases, and analysis.",
        "comprehensive": "Provide exhaustive research including statutory history, major cases, trends, and detailed analysis."
    }

    user_prompt = f"""Please conduct legal research on the following topic:

**Topic:** {request.topic}
**Jurisdiction:** {request.jurisdiction or "Please determine the most relevant jurisdiction"}
**Research Depth:** {request.research_depth}

{depth_instructions.get(request.research_depth, depth_instructions["standard"])}

{"**Specific Questions to Answer:**" + chr(10) + chr(10).join(f"- {q}" for q in request.specific_questions) if request.specific_questions else ""}

Please structure your research as a legal research memo:

1. **Question Presented**: Restate the legal question
2. **Brief Answer**: Concise answer
3. **Applicable Statutes**: Relevant statutory provisions with citations
4. **Relevant Cases**: Key cases with holdings
5. **Regulations**: Applicable administrative rules
6. **Analysis**: Detailed legal analysis
7. **Conclusion**: Summary and practical implications
8. **Uncertainties**: Areas where the law is unclear or evolving
9. **Recommended Next Steps**: (NOT legal advice)

Remember: This is legal research for INFORMATIONAL purposes. Always recommend attorney consultation.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            system=system_prompt,
            tools=[{"type": "web_search_20250305"}],
            messages=[{"role": "user", "content": user_prompt}]
        )

        response_text = ""
        web_searches = 0
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text
            elif hasattr(block, 'type') and block.type == 'tool_use':
                if block.name == 'web_search':
                    web_searches += 1

        if "DISCLAIMER" not in response_text:
            response_text += MANDATORY_DISCLAIMER

        # Extract citations
        import re
        citations = []
        citation_patterns = [
            r'Cal\. [A-Za-z\. &]+Code §\s*\d+',
            r'\d+ [A-Z][a-z]+\. [A-Z][a-z]+\. \d+[a-z]* \d+',
            r'\d+ C\.F\.R\. §\s*[\d\.]+',
            r'\d+ U\.S\.C\. §\s*\d+',
        ]
        for pattern in citation_patterns:
            found = re.findall(pattern, response_text)
            citations.extend(found)

        confidence = calculate_confidence(response_text, len(citations) > 0, "research")

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/legal/research",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            web_searches=web_searches,
            metadata={
                "topic": request.topic[:100],
                "jurisdiction": request.jurisdiction,
                "depth": request.research_depth,
                "citations_found": len(citations)
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="legal_research_completed",
            target=request.topic[:100],
            details={
                "jurisdiction": request.jurisdiction,
                "depth": request.research_depth,
                "citations_count": len(citations),
                "confidence_score": confidence["score"]
            },
            domain="legal",
            importance="medium"
        )

        return {
            "research_memo": response_text,
            "topic": request.topic,
            "jurisdiction": request.jurisdiction,
            "depth": request.research_depth,
            "citations": list(set(citations)),
            "confidence_score": confidence["score"],
            "confidence_level": confidence["level"],
            "web_searches_performed": web_searches,
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "consult_attorney": True
        }

    except Exception as e:
        await aria_reporter.report_error(
            error_type="legal_research_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error conducting research: {str(e)}")

# =============================================================================
# SITUATION MEMORY
# =============================================================================

@app.get("/situation")
async def get_situation(category: Optional[str] = None):
    """Get your current legal situation"""
    if not pool:
        return []

    async with pool.acquire() as conn:
        if category:
            rows = await conn.fetch(
                "SELECT * FROM solon_situation WHERE category = $1 ORDER BY updated_at DESC",
                category
            )
        else:
            rows = await conn.fetch("SELECT * FROM solon_situation ORDER BY category, topic")
        return [dict(r) for r in rows]


@app.post("/situation")
async def update_situation(category: str, topic: str, current_state: str, attorney_notes: Optional[str] = None):
    """Update your legal situation"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Check if exists
        existing = await conn.fetchrow(
            "SELECT id, history FROM solon_situation WHERE category = $1 AND topic = $2",
            category, topic
        )

        if existing:
            # Append old state to history
            history = existing['history'] or []
            history.append({
                "state": current_state,
                "updated_at": datetime.now().isoformat()
            })

            await conn.execute("""
                UPDATE solon_situation
                SET current_state = $2, history = $3, attorney_notes = $4, updated_at = NOW()
                WHERE id = $1
            """, existing['id'], current_state, json.dumps(history), attorney_notes)
        else:
            await conn.execute("""
                INSERT INTO solon_situation (category, topic, current_state, attorney_notes)
                VALUES ($1, $2, $3, $4)
            """, category, topic, current_state, attorney_notes)

        return {"status": "updated"}


# =============================================================================
# CONTRACTS
# =============================================================================

@app.get("/contracts")
async def list_contracts(status: Optional[str] = None):
    if not pool:
        return []

    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM solon_contracts WHERE status = $1 ORDER BY expiration_date",
                status
            )
        else:
            rows = await conn.fetch("SELECT * FROM solon_contracts ORDER BY status, expiration_date")
        return [dict(r) for r in rows]


@app.get("/contracts/expiring")
async def expiring_contracts(days: int = 30):
    """Get contracts expiring within N days"""
    if not pool:
        return []

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM solon_contracts
            WHERE status = 'active'
            AND expiration_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $1
            ORDER BY expiration_date
        """, days)
        return [dict(r) for r in rows]


@app.post("/contracts")
async def add_contract(
    name: str,
    contract_type: str,
    counterparty: str,
    effective_date: Optional[date] = None,
    expiration_date: Optional[date] = None,
    key_terms: Dict = {}
):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO solon_contracts (name, contract_type, counterparty, effective_date, expiration_date, key_terms)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, name, contract_type, counterparty, effective_date, expiration_date, json.dumps(key_terms))
        return dict(row)


# =============================================================================
# COMPLIANCE
# =============================================================================

@app.get("/compliance")
async def list_compliance(status: Optional[str] = None):
    if not pool:
        return []

    async with pool.acquire() as conn:
        if status:
            rows = await conn.fetch(
                "SELECT * FROM solon_compliance WHERE status = $1 ORDER BY due_date",
                status
            )
        else:
            rows = await conn.fetch("SELECT * FROM solon_compliance ORDER BY due_date NULLS LAST")
        return [dict(r) for r in rows]


@app.get("/compliance/due")
async def due_compliance(days: int = 30):
    """Get compliance items due within N days"""
    if not pool:
        return []

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM solon_compliance
            WHERE status = 'pending'
            AND due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + $1
            ORDER BY due_date
        """, days)
        return [dict(r) for r in rows]


# =============================================================================
# ATTORNEY MEETING PREP
# =============================================================================

@app.post("/prep/attorney")
async def prep_attorney_meeting(topics: List[str], context: Optional[str] = None):
    """Generate attorney meeting prep"""
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="AI not configured")

    # Gather current situation
    situation = await get_situation()
    contracts = await list_contracts(status='active')
    compliance = await due_compliance(days=90)

    prompt = f"""Prepare me for a meeting with my attorney.

Topics to discuss: {', '.join(topics)}
Additional context: {context or 'None'}

My current legal situation:
{json.dumps(situation, indent=2, default=str)}

Active contracts:
{json.dumps(contracts[:10], indent=2, default=str)}

Upcoming compliance:
{json.dumps(compliance, indent=2, default=str)}

Please provide:
1. Key questions to ask about each topic
2. Documents I should bring
3. Background context I should understand
4. Potential issues or risks to discuss
5. Action items to prepare before the meeting

Be specific and practical."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "topics": topics,
        "prep": response.content[0].text,
        "situation_summary": f"{len(situation)} tracked items, {len(contracts)} active contracts"
    }


# =============================================================================
# STATUS
# =============================================================================

@app.get("/status")
async def solon_status():
    """Get SOLON dashboard"""
    if not pool:
        return {"solon_says": "The law awaits your queries."}

    async with pool.acquire() as conn:
        contracts_expiring = await conn.fetchval("""
            SELECT COUNT(*) FROM solon_contracts
            WHERE status = 'active' AND expiration_date < CURRENT_DATE + 30
        """)

        compliance_due = await conn.fetchval("""
            SELECT COUNT(*) FROM solon_compliance
            WHERE status = 'pending' AND due_date < CURRENT_DATE + 30
        """)

        situation_count = await conn.fetchval("SELECT COUNT(*) FROM solon_situation")

        return {
            "situation_items": situation_count,
            "contracts_expiring_30d": contracts_expiring,
            "compliance_due_30d": compliance_due,
            "summary": f"{situation_count} tracked items, {contracts_expiring} contracts expiring soon",
            "solon_says": generate_solon_status(contracts_expiring, compliance_due)
        }


def generate_solon_status(contracts_expiring, compliance_due):
    if contracts_expiring > 0 and compliance_due > 0:
        return f"Attention required: {contracts_expiring} contracts expiring and {compliance_due} compliance items due."
    elif contracts_expiring > 0:
        return f"{contracts_expiring} contracts approaching expiration. Review recommended."
    elif compliance_due > 0:
        return f"{compliance_due} compliance matters require attention."
    else:
        return "Legal matters are in order. The law is satisfied."


# =============================================================================
# STARTUP
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8210)
