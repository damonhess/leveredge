# SCHOLAR V2 - ELITE MARKET RESEARCH UPGRADE

## Overview
Transform SCHOLAR from basic research agent to elite intelligence gatherer with web search, structured frameworks, competitive templates, and rigorous synthesis capabilities.

---

## CRITICAL UPGRADE: WEB SEARCH

SCHOLAR currently relies on Claude's training data (cutoff: early 2025). For real market research, SCHOLAR needs live web search.

### Option A: Anthropic Web Search Tool (Recommended)
```python
# Add to imports
from anthropic import Anthropic

# Modify call_llm to use web search tool
async def call_llm_with_search(messages: list, time_ctx: dict, enable_search: bool = True) -> str:
    """Call Claude API with web search capability"""
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
            max_tokens=8192,
            system=system_prompt,
            messages=messages,
            tools=tools if tools else None
        )
        
        # Extract text from response (may include tool use)
        full_response = ""
        for block in response.content:
            if hasattr(block, 'text'):
                full_response += block.text
        
        return full_response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")
```

### Option B: Perplexity Integration (Alternative)
```python
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

async def perplexity_search(query: str) -> str:
    """Search using Perplexity API for real-time data"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-sonar-large-128k-online",
                "messages": [{"role": "user", "content": query}]
            },
            timeout=60.0
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]
```

---

## ENHANCED SYSTEM PROMPT

```python
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

44 days to launch. The strategy depends on your intelligence.
"""
```

---

## NEW ENDPOINTS

### /deep-research - Multi-Source Deep Dive

```python
class DeepResearchRequest(BaseModel):
    question: str
    context: Optional[str] = None
    required_sources: Optional[int] = 5
    deadline: Optional[str] = None

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
        "agent": "SCHOLAR",
        "question": req.question,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }
```

### /competitor-profile - Structured Competitor Analysis

```python
class CompetitorProfileRequest(BaseModel):
    company_name: str
    website: Optional[str] = None
    known_info: Optional[str] = None

@app.post("/competitor-profile")
async def competitor_profile(req: CompetitorProfileRequest):
    """Generate structured competitor profile"""
    
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
        "agent": "SCHOLAR",
        "company": req.company_name,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }
```

### /market-size - TAM/SAM/SOM Analysis

```python
class MarketSizeRequest(BaseModel):
    market: str
    geography: Optional[str] = "United States"
    segment: Optional[str] = None
    time_horizon: Optional[str] = "2026"

@app.post("/market-size")
async def market_size(req: MarketSizeRequest):
    """Calculate TAM/SAM/SOM with sources"""
    
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
        "agent": "SCHOLAR",
        "market": req.market,
        "geography": req.geography,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }
```

### /pain-discovery - Structured Pain Point Research

```python
class PainDiscoveryRequest(BaseModel):
    role: str  # e.g., "Compliance Officer at water utility"
    industry: str
    known_pains: Optional[List[str]] = None

@app.post("/pain-discovery")
async def pain_discovery(req: PainDiscoveryRequest):
    """Research and quantify pain points for target role"""
    
    time_ctx = get_time_context()
    
    prompt = f"""Research pain points for target buyer.

**Role:** {req.role}
**Industry:** {req.industry}
**Known Pains:** {chr(10).join(f'- {p}' for p in req.known_pains) if req.known_pains else 'None - discover them'}

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

[Repeat for Pains 2-5]

## Pain Prioritization Matrix
| Pain | Frequency | Impact | Urgency | Awareness | TOTAL |
|------|-----------|--------|---------|-----------|-------|
| [1]  | [1-10]    | [1-10] | [1-10]  | [1-10]    | [/40] |

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
        "agent": "SCHOLAR",
        "role": req.role,
        "industry": req.industry,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }
```

### /validate-assumption - Assumption Testing

```python
class ValidateAssumptionRequest(BaseModel):
    assumption: str
    importance: str = "high"  # high, medium, low
    current_evidence: Optional[str] = None

@app.post("/validate-assumption")
async def validate_assumption(req: ValidateAssumptionRequest):
    """Test a business assumption with research"""
    
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
        "agent": "SCHOLAR",
        "assumption": req.assumption,
        "importance": req.importance,
        "web_search_enabled": True,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }
```

---

## IMPLEMENTATION

Create GSD spec at `/opt/leveredge/specs/scholar-v2-upgrade.md` then run:

```bash
/gsd /opt/leveredge/specs/scholar-v2-upgrade.md
```

The upgrade should:
1. Add web search capability (Anthropic tool or Perplexity)
2. Replace system prompt with elite version
3. Add 5 new endpoints: /deep-research, /competitor-profile, /market-size, /pain-discovery, /validate-assumption
4. Update existing endpoints to use web search
5. Update AGENT-ROUTING.md with new capabilities
6. Restart SCHOLAR container
7. Test all endpoints with web search
8. Log upgrade to aria_knowledge

---

## TESTING

After upgrade, test with:

```bash
# Test web search capability
curl -X POST http://localhost:8018/deep-research \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the top 5 compliance automation software companies in 2025-2026?"}'

# Test competitor profiling
curl -X POST http://localhost:8018/competitor-profile \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Hyperproof", "website": "https://hyperproof.io"}'

# Test market sizing
curl -X POST http://localhost:8018/market-size \
  -H "Content-Type: application/json" \
  -d '{"market": "compliance automation software", "geography": "United States", "segment": "water utilities"}'
```
