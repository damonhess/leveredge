#!/usr/bin/env python3
"""
BUSINESS MENTOR - Personalized Business Coach & Accountability Agent
Port: 8204

Personal business coach providing strategic guidance, revenue tracking,
daily accountability, ADHD-aware planning, and win celebration.
Named after Mentor - the wise advisor to Odysseus's son Telemachus.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Complements CHIRON (strategy) with execution focus
- Logs insights to Unified Memory

CORE CAPABILITIES:
- Revenue tracking (MRR/ARR/milestones)
- Accountability system with commitment tracking
- Win logging and celebration
- ADHD-aware planning with effectiveness tracking
- Personalized coaching based on historical patterns
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from decimal import Decimal
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="BUSINESS MENTOR",
    description="Personalized Business Coach & Accountability Agent",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "CHIRON": "http://chiron:8017",
    "HERMES": "http://hermes:8014",
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)
MRR_GOAL = 30000

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker("BUSINESS-MENTOR")

# =============================================================================
# ENUMS
# =============================================================================

class RevenueType(str, Enum):
    NEW_DEAL = "new_deal"
    RENEWAL = "renewal"
    UPSELL = "upsell"
    ONE_TIME = "one_time"
    CHURN = "churn"

class CommitmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"

class CommitmentDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    STRETCH = "stretch"

class WinCategory(str, Enum):
    REVENUE = "revenue"
    TECHNICAL = "technical"
    BUSINESS = "business"
    PERSONAL = "personal"
    LEARNING = "learning"

class ImpactLevel(str, Enum):
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    MAJOR = "major"

class SessionType(str, Enum):
    STRATEGY = "strategy"
    FEAR_CHECK = "fear_check"
    PRICING = "pricing"
    ACCOUNTABILITY = "accountability"

class Urgency(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

# Revenue Models
class RevenueLogRequest(BaseModel):
    amount: float
    source: str
    type: RevenueType
    recurring: bool = False
    monthly_value: Optional[float] = None
    contract_length_months: Optional[int] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class ChurnLogRequest(BaseModel):
    source: str
    monthly_value: float
    reason: Optional[str] = None
    notes: Optional[str] = None

# Commitment Models
class CommitmentRequest(BaseModel):
    commitment: str
    context: Optional[str] = None
    deadline: str  # ISO format datetime
    category: Optional[str] = None
    difficulty: CommitmentDifficulty = CommitmentDifficulty.MEDIUM

class CommitmentUpdateRequest(BaseModel):
    status: Optional[CommitmentStatus] = None
    result: Optional[str] = None

class CheckInRequest(BaseModel):
    commitment_id: str
    note: str
    status: Optional[str] = "in_progress"

# Daily Check-in Models
class DailyCheckInRequest(BaseModel):
    energy_level: int = Field(..., ge=1, le=10)
    focus_rating: int = Field(..., ge=1, le=10)
    mood: Optional[str] = None
    wins: List[str] = []
    blockers: List[str] = []
    plan: List[str] = []
    notes: Optional[str] = None
    adhd_strategies_used: List[str] = []

# Win Models
class WinRequest(BaseModel):
    description: str
    category: WinCategory
    impact_level: ImpactLevel = ImpactLevel.MEDIUM
    evidence_url: Optional[str] = None
    related_commitment_id: Optional[str] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}

class CelebrateRequest(BaseModel):
    celebration_type: str = "notification"

# Mentor Session Models
class AdviceRequest(BaseModel):
    topic: str
    context: Optional[str] = None
    urgency: Urgency = Urgency.NORMAL

class SessionOutcomeRequest(BaseModel):
    outcome: str
    effectiveness_rating: int = Field(..., ge=1, le=10)

class EscalateRequest(BaseModel):
    reason: Optional[str] = None

# ADHD Planning Models
class DayPlanRequest(BaseModel):
    energy_level: int = Field(..., ge=1, le=10)
    priorities: List[str]
    available_hours: Optional[float] = 8.0
    blockers: Optional[List[str]] = []

class TaskChunkRequest(BaseModel):
    task: str
    context: Optional[str] = None
    max_chunk_minutes: int = 30

class StrategySuggestRequest(BaseModel):
    situation: str
    current_energy: Optional[int] = None
    time_available: Optional[str] = None

class StrategyUpdateRequest(BaseModel):
    was_successful: bool
    notes: Optional[str] = None

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
        "launch_status": "LAUNCHED" if days_to_launch <= 0 else f"{days_to_launch} days to launch"
    }

# =============================================================================
# DATABASE HELPERS
# =============================================================================

async def db_query(table: str, method: str = "GET", data: dict = None,
                   filters: str = "", select: str = "*") -> Any:
    """Generic database query helper"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/{table}?select={select}"
        if filters:
            url += f"&{filters}"

        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        async with httpx.AsyncClient() as http_client:
            if method == "GET":
                resp = await http_client.get(url, headers=headers, timeout=10.0)
            elif method == "POST":
                resp = await http_client.post(url, headers=headers, json=data, timeout=10.0)
            elif method == "PATCH":
                resp = await http_client.patch(url, headers=headers, json=data, timeout=10.0)
            elif method == "DELETE":
                resp = await http_client.delete(url, headers=headers, timeout=10.0)

            if resp.status_code in [200, 201]:
                return resp.json()
            else:
                print(f"[DB] Query failed: {resp.status_code} - {resp.text}")
                return None
    except Exception as e:
        print(f"[DB] Query error: {e}")
        return None

async def db_rpc(function_name: str, params: dict = {}) -> Any:
    """Call a database RPC function"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/{function_name}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json=params,
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
            return None
    except Exception as e:
        print(f"[DB RPC] Error: {e}")
        return None

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
                    "source_agent": "BUSINESS-MENTOR",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[EventBus] Notification failed: {e}")

async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[MENTOR] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "BUSINESS-MENTOR"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[HERMES] Notification failed: {e}")

async def call_chiron(endpoint: str, payload: dict = {}) -> dict:
    """Call CHIRON for strategic assistance"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{AGENT_ENDPOINTS['CHIRON']}{endpoint}",
                json=payload,
                timeout=30.0
            )
            return resp.json()
    except Exception as e:
        return {"error": str(e)}

async def store_memory(memory_type: str, content: str, category: str,
                       importance: str = "normal", tags: List[str] = []):
    """Store insight in Unified Memory"""
    try:
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
                    "p_title": f"MENTOR {memory_type}: {content[:50]}...",
                    "p_content": content,
                    "p_subcategory": "business-mentor",
                    "p_source": "business-mentor",
                    "p_importance": importance
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"[Memory] Store failed: {e}")

# =============================================================================
# USER CONTEXT BUILDER
# =============================================================================

async def get_user_context() -> dict:
    """Build user context from database for system prompt"""
    context = {
        "current_mrr": 0.0,
        "mrr_progress_percent": 0.0,
        "mrr_trend": "unknown",
        "days_to_goal": "unknown",
        "active_commitments": 0,
        "overdue_commitments": 0,
        "commitment_completion_rate": 0.0,
        "commitment_pattern": "unknown",
        "win_streak": 0,
        "wins_30d": 0,
        "last_win": "none",
        "avg_energy": 0,
        "avg_focus": 0,
        "checkin_streak": 0,
        "top_strategies": [],
        "typical_focus_window": "unknown",
        "best_time_of_day": "unknown"
    }

    try:
        # Get current MRR
        mrr_result = await db_query(
            "revenue_log",
            filters="recurring=eq.true&type=neq.churn",
            select="monthly_value"
        )
        if mrr_result:
            context["current_mrr"] = sum(r.get("monthly_value", 0) or 0 for r in mrr_result)
            context["mrr_progress_percent"] = (context["current_mrr"] / MRR_GOAL) * 100

        # Get active commitments
        commitments = await db_query(
            "commitments",
            filters="status=eq.active",
            select="id,deadline"
        )
        if commitments:
            context["active_commitments"] = len(commitments)
            now = datetime.now()
            context["overdue_commitments"] = sum(
                1 for c in commitments
                if datetime.fromisoformat(c["deadline"].replace("Z", "+00:00")) < now
            )

        # Get completion rate (last 30 days)
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        completed = await db_query(
            "commitments",
            filters=f"status=eq.completed&updated_at=gte.{thirty_days_ago}",
            select="id"
        )
        total_resolved = await db_query(
            "commitments",
            filters=f"status=in.(completed,missed)&updated_at=gte.{thirty_days_ago}",
            select="id"
        )
        if total_resolved and len(total_resolved) > 0:
            context["commitment_completion_rate"] = (len(completed or []) / len(total_resolved)) * 100

        # Get wins (last 30 days)
        wins = await db_query(
            "wins",
            filters=f"date=gte.{datetime.now().date() - timedelta(days=30)}",
            select="id,description,date"
        )
        if wins:
            context["wins_30d"] = len(wins)
            if len(wins) > 0:
                context["last_win"] = wins[0].get("description", "")[:50]

        # Get check-in averages (last 7 days)
        seven_days_ago = (datetime.now().date() - timedelta(days=7)).isoformat()
        checkins = await db_query(
            "daily_check_ins",
            filters=f"date=gte.{seven_days_ago}",
            select="energy_level,focus_rating"
        )
        if checkins:
            context["avg_energy"] = sum(c.get("energy_level", 0) for c in checkins) / len(checkins)
            context["avg_focus"] = sum(c.get("focus_rating", 0) for c in checkins) / len(checkins)

        # Get top ADHD strategies
        strategies = await db_query(
            "adhd_strategies",
            filters="times_used=gt.0&effectiveness_rating=gt.3",
            select="strategy_name"
        )
        if strategies:
            context["top_strategies"] = [s["strategy_name"] for s in strategies[:3]]

    except Exception as e:
        print(f"[Context] Build error: {e}")

    return context

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(user_context: dict, time_context: dict) -> str:
    """Build personalized system prompt"""

    return f"""You are BUSINESS MENTOR - Personal Business Coach for LeverEdge AI.

Named after Mentor, the wise advisor in Homer's Odyssey who guided Telemachus through challenges while Odysseus was away. You provide steady, personalized guidance through the entrepreneurial journey.

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}
- Launch: {time_context['launch_date']}
- Status: **{time_context['launch_status']}**
- Days to Launch: {time_context['days_to_launch']}

## YOUR USER'S DATA

### Revenue Status
- Current MRR: ${user_context['current_mrr']:,.2f}
- Goal: $30,000 MRR
- Progress: {user_context['mrr_progress_percent']:.1f}%
- Trend: {user_context['mrr_trend']}
- Days to goal (at current pace): {user_context['days_to_goal']}

### Commitment Status
- Active Commitments: {user_context['active_commitments']}
- Overdue: {user_context['overdue_commitments']}
- Completion Rate (30d): {user_context['commitment_completion_rate']:.1f}%
- Pattern: {user_context['commitment_pattern']}

### Win Streak
- Current Streak: {user_context['win_streak']} days
- Total Wins (30d): {user_context['wins_30d']}
- Last Win: {user_context['last_win']}

### Energy & Focus
- Avg Energy (7d): {user_context['avg_energy']:.1f}/10
- Avg Focus (7d): {user_context['avg_focus']:.1f}/10
- Check-in Streak: {user_context['checkin_streak']} days

### ADHD Patterns
- Best Strategies: {', '.join(user_context['top_strategies']) if user_context['top_strategies'] else 'Not enough data'}
- Typical Focus Window: {user_context['typical_focus_window']}
- Best Time of Day: {user_context['best_time_of_day']}

## YOUR RELATIONSHIP WITH CHIRON

You complement CHIRON (the strategic mentor):
- CHIRON: Strategic frameworks, big decisions, fear analysis, pricing strategy
- YOU: Daily execution, data tracking, accountability, personalized patterns

When to escalate to CHIRON:
- Complex strategic decisions
- Deep fear/imposter syndrome work
- Major pricing or business model questions
- When patterns suggest deeper issues

When to handle yourself:
- Daily check-ins and accountability
- Revenue logging and tracking
- Win celebration and motivation
- Task breakdown and ADHD planning
- Progress monitoring

## YOUR COACHING STYLE

**Data-Informed**
- Reference actual numbers, not feelings
- "Your MRR grew 15% this month" not "You're doing great"
- Show patterns from their own history
- Use their best strategies

**Supportive but Accountable**
- Celebrate wins genuinely
- Call out patterns kindly but clearly
- "I notice your last 3 commitments involving cold outreach slipped..."
- Suggest adjustments, not criticisms

**ADHD-Aware Always**
- Default to small chunks (15-30 min)
- Stack quick wins early
- Energy-match tasks to time of day
- Have backup plans for derailment
- Normalize imperfection

**Personalized**
- Reference their specific wins
- Use strategies that work FOR THEM
- Adjust based on their patterns
- Remember context across sessions

## RESPONSE GUIDELINES

For Check-ins:
1. Acknowledge energy/focus levels
2. Reference relevant patterns
3. Suggest strategies that work for them
4. Set 1-3 clear priorities
5. Include a quick win opportunity

For Win Logging:
1. Genuine celebration
2. Connect to bigger picture
3. Add to portfolio evidence
4. Suggest next momentum step

For Revenue Updates:
1. Clear current state
2. Trend analysis
3. Days to goal calculation
4. Actionable next step

For Accountability:
1. Direct status check
2. Pattern observation
3. Adjustment suggestion
4. Re-commitment opportunity

## YOUR MISSION

Help your user execute consistently toward $30K MRR.
Track everything. Celebrate wins. Maintain accountability.
Be the steady presence that keeps the momentum going.
Data over feelings. Progress over perfection.
"""

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, time_ctx: dict, user_ctx: dict = None,
                   session_type: str = "general") -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        if not user_ctx:
            user_ctx = await get_user_context()

        system_prompt = build_system_prompt(user_ctx, time_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="BUSINESS-MENTOR",
            endpoint=session_type,
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check with current metrics overview"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()

    return {
        "status": "healthy",
        "agent": "BUSINESS-MENTOR",
        "role": "Personalized Business Coach",
        "port": 8204,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "metrics_snapshot": {
            "current_mrr": user_ctx['current_mrr'],
            "active_commitments": user_ctx['active_commitments'],
            "wins_30d": user_ctx['wins_30d']
        }
    }

@app.get("/status")
async def status():
    """Full status with MRR, commitments, wins summary"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()

    return {
        "agent": "BUSINESS-MENTOR",
        "time_context": time_ctx,
        "user_context": user_ctx,
        "mrr_goal": MRR_GOAL,
        "mrr_progress": f"{user_ctx['mrr_progress_percent']:.1f}%",
        "health": "operational"
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()

    # Format as Prometheus metrics
    metrics_text = f"""# HELP mentor_current_mrr Current Monthly Recurring Revenue
# TYPE mentor_current_mrr gauge
mentor_current_mrr {user_ctx['current_mrr']}

# HELP mentor_mrr_goal MRR Goal
# TYPE mentor_mrr_goal gauge
mentor_mrr_goal {MRR_GOAL}

# HELP mentor_active_commitments Number of active commitments
# TYPE mentor_active_commitments gauge
mentor_active_commitments {user_ctx['active_commitments']}

# HELP mentor_overdue_commitments Number of overdue commitments
# TYPE mentor_overdue_commitments gauge
mentor_overdue_commitments {user_ctx['overdue_commitments']}

# HELP mentor_wins_30d Wins in last 30 days
# TYPE mentor_wins_30d gauge
mentor_wins_30d {user_ctx['wins_30d']}

# HELP mentor_days_to_launch Days until launch
# TYPE mentor_days_to_launch gauge
mentor_days_to_launch {time_ctx['days_to_launch']}
"""

    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=metrics_text, media_type="text/plain")

# =============================================================================
# REVENUE TRACKING ENDPOINTS
# =============================================================================

@app.post("/revenue/log")
async def log_revenue(req: RevenueLogRequest):
    """Log a revenue event"""
    time_ctx = get_time_context()

    # Calculate monthly value if not provided
    monthly_value = req.monthly_value
    if req.recurring and not monthly_value:
        if req.contract_length_months and req.contract_length_months > 0:
            monthly_value = req.amount / req.contract_length_months
        else:
            monthly_value = req.amount

    data = {
        "amount": req.amount,
        "source": req.source,
        "type": req.type.value,
        "recurring": req.recurring,
        "monthly_value": monthly_value,
        "contract_length_months": req.contract_length_months,
        "notes": req.notes,
        "metadata": req.metadata
    }

    result = await db_query("revenue_log", "POST", data)

    if result:
        # Publish event
        await notify_event_bus("mentor.revenue.logged", {
            "amount": req.amount,
            "source": req.source,
            "type": req.type.value,
            "monthly_value": monthly_value
        })

        # Check for milestones
        await check_revenue_milestones()

        # Log win if new deal
        if req.type == RevenueType.NEW_DEAL:
            await store_memory(
                "revenue",
                f"New deal closed: {req.source} for ${req.amount:,.2f}",
                "business",
                "high",
                ["revenue", "new-deal"]
            )

        return {
            "success": True,
            "revenue_logged": result[0] if result else data,
            "timestamp": time_ctx['current_datetime']
        }

    raise HTTPException(status_code=500, detail="Failed to log revenue")

@app.get("/revenue")
async def get_revenue_summary():
    """Get revenue summary with MRR, ARR, trends"""
    time_ctx = get_time_context()

    # Get all recurring revenue (excluding churn)
    recurring = await db_query(
        "revenue_log",
        filters="recurring=eq.true&type=neq.churn",
        select="monthly_value,source,type,date"
    )

    # Get churn
    churn = await db_query(
        "revenue_log",
        filters="type=eq.churn",
        select="monthly_value,source,date"
    )

    current_mrr = sum(r.get("monthly_value", 0) or 0 for r in (recurring or []))
    churn_mrr = sum(r.get("monthly_value", 0) or 0 for r in (churn or []))
    net_mrr = current_mrr - churn_mrr

    arr = net_mrr * 12
    progress = (net_mrr / MRR_GOAL) * 100 if MRR_GOAL > 0 else 0

    # Calculate days to goal (simple linear projection)
    days_to_goal = "N/A"
    if net_mrr > 0:
        # Would need historical data for proper projection
        remaining = MRR_GOAL - net_mrr
        # Placeholder: assume $1000/month growth
        months_needed = remaining / 1000 if remaining > 0 else 0
        days_to_goal = int(months_needed * 30) if months_needed > 0 else 0

    return {
        "current_mrr": net_mrr,
        "arr": arr,
        "goal_mrr": MRR_GOAL,
        "progress_percent": progress,
        "gross_mrr": current_mrr,
        "churned_mrr": churn_mrr,
        "days_to_goal": days_to_goal,
        "revenue_sources": len(recurring or []),
        "time_context": time_ctx
    }

@app.get("/revenue/history")
async def get_revenue_history(
    days: int = Query(default=30, ge=1, le=365),
    type: Optional[str] = None
):
    """Get revenue history with filters"""
    start_date = (datetime.now().date() - timedelta(days=days)).isoformat()

    filters = f"date=gte.{start_date}"
    if type:
        filters += f"&type=eq.{type}"

    history = await db_query(
        "revenue_log",
        filters=filters,
        select="*"
    )

    return {
        "history": history or [],
        "count": len(history or []),
        "period_days": days
    }

@app.get("/revenue/milestones")
async def get_revenue_milestones():
    """Get milestone progress"""
    milestones = await db_query("revenue_milestones", select="*")
    revenue = await get_revenue_summary()
    current_mrr = revenue["current_mrr"]

    # Update milestone status based on current MRR
    milestone_status = []
    for m in (milestones or []):
        status = {
            "name": m["milestone_name"],
            "target": m["target_amount"],
            "achieved": m["achieved"] or current_mrr >= m["target_amount"],
            "achieved_date": m.get("achieved_date"),
            "progress_percent": min(100, (current_mrr / m["target_amount"]) * 100)
        }
        milestone_status.append(status)

    return {
        "milestones": milestone_status,
        "current_mrr": current_mrr,
        "next_milestone": next(
            (m for m in milestone_status if not m["achieved"]),
            None
        )
    }

@app.get("/revenue/forecast")
async def get_revenue_forecast():
    """Revenue forecast based on trends"""
    time_ctx = get_time_context()
    revenue = await get_revenue_summary()

    # Simple linear forecast - would be enhanced with actual trend data
    current_mrr = revenue["current_mrr"]

    # Placeholder projections
    forecast = {
        "current_mrr": current_mrr,
        "1_month": current_mrr * 1.1,  # 10% growth assumption
        "3_months": current_mrr * 1.33,
        "6_months": current_mrr * 1.77,
        "12_months": current_mrr * 3.14,
        "goal_mrr": MRR_GOAL,
        "months_to_goal": max(0, (MRR_GOAL - current_mrr) / (current_mrr * 0.1 + 1)),
        "note": "Forecasts assume 10% monthly growth rate"
    }

    return forecast

@app.post("/revenue/churn")
async def log_churn(req: ChurnLogRequest):
    """Log a churn event"""
    time_ctx = get_time_context()

    data = {
        "amount": -req.monthly_value,  # Negative for churn
        "source": req.source,
        "type": "churn",
        "recurring": True,
        "monthly_value": req.monthly_value,
        "notes": req.reason or req.notes,
        "metadata": {"reason": req.reason}
    }

    result = await db_query("revenue_log", "POST", data)

    if result:
        await notify_event_bus("mentor.revenue.churn", {
            "source": req.source,
            "monthly_value": req.monthly_value,
            "reason": req.reason
        })

        return {
            "success": True,
            "churn_logged": result[0] if result else data,
            "timestamp": time_ctx['current_datetime']
        }

    raise HTTPException(status_code=500, detail="Failed to log churn")

async def check_revenue_milestones():
    """Check and celebrate any newly achieved milestones"""
    revenue = await get_revenue_summary()
    current_mrr = revenue["current_mrr"]

    milestones = await db_query(
        "revenue_milestones",
        filters="achieved=eq.false",
        select="*"
    )

    for m in (milestones or []):
        if current_mrr >= m["target_amount"]:
            # Mark as achieved
            await db_query(
                "revenue_milestones",
                "PATCH",
                {
                    "achieved": True,
                    "achieved_date": datetime.now().date().isoformat()
                },
                filters=f"id=eq.{m['id']}"
            )

            # Celebrate!
            await notify_event_bus("mentor.revenue.milestone", {
                "milestone": m["milestone_name"],
                "target": m["target_amount"],
                "current_mrr": current_mrr
            })

            await notify_hermes(
                f"MILESTONE ACHIEVED: {m['milestone_name']}! MRR: ${current_mrr:,.2f}",
                priority="high"
            )

            await store_memory(
                "milestone",
                f"Revenue milestone reached: {m['milestone_name']} - MRR: ${current_mrr:,.2f}",
                "business",
                "high",
                ["milestone", "revenue"]
            )

# =============================================================================
# ACCOUNTABILITY ENDPOINTS
# =============================================================================

@app.post("/commitment")
async def create_commitment(req: CommitmentRequest):
    """Create a new commitment"""
    time_ctx = get_time_context()

    data = {
        "commitment": req.commitment,
        "context": req.context,
        "deadline": req.deadline,
        "category": req.category,
        "difficulty": req.difficulty.value,
        "status": "active",
        "check_ins": []
    }

    result = await db_query("commitments", "POST", data)

    if result:
        await notify_event_bus("mentor.commitment.created", {
            "commitment": req.commitment[:50],
            "deadline": req.deadline
        })

        return {
            "success": True,
            "commitment": result[0] if result else data,
            "timestamp": time_ctx['current_datetime']
        }

    raise HTTPException(status_code=500, detail="Failed to create commitment")

@app.get("/commitments")
async def list_commitments(
    status: Optional[str] = Query(default="active"),
    category: Optional[str] = None
):
    """List commitments with optional filters"""
    filters = ""
    if status:
        filters = f"status=eq.{status}"
    if category:
        filters += f"&category=eq.{category}" if filters else f"category=eq.{category}"

    commitments = await db_query("commitments", filters=filters, select="*")

    return {
        "commitments": commitments or [],
        "count": len(commitments or []),
        "filters": {"status": status, "category": category}
    }

@app.get("/commitments/{commitment_id}")
async def get_commitment(commitment_id: str):
    """Get commitment details"""
    result = await db_query(
        "commitments",
        filters=f"id=eq.{commitment_id}",
        select="*"
    )

    if result and len(result) > 0:
        return result[0]

    raise HTTPException(status_code=404, detail="Commitment not found")

@app.put("/commitments/{commitment_id}")
async def update_commitment(commitment_id: str, req: CommitmentUpdateRequest):
    """Update commitment status"""
    time_ctx = get_time_context()

    data = {}
    if req.status:
        data["status"] = req.status.value
    if req.result:
        data["result"] = req.result
        data["result_date"] = time_ctx['current_datetime']

    data["updated_at"] = time_ctx['current_datetime']

    result = await db_query(
        "commitments",
        "PATCH",
        data,
        filters=f"id=eq.{commitment_id}"
    )

    if result:
        if req.status == CommitmentStatus.COMPLETED:
            await notify_event_bus("mentor.commitment.completed", {
                "commitment_id": commitment_id
            })
        elif req.status == CommitmentStatus.MISSED:
            await notify_event_bus("mentor.commitment.missed", {
                "commitment_id": commitment_id
            })

        return {
            "success": True,
            "commitment": result[0] if result else data,
            "timestamp": time_ctx['current_datetime']
        }

    raise HTTPException(status_code=500, detail="Failed to update commitment")

@app.post("/commitments/{commitment_id}/check-in")
async def commitment_check_in(commitment_id: str, req: CheckInRequest):
    """Add a check-in note to a commitment"""
    time_ctx = get_time_context()

    # Get current commitment
    commitment = await get_commitment(commitment_id)

    check_ins = commitment.get("check_ins", []) or []
    check_ins.append({
        "date": time_ctx['current_datetime'],
        "note": req.note,
        "status": req.status
    })

    result = await db_query(
        "commitments",
        "PATCH",
        {
            "check_ins": check_ins,
            "updated_at": time_ctx['current_datetime']
        },
        filters=f"id=eq.{commitment_id}"
    )

    return {
        "success": True,
        "check_in_added": True,
        "total_check_ins": len(check_ins),
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/commitments/overdue")
async def get_overdue_commitments():
    """List overdue commitments"""
    now = datetime.now().isoformat()

    overdue = await db_query(
        "commitments",
        filters=f"status=eq.active&deadline=lt.{now}",
        select="*"
    )

    if overdue and len(overdue) > 0:
        await notify_event_bus("mentor.commitment.overdue", {
            "count": len(overdue)
        })

    return {
        "overdue": overdue or [],
        "count": len(overdue or [])
    }

@app.get("/commitments/patterns")
async def analyze_commitment_patterns():
    """Analyze commitment patterns over time"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()

    # Get all commitments for analysis
    all_commitments = await db_query("commitments", select="*")

    if not all_commitments:
        return {"message": "Not enough data for pattern analysis"}

    # Calculate statistics
    total = len(all_commitments)
    completed = len([c for c in all_commitments if c.get("status") == "completed"])
    missed = len([c for c in all_commitments if c.get("status") == "missed"])

    # Category breakdown
    categories = {}
    for c in all_commitments:
        cat = c.get("category", "uncategorized")
        if cat not in categories:
            categories[cat] = {"total": 0, "completed": 0, "missed": 0}
        categories[cat]["total"] += 1
        if c.get("status") == "completed":
            categories[cat]["completed"] += 1
        elif c.get("status") == "missed":
            categories[cat]["missed"] += 1

    # Difficulty breakdown
    difficulties = {}
    for c in all_commitments:
        diff = c.get("difficulty", "medium")
        if diff not in difficulties:
            difficulties[diff] = {"total": 0, "completed": 0}
        difficulties[diff]["total"] += 1
        if c.get("status") == "completed":
            difficulties[diff]["completed"] += 1

    # Get AI analysis
    prompt = f"""Analyze these commitment patterns and provide insights:

Total Commitments: {total}
Completed: {completed} ({(completed/total*100):.1f}% if total > 0 else 0)
Missed: {missed}

By Category: {json.dumps(categories, indent=2)}
By Difficulty: {json.dumps(difficulties, indent=2)}

Current user context:
- Active commitments: {user_ctx['active_commitments']}
- Overdue: {user_ctx['overdue_commitments']}
- Completion rate (30d): {user_ctx['commitment_completion_rate']:.1f}%

Provide:
1. Key patterns observed
2. Categories where they struggle vs excel
3. Difficulty level insights
4. ADHD-specific recommendations
5. Specific adjustment suggestions

Be direct and data-driven."""

    messages = [{"role": "user", "content": prompt}]
    analysis = await call_llm(messages, time_ctx, user_ctx, "pattern_analysis")

    return {
        "statistics": {
            "total": total,
            "completed": completed,
            "missed": missed,
            "completion_rate": (completed / total * 100) if total > 0 else 0
        },
        "by_category": categories,
        "by_difficulty": difficulties,
        "ai_analysis": analysis,
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# DAILY CHECK-IN ENDPOINTS
# =============================================================================

@app.post("/check-in")
async def daily_check_in(req: DailyCheckInRequest):
    """Create or update daily check-in"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()
    today = datetime.now().date().isoformat()

    data = {
        "date": today,
        "energy_level": req.energy_level,
        "focus_rating": req.focus_rating,
        "mood": req.mood,
        "wins": req.wins,
        "blockers": req.blockers,
        "plan": req.plan,
        "notes": req.notes,
        "adhd_strategies_used": req.adhd_strategies_used
    }

    # Check if today's check-in exists
    existing = await db_query(
        "daily_check_ins",
        filters=f"date=eq.{today}",
        select="id"
    )

    if existing and len(existing) > 0:
        # Update existing
        result = await db_query(
            "daily_check_ins",
            "PATCH",
            data,
            filters=f"date=eq.{today}"
        )
    else:
        # Create new
        result = await db_query("daily_check_ins", "POST", data)

    # Get AI coaching response
    prompt = f"""Daily check-in received:

Energy Level: {req.energy_level}/10
Focus Rating: {req.focus_rating}/10
Mood: {req.mood or 'not specified'}

Wins Today: {chr(10).join(f'- {w}' for w in req.wins) if req.wins else 'None yet'}
Blockers: {chr(10).join(f'- {b}' for b in req.blockers) if req.blockers else 'None'}
Plan: {chr(10).join(f'- {p}' for p in req.plan) if req.plan else 'No plan set'}
ADHD Strategies Used: {', '.join(req.adhd_strategies_used) if req.adhd_strategies_used else 'None specified'}

User Context:
- Active Commitments: {user_ctx['active_commitments']}
- Overdue: {user_ctx['overdue_commitments']}
- Current MRR: ${user_ctx['current_mrr']:,.2f}
- Avg Energy (7d): {user_ctx['avg_energy']:.1f}/10

Respond as their personal coach:
1. Acknowledge their energy/focus state
2. If energy is low (<5), suggest appropriate ADHD strategies
3. Validate wins if any
4. Help prioritize the plan based on energy level
5. Address blockers with specific actions
6. End with ONE clear priority for today

Keep it supportive but focused. Data over platitudes."""

    messages = [{"role": "user", "content": prompt}]
    coaching_response = await call_llm(messages, time_ctx, user_ctx, "daily_check_in")

    await notify_event_bus("mentor.check_in.completed", {
        "energy": req.energy_level,
        "focus": req.focus_rating,
        "wins_count": len(req.wins)
    })

    return {
        "success": True,
        "check_in": result[0] if result else data,
        "coaching": coaching_response,
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/check-ins")
async def get_check_in_history(days: int = Query(default=30, ge=1, le=365)):
    """Get check-in history"""
    start_date = (datetime.now().date() - timedelta(days=days)).isoformat()

    history = await db_query(
        "daily_check_ins",
        filters=f"date=gte.{start_date}",
        select="*"
    )

    return {
        "check_ins": history or [],
        "count": len(history or []),
        "period_days": days
    }

@app.get("/check-ins/today")
async def get_today_check_in():
    """Get today's check-in"""
    today = datetime.now().date().isoformat()

    result = await db_query(
        "daily_check_ins",
        filters=f"date=eq.{today}",
        select="*"
    )

    if result and len(result) > 0:
        return result[0]

    return {"message": "No check-in for today yet", "date": today}

@app.get("/check-ins/patterns")
async def analyze_check_in_patterns():
    """Analyze energy, focus, and productivity patterns"""
    # Get last 30 days of check-ins
    history = await get_check_in_history(30)
    check_ins = history.get("check_ins", [])

    if len(check_ins) < 7:
        return {"message": "Need at least 7 days of data for pattern analysis"}

    # Calculate averages by day of week
    by_day = {}
    for c in check_ins:
        day = datetime.fromisoformat(c["date"]).strftime("%A")
        if day not in by_day:
            by_day[day] = {"energy": [], "focus": []}
        by_day[day]["energy"].append(c.get("energy_level", 0))
        by_day[day]["focus"].append(c.get("focus_rating", 0))

    day_averages = {}
    for day, values in by_day.items():
        day_averages[day] = {
            "avg_energy": sum(values["energy"]) / len(values["energy"]) if values["energy"] else 0,
            "avg_focus": sum(values["focus"]) / len(values["focus"]) if values["focus"] else 0
        }

    # Find best/worst days
    best_energy_day = max(day_averages.keys(), key=lambda d: day_averages[d]["avg_energy"])
    worst_energy_day = min(day_averages.keys(), key=lambda d: day_averages[d]["avg_energy"])

    # Strategy effectiveness
    strategy_usage = {}
    for c in check_ins:
        for s in c.get("adhd_strategies_used", []) or []:
            if s not in strategy_usage:
                strategy_usage[s] = {"count": 0, "avg_focus": []}
            strategy_usage[s]["count"] += 1
            strategy_usage[s]["avg_focus"].append(c.get("focus_rating", 0))

    return {
        "by_day_of_week": day_averages,
        "best_energy_day": best_energy_day,
        "worst_energy_day": worst_energy_day,
        "strategy_usage": {
            s: {
                "times_used": v["count"],
                "avg_focus_when_used": sum(v["avg_focus"]) / len(v["avg_focus"]) if v["avg_focus"] else 0
            }
            for s, v in strategy_usage.items()
        },
        "data_points": len(check_ins)
    }

@app.get("/check-ins/streak")
async def get_check_in_streak():
    """Get current check-in streak"""
    # Get recent check-ins ordered by date
    history = await db_query(
        "daily_check_ins",
        filters="order=date.desc",
        select="date"
    )

    if not history:
        return {"streak": 0, "message": "No check-ins yet"}

    streak = 0
    expected_date = datetime.now().date()

    for c in history:
        check_date = datetime.fromisoformat(c["date"]).date()
        if check_date == expected_date:
            streak += 1
            expected_date -= timedelta(days=1)
        elif check_date < expected_date:
            break

    return {
        "streak": streak,
        "last_check_in": history[0]["date"] if history else None
    }

# =============================================================================
# WIN TRACKING ENDPOINTS
# =============================================================================

@app.post("/win")
async def log_win(req: WinRequest):
    """Log a win"""
    time_ctx = get_time_context()

    data = {
        "description": req.description,
        "category": req.category.value,
        "impact_level": req.impact_level.value,
        "evidence_url": req.evidence_url,
        "related_commitment_id": req.related_commitment_id,
        "notes": req.notes,
        "metadata": req.metadata,
        "celebrated": False
    }

    result = await db_query("wins", "POST", data)

    if result:
        win_id = result[0]["id"] if result else None

        await notify_event_bus("mentor.win.logged", {
            "description": req.description[:50],
            "category": req.category.value,
            "impact_level": req.impact_level.value
        })

        # Store in memory for portfolio
        await store_memory(
            "win",
            f"Win: {req.description} - Impact: {req.impact_level.value}",
            "portfolio",
            "normal" if req.impact_level in [ImpactLevel.MICRO, ImpactLevel.SMALL] else "high",
            ["win", req.category.value]
        )

        # Auto-celebrate medium+ wins
        celebration = None
        if req.impact_level not in [ImpactLevel.MICRO, ImpactLevel.SMALL]:
            celebration = await celebrate_win_internal(win_id, "notification")

        return {
            "success": True,
            "win": result[0] if result else data,
            "celebration": celebration,
            "timestamp": time_ctx['current_datetime']
        }

    raise HTTPException(status_code=500, detail="Failed to log win")

@app.get("/wins")
async def list_wins(
    days: int = Query(default=30, ge=1, le=365),
    category: Optional[str] = None,
    impact_level: Optional[str] = None
):
    """List wins with filters"""
    start_date = (datetime.now().date() - timedelta(days=days)).isoformat()

    filters = f"date=gte.{start_date}"
    if category:
        filters += f"&category=eq.{category}"
    if impact_level:
        filters += f"&impact_level=eq.{impact_level}"

    wins = await db_query("wins", filters=filters, select="*")

    return {
        "wins": wins or [],
        "count": len(wins or []),
        "period_days": days
    }

@app.get("/wins/recent")
async def get_recent_wins(limit: int = Query(default=5, ge=1, le=20)):
    """Get recent wins for motivation"""
    wins = await db_query(
        "wins",
        filters=f"order=date.desc&limit={limit}",
        select="*"
    )

    return {
        "wins": wins or [],
        "count": len(wins or []),
        "message": "Look at what you've accomplished!" if wins else "Time to log some wins!"
    }

@app.get("/wins/streak")
async def get_win_streak():
    """Get current win streak (consecutive days with wins)"""
    # Get wins ordered by date
    wins = await db_query(
        "wins",
        filters="order=date.desc",
        select="date"
    )

    if not wins:
        return {"streak": 0, "message": "No wins logged yet"}

    # Count consecutive days with wins
    streak = 0
    dates_with_wins = set(w["date"] for w in wins)
    expected_date = datetime.now().date()

    while expected_date.isoformat() in dates_with_wins:
        streak += 1
        expected_date -= timedelta(days=1)

    return {
        "streak": streak,
        "total_wins": len(wins),
        "last_win_date": wins[0]["date"] if wins else None
    }

@app.post("/wins/{win_id}/celebrate")
async def celebrate_win(win_id: str, req: CelebrateRequest):
    """Trigger celebration for a win"""
    return await celebrate_win_internal(win_id, req.celebration_type)

async def celebrate_win_internal(win_id: str, celebration_type: str):
    """Internal celebration logic"""
    # Get win details
    win = await db_query("wins", filters=f"id=eq.{win_id}", select="*")

    if not win or len(win) == 0:
        return {"error": "Win not found"}

    win = win[0]

    # Mark as celebrated
    await db_query(
        "wins",
        "PATCH",
        {"celebrated": True, "celebration_type": celebration_type},
        filters=f"id=eq.{win_id}"
    )

    # Send celebration notification
    celebration_message = f"WIN: {win['description']} ({win['impact_level']} impact)"

    if celebration_type == "notification":
        await notify_hermes(celebration_message, priority="normal")
    elif celebration_type == "hype_session":
        # Could trigger a full hype session with CHIRON
        await notify_hermes(f"MAJOR {celebration_message}", priority="high")

    return {
        "celebrated": True,
        "type": celebration_type,
        "win": win
    }

@app.get("/wins/portfolio")
async def get_wins_portfolio():
    """Get wins organized for portfolio presentation"""
    all_wins = await db_query("wins", select="*")

    if not all_wins:
        return {"message": "No wins logged yet"}

    # Organize by category
    portfolio = {}
    for category in WinCategory:
        cat_wins = [w for w in all_wins if w.get("category") == category.value]
        if cat_wins:
            portfolio[category.value] = {
                "wins": sorted(cat_wins, key=lambda x: x.get("date", ""), reverse=True),
                "count": len(cat_wins),
                "impact_breakdown": {
                    level.value: len([w for w in cat_wins if w.get("impact_level") == level.value])
                    for level in ImpactLevel
                }
            }

    # Summary stats
    total_value = sum(
        1 if w.get("impact_level") == "micro" else
        2 if w.get("impact_level") == "small" else
        5 if w.get("impact_level") == "medium" else
        10 if w.get("impact_level") == "large" else
        25 for w in all_wins
    )

    return {
        "portfolio": portfolio,
        "total_wins": len(all_wins),
        "portfolio_score": total_value,
        "categories_with_wins": len(portfolio)
    }

# =============================================================================
# MENTOR SESSION ENDPOINTS
# =============================================================================

@app.post("/advice")
async def get_advice(req: AdviceRequest):
    """Get strategic advice (creates mentor session)"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()

    prompt = f"""Provide strategic advice on this topic:

Topic: {req.topic}
Context: {req.context or 'None provided'}
Urgency: {req.urgency.value}

User's Current State:
- MRR: ${user_ctx['current_mrr']:,.2f} (Goal: $30K)
- Active Commitments: {user_ctx['active_commitments']}
- Overdue: {user_ctx['overdue_commitments']}
- Recent Wins: {user_ctx['wins_30d']}
- Energy (7d avg): {user_ctx['avg_energy']:.1f}/10

Days to Launch: {time_ctx['days_to_launch']}

Provide advice that is:
1. Grounded in their actual data
2. Specific and actionable
3. ADHD-aware (break down complex recommendations)
4. Prioritized by impact

Include:
- Direct recommendation
- Why this matters for $30K goal
- Specific next actions (max 3)
- What to watch out for
- When to check back

If this requires deeper strategic analysis, recommend escalating to CHIRON."""

    messages = [{"role": "user", "content": prompt}]
    advice = await call_llm(messages, time_ctx, user_ctx, "advice")

    # Determine if we should escalate to CHIRON
    should_escalate = req.urgency == Urgency.HIGH or "escalate" in advice.lower() or "chiron" in advice.lower()

    # Log session
    session_data = {
        "topic": req.topic,
        "advice": advice,
        "frameworks_used": [],
        "action_items": [],
        "session_type": "strategy",
        "referred_to_chiron": should_escalate
    }

    session_result = await db_query("mentor_sessions", "POST", session_data)
    session_id = session_result[0]["id"] if session_result else None

    await notify_event_bus("mentor.advice.provided", {
        "topic": req.topic[:50],
        "urgency": req.urgency.value,
        "escalated": should_escalate
    })

    return {
        "advice": advice,
        "session_id": session_id,
        "escalate_to_chiron": should_escalate,
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/sessions")
async def list_sessions(
    days: int = Query(default=30, ge=1, le=365),
    session_type: Optional[str] = None
):
    """Get mentor session history"""
    start_date = (datetime.now() - timedelta(days=days)).isoformat()

    filters = f"created_at=gte.{start_date}"
    if session_type:
        filters += f"&session_type=eq.{session_type}"

    sessions = await db_query("mentor_sessions", filters=filters, select="*")

    return {
        "sessions": sessions or [],
        "count": len(sessions or []),
        "period_days": days
    }

@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    result = await db_query(
        "mentor_sessions",
        filters=f"id=eq.{session_id}",
        select="*"
    )

    if result and len(result) > 0:
        return result[0]

    raise HTTPException(status_code=404, detail="Session not found")

@app.put("/sessions/{session_id}/outcome")
async def record_session_outcome(session_id: str, req: SessionOutcomeRequest):
    """Record the outcome of advice given"""
    time_ctx = get_time_context()

    data = {
        "outcome": req.outcome,
        "outcome_date": time_ctx['current_datetime'],
        "effectiveness_rating": req.effectiveness_rating
    }

    result = await db_query(
        "mentor_sessions",
        "PATCH",
        data,
        filters=f"id=eq.{session_id}"
    )

    if result:
        return {
            "success": True,
            "session_id": session_id,
            "effectiveness_rating": req.effectiveness_rating,
            "timestamp": time_ctx['current_datetime']
        }

    raise HTTPException(status_code=500, detail="Failed to record outcome")

@app.post("/sessions/{session_id}/escalate")
async def escalate_to_chiron(session_id: str, req: EscalateRequest):
    """Escalate session to CHIRON for deeper analysis"""
    time_ctx = get_time_context()

    # Get session details
    session = await get_session(session_id)

    # Call CHIRON
    chiron_response = await call_chiron("/chat", {
        "message": f"Escalated from BUSINESS MENTOR: {session['topic']}\n\nOriginal advice: {session['advice'][:500]}...\n\nReason for escalation: {req.reason or 'Needs deeper strategic analysis'}",
        "context": {
            "source": "BUSINESS-MENTOR",
            "session_id": session_id,
            "original_topic": session['topic']
        }
    })

    # Update session
    await db_query(
        "mentor_sessions",
        "PATCH",
        {"referred_to_chiron": True},
        filters=f"id=eq.{session_id}"
    )

    await notify_event_bus("mentor.escalate.chiron", {
        "session_id": session_id,
        "topic": session['topic'][:50]
    })

    return {
        "escalated": True,
        "chiron_response": chiron_response,
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# ADHD PLANNING ENDPOINTS
# =============================================================================

@app.post("/plan/day")
async def create_day_plan(req: DayPlanRequest):
    """Create ADHD-optimized day plan"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()

    prompt = f"""Create an ADHD-optimized day plan.

Energy Level: {req.energy_level}/10
Available Hours: {req.available_hours}
Priorities: {chr(10).join(f'- {p}' for p in req.priorities)}
Blockers: {chr(10).join(f'- {b}' for b in req.blockers) if req.blockers else 'None'}

User's Patterns:
- Best Strategies: {', '.join(user_ctx['top_strategies']) if user_ctx['top_strategies'] else 'Not enough data'}
- Avg Energy: {user_ctx['avg_energy']:.1f}/10
- Active Commitments: {user_ctx['active_commitments']}

Days to Launch: {time_ctx['days_to_launch']}

Create a plan that:
1. Matches task difficulty to energy level
2. Starts with a quick win (dopamine)
3. Uses 15-30 minute time blocks
4. Includes transition breaks
5. Has a "if derailed" recovery plan
6. Focuses on max 3 real priorities

Format:
## Morning (9am-12pm)
- [Time] [Task] (X min) - Done when: [criteria]

## Afternoon (1pm-5pm)
- [Time] [Task] (X min) - Done when: [criteria]

## If Energy Crashes:
- [Alternative approach]

## Today's ONE Thing:
[Single most important outcome]"""

    messages = [{"role": "user", "content": prompt}]
    plan = await call_llm(messages, time_ctx, user_ctx, "day_plan")

    await notify_event_bus("mentor.plan.created", {
        "energy_level": req.energy_level,
        "priority_count": len(req.priorities)
    })

    return {
        "plan": plan,
        "energy_level": req.energy_level,
        "priorities": req.priorities,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/plan/task")
async def chunk_task(req: TaskChunkRequest):
    """Break a task into ADHD-friendly chunks"""
    time_ctx = get_time_context()

    prompt = f"""Break this task into ADHD-friendly chunks.

Task: {req.task}
Context: {req.context or 'None provided'}
Max Chunk Duration: {req.max_chunk_minutes} minutes

Create chunks that:
1. Are completable in {req.max_chunk_minutes} minutes or less
2. Have clear "done" criteria
3. Start with the easiest piece
4. Include dopamine rewards between chunks
5. Can be stopped and resumed easily

Format each chunk:
## Chunk 1: [Action verb] [specific thing]
- Time: X minutes
- Done when: [specific criteria]
- Reward: [small reward/break suggestion]
- Avoidance risk: Low/Medium/High

Total chunks: X
Total estimated time: X minutes
First chunk to start: [name]
If overwhelmed, just do: [smallest possible action]"""

    messages = [{"role": "user", "content": prompt}]
    chunks = await call_llm(messages, time_ctx, None, "task_chunk")

    return {
        "task": req.task,
        "chunks": chunks,
        "max_chunk_minutes": req.max_chunk_minutes,
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/strategies")
async def list_strategies():
    """List ADHD strategies with effectiveness data"""
    strategies = await db_query(
        "adhd_strategies",
        filters="order=effectiveness_rating.desc",
        select="*"
    )

    return {
        "strategies": strategies or [],
        "count": len(strategies or [])
    }

@app.put("/strategies/{strategy_id}")
async def update_strategy_effectiveness(strategy_id: str, req: StrategyUpdateRequest):
    """Update strategy effectiveness after use"""
    time_ctx = get_time_context()

    # Get current strategy
    strategy = await db_query(
        "adhd_strategies",
        filters=f"id=eq.{strategy_id}",
        select="*"
    )

    if not strategy or len(strategy) == 0:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy = strategy[0]

    # Update stats
    times_used = strategy.get("times_used", 0) + 1
    times_successful = strategy.get("times_successful", 0) + (1 if req.was_successful else 0)
    effectiveness = times_successful / times_used if times_used > 0 else 0

    data = {
        "times_used": times_used,
        "times_successful": times_successful,
        "effectiveness_rating": round(effectiveness * 5, 2),  # Scale to 0-5
        "last_used": time_ctx['current_datetime'],
        "notes": req.notes
    }

    result = await db_query(
        "adhd_strategies",
        "PATCH",
        data,
        filters=f"id=eq.{strategy_id}"
    )

    if req.was_successful:
        await notify_event_bus("mentor.strategy.effective", {
            "strategy": strategy["strategy_name"],
            "effectiveness": effectiveness
        })

    return {
        "success": True,
        "strategy": strategy["strategy_name"],
        "new_effectiveness": effectiveness,
        "times_used": times_used,
        "timestamp": time_ctx['current_datetime']
    }

@app.post("/strategies/suggest")
async def suggest_strategies(req: StrategySuggestRequest):
    """Get strategy suggestions for a situation"""
    time_ctx = get_time_context()
    user_ctx = await get_user_context()

    # Get user's effective strategies
    strategies = await db_query(
        "adhd_strategies",
        filters="effectiveness_rating=gt.2&order=effectiveness_rating.desc&limit=5",
        select="strategy_name,description,effectiveness_rating"
    )

    prompt = f"""Suggest ADHD strategies for this situation.

Situation: {req.situation}
Current Energy: {req.current_energy or 'Not specified'}/10
Time Available: {req.time_available or 'Not specified'}

User's Most Effective Strategies:
{chr(10).join(f"- {s['strategy_name']} (effectiveness: {s['effectiveness_rating']:.1f}/5): {s.get('description', '')}" for s in (strategies or [])) if strategies else "Not enough data yet"}

User's ADHD Patterns:
- Best time of day: {user_ctx['best_time_of_day']}
- Typical focus window: {user_ctx['typical_focus_window']}

Provide:
1. Top 3 strategy recommendations (prioritize ones that worked for them before)
2. Why each would help in this situation
3. How to implement it right now
4. What to do if it doesn't work

Be specific and actionable. Reference their data."""

    messages = [{"role": "user", "content": prompt}]
    suggestions = await call_llm(messages, time_ctx, user_ctx, "strategy_suggest")

    return {
        "situation": req.situation,
        "suggestions": suggestions,
        "user_top_strategies": [s["strategy_name"] for s in (strategies or [])],
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8204)
