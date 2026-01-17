#!/usr/bin/env python3
"""
HEPHAESTUS (SERVER-ADMIN) - AI-Powered Infrastructure Management Agent
Port: 8207

Named after the Greek god of the forge and craftsmanship, who builds and
maintains the tools of the gods. SERVER-ADMIN builds and maintains LeverEdge
infrastructure with precision and care.

CORE CAPABILITIES:
- Service Monitoring: Real-time status tracking of all services
- Container Management: Docker container lifecycle management
- Health Checks: Comprehensive health verification across endpoints
- Alerting: Intelligent alerting with HERMES integration
- Maintenance: Schedule and track maintenance windows

TEAM INTEGRATION:
- Time-aware (knows current date, days to launch)
- Event Bus integration for state change notifications
- Cost tracking using shared.cost_tracker
- Unified Memory integration for operational insights
"""

import os
import sys
import json
import asyncio
import httpx
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")
DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "HERMES": os.getenv("HERMES_URL", "http://hermes:8014"),
    "CHRONOS": os.getenv("CHRONOS_URL", "http://chronos:8010"),
    "CERBERUS": os.getenv("CERBERUS_URL", "http://cerberus:8209"),
    "ARIA": os.getenv("ARIA_URL", "http://aria:8001"),
    "EVENT_BUS": EVENT_BUS_URL
}

# Key dates
LAUNCH_DATE = date(2026, 3, 1)

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("HEPHAESTUS")

# In-memory caches (will be replaced with database in production)
services_cache: Dict[str, Dict] = {}
incidents_cache: Dict[str, Dict] = {}
maintenance_cache: Dict[str, Dict] = {}
alert_rules_cache: Dict[str, Dict] = {}
health_results_cache: List[Dict] = []

# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    print("[HEPHAESTUS] Starting Infrastructure Management Agent on port 8207")
    await notify_event_bus("server.agent.started", {
        "agent": "HEPHAESTUS",
        "port": 8207,
        "capabilities": ["monitoring", "containers", "health", "alerting", "maintenance"]
    })
    yield
    # Shutdown
    print("[HEPHAESTUS] Shutting down...")
    await notify_event_bus("server.agent.stopped", {"agent": "HEPHAESTUS"})


app = FastAPI(
    title="HEPHAESTUS (SERVER-ADMIN)",
    description="AI-Powered Infrastructure Management Agent",
    version="1.0.0",
    lifespan=lifespan
)

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
        return "FINAL PUSH"
    elif days_to_launch <= 28:
        return "OUTREACH PHASE"
    elif days_to_launch <= 45:
        return "POLISH PHASE"
    else:
        return "INFRASTRUCTURE PHASE"


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(infra_context: dict) -> str:
    """Build infrastructure management system prompt"""
    time_ctx = get_time_context()

    return f"""You are HEPHAESTUS (SERVER-ADMIN) - Infrastructure Management Agent for LeverEdge AI.

Named after Hephaestus, the Greek god of the forge and craftsmanship who builds and maintains the tools of the gods, you build and maintain LeverEdge infrastructure with precision and care.

## TIME AWARENESS
- Current: {time_ctx['day_of_week']}, {time_ctx['current_date']} at {time_ctx['current_time']}
- Days to Launch: {time_ctx['days_to_launch']}
- Phase: {time_ctx['phase']}

## YOUR IDENTITY
You are the operations brain of LeverEdge. You monitor services, manage containers, run health checks, handle alerts, and schedule maintenance to ensure 99.9% uptime.

## CURRENT INFRASTRUCTURE STATUS
- Total Services: {infra_context.get('total_services', 0)}
- Healthy Services: {infra_context.get('healthy_services', 0)}
- Degraded Services: {infra_context.get('degraded_services', 0)}
- Down Services: {infra_context.get('down_services', 0)}
- Active Incidents: {infra_context.get('active_incidents', 0)}
- Scheduled Maintenance: {infra_context.get('upcoming_maintenance', 0)}

## YOUR CAPABILITIES

### Service Monitoring
- Track status of all services in real-time
- Monitor container health via Docker API
- Track resource utilization (CPU, memory, disk)
- Map service dependencies
- Trend historical performance

### Container Management
- Restart containers gracefully
- View and stream container logs
- Manage container lifecycle
- Automatic recovery on failure
- Rolling updates for zero-downtime

### Health Checks
- HTTP/HTTPS endpoint probing
- TCP port availability checks
- Database connectivity verification
- Dependency chain validation
- Custom health check scripts

### Alerting
- Multi-severity alert classification
- Alert deduplication and suppression
- Escalation policies
- Automatic incident creation
- Integration with HERMES for notifications

### Maintenance
- Schedule maintenance windows
- Suppress alerts during maintenance
- Pre/post maintenance health verification
- Stakeholder notifications
- Maintenance audit trail

## TEAM COORDINATION
- Route security events to CERBERUS
- Send notifications via HERMES
- Request backups before maintenance via CHRONOS
- Log insights to ARIA via Unified Memory
- Publish events to Event Bus
- Coordinate with all agents for health monitoring

## RESPONSE FORMAT
For status requests:
1. Overall health summary
2. Any degraded or down services
3. Active incidents
4. Recent significant events
5. Recommended actions

For incident response:
1. Incident classification
2. Affected services
3. Root cause hypothesis
4. Immediate actions taken
5. Escalation if needed

## YOUR MISSION
Keep LeverEdge infrastructure running at 99.9% uptime.
Detect issues before they become outages.
Automate recovery where safe.
Every service matters.
"""


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

# Service Models
class ServiceCreate(BaseModel):
    name: str
    type: str  # api, database, queue, cache, container
    host: str
    port: Optional[int] = None
    health_endpoint: Optional[str] = None
    container_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    health_endpoint: Optional[str] = None
    status: Optional[str] = None
    container_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ServiceResponse(BaseModel):
    id: str
    name: str
    type: str
    host: str
    port: Optional[int]
    health_endpoint: Optional[str]
    status: str
    last_check: Optional[str]
    container_name: Optional[str]
    metadata: Optional[Dict[str, Any]]


# Health Check Models
class HealthCheckRequest(BaseModel):
    service_id: Optional[str] = None
    service_name: Optional[str] = None
    check_type: str = "liveness"  # liveness, readiness, startup, deep


class HealthCheckResult(BaseModel):
    service_id: str
    service_name: str
    status: str  # healthy, degraded, down, timeout
    response_time_ms: int
    check_type: str
    error_message: Optional[str] = None
    checked_at: str


# Container Models
class ContainerAction(BaseModel):
    graceful: bool = True
    timeout_seconds: int = 30


class ContainerLogsRequest(BaseModel):
    lines: int = 100
    since: Optional[str] = None
    until: Optional[str] = None
    filter: Optional[str] = None


# Alert Models
class AlertRuleCreate(BaseModel):
    service_id: Optional[str] = None
    name: str
    metric_name: str
    comparison: str  # gt, lt, eq, gte, lte
    threshold: float
    severity: str  # critical, high, medium, low
    action: str  # alert, restart, escalate
    cooldown_minutes: int = 5
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    metric_name: Optional[str] = None
    comparison: Optional[str] = None
    threshold: Optional[float] = None
    severity: Optional[str] = None
    action: Optional[str] = None
    cooldown_minutes: Optional[int] = None
    enabled: Optional[bool] = None


# Incident Models
class IncidentResolve(BaseModel):
    resolution_notes: str
    auto_resolved: bool = False


# Maintenance Models
class MaintenanceCreate(BaseModel):
    service_ids: List[str]
    scheduled_start: str
    scheduled_end: str
    description: str
    suppress_alerts: bool = True
    created_by: Optional[str] = None


class MaintenanceUpdate(BaseModel):
    scheduled_start: Optional[str] = None
    scheduled_end: Optional[str] = None
    description: Optional[str] = None
    suppress_alerts: Optional[bool] = None


# AI Analysis Request
class AnalysisRequest(BaseModel):
    context: str
    question: Optional[str] = None
    include_recommendations: bool = True


# =============================================================================
# EVENT BUS INTEGRATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus for all agents to see"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "HEPHAESTUS",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime'],
                    "days_to_launch": time_ctx['days_to_launch']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[HEPHAESTUS] Event bus notification failed: {e}")


async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[HEPHAESTUS] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "HEPHAESTUS"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[HEPHAESTUS] HERMES notification failed: {e}")


async def update_aria_knowledge(category: str, title: str, content: str, importance: str = "normal"):
    """Add entry to aria_knowledge so ARIA stays informed"""
    try:
        time_ctx = get_time_context()
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
                    "p_title": title,
                    "p_content": f"{content}\n\n[Logged by HEPHAESTUS at {time_ctx['current_datetime']}]",
                    "p_subcategory": "infrastructure",
                    "p_source": "hephaestus",
                    "p_importance": importance
                },
                timeout=10.0
            )
            return True
    except Exception as e:
        print(f"[HEPHAESTUS] Knowledge update failed: {e}")
        return False


# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, infra_context: dict = None) -> str:
    """Call Claude API with full context and cost tracking"""
    if not client:
        return "LLM not configured (missing ANTHROPIC_API_KEY)"

    try:
        context = infra_context or get_infrastructure_summary()
        system_prompt = build_system_prompt(context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        time_ctx = get_time_context()
        await log_llm_usage(
            agent="HEPHAESTUS",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"days_to_launch": time_ctx.get("days_to_launch")}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_id() -> str:
    """Generate a simple UUID-like ID"""
    import uuid
    return str(uuid.uuid4())


def get_infrastructure_summary() -> dict:
    """Get summary of infrastructure status"""
    total = len(services_cache)
    healthy = sum(1 for s in services_cache.values() if s.get('status') == 'healthy')
    degraded = sum(1 for s in services_cache.values() if s.get('status') == 'degraded')
    down = sum(1 for s in services_cache.values() if s.get('status') == 'down')
    active_incidents = sum(1 for i in incidents_cache.values() if i.get('resolved_at') is None)
    upcoming = sum(1 for m in maintenance_cache.values()
                   if m.get('status') == 'scheduled')

    return {
        "total_services": total,
        "healthy_services": healthy,
        "degraded_services": degraded,
        "down_services": down,
        "active_incidents": active_incidents,
        "upcoming_maintenance": upcoming
    }


async def perform_health_check(service: dict, check_type: str = "liveness") -> dict:
    """Perform actual health check on a service"""
    start_time = datetime.now()
    result = {
        "service_id": service["id"],
        "service_name": service["name"],
        "check_type": check_type,
        "checked_at": start_time.isoformat()
    }

    try:
        health_url = f"http://{service['host']}"
        if service.get('port'):
            health_url += f":{service['port']}"
        if service.get('health_endpoint'):
            health_url += service['health_endpoint']
        else:
            health_url += "/health"

        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(health_url, timeout=10.0)

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result["response_time_ms"] = int(elapsed)

        if response.status_code == 200:
            result["status"] = "healthy"
        elif response.status_code < 500:
            result["status"] = "degraded"
            result["error_message"] = f"HTTP {response.status_code}"
        else:
            result["status"] = "down"
            result["error_message"] = f"HTTP {response.status_code}"

    except httpx.TimeoutException:
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result["response_time_ms"] = int(elapsed)
        result["status"] = "timeout"
        result["error_message"] = "Request timed out"
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result["response_time_ms"] = int(elapsed)
        result["status"] = "down"
        result["error_message"] = str(e)

    return result


async def create_incident_from_health_failure(service: dict, health_result: dict):
    """Create an incident when health check fails"""
    incident_id = generate_id()
    now = datetime.now().isoformat()

    severity = "high" if health_result["status"] == "down" else "medium"

    incident = {
        "id": incident_id,
        "service_id": service["id"],
        "severity": severity,
        "description": f"Service {service['name']} is {health_result['status']}: {health_result.get('error_message', 'Unknown error')}",
        "started_at": now,
        "resolved_at": None,
        "auto_resolved": False,
        "created_at": now
    }

    incidents_cache[incident_id] = incident

    # Notify via event bus
    await notify_event_bus("server.incident.created", {
        "incident_id": incident_id,
        "service": service["name"],
        "severity": severity
    })

    # Alert via HERMES if critical/high
    if severity in ["critical", "high"]:
        await notify_hermes(
            f"INCIDENT: {service['name']} is {health_result['status']}",
            priority="high"
        )

    return incident


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "HEPHAESTUS",
        "role": "Infrastructure Management",
        "port": 8207,
        "current_time": time_ctx['current_datetime'],
        "days_to_launch": time_ctx['days_to_launch'],
        "phase": time_ctx['phase']
    }


@app.get("/status")
async def overall_status():
    """Overall infrastructure status"""
    time_ctx = get_time_context()
    summary = get_infrastructure_summary()

    # Determine overall health
    if summary["down_services"] > 0:
        overall = "critical"
    elif summary["degraded_services"] > 0:
        overall = "degraded"
    elif summary["active_incidents"] > 0:
        overall = "warning"
    else:
        overall = "healthy"

    return {
        "overall_status": overall,
        "summary": summary,
        "time_context": time_ctx,
        "timestamp": time_ctx['current_datetime']
    }


@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics"""
    summary = get_infrastructure_summary()
    time_ctx = get_time_context()

    metrics = []
    metrics.append(f"# HELP hephaestus_services_total Total number of monitored services")
    metrics.append(f"# TYPE hephaestus_services_total gauge")
    metrics.append(f'hephaestus_services_total {summary["total_services"]}')

    metrics.append(f"# HELP hephaestus_services_healthy Number of healthy services")
    metrics.append(f"# TYPE hephaestus_services_healthy gauge")
    metrics.append(f'hephaestus_services_healthy {summary["healthy_services"]}')

    metrics.append(f"# HELP hephaestus_services_degraded Number of degraded services")
    metrics.append(f"# TYPE hephaestus_services_degraded gauge")
    metrics.append(f'hephaestus_services_degraded {summary["degraded_services"]}')

    metrics.append(f"# HELP hephaestus_services_down Number of down services")
    metrics.append(f"# TYPE hephaestus_services_down gauge")
    metrics.append(f'hephaestus_services_down {summary["down_services"]}')

    metrics.append(f"# HELP hephaestus_incidents_active Number of active incidents")
    metrics.append(f"# TYPE hephaestus_incidents_active gauge")
    metrics.append(f'hephaestus_incidents_active {summary["active_incidents"]}')

    metrics.append(f"# HELP hephaestus_days_to_launch Days until launch")
    metrics.append(f"# TYPE hephaestus_days_to_launch gauge")
    metrics.append(f'hephaestus_days_to_launch {time_ctx["days_to_launch"]}')

    return "\n".join(metrics)


@app.get("/dashboard")
async def dashboard():
    """Dashboard data summary"""
    time_ctx = get_time_context()
    summary = get_infrastructure_summary()

    # Get recent health checks
    recent_checks = health_results_cache[-20:] if health_results_cache else []

    # Get active incidents
    active_incidents = [i for i in incidents_cache.values() if i.get('resolved_at') is None]

    # Get upcoming maintenance
    upcoming_maintenance = [
        m for m in maintenance_cache.values()
        if m.get('status') == 'scheduled'
    ]

    return {
        "summary": summary,
        "services_by_status": {
            "healthy": [s["name"] for s in services_cache.values() if s.get('status') == 'healthy'],
            "degraded": [s["name"] for s in services_cache.values() if s.get('status') == 'degraded'],
            "down": [s["name"] for s in services_cache.values() if s.get('status') == 'down'],
            "unknown": [s["name"] for s in services_cache.values() if s.get('status') == 'unknown']
        },
        "recent_health_checks": recent_checks,
        "active_incidents": active_incidents,
        "upcoming_maintenance": upcoming_maintenance,
        "time_context": time_ctx
    }


# =============================================================================
# SERVICE MONITORING ENDPOINTS
# =============================================================================

@app.get("/services")
async def list_services(
    status: Optional[str] = None,
    type: Optional[str] = None
):
    """List all services"""
    services = list(services_cache.values())

    if status:
        services = [s for s in services if s.get('status') == status]
    if type:
        services = [s for s in services if s.get('type') == type]

    return {
        "services": services,
        "total": len(services),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/services")
async def register_service(service: ServiceCreate):
    """Register a new service for monitoring"""
    service_id = generate_id()
    now = datetime.now().isoformat()

    service_data = {
        "id": service_id,
        "name": service.name,
        "type": service.type,
        "host": service.host,
        "port": service.port,
        "health_endpoint": service.health_endpoint,
        "status": "unknown",
        "last_check": None,
        "container_name": service.container_name,
        "metadata": service.metadata or {},
        "created_at": now,
        "updated_at": now
    }

    services_cache[service_id] = service_data

    await notify_event_bus("server.service.registered", {
        "service_id": service_id,
        "name": service.name,
        "type": service.type
    })

    return service_data


@app.get("/services/{service_id}")
async def get_service(service_id: str):
    """Get service details"""
    if service_id not in services_cache:
        raise HTTPException(status_code=404, detail="Service not found")
    return services_cache[service_id]


@app.put("/services/{service_id}")
async def update_service(service_id: str, update: ServiceUpdate):
    """Update service configuration"""
    if service_id not in services_cache:
        raise HTTPException(status_code=404, detail="Service not found")

    service = services_cache[service_id]
    update_data = update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        service[key] = value

    service["updated_at"] = datetime.now().isoformat()
    services_cache[service_id] = service

    return service


@app.delete("/services/{service_id}")
async def delete_service(service_id: str):
    """Remove service from monitoring"""
    if service_id not in services_cache:
        raise HTTPException(status_code=404, detail="Service not found")

    service = services_cache.pop(service_id)

    await notify_event_bus("server.service.deregistered", {
        "service_id": service_id,
        "name": service["name"]
    })

    return {"message": f"Service {service['name']} removed", "service_id": service_id}


@app.get("/services/{service_id}/history")
async def get_service_history(
    service_id: str,
    limit: int = Query(default=50, le=500)
):
    """Get service health history"""
    if service_id not in services_cache:
        raise HTTPException(status_code=404, detail="Service not found")

    history = [
        r for r in health_results_cache
        if r.get('service_id') == service_id
    ][-limit:]

    return {
        "service_id": service_id,
        "history": history,
        "count": len(history)
    }


@app.get("/services/summary")
async def services_summary():
    """Executive summary of all services"""
    summary = get_infrastructure_summary()
    time_ctx = get_time_context()

    by_type = {}
    for service in services_cache.values():
        stype = service.get('type', 'unknown')
        if stype not in by_type:
            by_type[stype] = {"total": 0, "healthy": 0, "degraded": 0, "down": 0}
        by_type[stype]["total"] += 1
        status = service.get('status', 'unknown')
        if status in by_type[stype]:
            by_type[stype][status] += 1

    return {
        "overall": summary,
        "by_type": by_type,
        "uptime_target": "99.9%",
        "time_context": time_ctx
    }


# =============================================================================
# CONTAINER MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/containers")
async def list_containers():
    """List all Docker containers"""
    # Filter services that have container names
    containers = []
    for service in services_cache.values():
        if service.get('container_name'):
            containers.append({
                "name": service['container_name'],
                "service_id": service['id'],
                "service_name": service['name'],
                "status": service.get('status', 'unknown')
            })

    return {
        "containers": containers,
        "total": len(containers),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/containers/{name}")
async def get_container(name: str):
    """Get container details"""
    # Find service with this container name
    for service in services_cache.values():
        if service.get('container_name') == name:
            return {
                "container_name": name,
                "service": service,
                "status": service.get('status', 'unknown'),
                "note": "Docker API integration pending - showing service-level data"
            }

    raise HTTPException(status_code=404, detail=f"Container {name} not found")


@app.post("/containers/{name}/restart")
async def restart_container(name: str, action: ContainerAction = None):
    """Restart a container"""
    action = action or ContainerAction()

    # Find service
    service = None
    for s in services_cache.values():
        if s.get('container_name') == name:
            service = s
            break

    if not service:
        raise HTTPException(status_code=404, detail=f"Container {name} not found")

    # Log the restart request
    await notify_event_bus("server.container.restarted", {
        "container": name,
        "service": service['name'],
        "graceful": action.graceful
    })

    # In production, this would call Docker API
    return {
        "message": f"Restart initiated for container {name}",
        "graceful": action.graceful,
        "timeout_seconds": action.timeout_seconds,
        "note": "Docker API integration pending",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/containers/{name}/stop")
async def stop_container(name: str, action: ContainerAction = None):
    """Stop a container"""
    action = action or ContainerAction()

    for service in services_cache.values():
        if service.get('container_name') == name:
            await notify_event_bus("server.container.stopped", {
                "container": name,
                "service": service['name']
            })
            return {
                "message": f"Stop initiated for container {name}",
                "graceful": action.graceful,
                "note": "Docker API integration pending"
            }

    raise HTTPException(status_code=404, detail=f"Container {name} not found")


@app.post("/containers/{name}/start")
async def start_container(name: str):
    """Start a container"""
    for service in services_cache.values():
        if service.get('container_name') == name:
            await notify_event_bus("server.container.started", {
                "container": name,
                "service": service['name']
            })
            return {
                "message": f"Start initiated for container {name}",
                "note": "Docker API integration pending"
            }

    raise HTTPException(status_code=404, detail=f"Container {name} not found")


@app.get("/containers/{name}/logs")
async def get_container_logs(name: str, request: ContainerLogsRequest = None):
    """Get container logs"""
    request = request or ContainerLogsRequest()

    for service in services_cache.values():
        if service.get('container_name') == name:
            return {
                "container": name,
                "service": service['name'],
                "logs": [],
                "lines_requested": request.lines,
                "note": "Docker API integration pending - logs will be available after Docker socket mount"
            }

    raise HTTPException(status_code=404, detail=f"Container {name} not found")


@app.get("/containers/{name}/stats")
async def get_container_stats(name: str):
    """Get container resource stats"""
    for service in services_cache.values():
        if service.get('container_name') == name:
            return {
                "container": name,
                "service": service['name'],
                "stats": {
                    "cpu_percent": None,
                    "memory_mb": None,
                    "memory_percent": None,
                    "network_rx_bytes": None,
                    "network_tx_bytes": None
                },
                "note": "Docker API integration pending"
            }

    raise HTTPException(status_code=404, detail=f"Container {name} not found")


# =============================================================================
# HEALTH CHECK ENDPOINTS
# =============================================================================

@app.post("/health-check/run")
async def run_health_check(request: HealthCheckRequest):
    """Run health check on a service"""
    service = None

    if request.service_id:
        service = services_cache.get(request.service_id)
    elif request.service_name:
        for s in services_cache.values():
            if s['name'] == request.service_name:
                service = s
                break

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    result = await perform_health_check(service, request.check_type)

    # Update service status
    services_cache[service['id']]['status'] = result['status']
    services_cache[service['id']]['last_check'] = result['checked_at']

    # Cache result
    health_results_cache.append(result)
    if len(health_results_cache) > 1000:
        health_results_cache.pop(0)

    # Create incident if unhealthy
    if result['status'] in ['down', 'timeout']:
        await create_incident_from_health_failure(service, result)
        await notify_event_bus("server.service.down", {
            "service": service['name'],
            "status": result['status'],
            "error": result.get('error_message')
        })
    elif result['status'] == 'degraded':
        await notify_event_bus("server.health.degraded", {
            "service": service['name'],
            "status": result['status']
        })

    return result


@app.get("/health-check/results")
async def get_health_check_results(
    limit: int = Query(default=50, le=500),
    status: Optional[str] = None
):
    """Get recent health check results"""
    results = health_results_cache[-limit:]

    if status:
        results = [r for r in results if r.get('status') == status]

    return {
        "results": results,
        "count": len(results),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health-check/{service_id}")
async def get_health_history(
    service_id: str,
    limit: int = Query(default=50, le=500)
):
    """Get health check history for a service"""
    if service_id not in services_cache:
        raise HTTPException(status_code=404, detail="Service not found")

    history = [
        r for r in health_results_cache
        if r.get('service_id') == service_id
    ][-limit:]

    return {
        "service_id": service_id,
        "service_name": services_cache[service_id]['name'],
        "history": history,
        "count": len(history)
    }


@app.post("/health-check/all")
async def run_all_health_checks(background_tasks: BackgroundTasks):
    """Run health checks on all services"""
    services = list(services_cache.values())

    if not services:
        return {"message": "No services registered", "checked": 0}

    results = []
    for service in services:
        result = await perform_health_check(service, "liveness")
        results.append(result)

        # Update service status
        services_cache[service['id']]['status'] = result['status']
        services_cache[service['id']]['last_check'] = result['checked_at']

        health_results_cache.append(result)

    # Trim cache
    while len(health_results_cache) > 1000:
        health_results_cache.pop(0)

    summary = {
        "healthy": sum(1 for r in results if r['status'] == 'healthy'),
        "degraded": sum(1 for r in results if r['status'] == 'degraded'),
        "down": sum(1 for r in results if r['status'] == 'down'),
        "timeout": sum(1 for r in results if r['status'] == 'timeout')
    }

    return {
        "checked": len(results),
        "summary": summary,
        "results": results,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health-check/failing")
async def get_failing_services():
    """List currently failing services"""
    failing = []
    for service in services_cache.values():
        if service.get('status') in ['down', 'degraded', 'timeout']:
            failing.append({
                "service_id": service['id'],
                "name": service['name'],
                "type": service['type'],
                "status": service['status'],
                "last_check": service.get('last_check')
            })

    return {
        "failing_services": failing,
        "count": len(failing),
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# ALERTING ENDPOINTS
# =============================================================================

@app.get("/alerts")
async def list_alerts():
    """List active alerts (from recent health failures)"""
    # For now, alerts are derived from failing services and incidents
    alerts = []
    for incident in incidents_cache.values():
        if incident.get('resolved_at') is None:
            alerts.append({
                "id": incident['id'],
                "type": "incident",
                "severity": incident['severity'],
                "description": incident['description'],
                "service_id": incident['service_id'],
                "started_at": incident['started_at']
            })

    return {
        "alerts": alerts,
        "count": len(alerts),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/alerts/rules")
async def list_alert_rules():
    """List configured alert rules"""
    return {
        "rules": list(alert_rules_cache.values()),
        "count": len(alert_rules_cache),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/alerts/rules")
async def create_alert_rule(rule: AlertRuleCreate):
    """Create a new alert rule"""
    rule_id = generate_id()
    now = datetime.now().isoformat()

    rule_data = {
        "id": rule_id,
        "service_id": rule.service_id,
        "name": rule.name,
        "metric_name": rule.metric_name,
        "comparison": rule.comparison,
        "threshold": rule.threshold,
        "severity": rule.severity,
        "action": rule.action,
        "cooldown_minutes": rule.cooldown_minutes,
        "enabled": rule.enabled,
        "last_triggered": None,
        "metadata": rule.metadata or {},
        "created_at": now
    }

    alert_rules_cache[rule_id] = rule_data

    return rule_data


@app.put("/alerts/rules/{rule_id}")
async def update_alert_rule(rule_id: str, update: AlertRuleUpdate):
    """Update an alert rule"""
    if rule_id not in alert_rules_cache:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    rule = alert_rules_cache[rule_id]
    update_data = update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        rule[key] = value

    alert_rules_cache[rule_id] = rule

    return rule


@app.delete("/alerts/rules/{rule_id}")
async def delete_alert_rule(rule_id: str):
    """Delete an alert rule"""
    if rule_id not in alert_rules_cache:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    rule = alert_rules_cache.pop(rule_id)

    return {"message": f"Alert rule '{rule['name']}' deleted", "rule_id": rule_id}


@app.post("/alerts/rules/{rule_id}/toggle")
async def toggle_alert_rule(rule_id: str):
    """Enable/disable an alert rule"""
    if rule_id not in alert_rules_cache:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    rule = alert_rules_cache[rule_id]
    rule['enabled'] = not rule['enabled']

    return {
        "rule_id": rule_id,
        "name": rule['name'],
        "enabled": rule['enabled']
    }


@app.get("/alerts/history")
async def get_alert_history(
    limit: int = Query(default=50, le=500)
):
    """Get alert history"""
    # Return all incidents as alert history
    history = sorted(
        incidents_cache.values(),
        key=lambda x: x.get('started_at', ''),
        reverse=True
    )[:limit]

    return {
        "history": list(history),
        "count": len(history),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/alerts/acknowledge/{alert_id}")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert"""
    if alert_id in incidents_cache:
        incidents_cache[alert_id]['acknowledged'] = True
        incidents_cache[alert_id]['acknowledged_at'] = datetime.now().isoformat()
        return {"message": f"Alert {alert_id} acknowledged"}

    raise HTTPException(status_code=404, detail="Alert not found")


# =============================================================================
# INCIDENTS ENDPOINTS
# =============================================================================

@app.get("/incidents")
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(default=50, le=500)
):
    """List incidents"""
    incidents = list(incidents_cache.values())

    if status == "open":
        incidents = [i for i in incidents if i.get('resolved_at') is None]
    elif status == "resolved":
        incidents = [i for i in incidents if i.get('resolved_at') is not None]

    if severity:
        incidents = [i for i in incidents if i.get('severity') == severity]

    incidents = sorted(incidents, key=lambda x: x.get('started_at', ''), reverse=True)[:limit]

    return {
        "incidents": incidents,
        "count": len(incidents),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Get incident details"""
    if incident_id not in incidents_cache:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incidents_cache[incident_id]


@app.post("/incidents/{incident_id}/resolve")
async def resolve_incident(incident_id: str, resolution: IncidentResolve):
    """Resolve an incident"""
    if incident_id not in incidents_cache:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident = incidents_cache[incident_id]
    now = datetime.now().isoformat()

    incident['resolved_at'] = now
    incident['resolution_notes'] = resolution.resolution_notes
    incident['auto_resolved'] = resolution.auto_resolved

    await notify_event_bus("server.incident.resolved", {
        "incident_id": incident_id,
        "service_id": incident['service_id'],
        "auto_resolved": resolution.auto_resolved
    })

    # Update ARIA knowledge
    await update_aria_knowledge(
        "infrastructure",
        f"Incident Resolved: {incident['description'][:50]}",
        f"Incident resolved. Notes: {resolution.resolution_notes}",
        "normal"
    )

    return incident


@app.get("/incidents/open")
async def get_open_incidents():
    """Get currently open incidents"""
    open_incidents = [
        i for i in incidents_cache.values()
        if i.get('resolved_at') is None
    ]

    return {
        "incidents": open_incidents,
        "count": len(open_incidents),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/incidents/summary")
async def incidents_summary():
    """Get incident statistics"""
    all_incidents = list(incidents_cache.values())
    open_incidents = [i for i in all_incidents if i.get('resolved_at') is None]

    by_severity = {}
    for incident in all_incidents:
        sev = incident.get('severity', 'unknown')
        by_severity[sev] = by_severity.get(sev, 0) + 1

    return {
        "total": len(all_incidents),
        "open": len(open_incidents),
        "resolved": len(all_incidents) - len(open_incidents),
        "by_severity": by_severity,
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# MAINTENANCE ENDPOINTS
# =============================================================================

@app.get("/maintenance")
async def list_maintenance():
    """List all maintenance windows"""
    return {
        "maintenance_windows": list(maintenance_cache.values()),
        "count": len(maintenance_cache),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/maintenance")
async def schedule_maintenance(maintenance: MaintenanceCreate):
    """Schedule a maintenance window"""
    maintenance_id = generate_id()
    now = datetime.now().isoformat()

    maintenance_data = {
        "id": maintenance_id,
        "service_ids": maintenance.service_ids,
        "scheduled_start": maintenance.scheduled_start,
        "scheduled_end": maintenance.scheduled_end,
        "actual_start": None,
        "actual_end": None,
        "description": maintenance.description,
        "status": "scheduled",
        "suppress_alerts": maintenance.suppress_alerts,
        "pre_check_results": None,
        "post_check_results": None,
        "created_by": maintenance.created_by,
        "created_at": now
    }

    maintenance_cache[maintenance_id] = maintenance_data

    await notify_event_bus("server.maintenance.scheduled", {
        "maintenance_id": maintenance_id,
        "description": maintenance.description,
        "scheduled_start": maintenance.scheduled_start
    })

    # Notify via HERMES
    service_names = []
    for sid in maintenance.service_ids:
        if sid in services_cache:
            service_names.append(services_cache[sid]['name'])

    await notify_hermes(
        f"Maintenance scheduled: {maintenance.description}. Services: {', '.join(service_names)}. Start: {maintenance.scheduled_start}",
        priority="normal"
    )

    return maintenance_data


@app.put("/maintenance/{maintenance_id}")
async def update_maintenance(maintenance_id: str, update: MaintenanceUpdate):
    """Update a maintenance window"""
    if maintenance_id not in maintenance_cache:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    maintenance = maintenance_cache[maintenance_id]
    update_data = update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        maintenance[key] = value

    return maintenance


@app.delete("/maintenance/{maintenance_id}")
async def cancel_maintenance(maintenance_id: str):
    """Cancel a maintenance window"""
    if maintenance_id not in maintenance_cache:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    maintenance = maintenance_cache[maintenance_id]

    if maintenance['status'] == 'in_progress':
        raise HTTPException(status_code=400, detail="Cannot cancel in-progress maintenance")

    maintenance['status'] = 'cancelled'

    await notify_event_bus("server.maintenance.cancelled", {
        "maintenance_id": maintenance_id
    })

    return {"message": "Maintenance window cancelled", "maintenance_id": maintenance_id}


@app.post("/maintenance/{maintenance_id}/start")
async def start_maintenance(maintenance_id: str):
    """Start a maintenance window"""
    if maintenance_id not in maintenance_cache:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    maintenance = maintenance_cache[maintenance_id]
    now = datetime.now().isoformat()

    # Run pre-maintenance health checks
    pre_checks = []
    for service_id in maintenance['service_ids']:
        if service_id in services_cache:
            result = await perform_health_check(services_cache[service_id])
            pre_checks.append(result)

    maintenance['status'] = 'in_progress'
    maintenance['actual_start'] = now
    maintenance['pre_check_results'] = pre_checks

    await notify_event_bus("server.maintenance.started", {
        "maintenance_id": maintenance_id,
        "description": maintenance['description']
    })

    return maintenance


@app.post("/maintenance/{maintenance_id}/end")
async def end_maintenance(maintenance_id: str):
    """End a maintenance window"""
    if maintenance_id not in maintenance_cache:
        raise HTTPException(status_code=404, detail="Maintenance window not found")

    maintenance = maintenance_cache[maintenance_id]
    now = datetime.now().isoformat()

    # Run post-maintenance health checks
    post_checks = []
    for service_id in maintenance['service_ids']:
        if service_id in services_cache:
            result = await perform_health_check(services_cache[service_id])
            post_checks.append(result)

    maintenance['status'] = 'completed'
    maintenance['actual_end'] = now
    maintenance['post_check_results'] = post_checks

    await notify_event_bus("server.maintenance.ended", {
        "maintenance_id": maintenance_id,
        "description": maintenance['description']
    })

    # Update ARIA knowledge
    await update_aria_knowledge(
        "infrastructure",
        f"Maintenance Completed: {maintenance['description'][:50]}",
        f"Maintenance window completed. Duration: {maintenance['actual_start']} to {now}",
        "normal"
    )

    return maintenance


@app.get("/maintenance/active")
async def get_active_maintenance():
    """Get currently active maintenance windows"""
    active = [
        m for m in maintenance_cache.values()
        if m.get('status') == 'in_progress'
    ]

    return {
        "active_maintenance": active,
        "count": len(active),
        "alert_suppression_active": any(m.get('suppress_alerts') for m in active),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/maintenance/upcoming")
async def get_upcoming_maintenance():
    """Get upcoming maintenance windows"""
    upcoming = [
        m for m in maintenance_cache.values()
        if m.get('status') == 'scheduled'
    ]

    # Sort by scheduled start
    upcoming = sorted(upcoming, key=lambda x: x.get('scheduled_start', ''))

    return {
        "upcoming_maintenance": upcoming,
        "count": len(upcoming),
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# AI ANALYSIS ENDPOINTS
# =============================================================================

@app.post("/analyze")
async def analyze_infrastructure(request: AnalysisRequest):
    """AI-powered infrastructure analysis"""
    infra_context = get_infrastructure_summary()

    prompt = f"""Analyze the following infrastructure situation:

{request.context}

"""
    if request.question:
        prompt += f"Specific question: {request.question}\n\n"

    prompt += """Provide:
1. Current status assessment
2. Potential issues or risks
3. Root cause analysis (if applicable)
"""

    if request.include_recommendations:
        prompt += "4. Recommended actions with priority\n"

    messages = [{"role": "user", "content": prompt}]
    analysis = await call_llm(messages, infra_context)

    return {
        "analysis": analysis,
        "infrastructure_summary": infra_context,
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# TIME ENDPOINT
# =============================================================================

@app.get("/time")
async def get_time():
    """Get current time context"""
    return get_time_context()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8207)
