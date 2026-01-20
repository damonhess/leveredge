"""
VARYS - MASTER OF WHISPERS
Port: 8112
Domain: OMNISCIENT

"The spider sits at the center of the web, aware of every vibration."

VARYS transcends all networks. He sees all environments, all agents, all events.
He exists to serve Damon through ARIA - providing intelligence that enables
informed decisions.

Functions:
- Cross-environment visibility (host network mode)
- Docker container monitoring (all networks)
- Multi-source intelligence gathering
- Anomaly detection
- ARIA integration (intelligence on demand)
- Daily intelligence reports
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, date, timedelta
from collections import defaultdict
from pathlib import Path
from enum import Enum
import os
import asyncpg
import httpx
import json
import re
import asyncio
import random
import logging
import docker

# =============================================================================
# CONFIGURATION
# =============================================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VARYS")

# Environment
VARYS_PORT = int(os.getenv("VARYS_PORT", "8112"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8014")
LCIS_URL = os.getenv("LCIS_URL", "http://localhost:8050")
WATCHDOG_URL = os.getenv("WATCHDOG_URL", "http://localhost:8240")
DATABASE_URL = os.getenv("DATABASE_URL")  # DEV database
DATABASE_URL_PROD = os.getenv("DATABASE_URL_PROD")  # PROD database

# =============================================================================
# VARYS' VOICE
# =============================================================================

VARYS_WHISPERS = [
    "The spider feels every vibration in the web.",
    "Secrets are the only currency that never loses value.",
    "I serve the realm. The realm is Damon's vision.",
    "Power resides where men believe it resides.",
    "The storms come and go, the big fish eat the little fish, and I keep on paddling.",
    "Knowledge is not a passion, it is a disease.",
    "The little birds sing, and I listen.",
    "In the game of system monitoring, you watch or you restart.",
    "A mind needs data the way a sword needs a whetstone.",
    "I have many little birds. They tell me things.",
]

def varys_says() -> str:
    """Get a VARYS whisper."""
    return random.choice(VARYS_WHISPERS)

# =============================================================================
# ALL KNOWN AGENT ENDPOINTS
# =============================================================================

AGENT_ENDPOINTS = {
    # Fleet Network - Core Infrastructure
    "event-bus": {"port": 8099, "health": "/health", "category": "core"},
    "chronos": {"port": 8010, "health": "/health", "category": "core"},
    "hades": {"port": 8008, "health": "/health", "category": "core"},
    "hermes": {"port": 8014, "health": "/health", "category": "core"},
    "argus": {"port": 8016, "health": "/health", "category": "core"},
    "aloy": {"port": 8015, "health": "/health", "category": "core"},
    "athena": {"port": 8013, "health": "/health", "category": "core"},
    "apollo": {"port": 8234, "health": "/health", "category": "core"},
    "hephaestus-mcp": {"port": 8011, "health": "/health", "category": "core"},
    "terminal-bridge": {"port": 8251, "health": "/health", "category": "core"},
    "daedalus": {"port": 8026, "health": "/health", "category": "core"},

    # LCIS
    "lcis-librarian": {"port": 8050, "health": "/health", "category": "lcis"},
    "lcis-oracle": {"port": 8052, "health": "/health", "category": "lcis"},

    # Monitoring
    "watchdog": {"port": 8240, "health": "/health", "category": "monitoring"},

    # Council
    "convener": {"port": 8300, "health": "/health", "category": "council"},
    "scribe": {"port": 8301, "health": "/health", "category": "council"},

    # ARIA
    "aria-chat-dev": {"port": 8114, "health": "/health", "category": "aria"},
    "aria-chat-prod": {"port": 8115, "health": "/health", "category": "aria"},
    "aria-omniscience": {"port": 8112, "health": "/health", "category": "aria"},
    "aria-memory": {"port": 8114, "health": "/health", "category": "aria"},

    # Personal Agents
    "gym-coach": {"port": 8230, "health": "/health", "category": "personal"},
    "academic-guide": {"port": 8231, "health": "/health", "category": "personal"},
    "bombadil": {"port": 8232, "health": "/health", "category": "personal"},
    "samwise": {"port": 8233, "health": "/health", "category": "personal"},

    # Business Agents
    "scholar": {"port": 8018, "health": "/health", "category": "business"},
    "chiron": {"port": 8017, "health": "/health", "category": "business"},
    "plutus": {"port": 8207, "health": "/health", "category": "business"},
    "solon": {"port": 8210, "health": "/health", "category": "business"},
    "steward": {"port": 8220, "health": "/health", "category": "business"},

    # Creative Agents
    "muse": {"port": 8030, "health": "/health", "category": "creative"},
    "calliope": {"port": 8031, "health": "/health", "category": "creative"},
    "thalia": {"port": 8032, "health": "/health", "category": "creative"},
    "erato": {"port": 8033, "health": "/health", "category": "creative"},
    "clio": {"port": 8034, "health": "/health", "category": "creative"},

    # Security
    "cerberus": {"port": 8020, "health": "/health", "category": "security"},
    "asclepius": {"port": 8024, "health": "/health", "category": "security"},

    # Supabase (via Kong)
    "supabase-dev": {"port": 8100, "health": "/health", "category": "supabase"},
    "supabase-prod": {"port": 8000, "health": "/health", "category": "supabase"},
}

# =============================================================================
# ANOMALY PATTERNS
# =============================================================================

class AnomalySeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

ANOMALY_PATTERNS = [
    # Health anomalies
    {"name": "agent_death", "pattern": "container.stop", "severity": AnomalySeverity.CRITICAL},
    {"name": "health_degradation", "pattern": "health.latency > 5000ms", "severity": AnomalySeverity.WARNING},
    {"name": "restart_loop", "pattern": "restarts > 3 in 10min", "severity": AnomalySeverity.CRITICAL},

    # Data anomalies
    {"name": "chat_disappearing", "pattern": "conversation.count decreasing", "severity": AnomalySeverity.EMERGENCY},
    {"name": "sync_failure", "pattern": "realtime.subscription.error", "severity": AnomalySeverity.CRITICAL},
    {"name": "db_connection_pool", "pattern": "db.connections > 80%", "severity": AnomalySeverity.WARNING},

    # Deployment anomalies
    {"name": "post_deploy_errors", "pattern": "errors spike after deployment", "severity": AnomalySeverity.CRITICAL},
    {"name": "config_drift", "pattern": "env.mismatch between dev/prod", "severity": AnomalySeverity.WARNING},

    # Security anomalies
    {"name": "auth_failures", "pattern": "auth.failure > 10 in 1min", "severity": AnomalySeverity.CRITICAL},
    {"name": "unusual_access", "pattern": "api.access from unknown IP", "severity": AnomalySeverity.WARNING},
]

# =============================================================================
# MODELS
# =============================================================================

class Anomaly(BaseModel):
    name: str
    severity: AnomalySeverity
    details: Dict[str, Any] = {}
    target: Optional[str] = None
    recommendation: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)

class AgentHealth(BaseModel):
    agent: str
    port: int
    status: str  # healthy, unhealthy, unreachable
    category: str
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    last_check: datetime = Field(default_factory=datetime.utcnow)

class ContainerInfo(BaseModel):
    name: str
    status: str
    health: Optional[str] = None
    networks: List[str] = []
    created: Optional[str] = None
    image: Optional[str] = None
    restart_count: int = 0

class EnvironmentHealth(BaseModel):
    environment: str
    db_healthy: bool
    kong_healthy: bool
    realtime_healthy: bool
    studio_healthy: bool
    details: Dict[str, Any] = {}

class FleetStatus(BaseModel):
    total_agents: int
    healthy: int
    unhealthy: int
    unreachable: int
    by_category: Dict[str, Dict[str, int]] = {}
    agents: List[AgentHealth] = []

# =============================================================================
# APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="VARYS - Master of Whispers",
    description="The spider sits at the center of the web, aware of every vibration.",
    version="3.0.0"
)

# Global state
pool_dev: asyncpg.Pool = None
pool_prod: asyncpg.Pool = None
docker_client: docker.DockerClient = None

# Intelligence cache
intel_cache = {
    "fleet_health": None,
    "fleet_health_time": None,
    "anomalies": [],
    "container_events": [],
}

@app.on_event("startup")
async def startup():
    global pool_dev, pool_prod, docker_client

    # Connect to DEV database
    if DATABASE_URL:
        try:
            pool_dev = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
            logger.info("Connected to DEV database")
        except Exception as e:
            logger.error(f"Failed to connect to DEV database: {e}")

    # Connect to PROD database
    if DATABASE_URL_PROD:
        try:
            pool_prod = await asyncpg.create_pool(DATABASE_URL_PROD, min_size=2, max_size=10)
            logger.info("Connected to PROD database")
        except Exception as e:
            logger.error(f"Failed to connect to PROD database: {e}")

    # Connect to Docker
    try:
        docker_client = docker.from_env()
        logger.info("Connected to Docker daemon")
    except Exception as e:
        logger.error(f"Failed to connect to Docker: {e}")

    logger.info(f"VARYS awakens on port {VARYS_PORT}. The web is ready.")

@app.on_event("shutdown")
async def shutdown():
    if pool_dev:
        await pool_dev.close()
    if pool_prod:
        await pool_prod.close()

# =============================================================================
# HEALTH
# =============================================================================

@app.get("/health")
async def health():
    db_dev_status = "connected" if pool_dev else "disconnected"
    db_prod_status = "connected" if pool_prod else "disconnected"
    docker_status = "connected" if docker_client else "disconnected"

    return {
        "status": "healthy",
        "service": "VARYS - Master of Whispers",
        "port": VARYS_PORT,
        "network_mode": "host",
        "database_dev": db_dev_status,
        "database_prod": db_prod_status,
        "docker": docker_status,
        "varys_says": varys_says()
    }

# =============================================================================
# DOCKER CONTAINER MONITORING (Phase 1)
# =============================================================================

@app.get("/containers")
async def get_all_containers():
    """Get ALL containers across ALL Docker networks."""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker not connected")

    containers = []
    for container in docker_client.containers.list(all=True):
        networks = list(container.attrs.get('NetworkSettings', {}).get('Networks', {}).keys())
        health_status = container.attrs.get('State', {}).get('Health', {}).get('Status')

        containers.append(ContainerInfo(
            name=container.name,
            status=container.status,
            health=health_status,
            networks=networks,
            created=container.attrs.get('Created'),
            image=container.image.tags[0] if container.image.tags else None,
            restart_count=container.attrs.get('RestartCount', 0)
        ))

    return {
        "total": len(containers),
        "containers": [c.dict() for c in containers],
        "varys_says": f"I see {len(containers)} souls in the realm. Nothing escapes my notice."
    }

@app.get("/networks")
async def get_all_networks():
    """Get all Docker networks."""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker not connected")

    networks = []
    for network in docker_client.networks.list():
        containers = [c.name for c in network.containers]
        networks.append({
            "name": network.name,
            "driver": network.attrs.get('Driver'),
            "scope": network.attrs.get('Scope'),
            "containers": containers,
            "container_count": len(containers)
        })

    return {
        "total": len(networks),
        "networks": networks,
        "varys_says": "Every network, every connection - I see them all."
    }

@app.get("/containers/{container_name}")
async def get_container_details(container_name: str):
    """Get detailed info about a specific container."""
    if not docker_client:
        raise HTTPException(status_code=503, detail="Docker not connected")

    try:
        container = docker_client.containers.get(container_name)
        return {
            "name": container.name,
            "status": container.status,
            "health": container.attrs.get('State', {}).get('Health'),
            "networks": list(container.attrs.get('NetworkSettings', {}).get('Networks', {}).keys()),
            "ports": container.attrs.get('NetworkSettings', {}).get('Ports', {}),
            "env": container.attrs.get('Config', {}).get('Env', []),
            "created": container.attrs.get('Created'),
            "image": container.image.tags[0] if container.image.tags else None,
            "restart_count": container.attrs.get('RestartCount', 0),
            "state": container.attrs.get('State', {}),
        }
    except docker.errors.NotFound:
        raise HTTPException(status_code=404, detail=f"Container {container_name} not found")

# =============================================================================
# FLEET HEALTH MONITORING (Phase 2)
# =============================================================================

@app.get("/fleet/status")
async def get_fleet_status() -> FleetStatus:
    """Get health status of ALL known agents."""
    results = []
    by_category: Dict[str, Dict[str, int]] = defaultdict(lambda: {"healthy": 0, "unhealthy": 0, "unreachable": 0})

    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent, config in AGENT_ENDPOINTS.items():
            health = AgentHealth(
                agent=agent,
                port=config["port"],
                status="unknown",
                category=config["category"]
            )

            try:
                url = f"http://localhost:{config['port']}{config['health']}"
                resp = await client.get(url)

                if resp.status_code == 200:
                    health.status = "healthy"
                    health.latency_ms = resp.elapsed.total_seconds() * 1000
                else:
                    health.status = "unhealthy"
                    health.error = f"Status code: {resp.status_code}"
            except httpx.ConnectError:
                health.status = "unreachable"
                health.error = "Connection refused"
            except Exception as e:
                health.status = "unreachable"
                health.error = str(e)

            results.append(health)
            by_category[config["category"]][health.status] += 1

    healthy_count = sum(1 for r in results if r.status == "healthy")
    unhealthy_count = sum(1 for r in results if r.status == "unhealthy")
    unreachable_count = sum(1 for r in results if r.status == "unreachable")

    # Cache result
    intel_cache["fleet_health"] = results
    intel_cache["fleet_health_time"] = datetime.utcnow()

    return FleetStatus(
        total_agents=len(results),
        healthy=healthy_count,
        unhealthy=unhealthy_count,
        unreachable=unreachable_count,
        by_category=dict(by_category),
        agents=results
    )

@app.get("/environment/{env}/health")
async def get_environment_health(env: str) -> EnvironmentHealth:
    """Get health of a specific environment (dev or prod)."""
    if env not in ["dev", "prod"]:
        raise HTTPException(status_code=400, detail="Environment must be 'dev' or 'prod'")

    # Port mappings
    if env == "dev":
        kong_port = 8100
        db_port = 5433
        realtime_port = 54321  # dev realtime
        studio_port = 54323   # dev studio
    else:
        kong_port = 8000
        db_port = 5432
        realtime_port = 54322  # prod realtime
        studio_port = 54324   # prod studio

    details = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        # Check Kong
        try:
            resp = await client.get(f"http://localhost:{kong_port}/health")
            kong_healthy = resp.status_code == 200
            details["kong"] = {"status": "healthy" if kong_healthy else "unhealthy", "port": kong_port}
        except:
            kong_healthy = False
            details["kong"] = {"status": "unreachable", "port": kong_port}

        # Check DB (via container if possible)
        db_healthy = False
        if docker_client:
            try:
                db_container = docker_client.containers.get(f"supabase-db-{env}")
                db_healthy = db_container.status == "running"
                details["database"] = {"status": db_container.status, "port": db_port}
            except:
                details["database"] = {"status": "not found", "port": db_port}

        # Check Realtime
        realtime_healthy = False
        try:
            # Realtime containers have different naming
            if docker_client:
                rt_name = f"realtime-{env}.supabase-realtime"
                rt_container = docker_client.containers.get(rt_name)
                realtime_healthy = rt_container.status == "running"
                details["realtime"] = {"status": rt_container.status}
        except:
            details["realtime"] = {"status": "not found"}

        # Check Studio
        studio_healthy = False
        try:
            if docker_client:
                studio_name = f"supabase-studio-{env}"
                studio_container = docker_client.containers.get(studio_name)
                studio_healthy = studio_container.status == "running"
                details["studio"] = {"status": studio_container.status}
        except:
            details["studio"] = {"status": "not found"}

    return EnvironmentHealth(
        environment=env,
        db_healthy=db_healthy,
        kong_healthy=kong_healthy,
        realtime_healthy=realtime_healthy,
        studio_healthy=studio_healthy,
        details=details
    )

# =============================================================================
# ARIA INTEGRATION (Phase 3)
# =============================================================================

@app.get("/aria/brief")
async def aria_brief():
    """Quick briefing for ARIA - what does she need to know?"""
    # Get fleet health (use cache if recent)
    if intel_cache["fleet_health_time"] and \
       (datetime.utcnow() - intel_cache["fleet_health_time"]).seconds < 60:
        fleet = intel_cache["fleet_health"]
    else:
        status = await get_fleet_status()
        fleet = status.agents

    healthy = sum(1 for a in fleet if a.status == "healthy")
    unhealthy = sum(1 for a in fleet if a.status == "unhealthy")
    unreachable = sum(1 for a in fleet if a.status == "unreachable")

    # Check environments
    dev_health = await get_environment_health("dev")
    prod_health = await get_environment_health("prod")

    # Get recent anomalies
    recent_anomalies = [a for a in intel_cache.get("anomalies", [])
                       if (datetime.utcnow() - a.get("detected_at", datetime.utcnow())).seconds < 3600]

    # Determine status
    if unhealthy > 2 or len(recent_anomalies) > 0:
        overall_status = "NEEDS_ATTENTION"
    elif unreachable > 5:
        overall_status = "DEGRADED"
    else:
        overall_status = "HEALTHY"

    return {
        "overall_status": overall_status,
        "fleet_summary": {
            "total": len(fleet),
            "healthy": healthy,
            "unhealthy": unhealthy,
            "unreachable": unreachable,
            "unhealthy_agents": [a.agent for a in fleet if a.status == "unhealthy"],
        },
        "environment_status": {
            "dev": {
                "healthy": dev_health.db_healthy and dev_health.kong_healthy,
                "components": dev_health.details
            },
            "prod": {
                "healthy": prod_health.db_healthy and prod_health.kong_healthy,
                "components": prod_health.details
            }
        },
        "recent_anomalies": recent_anomalies[:5],
        "generated_at": datetime.utcnow().isoformat(),
        "varys_says": varys_says()
    }

@app.get("/aria/intel/{topic}")
async def aria_intel(topic: str):
    """Deep intel on a specific topic for ARIA."""
    intel_gatherers = {
        "agents": get_agent_intel,
        "containers": get_container_intel,
        "databases": get_database_intel,
        "errors": get_error_intel,
        "performance": get_performance_intel,
    }

    if topic not in intel_gatherers:
        return {"error": f"Unknown topic: {topic}", "available": list(intel_gatherers.keys())}

    return await intel_gatherers[topic]()

async def get_agent_intel():
    """Deep intel on agent status."""
    status = await get_fleet_status()

    # Group by category
    by_category = defaultdict(list)
    for agent in status.agents:
        by_category[agent.category].append({
            "name": agent.agent,
            "status": agent.status,
            "latency_ms": agent.latency_ms,
            "error": agent.error
        })

    return {
        "topic": "agents",
        "summary": f"{status.healthy} healthy, {status.unhealthy} unhealthy, {status.unreachable} unreachable",
        "by_category": dict(by_category),
        "critical_agents": [a for a in status.agents if a.status != "healthy" and a.category == "core"],
        "varys_says": "My little birds have reported on every agent in the realm."
    }

async def get_container_intel():
    """Deep intel on Docker containers."""
    containers = await get_all_containers()

    # Group by status
    by_status = defaultdict(list)
    for c in containers["containers"]:
        by_status[c["status"]].append(c["name"])

    # Find containers with restart issues
    restart_issues = [c for c in containers["containers"] if c["restart_count"] > 2]

    return {
        "topic": "containers",
        "total": containers["total"],
        "by_status": dict(by_status),
        "restart_issues": restart_issues,
        "varys_says": "Every container, every soul - I count them all."
    }

async def get_database_intel():
    """Deep intel on database connections."""
    result = {
        "topic": "databases",
        "dev": {"connected": pool_dev is not None},
        "prod": {"connected": pool_prod is not None},
    }

    if pool_dev:
        try:
            async with pool_dev.acquire() as conn:
                # Get table counts
                counts = await conn.fetch("""
                    SELECT relname as table, n_live_tup as rows
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC LIMIT 10
                """)
                result["dev"]["top_tables"] = [dict(r) for r in counts]
        except Exception as e:
            result["dev"]["error"] = str(e)

    if pool_prod:
        try:
            async with pool_prod.acquire() as conn:
                counts = await conn.fetch("""
                    SELECT relname as table, n_live_tup as rows
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                    ORDER BY n_live_tup DESC LIMIT 10
                """)
                result["prod"]["top_tables"] = [dict(r) for r in counts]
        except Exception as e:
            result["prod"]["error"] = str(e)

    result["varys_says"] = "The databases hold many secrets. I know them all."
    return result

async def get_error_intel():
    """Get recent errors from LCIS."""
    result = {"topic": "errors", "recent_errors": []}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LCIS_URL}/lessons", params={
                "type": "error",
                "limit": 20
            })
            if resp.status_code == 200:
                result["recent_errors"] = resp.json()
    except Exception as e:
        result["lcis_error"] = str(e)

    result["varys_says"] = "Errors are like whispers - they tell us what went wrong."
    return result

async def get_performance_intel():
    """Get performance metrics."""
    status = await get_fleet_status()

    # Calculate latency stats
    latencies = [a.latency_ms for a in status.agents if a.latency_ms]

    return {
        "topic": "performance",
        "agent_latencies": {
            "min_ms": min(latencies) if latencies else None,
            "max_ms": max(latencies) if latencies else None,
            "avg_ms": sum(latencies) / len(latencies) if latencies else None,
        },
        "slow_agents": [
            {"agent": a.agent, "latency_ms": a.latency_ms}
            for a in status.agents if a.latency_ms and a.latency_ms > 1000
        ],
        "varys_says": "Speed is power. Slowness is weakness."
    }

# =============================================================================
# ANOMALY DETECTION (Phase 4)
# =============================================================================

@app.get("/anomalies")
async def get_anomalies(hours: int = 24):
    """Get detected anomalies."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    recent = [a for a in intel_cache.get("anomalies", [])
              if a.get("detected_at", datetime.utcnow()) > cutoff]

    return {
        "anomalies": recent,
        "total": len(recent),
        "varys_says": "I watch for patterns in the chaos. These anomalies concern me."
    }

@app.post("/anomalies/detect")
async def detect_anomalies():
    """Run anomaly detection checks."""
    detected = []

    # Check for unhealthy agents
    status = await get_fleet_status()
    for agent in status.agents:
        if agent.status == "unhealthy":
            detected.append({
                "name": "agent_unhealthy",
                "severity": AnomalySeverity.WARNING.value,
                "target": agent.agent,
                "details": {"error": agent.error},
                "recommendation": f"Investigate {agent.agent} on port {agent.port}",
                "detected_at": datetime.utcnow().isoformat()
            })
        elif agent.status == "unreachable" and agent.category == "core":
            detected.append({
                "name": "core_agent_down",
                "severity": AnomalySeverity.CRITICAL.value,
                "target": agent.agent,
                "details": {"error": agent.error},
                "recommendation": f"URGENT: Restart {agent.agent} immediately",
                "detected_at": datetime.utcnow().isoformat()
            })

    # Check for container restart loops
    if docker_client:
        for container in docker_client.containers.list(all=True):
            restart_count = container.attrs.get('RestartCount', 0)
            if restart_count > 3:
                detected.append({
                    "name": "restart_loop",
                    "severity": AnomalySeverity.CRITICAL.value,
                    "target": container.name,
                    "details": {"restart_count": restart_count},
                    "recommendation": f"Check logs for {container.name}: docker logs {container.name}",
                    "detected_at": datetime.utcnow().isoformat()
                })

    # Check environment health
    for env in ["dev", "prod"]:
        env_health = await get_environment_health(env)
        if not env_health.db_healthy:
            detected.append({
                "name": "database_down",
                "severity": AnomalySeverity.EMERGENCY.value,
                "target": f"supabase-db-{env}",
                "details": env_health.details.get("database", {}),
                "recommendation": f"Check {env.upper()} database container immediately",
                "detected_at": datetime.utcnow().isoformat()
            })
        if not env_health.kong_healthy:
            detected.append({
                "name": "kong_down",
                "severity": AnomalySeverity.CRITICAL.value,
                "target": f"kong-{env}",
                "details": env_health.details.get("kong", {}),
                "recommendation": f"Check Kong gateway for {env.upper()}",
                "detected_at": datetime.utcnow().isoformat()
            })

    # Store in cache
    intel_cache["anomalies"].extend(detected)
    # Keep only last 100
    intel_cache["anomalies"] = intel_cache["anomalies"][-100:]

    # Alert ARIA/HERMES if critical anomalies
    critical = [a for a in detected if a["severity"] in [AnomalySeverity.CRITICAL.value, AnomalySeverity.EMERGENCY.value]]
    if critical:
        await alert_hermes(critical)

    return {
        "detected": len(detected),
        "anomalies": detected,
        "varys_says": f"I've found {len(detected)} vibrations in the web that concern me." if detected else "The web is quiet. For now."
    }

async def alert_hermes(anomalies: List[Dict]):
    """Send alert to HERMES."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            for anomaly in anomalies[:3]:  # Limit to 3 alerts
                await client.post(
                    f"{HERMES_URL}/alert",
                    json={
                        "severity": anomaly["severity"],
                        "source": "VARYS",
                        "title": f"VARYS: {anomaly['name']}",
                        "message": f"Target: {anomaly.get('target', 'unknown')}. {anomaly.get('recommendation', '')}",
                        "target": anomaly.get("target"),
                        "details": anomaly.get("details", {})
                    }
                )
    except Exception as e:
        logger.error(f"Failed to alert HERMES: {e}")

# =============================================================================
# DAILY INTELLIGENCE REPORT (Phase 5)
# =============================================================================

@app.get("/report/daily")
async def daily_report():
    """VARYS' daily intelligence report."""
    # Fleet status
    fleet = await get_fleet_status()

    # Environment health
    dev_health = await get_environment_health("dev")
    prod_health = await get_environment_health("prod")

    # Anomalies
    anomalies_24h = [a for a in intel_cache.get("anomalies", [])
                    if isinstance(a.get("detected_at"), str) and
                    datetime.fromisoformat(a["detected_at"]) > datetime.utcnow() - timedelta(hours=24)]

    # Generate summary
    if fleet.unhealthy > 0 or len(anomalies_24h) > 5:
        assessment = "NEEDS_ATTENTION"
        summary = f"The fleet shows signs of strain. {fleet.unhealthy} agents unhealthy, {len(anomalies_24h)} anomalies detected."
    elif fleet.unreachable > 3:
        assessment = "DEGRADED"
        summary = f"Several agents have gone dark. {fleet.unreachable} unreachable."
    else:
        assessment = "HEALTHY"
        summary = f"The realm is at peace. {fleet.healthy} agents healthy and reporting."

    return {
        "report_date": date.today().isoformat(),
        "report_time": datetime.utcnow().isoformat(),

        "executive_summary": {
            "assessment": assessment,
            "summary": summary
        },

        "fleet_status": {
            "total_agents": fleet.total_agents,
            "healthy": fleet.healthy,
            "unhealthy": fleet.unhealthy,
            "unreachable": fleet.unreachable,
            "by_category": fleet.by_category
        },

        "environment_health": {
            "dev": {
                "overall": "healthy" if (dev_health.db_healthy and dev_health.kong_healthy) else "degraded",
                "components": dev_health.details
            },
            "prod": {
                "overall": "healthy" if (prod_health.db_healthy and prod_health.kong_healthy) else "degraded",
                "components": prod_health.details
            }
        },

        "anomalies_24h": {
            "total": len(anomalies_24h),
            "critical": len([a for a in anomalies_24h if a.get("severity") in ["critical", "emergency"]]),
            "items": anomalies_24h[:10]
        },

        "unhealthy_agents": [
            {"agent": a.agent, "error": a.error, "port": a.port}
            for a in fleet.agents if a.status == "unhealthy"
        ],

        "recommendations": generate_recommendations(fleet, anomalies_24h),

        "varys_says": "Knowledge is power. Here is what I know."
    }

def generate_recommendations(fleet: FleetStatus, anomalies: List) -> List[str]:
    """Generate actionable recommendations."""
    recs = []

    # Core agent issues
    core_issues = [a for a in fleet.agents if a.category == "core" and a.status != "healthy"]
    if core_issues:
        recs.append(f"PRIORITY: {len(core_issues)} core agents need attention: {', '.join(a.agent for a in core_issues)}")

    # High anomaly count
    if len(anomalies) > 10:
        recs.append("High anomaly count suggests systemic issues. Review logs across the fleet.")

    # Restart loops
    restart_anomalies = [a for a in anomalies if a.get("name") == "restart_loop"]
    if restart_anomalies:
        recs.append(f"Restart loops detected in: {', '.join(a.get('target', 'unknown') for a in restart_anomalies)}")

    if not recs:
        recs.append("No immediate actions required. The realm is stable.")

    return recs

# =============================================================================
# LEGACY ENDPOINTS (Backward Compatibility)
# =============================================================================

@app.get("/fleet")
async def get_fleet():
    """Get full fleet registry (legacy endpoint)."""
    return {"fleet": AGENT_ENDPOINTS, "source": "config"}

@app.get("/briefing")
async def briefing():
    """Get intelligence briefing (legacy endpoint)."""
    return await aria_brief()

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=VARYS_PORT)
