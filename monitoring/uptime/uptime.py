#!/usr/bin/env python3
"""
Uptime Monitoring System for Leveredge Agent Fleet
Port: 8063

Monitors all agent endpoints every 5 minutes, tracks response times,
alerts on downtime via HERMES, and provides historical uptime statistics.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from pydantic import BaseModel

# Configuration
PORT = 8063
PING_INTERVAL_MINUTES = 5
HISTORY_FILE = Path(__file__).parent / "data" / "history.json"
HERMES_URL = "http://localhost:8014"
REQUEST_TIMEOUT = 10.0  # seconds

# Agent definitions
AGENTS = {
    # Core Fleet
    "ATLAS": {"port": 8007, "category": "Core", "description": "Central Orchestrator"},
    "HADES": {"port": 8008, "category": "Core", "description": "Storage & Persistence"},
    "CHRONOS": {"port": 8010, "category": "Core", "description": "Scheduler"},
    "HEPHAESTUS": {"port": 8011, "category": "Core", "description": "Code Forge"},
    "AEGIS": {"port": 8012, "category": "Core", "description": "Security Guardian"},
    "ATHENA": {"port": 8013, "category": "Core", "description": "Knowledge Base"},
    "HERMES": {"port": 8014, "category": "Core", "description": "Messenger"},
    "ALOY": {"port": 8015, "category": "Core", "description": "AI Assistant"},
    "ARGUS": {"port": 8016, "category": "Core", "description": "System Monitor"},
    "CHIRON": {"port": 8017, "category": "Core", "description": "Healer"},
    "SCHOLAR": {"port": 8018, "category": "Core", "description": "Research"},
    "SENTINEL": {"port": 8019, "category": "Core", "description": "Watchdog"},
    "EVENT-BUS": {"port": 8099, "category": "Core", "description": "Event System"},

    # Security Fleet
    "CERBERUS": {"port": 8020, "category": "Security", "description": "Access Control"},
    "PORT-MANAGER": {"port": 8021, "category": "Security", "description": "Port Registry"},

    # Creative Fleet
    "MUSE": {"port": 8030, "category": "Creative", "description": "Creative Director"},
    "CALLIOPE": {"port": 8031, "category": "Creative", "description": "Content Writer"},
    "THALIA": {"port": 8032, "category": "Creative", "description": "Visual Designer"},
    "ERATO": {"port": 8033, "category": "Creative", "description": "Video Producer"},
    "CLIO": {"port": 8034, "category": "Creative", "description": "Asset Manager"},

    # Personal Fleet
    "GYM-COACH": {"port": 8110, "category": "Personal", "description": "Fitness Training"},
    "NUTRITIONIST": {"port": 8101, "category": "Personal", "description": "Nutrition Planning"},
    "MEAL-PLANNER": {"port": 8102, "category": "Personal", "description": "Meal Planning"},
    "ACADEMIC-GUIDE": {"port": 8103, "category": "Personal", "description": "Academic Advisor"},
    "EROS": {"port": 8104, "category": "Personal", "description": "Relationship Coach"},

    # Business Fleet (8200-8209)
    "HERACLES": {"port": 8200, "category": "Business", "description": "Project Manager"},
    "LIBRARIAN": {"port": 8201, "category": "Business", "description": "Document Manager"},
    "DAEDALUS": {"port": 8202, "category": "Business", "description": "Solution Architect"},
    "THEMIS": {"port": 8203, "category": "Business", "description": "Legal Advisor"},
    "MENTOR": {"port": 8204, "category": "Business", "description": "Career Coach"},
    "PLUTUS": {"port": 8205, "category": "Business", "description": "Financial Advisor"},
    "PROCUREMENT": {"port": 8206, "category": "Business", "description": "Procurement Agent"},
    "HEPHAESTUS-SERVER": {"port": 8207, "category": "Business", "description": "Server Manager"},
    "ATLAS-INFRA": {"port": 8208, "category": "Business", "description": "Infrastructure"},
    "IRIS": {"port": 8209, "category": "Business", "description": "Communications"},
}


class AgentStatus(BaseModel):
    name: str
    port: int
    category: str
    description: str
    status: str  # "up", "down", "unknown"
    response_time_ms: Optional[float] = None
    last_check: Optional[str] = None
    error: Optional[str] = None


class HistoryEntry(BaseModel):
    timestamp: str
    status: str
    response_time_ms: Optional[float] = None
    error: Optional[str] = None


class UptimeData(BaseModel):
    agent: str
    uptime_24h: float
    uptime_7d: float
    uptime_30d: float
    avg_response_time_ms: float
    total_checks: int
    successful_checks: int


# Global state
current_status: Dict[str, AgentStatus] = {}
scheduler: Optional[AsyncIOScheduler] = None
downtime_alerts_sent: Dict[str, datetime] = {}  # Track when we sent alerts


def load_history() -> Dict[str, List[dict]]:
    """Load history from JSON file."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_history(history: Dict[str, List[dict]]):
    """Save history to JSON file."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def prune_old_history(history: Dict[str, List[dict]], days: int = 30) -> Dict[str, List[dict]]:
    """Remove history entries older than specified days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    pruned = {}
    for agent, entries in history.items():
        pruned[agent] = [e for e in entries if e.get("timestamp", "") >= cutoff_str]

    return pruned


async def ping_agent(agent_name: str, agent_info: dict) -> AgentStatus:
    """Ping a single agent and return its status."""
    url = f"http://localhost:{agent_info['port']}/health"
    status = AgentStatus(
        name=agent_name,
        port=agent_info["port"],
        category=agent_info["category"],
        description=agent_info["description"],
        status="unknown",
        last_check=datetime.utcnow().isoformat()
    )

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            start_time = time.time()
            response = await client.get(url)
            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                status.status = "up"
                status.response_time_ms = round(elapsed_ms, 2)
            else:
                status.status = "down"
                status.error = f"HTTP {response.status_code}"
                status.response_time_ms = round(elapsed_ms, 2)
    except httpx.TimeoutException:
        status.status = "down"
        status.error = "Timeout"
    except httpx.ConnectError:
        status.status = "down"
        status.error = "Connection refused"
    except Exception as e:
        status.status = "down"
        status.error = str(e)

    return status


async def send_alert(agent_name: str, status: str, error: Optional[str] = None):
    """Send alert to HERMES about agent status change."""
    # Don't spam alerts - only send once per downtime event
    if status == "down":
        if agent_name in downtime_alerts_sent:
            # Already sent alert for this downtime
            return
        downtime_alerts_sent[agent_name] = datetime.utcnow()
    else:
        # Agent is back up, clear the alert tracking
        downtime_alerts_sent.pop(agent_name, None)
        return  # Don't send recovery alerts for now (could add if needed)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            alert_data = {
                "type": "uptime_alert",
                "severity": "warning" if status == "down" else "info",
                "agent": agent_name,
                "status": status,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
                "message": f"Agent {agent_name} is {status}" + (f": {error}" if error else "")
            }
            await client.post(f"{HERMES_URL}/alert", json=alert_data)
    except Exception:
        # If HERMES is down, we can't send alerts - that's okay
        pass


async def ping_all_agents():
    """Ping all agents and update status."""
    global current_status

    history = load_history()

    # Ping all agents concurrently
    tasks = [ping_agent(name, info) for name, info in AGENTS.items()]
    results = await asyncio.gather(*tasks)

    for status in results:
        # Update current status
        current_status[status.name] = status

        # Record in history
        if status.name not in history:
            history[status.name] = []

        history[status.name].append({
            "timestamp": status.last_check,
            "status": status.status,
            "response_time_ms": status.response_time_ms,
            "error": status.error
        })

        # Send alert if down
        if status.status == "down":
            await send_alert(status.name, status.status, status.error)

    # Prune old history and save
    history = prune_old_history(history)
    save_history(history)


def calculate_uptime(entries: List[dict], hours: int) -> float:
    """Calculate uptime percentage for a given time window."""
    if not entries:
        return 0.0

    cutoff = datetime.utcnow() - timedelta(hours=hours)
    cutoff_str = cutoff.isoformat()

    recent = [e for e in entries if e.get("timestamp", "") >= cutoff_str]
    if not recent:
        return 0.0

    up_count = sum(1 for e in recent if e.get("status") == "up")
    return round((up_count / len(recent)) * 100, 2)


def calculate_avg_response_time(entries: List[dict]) -> float:
    """Calculate average response time from history entries."""
    times = [e.get("response_time_ms") for e in entries if e.get("response_time_ms") is not None]
    if not times:
        return 0.0
    return round(sum(times) / len(times), 2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - start/stop scheduler."""
    global scheduler

    # Initialize current status
    for name, info in AGENTS.items():
        current_status[name] = AgentStatus(
            name=name,
            port=info["port"],
            category=info["category"],
            description=info["description"],
            status="unknown"
        )

    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        ping_all_agents,
        trigger=IntervalTrigger(minutes=PING_INTERVAL_MINUTES),
        id="ping_all_agents",
        name="Ping all agents",
        replace_existing=True
    )
    scheduler.start()

    # Run initial ping
    await ping_all_agents()

    yield

    # Shutdown scheduler
    if scheduler:
        scheduler.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Uptime Monitor",
    description="Monitoring system for Leveredge Agent Fleet",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "uptime-monitor",
        "port": PORT,
        "timestamp": datetime.utcnow().isoformat(),
        "agents_monitored": len(AGENTS),
        "ping_interval_minutes": PING_INTERVAL_MINUTES
    }


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.get("/api/status")
async def get_status():
    """Get current status of all agents."""
    # Group by category
    by_category: Dict[str, List[dict]] = {}
    for status in current_status.values():
        cat = status.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(status.model_dump())

    # Calculate summary stats
    total = len(current_status)
    up = sum(1 for s in current_status.values() if s.status == "up")
    down = sum(1 for s in current_status.values() if s.status == "down")
    unknown = total - up - down

    return {
        "summary": {
            "total": total,
            "up": up,
            "down": down,
            "unknown": unknown,
            "uptime_percent": round((up / total) * 100, 2) if total > 0 else 0
        },
        "by_category": by_category,
        "last_check": datetime.utcnow().isoformat()
    }


@app.get("/api/history/{agent}")
async def get_agent_history(agent: str, hours: int = 24):
    """Get historical data for a specific agent."""
    if agent not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent {agent} not found")

    history = load_history()
    entries = history.get(agent, [])

    # Filter to requested time window
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    cutoff_str = cutoff.isoformat()
    recent = [e for e in entries if e.get("timestamp", "") >= cutoff_str]

    return {
        "agent": agent,
        "hours": hours,
        "entries": recent,
        "uptime_percent": calculate_uptime(entries, hours),
        "avg_response_time_ms": calculate_avg_response_time(recent),
        "total_checks": len(recent),
        "current_status": current_status.get(agent, {})
    }


@app.get("/api/uptime")
async def get_uptime_stats():
    """Get overall uptime percentages for all agents."""
    history = load_history()
    stats: List[dict] = []

    for agent_name in AGENTS:
        entries = history.get(agent_name, [])

        uptime_data = UptimeData(
            agent=agent_name,
            uptime_24h=calculate_uptime(entries, 24),
            uptime_7d=calculate_uptime(entries, 24 * 7),
            uptime_30d=calculate_uptime(entries, 24 * 30),
            avg_response_time_ms=calculate_avg_response_time(entries),
            total_checks=len(entries),
            successful_checks=sum(1 for e in entries if e.get("status") == "up")
        )
        stats.append(uptime_data.model_dump())

    # Sort by 24h uptime (worst first)
    stats.sort(key=lambda x: x["uptime_24h"])

    # Calculate overall averages
    if stats:
        avg_24h = sum(s["uptime_24h"] for s in stats) / len(stats)
        avg_7d = sum(s["uptime_7d"] for s in stats) / len(stats)
        avg_30d = sum(s["uptime_30d"] for s in stats) / len(stats)
    else:
        avg_24h = avg_7d = avg_30d = 0

    return {
        "overall": {
            "avg_uptime_24h": round(avg_24h, 2),
            "avg_uptime_7d": round(avg_7d, 2),
            "avg_uptime_30d": round(avg_30d, 2)
        },
        "agents": stats
    }


@app.post("/api/ping")
async def trigger_ping():
    """Manually trigger a ping of all agents."""
    await ping_all_agents()
    return {"status": "ok", "message": "Ping completed"}


@app.get("/api/agents")
async def list_agents():
    """List all monitored agents."""
    return {
        "agents": [
            {
                "name": name,
                "port": info["port"],
                "category": info["category"],
                "description": info["description"]
            }
            for name, info in AGENTS.items()
        ],
        "total": len(AGENTS)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
