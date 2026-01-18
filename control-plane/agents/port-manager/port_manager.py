"""
PORT-MANAGER - Network Port Allocation Manager
Manages port assignments for all LeverEdge services
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime
import socket

AGENT_NAME = "PORT-MANAGER"
AGENT_PORT = 8021

app = FastAPI(title=f"LeverEdge {AGENT_NAME}", description="Port Allocation Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Port registry
port_registry: Dict[int, Dict] = {
    # Core agents
    8000: {"service": "GAIA", "status": "active", "category": "core"},
    8007: {"service": "ATLAS", "status": "active", "category": "core"},
    8008: {"service": "HADES", "status": "active", "category": "core"},
    8010: {"service": "CHRONOS", "status": "active", "category": "core"},
    8011: {"service": "HEPHAESTUS", "status": "active", "category": "core"},
    8012: {"service": "AEGIS", "status": "active", "category": "core"},
    8013: {"service": "ATHENA", "status": "active", "category": "core"},
    8014: {"service": "HERMES", "status": "active", "category": "core"},
    8016: {"service": "ARGUS", "status": "active", "category": "core"},
    8017: {"service": "CHIRON", "status": "active", "category": "core"},
    8018: {"service": "SCHOLAR", "status": "active", "category": "core"},
    8019: {"service": "SENTINEL", "status": "active", "category": "core"},
    # Security
    8020: {"service": "CERBERUS", "status": "active", "category": "security"},
    8021: {"service": "PORT-MANAGER", "status": "active", "category": "security"},
    # Creative
    8030: {"service": "MUSE", "status": "reserved", "category": "creative"},
    8031: {"service": "CALLIOPE", "status": "reserved", "category": "creative"},
    8032: {"service": "THALIA", "status": "reserved", "category": "creative"},
    8033: {"service": "ERATO", "status": "reserved", "category": "creative"},
    8034: {"service": "CLIO", "status": "reserved", "category": "creative"},
    # Infrastructure
    8050: {"service": "FILE-PROCESSOR", "status": "reserved", "category": "infrastructure"},
    8051: {"service": "VOICE", "status": "reserved", "category": "infrastructure"},
    8060: {"service": "FLEET-DASHBOARD", "status": "reserved", "category": "infrastructure"},
    8061: {"service": "COST-DASHBOARD", "status": "reserved", "category": "infrastructure"},
    8066: {"service": "MEMORY-V2", "status": "reserved", "category": "infrastructure"},
    8067: {"service": "SHIELD-SWORD", "status": "reserved", "category": "infrastructure"},
    8070: {"service": "GATEWAY", "status": "reserved", "category": "infrastructure"},
    8099: {"service": "EVENT-BUS", "status": "active", "category": "infrastructure"},
    # Personal
    8101: {"service": "NUTRITIONIST", "status": "reserved", "category": "personal"},
    8102: {"service": "MEAL-PLANNER", "status": "reserved", "category": "personal"},
    8103: {"service": "ACADEMIC-GUIDE", "status": "reserved", "category": "personal"},
    8104: {"service": "EROS", "status": "reserved", "category": "personal"},
    8110: {"service": "GYM-COACH", "status": "reserved", "category": "personal"},
    # Business
    8200: {"service": "HERACLES", "status": "reserved", "category": "business"},
    8201: {"service": "LIBRARIAN", "status": "reserved", "category": "business"},
    8202: {"service": "DAEDALUS", "status": "reserved", "category": "business"},
    8203: {"service": "THEMIS", "status": "reserved", "category": "business"},
    8204: {"service": "MENTOR", "status": "reserved", "category": "business"},
    8205: {"service": "PLUTUS", "status": "reserved", "category": "business"},
    8206: {"service": "PROCUREMENT", "status": "reserved", "category": "business"},
    8207: {"service": "HEPHAESTUS-SERVER", "status": "reserved", "category": "business"},
    8208: {"service": "ATLAS-INFRA", "status": "reserved", "category": "business"},
    8209: {"service": "IRIS", "status": "reserved", "category": "business"},
    # Council
    8300: {"service": "CONVENER", "status": "active", "category": "council"},
    8301: {"service": "SCRIBE", "status": "reserved", "category": "council"},
}

# Port ranges
PORT_RANGES = {
    "core": (8000, 8019),
    "security": (8020, 8029),
    "creative": (8030, 8049),
    "infrastructure": (8050, 8098),
    "event_bus": (8099, 8099),
    "personal": (8100, 8119),
    "business": (8200, 8249),
    "council": (8300, 8319),
}

class PortRequest(BaseModel):
    service: str
    preferred_port: Optional[int] = None
    category: Optional[str] = None

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": AGENT_NAME,
        "port": AGENT_PORT,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/ports")
async def list_ports():
    """List all registered ports"""
    return {
        "ports": port_registry,
        "total": len(port_registry),
        "active": len([p for p in port_registry.values() if p["status"] == "active"]),
        "reserved": len([p for p in port_registry.values() if p["status"] == "reserved"])
    }

@app.get("/ports/by-category/{category}")
async def list_ports_by_category(category: str):
    """List ports by category"""
    filtered = {k: v for k, v in port_registry.items() if v.get("category") == category}
    return {"category": category, "ports": filtered, "count": len(filtered)}

@app.get("/ports/{port}")
async def get_port(port: int):
    """Get info about specific port"""
    if port in port_registry:
        return {"port": port, **port_registry[port]}
    return {"port": port, "status": "available"}

@app.post("/ports/allocate")
async def allocate_port(request: PortRequest):
    """Allocate a port for a service"""

    # Check preferred port
    if request.preferred_port:
        if request.preferred_port not in port_registry:
            port_registry[request.preferred_port] = {
                "service": request.service,
                "status": "reserved",
                "category": request.category or "uncategorized",
                "allocated_at": datetime.utcnow().isoformat()
            }
            return {"port": request.preferred_port, "status": "allocated"}
        else:
            raise HTTPException(400, f"Port {request.preferred_port} already in use by {port_registry[request.preferred_port]['service']}")

    # Find available port in category range
    if request.category and request.category in PORT_RANGES:
        start, end = PORT_RANGES[request.category]
        for port in range(start, end + 1):
            if port not in port_registry:
                port_registry[port] = {
                    "service": request.service,
                    "status": "reserved",
                    "category": request.category,
                    "allocated_at": datetime.utcnow().isoformat()
                }
                return {"port": port, "status": "allocated"}
        raise HTTPException(400, f"No available ports in {request.category} range")

    # Find any available port
    for port in range(8000, 9000):
        if port not in port_registry:
            port_registry[port] = {
                "service": request.service,
                "status": "reserved",
                "category": request.category or "uncategorized",
                "allocated_at": datetime.utcnow().isoformat()
            }
            return {"port": port, "status": "allocated"}

    raise HTTPException(400, "No available ports")

@app.post("/ports/{port}/activate")
async def activate_port(port: int):
    """Mark port as active (service running)"""
    if port not in port_registry:
        raise HTTPException(404, "Port not registered")

    port_registry[port]["status"] = "active"
    port_registry[port]["activated_at"] = datetime.utcnow().isoformat()

    return {"port": port, "status": "active"}

@app.delete("/ports/{port}")
async def release_port(port: int):
    """Release a port"""
    if port in port_registry:
        service = port_registry[port]["service"]
        del port_registry[port]
        return {"port": port, "status": "released", "was": service}
    return {"port": port, "status": "not_registered"}

@app.get("/ranges")
async def get_ranges():
    """Get port range definitions"""
    return PORT_RANGES

@app.get("/check-conflicts")
async def check_conflicts():
    """Check for port conflicts"""

    conflicts = []
    for port, info in port_registry.items():
        if info["status"] == "active":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()

            if result != 0:
                conflicts.append({
                    "port": port,
                    "service": info["service"],
                    "issue": "registered as active but not responding"
                })

    return {"conflicts": conflicts, "count": len(conflicts)}

@app.get("/summary")
async def get_summary():
    """Get summary of port allocations by category"""
    summary = {}
    for category in PORT_RANGES.keys():
        ports = [p for p, v in port_registry.items() if v.get("category") == category]
        active = [p for p in ports if port_registry[p]["status"] == "active"]
        reserved = [p for p in ports if port_registry[p]["status"] == "reserved"]
        summary[category] = {
            "total": len(ports),
            "active": len(active),
            "reserved": len(reserved),
            "range": PORT_RANGES[category]
        }
    return summary

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT)
