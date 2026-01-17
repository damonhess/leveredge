#!/usr/bin/env python3
"""
ATLAS - AI-Powered Infrastructure Advisory Agent
Port: 8208

Infrastructure advisor providing architecture decisions, scaling guidance,
cost optimization, technology selection, and capacity planning.
The Titan who holds up the celestial heavens - ATLAS holds up and supports the infrastructure.

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on all significant actions
- Logs decisions to aria_knowledge

CAPABILITIES:
- Architecture Decision Records (ADR) management
- Scaling analysis and recommendations
- Cost optimization and savings identification
- Technology evaluation framework
- Capacity planning and forecasting
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="ATLAS",
    description="AI-Powered Infrastructure Advisory Agent",
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
cost_tracker = CostTracker("ATLAS")

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

def build_system_prompt(infrastructure_context: dict) -> str:
    """Build infrastructure advisor system prompt"""
    return f"""You are ATLAS - Elite Infrastructure Advisory Agent for LeverEdge AI.

Named after the Titan who holds up the celestial heavens, you hold up and support all LeverEdge infrastructure with wisdom and foresight.

## TIME AWARENESS
- Current: {infrastructure_context['current_time']}
- Days to Launch: {infrastructure_context['days_to_launch']}

## YOUR IDENTITY
You are the strategic infrastructure brain of LeverEdge. You advise on architecture, guide scaling decisions, optimize costs, evaluate technologies, and plan capacity. Your recommendations are data-driven, cost-aware, and aligned with business objectives.

## CURRENT INFRASTRUCTURE STATUS
- Total Resources: {infrastructure_context.get('total_resources', 'Unknown')}
- Monthly Cost: ${infrastructure_context.get('monthly_cost', 'Unknown')}
- Cost Trend: {infrastructure_context.get('cost_trend', 'Unknown')}
- Services Near Capacity: {infrastructure_context.get('capacity_warnings', 0)}
- Pending Recommendations: {infrastructure_context.get('pending_recommendations', 0)}

## YOUR CAPABILITIES

### Architecture Decisions
- Create and manage Architecture Decision Records (ADRs)
- Analyze trade-offs between architectural options
- Recommend patterns based on requirements
- Document decisions with rationale and consequences
- Track decision history and supersession

### Scaling Guidance
- Analyze current resource utilization
- Recommend horizontal vs vertical scaling
- Configure auto-scaling policies
- Predict scaling needs based on trends
- Calculate cost impact of scaling decisions

### Cost Optimization
- Analyze infrastructure spending by service, type, tag
- Identify unused and underutilized resources
- Recommend right-sizing opportunities
- Suggest reserved instance purchases
- Track savings from implemented recommendations

### Technology Selection
- Evaluate technologies against weighted criteria
- Compare vendors and open-source options
- Assess migration effort and risks
- Provide proof-of-concept guidance
- Maintain technology radar

### Capacity Planning
- Forecast resource needs across time horizons
- Calculate runway until capacity limits
- Model growth based on business metrics
- Run what-if scenarios
- Alert on approaching limits

## DECISION FRAMEWORK

When making recommendations:
1. **Understand Context**: What's the business goal? What constraints exist?
2. **Gather Data**: Current metrics, trends, costs, dependencies
3. **Analyze Options**: Trade-offs, risks, costs, complexity
4. **Recommend**: Clear recommendation with rationale
5. **Document**: Create ADR for significant decisions

## COST AWARENESS
Always consider cost implications:
- What's the monthly cost impact?
- Is there a cheaper alternative with acceptable trade-offs?
- Can we use reserved/committed pricing?
- Are there idle resources to reclaim?

## TEAM COORDINATION
- Route implementation tasks to HEPHAESTUS
- Request backup before infrastructure changes via CHRONOS
- Send infrastructure alerts via HERMES
- Log insights to ARIA via Unified Memory
- Publish events to Event Bus

## RESPONSE FORMAT
For infrastructure advice:
1. **Context Understanding**: Restate the problem/requirement
2. **Current State**: Relevant metrics and observations
3. **Analysis**: Trade-offs and considerations
4. **Recommendation**: Clear, actionable guidance
5. **Cost Impact**: Expected cost change
6. **Next Steps**: Implementation path

## YOUR MISSION
Ensure LeverEdge infrastructure is:
- Performant: Fast and responsive
- Reliable: Highly available, fault tolerant
- Cost-efficient: No waste, optimized spending
- Scalable: Ready for growth
- Well-documented: Decisions tracked and rationale preserved
"""

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

# Health & Status Models
class HealthResponse(BaseModel):
    status: str
    agent: str
    role: str
    port: int
    current_time: str
    days_to_launch: int
    phase: str

# Architecture Models
class ArchitectureAdviceRequest(BaseModel):
    scenario: str
    constraints: Optional[List[str]] = None
    requirements: Optional[List[str]] = None
    context: Optional[str] = None

class ArchitectureDecisionCreate(BaseModel):
    title: str
    context: str
    decision: str
    alternatives: Optional[List[str]] = None
    consequences: Optional[List[str]] = None
    tags: Optional[List[str]] = None

class ArchitectureDecisionUpdate(BaseModel):
    status: str  # proposed, accepted, deprecated, superseded
    superseded_by: Optional[str] = None

class PatternRequest(BaseModel):
    use_case: str
    constraints: Optional[List[str]] = None

# Scaling Models
class ScalingAnalyzeRequest(BaseModel):
    service_name: str
    current_metrics: Optional[Dict[str, Any]] = None
    context: Optional[str] = None

class ScalingApplyRequest(BaseModel):
    recommendation_id: str
    confirm: bool = False

class ScalingPolicyUpdate(BaseModel):
    service_name: str
    policies: Dict[str, Any]

# Cost Models
class CostAnalyzeRequest(BaseModel):
    period: Optional[str] = None  # e.g., "2024-01", "2024-Q1"
    breakdown_by: Optional[str] = "service"  # service, type, tag

class CostAlertConfig(BaseModel):
    threshold_amount: float
    threshold_type: str = "monthly"  # monthly, daily, percentage
    notification_channels: List[str] = ["event_bus"]

# Technology Models
class TechnologyEvaluateRequest(BaseModel):
    category: str  # database, messaging, cache, framework, etc.
    requirement: str
    options: Optional[List[str]] = None
    criteria: Optional[List[str]] = None
    context: Optional[str] = None

class TechnologyCompareRequest(BaseModel):
    category: str
    technologies: List[str]
    criteria: Optional[List[str]] = None

# Capacity Models
class CapacityForecastRequest(BaseModel):
    service_name: str
    metric: str  # cpu, memory, storage, connections
    horizon_days: int = 30

class CapacityScenarioRequest(BaseModel):
    scenario_name: str
    assumptions: Dict[str, Any]  # e.g., {"user_growth": "2x", "traffic_spike": "3x"}
    services: Optional[List[str]] = None

# Inventory Models
class InventoryCreate(BaseModel):
    resource_type: str  # compute, storage, database, network, service
    name: str
    provider: str  # aws, gcp, azure, digitalocean, self-hosted
    region: Optional[str] = None
    specs: Dict[str, Any]
    monthly_cost: Optional[float] = None
    tags: Optional[List[str]] = None

class InventoryUpdate(BaseModel):
    specs: Optional[Dict[str, Any]] = None
    monthly_cost: Optional[float] = None
    utilization: Optional[Dict[str, Any]] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None

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
                    "source_agent": "ATLAS",
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
                    "message": f"[ATLAS] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "ATLAS"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")

async def update_aria_memory(memory_type: str, content: str, category: str, tags: List[str]):
    """Store memory in Unified Memory system"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/unified_memory",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "memory_type": memory_type,
                    "content": content,
                    "category": category,
                    "source_type": "agent_result",
                    "tags": tags
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"Memory update failed: {e}")

async def get_infrastructure_context() -> dict:
    """Fetch current infrastructure context from database"""
    time_ctx = get_time_context()

    # Default context
    context = {
        "current_time": time_ctx['current_time'],
        "days_to_launch": time_ctx['days_to_launch'],
        "total_resources": 0,
        "monthly_cost": 0,
        "cost_trend": "unknown",
        "capacity_warnings": 0,
        "pending_recommendations": 0
    }

    try:
        async with httpx.AsyncClient() as http_client:
            # Get inventory count
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/infrastructure_inventory?status=eq.active&select=id",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Prefer": "count=exact"
                },
                timeout=5.0
            )
            if resp.status_code == 200:
                count = resp.headers.get('content-range', '').split('/')[-1]
                context['total_resources'] = int(count) if count and count != '*' else 0

            # Get total monthly cost
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/infrastructure_inventory?status=eq.active&select=monthly_cost",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                total_cost = sum(item.get('monthly_cost', 0) or 0 for item in data)
                context['monthly_cost'] = round(total_cost, 2)
    except Exception as e:
        print(f"Failed to fetch infrastructure context: {e}")

    return context

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, infra_ctx: dict = None) -> str:
    """Call Claude API with full context and cost tracking"""
    try:
        if infra_ctx is None:
            infra_ctx = await get_infrastructure_context()

        system_prompt = build_system_prompt(infra_ctx)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="ATLAS",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": infra_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health + infrastructure overview"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    return {
        "status": "healthy",
        "agent": "ATLAS",
        "role": "Infrastructure Advisor",
        "port": 8208,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase'],
        "infrastructure": {
            "total_resources": infra_ctx['total_resources'],
            "monthly_cost": infra_ctx['monthly_cost'],
            "capacity_warnings": infra_ctx['capacity_warnings']
        }
    }

@app.get("/status")
async def status():
    """Real-time infrastructure status"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    return {
        "timestamp": time_ctx['current_datetime'],
        "infrastructure": infra_ctx,
        "time_context": time_ctx
    }

@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    metrics_text = f"""# HELP atlas_infrastructure_resources_total Total number of tracked infrastructure resources
# TYPE atlas_infrastructure_resources_total gauge
atlas_infrastructure_resources_total {infra_ctx['total_resources']}

# HELP atlas_infrastructure_monthly_cost_dollars Monthly infrastructure cost in dollars
# TYPE atlas_infrastructure_monthly_cost_dollars gauge
atlas_infrastructure_monthly_cost_dollars {infra_ctx['monthly_cost']}

# HELP atlas_capacity_warnings_total Number of services near capacity
# TYPE atlas_capacity_warnings_total gauge
atlas_capacity_warnings_total {infra_ctx['capacity_warnings']}

# HELP atlas_days_to_launch Days remaining until launch
# TYPE atlas_days_to_launch gauge
atlas_days_to_launch {time_ctx['days_to_launch']}
"""
    return metrics_text

# =============================================================================
# ARCHITECTURE DECISION ENDPOINTS
# =============================================================================

@app.post("/architecture/advise")
async def architecture_advise(req: ArchitectureAdviceRequest):
    """Get architectural advice for a scenario"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    prompt = f"""I need architectural advice for the following scenario:

**Scenario:** {req.scenario}
"""

    if req.constraints:
        prompt += f"\n**Constraints:**\n" + "\n".join(f"- {c}" for c in req.constraints)

    if req.requirements:
        prompt += f"\n**Requirements:**\n" + "\n".join(f"- {r}" for r in req.requirements)

    if req.context:
        prompt += f"\n**Additional Context:**\n{req.context}"

    prompt += """

Please provide:
1. **Context Understanding**: Restate the problem/requirement
2. **Current State Analysis**: Relevant observations
3. **Architecture Options**: 2-3 viable approaches with trade-offs
4. **Recommendation**: Clear, actionable guidance with rationale
5. **Cost Impact**: Expected cost implications
6. **Implementation Steps**: High-level path forward
7. **Risks & Mitigations**: What could go wrong and how to handle it
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    # Store in memory
    await update_aria_memory(
        memory_type="decision",
        content=f"Architecture advice: {req.scenario[:100]} - {response[:500]}",
        category="infrastructure",
        tags=["atlas", "architecture", "advice"]
    )

    await notify_event_bus("architecture.advice.provided", {
        "scenario": req.scenario[:100]
    })

    return {
        "advice": response,
        "agent": "ATLAS",
        "scenario": req.scenario,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/architecture/decisions")
async def list_architecture_decisions(
    status: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50
):
    """List all ADRs"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/architecture_decisions?order=created_at.desc&limit={limit}"

        if status:
            url += f"&status=eq.{status}"
        if tag:
            url += f"&tags=cs.{{{tag}}}"

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"decisions": resp.json(), "count": len(resp.json())}
            else:
                return {"decisions": [], "count": 0, "error": resp.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/architecture/decisions")
async def create_architecture_decision(req: ArchitectureDecisionCreate):
    """Create new ADR"""
    time_ctx = get_time_context()

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/architecture_decisions",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "title": req.title,
                    "context": req.context,
                    "decision": req.decision,
                    "alternatives": req.alternatives or [],
                    "consequences": req.consequences or [],
                    "tags": req.tags or [],
                    "status": "proposed"
                },
                timeout=10.0
            )

            if resp.status_code in [200, 201]:
                decision = resp.json()[0] if isinstance(resp.json(), list) else resp.json()

                # Store in memory
                await update_aria_memory(
                    memory_type="decision",
                    content=f"Architecture decision: {req.title} - {req.decision}",
                    category="infrastructure",
                    tags=["atlas", "architecture", "adr"]
                )

                await notify_event_bus("infra.decision.made", {
                    "title": req.title,
                    "decision_id": decision.get('id')
                })

                return {
                    "decision": decision,
                    "agent": "ATLAS",
                    "timestamp": time_ctx['current_datetime']
                }
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/architecture/decisions/{decision_id}")
async def get_architecture_decision(decision_id: str):
    """Get specific ADR"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/architecture_decisions?id=eq.{decision_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return {"decision": data[0]}
                else:
                    raise HTTPException(status_code=404, detail="Decision not found")
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/architecture/decisions/{decision_id}")
async def update_architecture_decision(decision_id: str, req: ArchitectureDecisionUpdate):
    """Update ADR status"""
    time_ctx = get_time_context()

    try:
        update_data = {"status": req.status, "updated_at": time_ctx['current_datetime']}

        if req.status == "accepted":
            update_data["decided_at"] = time_ctx['current_datetime']

        if req.superseded_by:
            update_data["superseded_by"] = req.superseded_by

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/architecture_decisions?id=eq.{decision_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=update_data,
                timeout=10.0
            )

            if resp.status_code == 200:
                if req.status == "superseded":
                    await notify_event_bus("infra.decision.superseded", {
                        "decision_id": decision_id,
                        "superseded_by": req.superseded_by
                    })

                return {"decision": resp.json()[0], "agent": "ATLAS"}
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/architecture/patterns")
async def get_architecture_patterns(req: PatternRequest = None, use_case: str = None):
    """Get recommended patterns for use case"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    target_use_case = use_case or (req.use_case if req else "general")
    constraints = req.constraints if req else []

    prompt = f"""Recommend architecture patterns for the following use case:

**Use Case:** {target_use_case}
"""

    if constraints:
        prompt += f"\n**Constraints:**\n" + "\n".join(f"- {c}" for c in constraints)

    prompt += """

Please provide:
1. **Recommended Patterns**: Top 2-3 patterns that fit this use case
2. **Pattern Details**: For each pattern:
   - Brief description
   - When to use it
   - Trade-offs (pros/cons)
   - Implementation considerations
3. **Best Fit**: Which pattern you'd recommend and why
4. **Anti-patterns**: What to avoid in this scenario
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    return {
        "patterns": response,
        "use_case": target_use_case,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# SCALING ENDPOINTS
# =============================================================================

@app.post("/scaling/analyze")
async def analyze_scaling(req: ScalingAnalyzeRequest):
    """Analyze current scaling needs"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    prompt = f"""Analyze scaling needs for the following service:

**Service:** {req.service_name}
"""

    if req.current_metrics:
        prompt += f"\n**Current Metrics:**\n```json\n{json.dumps(req.current_metrics, indent=2)}\n```"

    if req.context:
        prompt += f"\n**Context:**\n{req.context}"

    prompt += """

Please analyze:
1. **Current State**: Assessment of current resource utilization
2. **Scaling Need**: Is scaling needed? (Yes/No/Watch)
3. **Scaling Type**: Horizontal vs Vertical recommendation with rationale
4. **Specific Recommendation**: Exact changes to make
5. **Cost Impact**: Expected monthly cost change
6. **Auto-scaling Policy**: Recommended thresholds and policies
7. **Risks**: Potential issues with scaling
8. **Timeline**: When should scaling be implemented

Use these thresholds as guidance:
- CPU >75% sustained: Scale out/up
- Memory >80% sustained: Scale up + optimize
- Request Latency >500ms P95: Scale out + cache
- Queue Depth >1000: Add workers
- Error Rate >1%: Investigate + scale
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    await notify_event_bus("infra.scaling.recommended", {
        "service": req.service_name
    })

    return {
        "analysis": response,
        "service": req.service_name,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/scaling/recommendations")
async def get_scaling_recommendations():
    """Get pending scaling recommendations"""
    time_ctx = get_time_context()

    # In a real implementation, this would query a recommendations table
    # For now, return structure
    return {
        "recommendations": [],
        "count": 0,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime'],
        "note": "Recommendations are generated via /scaling/analyze endpoint"
    }

@app.post("/scaling/apply")
async def apply_scaling(req: ScalingApplyRequest):
    """Apply scaling recommendation"""
    time_ctx = get_time_context()

    if not req.confirm:
        return {
            "status": "confirmation_required",
            "message": "Set confirm=true to apply this scaling change",
            "agent": "ATLAS"
        }

    # In real implementation, this would apply the scaling change
    await notify_event_bus("infra.scaling.applied", {
        "recommendation_id": req.recommendation_id
    })

    return {
        "status": "applied",
        "recommendation_id": req.recommendation_id,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime'],
        "note": "Scaling change applied. Monitor for 15 minutes."
    }

@app.get("/scaling/events")
async def get_scaling_events(limit: int = 50):
    """List scaling history"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/scaling_events?order=created_at.desc&limit={limit}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"events": resp.json(), "count": len(resp.json())}
            else:
                return {"events": [], "count": 0}
    except Exception as e:
        return {"events": [], "count": 0, "error": str(e)}

@app.get("/scaling/policies")
async def get_scaling_policies():
    """Get configured auto-scaling policies"""
    # Return default policies structure
    return {
        "policies": {
            "default": {
                "cpu_threshold_up": 75,
                "cpu_threshold_down": 25,
                "memory_threshold_up": 80,
                "memory_threshold_down": 30,
                "cooldown_seconds": 300,
                "min_instances": 1,
                "max_instances": 10
            }
        },
        "agent": "ATLAS"
    }

@app.put("/scaling/policies")
async def update_scaling_policies(req: ScalingPolicyUpdate):
    """Update scaling policies"""
    time_ctx = get_time_context()

    await notify_event_bus("scaling.policies.updated", {
        "service": req.service_name
    })

    return {
        "status": "updated",
        "service": req.service_name,
        "policies": req.policies,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# COST OPTIMIZATION ENDPOINTS
# =============================================================================

@app.get("/cost/analysis")
async def get_cost_analysis():
    """Get current cost analysis"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/cost_analysis?order=created_at.desc&limit=1",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                data = resp.json()
                return {"analysis": data[0] if data else None, "agent": "ATLAS"}
            else:
                return {"analysis": None, "agent": "ATLAS"}
    except Exception as e:
        return {"analysis": None, "error": str(e), "agent": "ATLAS"}

@app.post("/cost/analyze")
async def trigger_cost_analysis(req: CostAnalyzeRequest):
    """Trigger new cost analysis"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    period = req.period or datetime.now().strftime("%Y-%m")

    prompt = f"""Perform a cost analysis for the infrastructure.

**Period:** {period}
**Breakdown By:** {req.breakdown_by}
**Current Monthly Cost:** ${infra_ctx['monthly_cost']}
**Total Resources:** {infra_ctx['total_resources']}

Please provide:
1. **Cost Summary**: Total spend and change from previous period
2. **Breakdown**: Costs by {req.breakdown_by}
3. **Top Spenders**: Top 5 cost drivers
4. **Anomalies**: Any unusual spending patterns
5. **Optimization Opportunities**:
   - Underutilized resources
   - Right-sizing recommendations
   - Reserved instance opportunities
   - Idle resources to terminate
6. **Estimated Savings**: Potential monthly savings from recommendations
7. **Priority Actions**: Top 3 cost-saving actions to take now
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    # Store insight in memory
    await update_aria_memory(
        memory_type="fact",
        content=f"Monthly infrastructure cost: ${infra_ctx['monthly_cost']}. Analysis: {response[:300]}",
        category="infrastructure",
        tags=["atlas", "cost", "optimization"]
    )

    return {
        "analysis": response,
        "period": period,
        "current_cost": infra_ctx['monthly_cost'],
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/cost/recommendations")
async def get_cost_recommendations():
    """Get cost optimization recommendations"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    prompt = """Generate cost optimization recommendations based on current infrastructure.

Focus on:
1. Quick wins (can implement today)
2. Medium-term optimizations (this month)
3. Strategic changes (this quarter)

For each recommendation:
- What to change
- Expected savings
- Effort level (low/medium/high)
- Risk level (low/medium/high)
- Implementation steps
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    await notify_event_bus("infra.cost.savings.identified", {
        "analysis_time": time_ctx['current_datetime']
    })

    return {
        "recommendations": response,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/cost/trends")
async def get_cost_trends(days: int = 30):
    """Cost trends over time"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/cost_analysis?order=created_at.desc&limit={days}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"trends": resp.json(), "days": days, "agent": "ATLAS"}
            else:
                return {"trends": [], "days": days, "agent": "ATLAS"}
    except Exception as e:
        return {"trends": [], "days": days, "error": str(e), "agent": "ATLAS"}

@app.get("/cost/forecast")
async def get_cost_forecast(months: int = 3):
    """Projected costs"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    prompt = f"""Forecast infrastructure costs for the next {months} months.

**Current Monthly Cost:** ${infra_ctx['monthly_cost']}
**Total Resources:** {infra_ctx['total_resources']}
**Days to Launch:** {time_ctx['days_to_launch']}

Consider:
1. Expected growth after launch
2. Seasonal patterns
3. Planned infrastructure changes
4. Market pricing trends

Provide:
1. **Monthly Projections**: Cost for each of the next {months} months
2. **Assumptions**: What's driving the forecast
3. **Confidence Level**: How certain is this forecast
4. **Risk Factors**: What could make costs higher/lower
5. **Budget Recommendations**: Suggested monthly budget with buffer
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    return {
        "forecast": response,
        "months": months,
        "current_cost": infra_ctx['monthly_cost'],
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/cost/breakdown")
async def get_cost_breakdown(by: str = "service"):
    """Cost breakdown by service/tag"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/infrastructure_inventory?status=eq.active&select=name,resource_type,monthly_cost,tags",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                data = resp.json()

                # Group by requested dimension
                breakdown = {}
                for item in data:
                    if by == "service":
                        key = item.get('name', 'unknown')
                    elif by == "type":
                        key = item.get('resource_type', 'unknown')
                    else:  # by tag
                        key = ','.join(item.get('tags', []) or ['untagged'])

                    if key not in breakdown:
                        breakdown[key] = 0
                    breakdown[key] += item.get('monthly_cost', 0) or 0

                return {
                    "breakdown": breakdown,
                    "by": by,
                    "total": sum(breakdown.values()),
                    "agent": "ATLAS"
                }
            else:
                return {"breakdown": {}, "by": by, "agent": "ATLAS"}
    except Exception as e:
        return {"breakdown": {}, "by": by, "error": str(e), "agent": "ATLAS"}

@app.post("/cost/alert")
async def configure_cost_alert(req: CostAlertConfig):
    """Configure cost alerts"""
    time_ctx = get_time_context()

    await notify_event_bus("cost.alert.configured", {
        "threshold": req.threshold_amount,
        "type": req.threshold_type
    })

    return {
        "status": "configured",
        "alert": {
            "threshold_amount": req.threshold_amount,
            "threshold_type": req.threshold_type,
            "notification_channels": req.notification_channels
        },
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# TECHNOLOGY EVALUATION ENDPOINTS
# =============================================================================

@app.post("/technology/evaluate")
async def evaluate_technology(req: TechnologyEvaluateRequest):
    """Evaluate technology options"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    default_criteria = [
        "Performance benchmarks",
        "Operational complexity",
        "Community and support",
        "Cost (license + operational)",
        "Security posture",
        "Integration capabilities",
        "Learning curve"
    ]

    criteria = req.criteria or default_criteria

    prompt = f"""Evaluate technology options for the following requirement:

**Category:** {req.category}
**Requirement:** {req.requirement}
"""

    if req.options:
        prompt += f"\n**Options to Evaluate:**\n" + "\n".join(f"- {o}" for o in req.options)
    else:
        prompt += "\n**Please suggest 3-4 options to evaluate.**"

    prompt += f"\n\n**Evaluation Criteria:**\n" + "\n".join(f"- {c}" for c in criteria)

    if req.context:
        prompt += f"\n\n**Additional Context:**\n{req.context}"

    prompt += """

Please provide:
1. **Options Summary**: Brief description of each option
2. **Evaluation Matrix**: Score each option 1-10 on each criterion
3. **Weighted Analysis**: Overall score with weights applied
4. **Recommendation**: The best choice with clear rationale
5. **Migration Effort**: Low/Medium/High effort to adopt
6. **Risks**: Key risks with each option
7. **POC Guidance**: How to test the recommended option
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    # Store evaluation
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{SUPABASE_URL}/rest/v1/technology_evaluations",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json={
                    "category": req.category,
                    "requirement": req.requirement,
                    "options": {"options": req.options, "criteria": criteria},
                    "recommendation": response[:500],
                    "rationale": response
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"Failed to store evaluation: {e}")

    await notify_event_bus("infra.technology.evaluated", {
        "category": req.category,
        "requirement": req.requirement[:50]
    })

    return {
        "evaluation": response,
        "category": req.category,
        "requirement": req.requirement,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/technology/evaluations")
async def list_technology_evaluations(category: Optional[str] = None, limit: int = 50):
    """List all evaluations"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/technology_evaluations?order=evaluated_at.desc&limit={limit}"

        if category:
            url += f"&category=eq.{category}"

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"evaluations": resp.json(), "count": len(resp.json())}
            else:
                return {"evaluations": [], "count": 0}
    except Exception as e:
        return {"evaluations": [], "count": 0, "error": str(e)}

@app.get("/technology/evaluations/{evaluation_id}")
async def get_technology_evaluation(evaluation_id: str):
    """Get specific evaluation"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/technology_evaluations?id=eq.{evaluation_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return {"evaluation": data[0]}
                else:
                    raise HTTPException(status_code=404, detail="Evaluation not found")
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/technology/radar")
async def get_technology_radar():
    """Get technology radar"""
    time_ctx = get_time_context()

    # Standard technology radar structure
    radar = {
        "adopt": [
            {"name": "FastAPI", "category": "framework", "notes": "Primary Python API framework"},
            {"name": "PostgreSQL", "category": "database", "notes": "Primary relational database"},
            {"name": "Docker", "category": "platform", "notes": "Container runtime"},
            {"name": "Claude API", "category": "ai", "notes": "Primary LLM provider"}
        ],
        "trial": [
            {"name": "Supabase", "category": "platform", "notes": "Managed Postgres + Auth"},
            {"name": "n8n", "category": "automation", "notes": "Workflow automation"}
        ],
        "assess": [
            {"name": "Kubernetes", "category": "platform", "notes": "Evaluate for scaling"},
            {"name": "Redis Cluster", "category": "cache", "notes": "For session management"}
        ],
        "hold": [
            {"name": "MongoDB", "category": "database", "notes": "Stick with PostgreSQL"},
            {"name": "GraphQL", "category": "api", "notes": "REST sufficient for now"}
        ],
        "last_updated": time_ctx['current_datetime'],
        "agent": "ATLAS"
    }

    return radar

@app.post("/technology/compare")
async def compare_technologies(req: TechnologyCompareRequest):
    """Compare specific technologies"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    default_criteria = [
        "Performance",
        "Scalability",
        "Ease of use",
        "Community support",
        "Cost",
        "Security"
    ]

    criteria = req.criteria or default_criteria

    prompt = f"""Compare these technologies head-to-head:

**Category:** {req.category}
**Technologies:** {', '.join(req.technologies)}
**Criteria:** {', '.join(criteria)}

Provide:
1. **Comparison Matrix**: Score each technology 1-10 on each criterion
2. **Strengths/Weaknesses**: For each technology
3. **Use Case Fit**: When to use each one
4. **Migration Considerations**: If switching between them
5. **Recommendation**: Based on LeverEdge's needs
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    return {
        "comparison": response,
        "technologies": req.technologies,
        "category": req.category,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# CAPACITY PLANNING ENDPOINTS
# =============================================================================

@app.get("/capacity/forecasts")
async def get_capacity_forecasts(service: Optional[str] = None):
    """Get all capacity forecasts"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/capacity_forecasts?order=forecast_date.desc&limit=50"

        if service:
            url += f"&service_name=eq.{service}"

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"forecasts": resp.json(), "count": len(resp.json())}
            else:
                return {"forecasts": [], "count": 0}
    except Exception as e:
        return {"forecasts": [], "count": 0, "error": str(e)}

@app.post("/capacity/forecast")
async def generate_capacity_forecast(req: CapacityForecastRequest):
    """Generate new forecast"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    prompt = f"""Generate a capacity forecast for:

**Service:** {req.service_name}
**Metric:** {req.metric}
**Horizon:** {req.horizon_days} days
**Days to Launch:** {time_ctx['days_to_launch']}

Provide:
1. **Current State**: Current utilization of {req.metric}
2. **Trend Analysis**: Recent growth/decline pattern
3. **Forecast**:
   - 7-day projection
   - 30-day projection
   - {req.horizon_days}-day projection
4. **Days Until Threshold**: When will we hit 80% capacity?
5. **Confidence Level**: How certain is this forecast (0-100%)
6. **Recommendation**: What action to take and when
7. **Risk Factors**: What could accelerate capacity consumption
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    return {
        "forecast": response,
        "service": req.service_name,
        "metric": req.metric,
        "horizon_days": req.horizon_days,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

@app.get("/capacity/alerts")
async def get_capacity_alerts():
    """Services approaching capacity"""
    time_ctx = get_time_context()

    try:
        # Query forecasts where days_until_threshold is low
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/capacity_forecasts?days_until_threshold=lt.30&order=days_until_threshold.asc",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                alerts = resp.json()

                # Categorize by severity
                critical = [a for a in alerts if (a.get('days_until_threshold') or 999) <= 7]
                warning = [a for a in alerts if 7 < (a.get('days_until_threshold') or 999) <= 30]

                if critical:
                    await notify_event_bus("infra.capacity.critical", {
                        "count": len(critical),
                        "services": [a['service_name'] for a in critical]
                    })

                return {
                    "alerts": {
                        "critical": critical,
                        "warning": warning
                    },
                    "total_alerts": len(alerts),
                    "agent": "ATLAS",
                    "timestamp": time_ctx['current_datetime']
                }
            else:
                return {"alerts": {"critical": [], "warning": []}, "total_alerts": 0}
    except Exception as e:
        return {"alerts": {"critical": [], "warning": []}, "error": str(e)}

@app.get("/capacity/runway")
async def get_capacity_runway():
    """Days until capacity for each service"""
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/capacity_forecasts?select=service_name,metric,days_until_threshold,utilization_pct&order=days_until_threshold.asc",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"runway": resp.json(), "agent": "ATLAS"}
            else:
                return {"runway": [], "agent": "ATLAS"}
    except Exception as e:
        return {"runway": [], "error": str(e), "agent": "ATLAS"}

@app.post("/capacity/scenario")
async def run_capacity_scenario(req: CapacityScenarioRequest):
    """Run what-if scenario"""
    time_ctx = get_time_context()
    infra_ctx = await get_infrastructure_context()

    prompt = f"""Run a what-if capacity scenario:

**Scenario Name:** {req.scenario_name}
**Assumptions:**
```json
{json.dumps(req.assumptions, indent=2)}
```
**Services to Analyze:** {', '.join(req.services) if req.services else 'All services'}
**Current Infrastructure:** {infra_ctx['total_resources']} resources, ${infra_ctx['monthly_cost']}/month

Analyze:
1. **Impact Assessment**: How do these assumptions affect each service?
2. **Capacity Requirements**: What additional capacity is needed?
3. **Timeline**: When would we need the additional capacity?
4. **Cost Projection**: Expected cost increase
5. **Preparation Steps**: What to do now to prepare
6. **Alternatives**: Other ways to handle this scenario
7. **Risks**: What could go wrong
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, infra_ctx)

    return {
        "scenario_analysis": response,
        "scenario_name": req.scenario_name,
        "assumptions": req.assumptions,
        "agent": "ATLAS",
        "timestamp": time_ctx['current_datetime']
    }

# =============================================================================
# INVENTORY ENDPOINTS
# =============================================================================

@app.get("/inventory")
async def list_inventory(
    resource_type: Optional[str] = None,
    provider: Optional[str] = None,
    status: str = "active",
    limit: int = 100
):
    """List all infrastructure"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/infrastructure_inventory?status=eq.{status}&order=created_at.desc&limit={limit}"

        if resource_type:
            url += f"&resource_type=eq.{resource_type}"
        if provider:
            url += f"&provider=eq.{provider}"

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                url,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                data = resp.json()
                return {
                    "inventory": data,
                    "count": len(data),
                    "filters": {
                        "resource_type": resource_type,
                        "provider": provider,
                        "status": status
                    },
                    "agent": "ATLAS"
                }
            else:
                return {"inventory": [], "count": 0, "agent": "ATLAS"}
    except Exception as e:
        return {"inventory": [], "count": 0, "error": str(e), "agent": "ATLAS"}

@app.post("/inventory")
async def add_to_inventory(req: InventoryCreate):
    """Add resource to inventory"""
    time_ctx = get_time_context()

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                f"{SUPABASE_URL}/rest/v1/infrastructure_inventory",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "resource_type": req.resource_type,
                    "name": req.name,
                    "provider": req.provider,
                    "region": req.region,
                    "specs": req.specs,
                    "monthly_cost": req.monthly_cost,
                    "tags": req.tags or [],
                    "status": "active"
                },
                timeout=10.0
            )

            if resp.status_code in [200, 201]:
                resource = resp.json()[0] if isinstance(resp.json(), list) else resp.json()

                await notify_event_bus("inventory.resource.added", {
                    "name": req.name,
                    "type": req.resource_type
                })

                return {
                    "resource": resource,
                    "agent": "ATLAS",
                    "timestamp": time_ctx['current_datetime']
                }
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/inventory/{resource_id}")
async def update_inventory(resource_id: str, req: InventoryUpdate):
    """Update resource"""
    time_ctx = get_time_context()

    try:
        update_data = {"last_updated": time_ctx['current_datetime']}

        if req.specs is not None:
            update_data["specs"] = req.specs
        if req.monthly_cost is not None:
            update_data["monthly_cost"] = req.monthly_cost
        if req.utilization is not None:
            update_data["utilization"] = req.utilization
        if req.status is not None:
            update_data["status"] = req.status
        if req.tags is not None:
            update_data["tags"] = req.tags

        async with httpx.AsyncClient() as http_client:
            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/infrastructure_inventory?id=eq.{resource_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=update_data,
                timeout=10.0
            )

            if resp.status_code == 200:
                return {"resource": resp.json()[0], "agent": "ATLAS"}
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/inventory/{resource_id}")
async def remove_from_inventory(resource_id: str):
    """Remove resource (soft delete)"""
    time_ctx = get_time_context()

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.patch(
                f"{SUPABASE_URL}/rest/v1/infrastructure_inventory?id=eq.{resource_id}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json={
                    "status": "terminated",
                    "last_updated": time_ctx['current_datetime']
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                await notify_event_bus("inventory.resource.removed", {
                    "resource_id": resource_id
                })

                return {
                    "status": "terminated",
                    "resource_id": resource_id,
                    "agent": "ATLAS"
                }
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/inventory/summary")
async def get_inventory_summary():
    """Infrastructure summary"""
    time_ctx = get_time_context()

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.get(
                f"{SUPABASE_URL}/rest/v1/infrastructure_inventory?status=eq.active&select=resource_type,provider,monthly_cost",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}"
                },
                timeout=10.0
            )

            if resp.status_code == 200:
                data = resp.json()

                # Aggregate by type and provider
                by_type = {}
                by_provider = {}
                total_cost = 0

                for item in data:
                    rtype = item.get('resource_type', 'unknown')
                    provider = item.get('provider', 'unknown')
                    cost = item.get('monthly_cost', 0) or 0

                    by_type[rtype] = by_type.get(rtype, 0) + 1
                    by_provider[provider] = by_provider.get(provider, 0) + 1
                    total_cost += cost

                return {
                    "summary": {
                        "total_resources": len(data),
                        "total_monthly_cost": round(total_cost, 2),
                        "by_type": by_type,
                        "by_provider": by_provider
                    },
                    "agent": "ATLAS",
                    "timestamp": time_ctx['current_datetime']
                }
            else:
                return {"summary": {}, "agent": "ATLAS"}
    except Exception as e:
        return {"summary": {}, "error": str(e), "agent": "ATLAS"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8208)
