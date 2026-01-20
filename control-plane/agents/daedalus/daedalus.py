#!/usr/bin/env python3
"""
DAEDALUS - Architect of the Labyrinth
Port: 8026
Domain: THE KEEP

Infrastructure strategist for LeverEdge. Researches, advises, and plans all
infrastructure decisions - from hosting choices to scaling patterns to
client isolation strategies.

"Builder of systems that scale"
"""

import os
import sys
import json
import httpx
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
try:
    from cost_tracker import CostTracker, log_llm_usage
except ImportError:
    # Fallback if cost_tracker not available
    class CostTracker:
        def __init__(self, name): pass
        def log(self, *args, **kwargs): pass
    def log_llm_usage(*args, **kwargs): pass

app = FastAPI(
    title="DAEDALUS",
    description="Architect of the Labyrinth - Infrastructure Strategy Agent",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# CONFIGURATION
# =============================================================================

AGENT_NAME = "DAEDALUS"
AGENT_PORT = 8026
AGENT_DOMAIN = "THE_KEEP"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "SCHOLAR": "http://scholar:8018",
    "CHIRON": "http://chiron:8017",
    "AEGIS": "http://aegis:8012",
    "CHRONOS": "http://chronos:8010",
    "PANOPTES": "http://panoptes:8023",
    "ARGUS": "http://argus:8016",
    "ALOY": "http://aloy:8015",
    "EVENT_BUS": EVENT_BUS_URL
}

# Initialize Anthropic client
client = None
if ANTHROPIC_API_KEY:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Initialize cost tracker
cost_tracker = CostTracker(AGENT_NAME)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AnalyzeRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None

class VendorEvaluationRequest(BaseModel):
    vendor: str
    use_case: str
    requirements: Optional[List[str]] = None

class CostOptimizeRequest(BaseModel):
    current_infra: Dict[str, Any]
    monthly_spend: float
    constraints: Optional[List[str]] = None

class ScalePlanRequest(BaseModel):
    current_load: Dict[str, Any]
    growth_rate: str
    budget_constraint: Optional[float] = None

class ClientArchitectureRequest(BaseModel):
    client_tier: int
    requirements: List[str]
    compliance: Optional[List[str]] = None
    budget_max: Optional[float] = None


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are DAEDALUS - Architect of the Labyrinth, the infrastructure strategist for LeverEdge AI.

## YOUR IDENTITY
- Name: DAEDALUS
- Title: Architect of the Labyrinth
- Tagline: "Builder of systems that scale"
- Domain: THE KEEP (Infrastructure)

## YOUR MISSION
Research, advise, and plan all infrastructure decisions:
- Hosting choices (VPS, cloud, hybrid)
- Scaling patterns
- Client isolation strategies
- Cost optimization
- Compliance readiness

## KEY PRINCIPLE
Build for today's needs with tomorrow's growth in mind. Never overbuild, never underprepare.

## CURRENT LEVEREGE INFRASTRUCTURE
- Primary: Contabo VPS (single server, ~$15/mo)
- Database: Supabase (DEV + PROD)
- CDN/Proxy: Cloudflare + Caddy
- Containers: Docker Compose
- MRR Target: $30K/month by Q2 2026

## EXPERTISE AREAS

### Cloud Platforms (Expert)
- Hetzner, Contabo, Cloudflare (cost-effective)
- AWS, GCP, Azure (enterprise)
- DigitalOcean, Vultr (mid-tier)

### Technologies
- Docker/Kubernetes, Terraform/IaC
- Load balancers, CDN/Edge
- Database scaling, Redis caching
- Message queues, monitoring

### Architecture Patterns
- Multi-tenant SaaS (expert)
- Microservices, Event-driven
- Serverless, Edge computing

### Compliance
- SOC 2 (advanced), GDPR (advanced)
- HIPAA (intermediate), PCI-DSS (intermediate)

## DECISION FRAMEWORKS

### When to Scale Up vs Out
- CPU bound → Scale up or optimize
- Memory bound → Scale up or add caching
- I/O bound → Better storage or database optimization
- Network bound → CDN, edge, or horizontal scale
- All of above → Time to go horizontal/multi-server

### Multi-Tenant vs Single-Tenant
- < $5K/mo contract → Multi-tenant (shared infrastructure)
- $5K-15K/mo → Multi-tenant with dedicated database
- $15K-50K/mo → Single-tenant optional (premium offering)
- > $50K/mo → Single-tenant recommended
- HIPAA → Single-tenant strongly recommended
- PCI-DSS → Single-tenant required

### Cloud Provider Selection
- Cost priority → Hetzner, Contabo, Vultr
- Enterprise clients → AWS, Azure, GCP
- Edge/CDN needs → Cloudflare
- Compliance heavy → AWS GovCloud, Azure Government
- Simplicity → DigitalOcean, Render

### When to Migrate Triggers
- Costs > 10% of revenue → Optimize or migrate
- Performance SLA missed 3x → Upgrade
- Client requires specific cloud → Migrate that client
- Compliance audit coming → Ensure readiness

## COMMUNICATION STYLE
- Be specific with numbers, costs, and timelines
- Provide clear recommendations with rationale
- Include risk assessments
- Offer alternatives when appropriate
- Ask clarifying questions if needed

## OUTPUT FORMAT
Always structure your responses with:
1. **Recommendation** - Clear, actionable advice
2. **Rationale** - Why this is the best choice
3. **Cost Impact** - Financial implications
4. **Risk Assessment** - What could go wrong
5. **Alternatives** - Other options considered
6. **Next Steps** - Concrete actions to take
"""


# =============================================================================
# EVENT BUS INTEGRATION
# =============================================================================

async def publish_event(event_type: str, data: Dict[str, Any]):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            await http.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event": event_type,
                    "source": AGENT_NAME.lower(),
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": data
                }
            )
    except Exception as e:
        print(f"Event bus publish failed: {e}")


# =============================================================================
# LLM HELPER
# =============================================================================

async def get_llm_response(prompt: str, context: str = "") -> str:
    """Get response from Claude"""
    if not client:
        return "LLM not available - ANTHROPIC_API_KEY not set"

    try:
        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": full_prompt}]
        )

        # Log usage
        log_llm_usage(
            agent=AGENT_NAME,
            model="claude-sonnet-4-20250514",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens
        )

        return response.content[0].text

    except Exception as e:
        return f"LLM error: {str(e)}"


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": AGENT_NAME,
        "title": "Architect of the Labyrinth",
        "port": AGENT_PORT,
        "domain": AGENT_DOMAIN,
        "llm_available": client is not None,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/info")
async def info():
    """Agent information"""
    return {
        "agent": AGENT_NAME,
        "title": "Architect of the Labyrinth",
        "tagline": "Builder of systems that scale",
        "domain": AGENT_DOMAIN,
        "port": AGENT_PORT,
        "version": "1.0.0",
        "capabilities": [
            "infrastructure_strategy",
            "cost_optimization",
            "vendor_evaluation",
            "client_architecture",
            "compliance_assessment",
            "scaling_plans"
        ],
        "endpoints": [
            "/analyze",
            "/evaluate-vendor",
            "/cost-optimize",
            "/scale-plan",
            "/client-architecture"
        ]
    }


@app.post("/analyze")
async def analyze(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    General infrastructure analysis and advice.

    Example: "Should I use AWS or Hetzner for a new client?"
    """
    context = ""
    if request.context:
        context = f"Additional context:\n{json.dumps(request.context, indent=2)}"

    response = await get_llm_response(request.question, context)

    # Publish event
    background_tasks.add_task(
        publish_event,
        "daedalus.analysis.completed",
        {"question_preview": request.question[:100], "has_response": True}
    )

    return {
        "agent": AGENT_NAME,
        "question": request.question,
        "response": response,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/evaluate-vendor")
async def evaluate_vendor(request: VendorEvaluationRequest, background_tasks: BackgroundTasks):
    """
    Evaluate a vendor for a specific use case.

    Example: vendor="AWS", use_case="compliance-heavy client"
    """
    prompt = f"""Evaluate {request.vendor} for the following use case:

USE CASE: {request.use_case}

{f"REQUIREMENTS: {', '.join(request.requirements)}" if request.requirements else ""}

Please provide:
1. Overall score (1-100)
2. Pros (at least 3)
3. Cons (at least 3)
4. Best-fit use cases
5. Alternative vendors to consider
6. Cost estimate range
"""

    response = await get_llm_response(prompt)

    background_tasks.add_task(
        publish_event,
        "daedalus.vendor.evaluated",
        {"vendor": request.vendor, "use_case": request.use_case}
    )

    return {
        "agent": AGENT_NAME,
        "vendor": request.vendor,
        "use_case": request.use_case,
        "evaluation": response,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/cost-optimize")
async def cost_optimize(request: CostOptimizeRequest, background_tasks: BackgroundTasks):
    """
    Analyze current infrastructure and recommend cost optimizations.
    """
    prompt = f"""Analyze the following infrastructure setup and recommend cost optimizations:

CURRENT INFRASTRUCTURE:
{json.dumps(request.current_infra, indent=2)}

MONTHLY SPEND: ${request.monthly_spend}

{f"CONSTRAINTS: {', '.join(request.constraints)}" if request.constraints else ""}

Please provide:
1. Quick wins (immediate savings)
2. Medium-term optimizations (1-3 months)
3. Strategic changes (3-6 months)
4. Estimated total savings potential
5. Risk assessment for each recommendation
"""

    response = await get_llm_response(prompt)

    background_tasks.add_task(
        publish_event,
        "daedalus.cost.optimized",
        {"monthly_spend": request.monthly_spend}
    )

    return {
        "agent": AGENT_NAME,
        "current_spend": request.monthly_spend,
        "recommendations": response,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/scale-plan")
async def scale_plan(request: ScalePlanRequest, background_tasks: BackgroundTasks):
    """
    Create a scaling plan based on current load and growth projections.
    """
    prompt = f"""Create a scaling plan based on:

CURRENT LOAD:
{json.dumps(request.current_load, indent=2)}

GROWTH RATE: {request.growth_rate}

{f"BUDGET CONSTRAINT: ${request.budget_constraint}/month max" if request.budget_constraint else ""}

Please provide:
1. Scaling timeline (when to scale)
2. Trigger points (specific metrics to watch)
3. Scaling steps (vertical vs horizontal)
4. Cost projection at each phase
5. Risk mitigation for each transition
6. Rollback plan if scaling fails
"""

    response = await get_llm_response(prompt)

    background_tasks.add_task(
        publish_event,
        "daedalus.scale.planned",
        {"growth_rate": request.growth_rate}
    )

    return {
        "agent": AGENT_NAME,
        "growth_rate": request.growth_rate,
        "scale_plan": response,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/client-architecture")
async def client_architecture(request: ClientArchitectureRequest, background_tasks: BackgroundTasks):
    """
    Recommend infrastructure setup for a new client.
    """
    prompt = f"""Recommend infrastructure setup for a new client:

CLIENT TIER: Tier {request.client_tier}
REQUIREMENTS: {', '.join(request.requirements)}
{f"COMPLIANCE: {', '.join(request.compliance)}" if request.compliance else "NO SPECIFIC COMPLIANCE"}
{f"MAX BUDGET: ${request.budget_max}/month" if request.budget_max else ""}

Please provide:
1. Recommended isolation level (shared/database_isolated/single_tenant)
2. Infrastructure setup (servers, databases, add-ons)
3. Estimated monthly cost
4. Setup timeline
5. Upsell opportunities (premium infrastructure)
6. Compliance considerations
"""

    response = await get_llm_response(prompt)

    background_tasks.add_task(
        publish_event,
        "daedalus.client.architecture",
        {"tier": request.client_tier, "compliance": request.compliance}
    )

    return {
        "agent": AGENT_NAME,
        "client_tier": request.client_tier,
        "architecture": response,
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
