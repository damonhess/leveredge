"""
LeverEdge Agent Template
Copy this to create new agents.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
import os

# Configuration
AGENT_NAME = "TEMPLATE"
AGENT_PORT = 8XXX
AGENT_DESCRIPTION = "Template agent description"
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54322")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
EVENT_BUS_URL = "http://localhost:8099"
HERMES_URL = "http://localhost:8014"

# App
app = FastAPI(
    title=f"LeverEdge {AGENT_NAME}",
    description=AGENT_DESCRIPTION,
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class HealthResponse(BaseModel):
    status: str
    agent: str
    version: str
    timestamp: str
    port: int

class ActionRequest(BaseModel):
    action: str
    params: Dict[str, Any] = {}

class ActionResponse(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None

# Helpers
async def log_to_event_bus(event_type: str, data: Dict):
    """Log event to Event Bus for audit trail"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{EVENT_BUS_URL}/publish", json={
                "event": event_type,
                "source": AGENT_NAME,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"Event Bus logging failed: {e}")

async def notify_hermes(message: str, priority: str = "normal"):
    """Send notification via HERMES"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(f"{HERMES_URL}/notify", json={
                "channel": "telegram",
                "message": f"[{AGENT_NAME}] {message}",
                "priority": priority
            })
    except Exception as e:
        print(f"HERMES notification failed: {e}")

async def supabase_query(query: str, params: List = None):
    """Execute Supabase query via REST"""
    # Implement based on your Supabase setup
    pass

# Endpoints
@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy",
        agent=AGENT_NAME,
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat(),
        port=AGENT_PORT
    )

@app.get("/info")
async def info():
    """Agent information"""
    return {
        "agent": AGENT_NAME,
        "description": AGENT_DESCRIPTION,
        "port": AGENT_PORT,
        "endpoints": [route.path for route in app.routes]
    }

@app.post("/action", response_model=ActionResponse)
async def action(request: ActionRequest):
    """Generic action endpoint - override in specific agents"""
    await log_to_event_bus(f"{AGENT_NAME.lower()}_action", {
        "action": request.action,
        "params": request.params
    })

    # Implement your logic here
    return ActionResponse(
        success=True,
        result={"message": f"Action {request.action} executed"}
    )

# Lifecycle
@app.on_event("startup")
async def startup():
    """Register with Event Bus on startup"""
    await log_to_event_bus("agent_started", {
        "agent": AGENT_NAME,
        "port": AGENT_PORT
    })

@app.on_event("shutdown")
async def shutdown():
    """Deregister on shutdown"""
    await log_to_event_bus("agent_stopped", {
        "agent": AGENT_NAME,
        "port": AGENT_PORT
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
