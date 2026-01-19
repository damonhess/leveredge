"""
LeverEdge Fleet Dashboard
========================
Real-time monitoring dashboard for all agents in the LeverEdge fleet.
Port: 8060
"""

import asyncio
import json
import os
import time
from datetime import datetime, date
from typing import Optional

import httpx
import psutil
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LeverEdge Fleet Dashboard", version="1.0.0")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Agent configuration loaded from registry
def load_agents_from_registry():
    """Load agents from alias registry."""
    with open("/opt/leveredge/config/agent-aliases.json", 'r') as f:
        registry = json.load(f)

    agents = {}
    for domain, domain_agents in registry.get("agents", {}).items():
        for generic, info in domain_agents.items():
            if info.get("status") != "active":
                continue

            alias = info.get("alias", generic.upper())
            primary_port = info["ports"][0] if info.get("ports") else None

            if primary_port:
                agents[alias] = {
                    "port": primary_port,
                    "category": domain.lower(),
                    "description": info.get("function", ""),
                    "generic": generic
                }

    return agents

AGENTS = load_agents_from_registry()

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


# ============ COMMAND CENTER ENDPOINTS ============

async def fetch_magnus_status() -> dict:
    """Fetch project status from MAGNUS."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("http://localhost:8017/status")
            if response.status_code == 200:
                return response.json()
    except:
        pass
    return {"error": "MAGNUS unavailable"}


async def fetch_varys_intel() -> dict:
    """Fetch intelligence from VARYS."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("http://localhost:8112/portfolio/summary")
            if response.status_code == 200:
                return response.json()
    except:
        pass
    return {"error": "VARYS unavailable"}


async def fetch_littlefinger_finances() -> dict:
    """Fetch financial status from LITTLEFINGER."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("http://localhost:8020/snapshot")
            if response.status_code == 200:
                return response.json()
    except:
        pass
    return {"error": "LITTLEFINGER unavailable"}


@app.get("/command-center/status")
async def command_center_status():
    """Aggregate status for Command Center - main dashboard endpoint."""

    # Calculate days to launch (March 1, 2026)
    launch_date = date(2026, 3, 1)
    days_to_launch = (launch_date - date.today()).days

    # Parallel fetch from all sources
    magnus_task = fetch_magnus_status()
    varys_task = fetch_varys_intel()
    littlefinger_task = fetch_littlefinger_finances()

    magnus, varys, littlefinger = await asyncio.gather(
        magnus_task, varys_task, littlefinger_task,
        return_exceptions=True
    )

    # Handle exceptions
    if isinstance(magnus, Exception):
        magnus = {"error": str(magnus)}
    if isinstance(varys, Exception):
        varys = {"error": str(varys)}
    if isinstance(littlefinger, Exception):
        littlefinger = {"error": str(littlefinger)}

    return {
        "timestamp": datetime.now().isoformat(),
        "days_to_launch": days_to_launch,
        "projects": magnus,
        "portfolio": varys,
        "finances": littlefinger,
    }


@app.get("/command-center/agents")
async def command_center_agents():
    """Get status of all agents organized by domain."""

    # Group agents by category
    domains = {}
    for name, config in AGENTS.items():
        category = config["category"]
        if category not in domains:
            domains[category] = []
        domains[category].append({
            "name": name,
            "port": config["port"],
            "description": config["description"]
        })

    # Check health for each agent
    async with httpx.AsyncClient(timeout=2.0) as client:
        for category, agents in domains.items():
            for agent in agents:
                if agent["port"] == 0:
                    agent["status"] = "external"
                    continue
                try:
                    response = await client.get(f"http://localhost:{agent['port']}/health")
                    agent["status"] = "healthy" if response.status_code == 200 else "unhealthy"
                except:
                    agent["status"] = "down"

    return domains


@app.get("/command-center/projects")
async def command_center_projects():
    """Get project details from MAGNUS."""
    return await fetch_magnus_status()


@app.get("/command-center/intel")
async def command_center_intel():
    """Get intelligence from VARYS."""
    return await fetch_varys_intel()


@app.get("/command-center/finances")
async def command_center_finances():
    """Get financial status from LITTLEFINGER."""
    return await fetch_littlefinger_finances()


@app.websocket("/ws/command-center")
async def command_center_websocket(websocket: WebSocket):
    """Real-time updates for Command Center."""
    await websocket.accept()

    try:
        while True:
            # Send status update every 30 seconds
            status = await command_center_status()
            await websocket.send_json(status)
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8060)
