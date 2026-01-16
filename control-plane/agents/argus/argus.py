#!/usr/bin/env python3
"""
ARGUS - Monitoring Agent
Port: 8016

Provides unified monitoring view across all agents and services.
Integrates with Prometheus for metrics.
"""

import os
import httpx
import asyncio
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

app = FastAPI(title="ARGUS", description="Monitoring Agent", version="1.0.0")

# Configuration
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://host.docker.internal:9090")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")

# Agent registry with health endpoints
AGENTS = {
    "event-bus": {"url": "http://event-bus:8099", "port": 8099},
    "chronos": {"url": "http://chronos:8010", "port": 8010},
    "hades": {"url": "http://hades:8008", "port": 8008},
    "hermes": {"url": "http://hermes:8014", "port": 8014},
    "aegis": {"url": "http://host.docker.internal:8012", "port": 8012},
    "hephaestus": {"url": "http://host.docker.internal:8011", "port": 8011},
    "control-n8n": {"url": "http://control-n8n:5678", "port": 5678},
}

# Alert thresholds
THRESHOLDS = {
    "cpu_percent": {"warning": 70, "critical": 90},
    "memory_percent": {"warning": 80, "critical": 95},
    "failure_rate": {"warning": 0.1, "critical": 0.3},  # 10%, 30%
}

# Models
class AlertRequest(BaseModel):
    severity: str = "warning"  # info, warning, critical
    message: str
    target: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class AgentStatus(BaseModel):
    name: str
    status: str
    response_time_ms: Optional[float] = None
    last_check: str
    details: Optional[Dict[str, Any]] = None

# Helpers
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "ARGUS",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

async def send_alert_to_hermes(severity: str, message: str, target: str = ""):
    """Send alert notification via HERMES"""
    try:
        async with httpx.AsyncClient() as client:
            priority = "critical" if severity == "critical" else "high" if severity == "warning" else "normal"
            await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "message": f"[{severity.upper()}] {target}: {message}",
                    "priority": priority
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES alert failed: {e}")

async def check_agent_health(name: str, config: dict) -> AgentStatus:
    """Check health of a single agent"""
    start = datetime.utcnow()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{config['url']}/health",
                timeout=5.0
            )
            elapsed = (datetime.utcnow() - start).total_seconds() * 1000

            if resp.status_code == 200:
                return AgentStatus(
                    name=name,
                    status="healthy",
                    response_time_ms=elapsed,
                    last_check=datetime.utcnow().isoformat(),
                    details=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else None
                )
            else:
                return AgentStatus(
                    name=name,
                    status="unhealthy",
                    response_time_ms=elapsed,
                    last_check=datetime.utcnow().isoformat(),
                    details={"status_code": resp.status_code}
                )
    except httpx.TimeoutException:
        return AgentStatus(
            name=name,
            status="timeout",
            last_check=datetime.utcnow().isoformat()
        )
    except Exception as e:
        return AgentStatus(
            name=name,
            status="error",
            last_check=datetime.utcnow().isoformat(),
            details={"error": str(e)}
        )

async def query_prometheus(query: str) -> Optional[Dict]:
    """Query Prometheus for metrics"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{PROMETHEUS_URL}/api/v1/query",
                params={"query": query},
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"Prometheus query failed: {e}")
    return None

# Endpoints
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "ARGUS",
        "port": 8016,
        "monitored_agents": len(AGENTS),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/status")
async def get_all_status():
    """Get health status of all monitored agents"""
    tasks = [check_agent_health(name, config) for name, config in AGENTS.items()]
    results = await asyncio.gather(*tasks)

    statuses = [r.model_dump() for r in results]
    healthy_count = sum(1 for r in results if r.status == "healthy")
    unhealthy = [r.name for r in results if r.status != "healthy"]

    overall = "healthy" if healthy_count == len(AGENTS) else "degraded" if healthy_count > 0 else "critical"

    return {
        "overall_status": overall,
        "healthy_count": healthy_count,
        "total_agents": len(AGENTS),
        "unhealthy_agents": unhealthy,
        "agents": statuses,
        "checked_at": datetime.utcnow().isoformat()
    }

@app.get("/status/{agent}")
async def get_agent_status(agent: str):
    """Get health status of a specific agent"""
    if agent not in AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent}' not registered")

    status = await check_agent_health(agent, AGENTS[agent])
    return status.model_dump()

@app.get("/metrics")
async def get_metrics_summary():
    """Get simplified metrics summary from Prometheus"""
    metrics = {}

    # Query key metrics
    queries = {
        "cpu_usage": 'avg(100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100))',
        "memory_usage": '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
        "disk_usage": '100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)',
        "container_count": 'count(container_last_seen{name!=""})',
    }

    for name, query in queries.items():
        result = await query_prometheus(query)
        if result and result.get("status") == "success":
            data = result.get("data", {}).get("result", [])
            if data:
                metrics[name] = float(data[0].get("value", [0, 0])[1])

    return {
        "metrics": metrics,
        "prometheus_reachable": bool(metrics),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/alert")
async def trigger_alert(req: AlertRequest):
    """Manually trigger an alert"""
    await log_to_event_bus(
        "alert_triggered",
        target=req.target or "system",
        details={
            "severity": req.severity,
            "message": req.message,
            "details": req.details
        }
    )

    # Send to HERMES
    await send_alert_to_hermes(req.severity, req.message, req.target or "")

    return {
        "status": "sent",
        "severity": req.severity,
        "target": req.target,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/check")
async def run_health_check():
    """Run a comprehensive health check and alert on issues"""
    issues = []

    # Check all agents
    for name, config in AGENTS.items():
        status = await check_agent_health(name, config)
        if status.status != "healthy":
            issues.append({
                "agent": name,
                "status": status.status,
                "details": status.details
            })

    # Log to Event Bus
    await log_to_event_bus(
        "health_check_completed",
        details={
            "issues_found": len(issues),
            "issues": issues
        }
    )

    # Alert on critical issues
    if issues:
        for issue in issues:
            if issue["status"] in ["error", "timeout"]:
                await send_alert_to_hermes(
                    "critical",
                    f"Agent {issue['agent']} is {issue['status']}",
                    issue['agent']
                )

    return {
        "status": "completed",
        "issues_found": len(issues),
        "issues": issues,
        "checked_at": datetime.utcnow().isoformat()
    }

@app.get("/prometheus/query")
async def prometheus_query(query: str):
    """Execute a Prometheus query"""
    result = await query_prometheus(query)
    if result is None:
        raise HTTPException(status_code=503, detail="Prometheus unavailable")
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8016)
