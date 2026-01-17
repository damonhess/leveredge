#!/usr/bin/env python3
"""
CROESUS - AI-Powered Tax & Wealth Advisor Agent
Port: 8211

Named after Croesus, King of Lydia renowned for his vast wealth.
Provides tax INFORMATION (not advice) with authoritative citations.

CRITICAL SAFETY:
- Always includes disclaimers
- Never provides tax advice
- Cites IRS publications and state codes
- Says "I don't know" when uncertain
- Recommends CPA consultation

V1 CAPABILITIES:
- Multi-jurisdiction tax questions (Federal, CA, NV)
- Tax liability estimation
- Deduction identification
- Tax planning strategies
- Deadline tracking
- Wealth building guidance

JURISDICTIONS:
- US Federal (comprehensive)
- California (deep)
- Nevada (deep)

KEY 2026 TAX CHANGES (OBBBA):
- 100% bonus depreciation permanent
- 20% QBI deduction permanent with $400 minimum
- CA business credits capped at $5M/year (2024-2026)
- CA NOL suspended (2024-2027)
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from decimal import Decimal
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.insert(0, '/opt/leveredge/shared')
from aria_reporter import ARIAReporter
from cost_tracker import CostTracker

app = FastAPI(
    title="CROESUS",
    description="AI-Powered Tax & Wealth Advisor - Tax Information Only",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Initialize clients
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
cost_tracker = CostTracker("CROESUS")
aria_reporter = ARIAReporter("CROESUS")

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Mandatory disclaimer
MANDATORY_DISCLAIMER = """

---
**DISCLAIMER:** This information is provided for educational purposes only and does not constitute tax advice. Tax situations are highly fact-specific. For advice about your specific situation, please consult with a CPA or qualified tax professional. Tax laws change frequently - verify current rules before making decisions.
"""

# =============================================================================
# TAX BRACKETS AND RATES (2026)
# =============================================================================

# Federal 2026 Tax Brackets (Single)
FEDERAL_BRACKETS_SINGLE_2026 = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float('inf'), 0.37)
]

# Federal 2026 Tax Brackets (Married Filing Jointly)
FEDERAL_BRACKETS_MFJ_2026 = [
    (23200, 0.10),
    (94300, 0.12),
    (201050, 0.22),
    (383900, 0.24),
    (487450, 0.32),
    (731200, 0.35),
    (float('inf'), 0.37)
]

# California 2026 Tax Brackets (Single)
CA_BRACKETS_SINGLE_2026 = [
    (10412, 0.01),
    (24684, 0.02),
    (38959, 0.04),
    (54081, 0.06),
    (68350, 0.08),
    (349137, 0.093),
    (418961, 0.103),
    (698271, 0.113),
    (float('inf'), 0.123)
]

# Self-employment tax rate
SE_TAX_RATE = 0.153  # 15.3% (12.4% SS + 2.9% Medicare)
SE_TAX_INCOME_FACTOR = 0.9235  # SE tax applies to 92.35% of SE income

# QBI Deduction
QBI_DEDUCTION_RATE = 0.20  # 20% of qualified business income
QBI_MINIMUM = 400  # $400 minimum with $1K+ income (OBBBA)

# =============================================================================
# MODELS
# =============================================================================

class TaxQuestionRequest(BaseModel):
    question: str = Field(..., description="The tax question to answer")
    jurisdiction: Optional[str] = Field(None, description="federal, CA, or NV")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

class TaxEstimateRequest(BaseModel):
    tax_year: int = Field(2026, description="Tax year to estimate")
    gross_income: float = Field(..., description="Annual gross income")
    deductions: Optional[Dict[str, float]] = Field(None, description="Deductions by category")
    filing_status: str = Field(..., description="single, married_joint, married_separate, hoh")
    state: str = Field(..., description="State of residence")
    business_type: Optional[str] = Field(None, description="sole_prop, llc, s_corp, c_corp")
    include_se_tax: bool = Field(True, description="Include self-employment tax")

class DeductionFinderRequest(BaseModel):
    business_type: str = Field(..., description="sole_prop, llc, s_corp, c_corp")
    industry: Optional[str] = Field(None, description="Type of business")
    work_from_home: bool = Field(False, description="Do you work from home?")
    has_vehicle: bool = Field(False, description="Do you use a vehicle for business?")
    current_deductions: Optional[List[str]] = Field(None, description="Already-claimed deductions")

class TaxPlanningRequest(BaseModel):
    current_situation: Dict[str, Any] = Field(..., description="Current tax situation")
    goals: Optional[List[str]] = Field(None, description="Tax planning goals")
    planning_horizon: str = Field("annual", description="annual or multi_year")

class WealthStrategyRequest(BaseModel):
    current_income: float = Field(..., description="Annual income")
    savings_rate: Optional[float] = Field(None, description="Current savings rate (0-1)")
    existing_accounts: Optional[List[str]] = Field(None, description="Current investment accounts")
    goals: Optional[List[str]] = Field(None, description="Financial goals")
    risk_tolerance: Optional[str] = Field("moderate", description="low, moderate, high")

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    # Calculate next estimated tax deadline
    tax_deadlines = [
        (date(2026, 1, 15), "Q4 2025 Estimated"),
        (date(2026, 4, 15), "Q1 2026 Estimated / Tax Day"),
        (date(2026, 6, 15), "Q2 2026 Estimated"),
        (date(2026, 9, 15), "Q3 2026 Estimated"),
    ]

    next_deadline = None
    days_to_deadline = None
    for deadline_date, deadline_name in tax_deadlines:
        if deadline_date > today:
            next_deadline = f"{deadline_name} ({deadline_date})"
            days_to_deadline = (deadline_date - today).days
            break

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "days_to_launch": days_to_launch,
        "tax_year": 2026,
        "next_estimated_due": next_deadline,
        "days_to_deadline": days_to_deadline
    }

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(time_context: dict) -> str:
    """Build CROESUS system prompt with safety requirements"""

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

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}
- Tax Year: {time_context['tax_year']}
- Next Estimated Payment Due: {time_context['next_estimated_due']}
- Days to Next Deadline: {time_context['days_to_deadline']}

## CURRENT TAX CONTEXT (2026)
Key OBBBA Changes (signed July 4, 2025):
- 100% Bonus Depreciation: Permanently restored
- QBI Deduction: 20% permanent with $400 minimum
- R&D Expenses: Immediately expensible (2025+)
- Employer Childcare Credit: Increased to 40-50%

California Considerations:
- Business Credits: Capped at $5M/year (2024-2026)
- NOL Deduction: Suspended for certain taxpayers (2024-2027)
- Franchise Tax: $800 minimum for LLCs

Nevada Considerations:
- No state income tax
- Commerce Tax: 0.051% on businesses > $4M gross revenue
- Modified Business Tax (MBT): 1.378% on wages over $50K/quarter

## SOURCE CITATION
Always cite your sources:
- IRS Publications: "Per IRS Publication 535..."
- IRC Sections: "Under IRC Section 162..."
- State Codes: "California Revenue & Tax Code Section..."
- State Franchise Tax Board: "Per FTB guidance..."

## TAX DOMAINS
- Federal Income Tax (personal + business)
- Self-Employment Tax (15.3% on 92.35% of SE income)
- California State Tax (up to 12.3%)
- Nevada Tax (no income tax, commerce tax)
- Estimated Taxes (quarterly payments)
- Business Deductions (home office, vehicle, equipment)
- Retirement Accounts (SEP-IRA, Solo 401(k), Traditional/Roth)
- Entity Selection (S-Corp election, LLC taxation)

## RESPONSE FORMAT

For tax questions:
1. Direct answer (if confident) with applicable tax law
2. Relevant IRC sections, IRS publications, or state codes
3. Key considerations and scenarios
4. Confidence level
5. MANDATORY DISCLAIMER
6. "Consult a CPA for advice about your specific situation"

For estimates:
1. Input summary
2. Calculation breakdown
3. Federal/state/SE components
4. Effective vs marginal rates
5. Quarterly payment schedule
6. Important caveats
7. DISCLAIMER

## YOUR MISSION
Provide accurate, well-sourced tax information.
Help users understand their tax situation.
Never provide tax advice - that's for CPAs.
Always prioritize accuracy and proper disclaimers.
When in doubt, recommend a CPA.
"""

# =============================================================================
# TAX CALCULATION HELPERS
# =============================================================================

def calculate_federal_tax(taxable_income: float, filing_status: str) -> dict:
    """Calculate federal income tax using 2026 brackets"""

    if filing_status == "married_joint":
        brackets = FEDERAL_BRACKETS_MFJ_2026
    else:
        brackets = FEDERAL_BRACKETS_SINGLE_2026

    tax = 0
    remaining_income = taxable_income
    prev_bracket = 0
    bracket_breakdown = []

    for bracket_top, rate in brackets:
        if remaining_income <= 0:
            break

        taxable_in_bracket = min(remaining_income, bracket_top - prev_bracket)
        tax_in_bracket = taxable_in_bracket * rate

        if taxable_in_bracket > 0:
            bracket_breakdown.append({
                "bracket": f"${prev_bracket:,.0f} - ${bracket_top:,.0f}",
                "rate": f"{rate * 100:.0f}%",
                "income_in_bracket": taxable_in_bracket,
                "tax": tax_in_bracket
            })

        tax += tax_in_bracket
        remaining_income -= taxable_in_bracket
        prev_bracket = bracket_top

    # Find marginal rate
    marginal_rate = 0
    for bracket_top, rate in brackets:
        if taxable_income <= bracket_top:
            marginal_rate = rate
            break
        marginal_rate = rate

    return {
        "tax": tax,
        "effective_rate": (tax / taxable_income * 100) if taxable_income > 0 else 0,
        "marginal_rate": marginal_rate * 100,
        "bracket_breakdown": bracket_breakdown
    }

def calculate_ca_tax(taxable_income: float) -> dict:
    """Calculate California state income tax using 2026 brackets"""

    brackets = CA_BRACKETS_SINGLE_2026
    tax = 0
    remaining_income = taxable_income
    prev_bracket = 0

    for bracket_top, rate in brackets:
        if remaining_income <= 0:
            break

        taxable_in_bracket = min(remaining_income, bracket_top - prev_bracket)
        tax += taxable_in_bracket * rate
        remaining_income -= taxable_in_bracket
        prev_bracket = bracket_top

    return {
        "tax": tax,
        "effective_rate": (tax / taxable_income * 100) if taxable_income > 0 else 0
    }

def calculate_se_tax(net_se_income: float) -> dict:
    """Calculate self-employment tax"""

    # SE tax applies to 92.35% of net SE income
    se_taxable = net_se_income * SE_TAX_INCOME_FACTOR

    # Social Security tax (12.4%) only on first $168,600 (2026)
    ss_wage_base = 168600
    ss_tax = min(se_taxable, ss_wage_base) * 0.124

    # Medicare tax (2.9%) on all SE income
    medicare_tax = se_taxable * 0.029

    # Additional Medicare tax (0.9%) on income over $200K (single)
    additional_medicare = max(0, se_taxable - 200000) * 0.009

    total_se_tax = ss_tax + medicare_tax + additional_medicare

    return {
        "se_taxable_income": se_taxable,
        "social_security_tax": ss_tax,
        "medicare_tax": medicare_tax,
        "additional_medicare_tax": additional_medicare,
        "total_se_tax": total_se_tax,
        "se_deduction": total_se_tax / 2  # Deductible portion
    }

def calculate_qbi_deduction(qualified_business_income: float) -> float:
    """Calculate QBI deduction (20% with $400 minimum per OBBBA)"""
    if qualified_business_income >= 1000:
        return max(400, qualified_business_income * QBI_DEDUCTION_RATE)
    elif qualified_business_income > 0:
        return qualified_business_income * QBI_DEDUCTION_RATE
    return 0

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CROESUS",
        "version": "1.0.0",
        "port": 8211,
        "capabilities": ["tax_questions", "tax_estimates", "deductions", "planning", "wealth_strategy"]
    }

@app.get("/tax/deadlines")
async def get_tax_deadlines(days_ahead: int = 90):
    """Get upcoming tax deadlines"""
    today = date.today()
    end_date = date(today.year, today.month, today.day)

    # Key tax deadlines for 2026
    deadlines = [
        {"date": "2026-01-15", "title": "Q4 2025 Estimated Tax", "type": "estimated", "description": "Fourth quarter 2025 estimated tax payment (Form 1040-ES)"},
        {"date": "2026-01-31", "title": "W-2/1099 Filing", "type": "form", "description": "Issue W-2s and 1099s to contractors/employees"},
        {"date": "2026-03-15", "title": "S-Corp/Partnership Returns", "type": "filing", "description": "Form 1120-S and 1065 due"},
        {"date": "2026-04-15", "title": "Tax Day", "type": "filing", "description": "Form 1040 and 1120 due; Q1 2026 estimated payment"},
        {"date": "2026-06-15", "title": "Q2 Estimated Tax", "type": "estimated", "description": "Second quarter 2026 estimated payment"},
        {"date": "2026-09-15", "title": "Q3 Estimated Tax / Extended Returns", "type": "estimated", "description": "Q3 estimated payment; extended S-Corp/Partnership returns due"},
        {"date": "2026-10-15", "title": "Extended Individual/C-Corp", "type": "filing", "description": "Extended Form 1040 and 1120 due"},
    ]

    # Filter to upcoming deadlines
    upcoming = []
    next_deadline = None
    for d in deadlines:
        deadline_date = date.fromisoformat(d["date"])
        days_until = (deadline_date - today).days

        if 0 <= days_until <= days_ahead:
            d["days_until"] = days_until
            d["urgent"] = days_until <= 14
            upcoming.append(d)

            if next_deadline is None:
                next_deadline = d

    return {
        "deadlines": upcoming,
        "next_deadline": next_deadline,
        "count": len(upcoming),
        "disclaimer": "Deadlines may vary based on your specific situation. Consult a CPA."
    }

@app.post("/tax/question")
async def answer_tax_question(request: TaxQuestionRequest, background_tasks: BackgroundTasks):
    """
    Answer a tax question with citations and confidence scoring.

    ALWAYS includes disclaimer and recommends CPA consultation.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    user_prompt = f"""Please answer the following tax question:

**Question:** {request.question}

**Jurisdiction:** {request.jurisdiction or "Please determine the most relevant jurisdiction"}

{"**Additional Context:** " + json.dumps(request.context) if request.context else ""}

Remember to:
1. Cite specific IRC sections, IRS publications, or state tax codes
2. State your confidence level
3. Include the mandatory disclaimer
4. Recommend consulting a CPA for specific advice
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
        citations = []

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
        citation_patterns = [
            r'IRC Section \d+',
            r'IRS Publication \d+',
            r'26 U\.S\.C\. §\s*\d+',
            r'Cal\. Rev\. & Tax\. Code §\s*\d+',
        ]
        for pattern in citation_patterns:
            found = re.findall(pattern, response_text)
            citations.extend(found)

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/tax/question",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            web_searches=web_searches,
            metadata={
                "jurisdiction": request.jurisdiction,
                "citations_count": len(citations)
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="answered_tax_question",
            target=request.question[:100],
            details={
                "jurisdiction": request.jurisdiction,
                "citations_count": len(citations),
                "web_searches": web_searches
            },
            domain="tax",
            importance="medium"
        )

        return {
            "answer": response_text,
            "citations": list(set(citations)),
            "jurisdiction": request.jurisdiction,
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "consult_cpa": True
        }

    except Exception as e:
        await aria_reporter.report_error(
            error_type="tax_question_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error processing tax question: {str(e)}")

@app.post("/tax/estimate")
async def estimate_tax(request: TaxEstimateRequest, background_tasks: BackgroundTasks):
    """
    Estimate tax liability based on income and deductions.

    Uses 2026 tax brackets and rates.
    """
    try:
        # Calculate total deductions
        total_deductions = sum(request.deductions.values()) if request.deductions else 0

        # Standard deduction for 2026 (estimated)
        standard_deduction = {
            "single": 15000,
            "married_joint": 30000,
            "married_separate": 15000,
            "hoh": 22500
        }.get(request.filing_status, 15000)

        # Use greater of itemized or standard
        deduction_used = max(total_deductions, standard_deduction)
        deduction_type = "itemized" if total_deductions > standard_deduction else "standard"

        # Calculate SE tax if applicable
        se_result = {"total_se_tax": 0, "se_deduction": 0}
        if request.include_se_tax and request.business_type in ["sole_prop", "llc"]:
            se_result = calculate_se_tax(request.gross_income)

        # Calculate QBI deduction
        qbi_deduction = 0
        if request.business_type in ["sole_prop", "llc", "s_corp"]:
            qbi_deduction = calculate_qbi_deduction(request.gross_income - total_deductions)

        # Calculate taxable income
        taxable_income = request.gross_income - deduction_used - se_result["se_deduction"] - qbi_deduction
        taxable_income = max(0, taxable_income)

        # Calculate federal tax
        federal_result = calculate_federal_tax(taxable_income, request.filing_status)

        # Calculate state tax
        state_tax = 0
        state_result = {"tax": 0, "effective_rate": 0}
        if request.state == "CA":
            state_result = calculate_ca_tax(taxable_income)
            state_tax = state_result["tax"]
        # Nevada has no state income tax

        # Total tax
        total_tax = federal_result["tax"] + se_result["total_se_tax"] + state_tax

        # Quarterly payments
        quarterly_payment = total_tax / 4

        # Build response
        estimate = {
            "tax_year": request.tax_year,
            "inputs": {
                "gross_income": request.gross_income,
                "filing_status": request.filing_status,
                "state": request.state,
                "business_type": request.business_type
            },
            "deductions": {
                "type": deduction_type,
                "amount": deduction_used,
                "itemized_total": total_deductions,
                "standard_deduction": standard_deduction,
                "se_deduction": se_result["se_deduction"],
                "qbi_deduction": qbi_deduction
            },
            "taxable_income": taxable_income,
            "federal_tax": {
                "tax": federal_result["tax"],
                "effective_rate": federal_result["effective_rate"],
                "marginal_rate": federal_result["marginal_rate"],
                "brackets": federal_result["bracket_breakdown"]
            },
            "se_tax": {
                "total": se_result["total_se_tax"],
                "social_security": se_result.get("social_security_tax", 0),
                "medicare": se_result.get("medicare_tax", 0)
            } if request.include_se_tax else None,
            "state_tax": {
                "state": request.state,
                "tax": state_tax,
                "effective_rate": state_result["effective_rate"]
            } if request.state == "CA" else {"state": request.state, "tax": 0, "note": "No state income tax"},
            "total_tax": total_tax,
            "effective_rate": (total_tax / request.gross_income * 100) if request.gross_income > 0 else 0,
            "quarterly_payments": {
                "amount": quarterly_payment,
                "schedule": [
                    {"quarter": "Q1", "due": "April 15", "amount": quarterly_payment},
                    {"quarter": "Q2", "due": "June 15", "amount": quarterly_payment},
                    {"quarter": "Q3", "due": "September 15", "amount": quarterly_payment},
                    {"quarter": "Q4", "due": "January 15 (next year)", "amount": quarterly_payment}
                ]
            },
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "notes": [
                "This is an ESTIMATE for planning purposes only",
                "Actual taxes may vary based on your specific situation",
                "Consult a CPA for accurate tax preparation",
                "Tax laws change - verify current rules"
            ]
        }

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/tax/estimate",
            model="calculation",
            input_tokens=0,
            output_tokens=0,
            metadata={
                "gross_income": request.gross_income,
                "total_tax": total_tax,
                "state": request.state
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="tax_estimate_calculated",
            target=f"{request.tax_year}_{request.filing_status}",
            details={
                "gross_income": request.gross_income,
                "total_tax": total_tax,
                "effective_rate": estimate["effective_rate"],
                "state": request.state
            },
            domain="tax",
            importance="medium"
        )

        return estimate

    except Exception as e:
        await aria_reporter.report_error(
            error_type="tax_estimate_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error calculating estimate: {str(e)}")

@app.post("/tax/deductions")
async def find_deductions(request: DeductionFinderRequest, background_tasks: BackgroundTasks):
    """
    Find potential tax deductions based on business type and situation.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    user_prompt = f"""Please identify potential tax deductions for the following business:

**Business Type:** {request.business_type}
**Industry:** {request.industry or "Not specified"}
**Work from Home:** {"Yes" if request.work_from_home else "No"}
**Uses Vehicle for Business:** {"Yes" if request.has_vehicle else "No"}
**Currently Claimed Deductions:** {", ".join(request.current_deductions) if request.current_deductions else "None specified"}

Please provide:
1. **Potential Deductions**: List each deduction with:
   - Category
   - Estimated value range (if applicable)
   - Documentation required
   - IRS guidance reference
2. **Commonly Missed Deductions**: Deductions people often overlook
3. **Documentation Checklist**: What records to keep
4. **Cautions**: Deductions that require careful documentation

Focus on deductions specific to:
- {request.business_type} business structure
- {request.industry or "general business"} industry
{"- Home office deduction (simplified vs. regular method)" if request.work_from_home else ""}
{"- Vehicle expenses (standard mileage vs. actual expense)" if request.has_vehicle else ""}

Remember: This is informational only, not tax advice. Recommend CPA consultation.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text

        if "DISCLAIMER" not in response_text:
            response_text += MANDATORY_DISCLAIMER

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/tax/deductions",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            metadata={
                "business_type": request.business_type,
                "industry": request.industry
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="deductions_identified",
            target=f"{request.business_type}_{request.industry or 'general'}",
            details={
                "business_type": request.business_type,
                "work_from_home": request.work_from_home,
                "has_vehicle": request.has_vehicle
            },
            domain="tax",
            importance="medium"
        )

        return {
            "analysis": response_text,
            "business_type": request.business_type,
            "industry": request.industry,
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "consult_cpa": True
        }

    except Exception as e:
        await aria_reporter.report_error(
            error_type="deduction_finder_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error finding deductions: {str(e)}")

@app.post("/tax/planning")
async def tax_planning(request: TaxPlanningRequest, background_tasks: BackgroundTasks):
    """
    Get tax planning strategies based on current situation.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    user_prompt = f"""Please provide tax planning strategies for the following situation:

**Current Situation:**
{json.dumps(request.current_situation, indent=2)}

**Goals:** {", ".join(request.goals) if request.goals else "Minimize tax liability"}
**Planning Horizon:** {request.planning_horizon}

Please provide:
1. **Recommended Strategies**: For each strategy, include:
   - Strategy name
   - Estimated tax savings
   - Requirements/eligibility
   - Implementation steps
   - Deadline (if applicable)
   - IRS/state guidance reference

2. **Strategy Categories**:
   - Income timing (deferral/acceleration)
   - Entity structure optimization
   - Retirement contributions
   - Deduction maximization
   - State tax planning (CA vs NV if applicable)

3. **Implementation Timeline**: When to take action

4. **Cautions**: Strategies that require professional guidance

Key 2026 Considerations:
- 100% bonus depreciation is permanent (OBBBA)
- QBI deduction is permanent at 20%
- CA business credit cap: $5M/year
- CA NOL suspension through 2027

Remember: These are strategy OPTIONS for discussion with a CPA, not advice.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=5000,
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

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/tax/planning",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            web_searches=web_searches,
            metadata={
                "planning_horizon": request.planning_horizon,
                "goals": request.goals
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="tax_planning_completed",
            target=request.planning_horizon,
            details={
                "goals": request.goals,
                "web_searches": web_searches
            },
            domain="tax",
            importance="high"
        )

        return {
            "strategies": response_text,
            "planning_horizon": request.planning_horizon,
            "goals": request.goals,
            "disclaimer": MANDATORY_DISCLAIMER.strip(),
            "consult_cpa": True
        }

    except Exception as e:
        await aria_reporter.report_error(
            error_type="tax_planning_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error generating plan: {str(e)}")

@app.post("/wealth/strategy")
async def wealth_strategy(request: WealthStrategyRequest, background_tasks: BackgroundTasks):
    """
    Get wealth building guidance.

    NOT investment advice - general information only.
    """
    time_context = get_time_context()
    system_prompt = build_system_prompt(time_context)

    user_prompt = f"""Please provide wealth building guidance for the following situation:

**Annual Income:** ${request.current_income:,.0f}
**Current Savings Rate:** {f"{request.savings_rate * 100:.0f}%" if request.savings_rate else "Not specified"}
**Existing Accounts:** {", ".join(request.existing_accounts) if request.existing_accounts else "Not specified"}
**Goals:** {", ".join(request.goals) if request.goals else "General wealth building"}
**Risk Tolerance:** {request.risk_tolerance}

Please provide:

1. **Savings Rate Analysis**: Is current rate optimal?

2. **Tax-Advantaged Account Comparison**:
   | Account Type | Contribution Limit | Tax Treatment | Best For |
   |--------------|-------------------|---------------|----------|
   Compare: Traditional 401(k), Roth 401(k), Solo 401(k), SEP-IRA, Traditional IRA, Roth IRA, HSA

3. **Recommended Account Priority**: Which accounts to fund first and why

4. **Emergency Fund Guidance**: Recommended size and where to keep it

5. **Debt Strategy**: If applicable, general guidance on debt payoff vs investing

6. **Key Milestones**: Timeline-based goals

Remember: This is GENERAL INFORMATION about wealth building concepts, NOT personalized investment advice. Recommend consulting a financial advisor for specific advice.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text

        if "DISCLAIMER" not in response_text:
            response_text += "\n\n---\n**DISCLAIMER:** This is general information about wealth building concepts, not personalized investment advice. Consult a qualified financial advisor for advice specific to your situation."

        # Log usage
        await cost_tracker.log_usage(
            endpoint="/wealth/strategy",
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            metadata={
                "income": request.current_income,
                "goals": request.goals
            }
        )

        # Report to ARIA
        background_tasks.add_task(
            aria_reporter.report_action,
            action="wealth_strategy_provided",
            target="wealth_guidance",
            details={
                "income_range": f"${request.current_income:,.0f}",
                "goals": request.goals
            },
            domain="wealth",
            importance="medium"
        )

        return {
            "guidance": response_text,
            "income": request.current_income,
            "goals": request.goals,
            "disclaimer": "This is general information, not personalized investment advice. Consult a financial advisor.",
            "consult_advisor": True
        }

    except Exception as e:
        await aria_reporter.report_error(
            error_type="wealth_strategy_failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Error generating guidance: {str(e)}")

# =============================================================================
# STARTUP
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8211)
