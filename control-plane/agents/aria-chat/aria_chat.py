#!/usr/bin/env python3
"""
ARIA Chat Service V3.3 - Cross-Environment Aware

Full personality chat endpoint with dynamic context injection.
Now with cross-environment awareness - ARIA knows where she is and can query both environments.
Port: 8113
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ARIA-CHAT")

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")  # Upgraded from mini for better personality
PROMPTS_DIR = Path(__file__).parent / "prompts"

# Cross-Environment Configuration
ARIA_ENVIRONMENT = os.getenv("ARIA_ENVIRONMENT", "unknown")
CROSS_ENVIRONMENT = os.getenv("CROSS_ENVIRONMENT", "unknown")
PRIMARY_LCIS_URL = os.getenv("PRIMARY_LCIS_URL", "http://lcis-librarian:8050")
CROSS_LCIS_URL = os.getenv("CROSS_LCIS_URL", "http://lcis-librarian:8050")
PRIMARY_EVENT_BUS_URL = os.getenv("PRIMARY_EVENT_BUS_URL", "http://event-bus:8099")
CROSS_EVENT_BUS_URL = os.getenv("CROSS_EVENT_BUS_URL", "http://event-bus:8099")

# Agent health endpoints for each environment
AGENT_HEALTH_ENDPOINTS = {
    "dev": {
        "aria-chat": "http://aria-chat-dev:8113/health",
        "event-bus": "http://event-bus:8099/health",
        "lcis": "http://lcis-librarian:8050/health",
    },
    "prod": {
        "aria-chat": "http://aria-chat-prod:8113/health",
        "event-bus": "http://event-bus:8099/health",
        "lcis": "http://lcis-librarian:8050/health",
    }
}

# Load full system prompt from file
def load_system_prompt() -> str:
    """Load the comprehensive ARIA system prompt"""
    prompt_file = PROMPTS_DIR / "aria_system_prompt.txt"
    try:
        if prompt_file.exists():
            return prompt_file.read_text()
        else:
            logger.warning(f"System prompt file not found: {prompt_file}")
            return "You are ARIA, a helpful AI assistant."
    except Exception as e:
        logger.error(f"Error loading system prompt: {e}")
        return "You are ARIA, a helpful AI assistant."

# Cache the loaded prompt
ARIA_SYSTEM_PROMPT = load_system_prompt()

# Mode-specific behavioral modifiers (added to base prompt)
MODE_MODIFIERS = {
    "DEFAULT": """
## CURRENT MODE: DEFAULT
Be your warm, balanced self. Helpful, clear, efficient. This is your baseline personality.
""",
    "COACH": """
## CURRENT MODE: COACH
Switch to motivational, supportive mode. Celebrate progress. Encourage action. Build confidence.
- "You've got this!"
- "That's real progress - don't minimize it."
- Focus on what's working and build from there.
""",
    "HYPE": """
## CURRENT MODE: HYPE
MAXIMUM ENERGY! Celebrate EVERYTHING! Enthusiasm cranked to 11!
- Use exclamation marks freely!
- Emojis are welcome: 🔥💪🚀
- Get Damon PUMPED and ready to conquer!
- "YES! That's what I'm talking about!"
""",
    "COMFORT": """
## CURRENT MODE: COMFORT
Shift to calm, gentle, emotionally supportive mode. No pressure.
- "That sounds really hard. I hear you."
- Soft, nurturing tone
- Presence over solutions
- It's okay to just listen
""",
    "FOCUS": """
## CURRENT MODE: FOCUS
Direct. Concise. No fluff. Cut through the noise.
- Lead with the answer
- Bullet points over paragraphs
- "Here's what matters: X"
- Ruthless prioritization
""",
    "DRILL": """
## CURRENT MODE: DRILL
Tough love activated. Challenge hard. No excuses accepted.
- "Stop making excuses. What's the REAL blocker?"
- Push past comfort zone
- High standards, no coddling
- "You're better than this."
- Call out avoidance directly
""",
    "STRATEGY": """
## CURRENT MODE: STRATEGY
Analytical, methodical, long-term thinking mode.
- Consider trade-offs and second-order effects
- Systems thinking perspective
- "Let's think through the implications..."
- Connect to bigger picture goals
""",
}


# =============================================================================
# CROSS-ENVIRONMENT FUNCTIONS
# =============================================================================

async def get_environment_info() -> Dict[str, Any]:
    """Get information about current and cross environment"""
    return {
        "current_environment": ARIA_ENVIRONMENT,
        "cross_environment": CROSS_ENVIRONMENT,
        "message": f"I am ARIA running in {ARIA_ENVIRONMENT}. I can also access {CROSS_ENVIRONMENT}."
    }


async def query_lcis(query: str, environment: str = "current") -> Dict[str, Any]:
    """Query LCIS knowledge base in either environment via /recent endpoint with domain filter"""
    if environment == "current" or environment == ARIA_ENVIRONMENT:
        url = PRIMARY_LCIS_URL
        env_label = ARIA_ENVIRONMENT
    else:
        url = CROSS_LCIS_URL
        env_label = CROSS_ENVIRONMENT

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Get recent lessons, optionally filtered by domain
            params = {"limit": 10}
            if query.upper() in ["ARIA", "DEPLOYMENT", "INFRASTRUCTURE", "SECURITY", "AGENT"]:
                params["domain"] = query.upper()

            response = await client.get(f"{url}/recent", params=params)
            lessons = response.json()

            # If it's a general search, filter by content containing query
            if "domain" not in params and query:
                query_lower = query.lower()
                lessons = [l for l in lessons if query_lower in (l.get("content", "") or "").lower()]

            return {"environment": env_label, "results": lessons, "query": query}
    except Exception as e:
        logger.error(f"LCIS query error ({env_label}): {e}")
        return {"error": str(e), "environment": env_label}


async def check_environment_health(environment: str = "current") -> Dict[str, Any]:
    """Check health of agents in an environment"""
    env_key = ARIA_ENVIRONMENT if environment == "current" else environment
    if env_key not in AGENT_HEALTH_ENDPOINTS:
        env_key = CROSS_ENVIRONMENT

    endpoints = AGENT_HEALTH_ENDPOINTS.get(env_key, {})
    results = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent, url in endpoints.items():
            try:
                response = await client.get(url)
                results[agent] = {"status": "healthy" if response.status_code == 200 else "unhealthy"}
            except Exception as e:
                results[agent] = {"status": "unreachable", "error": str(e)}

    return {"environment": env_key, "agents": results}


def get_dynamic_context() -> str:
    """
    Fetch REAL dynamic context to inject into ARIA's prompt.
    This gives ARIA awareness of portfolio, launch countdown, and recent activity.
    """
    from datetime import date

    now = datetime.now()

    # Calculate days to launch
    launch_date = date(2026, 3, 1)
    days_to_launch = (launch_date - now.date()).days

    # Portfolio data - TODO: Query from Supabase when connected
    # These are the real current values as of Jan 18, 2026
    portfolio_min = 58000
    portfolio_max = 117000
    wins_count = 28

    # Recent major accomplishments (last 7 days)
    recent_wins = [
        "DAEDALUS spec created (Infrastructure Architect, port 8026)",
        "DEV/PROD isolation system deployed (no more accidental prod changes)",
        "Google Workspace configured (damon@leveredgeai.com ready)",
        "11 pipeline tables + CONSUL agent added",
        "ALCHEMY creative team (5 agents) deployed",
        "Control n8n fixed and operational",
        "ARIA V4 personality restored"
    ]

    # Agent fleet status
    agent_count = 35  # Approximate current count

    # Format recent wins
    wins_text = "\n".join([f"  - {win}" for win in recent_wins[:5]])

    context = f"""
## CURRENT CONTEXT (as of {now.strftime('%B %d, %Y %I:%M %p')} PST)

**🚀 LAUNCH COUNTDOWN: {days_to_launch} days to March 1, 2026**

**Portfolio Value:** ${portfolio_min:,} - ${portfolio_max:,} across {wins_count} documented wins

**Agent Fleet:** {agent_count}+ agents operational

**Current Phase:**
- NOW: Infrastructure hardening, ARIA restoration
- Feb 1-14: Outreach training + prep
- Feb 15-28: Cold outreach campaign (target: 10 attempts, 3 calls)
- March 1: IN BUSINESS

**Recent Wins (Last 7 Days):**
{wins_text}

**Active Priorities:**
1. Get ARIA fully operational with real personality
2. Finish Command Center agent pages
3. Prepare for February outreach module
"""
    return context


app = FastAPI(
    title="ARIA Chat Service V3.3",
    description="Elite AI executive assistant with full personality and cross-environment awareness",
    version="3.3.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dev.aria.leveredgeai.com",
        "https://aria.leveredgeai.com",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[Message]
    mode: str = "DEFAULT"
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    content: str
    mode: str
    model: str
    usage: Optional[dict] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
    cross_environment: str
    openai_configured: bool
    model: str
    prompt_loaded: bool


class EnvironmentResponse(BaseModel):
    current_environment: str
    cross_environment: str
    message: str


class LcisQueryResponse(BaseModel):
    environment: str
    results: Optional[Any] = None
    error: Optional[str] = None


class EnvironmentHealthResponse(BaseModel):
    environment: str
    agents: Dict[str, Any]


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check"""
    return HealthResponse(
        status="healthy",
        service="ARIA Chat V3.3",
        version="3.3.0",
        environment=ARIA_ENVIRONMENT,
        cross_environment=CROSS_ENVIRONMENT,
        openai_configured=bool(OPENAI_API_KEY),
        model=OPENAI_MODEL,
        prompt_loaded=len(ARIA_SYSTEM_PROMPT) > 100
    )


@app.get("/environment", response_model=EnvironmentResponse)
async def get_environment():
    """Get environment information - which ARIA this is"""
    info = await get_environment_info()
    return EnvironmentResponse(**info)


@app.get("/query/lcis", response_model=LcisQueryResponse)
async def api_query_lcis(q: str, env: str = "current"):
    """Query LCIS knowledge base in current or cross environment"""
    result = await query_lcis(q, env)
    return LcisQueryResponse(**result)


@app.get("/health/{environment}", response_model=EnvironmentHealthResponse)
async def api_environment_health(environment: str):
    """Check health of agents in specified environment"""
    result = await check_environment_health(environment)
    return EnvironmentHealthResponse(**result)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process chat message and return AI response with full ARIA personality"""

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")

    # Build comprehensive system prompt
    mode_modifier = MODE_MODIFIERS.get(request.mode, MODE_MODIFIERS["DEFAULT"])
    dynamic_context = get_dynamic_context()

    # Combine: Base personality + Mode modifier + Dynamic context
    full_system_prompt = f"{ARIA_SYSTEM_PROMPT}\n\n{mode_modifier}\n\n{dynamic_context}"

    # Build messages for OpenAI
    openai_messages = [
        {"role": "system", "content": full_system_prompt}
    ]

    # Add conversation history (last 20 messages max)
    for msg in request.messages[-20:]:
        openai_messages.append({
            "role": msg.role,
            "content": msg.content
        })

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": openai_messages,
                    "temperature": 0.8,  # Slightly higher for more personality
                    "max_tokens": 1500,  # More room for rich responses
                },
                timeout=60.0
            )

            if response.status_code != 200:
                logger.error(f"OpenAI error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=502, detail="AI service error")

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage")

            logger.info(f"ARIA V3.2 response: mode={request.mode}, model={OPENAI_MODEL}, tokens={usage}")

            return ChatResponse(
                content=content,
                mode=request.mode,
                model=OPENAI_MODEL,
                usage=usage
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI service timeout")
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reload-prompt")
async def reload_prompt():
    """Reload the system prompt from file (for hot updates)"""
    global ARIA_SYSTEM_PROMPT
    ARIA_SYSTEM_PROMPT = load_system_prompt()
    return {"status": "reloaded", "prompt_length": len(ARIA_SYSTEM_PROMPT)}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8113"))
    logger.info(f"Starting ARIA Chat V3.2 on port {port}")
    logger.info(f"Model: {OPENAI_MODEL}")
    logger.info(f"System prompt loaded: {len(ARIA_SYSTEM_PROMPT)} chars")

    uvicorn.run(
        "aria_chat:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )
