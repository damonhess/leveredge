"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              SENTINEL                                          ║
║                    The Guardian of OLYMPUS                                     ║
║                                                                                ║
║  Responsibilities:                                                             ║
║  • Smart routing (n8n vs FastAPI ATLAS)                                       ║
║  • Health monitoring                                                           ║
║  • Drift detection                                                             ║
║  • Auto-failover                                                               ║
║  • Sync validation                                                             ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import httpx
import yaml
import os
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
FASTAPI_ATLAS_URL = os.getenv("FASTAPI_ATLAS_URL", "http://atlas:8007")
N8N_ATLAS_URL = os.getenv("N8N_ATLAS_URL", "http://control-n8n:5679")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")

# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH TRACKING
# ═══════════════════════════════════════════════════════════════════════════════

class EngineStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class EngineHealth:
    """Tracks health of an execution engine."""
    name: str
    url: str
    status: EngineStatus = EngineStatus.UNKNOWN
    last_check: Optional[datetime] = None
    last_success: Optional[datetime] = None
    consecutive_failures: int = 0
    response_time_ms: int = 0
    error: Optional[str] = None


class HealthMonitor:
    """Monitors health of ATLAS implementations."""
    
    def __init__(self):
        self.engines: Dict[str, EngineHealth] = {
            "fastapi": EngineHealth(name="FastAPI ATLAS", url=FASTAPI_ATLAS_URL),
            "n8n": EngineHealth(name="n8n ATLAS", url=N8N_ATLAS_URL)
        }
        self.client = httpx.AsyncClient(timeout=10.0)
        self.unhealthy_threshold = 3
    
    async def check_engine(self, engine_id: str) -> EngineHealth:
        """Check health of specific engine."""
        engine = self.engines.get(engine_id)
        if not engine:
            return None
        
        start = datetime.utcnow()
        
        try:
            if engine_id == "fastapi":
                response = await self.client.get(f"{engine.url}/health")
            else:
                # n8n health check
                response = await self.client.get(f"{engine.url}/healthz")
            
            response.raise_for_status()
            
            engine.status = EngineStatus.HEALTHY
            engine.last_success = datetime.utcnow()
            engine.consecutive_failures = 0
            engine.error = None
            
        except Exception as e:
            engine.consecutive_failures += 1
            engine.error = str(e)
            
            if engine.consecutive_failures >= self.unhealthy_threshold:
                engine.status = EngineStatus.UNHEALTHY
            else:
                engine.status = EngineStatus.DEGRADED
        
        engine.last_check = datetime.utcnow()
        engine.response_time_ms = int((engine.last_check - start).total_seconds() * 1000)
        
        return engine
    
    async def check_all(self) -> Dict[str, EngineHealth]:
        """Check all engines."""
        await asyncio.gather(
            self.check_engine("fastapi"),
            self.check_engine("n8n")
        )
        return self.engines
    
    def get_healthy_engine(self, preferred: str = None, complexity: str = "simple") -> Optional[str]:
        """Get healthiest engine, considering preference and complexity."""
        
        # Load routing config from registry
        with open(REGISTRY_PATH) as f:
            registry = yaml.safe_load(f)
        
        routing = registry.get("routing", {})
        engine_selection = routing.get("engine_selection", {})
        
        # Get preferred engine for complexity
        complexity_pref = engine_selection.get(complexity, {})
        preferred = preferred or complexity_pref.get("preferred", "n8n")
        fallback = complexity_pref.get("fallback", "fastapi")
        
        # Check preferred first
        if self.engines[preferred].status == EngineStatus.HEALTHY:
            return preferred
        
        # Try fallback
        if self.engines[fallback].status == EngineStatus.HEALTHY:
            return fallback
        
        # Return least-bad option
        if self.engines[preferred].status == EngineStatus.DEGRADED:
            return preferred
        if self.engines[fallback].status == EngineStatus.DEGRADED:
            return fallback
        
        return None


health_monitor = HealthMonitor()

# ═══════════════════════════════════════════════════════════════════════════════
# DRIFT DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class DriftDetector:
    """Detects drift between implementations and registry."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def validate_sync(self) -> dict:
        """Validate both implementations are in sync with registry."""
        
        with open(REGISTRY_PATH) as f:
            registry = yaml.safe_load(f)
        
        issues = []
        
        # Check FastAPI ATLAS
        try:
            response = await self.client.get(f"{FASTAPI_ATLAS_URL}/chains")
            fastapi_chains = {c["name"] for c in response.json().get("chains", [])}
            registry_chains = set(registry.get("chains", {}).keys())
            
            missing_in_fastapi = registry_chains - fastapi_chains
            if missing_in_fastapi:
                issues.append({
                    "engine": "fastapi",
                    "type": "missing_chains",
                    "chains": list(missing_in_fastapi)
                })
                
        except Exception as e:
            issues.append({
                "engine": "fastapi",
                "type": "unreachable",
                "error": str(e)
            })
        
        # Check n8n ATLAS (would need to query n8n API for workflows)
        # This is a placeholder - actual implementation would check n8n workflows
        
        return {
            "synced": len(issues) == 0,
            "issues": issues,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    async def auto_repair(self, issues: list) -> dict:
        """Attempt to auto-repair drift issues."""
        repairs = []
        
        for issue in issues:
            if issue["type"] == "missing_chains":
                # Could trigger ATHENA to regenerate n8n workflows
                repairs.append({
                    "issue": issue,
                    "action": "regenerate_required",
                    "manual": True
                })
        
        return {"repairs": repairs}


drift_detector = DriftDetector()

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════════════════════════════════════

class Router:
    """Routes intents to appropriate engine."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=180.0)
    
    def determine_complexity(self, intent: dict) -> str:
        """Determine complexity of an intent."""
        
        # Check for parallel steps
        steps = intent.get("steps", [])
        for step in steps:
            if step.get("type") == "parallel":
                return "complex"
        
        # Check chain name
        chain_name = intent.get("chain_name")
        if chain_name:
            with open(REGISTRY_PATH) as f:
                registry = yaml.safe_load(f)
            chain = registry.get("chains", {}).get(chain_name, {})
            return chain.get("complexity", "simple")
        
        # Check step count
        if len(steps) > 3:
            return "moderate"
        
        return "simple"
    
    async def route(self, intent: dict) -> dict:
        """Route intent to best available engine."""
        
        complexity = self.determine_complexity(intent)
        engine = health_monitor.get_healthy_engine(complexity=complexity)
        
        if not engine:
            raise HTTPException(503, "No healthy orchestration engine available")
        
        # Forward to selected engine
        if engine == "fastapi":
            response = await self.client.post(
                f"{FASTAPI_ATLAS_URL}/execute",
                json=intent
            )
        else:
            # Forward to n8n webhook
            response = await self.client.post(
                f"{N8N_ATLAS_URL}/webhook/atlas",
                json=intent
            )
        
        result = response.json()
        result["_routed_to"] = engine
        result["_complexity"] = complexity
        
        return result


router = Router()

# ═══════════════════════════════════════════════════════════════════════════════
# API MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class Intent(BaseModel):
    intent_id: Optional[str] = None
    source: str = "api"
    type: str = "single"
    chain_name: Optional[str] = None
    steps: Optional[list] = None
    input: dict = {}
    options: Optional[dict] = None
    
    # Routing hints
    prefer_engine: Optional[str] = None  # "fastapi" or "n8n"
    force_engine: Optional[str] = None   # Override routing decision

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="SENTINEL - The Guardian",
    description="Smart routing, health monitoring, and drift detection for OLYMPUS",
    version="1.0.0"
)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "agent": "SENTINEL",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/status")
async def status():
    """Get full system status."""
    await health_monitor.check_all()
    
    return {
        "sentinel": "healthy",
        "engines": {
            name: {
                "status": eng.status.value,
                "last_check": eng.last_check.isoformat() if eng.last_check else None,
                "response_time_ms": eng.response_time_ms,
                "consecutive_failures": eng.consecutive_failures,
                "error": eng.error
            }
            for name, eng in health_monitor.engines.items()
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/engines")
async def list_engines():
    """List available engines and their status."""
    await health_monitor.check_all()
    
    return {
        "engines": [
            {
                "id": name,
                "name": eng.name,
                "url": eng.url,
                "status": eng.status.value,
                "healthy": eng.status == EngineStatus.HEALTHY
            }
            for name, eng in health_monitor.engines.items()
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/orchestrate")
async def orchestrate(intent: Intent, background_tasks: BackgroundTasks):
    """
    Main orchestration endpoint.
    
    Routes to the best available engine based on:
    - Intent complexity
    - Engine health
    - User preference
    """
    
    # Check health first
    await health_monitor.check_all()
    
    # Honor force_engine if specified
    if intent.force_engine:
        engine = intent.force_engine
        eng_health = health_monitor.engines.get(engine)
        if not eng_health or eng_health.status == EngineStatus.UNHEALTHY:
            raise HTTPException(503, f"Forced engine '{engine}' is unhealthy")
    else:
        # Smart routing
        complexity = router.determine_complexity(intent.dict())
        engine = health_monitor.get_healthy_engine(
            preferred=intent.prefer_engine,
            complexity=complexity
        )
    
    if not engine:
        raise HTTPException(503, "No healthy orchestration engine available")
    
    # Log routing decision
    background_tasks.add_task(
        log_event,
        "orchestration_routed",
        {
            "intent_id": intent.intent_id,
            "engine": engine,
            "complexity": router.determine_complexity(intent.dict())
        }
    )
    
    # Forward to engine
    return await router.route(intent.dict())

# ─────────────────────────────────────────────────────────────────────────────
# SYNC VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/validate-sync")
async def validate_sync(background_tasks: BackgroundTasks):
    """Validate both engines are in sync with registry."""
    result = await drift_detector.validate_sync()
    
    if not result["synced"]:
        # Alert on drift
        background_tasks.add_task(
            alert_drift,
            result["issues"]
        )
    
    return result

@app.post("/repair-drift")
async def repair_drift():
    """Attempt to repair drift between implementations."""
    validation = await drift_detector.validate_sync()
    
    if validation["synced"]:
        return {"message": "No drift detected, nothing to repair"}
    
    repairs = await drift_detector.auto_repair(validation["issues"])
    return repairs

# ─────────────────────────────────────────────────────────────────────────────
# DIRECT ROUTING (bypass ATLAS for simple single-agent calls)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/direct/{agent}/{action}")
async def direct_call(agent: str, action: str, params: dict = {}):
    """
    Direct call to an agent, bypassing ATLAS.
    
    Use for simple single-agent calls where orchestration overhead isn't needed.
    """
    with open(REGISTRY_PATH) as f:
        registry = yaml.safe_load(f)
    
    agent_config = registry.get("agents", {}).get(agent.lower())
    if not agent_config:
        raise HTTPException(404, f"Agent '{agent}' not found")
    
    action_config = agent_config.get("actions", {}).get(action)
    if not action_config:
        raise HTTPException(404, f"Action '{action}' not found for agent '{agent}'")
    
    # Build request
    url = f"{agent_config['connection']['url']}{action_config['endpoint']}"
    method = action_config.get("method", "POST")
    timeout = action_config.get("timeout_ms", 60000) / 1000
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        if method == "GET":
            response = await client.get(url, params=params)
        else:
            response = await client.post(url, json=params)
        
        return response.json()

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

async def log_event(event_type: str, data: dict):
    """Log event to Event Bus."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={"event_type": event_type, "source": "SENTINEL", "data": data},
                timeout=2.0
            )
    except:
        pass

async def alert_drift(issues: list):
    """Alert on drift detection."""
    message = f"⚠️ ATLAS Drift Detected:\n"
    for issue in issues:
        message += f"• {issue['engine']}: {issue['type']}\n"
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{HERMES_URL}/notify",
                json={"channel": "telegram", "message": message, "priority": "high"},
                timeout=5.0
            )
    except:
        pass

# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND TASKS
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize on startup."""
    await health_monitor.check_all()
    await log_event("agent_started", {"agent": "SENTINEL", "version": "1.0.0"})

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
