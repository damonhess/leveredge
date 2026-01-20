# GSD: Build MOMUS - The Fault-Finder

**Priority:** HIGH - System Integrity  
**Estimated Time:** 3-4 hours  
**Created:** 2026-01-18  
**Port:** 8022  
**Domain:** Infrastructure (Security-adjacent)

---

## The Story

> *Momus was the Greek god of satire, mockery, and fault-finding. He criticized Hephaestus's craftsmanship, found fault in Athena's house, and was eventually expelled from Olympus for his relentless criticism of the other gods.*

MOMUS ensures nothing slips through. He's the agent who would have caught "ATLAS doesn't exist" on day one.

---

## Problem Statement

Current monitoring has critical blind spots:

1. **ARGUS** only monitors 7 hardcoded agents (of 40+)
2. **No registry validation** - agents can claim any identity
3. **No port conflict detection** - discovered VARYS and CERBERUS both on 8020
4. **No code/config drift detection** - ATLAS claimed port 8208 but registry said 8007
5. **No integrity verification** - "is this agent what it claims to be?"

### Current Issues Found

| Issue | Details |
|-------|---------|
| Port 8020 conflict | VARYS and CERBERUS both assigned |
| Port 8202 conflict | DAEDALUS and GENDRY both assigned |
| Port 8207 conflict | HEPHAESTUS and HEPHAESTUS-SERVER both assigned |
| Duplicate directories | arwen/eros + eros/eros, gandalf + academic-guide, etc. |
| ATLAS ghost | Registry said 8007, code was 8208, nothing actually ran |
| ARGUS blind | Only monitors 7 of 40+ agents |

---

## Success Criteria

- [ ] MOMUS running on port 8022
- [ ] All port conflicts detected and reported
- [ ] Registry vs code validation working
- [ ] All 40+ agents health-checkable
- [ ] Daily integrity scan scheduled
- [ ] Alerts sent via HERMES on critical issues
- [ ] Dashboard/report endpoint available
- [ ] Historical drift tracking in database

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          MOMUS                                   │
│                     The Fault-Finder                             │
│                        Port: 8022                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Registry   │  │    Code      │  │   Runtime    │          │
│  │   Validator  │  │   Scanner    │  │   Checker    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                    │
│         └─────────────────┴─────────────────┘                    │
│                           │                                      │
│                    ┌──────▼──────┐                              │
│                    │  Integrity  │                              │
│                    │   Report    │                              │
│                    └──────┬──────┘                              │
│                           │                                      │
│         ┌─────────────────┼─────────────────┐                   │
│         ▼                 ▼                 ▼                   │
│    ┌─────────┐      ┌─────────┐      ┌─────────┐              │
│    │ HERMES  │      │ Event   │      │ Supabase│              │
│    │ Alerts  │      │  Bus    │      │ History │              │
│    └─────────┘      └─────────┘      └─────────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 1: Create Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/momus
```

---

## Section 2: Core MOMUS Agent

Create `/opt/leveredge/control-plane/agents/momus/momus.py`:

```python
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              MOMUS                                             ║
║                     The Fault-Finder of Olympus                                ║
║                                                                                ║
║  Port: 8022                                                                    ║
║                                                                                ║
║  Named after the Greek god of mockery and fault-finding, MOMUS ensures        ║
║  nothing slips through the cracks. He validates registry against reality,     ║
║  detects port conflicts, verifies agent identity, and catches drift.          ║
║                                                                                ║
║  CAPABILITIES:                                                                 ║
║  • Registry vs Code validation                                                ║
║  • Port conflict detection                                                    ║
║  • Agent identity verification                                                ║
║  • Runtime health aggregation                                                 ║
║  • Drift detection and alerting                                               ║
║  • Historical integrity tracking                                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys
import re
import yaml
import json
import subprocess
from datetime import datetime, date, timedelta
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from collections import defaultdict

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

MOMUS_PORT = 8022
REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
AGENTS_PATH = Path(os.getenv("AGENTS_PATH", "/opt/leveredge/control-plane/agents"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8014")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54322")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Launch tracking
LAUNCH_DATE = date(2026, 3, 1)

# Severity levels
class Severity(str, Enum):
    CRITICAL = "critical"  # System broken, immediate action needed
    HIGH = "high"          # Significant issue, fix soon
    MEDIUM = "medium"      # Should be fixed, not urgent
    LOW = "low"            # Minor issue, nice to fix
    INFO = "info"          # Informational only


@dataclass
class Issue:
    """Represents a detected issue."""
    id: str
    category: str  # port_conflict, missing_agent, identity_mismatch, etc.
    severity: Severity
    title: str
    description: str
    affected: List[str]  # Affected agents/resources
    recommendation: str
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class IntegrityReport:
    """Full integrity scan report."""
    scan_id: str
    scan_type: str  # full, quick, targeted
    started_at: str
    completed_at: Optional[str] = None
    duration_ms: int = 0
    
    # Counts
    agents_checked: int = 0
    agents_healthy: int = 0
    agents_unhealthy: int = 0
    agents_missing: int = 0
    
    # Issues
    issues: List[Issue] = field(default_factory=list)
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    
    # Status
    overall_status: str = "unknown"  # healthy, degraded, critical


# In-memory cache for scan results
last_scan: Optional[IntegrityReport] = None
issue_history: List[Issue] = []

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════════

def load_registry() -> dict:
    """Load the agent registry."""
    try:
        with open(REGISTRY_PATH) as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load registry: {e}")


def get_registered_agents() -> Dict[str, dict]:
    """Get all agents from registry with their expected ports."""
    registry = load_registry()
    agents = registry.get("agents", {})
    
    result = {}
    for name, config in agents.items():
        connection = config.get("connection", {})
        url = connection.get("url", "")
        
        # Extract port from URL
        port_match = re.search(r':(\d+)$', url)
        port = int(port_match.group(1)) if port_match else None
        
        result[name] = {
            "name": name,
            "url": url,
            "port": port,
            "description": config.get("description", ""),
            "category": config.get("category", "unknown"),
            "health_endpoint": connection.get("health_endpoint", "/health")
        }
    
    return result

# ═══════════════════════════════════════════════════════════════════════════════
# CODE SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

def scan_agent_code() -> Dict[str, dict]:
    """Scan agent directories for port declarations in code."""
    agents_found = {}
    
    for agent_dir in AGENTS_PATH.iterdir():
        if not agent_dir.is_dir():
            continue
        if agent_dir.name.startswith('.') or agent_dir.name == '__pycache__':
            continue
        
        # Look for Python files
        for py_file in agent_dir.glob("*.py"):
            if py_file.name.startswith('_'):
                continue
            
            try:
                content = py_file.read_text()
                
                # Find port declarations
                # Pattern 1: Port: XXXX in docstring
                port_doc = re.search(r'Port:\s*(\d+)', content)
                # Pattern 2: port=XXXX or port = XXXX
                port_var = re.search(r'port\s*[=:]\s*(\d+)', content, re.IGNORECASE)
                # Pattern 3: AGENT_PORT = XXXX
                port_const = re.search(r'_PORT\s*=\s*(\d+)', content)
                
                port = None
                if port_doc:
                    port = int(port_doc.group(1))
                elif port_const:
                    port = int(port_const.group(1))
                elif port_var:
                    port = int(port_var.group(1))
                
                # Find agent name declarations
                # Pattern: agent": "NAME" or agent = "NAME"
                name_match = re.search(r'"agent"\s*:\s*"([^"]+)"', content)
                if not name_match:
                    name_match = re.search(r"'agent'\s*:\s*'([^']+)'", content)
                
                agent_name = name_match.group(1) if name_match else agent_dir.name.upper()
                
                if port:
                    key = f"{agent_dir.name}/{py_file.name}"
                    agents_found[key] = {
                        "directory": agent_dir.name,
                        "file": py_file.name,
                        "path": str(py_file),
                        "agent_name": agent_name,
                        "port": port
                    }
            except Exception as e:
                print(f"Error scanning {py_file}: {e}")
    
    return agents_found

# ═══════════════════════════════════════════════════════════════════════════════
# PORT CONFLICT DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

def detect_port_conflicts(registry_agents: Dict[str, dict], code_agents: Dict[str, dict]) -> List[Issue]:
    """Detect port conflicts in registry and code."""
    issues = []
    
    # Check registry for conflicts
    registry_ports = defaultdict(list)
    for name, config in registry_agents.items():
        if config.get("port"):
            registry_ports[config["port"]].append(name)
    
    for port, agents in registry_ports.items():
        if len(agents) > 1:
            issues.append(Issue(
                id=f"port-conflict-registry-{port}",
                category="port_conflict",
                severity=Severity.CRITICAL,
                title=f"Port {port} conflict in registry",
                description=f"Multiple agents assigned to port {port} in agent-registry.yaml",
                affected=agents,
                recommendation=f"Reassign one of these agents to a different port: {', '.join(agents)}"
            ))
    
    # Check code for conflicts
    code_ports = defaultdict(list)
    for key, config in code_agents.items():
        if config.get("port"):
            code_ports[config["port"]].append(key)
    
    for port, files in code_ports.items():
        if len(files) > 1:
            issues.append(Issue(
                id=f"port-conflict-code-{port}",
                category="port_conflict",
                severity=Severity.HIGH,
                title=f"Port {port} conflict in code",
                description=f"Multiple agent files claim port {port}",
                affected=files,
                recommendation=f"Fix port declarations in: {', '.join(files)}"
            ))
    
    return issues

# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY VS CODE VALIDATOR
# ═══════════════════════════════════════════════════════════════════════════════

def validate_registry_vs_code(registry_agents: Dict[str, dict], code_agents: Dict[str, dict]) -> List[Issue]:
    """Validate that registry matches code declarations."""
    issues = []
    
    # Build port -> code mapping
    code_by_port = {}
    for key, config in code_agents.items():
        port = config.get("port")
        if port:
            if port not in code_by_port:
                code_by_port[port] = []
            code_by_port[port].append(config)
    
    # Check each registry agent
    for name, config in registry_agents.items():
        expected_port = config.get("port")
        if not expected_port:
            continue
        
        # Find matching code
        code_matches = code_by_port.get(expected_port, [])
        
        if not code_matches:
            issues.append(Issue(
                id=f"missing-code-{name}",
                category="missing_agent",
                severity=Severity.CRITICAL,
                title=f"No code found for {name}",
                description=f"Registry expects {name} on port {expected_port}, but no code declares this port",
                affected=[name],
                recommendation=f"Create agent code for {name} or remove from registry"
            ))
        elif len(code_matches) > 1:
            files = [c["path"] for c in code_matches]
            issues.append(Issue(
                id=f"multiple-code-{name}",
                category="duplicate_code",
                severity=Severity.MEDIUM,
                title=f"Multiple code files for port {expected_port}",
                description=f"Registry agent {name} has multiple code files claiming its port",
                affected=files,
                recommendation=f"Remove duplicate implementations"
            ))
    
    return issues

# ═══════════════════════════════════════════════════════════════════════════════
# RUNTIME HEALTH CHECKER
# ═══════════════════════════════════════════════════════════════════════════════

async def check_agent_health(name: str, url: str, health_endpoint: str = "/health") -> Tuple[bool, Optional[dict], Optional[str]]:
    """Check if an agent is healthy and responding."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Handle URL construction
            if url.startswith("http://"):
                # Replace hostname with localhost for local checks
                url_parts = url.replace("http://", "").split(":")
                if len(url_parts) == 2:
                    port = url_parts[1]
                    check_url = f"http://localhost:{port}{health_endpoint}"
                else:
                    check_url = f"{url}{health_endpoint}"
            else:
                check_url = f"{url}{health_endpoint}"
            
            response = await client.get(check_url)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return True, data, None
                except:
                    return True, {"raw": response.text}, None
            else:
                return False, None, f"HTTP {response.status_code}"
                
    except httpx.ConnectError:
        return False, None, "Connection refused"
    except httpx.TimeoutException:
        return False, None, "Timeout"
    except Exception as e:
        return False, None, str(e)


async def check_all_agents(registry_agents: Dict[str, dict]) -> Tuple[Dict[str, dict], List[Issue]]:
    """Check health of all registered agents."""
    results = {}
    issues = []
    
    tasks = []
    agent_names = []
    
    for name, config in registry_agents.items():
        url = config.get("url", "")
        health_endpoint = config.get("health_endpoint", "/health")
        tasks.append(check_agent_health(name, url, health_endpoint))
        agent_names.append(name)
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    for name, response in zip(agent_names, responses):
        config = registry_agents[name]
        
        if isinstance(response, Exception):
            results[name] = {
                "healthy": False,
                "error": str(response),
                "port": config.get("port")
            }
            issues.append(Issue(
                id=f"health-error-{name}",
                category="health_check_error",
                severity=Severity.HIGH,
                title=f"{name} health check failed",
                description=f"Error checking {name}: {response}",
                affected=[name],
                recommendation=f"Investigate {name} on port {config.get('port')}"
            ))
        else:
            healthy, data, error = response
            results[name] = {
                "healthy": healthy,
                "response": data,
                "error": error,
                "port": config.get("port")
            }
            
            if not healthy:
                issues.append(Issue(
                    id=f"unhealthy-{name}",
                    category="agent_unhealthy",
                    severity=Severity.HIGH,
                    title=f"{name} is unhealthy",
                    description=f"Agent {name} on port {config.get('port')} is not responding: {error}",
                    affected=[name],
                    recommendation=f"Check if {name} is running: systemctl status leveredge-{name.lower()}"
                ))
            else:
                # Verify identity
                if data and isinstance(data, dict):
                    reported_name = data.get("agent", "").upper()
                    expected_name = name.upper()
                    
                    # Normalize names for comparison
                    reported_clean = reported_name.replace("-", "").replace("_", "")
                    expected_clean = expected_name.replace("-", "").replace("_", "")
                    
                    if reported_clean and expected_clean and reported_clean != expected_clean:
                        issues.append(Issue(
                            id=f"identity-mismatch-{name}",
                            category="identity_mismatch",
                            severity=Severity.CRITICAL,
                            title=f"{name} identity mismatch",
                            description=f"Registry says '{name}' but agent reports '{reported_name}'",
                            affected=[name],
                            recommendation=f"Verify correct agent is running on port {config.get('port')}"
                        ))
    
    return results, issues

# ═══════════════════════════════════════════════════════════════════════════════
# DUPLICATE DIRECTORY DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

def detect_duplicate_directories() -> List[Issue]:
    """Detect directories that appear to contain the same agent."""
    issues = []
    
    # Known duplicates pattern: different dir names, same agent
    code_agents = scan_agent_code()
    
    # Group by port
    by_port = defaultdict(list)
    for key, config in code_agents.items():
        port = config.get("port")
        if port:
            by_port[port].append(config)
    
    # Check for duplicates
    for port, configs in by_port.items():
        if len(configs) > 1:
            dirs = list(set(c["directory"] for c in configs))
            if len(dirs) > 1:
                issues.append(Issue(
                    id=f"duplicate-dirs-{port}",
                    category="duplicate_directories",
                    severity=Severity.LOW,
                    title=f"Duplicate directories for port {port}",
                    description=f"Multiple directories contain agents for port {port}: {', '.join(dirs)}",
                    affected=dirs,
                    recommendation=f"Remove duplicate directories, keep canonical one"
                ))
    
    return issues

# ═══════════════════════════════════════════════════════════════════════════════
# FULL INTEGRITY SCAN
# ═══════════════════════════════════════════════════════════════════════════════

async def run_full_scan() -> IntegrityReport:
    """Run a complete integrity scan."""
    global last_scan
    
    import uuid
    scan_id = str(uuid.uuid4())[:8]
    started_at = datetime.utcnow()
    
    report = IntegrityReport(
        scan_id=scan_id,
        scan_type="full",
        started_at=started_at.isoformat()
    )
    
    try:
        # Load data
        registry_agents = get_registered_agents()
        code_agents = scan_agent_code()
        
        report.agents_checked = len(registry_agents)
        
        # Run all checks
        all_issues = []
        
        # 1. Port conflicts
        port_issues = detect_port_conflicts(registry_agents, code_agents)
        all_issues.extend(port_issues)
        
        # 2. Registry vs Code validation
        code_issues = validate_registry_vs_code(registry_agents, code_agents)
        all_issues.extend(code_issues)
        
        # 3. Duplicate directories
        dup_issues = detect_duplicate_directories()
        all_issues.extend(dup_issues)
        
        # 4. Runtime health checks
        health_results, health_issues = await check_all_agents(registry_agents)
        all_issues.extend(health_issues)
        
        # Count healthy/unhealthy
        report.agents_healthy = sum(1 for r in health_results.values() if r.get("healthy"))
        report.agents_unhealthy = sum(1 for r in health_results.values() if not r.get("healthy"))
        
        # Store issues
        report.issues = all_issues
        report.critical_count = sum(1 for i in all_issues if i.severity == Severity.CRITICAL)
        report.high_count = sum(1 for i in all_issues if i.severity == Severity.HIGH)
        report.medium_count = sum(1 for i in all_issues if i.severity == Severity.MEDIUM)
        report.low_count = sum(1 for i in all_issues if i.severity == Severity.LOW)
        
        # Determine overall status
        if report.critical_count > 0:
            report.overall_status = "critical"
        elif report.high_count > 0 or report.agents_unhealthy > report.agents_healthy:
            report.overall_status = "degraded"
        else:
            report.overall_status = "healthy"
        
    except Exception as e:
        report.issues.append(Issue(
            id="scan-error",
            category="scan_error",
            severity=Severity.CRITICAL,
            title="Scan failed",
            description=str(e),
            affected=["MOMUS"],
            recommendation="Check MOMUS logs"
        ))
        report.overall_status = "error"
    
    finally:
        completed_at = datetime.utcnow()
        report.completed_at = completed_at.isoformat()
        report.duration_ms = int((completed_at - started_at).total_seconds() * 1000)
        
        # Cache result
        last_scan = report
        
        # Store issues in history
        issue_history.extend(report.issues)
    
    return report

# ═══════════════════════════════════════════════════════════════════════════════
# ALERTING
# ═══════════════════════════════════════════════════════════════════════════════

async def send_alert(severity: str, title: str, description: str):
    """Send alert via HERMES."""
    try:
        priority = "critical" if severity == "critical" else "high" if severity == "high" else "normal"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "message": f"[MOMUS {severity.upper()}] {title}\n{description}",
                    "priority": priority,
                    "channel": "telegram"
                }
            )
    except Exception as e:
        print(f"Failed to send alert: {e}")


async def send_scan_report(report: IntegrityReport):
    """Send scan report summary via HERMES."""
    if report.critical_count == 0 and report.high_count == 0:
        return  # Don't alert on clean scans
    
    message = f"""🔍 MOMUS Integrity Scan Complete

Status: {report.overall_status.upper()}
Agents: {report.agents_healthy}/{report.agents_checked} healthy

Issues Found:
• Critical: {report.critical_count}
• High: {report.high_count}
• Medium: {report.medium_count}
• Low: {report.low_count}

Top Issues:"""
    
    for issue in report.issues[:3]:
        if issue.severity in [Severity.CRITICAL, Severity.HIGH]:
            message += f"\n• [{issue.severity.value}] {issue.title}"
    
    await send_alert(report.overall_status, "Integrity Scan Complete", message)


async def log_to_event_bus(event_type: str, data: dict):
    """Log event to Event Bus."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "MOMUS",
                    "data": data
                }
            )
    except:
        pass

# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ScanRequest(BaseModel):
    scan_type: str = "full"  # full, quick, targeted
    targets: Optional[List[str]] = None  # For targeted scans


class IssueResponse(BaseModel):
    id: str
    category: str
    severity: str
    title: str
    description: str
    affected: List[str]
    recommendation: str
    detected_at: str
    resolved: bool

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="MOMUS - The Fault-Finder",
    description="System integrity validation, port conflict detection, and drift monitoring",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check."""
    today = date.today()
    days_to_launch = (LAUNCH_DATE - today).days
    
    return {
        "status": "healthy",
        "agent": "MOMUS",
        "role": "Fault-Finder & Integrity Checker",
        "port": MOMUS_PORT,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "days_to_launch": days_to_launch,
        "last_scan": last_scan.scan_id if last_scan else None,
        "last_scan_status": last_scan.overall_status if last_scan else None
    }


@app.get("/status")
async def status():
    """Get current status with last scan summary."""
    registry_agents = get_registered_agents()
    
    return {
        "momus": "healthy",
        "registered_agents": len(registry_agents),
        "last_scan": {
            "scan_id": last_scan.scan_id if last_scan else None,
            "status": last_scan.overall_status if last_scan else None,
            "completed_at": last_scan.completed_at if last_scan else None,
            "issues": {
                "critical": last_scan.critical_count if last_scan else 0,
                "high": last_scan.high_count if last_scan else 0,
                "medium": last_scan.medium_count if last_scan else 0,
                "low": last_scan.low_count if last_scan else 0
            }
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# ─────────────────────────────────────────────────────────────────────────────
# SCANNING
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/scan")
async def trigger_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """Trigger an integrity scan."""
    
    if request.scan_type == "full":
        report = await run_full_scan()
        
        # Alert on issues
        background_tasks.add_task(send_scan_report, report)
        
        # Log to event bus
        background_tasks.add_task(
            log_to_event_bus,
            "integrity_scan_completed",
            {
                "scan_id": report.scan_id,
                "status": report.overall_status,
                "issues": report.critical_count + report.high_count
            }
        )
        
        return {
            "scan_id": report.scan_id,
            "status": report.overall_status,
            "duration_ms": report.duration_ms,
            "agents_checked": report.agents_checked,
            "agents_healthy": report.agents_healthy,
            "issues": {
                "critical": report.critical_count,
                "high": report.high_count,
                "medium": report.medium_count,
                "low": report.low_count,
                "total": len(report.issues)
            }
        }
    else:
        raise HTTPException(400, f"Scan type '{request.scan_type}' not implemented")


@app.get("/scan/last")
async def get_last_scan():
    """Get the last scan report."""
    if not last_scan:
        raise HTTPException(404, "No scan has been run yet")
    
    return {
        "scan_id": last_scan.scan_id,
        "scan_type": last_scan.scan_type,
        "started_at": last_scan.started_at,
        "completed_at": last_scan.completed_at,
        "duration_ms": last_scan.duration_ms,
        "overall_status": last_scan.overall_status,
        "agents": {
            "checked": last_scan.agents_checked,
            "healthy": last_scan.agents_healthy,
            "unhealthy": last_scan.agents_unhealthy
        },
        "issues": {
            "critical": last_scan.critical_count,
            "high": last_scan.high_count,
            "medium": last_scan.medium_count,
            "low": last_scan.low_count,
            "details": [asdict(i) for i in last_scan.issues]
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# ISSUES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/issues")
async def list_issues(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    resolved: Optional[bool] = None
):
    """List all detected issues."""
    issues = last_scan.issues if last_scan else []
    
    # Filter
    if severity:
        issues = [i for i in issues if i.severity.value == severity]
    if category:
        issues = [i for i in issues if i.category == category]
    if resolved is not None:
        issues = [i for i in issues if i.resolved == resolved]
    
    return {
        "issues": [asdict(i) for i in issues],
        "count": len(issues)
    }


@app.get("/issues/critical")
async def list_critical_issues():
    """List only critical issues."""
    issues = last_scan.issues if last_scan else []
    critical = [i for i in issues if i.severity == Severity.CRITICAL]
    
    return {
        "issues": [asdict(i) for i in critical],
        "count": len(critical)
    }

# ─────────────────────────────────────────────────────────────────────────────
# PORT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/ports")
async def analyze_ports():
    """Analyze port assignments."""
    registry_agents = get_registered_agents()
    code_agents = scan_agent_code()
    
    # Build port map
    port_map = defaultdict(lambda: {"registry": [], "code": []})
    
    for name, config in registry_agents.items():
        port = config.get("port")
        if port:
            port_map[port]["registry"].append(name)
    
    for key, config in code_agents.items():
        port = config.get("port")
        if port:
            port_map[port]["code"].append({
                "directory": config["directory"],
                "file": config["file"],
                "agent_name": config["agent_name"]
            })
    
    # Identify conflicts
    conflicts = []
    for port, data in port_map.items():
        if len(data["registry"]) > 1 or len(data["code"]) > 1:
            conflicts.append({
                "port": port,
                "registry_agents": data["registry"],
                "code_files": data["code"]
            })
    
    return {
        "port_assignments": dict(port_map),
        "conflicts": conflicts,
        "conflict_count": len(conflicts)
    }

# ─────────────────────────────────────────────────────────────────────────────
# AGENT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/agents")
async def list_agents_status():
    """List all agents with their current status."""
    registry_agents = get_registered_agents()
    health_results, _ = await check_all_agents(registry_agents)
    
    agents = []
    for name, config in registry_agents.items():
        health = health_results.get(name, {})
        agents.append({
            "name": name,
            "port": config.get("port"),
            "category": config.get("category"),
            "healthy": health.get("healthy", False),
            "error": health.get("error"),
            "response": health.get("response")
        })
    
    # Sort by health status (unhealthy first)
    agents.sort(key=lambda x: (x["healthy"], x["name"]))
    
    return {
        "agents": agents,
        "total": len(agents),
        "healthy": sum(1 for a in agents if a["healthy"]),
        "unhealthy": sum(1 for a in agents if not a["healthy"])
    }


@app.get("/agents/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed analysis of a specific agent."""
    registry_agents = get_registered_agents()
    
    # Find in registry
    registry_config = None
    for name, config in registry_agents.items():
        if name.lower() == agent_name.lower():
            registry_config = config
            break
    
    if not registry_config:
        raise HTTPException(404, f"Agent '{agent_name}' not found in registry")
    
    # Find in code
    code_agents = scan_agent_code()
    code_matches = [
        c for c in code_agents.values()
        if c.get("port") == registry_config.get("port")
    ]
    
    # Check health
    healthy, response, error = await check_agent_health(
        agent_name,
        registry_config.get("url", ""),
        registry_config.get("health_endpoint", "/health")
    )
    
    return {
        "name": agent_name,
        "registry": registry_config,
        "code_files": code_matches,
        "runtime": {
            "healthy": healthy,
            "response": response,
            "error": error
        },
        "issues": [
            asdict(i) for i in (last_scan.issues if last_scan else [])
            if agent_name.lower() in [a.lower() for a in i.affected]
        ]
    }

# ─────────────────────────────────────────────────────────────────────────────
# QUICK CHECKS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/check/ports")
async def quick_check_ports():
    """Quick check for port conflicts only."""
    registry_agents = get_registered_agents()
    code_agents = scan_agent_code()
    issues = detect_port_conflicts(registry_agents, code_agents)
    
    return {
        "conflicts_found": len(issues),
        "issues": [asdict(i) for i in issues]
    }


@app.get("/check/health")
async def quick_check_health():
    """Quick health check of all agents."""
    registry_agents = get_registered_agents()
    results, issues = await check_all_agents(registry_agents)
    
    healthy = sum(1 for r in results.values() if r.get("healthy"))
    unhealthy = sum(1 for r in results.values() if not r.get("healthy"))
    
    return {
        "total": len(results),
        "healthy": healthy,
        "unhealthy": unhealthy,
        "unhealthy_agents": [
            {"name": name, "error": data.get("error")}
            for name, data in results.items()
            if not data.get("healthy")
        ]
    }


@app.get("/check/registry")
async def quick_check_registry():
    """Quick validation of registry vs code."""
    registry_agents = get_registered_agents()
    code_agents = scan_agent_code()
    issues = validate_registry_vs_code(registry_agents, code_agents)
    
    return {
        "mismatches_found": len(issues),
        "issues": [asdict(i) for i in issues]
    }

# ─────────────────────────────────────────────────────────────────────────────
# LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Run initial scan on startup."""
    print(f"🔍 MOMUS The Fault-Finder starting on port {MOMUS_PORT}")
    
    # Run initial scan
    try:
        report = await run_full_scan()
        print(f"   Initial scan: {report.overall_status}")
        print(f"   Agents: {report.agents_healthy}/{report.agents_checked} healthy")
        print(f"   Issues: {report.critical_count} critical, {report.high_count} high")
        
        # Alert if critical issues found
        if report.critical_count > 0:
            await send_scan_report(report)
            
    except Exception as e:
        print(f"   Initial scan failed: {e}")
    
    # Log startup
    await log_to_event_bus("agent_started", {
        "agent": "MOMUS",
        "port": MOMUS_PORT,
        "version": "1.0.0"
    })

# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=MOMUS_PORT)
```

---

## Section 3: Requirements

Create `/opt/leveredge/control-plane/agents/momus/requirements.txt`:

```
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pyyaml>=6.0
pydantic>=2.0
```

---

## Section 4: Systemd Service

Create `/opt/leveredge/shared/systemd/leveredge-momus.service`:

```ini
[Unit]
Description=LeverEdge MOMUS - Fault-Finder & Integrity Checker
After=network.target
Wants=leveredge-event-bus.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/leveredge/control-plane/agents/momus
Environment=PYTHONUNBUFFERED=1
Environment=REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml
Environment=AGENTS_PATH=/opt/leveredge/control-plane/agents
Environment=EVENT_BUS_URL=http://localhost:8099
Environment=HERMES_URL=http://localhost:8014
ExecStart=/opt/leveredge/shared/venv/bin/python momus.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## Section 5: Add to Agent Registry

Add to `/opt/leveredge/config/agent-registry.yaml` in the agents section:

```yaml
  # ─────────────────────────────────────────────────────────────────────────────
  # MOMUS - System Integrity Checker
  # ─────────────────────────────────────────────────────────────────────────────
  momus:
    name: MOMUS
    version: "1.0"
    description: "Fault-Finder - System integrity, port conflicts, drift detection"
    category: infrastructure
    llm_powered: false

    connection:
      url: http://momus:8022
      health_endpoint: /health
      timeout_ms: 30000

    capabilities:
      - integrity_scanning
      - port_conflict_detection
      - registry_validation
      - health_aggregation
      - drift_detection

    actions:

      scan:
        endpoint: /scan
        method: POST
        description: "Run integrity scan"
        timeout_ms: 60000
        params:
          - name: scan_type
            type: string
            required: false
            default: "full"
            enum: [full, quick, targeted]
        returns:
          type: object
          fields: [scan_id, status, issues]

      check-ports:
        endpoint: /check/ports
        method: GET
        description: "Quick port conflict check"
        timeout_ms: 10000
        returns:
          type: object
          fields: [conflicts_found, issues]

      check-health:
        endpoint: /check/health
        method: GET
        description: "Quick health check all agents"
        timeout_ms: 60000
        returns:
          type: object
          fields: [total, healthy, unhealthy, unhealthy_agents]

      check-registry:
        endpoint: /check/registry
        method: GET
        description: "Validate registry vs code"
        timeout_ms: 30000
        returns:
          type: object
          fields: [mismatches_found, issues]

      issues:
        endpoint: /issues
        method: GET
        description: "List detected issues"
        timeout_ms: 10000
        params:
          - name: severity
            type: string
            required: false
          - name: category
            type: string
            required: false
        returns:
          type: object
          fields: [issues, count]

      agents:
        endpoint: /agents
        method: GET
        description: "List all agents with status"
        timeout_ms: 60000
        returns:
          type: object
          fields: [agents, total, healthy, unhealthy]
```

---

## Section 6: Fix Known Issues

### 6.1 Fix Port 8020 Conflict (VARYS vs CERBERUS)

VARYS should move to port 8023:

```bash
# Update agent-registry.yaml
sed -i 's|http://varys:8020|http://varys:8023|g' /opt/leveredge/config/agent-registry.yaml

# Update VARYS code if it exists
find /opt/leveredge/control-plane/agents -name "*.py" -exec grep -l "varys" {} \; | xargs sed -i 's/8020/8023/g' 2>/dev/null || true
```

### 6.2 Fix Port 8202 Conflict (DAEDALUS vs GENDRY)

Remove GENDRY (duplicate of DAEDALUS):

```bash
# Remove duplicate directory
rm -rf /opt/leveredge/control-plane/agents/gendry
```

### 6.3 Fix Port 8207 Conflict (HEPHAESTUS vs HEPHAESTUS-SERVER)

HEPHAESTUS-SERVER should be on 8207, HEPHAESTUS MCP is on 8011:

```bash
# Verify HEPHAESTUS files
# hephaestus.py (port 8207) - the FastAPI backend
# hephaestus_mcp.py (port 8011) - the MCP server for Claude
# These are different components, should be OK
```

### 6.4 Clean Up Duplicate Directories

```bash
# Remove duplicates (keep the canonical names)
rm -rf /opt/leveredge/control-plane/agents/eros  # Keep arwen
rm -rf /opt/leveredge/control-plane/agents/gandalf  # Keep academic-guide  
rm -rf /opt/leveredge/control-plane/agents/aragorn  # Keep gym-coach
```

---

## Section 7: Deploy Script

Create `/opt/leveredge/shared/scripts/deploy-momus.sh`:

```bash
#!/bin/bash
set -e

echo "🔍 Deploying MOMUS - The Fault-Finder..."

# Create directory
mkdir -p /opt/leveredge/control-plane/agents/momus

# Copy files (assuming they're created)
cd /opt/leveredge/control-plane/agents/momus

# Install systemd service
sudo cp /opt/leveredge/shared/systemd/leveredge-momus.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable leveredge-momus
sudo systemctl restart leveredge-momus

# Wait for startup
sleep 3

# Check health
if curl -s http://localhost:8022/health | grep -q "healthy"; then
    echo "✅ MOMUS is healthy!"
else
    echo "❌ MOMUS health check failed"
    sudo journalctl -u leveredge-momus -n 50
    exit 1
fi

# Run initial scan
echo ""
echo "Running initial integrity scan..."
curl -s -X POST http://localhost:8022/scan | python3 -m json.tool

echo ""
echo "🔍 MOMUS deployed successfully!"
echo "   Port: 8022"
echo "   Health: http://localhost:8022/health"
echo "   Scan: curl -X POST http://localhost:8022/scan"
echo "   Issues: http://localhost:8022/issues"
```

---

## Section 8: Cron Job for Daily Scan

Add to crontab:

```bash
# Daily integrity scan at 6 AM
0 6 * * * curl -s -X POST http://localhost:8022/scan > /dev/null 2>&1
```

---

## Execution Order

1. **Create MOMUS directory and files** (Sections 1-3)
2. **Create systemd service** (Section 4)
3. **Add to agent registry** (Section 5)
4. **Fix known issues** (Section 6)
5. **Deploy** (Section 7)
6. **Set up daily scan** (Section 8)
7. **Verify**

---

## GSD Command

```
/gsd /opt/leveredge/specs/gsd-build-momus-integrity-checker.md

CONTEXT: We discovered ATLAS didn't exist because no audit system caught it.
MOMUS is the Fault-Finder that will catch these issues going forward.

CRITICAL NOTES:
- Port 8022 (next available in infrastructure range)
- Must fix existing port conflicts: 8020 (VARYS/CERBERUS), 8202 (DAEDALUS/GENDRY)
- Clean up duplicate directories
- Run initial scan on startup
- Alert via HERMES on critical issues

FIXES NEEDED:
- Move VARYS from 8020 to 8023 (CERBERUS keeps 8020)
- Remove /agents/gendry (duplicate of daedalus)
- Remove /agents/eros (duplicate of arwen)
- Remove /agents/gandalf (duplicate of academic-guide)
- Remove /agents/aragorn (duplicate of gym-coach)
```

---

## Expected Outcome

After deployment:
- ✅ MOMUS running on port 8022
- ✅ All port conflicts detected and fixed
- ✅ Duplicate directories cleaned up
- ✅ Full agent health visibility (40+ agents)
- ✅ Daily integrity scans
- ✅ Alerts on critical issues
- ✅ No more "ATLAS doesn't exist" surprises

---

## Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Status with last scan |
| `/scan` | POST | Trigger integrity scan |
| `/scan/last` | GET | Get last scan report |
| `/issues` | GET | List all issues |
| `/issues/critical` | GET | List critical only |
| `/ports` | GET | Port analysis |
| `/agents` | GET | All agents with status |
| `/agents/{name}` | GET | Single agent details |
| `/check/ports` | GET | Quick port check |
| `/check/health` | GET | Quick health check |
| `/check/registry` | GET | Quick registry validation |

---

**Total Estimated Time: 3-4 hours**
