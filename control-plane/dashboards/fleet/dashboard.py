"""
LeverEdge Fleet Dashboard
========================
Real-time monitoring dashboard for all agents in the LeverEdge fleet.
Port: 8060
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Optional

import httpx
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LeverEdge Fleet Dashboard", version="1.0.0")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Agent configuration
AGENTS = {
    # Core Fleet
    "ATLAS": {"port": 8007, "category": "core", "description": "Infrastructure orchestrator"},
    "HADES": {"port": 8008, "category": "core", "description": "Data persistence layer"},
    "CHRONOS": {"port": 8010, "category": "core", "description": "Scheduler & time management"},
    "HEPHAESTUS": {"port": 8011, "category": "core", "description": "Code generation & tooling"},
    "AEGIS": {"port": 8012, "category": "core", "description": "Security & access control"},
    "ATHENA": {"port": 8013, "category": "core", "description": "Knowledge & reasoning"},
    "HERMES": {"port": 8014, "category": "core", "description": "Communication & messaging"},
    "ALOY": {"port": 8015, "category": "core", "description": "Resource management"},
    "ARGUS": {"port": 8016, "category": "core", "description": "Monitoring & alerting"},
    "CHIRON": {"port": 8017, "category": "core", "description": "Training & mentoring"},
    "SCHOLAR": {"port": 8018, "category": "core", "description": "Research & analysis"},
    "SENTINEL": {"port": 8019, "category": "core", "description": "Threat detection"},
    "EVENT-BUS": {"port": 8099, "category": "core", "description": "Event messaging backbone"},

    # Security Fleet
    "CERBERUS": {"port": 8020, "category": "security", "description": "Authentication guardian"},
    "PORT-MANAGER": {"port": 8021, "category": "security", "description": "Network port control"},

    # Creative Fleet
    "MUSE": {"port": 8030, "category": "creative", "description": "Creative inspiration"},
    "CALLIOPE": {"port": 8031, "category": "creative", "description": "Epic content creation"},
    "THALIA": {"port": 8032, "category": "creative", "description": "Comedy & entertainment"},
    "ERATO": {"port": 8033, "category": "creative", "description": "Lyric & poetry"},
    "CLIO": {"port": 8034, "category": "creative", "description": "History & documentation"},

    # Personal Fleet
    "GYM-COACH": {"port": 8110, "category": "personal", "description": "Fitness training"},
    "NUTRITIONIST": {"port": 8101, "category": "personal", "description": "Diet planning"},
    "MEAL-PLANNER": {"port": 8102, "category": "personal", "description": "Meal scheduling"},
    "ACADEMIC-GUIDE": {"port": 8103, "category": "personal", "description": "Education support"},
    "EROS": {"port": 8104, "category": "personal", "description": "Relationship coaching"},

    # Business Fleet
    "HERACLES": {"port": 8200, "category": "business", "description": "Strength & performance"},
    "LIBRARIAN": {"port": 8201, "category": "business", "description": "Knowledge management"},
    "DAEDALUS": {"port": 8202, "category": "business", "description": "Architecture & design"},
    "THEMIS": {"port": 8203, "category": "business", "description": "Legal & compliance"},
    "MENTOR": {"port": 8204, "category": "business", "description": "Professional guidance"},
    "PLUTUS": {"port": 8205, "category": "business", "description": "Financial analysis"},
    "PROCUREMENT": {"port": 8206, "category": "business", "description": "Purchasing & supply"},
    "HEPHAESTUS-SERVER": {"port": 8207, "category": "business", "description": "Server tooling"},
    "ATLAS-INFRA": {"port": 8208, "category": "business", "description": "Infrastructure management"},
    "IRIS": {"port": 8209, "category": "business", "description": "Communication bridge"},
}

# Store activity logs in memory
activity_log = []
MAX_LOG_ENTRIES = 100

# Cost tracking cache
cost_cache = {}
cost_cache_time = 0
COST_CACHE_TTL = 60  # seconds


def log_activity(agent: str, action: str, status: str, details: str = ""):
    """Add entry to activity log."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent,
        "action": action,
        "status": status,
        "details": details
    }
    activity_log.insert(0, entry)
    if len(activity_log) > MAX_LOG_ENTRIES:
        activity_log.pop()


async def check_agent_health(name: str, port: int) -> dict:
    """Check health status of a single agent."""
    url = f"http://localhost:{port}/health"
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            start = time.time()
            response = await client.get(url)
            latency = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                return {
                    "status": "healthy",
                    "latency_ms": round(latency, 1),
                    "details": data
                }
            else:
                return {
                    "status": "unhealthy",
                    "latency_ms": round(latency, 1),
                    "error": f"HTTP {response.status_code}"
                }
    except httpx.ConnectError:
        return {"status": "offline", "error": "Connection refused"}
    except httpx.TimeoutException:
        return {"status": "timeout", "error": "Request timed out"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def get_process_stats(port: int) -> dict:
    """Get CPU and memory stats for process listening on port."""
    try:
        # Find process by port
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr.port == port and conn.status == 'LISTEN':
                try:
                    proc = psutil.Process(conn.pid)
                    with proc.oneshot():
                        cpu = proc.cpu_percent(interval=0.1)
                        mem = proc.memory_info()
                        return {
                            "pid": conn.pid,
                            "cpu_percent": round(cpu, 1),
                            "memory_mb": round(mem.rss / 1024 / 1024, 1),
                            "memory_percent": round(proc.memory_percent(), 1),
                            "threads": proc.num_threads(),
                            "status": proc.status()
                        }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        return {"error": "Process not found"}
    except Exception as e:
        return {"error": str(e)}


async def fetch_agent_costs() -> dict:
    """Fetch cost data from Event Bus."""
    global cost_cache, cost_cache_time

    # Return cached data if fresh
    if time.time() - cost_cache_time < COST_CACHE_TTL and cost_cache:
        return cost_cache

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Try to get costs from Event Bus
            response = await client.get("http://localhost:8099/costs/by-agent")
            if response.status_code == 200:
                cost_cache = response.json()
                cost_cache_time = time.time()
                return cost_cache
    except:
        pass

    # Return empty if Event Bus unavailable
    return {}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    with open(index_path, "r") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/agents")
async def get_agents():
    """Get list of all agents with their configuration."""
    return JSONResponse(content=AGENTS)


@app.get("/api/status")
async def get_all_status():
    """Get health status and stats for all agents."""
    tasks = []
    agent_names = list(AGENTS.keys())

    # Check health for all agents concurrently
    for name, config in AGENTS.items():
        tasks.append(check_agent_health(name, config["port"]))

    health_results = await asyncio.gather(*tasks)

    # Get process stats concurrently
    stats_tasks = []
    for name, config in AGENTS.items():
        stats_tasks.append(get_process_stats(config["port"]))

    stats_results = await asyncio.gather(*stats_tasks)

    # Fetch costs
    costs = await fetch_agent_costs()

    # Combine results
    result = {}
    for i, name in enumerate(agent_names):
        config = AGENTS[name]
        result[name] = {
            "name": name,
            "port": config["port"],
            "category": config["category"],
            "description": config["description"],
            "health": health_results[i],
            "stats": stats_results[i],
            "cost": costs.get(name, {"total": 0, "today": 0})
        }

    return JSONResponse(content=result)


@app.get("/api/status/{agent_name}")
async def get_agent_status(agent_name: str):
    """Get status for a specific agent."""
    agent_name = agent_name.upper()
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

    config = AGENTS[agent_name]
    health = await check_agent_health(agent_name, config["port"])
    stats = await get_process_stats(config["port"])
    costs = await fetch_agent_costs()

    return JSONResponse(content={
        "name": agent_name,
        "port": config["port"],
        "category": config["category"],
        "description": config["description"],
        "health": health,
        "stats": stats,
        "cost": costs.get(agent_name, {"total": 0, "today": 0})
    })


@app.post("/api/restart/{agent_name}")
async def restart_agent(agent_name: str):
    """Request agent restart via ATLAS."""
    agent_name = agent_name.upper()
    if agent_name not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

    log_activity(agent_name, "restart", "pending", "Restart requested")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:8007/restart",
                json={"agent": agent_name}
            )

            if response.status_code == 200:
                log_activity(agent_name, "restart", "success", "Restart initiated")
                return JSONResponse(content={
                    "status": "success",
                    "message": f"Restart initiated for {agent_name}"
                })
            else:
                log_activity(agent_name, "restart", "failed", f"HTTP {response.status_code}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"ATLAS returned {response.status_code}"
                )
    except httpx.ConnectError:
        log_activity(agent_name, "restart", "failed", "ATLAS unreachable")
        raise HTTPException(status_code=503, detail="ATLAS service unavailable")
    except httpx.TimeoutException:
        log_activity(agent_name, "restart", "failed", "Request timeout")
        raise HTTPException(status_code=504, detail="Request to ATLAS timed out")


@app.get("/api/activity")
async def get_activity():
    """Get recent activity log."""
    return JSONResponse(content=activity_log)


@app.get("/api/summary")
async def get_summary():
    """Get fleet summary statistics."""
    status = await get_all_status()
    data = status.body.decode() if hasattr(status, 'body') else "{}"

    # Parse the response
    import json
    agents_data = json.loads(data) if isinstance(data, str) else data

    healthy = 0
    unhealthy = 0
    offline = 0
    total_cpu = 0
    total_memory = 0
    total_cost = 0

    for name, agent in agents_data.items():
        health_status = agent.get("health", {}).get("status", "unknown")
        if health_status == "healthy":
            healthy += 1
        elif health_status == "offline":
            offline += 1
        else:
            unhealthy += 1

        stats = agent.get("stats", {})
        if "cpu_percent" in stats:
            total_cpu += stats["cpu_percent"]
        if "memory_mb" in stats:
            total_memory += stats["memory_mb"]

        cost = agent.get("cost", {})
        if isinstance(cost, dict):
            total_cost += cost.get("today", 0)

    return JSONResponse(content={
        "total_agents": len(AGENTS),
        "healthy": healthy,
        "unhealthy": unhealthy,
        "offline": offline,
        "total_cpu_percent": round(total_cpu, 1),
        "total_memory_mb": round(total_memory, 1),
        "total_cost_today": round(total_cost, 4)
    })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "fleet-dashboard", "port": 8060}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8060)
