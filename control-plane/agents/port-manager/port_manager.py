#!/usr/bin/env python3
"""
PORT MANAGER - Port Allocation & Registry Agent
Port: 8021

Central registry for all port allocations across LeverEdge infrastructure.
Detects conflicts, manages dynamic port assignment, ensures no service collisions.
Named after the Harbor Master - managing the ports where all traffic flows.

This is a UTILITY agent - no LLM required, just data management.

TEAM INTEGRATION:
- Time-aware (knows current date)
- Communicates with other agents via Event Bus
- Provides port info to CERBERUS for security monitoring
- Updates ARGUS with port metrics
- Supports ATLAS during orchestration
"""

import os
import sys
import socket
import json
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
import httpx

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')

# =============================================================================
# CONFIGURATION
# =============================================================================

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Agent info
AGENT_NAME = "PORT-MANAGER"
AGENT_PORT = 8021
AGENT_VERSION = "1.0.0"

# Port ranges as defined in spec
PORT_RANGES = {
    "n8n": {"start": 5678, "end": 5699, "description": "n8n instances"},
    "infrastructure": {"start": 8000, "end": 8019, "description": "Core infrastructure (Supabase, GAIA, CHRONOS)"},
    "control_plane": {"start": 8020, "end": 8049, "description": "Control plane agents"},
    "data_plane": {"start": 8050, "end": 8079, "description": "Data plane services"},
    "integration": {"start": 8080, "end": 8099, "description": "Integration services (Event Bus)"},
    "personal": {"start": 8100, "end": 8199, "description": "Personal life agents"},
    "business": {"start": 8200, "end": 8299, "description": "Business agents"},
    "client": {"start": 8300, "end": 8399, "description": "Client deployments"},
    "development": {"start": 3000, "end": 3999, "description": "Development/testing (temporary)"},
}

# In-memory port registry (will be backed by database in future)
# Format: {port: {service_name, agent_name, environment, status, ...}}
_port_registry: Dict[int, Dict[str, Any]] = {}

# Seed data for known port allocations
SEED_PORTS = [
    # n8n
    {"port": 5678, "service_name": "n8n-prod", "agent_name": None, "environment": "prod", "category": "n8n"},
    {"port": 5679, "service_name": "n8n-control", "agent_name": None, "environment": "prod", "category": "n8n"},
    {"port": 5680, "service_name": "n8n-dev", "agent_name": None, "environment": "dev", "category": "n8n"},
    # Infrastructure
    {"port": 8000, "service_name": "supabase-kong", "agent_name": None, "environment": "prod", "category": "infrastructure"},
    {"port": 8007, "service_name": "atlas", "agent_name": "ATLAS", "environment": "prod", "category": "infrastructure"},
    {"port": 8008, "service_name": "hades", "agent_name": "HADES", "environment": "prod", "category": "infrastructure"},
    {"port": 8009, "service_name": "argus", "agent_name": "ARGUS", "environment": "prod", "category": "infrastructure"},
    {"port": 8010, "service_name": "chronos", "agent_name": "CHRONOS", "environment": "prod", "category": "infrastructure"},
    {"port": 8011, "service_name": "hephaestus", "agent_name": "HEPHAESTUS", "environment": "prod", "category": "infrastructure"},
    {"port": 8012, "service_name": "aegis", "agent_name": "AEGIS", "environment": "prod", "category": "infrastructure"},
    {"port": 8013, "service_name": "athena", "agent_name": "ATHENA", "environment": "prod", "category": "infrastructure"},
    {"port": 8014, "service_name": "hermes", "agent_name": "HERMES", "environment": "prod", "category": "infrastructure"},
    {"port": 8015, "service_name": "aloy", "agent_name": "ALOY", "environment": "prod", "category": "infrastructure"},
    {"port": 8016, "service_name": "argus-metrics", "agent_name": "ARGUS", "environment": "prod", "category": "infrastructure"},
    {"port": 8017, "service_name": "chiron", "agent_name": "CHIRON", "environment": "prod", "category": "infrastructure"},
    {"port": 8018, "service_name": "scholar", "agent_name": "SCHOLAR", "environment": "prod", "category": "infrastructure"},
    # Control plane
    {"port": 8020, "service_name": "cerberus", "agent_name": "CERBERUS", "environment": "prod", "category": "control_plane", "status": "planned"},
    {"port": 8021, "service_name": "port-manager", "agent_name": "PORT-MANAGER", "environment": "prod", "category": "control_plane"},
    # Integration
    {"port": 8099, "service_name": "event-bus", "agent_name": None, "environment": "prod", "category": "integration"},
]


# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize registry on startup"""
    # Seed the in-memory registry
    for port_data in SEED_PORTS:
        _port_registry[port_data["port"]] = {
            "port": port_data["port"],
            "service_name": port_data["service_name"],
            "agent_name": port_data.get("agent_name"),
            "environment": port_data.get("environment", "prod"),
            "category": port_data.get("category", "unknown"),
            "protocol": port_data.get("protocol", "tcp"),
            "status": port_data.get("status", "active"),
            "description": port_data.get("description"),
            "host": port_data.get("host", "localhost"),
            "allocated_at": datetime.utcnow().isoformat(),
            "health_status": "unknown",
            "metadata": {}
        }
    print(f"[{AGENT_NAME}] Initialized with {len(_port_registry)} port allocations")

    yield

    print(f"[{AGENT_NAME}] Shutting down")


# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="PORT MANAGER",
    description="Port Allocation & Registry Agent for LeverEdge",
    version=AGENT_VERSION,
    lifespan=lifespan
)


# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    return {
        "current_datetime": now.isoformat(),
        "current_date": now.date().isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
    }


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class PortRegistration(BaseModel):
    """Request model for registering a port"""
    port: int = Field(..., ge=1, le=65535, description="Port number to register")
    service_name: str = Field(..., min_length=1, description="Name of the service")
    agent_name: Optional[str] = Field(None, description="Name of the agent using this port")
    environment: str = Field("prod", description="Environment: dev, prod, test")
    category: str = Field("unknown", description="Port category for organization")
    protocol: str = Field("tcp", description="Protocol: tcp, udp, both")
    description: Optional[str] = None
    host: str = Field("localhost", description="Host for remote services")
    expires_at: Optional[str] = Field(None, description="ISO timestamp for temporary allocations")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PortUpdate(BaseModel):
    """Request model for updating a port registration"""
    service_name: Optional[str] = None
    agent_name: Optional[str] = None
    environment: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PortCheckRequest(BaseModel):
    """Request to check port availability"""
    ports: List[int] = Field(..., description="List of ports to check")


class AllocationRequest(BaseModel):
    """Request for dynamic port allocation"""
    category: str = Field(..., description="Category to allocate from")
    service_name: str = Field(..., description="Service name")
    agent_name: Optional[str] = None
    environment: str = Field("prod")
    count: int = Field(1, ge=1, le=10, description="Number of ports to allocate")


class ReservationRequest(BaseModel):
    """Request to reserve a port for future use"""
    port: int = Field(..., ge=1, le=65535)
    service_name: str
    duration_hours: int = Field(24, ge=1, le=720, description="Reservation duration in hours")


class ScanResult(BaseModel):
    """Result of a port scan"""
    port: int
    is_open: bool
    is_registered: bool
    service_name: Optional[str] = None


# =============================================================================
# EVENT BUS INTEGRATION
# =============================================================================

async def publish_event(event_type: str, details: dict = None):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": AGENT_NAME,
                    "event_type": event_type,
                    "details": details or {},
                    "timestamp": time_ctx['current_datetime']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"[{AGENT_NAME}] Event bus publish failed: {e}")


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_category_for_port(port: int) -> Optional[str]:
    """Determine which category a port belongs to"""
    for category, range_info in PORT_RANGES.items():
        if range_info["start"] <= port <= range_info["end"]:
            return category
    return None


def is_port_in_use(port: int, host: str = "localhost") -> bool:
    """Check if a port is currently listening on the system"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            return result == 0
    except Exception:
        return False


def find_available_ports(category: str, count: int = 1) -> List[int]:
    """Find available ports in a category range"""
    if category not in PORT_RANGES:
        return []

    range_info = PORT_RANGES[category]
    available = []

    for port in range(range_info["start"], range_info["end"] + 1):
        if port not in _port_registry:
            # Also check if actually in use
            if not is_port_in_use(port):
                available.append(port)
                if len(available) >= count:
                    break

    return available


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check endpoint"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": AGENT_NAME,
        "role": "Port Allocation & Registry",
        "port": AGENT_PORT,
        "version": AGENT_VERSION,
        "current_time": time_ctx['current_datetime'],
        "registered_ports": len(_port_registry),
        "llm_required": False
    }


@app.get("/status")
async def status():
    """Get port allocation overview"""
    time_ctx = get_time_context()

    # Count by category
    category_counts = {}
    for port_data in _port_registry.values():
        cat = port_data.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Count by status
    status_counts = {}
    for port_data in _port_registry.values():
        st = port_data.get("status", "active")
        status_counts[st] = status_counts.get(st, 0) + 1

    # Count by environment
    env_counts = {}
    for port_data in _port_registry.values():
        env = port_data.get("environment", "unknown")
        env_counts[env] = env_counts.get(env, 0) + 1

    return {
        "agent": AGENT_NAME,
        "timestamp": time_ctx['current_datetime'],
        "total_registered_ports": len(_port_registry),
        "by_category": category_counts,
        "by_status": status_counts,
        "by_environment": env_counts,
        "port_ranges": PORT_RANGES
    }


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics (stub for ARGUS integration)"""
    # TODO: Implement Prometheus format metrics
    return {
        "registered_ports_total": len(_port_registry),
        "active_ports": sum(1 for p in _port_registry.values() if p.get("status") == "active"),
        "reserved_ports": sum(1 for p in _port_registry.values() if p.get("status") == "reserved"),
        "conflicts_detected": 0,  # Placeholder
        "health_checks_total": 0  # Placeholder
    }


# =============================================================================
# PORT REGISTRY ENDPOINTS
# =============================================================================

@app.get("/ports")
async def list_ports(
    category: Optional[str] = Query(None, description="Filter by category"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, description="Filter by status"),
    agent: Optional[str] = Query(None, description="Filter by agent name")
):
    """List all registered ports with optional filters"""
    result = list(_port_registry.values())

    if category:
        result = [p for p in result if p.get("category") == category]
    if environment:
        result = [p for p in result if p.get("environment") == environment]
    if status:
        result = [p for p in result if p.get("status") == status]
    if agent:
        result = [p for p in result if p.get("agent_name") == agent]

    return {
        "count": len(result),
        "ports": sorted(result, key=lambda x: x["port"])
    }


@app.get("/ports/{port}")
async def get_port(port: int):
    """Get details for a specific port"""
    if port not in _port_registry:
        raise HTTPException(status_code=404, detail=f"Port {port} not registered")

    port_data = _port_registry[port]
    # Add live status
    port_data["is_listening"] = is_port_in_use(port, port_data.get("host", "localhost"))

    return port_data


@app.post("/ports/register")
async def register_port(req: PortRegistration):
    """Register a new port allocation"""
    if req.port in _port_registry:
        existing = _port_registry[req.port]
        raise HTTPException(
            status_code=409,
            detail=f"Port {req.port} already registered to {existing['service_name']}"
        )

    # Auto-detect category if not provided
    category = req.category
    if category == "unknown":
        detected = get_category_for_port(req.port)
        if detected:
            category = detected

    port_data = {
        "port": req.port,
        "service_name": req.service_name,
        "agent_name": req.agent_name,
        "environment": req.environment,
        "category": category,
        "protocol": req.protocol,
        "status": "active",
        "description": req.description,
        "host": req.host,
        "allocated_at": datetime.utcnow().isoformat(),
        "expires_at": req.expires_at,
        "health_status": "unknown",
        "metadata": req.metadata
    }

    _port_registry[req.port] = port_data

    # Publish event
    await publish_event("ports.allocated", {
        "port": req.port,
        "service": req.service_name,
        "agent": req.agent_name,
        "category": category
    })

    return {
        "message": f"Port {req.port} registered successfully",
        "port": port_data
    }


@app.put("/ports/{port}")
async def update_port(port: int, req: PortUpdate):
    """Update port registration"""
    if port not in _port_registry:
        raise HTTPException(status_code=404, detail=f"Port {port} not registered")

    port_data = _port_registry[port]

    if req.service_name is not None:
        port_data["service_name"] = req.service_name
    if req.agent_name is not None:
        port_data["agent_name"] = req.agent_name
    if req.environment is not None:
        port_data["environment"] = req.environment
    if req.status is not None:
        port_data["status"] = req.status
    if req.description is not None:
        port_data["description"] = req.description
    if req.metadata is not None:
        port_data["metadata"].update(req.metadata)

    port_data["updated_at"] = datetime.utcnow().isoformat()

    return {
        "message": f"Port {port} updated",
        "port": port_data
    }


@app.delete("/ports/{port}")
async def release_port(port: int):
    """Release a port allocation"""
    if port not in _port_registry:
        raise HTTPException(status_code=404, detail=f"Port {port} not registered")

    released = _port_registry.pop(port)

    await publish_event("ports.released", {
        "port": port,
        "service": released["service_name"],
        "agent": released.get("agent_name")
    })

    return {
        "message": f"Port {port} released",
        "released": released
    }


@app.get("/ports/service/{name}")
async def find_by_service(name: str):
    """Find port by service name"""
    for port, data in _port_registry.items():
        if data["service_name"].lower() == name.lower():
            data["is_listening"] = is_port_in_use(port, data.get("host", "localhost"))
            return data

    raise HTTPException(status_code=404, detail=f"Service '{name}' not found")


@app.get("/ports/agent/{name}")
async def find_by_agent(name: str):
    """List all ports for an agent"""
    result = []
    for port, data in _port_registry.items():
        if data.get("agent_name", "").upper() == name.upper():
            data["is_listening"] = is_port_in_use(port, data.get("host", "localhost"))
            result.append(data)

    return {
        "agent": name,
        "count": len(result),
        "ports": sorted(result, key=lambda x: x["port"])
    }


@app.get("/ports/available/{category}")
async def list_available(category: str, count: int = Query(5, ge=1, le=50)):
    """List available ports in a category range"""
    if category not in PORT_RANGES:
        raise HTTPException(status_code=404, detail=f"Unknown category '{category}'")

    available = find_available_ports(category, count)

    return {
        "category": category,
        "range": PORT_RANGES[category],
        "available_count": len(available),
        "available_ports": available
    }


# =============================================================================
# CONFLICT DETECTION ENDPOINTS
# =============================================================================

@app.post("/check")
async def check_ports(req: PortCheckRequest):
    """Check if port(s) are available"""
    results = []

    for port in req.ports:
        is_registered = port in _port_registry
        is_open = is_port_in_use(port)

        result = {
            "port": port,
            "available": not is_registered and not is_open,
            "is_registered": is_registered,
            "is_listening": is_open,
            "registered_to": _port_registry.get(port, {}).get("service_name") if is_registered else None
        }
        results.append(result)

    return {
        "checked": len(req.ports),
        "all_available": all(r["available"] for r in results),
        "results": results
    }


@app.post("/scan")
async def scan_ports(
    start: int = Query(8000, ge=1, le=65535),
    end: int = Query(8100, ge=1, le=65535)
):
    """Scan system for listening ports in a range"""
    if end < start:
        raise HTTPException(status_code=400, detail="end must be >= start")
    if end - start > 1000:
        raise HTTPException(status_code=400, detail="Range too large (max 1000 ports)")

    results: List[ScanResult] = []

    for port in range(start, end + 1):
        is_open = is_port_in_use(port)
        is_registered = port in _port_registry
        service_name = _port_registry.get(port, {}).get("service_name") if is_registered else None

        if is_open or is_registered:
            results.append(ScanResult(
                port=port,
                is_open=is_open,
                is_registered=is_registered,
                service_name=service_name
            ))

    return {
        "range": {"start": start, "end": end},
        "scanned": end - start + 1,
        "found": len(results),
        "results": [r.model_dump() for r in results]
    }


@app.get("/conflicts")
async def get_conflicts():
    """List detected port conflicts (stub - will check live vs registered)"""
    conflicts = []

    for port, data in _port_registry.items():
        is_listening = is_port_in_use(port, data.get("host", "localhost"))

        # Conflict: registered as active but not listening
        if data.get("status") == "active" and not is_listening:
            conflicts.append({
                "type": "zombie",
                "port": port,
                "service": data["service_name"],
                "description": "Registered as active but not listening"
            })

    # Also check for unregistered listening ports in known ranges
    for category, range_info in PORT_RANGES.items():
        for port in range(range_info["start"], min(range_info["end"] + 1, range_info["start"] + 100)):
            if port not in _port_registry and is_port_in_use(port):
                conflicts.append({
                    "type": "orphan",
                    "port": port,
                    "category": category,
                    "description": "Listening but not registered"
                })

    if conflicts:
        await publish_event("ports.conflict.detected", {
            "count": len(conflicts),
            "types": list(set(c["type"] for c in conflicts))
        })

    return {
        "conflict_count": len(conflicts),
        "conflicts": conflicts
    }


@app.post("/validate/compose")
async def validate_compose(compose_content: Dict[str, Any]):
    """Validate docker-compose file for port conflicts (stub)"""
    # TODO: Parse docker-compose format and check ports
    return {
        "valid": True,
        "message": "Docker compose validation not yet implemented",
        "conflicts": []
    }


# =============================================================================
# DYNAMIC ALLOCATION ENDPOINTS
# =============================================================================

@app.post("/allocate")
async def allocate_port(req: AllocationRequest):
    """Request port(s) from a category range"""
    if req.category not in PORT_RANGES:
        raise HTTPException(status_code=404, detail=f"Unknown category '{req.category}'")

    available = find_available_ports(req.category, req.count)

    if len(available) < req.count:
        raise HTTPException(
            status_code=409,
            detail=f"Only {len(available)} ports available in {req.category} range, requested {req.count}"
        )

    allocated = []
    for port in available:
        port_data = {
            "port": port,
            "service_name": req.service_name if req.count == 1 else f"{req.service_name}-{port}",
            "agent_name": req.agent_name,
            "environment": req.environment,
            "category": req.category,
            "protocol": "tcp",
            "status": "active",
            "description": f"Auto-allocated from {req.category} range",
            "host": "localhost",
            "allocated_at": datetime.utcnow().isoformat(),
            "health_status": "unknown",
            "metadata": {"auto_allocated": True}
        }
        _port_registry[port] = port_data
        allocated.append(port_data)

    await publish_event("ports.allocated", {
        "ports": [p["port"] for p in allocated],
        "service": req.service_name,
        "category": req.category,
        "auto_allocated": True
    })

    return {
        "message": f"Allocated {len(allocated)} port(s)",
        "allocated": allocated
    }


@app.post("/reserve")
async def reserve_port(req: ReservationRequest):
    """Reserve a port for future use"""
    if req.port in _port_registry:
        existing = _port_registry[req.port]
        raise HTTPException(
            status_code=409,
            detail=f"Port {req.port} already registered to {existing['service_name']}"
        )

    from datetime import timedelta
    expires_at = datetime.utcnow() + timedelta(hours=req.duration_hours)

    port_data = {
        "port": req.port,
        "service_name": req.service_name,
        "agent_name": None,
        "environment": "pending",
        "category": get_category_for_port(req.port) or "unknown",
        "protocol": "tcp",
        "status": "reserved",
        "description": f"Reserved for {req.duration_hours} hours",
        "host": "localhost",
        "allocated_at": datetime.utcnow().isoformat(),
        "expires_at": expires_at.isoformat(),
        "health_status": "unknown",
        "metadata": {"reservation": True}
    }

    _port_registry[req.port] = port_data

    return {
        "message": f"Port {req.port} reserved until {expires_at.isoformat()}",
        "reservation": port_data
    }


@app.delete("/reserve/{port}")
async def cancel_reservation(port: int):
    """Cancel a port reservation"""
    if port not in _port_registry:
        raise HTTPException(status_code=404, detail=f"Port {port} not found")

    port_data = _port_registry[port]
    if port_data.get("status") != "reserved":
        raise HTTPException(status_code=400, detail=f"Port {port} is not reserved (status: {port_data.get('status')})")

    released = _port_registry.pop(port)

    return {
        "message": f"Reservation for port {port} cancelled",
        "released": released
    }


@app.post("/bulk-allocate")
async def bulk_allocate(requests: List[AllocationRequest]):
    """Allocate multiple ports for multi-container deployments"""
    results = []
    errors = []

    for req in requests:
        try:
            if req.category not in PORT_RANGES:
                errors.append({"service": req.service_name, "error": f"Unknown category '{req.category}'"})
                continue

            available = find_available_ports(req.category, req.count)
            if len(available) < req.count:
                errors.append({
                    "service": req.service_name,
                    "error": f"Only {len(available)} ports available"
                })
                continue

            for port in available:
                port_data = {
                    "port": port,
                    "service_name": req.service_name if req.count == 1 else f"{req.service_name}-{port}",
                    "agent_name": req.agent_name,
                    "environment": req.environment,
                    "category": req.category,
                    "protocol": "tcp",
                    "status": "active",
                    "host": "localhost",
                    "allocated_at": datetime.utcnow().isoformat(),
                    "health_status": "unknown",
                    "metadata": {"bulk_allocated": True}
                }
                _port_registry[port] = port_data
                results.append(port_data)
        except Exception as e:
            errors.append({"service": req.service_name, "error": str(e)})

    return {
        "allocated_count": len(results),
        "error_count": len(errors),
        "allocated": results,
        "errors": errors
    }


# =============================================================================
# HEALTH MONITORING ENDPOINTS
# =============================================================================

@app.get("/health-report")
async def health_report():
    """Full health report of all registered ports"""
    report = {
        "timestamp": get_time_context()["current_datetime"],
        "total_ports": len(_port_registry),
        "healthy": 0,
        "unhealthy": 0,
        "unknown": 0,
        "details": []
    }

    for port, data in sorted(_port_registry.items()):
        is_listening = is_port_in_use(port, data.get("host", "localhost"))
        status = "healthy" if is_listening else "unhealthy"

        if data.get("status") == "reserved":
            status = "reserved"
        elif data.get("status") == "planned":
            status = "planned"

        if status == "healthy":
            report["healthy"] += 1
        elif status == "unhealthy":
            report["unhealthy"] += 1
        else:
            report["unknown"] += 1

        report["details"].append({
            "port": port,
            "service": data["service_name"],
            "agent": data.get("agent_name"),
            "status": status,
            "is_listening": is_listening
        })

    return report


@app.post("/health-check")
async def trigger_health_check():
    """Trigger health check and update statuses"""
    checked = 0
    updated = 0

    for port, data in _port_registry.items():
        checked += 1
        is_listening = is_port_in_use(port, data.get("host", "localhost"))
        new_status = "healthy" if is_listening else "unhealthy"

        if data.get("health_status") != new_status:
            data["health_status"] = new_status
            data["last_health_check"] = datetime.utcnow().isoformat()
            updated += 1

            if new_status == "unhealthy" and data.get("status") == "active":
                await publish_event("ports.health.unhealthy", {
                    "port": port,
                    "service": data["service_name"],
                    "agent": data.get("agent_name")
                })

    return {
        "message": f"Health check completed",
        "checked": checked,
        "updated": updated
    }


@app.get("/orphans")
async def get_orphans():
    """Get unregistered listening ports (orphans)"""
    orphans = []

    # Check common port ranges
    ranges_to_check = [
        (3000, 3100),  # Development
        (5678, 5700),  # n8n
        (8000, 8100),  # Infrastructure
        (8100, 8200),  # Personal
        (8200, 8300),  # Business
    ]

    for start, end in ranges_to_check:
        for port in range(start, end):
            if port not in _port_registry and is_port_in_use(port):
                category = get_category_for_port(port)
                orphans.append({
                    "port": port,
                    "category": category,
                    "description": "Listening but not registered"
                })

    if orphans:
        await publish_event("ports.orphan.detected", {"count": len(orphans)})

    return {
        "count": len(orphans),
        "orphans": orphans
    }


@app.get("/zombies")
async def get_zombies():
    """Get registered but not listening ports (zombies)"""
    zombies = []

    for port, data in _port_registry.items():
        if data.get("status") in ["active"] and not is_port_in_use(port, data.get("host", "localhost")):
            zombies.append({
                "port": port,
                "service": data["service_name"],
                "agent": data.get("agent_name"),
                "description": "Registered as active but not listening"
            })

    return {
        "count": len(zombies),
        "zombies": zombies
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
