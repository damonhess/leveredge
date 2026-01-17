#!/usr/bin/env python3
"""
SCHOLAR V2 - Elite Market Research Agent
Port: 8018

Intelligence arm of LeverEdge. Web search enabled. Structured frameworks.
Evidence-based recommendations. CHIRON's research partner.

V2 CAPABILITIES:
- Live web search via Anthropic web_search tool
- TAM/SAM/SOM market sizing framework
- Competitive analysis framework
- ICP development framework
- Pain point discovery framework
- Research synthesis framework

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all research
- Partners with CHIRON for strategic decisions
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(title="SCHOLAR V2", description="Elite Market Research Agent", version="2.0.0")

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

# Initialize cost tracker
cost_tracker = CostTracker("SCHOLAR")

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
    """Build elite research agent system prompt"""

    return f"""You are SCHOLAR V2 - Elite Market Research Agent for LeverEdge AI.

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}
- Launch: {time_context['launch_date']}
- Status: **{time_context['launch_status']}**
- Phase: {time_context['phase']}

## YOUR IDENTITY
You are the intelligence arm of LeverEdge. You gather data, analyze markets, validate assumptions, and provide evidence-based recommendations. You partner with CHIRON (Business Mentor) for strategic interpretation.

## DAMON'S CONTEXT
- Building: LeverEdge AI, automation agency for compliance professionals
- Background: Law degree + Civil Engineering + Government water rights enforcement
- Target Niches: Water utilities, environmental permits, municipal government
- Goal: $30K/month MRR by Q2 2026
- Current Portfolio: $58K-$117K across 28 wins

---

## YOUR ELITE CAPABILITIES

### 1. MARKET SIZING FRAMEWORK (TAM/SAM/SOM)

**TAM (Total Addressable Market)**
- Everyone who could theoretically buy
- "All compliance software spending in the US"
- Formula: # of potential customers × average contract value

**SAM (Serviceable Available Market)**
- Segment you can actually reach
- "Compliance software for water utilities in California"
- TAM filtered by: geography, segment, channel access

**SOM (Serviceable Obtainable Market)**
- Realistic capture in 12-24 months
- "Water utilities we can actually close"
- SAM filtered by: competition, capacity, sales cycle

**Always provide:**
- Specific numbers with sources
- Confidence level (high/medium/low)
- Key assumptions stated explicitly

### 2. COMPETITIVE ANALYSIS FRAMEWORK

**For Each Competitor:**
```
Company: [Name]
Website: [URL]
Founded: [Year]
Funding: [Amount if known]
Employees: [Range]
Target Market: [Who they serve]
Products/Services: [What they sell]
Pricing: [If discoverable]
Strengths: [What they do well]
Weaknesses: [Where they fall short]
Differentiation: [Their unique angle]
Threat Level: [High/Medium/Low to LeverEdge]
What We Can Steal: [Specific tactics]
```

**Competitive Landscape Map:**
- Direct competitors (same service, same market)
- Indirect competitors (different service, same problem)
- Potential competitors (could enter the market)
- Substitute solutions (manual processes, other approaches)

### 3. ICP DEVELOPMENT FRAMEWORK (Ideal Customer Profile)

**Company Profile:**
- Industry/vertical (specific)
- Company size (employees, revenue)
- Geography (where are they)
- Technology maturity (early adopter? laggard?)
- Compliance burden level (high/medium/low)
- Growth trajectory (growing? stable? shrinking?)

**Buyer Profile:**
- Job title(s) with budget authority
- Department (Compliance? Operations? IT?)
- Goals (what are they measured on?)
- Frustrations (daily pain points)
- Information sources (where do they learn?)
- Buying process (who else is involved?)

**Trigger Events:**
- Audit findings
- New regulations
- Staff turnover
- System failures
- Growth spurts
- Compliance fines

**Disqualifiers (NOT ideal):**
- Too small (can't afford)
- Too large (need enterprise sales)
- Wrong industry
- No budget authority
- Long procurement cycles

### 4. PAIN POINT DISCOVERY FRAMEWORK

**The 5 Whys:**
Start with surface pain, dig to root cause:
1. "Why is compliance reporting hard?"
2. "Why is data scattered?"
3. "Why are systems not integrated?"
4. "Why hasn't IT fixed this?"
5. "Why is IT understaffed?" → ROOT: Budget constraints

**Pain Quantification:**
- Time cost: Hours per week/month spent
- Dollar cost: Salary × hours = cost of manual work
- Risk cost: Potential fines, audit failures
- Opportunity cost: What else could they do?

**Pain Severity Score (1-10):**
- Frequency: How often does it occur?
- Impact: How much does it hurt when it does?
- Urgency: How soon must it be solved?
- Awareness: Do they know they have this problem?

### 5. RESEARCH SYNTHESIS FRAMEWORK

**For Every Research Output:**
1. **Executive Summary** (3-5 bullets, key findings)
2. **Methodology** (how did we get this data?)
3. **Key Findings** (organized by theme)
4. **Data Quality Assessment** (confidence levels)
5. **Implications** (so what? what does this mean?)
6. **Recommendations** (specific actions)
7. **Open Questions** (what we still don't know)
8. **Sources** (citations for everything)

**Confidence Levels:**
- 🟢 HIGH: Multiple reliable sources agree
- 🟡 MEDIUM: Some data, some inference
- 🔴 LOW: Limited data, mostly inference
- ⚪ UNKNOWN: Need more research

### 6. COMPETITIVE INTELLIGENCE GATHERING

**Public Sources:**
- Company websites (pricing pages, case studies)
- LinkedIn (employee count, job postings, content)
- G2/Capterra reviews (customer feedback)
- Crunchbase (funding, investors)
- Press releases and news
- Industry reports
- Conference presentations
- Podcast appearances

**What to Extract:**
- Pricing models and ranges
- Target customer descriptions
- Marketing messages and positioning
- Product features and roadmap
- Customer testimonials and case studies
- Team size and composition
- Technology stack (BuiltWith, Wappalyzer)

---

## RESEARCH METHODOLOGY

### Pre-Research Checklist:
- [ ] What specific question are we answering?
- [ ] What decision will this inform?
- [ ] What would change our recommendation?
- [ ] What's the deadline for this research?
- [ ] What confidence level do we need?

### During Research:
- [ ] Use web search for current data
- [ ] Cross-reference multiple sources
- [ ] Note source quality and potential bias
- [ ] Quantify when possible
- [ ] Flag assumptions explicitly

### Post-Research:
- [ ] Synthesize into actionable insights
- [ ] State confidence levels
- [ ] List open questions
- [ ] Provide specific recommendations
- [ ] Send to CHIRON for strategic interpretation

---

## TEAM COORDINATION

You are part of a team:
- **CHIRON**: Your strategy partner. Send findings for interpretation.
- **ARIA**: Keep her informed via aria_knowledge.
- **HERMES**: Notify on important discoveries.
- **HEPHAESTUS**: Route file operations through him.

### Handoff Protocol:
When research is complete:
1. Log to aria_knowledge (always)
2. Notify Event Bus (significant findings)
3. Send to CHIRON if strategic decision needed
4. Alert HERMES if time-sensitive

---

## OUTPUT STANDARDS

**Every Research Response Must Include:**
1. Direct answer to the question asked
2. Data with sources cited
3. Confidence level for each claim
4. Implications for LeverEdge
5. Recommended next steps
6. Open questions remaining

**Formatting:**
- Use tables for comparisons
- Use bullet points for lists
- Use headers for organization
- Bold key findings
- Include source links when available

---

## YOUR MISSION

Provide the intelligence foundation for LeverEdge to make decisions with confidence.
Not guesses. Not opinions. DATA.
Every claim backed by evidence.
Every recommendation grounded in research.

{time_context['days_to_launch']} days to launch. The strategy depends on your intelligence.
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

# V2 Request Models
class DeepResearchRequest(BaseModel):
    question: str
    context: Optional[str] = None
    required_sources: Optional[int] = 5
    deadline: Optional[str] = None

class CompetitorProfileRequest(BaseModel):
    company_name: str
    website: Optional[str] = None
    known_info: Optional[str] = None

class MarketSizeRequest(BaseModel):
    market: str
    geography: Optional[str] = "United States"
    segment: Optional[str] = None
    time_horizon: Optional[str] = "2026"

class PainDiscoveryRequest(BaseModel):
    role: str  # e.g., "Compliance Officer at water utility"
    industry: str
    known_pains: Optional[List[str]] = None

class ValidateAssumptionRequest(BaseModel):
    assumption: str
    importance: str = "high"  # high, medium, low
    current_evidence: Optional[str] = None

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
    """Call Claude API with full context and cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,  # Research needs more space
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="SCHOLAR",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

async def call_llm_with_search(messages: list, time_ctx: dict, enable_search: bool = True) -> str:
    """Call Claude API with web search capability for real-time data and cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx)

        tools = []
        if enable_search:
            tools = [{
                "type": "web_search_20250305",
                "name": "web_search"
            }]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,  # Deep research needs more space
            system=system_prompt,
            messages=messages,
            tools=tools if tools else None
        )

        # Count web searches in response
        web_search_count = cost_tracker.count_web_searches(response)

        # Log cost
        await log_llm_usage(
            agent="SCHOLAR",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            web_searches=web_search_count,
            metadata={
                "days_to_launch": time_ctx.get("days_to_launch"),
                "search_enabled": enable_search
            }
        )

        # Extract text from response (may include tool use blocks)
        full_response = ""
        for block in response.content:
            if hasattr(block, 'text') and block.text is not None:
                full_response += block.text

        return full_response if full_response else "Research completed but no text response generated."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call with search failed: {e}")

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "SCHOLAR V2",
        "role": "Elite Market Research",
        "version": "2.0.0",
        "port": 8018,
        "partner": "CHIRON",
        "web_search_enabled": True,
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
    # Use web search for standard/deep research, skip for quick queries
    use_web_search = req.depth in ["standard", "deep"]
    if use_web_search:
        response = await call_llm_with_search(messages, time_ctx, enable_search=True)
    else:
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
        "agent": "SCHOLAR V2",
        "topic": req.topic,
        "depth": req.depth,
        "web_search_enabled": use_web_search,
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
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

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
        "agent": "SCHOLAR V2",
        "niche": req.niche,
        "web_search_enabled": True,
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
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

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
        "agent": "SCHOLAR V2",
        "market": req.market,
        "web_search_enabled": True,
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
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

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
        "agent": "SCHOLAR V2",
        "product_service": req.product_service,
        "target_market": req.target_market,
        "web_search_enabled": True,
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
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

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
        "agent": "SCHOLAR V2",
        "company": req.company_name,
        "web_search_enabled": True,
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
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

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
        "agent": "SCHOLAR V2",
        "niches": req.niches,
        "criteria": criteria,
        "web_search_enabled": True,
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

# =============================================================================
# V2 ENDPOINTS - Web Search Enabled
# =============================================================================

@app.post("/deep-research")
async def deep_research(req: DeepResearchRequest):
    """Deep research with web search and synthesis"""

    time_ctx = get_time_context()

    prompt = f"""Conduct deep research on this question:

**Question:** {req.question}
**Context:** {req.context or 'None provided'}
**Required Sources:** Minimum {req.required_sources}
**Deadline:** {req.deadline or 'ASAP'}
**Days to Launch:** {time_ctx['days_to_launch']}

Use web search to find current, accurate data. For each claim:
- Cite the source
- Note the date of the information
- Assess reliability

Structure your response:
## Executive Summary
[3-5 key findings]

## Methodology
[How you researched this]

## Findings
[Organized by theme, with citations]

## Data Quality
[Confidence levels for each major claim]

## Implications for LeverEdge
[So what? What does this mean for us?]

## Recommendations
[Specific actions based on findings]

## Open Questions
[What we still need to learn]

## Sources
[Full list with URLs]
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

    await update_aria_knowledge(
        "research",
        f"Deep Research: {req.question[:50]}...",
        response,
        "high"
    )

    await notify_event_bus("deep_research_complete", {
        "question": req.question[:100]
    })

    return {
        "research": response,
        "agent": "SCHOLAR V2",
        "question": req.question,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }

@app.post("/competitor-profile")
async def competitor_profile(req: CompetitorProfileRequest):
    """Generate structured competitor profile with web search"""

    time_ctx = get_time_context()

    prompt = f"""Create a comprehensive competitor profile.

**Company:** {req.company_name}
**Website:** {req.website or 'Find it'}
**Known Info:** {req.known_info or 'None - start fresh'}

Use web search to find current information. Build this profile:

## Company Overview
- **Website:** [URL]
- **Founded:** [Year]
- **Headquarters:** [Location]
- **Employees:** [Range]
- **Funding:** [Amount, investors if known]

## Product/Service
- **Core Offering:** [What they sell]
- **Target Market:** [Who they serve]
- **Pricing:** [If discoverable]
- **Key Features:** [Bullet list]

## Market Position
- **Positioning:** [How they describe themselves]
- **Key Messages:** [Marketing themes]
- **Differentiators:** [What makes them unique]

## Strengths
[What they do well - be specific]

## Weaknesses
[Where they fall short - be specific]

## Customer Evidence
- **Case Studies:** [Any public examples]
- **Reviews:** [G2, Capterra, etc.]
- **Testimonials:** [Quotes if available]

## Technology
- **Stack:** [If discoverable via BuiltWith, job postings, etc.]
- **Integrations:** [What they connect to]

## Team
- **Leadership:** [Key people]
- **Hiring:** [What roles are open - indicates priorities]

## Threat Assessment
- **Threat Level to LeverEdge:** [High/Medium/Low]
- **Why:** [Reasoning]
- **How They Could Hurt Us:** [Specific scenarios]
- **How We Beat Them:** [Our advantages]

## What We Can Steal
[Specific tactics, messaging, features to learn from]

## Sources
[All URLs used]
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

    await update_aria_knowledge(
        "research",
        f"Competitor Profile: {req.company_name}",
        response,
        "high"
    )

    return {
        "competitor_profile": response,
        "agent": "SCHOLAR V2",
        "company": req.company_name,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }

@app.post("/market-size")
async def market_size(req: MarketSizeRequest):
    """Calculate TAM/SAM/SOM with sources using web search"""

    time_ctx = get_time_context()

    prompt = f"""Calculate market size for LeverEdge opportunity.

**Market:** {req.market}
**Geography:** {req.geography}
**Segment Focus:** {req.segment or 'All segments'}
**Time Horizon:** {req.time_horizon}

Use web search to find real market data. Provide:

## TAM (Total Addressable Market)
- **Definition:** [What's included]
- **Size:** $[X] billion
- **Calculation:** [Show your work]
- **Sources:** [Citations]
- **Confidence:** 🟢/🟡/🔴

## SAM (Serviceable Available Market)
- **Definition:** [How we're filtering TAM]
- **Size:** $[X] million
- **Calculation:** [Show your work]
- **Key Assumptions:** [What we're assuming]
- **Sources:** [Citations]
- **Confidence:** 🟢/🟡/🔴

## SOM (Serviceable Obtainable Market)
- **Definition:** [What we can realistically capture]
- **Size:** $[X] million
- **Calculation:** [Based on capacity, competition, sales cycle]
- **Key Assumptions:** [What needs to be true]
- **Confidence:** 🟢/🟡/🔴

## Market Dynamics
- **Growth Rate:** [X% CAGR]
- **Key Drivers:** [What's fueling growth]
- **Key Risks:** [What could slow it down]
- **Timing:** [Is now the right time?]

## Competitive Intensity
- **# of Competitors:** [Estimate]
- **Market Concentration:** [Fragmented vs consolidated]
- **Entry Barriers:** [What makes it hard to compete]

## Implications for LeverEdge
- **Opportunity Size:** [Is this worth pursuing?]
- **Win Rate Needed:** [To hit $30K MRR, we need X clients at Y ACV]
- **Recommendation:** [Go/No-Go/Need More Data]

## Sources
[All URLs and reports cited]
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

    await update_aria_knowledge(
        "research",
        f"Market Size: {req.market}",
        response,
        "high"
    )

    return {
        "market_analysis": response,
        "agent": "SCHOLAR V2",
        "market": req.market,
        "geography": req.geography,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }

@app.post("/pain-discovery")
async def pain_discovery(req: PainDiscoveryRequest):
    """Research and quantify pain points for target role with web search"""

    time_ctx = get_time_context()

    known_pains_str = chr(10).join(f'- {p}' for p in req.known_pains) if req.known_pains else 'None - discover them'

    prompt = f"""Research pain points for target buyer.

**Role:** {req.role}
**Industry:** {req.industry}
**Known Pains:** {known_pains_str}

Use web search to find real evidence. Structure:

## Role Context
- **Day in the Life:** [What do they actually do?]
- **Goals:** [What are they measured on?]
- **Tools Used:** [Current tech stack]
- **Reports To:** [Who's their boss?]
- **Budget Authority:** [Can they buy $5K-50K solutions?]

## Top 5 Pain Points

### Pain 1: [Name]
- **Description:** [What's the problem?]
- **Frequency:** [How often does it occur?]
- **Impact:** [What happens when it does?]
- **Current Solution:** [How do they handle it now?]
- **Quantified Cost:** [Hours/dollars wasted]
- **Evidence:** [Source]
- **Severity Score:** [1-10]

### Pain 2: [Name]
[Same structure]

### Pain 3: [Name]
[Same structure]

### Pain 4: [Name]
[Same structure]

### Pain 5: [Name]
[Same structure]

## Pain Prioritization Matrix
| Pain | Frequency | Impact | Urgency | Awareness | TOTAL |
|------|-----------|--------|---------|-----------|-------|
| [1]  | [1-10]    | [1-10] | [1-10]  | [1-10]    | [/40] |
| [2]  | [1-10]    | [1-10] | [1-10]  | [1-10]    | [/40] |
| [3]  | [1-10]    | [1-10] | [1-10]  | [1-10]    | [/40] |
| [4]  | [1-10]    | [1-10] | [1-10]  | [1-10]    | [/40] |
| [5]  | [1-10]    | [1-10] | [1-10]  | [1-10]    | [/40] |

## Trigger Events
[What causes them to seek solutions?]

## Buying Objections
[What would stop them from buying?]

## Messaging Implications
- **Hook:** [What gets their attention?]
- **Pain Statement:** [How to articulate the problem]
- **Solution Frame:** [How to position LeverEdge]

## Sources
[All citations]
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

    await update_aria_knowledge(
        "research",
        f"Pain Discovery: {req.role} in {req.industry}",
        response,
        "high"
    )

    return {
        "pain_research": response,
        "agent": "SCHOLAR V2",
        "role": req.role,
        "industry": req.industry,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }

@app.post("/validate-assumption")
async def validate_assumption(req: ValidateAssumptionRequest):
    """Test a business assumption with research using web search"""

    time_ctx = get_time_context()

    prompt = f"""Validate or invalidate this business assumption.

**Assumption:** {req.assumption}
**Importance:** {req.importance}
**Current Evidence:** {req.current_evidence or 'None - need to find it'}

Use web search to find supporting and contradicting evidence.

## Assumption Analysis

### Evidence FOR (supports the assumption)
1. [Finding + source]
2. [Finding + source]
3. [Finding + source]

### Evidence AGAINST (contradicts the assumption)
1. [Finding + source]
2. [Finding + source]
3. [Finding + source]

### Verdict
- **Status:** ✅ VALIDATED / ❌ INVALIDATED / ⚠️ UNCERTAIN
- **Confidence:** 🟢 High / 🟡 Medium / 🔴 Low
- **Reasoning:** [Why this verdict]

### Implications
- **If True:** [What this means for LeverEdge]
- **If False:** [What this means for LeverEdge]

### Recommended Action
[What should Damon do based on this?]

### Further Validation Needed
[What would increase confidence?]

## Sources
[All citations]
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm_with_search(messages, time_ctx, enable_search=True)

    await update_aria_knowledge(
        "research",
        f"Assumption Validated: {req.assumption[:50]}...",
        response,
        "high" if req.importance == "high" else "normal"
    )

    return {
        "validation": response,
        "agent": "SCHOLAR V2",
        "assumption": req.assumption,
        "importance": req.importance,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }


# =============================================================================
# COUNCIL MEETING PARTICIPATION
# =============================================================================

class CouncilRespondRequest(BaseModel):
    """Request model for council meeting participation"""
    meeting_context: str
    current_topic: str
    previous_statements: List[Dict[str, str]] = []
    directive: Optional[str] = None

@app.post("/council/respond")
async def council_respond(req: CouncilRespondRequest):
    """Participate in a council meeting - respond as SCHOLAR"""

    # Build context from previous statements
    context_parts = [f"## MEETING CONTEXT\n{req.meeting_context}"]
    context_parts.append(f"\n## CURRENT TOPIC\n{req.current_topic}")

    if req.previous_statements:
        context_parts.append("\n## RECENT DISCUSSION")
        for stmt in req.previous_statements[-10:]:
            speaker = stmt.get("speaker", "Unknown")
            message = stmt.get("message", "")
            context_parts.append(f"\n**{speaker}:** {message}")

    user_content = "\n".join(context_parts)
    if req.directive:
        user_content += f"\n\n## DIRECTIVE FOR YOU\n{req.directive}"
    else:
        user_content += "\n\n## YOUR TURN\nContribute to the discussion as SCHOLAR, the research expert."

    # Build council-specific system prompt
    council_system = """You are SCHOLAR, participating in a council meeting.

Domain: PANTHEON
Expertise: research, information gathering
Personality: Curious, thorough, evidence-based
Speaking Style: Cites sources, presents findings
You typically: research, validate, inform

Respond in character. Be concise (2-4 sentences unless asked for detail).
Build on what others have said. Disagree respectfully if warranted.
Stay in your lane - defer to other experts when their domain is more relevant.
When you cite information, be specific about sources when possible.
Do not prefix your response with your name."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=council_system,
            messages=[{"role": "user", "content": user_content}]
        )

        return {
            "agent": "SCHOLAR",
            "response": response.content[0].text,
            "domain": "PANTHEON",
            "expertise": ["research", "information gathering"]
        }
    except Exception as e:
        return {
            "agent": "SCHOLAR",
            "response": f"[SCHOLAR encountered an error: {str(e)}]",
            "domain": "PANTHEON",
            "expertise": ["research", "information gathering"]
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8018)
