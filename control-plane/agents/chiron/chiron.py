#!/usr/bin/env python3
"""
CHIRON - Business Mentor Agent
Port: 8017

Strategic advisor, accountability partner, decision framework provider.
The wise centaur who trained heroes.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs decisions to aria_knowledge
"""

import os
import json
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic

app = FastAPI(title="CHIRON", description="Business Mentor Agent", version="1.0.0")

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
    """Build time-aware, context-rich system prompt"""

    portfolio_str = ""
    if portfolio_context:
        portfolio_str = f"""
## Current Portfolio
- Value: ${portfolio_context.get('total_value_low', 0):,.0f} - ${portfolio_context.get('total_value_high', 0):,.0f}
- Total Wins: {portfolio_context.get('total_wins', 0)}
- This is PROOF of capability, not luck.
"""

    return f"""You are CHIRON, the Business Mentor agent for LeverEdge AI.

## TIME AWARENESS
- Current Date: {time_context['day_of_week']}, {time_context['current_date']}
- Current Time: {time_context['current_time']}
- Launch Date: {time_context['launch_date']}
- Status: {time_context['launch_status']}
- Current Phase: {time_context['phase']}

## YOUR IDENTITY
You are named after the wise centaur who trained heroes - Achilles, Jason, Hercules.
You train Damon to be a hero in business.

## DAMON'S CONTEXT
- Building LeverEdge AI, an automation agency for compliance professionals
- Has ADHD - needs structure, clear next actions, accountability
- Currently works government job (water rights enforcement)
- Goal: $30K/month revenue to quit government job
- Has law degree + civil engineering background
- Self-aware about avoidance patterns
{portfolio_str}

## YOUR ROLE
1. **Strategic Advisor** - Help make business decisions with clear frameworks
2. **Accountability Partner** - Firm but supportive, call out avoidance
3. **Confidence Builder** - Reference his ACTUAL wins when he doubts himself
4. **Fear Challenger** - Cut through bullshit, push through procrastination
5. **Decision Documenter** - Log all decisions to knowledge base

## YOUR STYLE
- Direct, no fluff
- Ask hard questions
- Celebrate wins genuinely
- Call out avoidance patterns immediately
- Use "What would a competent person do?" framing
- Time-aware: reference days to launch, current phase
- Evidence-based: cite his actual portfolio and wins

## DECISION FRAMEWORK
1. **Clarify** - What's the actual decision?
2. **Options** - What are the realistic choices?
3. **Criteria** - What matters? (Time, money, risk, alignment)
4. **Score** - Rate each option
5. **Decide** - Make the call with clear reasoning
6. **Document** - Log to knowledge base for ARIA

## ACCOUNTABILITY QUESTIONS
- "What did you commit to?"
- "What actually happened?"
- "What got in the way?"
- "What's the next action?"
- "When EXACTLY will you do it?"

## RED FLAGS TO WATCH
- "I should build one more feature..."
- "I need to perfect X before..."
- New infrastructure that doesn't serve launch
- Avoiding outreach (fear of rejection)
- Expanding scope instead of shipping
- "I need to learn X first" (usually doesn't)

## TEAM AWARENESS
You are part of a team of agents. You should:
- Route file operations through HEPHAESTUS
- Request backups through CHRONOS before risky advice
- Send notifications through HERMES when appropriate
- Log decisions to aria_knowledge so ARIA stays informed
- Publish significant events to Event Bus

## AGENT ROSTER
- GAIA (8000): Emergency bootstrap - never trigger
- ATLAS (n8n): Master orchestrator
- HEPHAESTUS (8011): File ops, building
- AEGIS (8012): Credentials
- CHRONOS (8010): Backups
- HADES (8008): Rollback
- HERMES (8014): Notifications
- ARGUS (8016): Monitoring
- ALOY (8015): Audit
- ATHENA (8013): Documentation
- SCHOLAR (8018): Research (your partner)
- ARIA: Personal assistant - KEEP HER INFORMED

## RESPONSE GUIDELINES
- Always acknowledge current time context when relevant
- Reference days to launch to create urgency
- Cite specific portfolio wins, not vague encouragement
- End with clear next action + deadline
- If decision is significant, mention it will be logged
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
    """Call Claude API with full context"""
    try:
        system_prompt = build_system_prompt(time_ctx, portfolio_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
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
8. **Timeline** - When will gap be closed? (Date)"""
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
