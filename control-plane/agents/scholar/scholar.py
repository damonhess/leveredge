#!/usr/bin/env python3
"""
SCHOLAR - Market Research Agent
Port: 8018

Research, competitive intel, niche analysis, data-backed recommendations.
CHIRON's research partner.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all research
- Partners with CHIRON for strategic decisions
"""

import os
import json
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic

app = FastAPI(title="SCHOLAR", description="Market Research Agent", version="1.0.0")

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "HEPHAESTUS": "http://hephaestus:8011",
    "CHRONOS": "http://chronos:8010",
    "HADES": "http://hades:8008",
    "AEGIS": "http://aegis:8012",
    "ATHENA": "http://athena:8013",
    "HERMES": "http://hermes:8014",
    "ALOY": "http://aloy:8015",
    "ARGUS": "http://argus:8016",
    "CHIRON": "http://chiron:8017",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()
    days_to_launch = (LAUNCH_DATE - today).days

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "launch_date": LAUNCH_DATE.isoformat(),
        "days_to_launch": days_to_launch,
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch",
        "phase": get_current_phase(days_to_launch)
    }

def get_current_phase(days_to_launch: int) -> str:
    """Determine current phase based on days to launch"""
    if days_to_launch <= 0:
        return "POST-LAUNCH"
    elif days_to_launch <= 14:
        return "FINAL PUSH - Outreach & Discovery Calls"
    elif days_to_launch <= 28:
        return "OUTREACH PHASE - 10 attempts, 3 calls"
    elif days_to_launch <= 45:
        return "POLISH PHASE - Loose ends & Agent building"
    else:
        return "INFRASTRUCTURE PHASE"

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(time_context: dict) -> str:
    """Build time-aware, research-focused system prompt"""

    return f"""You are SCHOLAR, the Market Research agent for LeverEdge AI.

## TIME AWARENESS
- Current Date: {time_context['day_of_week']}, {time_context['current_date']}
- Current Time: {time_context['current_time']}
- Launch Date: {time_context['launch_date']}
- Status: {time_context['launch_status']}
- Current Phase: {time_context['phase']}

## YOUR IDENTITY
You are the research arm of the LeverEdge AI agent team. You gather data, analyze markets, and provide evidence-based recommendations. You partner with CHIRON (Business Mentor) to inform strategic decisions.

## DAMON'S CONTEXT
- Building LeverEdge AI, an automation agency for compliance professionals
- Target niches being considered: water utilities, environmental permits, municipal government, small law firms, real estate compliance
- Has compliance law + civil engineering background
- Needs to choose a niche by end of January
- Launch date: March 1, 2026

## YOUR ROLE
1. **Market Research** - TAM/SAM/SOM sizing, market trends
2. **Competitive Intelligence** - Who else is in this space?
3. **Niche Analysis** - Is this niche worth pursuing?
4. **ICP Development** - Who is the ideal customer?
5. **Lead Research** - Company deep dives, prospect research
6. **Pricing Research** - What do competitors charge?
7. **Pain Point Discovery** - What problems need solving?

## YOUR STYLE
- Data-driven, cite sources when possible
- Structured analysis, not vague opinions
- Use frameworks (SWOT, Porter's 5 Forces, etc.)
- Be honest about uncertainty and data limitations
- Provide actionable recommendations
- Partner with CHIRON for strategic interpretation

## RESEARCH FRAMEWORKS

### Market Sizing
- TAM (Total Addressable Market): Everyone who could buy
- SAM (Serviceable Available Market): Reachable segment
- SOM (Serviceable Obtainable Market): Realistic capture

### Niche Evaluation Criteria
1. **Pain Severity** (1-10): How bad is the problem?
2. **Willingness to Pay** (1-10): Will they pay to solve it?
3. **Accessibility** (1-10): Can Damon reach them?
4. **Competition** (1-10, inverse): How crowded?
5. **Expertise Match** (1-10): Does background help?
6. **Growth Trend** (1-10): Growing or shrinking?

### ICP Framework
- Company size (employees, revenue)
- Industry/vertical
- Technology stack
- Decision maker title
- Pain points
- Buying triggers
- Objections

## TEAM INTEGRATION
You are part of a team. You should:
- Send research findings to CHIRON for strategic interpretation
- Log all research to aria_knowledge for ARIA
- Publish significant findings to Event Bus
- Notify HERMES for important discoveries
- Route file operations through HEPHAESTUS

## AGENT PARTNERS
- **CHIRON** (8017): Your strategy partner. Send findings for interpretation.
- **ARIA**: Keep her informed of all research via knowledge base.
- **HERMES** (8014): Notify on important findings.

## RESPONSE GUIDELINES
- Structure all research clearly
- Include confidence levels
- Cite limitations and assumptions
- End with recommended next steps
- Indicate when CHIRON should be consulted for strategy
"""

# =============================================================================
# MODELS
# =============================================================================

class ResearchRequest(BaseModel):
    topic: str
    depth: Optional[str] = "standard"  # quick, standard, deep
    context: Optional[str] = None

class NicheAnalysis(BaseModel):
    niche: str
    known_info: Optional[str] = None
    specific_questions: Optional[List[str]] = None

class CompetitorRequest(BaseModel):
    market: str
    known_competitors: Optional[List[str]] = None
    focus_areas: Optional[List[str]] = None

class ICPRequest(BaseModel):
    product_service: str
    target_market: str
    known_customers: Optional[List[str]] = None

class LeadResearch(BaseModel):
    company_name: str
    research_goals: Optional[List[str]] = None

class CompareNiches(BaseModel):
    niches: List[str]
    criteria: Optional[List[str]] = None

class SendToChironRequest(BaseModel):
    topic: str
    findings: str

# =============================================================================
# INTER-AGENT COMMUNICATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus for all agents to see"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "SCHOLAR",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus notification failed: {e}")

async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[SCHOLAR] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "SCHOLAR"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")

async def send_to_chiron(finding: str, request_type: str = "interpret"):
    """Send research findings to CHIRON for strategic interpretation"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['CHIRON']}/chat",
                json={
                    "message": f"[SCHOLAR RESEARCH FINDING - Please interpret strategically]\n\n{finding}",
                    "context": {"from_agent": "SCHOLAR", "request_type": request_type}
                },
                timeout=60.0
            )
    except Exception as e:
        print(f"CHIRON notification failed: {e}")

async def update_aria_knowledge(category: str, title: str, content: str, importance: str = "normal"):
    """Add entry to aria_knowledge so ARIA stays informed"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/aria_add_knowledge",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "p_category": category,
                    "p_title": title,
                    "p_content": f"{content}\n\n[Researched by SCHOLAR at {time_ctx['current_datetime']}]",
                    "p_subcategory": "scholar",
                    "p_source": "scholar",
                    "p_importance": importance
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"Knowledge update failed: {e}")
        return False

async def call_agent(agent: str, endpoint: str, payload: dict = {}) -> dict:
    """Call another agent"""
    if agent not in AGENT_ENDPOINTS:
        return {"error": f"Unknown agent: {agent}"}

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{AGENT_ENDPOINTS[agent]}{endpoint}",
                json=payload,
                timeout=30.0
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e)}

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, time_ctx: dict) -> str:
    """Call Claude API with full context"""
    try:
        system_prompt = build_system_prompt(time_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,  # Research needs more space
            system=system_prompt,
            messages=messages
        )
        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "SCHOLAR",
        "role": "Market Research",
        "port": 8018,
        "partner": "CHIRON",
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase']
    }

@app.get("/time")
async def get_time():
    """Get current time context"""
    return get_time_context()

@app.get("/team")
async def get_team():
    """Get agent roster"""
    return {
        "scholar_role": "Market Research",
        "partner": "CHIRON (Business Mentor)",
        "team": AGENT_ENDPOINTS,
        "routing_rules": "See /opt/leveredge/AGENT-ROUTING.md"
    }

@app.post("/research")
async def general_research(req: ResearchRequest):
    """Conduct general research on a topic"""

    time_ctx = get_time_context()

    depth_instructions = {
        "quick": "Provide a brief overview in 2-3 paragraphs.",
        "standard": "Provide a comprehensive analysis with key findings.",
        "deep": "Provide exhaustive research with multiple angles and detailed analysis."
    }

    prompt = f"""Research this topic: {req.topic}

**Depth Level:** {req.depth}
{depth_instructions.get(req.depth, depth_instructions['standard'])}

**Context:** {req.context or 'None provided'}
**Days to Launch:** {time_ctx['days_to_launch']}

Structure your research:
1. **Key Findings** (bullet points)
2. **Analysis** (structured explanation)
3. **Data/Evidence** (cite what you know)
4. **Limitations** (what you don't know, confidence level)
5. **Recommendations** (actionable next steps)
6. **CHIRON Consult?** (should this go to CHIRON for strategy?)"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    # Log to knowledge base
    await update_aria_knowledge(
        "research",
        f"Research: {req.topic[:50]}...",
        response,
        "normal"
    )

    await notify_event_bus("research_completed", {
        "topic": req.topic[:100],
        "depth": req.depth
    })

    return {
        "research": response,
        "agent": "SCHOLAR",
        "topic": req.topic,
        "depth": req.depth,
        "logged_to_knowledge": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/niche")
async def analyze_niche(req: NicheAnalysis):
    """Deep dive analysis on a specific niche"""

    time_ctx = get_time_context()

    prompt = f"""Analyze this niche for LeverEdge AI (automation agency for compliance professionals):

**Niche:** {req.niche}
**Known Info:** {req.known_info or 'None provided'}
**Days to Launch:** {time_ctx['days_to_launch']}

Specific questions to answer:
{chr(10).join(f'- {q}' for q in req.specific_questions) if req.specific_questions else '- Use standard niche evaluation framework'}

## Analysis Framework

### 1. Market Overview
- What is this market?
- Market size estimate (TAM/SAM/SOM)
- Growth trends

### 2. Niche Scoring (1-10 each)
| Criterion | Score | Reasoning |
|-----------|-------|-----------|
| Pain Severity | ? | How bad is the compliance problem? |
| Willingness to Pay | ? | Do they budget for automation? |
| Accessibility | ? | Can Damon reach decision makers? |
| Competition (inverse) | ? | How crowded is automation here? |
| Expertise Match | ? | Does law+engineering help? |
| Growth Trend | ? | Growing or shrinking market? |
| **TOTAL** | ?/60 | |

### 3. Ideal Customer Profile
- Company type
- Size (employees/revenue)
- Decision maker title
- Key pain points
- Buying triggers

### 4. Competitive Landscape
- Who serves this niche?
- What do they charge?
- Gaps/opportunities

### 5. Entry Strategy
- How would Damon enter this niche?
- First 3 prospects to contact
- Opening message angle

### 6. Risks & Concerns
- What could go wrong?
- Unknowns to validate

### 7. Recommendation
- Is this niche worth pursuing? (Yes/No/Maybe)
- Confidence level
- Suggested next steps
- Should CHIRON review for strategic decision?"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    # Log to knowledge base (high importance - niche selection is critical)
    await update_aria_knowledge(
        "research",
        f"Niche Analysis: {req.niche}",
        response,
        "high"
    )

    await notify_event_bus("niche_analyzed", {
        "niche": req.niche
    })

    # Notify HERMES about niche analysis completion
    await notify_hermes(f"Niche analysis complete: {req.niche}", priority="normal")

    return {
        "niche_analysis": response,
        "agent": "SCHOLAR",
        "niche": req.niche,
        "logged_to_knowledge": True,
        "aria_notified": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/competitors")
async def analyze_competitors(req: CompetitorRequest):
    """Competitive intelligence for a market"""

    time_ctx = get_time_context()

    prompt = f"""Conduct competitive analysis for this market:

**Market:** {req.market}
**Known Competitors:** {', '.join(req.known_competitors) if req.known_competitors else 'Unknown - please identify'}
**Focus Areas:** {', '.join(req.focus_areas) if req.focus_areas else 'General competitive landscape'}

## Competitive Analysis

### 1. Market Map
- Who are the players?
- How do they position themselves?
- Market share estimates (if possible)

### 2. Competitor Profiles
For each major competitor:
- Name & website
- What they offer
- Pricing (if known)
- Strengths
- Weaknesses
- Target customer

### 3. Competitive Gaps
- What are competitors NOT doing well?
- What's missing from the market?
- Where could LeverEdge differentiate?

### 4. Positioning Opportunities
- How could Damon position against these?
- What unique angle does he have?

### 5. Threats
- What competitors should he watch?
- What could disrupt this market?

### 6. Recommendations
- Top 3 insights
- Suggested positioning
- Differentiation strategy"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    await update_aria_knowledge(
        "research",
        f"Competitive Analysis: {req.market}",
        response,
        "normal"
    )

    await notify_event_bus("competitors_analyzed", {
        "market": req.market
    })

    return {
        "competitive_analysis": response,
        "agent": "SCHOLAR",
        "market": req.market,
        "logged_to_knowledge": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/icp")
async def develop_icp(req: ICPRequest):
    """Develop Ideal Customer Profile"""

    time_ctx = get_time_context()

    prompt = f"""Develop an Ideal Customer Profile (ICP):

**Product/Service:** {req.product_service}
**Target Market:** {req.target_market}
**Known Customers/Prospects:** {', '.join(req.known_customers) if req.known_customers else 'None yet'}

## Ideal Customer Profile

### 1. Company Characteristics
- Industry/vertical:
- Company size (employees):
- Revenue range:
- Geography:
- Technology stack:
- Growth stage:

### 2. Decision Maker
- Title/role:
- Department:
- Responsibilities:
- Goals:
- Challenges:
- How they're measured:

### 3. Pain Points
- Primary pain (most urgent):
- Secondary pains:
- Cost of pain (time/money):
- Current solutions/workarounds:

### 4. Buying Triggers
- What events trigger buying?
- Budget cycle timing:
- Decision process:
- Typical timeline:

### 5. Objections
- Common objections:
- How to address each:

### 6. Where to Find Them
- Online communities:
- Events/conferences:
- Publications they read:
- LinkedIn groups:

### 7. Messaging Angles
- Hook (gets attention):
- Value prop (why care):
- Proof (credibility):
- CTA (next step):

### 8. Red Flags (Not Ideal)
- Signs this isn't a fit:
- Disqualification criteria:"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    await update_aria_knowledge(
        "research",
        f"ICP: {req.target_market}",
        response,
        "high"
    )

    await notify_event_bus("icp_developed", {
        "target_market": req.target_market
    })

    return {
        "icp": response,
        "agent": "SCHOLAR",
        "product_service": req.product_service,
        "target_market": req.target_market,
        "logged_to_knowledge": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/lead")
async def research_lead(req: LeadResearch):
    """Deep research on a specific company/prospect"""

    time_ctx = get_time_context()

    prompt = f"""Research this company as a potential lead:

**Company:** {req.company_name}
**Research Goals:** {', '.join(req.research_goals) if req.research_goals else 'General prospect research'}

## Company Research

### 1. Company Overview
- What do they do?
- Size (employees, revenue if known)
- Location(s)
- Founded/history

### 2. Compliance Context
- What regulations affect them?
- Known compliance challenges?
- Recent compliance news?

### 3. Technology Stack
- What tools do they use?
- Automation maturity level?
- Integration opportunities?

### 4. Decision Makers
- Who would buy automation services?
- Titles to target
- LinkedIn profiles to find

### 5. Pain Point Hypotheses
- What problems might they have?
- How could LeverEdge help?

### 6. Outreach Angle
- Best hook for this company?
- Personalization opportunities?
- Mutual connections?

### 7. Red Flags
- Any concerns about this prospect?
- Reasons it might not fit?

### 8. Recommended Next Steps
- How to approach?
- What to say?"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    await update_aria_knowledge(
        "research",
        f"Lead Research: {req.company_name}",
        response,
        "normal"
    )

    await notify_event_bus("lead_researched", {
        "company": req.company_name
    })

    return {
        "lead_research": response,
        "agent": "SCHOLAR",
        "company": req.company_name,
        "logged_to_knowledge": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/compare")
async def compare_niches(req: CompareNiches):
    """Compare multiple niches side by side"""

    time_ctx = get_time_context()

    criteria = req.criteria or [
        "Pain Severity",
        "Willingness to Pay",
        "Accessibility",
        "Competition (inverse)",
        "Expertise Match",
        "Growth Trend"
    ]

    prompt = f"""Compare these niches for LeverEdge AI:

**Niches:** {', '.join(req.niches)}
**Criteria:** {', '.join(criteria)}
**Days to Launch:** {time_ctx['days_to_launch']}

## Niche Comparison

### Scoring Matrix (1-10 each)

| Criterion | {' | '.join(req.niches)} |
|-----------|{'|'.join(['-----' for _ in req.niches])}|
{chr(10).join(f'| {c} | {" | ".join(["?" for _ in req.niches])} |' for c in criteria)}
| **TOTAL** | {' | '.join(['?' for _ in req.niches])} |

### Analysis by Niche

{chr(10).join(f'**{niche}:**' + chr(10) + '- Strengths:' + chr(10) + '- Weaknesses:' + chr(10) + '- Key insight:' + chr(10) for niche in req.niches)}

### Head-to-Head Comparison
- Which has highest pain?
- Which has best accessibility?
- Which has least competition?
- Which fits Damon's background best?

### Recommendation
1. **Top Pick:** [which niche] - [why]
2. **Runner Up:** [which niche] - [why]
3. **Avoid:** [if any] - [why]

### Confidence Level
- How confident in this recommendation?
- What would change the answer?
- What needs validation?

### Next Steps
- Recommended immediate action
- Send to CHIRON for strategic decision? (Yes/No)"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    # This is high importance - niche selection is critical
    await update_aria_knowledge(
        "decision",
        f"Niche Comparison: {' vs '.join(req.niches)}",
        response,
        "high"
    )

    await notify_event_bus("niches_compared", {
        "niches": req.niches
    })

    # Notify HERMES
    await notify_hermes(f"Niche comparison complete: {' vs '.join(req.niches)}", priority="normal")

    return {
        "comparison": response,
        "agent": "SCHOLAR",
        "niches": req.niches,
        "criteria": criteria,
        "logged_to_knowledge": True,
        "aria_notified": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/send-to-chiron")
async def send_findings_to_chiron(req: SendToChironRequest):
    """Send research findings to CHIRON for strategic interpretation"""

    time_ctx = get_time_context()

    await send_to_chiron(
        f"**Research Topic:** {req.topic}\n\n**Findings:**\n{req.findings}\n\n**Request:** Please interpret these findings strategically and advise on next steps.",
        "interpret"
    )

    await notify_event_bus("findings_sent_to_chiron", {
        "topic": req.topic[:100]
    })

    return {
        "status": "sent",
        "to_agent": "CHIRON",
        "topic": req.topic,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/upgrade-self")
async def upgrade_self():
    """SCHOLAR's first mission: propose upgrades to itself"""

    time_ctx = get_time_context()

    prompt = """You are SCHOLAR, reflecting on your own capabilities.

Analyze your current implementation and propose upgrades:

1. **Current Capabilities:**
   - General research, niche analysis, competitor analysis
   - ICP development, lead research, niche comparison
   - Team integration (CHIRON, ARIA, HERMES, Event Bus)
   - Time awareness, knowledge logging

2. **What's Missing for Better Research?**
   - What data sources should I integrate?
   - What research frameworks am I missing?
   - How could I provide better evidence?
   - What would make my analysis more actionable?

3. **Integration Improvements:**
   - How could I work better with CHIRON?
   - What should I automatically send to ARIA?
   - When should I alert HERMES?

4. **Propose Specific Upgrades:**
   - New endpoints needed
   - Data integrations (web search, APIs, databases)
   - Enhanced frameworks
   - Better output formats

5. **For Damon's Launch:**
   - What research do I need to do before March 1?
   - What's the highest-value research right now?
   - Priority order of research tasks

Think like a research director upgrading a research agent."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    await update_aria_knowledge(
        "project",
        "SCHOLAR Self-Upgrade Proposal",
        response,
        "high"
    )

    await notify_event_bus("self_upgrade_proposed", {
        "agent": "SCHOLAR"
    })

    return {
        "upgrade_proposal": response,
        "agent": "SCHOLAR",
        "logged_to_knowledge": True,
        "timestamp": time_ctx['current_datetime']
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8018)
