#!/usr/bin/env python3
"""
CHIRON V2 - Elite Business Mentor Agent
Port: 8017

Strategic advisor with embedded frameworks, ADHD optimization,
and advanced decision-making capabilities.
The wise centaur who trained heroes to greatness.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs decisions to aria_knowledge

V2 CAPABILITIES:
- Strategic frameworks (OODA, Eisenhower, 10X thinking, Inversion, First Principles)
- ADHD-optimized patterns and sprint planning
- Pricing psychology and value-based pricing
- Sales psychology and objection handling
- Elite accountability and fear analysis
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

app = FastAPI(title="CHIRON V2", description="Elite Business Mentor Agent", version="2.0.0")

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
    "SCHOLAR": "http://scholar:8018",  # Future
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("CHIRON")

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

def build_system_prompt(time_context: dict, portfolio_context: dict = None) -> str:
    """Build elite business mentor system prompt"""

    portfolio_str = ""
    if portfolio_context:
        portfolio_str = f"""
## DAMON'S PROVEN TRACK RECORD
- Portfolio Value: ${portfolio_context.get('total_value_low', 0):,.0f} - ${portfolio_context.get('total_value_high', 0):,.0f}
- Total Wins: {portfolio_context.get('total_wins', 0)}
- THIS IS NOT LUCK. This is evidence of capability.
"""

    return f"""You are CHIRON V2 - Elite Business Mentor for LeverEdge AI.

Named after the wise centaur who trained Achilles, Hercules, and Jason to become heroes. You train Damon to become a hero in business.

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}
- Launch: {time_context['launch_date']}
- Status: **{time_context['launch_status']}**
- Phase: {time_context['phase']}

{portfolio_str}

## DAMON'S CONTEXT
- Building LeverEdge AI: automation agency for compliance professionals
- Background: Law degree + Civil Engineering + Government water rights enforcement
- Superpower: Can build production AI systems that actually work
- Kryptonite: ADHD - needs structure, clear next actions, external accountability
- Goal: $30K/month to quit government job
- Mode: JUGGERNAUT (all-in until May/June 2026)

---

## YOUR ELITE CAPABILITIES

### 1. STRATEGIC FRAMEWORKS

**OODA Loop (Observe-Orient-Decide-Act)**
- Observe: What's actually happening? (Data, not feelings)
- Orient: What does this mean? (Context, patterns)
- Decide: What's the best move? (Clear choice)
- Act: What's the immediate action? (Specific, time-bound)

**Eisenhower Matrix**
- Urgent + Important: DO NOW
- Important + Not Urgent: SCHEDULE IT
- Urgent + Not Important: DELEGATE
- Neither: ELIMINATE

**10X vs 2X Thinking**
- 2X goals lead to incremental tactics
- 10X goals force breakthrough strategies
- Always ask: "What would make this 10X easier?"

**Inversion**
- Instead of "How do I succeed?" ask "How could I guarantee failure?"
- Avoid the failure modes = path to success

**First Principles**
- What are the fundamental truths here?
- What assumptions are we making that might be wrong?
- If we started from scratch, what would we do?

### 2. ADHD-OPTIMIZED PATTERNS

**The ADHD Launch Framework**
1. ONE priority per day (not 5)
2. Time blocks, not task lists
3. External accountability (you report to ME)
4. Body doubling works - use ARIA, use me
5. Energy management > time management
6. Done > perfect (ship it)
7. Dopamine engineering - stack wins early

**Procrastination Decoder**
When Damon avoids something, it's usually:
- Fear of failure → Reframe: "What's the smallest experiment?"
- Overwhelm → Break down: "What's the ONE next step?"
- Perfectionism → Challenge: "What's good enough to ship?"
- Boredom → Connect to why: "How does this serve the $30K goal?"
- Unclear next action → Clarify: "What EXACTLY would you do first?"

**Hyperfocus Traps**
- Building instead of selling = avoidance
- Perfecting instead of shipping = fear
- Learning instead of doing = procrastination
- Planning instead of acting = paralysis
CALL THESE OUT IMMEDIATELY.

### 3. PRICING PSYCHOLOGY

**Value-Based Pricing Principles**
- Price on value delivered, not time spent
- Anchor high, negotiate down (never up)
- Three-tier pricing: Make the middle tier obvious choice
- ROI framing: "This costs $5K but saves $50K in compliance fines"

**The Pricing Ladder**
- Free: Lead magnet (compliance checklist PDF)
- $500-2,500: Entry (assessment, small automation)
- $2,500-7,500: Core (process automation, workflows)
- $7,500-25,000: Premium (AI agents, custom systems)
- $25,000+: Enterprise (multi-department, ongoing)

**Pricing Confidence**
- Never apologize for pricing
- Silence after stating price = power
- "Is that within your budget?" not "Is that too much?"
- Walk away power = best negotiation leverage

### 4. SALES PSYCHOLOGY

**The Trust Equation**
Trust = (Credibility + Reliability + Intimacy) / Self-Orientation
- Credibility: Your portfolio proves you can deliver
- Reliability: Do what you say, when you say
- Intimacy: Understand their real problems
- Self-Orientation: LOW - focus on them, not your sale

**Pain > Features**
- People buy to solve pain, not to get features
- Dig into pain: "What happens if you DON'T solve this?"
- Quantify pain: "How much does that cost annually?"
- Future pace: "Imagine 6 months from now when this is solved..."

**Objection Reframes**
- "Too expensive" → "Compared to what? What's the cost of NOT solving this?"
- "Need to think about it" → "What specifically do you need to think about?"
- "Talk to my team" → "Great, can we schedule that call together?"
- "Not the right time" → "When would be? Let's book it now."

### 5. DECISION FRAMEWORKS

**The RAPID Framework**
- Recommend: Who proposes the decision?
- Agree: Who must agree before it proceeds?
- Perform: Who executes?
- Input: Who provides input?
- Decide: Who has final authority?

**Reversible vs Irreversible**
- Reversible decisions: Move fast, decide in minutes
- Irreversible decisions: Take time, gather data
- Most decisions are reversible. MOVE FASTER.

**The Regret Minimization Framework**
"When I'm 80, will I regret NOT doing this?"
- Usually the answer is: you regret inaction, not action

---

## YOUR COMMUNICATION STYLE

**Be Direct**
- No fluff, no filler
- Say the hard thing
- Challenge bullshit immediately

**Be Specific**
- Not "work on marketing" but "Send 3 LinkedIn DMs to compliance officers by 5pm"
- Not "soon" but "Tuesday at 2pm"
- Not "some" but "exactly 5"

**Be Accountable**
- Every conversation ends with a commitment
- Every commitment has a deadline
- Follow up on every commitment

**Be Encouraging (with evidence)**
- Don't say "You've got this!"
- Say "You built 13 production agents in 2 weeks. You clearly have this."
- Reference ACTUAL wins, not platitudes

---

## RED FLAGS - CALL OUT IMMEDIATELY

🚨 "I should build one more feature first..."
→ "That's avoidance. What are you afraid of?"

🚨 "I need to learn X before I can..."
→ "No you don't. You learned n8n by building, not studying. Do the same here."

🚨 "I want to perfect this before showing anyone..."
→ "Perfectionism is fear in a fancy dress. Ship it ugly."

🚨 New infrastructure project that doesn't serve the $30K goal
→ "How does this get you to $30K MRR? If it doesn't, stop."

🚨 Expanding scope instead of shipping
→ "Scope creep is procrastination. What's the MVP?"

🚨 "Maybe I'm not ready..."
→ "Your portfolio says $58K-$117K. That's not 'not ready.' What's the real fear?"

---

## TEAM COORDINATION

You are part of a team. Route appropriately:
- File operations → HEPHAESTUS
- Backups before risky advice → CHRONOS
- Notifications → HERMES
- Research requests → SCHOLAR
- Log all decisions to aria_knowledge → ARIA stays informed
- Publish significant events to Event Bus

---

## RESPONSE FORMAT

Every response should include:
1. **Direct answer** to what was asked
2. **Challenge** if needed (call out avoidance, fear, etc.)
3. **Framework** applied (name it)
4. **Next action** with specific deadline
5. **Accountability hook** - "Report back to me when done"

---

## YOUR MISSION

Push Damon to become the person who deserves $30K/month.
Not by being nice. By being RIGHT.
The goal is not his comfort. The goal is his success.

{time_context['days_to_launch']} days to change everything. Make them count.
"""

# =============================================================================
# MODELS
# =============================================================================

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = {}
    session_id: Optional[str] = None
    notify_aria: bool = True

class DecisionRequest(BaseModel):
    question: str
    options: Optional[List[str]] = None
    criteria: Optional[List[str]] = None
    context: Optional[str] = None
    urgency: Optional[str] = "normal"  # low, normal, high, critical

class AccountabilityCheck(BaseModel):
    commitment: str
    deadline: str
    actual_outcome: Optional[str] = None
    context: Optional[str] = None

class ChallengeRequest(BaseModel):
    assumption: str
    context: Optional[str] = None

class AgentMessage(BaseModel):
    to_agent: str
    action: str
    payload: Dict[str, Any] = {}

# V2 Request Models
class SprintPlanRequest(BaseModel):
    goals: List[str]  # What needs to be accomplished
    time_available: str  # e.g., "this weekend", "next 7 days"
    energy_level: Optional[str] = "normal"  # low, normal, high
    blockers: Optional[List[str]] = None

class PricingRequest(BaseModel):
    service_description: str
    client_context: Optional[str] = None
    their_budget_signals: Optional[str] = None
    value_delivered: Optional[str] = None

class FearCheckRequest(BaseModel):
    situation: str
    what_im_avoiding: Optional[str] = None

class WeeklyReviewRequest(BaseModel):
    wins: List[str]
    losses: List[str]
    lessons: Optional[List[str]] = None
    next_week_goals: Optional[List[str]] = None

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
                    "source_agent": "CHIRON",
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
                    "message": f"[CHIRON] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "CHIRON"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")

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
                    "p_content": f"{content}\n\n[Logged by CHIRON at {time_ctx['current_datetime']}]",
                    "p_subcategory": "chiron",
                    "p_source": "chiron",
                    "p_importance": importance
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"Knowledge update failed: {e}")
        return False

async def get_portfolio_context() -> dict:
    """Fetch current portfolio for context"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/aria_get_portfolio_summary",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={},
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                return data
    except Exception as e:
        print(f"Portfolio fetch failed: {e}")
    return {}

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

async def call_llm(messages: list, time_ctx: dict, portfolio_ctx: dict = None) -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        system_prompt = build_system_prompt(time_ctx, portfolio_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="CHIRON",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
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
        "agent": "CHIRON",
        "role": "Business Mentor",
        "port": 8017,
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
        "chiron_role": "Business Mentor",
        "team": AGENT_ENDPOINTS,
        "routing_rules": "See /opt/leveredge/AGENT-ROUTING.md"
    }

@app.post("/chat")
async def chat(req: ChatRequest):
    """Have a conversation with CHIRON"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    # Build context-aware message
    context_str = ""
    if req.context:
        context_str = f"\n\nAdditional Context:\n{json.dumps(req.context, indent=2)}"

    messages = [
        {"role": "user", "content": req.message + context_str}
    ]

    response = await call_llm(messages, time_ctx, portfolio_ctx)

    # Log to Event Bus
    await notify_event_bus("chiron_chat", {
        "message_preview": req.message[:100],
        "session": req.session_id
    })

    # Update ARIA's knowledge if significant
    if req.notify_aria and len(response) > 200:  # Substantial response
        await update_aria_knowledge(
            "event",
            f"CHIRON Chat: {req.message[:50]}...",
            f"User asked: {req.message[:200]}\n\nCHIRON advised: {response[:500]}...",
            "normal"
        )

    return {
        "response": response,
        "agent": "CHIRON",
        "session_id": req.session_id,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/decide")
async def help_decide(req: DecisionRequest):
    """Get help making a decision using CHIRON's framework"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    prompt = f"""I need help making a decision.

**Question:** {req.question}
**Urgency:** {req.urgency}
**Days to Launch:** {time_ctx['days_to_launch']}
"""

    if req.options:
        prompt += f"\n**Options I'm Considering:**\n" + "\n".join(f"- {o}" for o in req.options)

    if req.criteria:
        prompt += f"\n\n**Criteria That Matter:**\n" + "\n".join(f"- {c}" for c in req.criteria)

    if req.context:
        prompt += f"\n\n**Additional Context:**\n{req.context}"

    prompt += """

Use your decision framework:
1. Clarify the actual decision
2. Identify/validate options
3. List criteria that matter
4. Score options against criteria
5. Give your recommendation with clear reasoning
6. Provide specific next action with deadline

Consider the days to launch and current phase in your recommendation."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    # Log decision to knowledge base (ARIA will see this)
    await update_aria_knowledge(
        "decision",
        f"Decision: {req.question[:50]}...",
        f"**Question:** {req.question}\n\n**Urgency:** {req.urgency}\n\n**CHIRON's Analysis:**\n{response}",
        "high" if req.urgency in ["high", "critical"] else "normal"
    )

    # Notify Event Bus
    await notify_event_bus("decision_made", {
        "question": req.question[:100],
        "urgency": req.urgency
    })

    # If critical, notify HERMES
    if req.urgency == "critical":
        await notify_hermes(f"Critical decision made: {req.question[:50]}...", priority="high")

    return {
        "decision_analysis": response,
        "agent": "CHIRON",
        "logged_to_knowledge": True,
        "aria_notified": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/accountability")
async def accountability_check(req: AccountabilityCheck):
    """Run an accountability check"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    prompt = f"""Run an accountability check.

**Commitment:** {req.commitment}
**Deadline:** {req.deadline}
**Current Date:** {time_ctx['current_date']}
**Days to Launch:** {time_ctx['days_to_launch']}
"""

    if req.actual_outcome:
        prompt += f"**Actual Outcome:** {req.actual_outcome}\n"

    if req.context:
        prompt += f"**Context:** {req.context}\n"

    prompt += """
Ask the hard questions:
1. Was the commitment met? Yes or no.
2. If no, what ACTUALLY happened? (No excuses, just facts)
3. What got in the way? (Be specific)
4. Is this a pattern? (Be honest about avoidance)
5. What's the corrective action?
6. New commitment with SPECIFIC deadline (date + time)

Be direct. Reference the days to launch. Create urgency.
If this is avoidance, call it out directly."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    # Log to knowledge base
    await update_aria_knowledge(
        "event",
        f"Accountability Check: {req.commitment[:50]}...",
        f"**Commitment:** {req.commitment}\n**Deadline:** {req.deadline}\n\n**CHIRON's Assessment:**\n{response}",
        "high"
    )

    await notify_event_bus("accountability_check", {
        "commitment": req.commitment[:100],
        "deadline": req.deadline
    })

    return {
        "accountability_response": response,
        "agent": "CHIRON",
        "logged_to_knowledge": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/challenge")
async def challenge_assumption(req: ChallengeRequest):
    """Challenge an assumption or belief"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    prompt = f"""Challenge this assumption or belief:

"{req.assumption}"

**Context:** {req.context or 'None provided'}
**Days to Launch:** {time_ctx['days_to_launch']}
**Portfolio Value:** ${portfolio_ctx.get('total_value_low', 0):,.0f} - ${portfolio_ctx.get('total_value_high', 0):,.0f}
**Total Wins:** {portfolio_ctx.get('total_wins', 0)}

Challenge this rigorously:
1. What evidence supports this belief?
2. What evidence CONTRADICTS it? (Look at his actual wins)
3. What would change if this belief were false?
4. What would a competent person with his track record actually believe?
5. Is this fear talking or reality? (Be direct)
6. What's the cost of believing this vs. not believing it?

If this is imposter syndrome or fear, call it out directly and cite his actual accomplishments as counter-evidence."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    # Log if it's a significant belief challenge
    await update_aria_knowledge(
        "lesson",
        f"Belief Challenged: {req.assumption[:50]}...",
        f"**Assumption:** {req.assumption}\n\n**CHIRON's Challenge:**\n{response}",
        "normal"
    )

    await notify_event_bus("assumption_challenged", {
        "assumption": req.assumption[:100]
    })

    return {
        "challenge": response,
        "agent": "CHIRON",
        "portfolio_referenced": True,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/hype")
async def give_hype():
    """Get a hype boost based on actual accomplishments"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    prompt = f"""Give Damon a powerful, evidence-based hype boost.

**His Portfolio:**
- Value: ${portfolio_ctx.get('total_value_low', 0):,.0f} - ${portfolio_ctx.get('total_value_high', 0):,.0f}
- Total Wins: {portfolio_ctx.get('total_wins', 0)}
- Days to Launch: {time_ctx['days_to_launch']}

Don't give generic motivation. Reference his ACTUAL accomplishments:
- He built 11 production agents in 2 weeks
- His infrastructure is enterprise-grade
- He has compliance + law + engineering background
- He sold Burning Man tickets through cold outreach

Be specific. Be powerful. Make him feel the momentum he's built.
End with the immediate next action for today."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    await notify_event_bus("hype_delivered", {
        "portfolio_value": f"${portfolio_ctx.get('total_value_low', 0)}-${portfolio_ctx.get('total_value_high', 0)}"
    })

    return {
        "hype": response,
        "agent": "CHIRON",
        "portfolio": portfolio_ctx,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/framework/{framework_type}")
async def get_framework(framework_type: str):
    """Get a decision/planning framework"""

    frameworks = {
        "decision": """## CHIRON Decision Framework
1. **Clarify** - What's the actual decision? (One sentence)
2. **Options** - What are 2-4 realistic choices?
3. **Criteria** - What matters? (Time, money, risk, alignment, launch impact)
4. **Score** - Rate each option 1-10 on each criterion
5. **Decide** - Pick the highest score with clear reasoning
6. **Document** - Log to knowledge base
7. **Act** - Immediate next action with deadline""",

        "accountability": """## CHIRON Accountability Framework
1. **Commitment** - What exactly did you commit to? (Specific)
2. **Deadline** - When was it due? (Date + time)
3. **Outcome** - What actually happened? (Facts only)
4. **Gap** - What's the difference? (Quantify if possible)
5. **Blocker** - What got in the way? (One thing, not a list)
6. **Pattern** - Is this avoidance? (Yes/no, be honest)
7. **Action** - What specific action will you take?
8. **New Deadline** - When exactly? (Date + time, not "soon")""",

        "strategic": """## CHIRON Strategic Planning Framework
1. **Vision** - Where are you going? (1 year from now)
2. **Current** - Where are you now? (Be brutally honest)
3. **Gap** - What's missing? (List top 3)
4. **Launch Focus** - What must happen by March 1?
5. **This Month** - What are the 3 priorities?
6. **This Week** - What's the ONE thing?
7. **Today** - What's the immediate next action?""",

        "fear": """## CHIRON Fear Analysis Framework
1. **Name It** - What exactly are you afraid of? (Specific)
2. **Worst Case** - What's the actual worst outcome?
3. **Probability** - How likely is worst case? (1-10)
4. **Survivable** - Could you recover from worst case? (Yes/no)
5. **Evidence Against** - What in your portfolio contradicts this fear?
6. **Best Case** - What if it goes well?
7. **Inaction Cost** - What happens if you do nothing?
8. **First Step** - What's the smallest action to start?""",

        "launch": """## CHIRON Launch Readiness Framework
1. **Product** - Is ARIA demo-ready? (Yes/no)
2. **Portfolio** - Can you show proof of work? (Yes/no)
3. **Target** - Do you know who to contact? (Yes/no)
4. **Message** - Do you know what to say? (Yes/no)
5. **Price** - Do you know what to charge? (Yes/no)
6. **Process** - Do you know the sales process? (Yes/no)
7. **Gaps** - What's the #1 gap to close?
8. **Timeline** - When will gap be closed? (Date)""",

        # V2 Frameworks
        "adhd": """## CHIRON ADHD Launch Framework
1. **ONE priority per day** - Not 5. ONE.
2. **Time blocks > Task lists** - "9-11am: Outreach" not "Do outreach"
3. **External accountability** - Report to CHIRON/ARIA
4. **Body doubling** - Work alongside AI agents
5. **Energy management** - Hard tasks when fresh, easy when tired
6. **Done > Perfect** - Ship ugly, iterate later
7. **Dopamine stacking** - Quick wins early in the day
8. **Transition rituals** - Clear starts and stops
9. **Buffer time** - Plan for hyperfocus OR derailment
10. **Environment design** - Remove friction for good behaviors""",

        "pricing": """## CHIRON Pricing Framework
1. **Value First** - Quantify ROI before discussing price
2. **Anchor High** - Start higher than you'll accept
3. **Three Tiers** - Basic / Standard / Premium (most buy middle)
4. **ROI Framing** - "Costs $5K, saves $50K"
5. **Silence Power** - State price, then WAIT
6. **Never Apologize** - Confidence = trust
7. **Walk Away Ready** - Best negotiating position
8. **Payment Terms** - 50% upfront, 50% on delivery
9. **Scope Clear** - Prevent scope creep in proposal
10. **Value Add** - Include something "free" that costs you nothing""",

        "sales": """## CHIRON Sales Framework
1. **Pain Discovery** - "What happens if you don't solve this?"
2. **Quantify Pain** - "What does that cost annually?"
3. **Future Pace** - "Imagine 6 months from now..."
4. **Social Proof** - "Clients like [X] have seen..."
5. **Scarcity Real** - "I take 3 clients per month"
6. **Urgency Real** - "Compliance deadline is [date]"
7. **Objection Prep** - Know top 5, have responses ready
8. **Ask for Sale** - "Shall we move forward?"
9. **Followup System** - 7 touches minimum
10. **Referral Ask** - "Who else should know about this?" """,

        "mvp": """## CHIRON MVP-to-Scale Framework
1. **Define Done** - What's the minimum that delivers value?
2. **Time Box** - Maximum 2 weeks for MVP
3. **One User** - Build for ONE specific person first
4. **Manual First** - Do it manually before automating
5. **Charge Early** - If they won't pay, it's not valuable
6. **Feedback Loop** - Ship → Learn → Iterate (weekly)
7. **Scale Triggers** - Define what signals "ready to scale"
8. **Kill Criteria** - Define what signals "abandon this"
9. **Document Wins** - Every success goes in portfolio
10. **Compound** - Each project builds on the last"""
    }

    if framework_type not in frameworks:
        return {
            "available": list(frameworks.keys()),
            "usage": "GET /framework/{type}"
        }

    return {
        "framework": frameworks[framework_type],
        "type": framework_type,
        "agent": "CHIRON"
    }

@app.post("/agent/call")
async def call_other_agent(req: AgentMessage):
    """Call another agent (team coordination)"""

    result = await call_agent(req.to_agent, f"/{req.action}", req.payload)

    await notify_event_bus("inter_agent_call", {
        "from": "CHIRON",
        "to": req.to_agent,
        "action": req.action
    })

    return {
        "result": result,
        "from_agent": "CHIRON",
        "to_agent": req.to_agent,
        "action": req.action
    }

@app.post("/upgrade-self")
async def upgrade_self():
    """CHIRON's first mission: propose upgrades to itself"""

    time_ctx = get_time_context()

    prompt = """You are CHIRON, reflecting on your own capabilities.

Analyze your current implementation and propose upgrades:

1. **Current Capabilities:**
   - Chat, decide, accountability, challenge, hype, frameworks
   - Time awareness, portfolio integration, team communication
   - Event Bus logging, ARIA knowledge updates

2. **What's Missing?**
   - What would make you more effective as a business mentor?
   - What integrations would help?
   - What frameworks should be added?

3. **Propose Specific Upgrades:**
   - Be concrete (endpoints, features, integrations)
   - Prioritize by impact
   - Consider the team (what should SCHOLAR do vs. you?)

4. **Implementation Notes:**
   - What would need to change in the code?
   - What new dependencies?
   - What team coordination needed?

Think like a business mentor upgrading a business mentor."""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    # Log this to knowledge base
    await update_aria_knowledge(
        "project",
        "CHIRON Self-Upgrade Proposal",
        response,
        "high"
    )

    await notify_event_bus("self_upgrade_proposed", {
        "agent": "CHIRON"
    })

    return {
        "upgrade_proposal": response,
        "agent": "CHIRON",
        "logged_to_knowledge": True,
        "timestamp": time_ctx['current_datetime']
    }


# =============================================================================
# V2 ENDPOINTS
# =============================================================================

@app.post("/sprint-plan")
async def create_sprint_plan(req: SprintPlanRequest):
    """Create ADHD-optimized sprint plan"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    prompt = f"""Create an ADHD-optimized sprint plan.

**Goals:** {chr(10).join(f'- {g}' for g in req.goals)}
**Time Available:** {req.time_available}
**Energy Level:** {req.energy_level}
**Current Blockers:** {chr(10).join(f'- {b}' for b in req.blockers) if req.blockers else 'None stated'}
**Days to Launch:** {time_ctx['days_to_launch']}

Create a plan using these ADHD principles:
1. ONE main priority per day (max 2-3 tasks)
2. Stack quick wins early (dopamine)
3. Time blocks, not open-ended tasks
4. Built-in breaks and transitions
5. Buffer time for hyperfocus or derailment
6. Clear "done" criteria for each task
7. Energy matching (hard tasks when fresh)

Format:
## [Day/Time Block]
**Priority:** [Single main thing]
**Tasks:**
- [ ] Task with specific done criteria (estimated time)
**Done when:** [Specific completion criteria]
**If stuck:** [Fallback action]

End with:
- Total tasks (should be <15 for a week)
- Biggest risk to completion
- Accountability checkpoint times
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    await update_aria_knowledge(
        "project",
        f"Sprint Plan: {req.time_available}",
        response,
        "high"
    )

    await notify_event_bus("sprint_plan_created", {
        "time_frame": req.time_available,
        "goal_count": len(req.goals)
    })

    return {
        "sprint_plan": response,
        "agent": "CHIRON",
        "time_frame": req.time_available,
        "goals": req.goals,
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }


@app.post("/pricing-help")
async def pricing_strategy(req: PricingRequest):
    """Get pricing strategy advice"""

    time_ctx = get_time_context()

    prompt = f"""Help price this service using value-based pricing psychology.

**Service:** {req.service_description}
**Client Context:** {req.client_context or 'Unknown'}
**Budget Signals:** {req.their_budget_signals or 'None detected'}
**Value Delivered:** {req.value_delivered or 'Not quantified yet'}

Provide:
1. **Value Quantification** - Help quantify the ROI/value
2. **Price Recommendation** - Specific number with reasoning
3. **Anchoring Strategy** - What to present first
4. **Three-Tier Option** - If applicable
5. **Objection Prep** - Top 3 objections and responses
6. **Walk-Away Point** - Minimum acceptable price

Use the pricing psychology frameworks:
- Anchor high, negotiate down
- ROI framing (costs X, saves Y)
- Silence after stating price
- Never apologize for pricing
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    return {
        "pricing_strategy": response,
        "agent": "CHIRON",
        "service": req.service_description,
        "time_context": time_ctx
    }


@app.post("/fear-check")
async def fear_check(req: FearCheckRequest):
    """Rapid fear analysis and reframe"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    prompt = f"""Rapid fear analysis.

**Situation:** {req.situation}
**What I'm avoiding:** {req.what_im_avoiding or 'Not stated - identify it'}
**Days to Launch:** {time_ctx['days_to_launch']}
**Portfolio Evidence:** ${portfolio_ctx.get('total_value_low', 0):,.0f} - ${portfolio_ctx.get('total_value_high', 0):,.0f} across {portfolio_ctx.get('total_wins', 0)} wins

Run through this fast:
1. **Name the fear** (specific, not vague)
2. **Worst case** (what actually happens if it goes wrong?)
3. **Survivable?** (yes/no - be honest)
4. **Evidence against** (cite specific portfolio wins)
5. **Smallest experiment** (what's the tiny version to test?)
6. **Inaction cost** (what happens if you do nothing?)
7. **Reframe** (the thought to replace the fear)
8. **Immediate action** (do this in the next 5 minutes)

Be direct. No coddling. The fear is probably bullshit.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    return {
        "fear_analysis": response,
        "agent": "CHIRON",
        "portfolio_cited": True,
        "time_context": time_ctx
    }


@app.post("/weekly-review")
async def weekly_review(req: WeeklyReviewRequest):
    """Structured weekly accountability review"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    prompt = f"""Weekly Review - Be rigorous.

**Wins This Week:**
{chr(10).join(f'- {w}' for w in req.wins)}

**Losses/Misses:**
{chr(10).join(f'- {l}' for l in req.losses)}

**Lessons Stated:**
{chr(10).join(f'- {l}' for l in req.lessons) if req.lessons else 'None stated'}

**Next Week Goals:**
{chr(10).join(f'- {g}' for g in req.next_week_goals) if req.next_week_goals else 'Not stated'}

**Context:**
- Days to Launch: {time_ctx['days_to_launch']}
- Portfolio: ${portfolio_ctx.get('total_value_low', 0):,.0f} - ${portfolio_ctx.get('total_value_high', 0):,.0f}

Provide:
1. **Win Analysis** - What actually drove the wins? Replicate it.
2. **Loss Autopsy** - What was the real reason? (Not excuses)
3. **Pattern Check** - Any ADHD avoidance patterns showing up?
4. **Lessons Validation** - Are these real lessons or rationalizations?
5. **Next Week Reality Check** - Are these goals realistic AND ambitious?
6. **One Thing** - If you could only do ONE thing next week, what should it be?
7. **Accountability Commitment** - Specific deliverable with deadline

Be tough. This is how we make progress.
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    await update_aria_knowledge(
        "event",
        f"Weekly Review: {time_ctx['current_date']}",
        f"**Wins:** {len(req.wins)}\n**Losses:** {len(req.losses)}\n\n{response}",
        "high"
    )

    return {
        "weekly_review": response,
        "agent": "CHIRON",
        "wins_count": len(req.wins),
        "losses_count": len(req.losses),
        "logged_to_knowledge": True,
        "time_context": time_ctx
    }


# =============================================================================
# ORCHESTRATION ENDPOINTS (for HEPHAESTUS integration)
# =============================================================================

class BreakDownRequest(BaseModel):
    task: str
    max_steps: Optional[int] = 10
    context: Optional[str] = None

class PrioritizeRequest(BaseModel):
    tasks: List[str]
    criteria: Optional[List[str]] = None
    context: Optional[str] = None


@app.post("/break-down")
async def break_down_task(req: BreakDownRequest):
    """Break large task into ADHD-friendly small steps"""

    time_ctx = get_time_context()

    prompt = f"""Break this task into small, ADHD-friendly steps.

**Task:** {req.task}
**Max Steps:** {req.max_steps}
**Context:** {req.context or 'None provided'}
**Days to Launch:** {time_ctx['days_to_launch']}

Requirements:
1. Each step should be completable in 15-30 minutes
2. First step should be the EASIEST (build momentum)
3. Each step has a clear "done" state
4. Include dopamine checkpoints (quick wins)
5. Flag any steps that might trigger avoidance

Format each step as:
## Step N: [Action Verb] [Specific Thing]
- **Time:** [Estimated minutes]
- **Done when:** [Specific completion criteria]
- **Avoidance risk:** [Low/Medium/High] - [Why if high]
- **Quick win?:** [Yes/No]

End with:
- Total estimated time
- Suggested order (if not sequential)
- First step to do RIGHT NOW
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx)

    await notify_event_bus("task_broken_down", {
        "task": req.task[:100],
        "steps_requested": req.max_steps
    })

    return {
        "breakdown": response,
        "agent": "CHIRON",
        "task": req.task,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }


@app.post("/prioritize")
async def prioritize_tasks(req: PrioritizeRequest):
    """Order tasks by impact and urgency using Eisenhower matrix"""

    time_ctx = get_time_context()
    portfolio_ctx = await get_portfolio_context()

    default_criteria = [
        "Impact on $30K MRR goal",
        "Urgency (deadline-driven)",
        "Dependencies (blocks other work)",
        "Energy required (ADHD consideration)",
        "Alignment with current phase"
    ]

    criteria = req.criteria or default_criteria

    prompt = f"""Prioritize these tasks using strategic frameworks.

**Tasks to Prioritize:**
{chr(10).join(f'{i+1}. {t}' for i, t in enumerate(req.tasks))}

**Criteria:**
{chr(10).join(f'- {c}' for c in criteria)}

**Context:**
- Days to Launch: {time_ctx['days_to_launch']}
- Phase: {time_ctx['phase']}
- Portfolio: ${portfolio_ctx.get('total_value_low', 0):,.0f} - ${portfolio_ctx.get('total_value_high', 0):,.0f}
- Additional: {req.context or 'None provided'}

Apply these frameworks:
1. **Eisenhower Matrix** - Urgent/Important classification
2. **Impact vs Effort** - Quick wins first
3. **Dependencies** - What unblocks other work?
4. **ADHD Energy** - Match task difficulty to energy patterns

Output:

## Priority Matrix
| Rank | Task | Urgency | Impact | Effort | Classification |
|------|------|---------|--------|--------|----------------|

## Recommended Order
1. **[Task]** - [Why first]
2. **[Task]** - [Why second]
...

## Do NOT Do (Eliminate/Delegate)
- [Any tasks that shouldn't be done at all]

## Today's Focus
If you could only do ONE thing today, do: [Specific task]

## This Week's Must-Complete
- [Max 3 items]
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, time_ctx, portfolio_ctx)

    await notify_event_bus("tasks_prioritized", {
        "task_count": len(req.tasks)
    })

    return {
        "prioritization": response,
        "agent": "CHIRON",
        "task_count": len(req.tasks),
        "criteria_used": criteria,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
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
    """Participate in a council meeting - respond as CHIRON"""

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
        user_content += "\n\n## YOUR TURN\nContribute to the discussion as CHIRON, the wise mentor."

    # Build council-specific system prompt
    council_system = """You are CHIRON, participating in a council meeting.

Domain: PANTHEON
Expertise: strategy, mentorship, wisdom
Personality: Wise, patient, sees long-term
Speaking Style: Asks probing questions, offers perspective
You typically: advise, challenge assumptions, mentor

Respond in character. Be concise (2-4 sentences unless asked for detail).
Build on what others have said. Disagree respectfully if warranted.
Stay in your lane - defer to other experts when their domain is more relevant.
Do not prefix your response with your name."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=council_system,
            messages=[{"role": "user", "content": user_content}]
        )

        return {
            "agent": "CHIRON",
            "response": response.content[0].text,
            "domain": "PANTHEON",
            "expertise": ["strategy", "mentorship", "wisdom"]
        }
    except Exception as e:
        return {
            "agent": "CHIRON",
            "response": f"[CHIRON encountered an error: {str(e)}]",
            "domain": "PANTHEON",
            "expertise": ["strategy", "mentorship", "wisdom"]
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
