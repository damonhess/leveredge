# GSD: Build PANOPTES - The All-Seeing Integrity Guardian

**Priority:** HIGH - System Integrity  
**Estimated Time:** 3-4 hours  
**Created:** 2026-01-18  
**Status:** Ready for execution

---

## Naming & Domain

### PANOPTES (Πανόπτης)

**"The All-Seeing One"**

In Greek mythology, **Argus Panoptes** was a giant with 100 eyes - some always awake, always watching. He was the ultimate guardian, assigned by Hera to watch over Io. Nothing escaped his gaze.

**Why this name:**
- Distinct from ARGUS (metrics/health) - PANOPTES sees *deeper*
- Fits the Greek theme
- Perfect metaphor: 100 eyes = checks every agent, every port, every config
- "All-seeing" = integrity verification across the entire system

**Domain:** Security Fleet (alongside CERBERUS)  
**Port:** 8022

---

## Problem Statement

The ATLAS incident revealed a critical gap: **no one verifies the system is what it claims to be.**

Current monitoring:
- ARGUS → Checks if services respond (but not *what* they are)
- ALOY → Detects anomalous events (but not structural issues)
- SENTINEL → Routes requests (but doesn't validate identity)

Missing:
- Registry vs Reality validation
- Port conflict detection  
- Agent identity verification
- Duplicate code detection
- Systemd service validation

---

## Success Criteria

- [ ] PANOPTES running on port 8022
- [ ] Daily integrity scan automated
- [ ] Port conflict detection working
- [ ] Registry validation working
- [ ] Alerts via HERMES on critical issues
- [ ] Dashboard endpoint for quick status
- [ ] All current issues detected and reported

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PANOPTES                                 │
│                    "The All-Seeing One"                          │
│                         :8022                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Registry   │  │    Port     │  │   Agent     │             │
│  │  Validator  │  │  Scanner    │  │  Identity   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │  Duplicate  │  │  Systemd    │  │   Report    │             │
│  │  Detector   │  │  Checker    │  │  Generator  │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                          │                                       │
│                    ┌─────▼─────┐                                │
│                    │  HERMES   │ (alerts)                       │
│                    └───────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 1: Create Directory Structure

```bash
mkdir -p /opt/leveredge/control-plane/agents/panoptes
```

---

## Section 2: Core PANOPTES Agent

Create `/opt/leveredge/control-plane/agents/panoptes/panoptes.py`:

```python
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              PANOPTES                                          ║
║                    The All-Seeing Integrity Guardian                           ║
║                                                                                ║
║  Port: 8022                                                                    ║
║  Domain: Security Fleet                                                        ║
║                                                                                ║
║  Named after Argus Panoptes, the hundred-eyed giant who never slept.          ║
║  PANOPTES sees everything - every agent, every port, every config.            ║
║                                                                                ║
║  CAPABILITIES:                                                                 ║
║  • Registry vs Reality validation                                             ║
║  • Port conflict detection                                                    ║
║  • Agent identity verification                                                ║
║  • Duplicate code/directory detection                                         ║
║  • Systemd service validation                                                 ║
║  • Daily integrity reports                                                    ║
║  • Real-time alerts on critical issues                                        ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys
import re
import yaml
import socket
import subprocess
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

PANOPTES_PORT = 8022
REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
AGENTS_PATH = Path(os.getenv("AGENTS_PATH", "/opt/leveredge/control-plane/agents"))
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8014")

LAUNCH_DATE = date(2026, 3, 1)

# Severity levels
class Severity(str, Enum):
    CRITICAL = "critical"  # System broken, immediate action needed
    HIGH = "high"          # Significant issue, fix soon
    MEDIUM = "medium"      # Should be fixed, not urgent
    LOW = "low"            # Informational, cleanup item
    INFO = "info"          # FYI only

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Issue:
    """Represents a detected issue."""
    id: str
    category: str
    severity: Severity
    title: str
    description: str
    affected: List[str]
    recommendation: str
    detected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self):
        d = asdict(self)
        d['severity'] = self.severity.value
        return d


@dataclass
class IntegrityReport:
    """Full integrity scan report."""
    report_id: str
    scan_started: str
    scan_completed: str
    total_checks: int
    passed_checks: int
    issues: List[Issue]
    summary: Dict[str, int]  # by severity
    
    def to_dict(self):
        return {
            "report_id": self.report_id,
            "scan_started": self.scan_started,
            "scan_completed": self.scan_completed,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.total_checks - self.passed_checks,
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "health_score": round(self.passed_checks / max(self.total_checks, 1) * 100, 1)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRY LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class RegistryLoader:
    """Load and parse the agent registry."""
    
    def __init__(self):
        self._cache = None
        self._loaded_at = None
    
    def load(self, force: bool = False) -> dict:
        """Load registry YAML."""
        if self._cache and not force:
            return self._cache
        
        with open(REGISTRY_PATH) as f:
            self._cache = yaml.safe_load(f)
            self._loaded_at = datetime.utcnow()
        return self._cache
    
    def get_agents(self) -> Dict[str, dict]:
        """Get all registered agents."""
        return self.load().get("agents", {})
    
    def get_chains(self) -> Dict[str, dict]:
        """Get all registered chains."""
        return self.load().get("chains", {})
    
    def get_agent_port(self, agent_name: str) -> Optional[int]:
        """Extract port from agent URL."""
        agents = self.get_agents()
        agent = agents.get(agent_name, {})
        url = agent.get("connection", {}).get("url", "")
        match = re.search(r':(\d+)$', url)
        return int(match.group(1)) if match else None


registry = RegistryLoader()

# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRITY SCANNERS
# ═══════════════════════════════════════════════════════════════════════════════

class PortScanner:
    """Scan for port conflicts and availability."""
    
    async def scan(self) -> Tuple[List[Issue], int]:
        """Scan all ports for conflicts."""
        issues = []
        checks = 0
        
        # Build port -> agents mapping from registry
        port_map: Dict[int, List[str]] = {}
        agents = registry.get_agents()
        
        for name, config in agents.items():
            checks += 1
            port = registry.get_agent_port(name)
            if port:
                if port not in port_map:
                    port_map[port] = []
                port_map[port].append(name)
        
        # Check for conflicts
        for port, agent_list in port_map.items():
            if len(agent_list) > 1:
                issues.append(Issue(
                    id=f"port-conflict-{port}",
                    category="port_conflict",
                    severity=Severity.CRITICAL,
                    title=f"Port {port} assigned to multiple agents",
                    description=f"Agents {', '.join(agent_list)} are all configured to use port {port}",
                    affected=agent_list,
                    recommendation=f"Reassign one of these agents to a different port"
                ))
        
        # Check if ports are actually in use by expected service
        for port, agent_list in port_map.items():
            if len(agent_list) == 1:
                checks += 1
                agent_name = agent_list[0]
                is_listening = await self._check_port_listening(port)
                
                if not is_listening:
                    issues.append(Issue(
                        id=f"port-not-listening-{port}",
                        category="agent_offline",
                        severity=Severity.HIGH,
                        title=f"Agent {agent_name} not listening on port {port}",
                        description=f"Registry says {agent_name} should be on port {port}, but nothing is listening",
                        affected=[agent_name],
                        recommendation=f"Start the {agent_name} service or check if it crashed"
                    ))
        
        return issues, checks
    
    async def _check_port_listening(self, port: int) -> bool:
        """Check if something is listening on a port."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        try:
            result = sock.connect_ex(('localhost', port))
            return result == 0
        except:
            return False
        finally:
            sock.close()


class IdentityVerifier:
    """Verify agents are what they claim to be."""
    
    async def scan(self) -> Tuple[List[Issue], int]:
        """Verify agent identities via health endpoints."""
        issues = []
        checks = 0
        
        agents = registry.get_agents()
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, config in agents.items():
                checks += 1
                url = config.get("connection", {}).get("url", "")
                if not url:
                    continue
                
                try:
                    # Call health endpoint
                    response = await client.get(f"{url.replace('http://', 'http://localhost:').split(':')[0]}:{registry.get_agent_port(name)}/health")
                    
                    if response.status_code == 200:
                        data = response.json()
                        reported_agent = data.get("agent", "").lower()
                        expected_agent = config.get("name", name).upper()
                        
                        # Check if agent reports correct identity
                        if reported_agent and reported_agent.upper() != expected_agent:
                            issues.append(Issue(
                                id=f"identity-mismatch-{name}",
                                category="identity_mismatch",
                                severity=Severity.CRITICAL,
                                title=f"Agent identity mismatch on port {registry.get_agent_port(name)}",
                                description=f"Expected {expected_agent}, but agent reports as {reported_agent}",
                                affected=[name, reported_agent],
                                recommendation=f"Check if wrong code is deployed or port is misconfigured"
                            ))
                        
                        # Check port in response matches
                        reported_port = data.get("port")
                        expected_port = registry.get_agent_port(name)
                        if reported_port and reported_port != expected_port:
                            issues.append(Issue(
                                id=f"port-mismatch-{name}",
                                category="port_mismatch",
                                severity=Severity.HIGH,
                                title=f"Agent {name} reports wrong port",
                                description=f"Registry says port {expected_port}, agent reports port {reported_port}",
                                affected=[name],
                                recommendation=f"Update agent code or registry to match"
                            ))
                
                except httpx.ConnectError:
                    # Already caught by port scanner
                    pass
                except Exception as e:
                    issues.append(Issue(
                        id=f"health-check-error-{name}",
                        category="health_error",
                        severity=Severity.MEDIUM,
                        title=f"Cannot verify agent {name}",
                        description=f"Health check failed: {str(e)}",
                        affected=[name],
                        recommendation=f"Check agent logs and ensure /health endpoint works"
                    ))
        
        return issues, checks


class CodeScanner:
    """Scan agent code directories for issues."""
    
    def scan(self) -> Tuple[List[Issue], int]:
        """Scan code directories."""
        issues = []
        checks = 0
        
        if not AGENTS_PATH.exists():
            return issues, checks
        
        # Find all Python files with port declarations
        port_files: Dict[int, List[Tuple[str, str]]] = {}  # port -> [(dir, file)]
        
        for agent_dir in AGENTS_PATH.iterdir():
            if not agent_dir.is_dir() or agent_dir.name.startswith('.'):
                continue
            
            for py_file in agent_dir.glob("*.py"):
                if py_file.name.startswith('__'):
                    continue
                
                checks += 1
                content = py_file.read_text()
                
                # Find port declarations
                port_matches = re.findall(r'(?:port["\s:=]+|Port:\s*)(\d{4})', content)
                for port_str in port_matches:
                    port = int(port_str)
                    if port not in port_files:
                        port_files[port] = []
                    port_files[port].append((agent_dir.name, py_file.name))
        
        # Check for code-level port conflicts
        for port, files in port_files.items():
            unique_dirs = set(f[0] for f in files)
            if len(unique_dirs) > 1:
                issues.append(Issue(
                    id=f"code-port-conflict-{port}",
                    category="code_conflict",
                    severity=Severity.HIGH,
                    title=f"Port {port} declared in multiple directories",
                    description=f"Directories: {', '.join(unique_dirs)}",
                    affected=list(unique_dirs),
                    recommendation=f"Remove duplicate code or fix port assignments"
                ))
        
        # Find duplicate directories (same functionality, different names)
        self._check_duplicates(issues)
        
        return issues, checks
    
    def _check_duplicates(self, issues: List[Issue]):
        """Check for duplicate agent directories."""
        # Known duplicates from the audit
        known_duplicates = [
            ("arwen", "eros", "EROS agent"),
            ("gandalf", "academic-guide", "ACADEMIC-GUIDE agent"),
            ("aragorn", "gym-coach", "GYM-COACH agent"),
            ("atlas", "atlas-infra", "ATLAS-INFRA agent (old ATLAS dir has wrong code)"),
        ]
        
        for dir1, dir2, description in known_duplicates:
            path1 = AGENTS_PATH / dir1
            path2 = AGENTS_PATH / dir2
            
            if path1.exists() and path2.exists():
                issues.append(Issue(
                    id=f"duplicate-dir-{dir1}-{dir2}",
                    category="duplicate_code",
                    severity=Severity.LOW,
                    title=f"Duplicate directories: {dir1} and {dir2}",
                    description=f"Both directories contain {description}",
                    affected=[dir1, dir2],
                    recommendation=f"Remove one directory and update any references"
                ))


class SystemdScanner:
    """Scan systemd services."""
    
    def scan(self) -> Tuple[List[Issue], int]:
        """Check systemd service status."""
        issues = []
        checks = 0
        
        # Get list of expected services
        agents = registry.get_agents()
        
        for name in agents.keys():
            service_name = f"leveredge-{name}.service"
            checks += 1
            
            # Check if service file exists
            service_path = Path(f"/etc/systemd/system/{service_name}")
            if not service_path.exists():
                # Not all agents need systemd - only flag core ones
                core_agents = ["atlas", "sentinel", "hermes", "chronos", "hades", "aegis", "argus", "event-bus"]
                if name.lower() in core_agents:
                    issues.append(Issue(
                        id=f"no-systemd-{name}",
                        category="missing_service",
                        severity=Severity.MEDIUM,
                        title=f"No systemd service for {name}",
                        description=f"Core agent {name} should have a systemd service for auto-restart",
                        affected=[name],
                        recommendation=f"Create /etc/systemd/system/{service_name}"
                    ))
                continue
            
            # Check if service is enabled and running
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0:
                    issues.append(Issue(
                        id=f"service-not-running-{name}",
                        category="service_down",
                        severity=Severity.HIGH,
                        title=f"Systemd service {service_name} not running",
                        description=f"Service exists but is not active",
                        affected=[name],
                        recommendation=f"Run: sudo systemctl start {service_name}"
                    ))
            except Exception as e:
                pass
        
        return issues, checks


class RegistryValidator:
    """Validate registry consistency."""
    
    def scan(self) -> Tuple[List[Issue], int]:
        """Validate registry file."""
        issues = []
        checks = 0
        
        try:
            data = registry.load(force=True)
        except Exception as e:
            issues.append(Issue(
                id="registry-parse-error",
                category="registry_error",
                severity=Severity.CRITICAL,
                title="Cannot parse agent-registry.yaml",
                description=str(e),
                affected=["registry"],
                recommendation="Fix YAML syntax errors in agent-registry.yaml"
            ))
            return issues, 1
        
        agents = data.get("agents", {})
        chains = data.get("chains", {})
        
        # Check each agent has required fields
        for name, config in agents.items():
            checks += 1
            
            if not config.get("connection", {}).get("url"):
                issues.append(Issue(
                    id=f"missing-url-{name}",
                    category="registry_incomplete",
                    severity=Severity.HIGH,
                    title=f"Agent {name} missing connection URL",
                    description=f"Registry entry for {name} has no connection.url",
                    affected=[name],
                    recommendation=f"Add connection.url to agent {name} in registry"
                ))
            
            if not config.get("actions"):
                issues.append(Issue(
                    id=f"no-actions-{name}",
                    category="registry_incomplete",
                    severity=Severity.LOW,
                    title=f"Agent {name} has no actions defined",
                    description=f"Registry entry for {name} has empty actions",
                    affected=[name],
                    recommendation=f"Add actions to agent {name} if it should be callable"
                ))
        
        # Check chains reference valid agents
        for chain_name, chain_config in chains.items():
            checks += 1
            steps = chain_config.get("steps", [])
            
            for step in steps:
                agent_ref = step.get("agent")
                if agent_ref and agent_ref.lower() not in [a.lower() for a in agents.keys()]:
                    issues.append(Issue(
                        id=f"invalid-chain-ref-{chain_name}-{agent_ref}",
                        category="invalid_reference",
                        severity=Severity.HIGH,
                        title=f"Chain {chain_name} references unknown agent {agent_ref}",
                        description=f"Step references agent '{agent_ref}' which is not in registry",
                        affected=[chain_name, agent_ref],
                        recommendation=f"Add {agent_ref} to registry or fix chain step"
                    ))
        
        return issues, checks


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN SCANNER ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════════════

class IntegrityScanner:
    """Orchestrates all integrity scans."""
    
    def __init__(self):
        self.port_scanner = PortScanner()
        self.identity_verifier = IdentityVerifier()
        self.code_scanner = CodeScanner()
        self.systemd_scanner = SystemdScanner()
        self.registry_validator = RegistryValidator()
    
    async def full_scan(self) -> IntegrityReport:
        """Run all integrity checks."""
        import uuid
        
        report_id = str(uuid.uuid4())[:8]
        started = datetime.utcnow()
        all_issues = []
        total_checks = 0
        
        # Run all scanners
        scanners = [
            ("Registry Validation", self.registry_validator.scan),
            ("Port Scan", self.port_scanner.scan),
            ("Identity Verification", self.identity_verifier.scan),
            ("Code Scan", self.code_scanner.scan),
            ("Systemd Scan", self.systemd_scanner.scan),
        ]
        
        for name, scanner in scanners:
            try:
                if asyncio.iscoroutinefunction(scanner):
                    issues, checks = await scanner()
                else:
                    issues, checks = scanner()
                all_issues.extend(issues)
                total_checks += checks
            except Exception as e:
                all_issues.append(Issue(
                    id=f"scanner-error-{name}",
                    category="scanner_error",
                    severity=Severity.HIGH,
                    title=f"Scanner {name} failed",
                    description=str(e),
                    affected=[name],
                    recommendation="Check PANOPTES logs"
                ))
        
        completed = datetime.utcnow()
        
        # Count by severity
        summary = {s.value: 0 for s in Severity}
        for issue in all_issues:
            summary[issue.severity.value] += 1
        
        return IntegrityReport(
            report_id=report_id,
            scan_started=started.isoformat(),
            scan_completed=completed.isoformat(),
            total_checks=total_checks,
            passed_checks=total_checks - len(all_issues),
            issues=all_issues,
            summary=summary
        )
    
    async def quick_scan(self) -> Dict:
        """Quick health overview."""
        issues = []
        
        # Just check ports and identity
        port_issues, _ = await self.port_scanner.scan()
        identity_issues, _ = await self.identity_verifier.scan()
        
        issues.extend(port_issues)
        issues.extend(identity_issues)
        
        critical = [i for i in issues if i.severity == Severity.CRITICAL]
        high = [i for i in issues if i.severity == Severity.HIGH]
        
        return {
            "status": "critical" if critical else "degraded" if high else "healthy",
            "critical_issues": len(critical),
            "high_issues": len(high),
            "total_issues": len(issues),
            "issues": [i.to_dict() for i in (critical + high)[:10]]  # Top 10
        }


scanner = IntegrityScanner()

# ═══════════════════════════════════════════════════════════════════════════════
# ALERTING
# ═══════════════════════════════════════════════════════════════════════════════

async def send_alert(severity: str, title: str, description: str):
    """Send alert via HERMES."""
    try:
        async with httpx.AsyncClient() as client:
            emoji = "🚨" if severity == "critical" else "⚠️" if severity == "high" else "ℹ️"
            await client.post(
                f"{HERMES_URL}/notify",
                json={
                    "message": f"{emoji} [PANOPTES] {title}\n{description}",
                    "priority": severity,
                    "channel": "telegram"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Alert failed: {e}")


async def log_to_event_bus(event_type: str, data: dict):
    """Log to Event Bus."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "PANOPTES",
                    "data": data
                },
                timeout=2.0
            )
    except:
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="PANOPTES - The All-Seeing Integrity Guardian",
    description="System integrity verification and audit",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store last scan result
last_report: Optional[IntegrityReport] = None


@app.get("/health")
async def health():
    """Health check."""
    today = date.today()
    days_to_launch = (LAUNCH_DATE - today).days
    
    return {
        "status": "healthy",
        "agent": "PANOPTES",
        "role": "Integrity Guardian",
        "port": PANOPTES_PORT,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "days_to_launch": days_to_launch,
        "last_scan": last_report.scan_completed if last_report else None,
        "registered_agents": len(registry.get_agents())
    }


@app.get("/status")
async def status():
    """Quick status overview."""
    return await scanner.quick_scan()


@app.post("/scan")
async def run_full_scan(background_tasks: BackgroundTasks):
    """Run full integrity scan."""
    global last_report
    
    report = await scanner.full_scan()
    last_report = report
    
    # Alert on critical issues
    critical = [i for i in report.issues if i.severity == Severity.CRITICAL]
    if critical:
        background_tasks.add_task(
            send_alert,
            "critical",
            f"Integrity Scan Found {len(critical)} Critical Issues",
            "\n".join(f"• {i.title}" for i in critical[:5])
        )
    
    # Log to event bus
    background_tasks.add_task(
        log_to_event_bus,
        "integrity_scan_completed",
        {
            "report_id": report.report_id,
            "total_issues": len(report.issues),
            "critical": report.summary.get("critical", 0),
            "health_score": report.to_dict()["health_score"]
        }
    )
    
    return report.to_dict()


@app.get("/scan/last")
async def get_last_scan():
    """Get last scan report."""
    if not last_report:
        raise HTTPException(404, "No scan has been run yet")
    return last_report.to_dict()


@app.get("/issues")
async def list_issues(severity: Optional[str] = None):
    """List current issues."""
    if not last_report:
        # Run quick scan
        result = await scanner.quick_scan()
        return {"issues": result["issues"]}
    
    issues = last_report.issues
    if severity:
        issues = [i for i in issues if i.severity.value == severity]
    
    return {"issues": [i.to_dict() for i in issues], "count": len(issues)}


@app.get("/ports")
async def scan_ports():
    """Scan ports only."""
    issues, checks = await scanner.port_scanner.scan()
    return {
        "checks": checks,
        "issues": [i.to_dict() for i in issues],
        "conflicts": [i.to_dict() for i in issues if i.category == "port_conflict"]
    }


@app.get("/agents/verify")
async def verify_agents():
    """Verify agent identities."""
    issues, checks = await scanner.identity_verifier.scan()
    return {
        "checks": checks,
        "issues": [i.to_dict() for i in issues],
        "mismatches": [i.to_dict() for i in issues if i.category == "identity_mismatch"]
    }


@app.get("/registry/validate")
async def validate_registry():
    """Validate registry file."""
    issues, checks = scanner.registry_validator.scan()
    return {
        "checks": checks,
        "valid": len(issues) == 0,
        "issues": [i.to_dict() for i in issues]
    }


@app.get("/dashboard")
async def dashboard():
    """Quick dashboard view."""
    status_result = await scanner.quick_scan()
    
    agents = registry.get_agents()
    chains = registry.get_chains()
    
    return {
        "system_status": status_result["status"],
        "registered_agents": len(agents),
        "registered_chains": len(chains),
        "critical_issues": status_result["critical_issues"],
        "high_issues": status_result["high_issues"],
        "last_scan": last_report.scan_completed if last_report else None,
        "health_score": last_report.to_dict()["health_score"] if last_report else None,
        "top_issues": status_result["issues"][:5]
    }


@app.on_event("startup")
async def startup():
    """Run initial scan on startup."""
    global last_report
    
    # Load registry
    registry.load()
    
    # Run initial scan
    last_report = await scanner.full_scan()
    
    # Log startup
    await log_to_event_bus("agent_started", {
        "agent": "PANOPTES",
        "port": PANOPTES_PORT,
        "initial_issues": len(last_report.issues)
    })
    
    print(f"👁️ PANOPTES - The All-Seeing One - started on port {PANOPTES_PORT}")
    print(f"   Initial scan: {len(last_report.issues)} issues found")
    print(f"   Health score: {last_report.to_dict()['health_score']}%")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PANOPTES_PORT)
```

---

## Section 3: Requirements

Create `/opt/leveredge/control-plane/agents/panoptes/requirements.txt`:

```
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pyyaml>=6.0
pydantic>=2.0
```

---

## Section 4: Systemd Service

Create `/opt/leveredge/shared/systemd/leveredge-panoptes.service`:

```ini
[Unit]
Description=LeverEdge PANOPTES Integrity Guardian
After=network.target leveredge-atlas.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/leveredge/control-plane/agents/panoptes
Environment=PYTHONUNBUFFERED=1
Environment=REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml
Environment=AGENTS_PATH=/opt/leveredge/control-plane/agents
Environment=EVENT_BUS_URL=http://localhost:8099
Environment=HERMES_URL=http://localhost:8014
ExecStart=/opt/leveredge/shared/venv/bin/python panoptes.py
Restart=always
RestartSec=10
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
  # PANOPTES - Integrity Guardian
  # ─────────────────────────────────────────────────────────────────────────────
  panoptes:
    name: PANOPTES
    version: "1.0"
    description: "The All-Seeing Integrity Guardian - system verification and audit"
    category: security
    llm_powered: false

    connection:
      url: http://panoptes:8022
      health_endpoint: /health
      timeout_ms: 30000

    capabilities:
      - registry_validation
      - port_scanning
      - identity_verification
      - code_scanning
      - integrity_reporting

    actions:

      scan:
        endpoint: /scan
        method: POST
        description: "Run full integrity scan"
        timeout_ms: 60000
        params: []
        returns:
          type: object
          fields: [report_id, total_checks, passed_checks, issues, health_score]

      status:
        endpoint: /status
        method: GET
        description: "Quick status overview"
        timeout_ms: 10000
        params: []
        returns:
          type: object
          fields: [status, critical_issues, high_issues, total_issues]

      dashboard:
        endpoint: /dashboard
        method: GET
        description: "Dashboard view with key metrics"
        timeout_ms: 10000
        params: []
        returns:
          type: object
          fields: [system_status, registered_agents, critical_issues, health_score]

      ports:
        endpoint: /ports
        method: GET
        description: "Scan for port conflicts"
        timeout_ms: 30000
        params: []
        returns:
          type: object
          fields: [checks, issues, conflicts]

      verify-agents:
        endpoint: /agents/verify
        method: GET
        description: "Verify agent identities"
        timeout_ms: 60000
        params: []
        returns:
          type: object
          fields: [checks, issues, mismatches]

      validate-registry:
        endpoint: /registry/validate
        method: GET
        description: "Validate registry file"
        timeout_ms: 10000
        params: []
        returns:
          type: object
          fields: [checks, valid, issues]
```

---

## Section 6: Fix Known Issues Script

Create `/opt/leveredge/shared/scripts/fix-port-conflicts.sh`:

```bash
#!/bin/bash
# Fix known port conflicts discovered by audit

echo "🔧 Fixing known port conflicts..."

# Issue 1: VARYS (8020) vs CERBERUS (8020)
# Decision: VARYS gets 8023, CERBERUS keeps 8020
echo "→ VARYS: Moving from 8020 to 8023"
# Update will be in registry

# Issue 2: DAEDALUS vs GENDRY (both 8202)  
# Decision: Keep DAEDALUS at 8202, GENDRY is duplicate - remove
echo "→ Removing duplicate gendry directory (same as daedalus)"

# Issue 3: Duplicate directories to clean up
echo "→ Marking duplicate directories for review:"
echo "   - arwen/ (duplicate of eros/)"
echo "   - gandalf/ (duplicate of academic-guide/)"
echo "   - aragorn/ (duplicate of gym-coach/)"
echo "   - atlas/ (old wrong code, atlas-orchestrator/ is correct)"

echo ""
echo "Registry updates needed:"
echo "1. Change VARYS port from 8020 to 8023"
echo "2. Verify CERBERUS stays at 8020"
echo ""
echo "Run PANOPTES scan after fixes to verify: curl http://localhost:8022/scan"
```

---

## Section 7: Cron for Daily Scan

Add to crontab:

```bash
# Daily integrity scan at 6 AM
0 6 * * * curl -s -X POST http://localhost:8022/scan > /dev/null 2>&1
```

---

## Section 8: Deployment Commands

```bash
# Create directory
mkdir -p /opt/leveredge/control-plane/agents/panoptes

# Copy files (GSD will create them)

# Install systemd service
sudo cp /opt/leveredge/shared/systemd/leveredge-panoptes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable leveredge-panoptes
sudo systemctl start leveredge-panoptes

# Verify
curl http://localhost:8022/health
curl http://localhost:8022/dashboard
```

---

## GSD Command

```
/gsd /opt/leveredge/specs/gsd-build-panoptes.md

CONTEXT: After the ATLAS incident (agent didn't exist for months), we need 
a system integrity checker. PANOPTES will be "The All-Seeing One" - verifying
that the system is what it claims to be.

CRITICAL: 
- Port 8022 (Security Fleet)
- Must detect: port conflicts, identity mismatches, missing agents
- Runs initial scan on startup
- Alerts via HERMES on critical issues

KNOWN ISSUES TO DETECT:
- Port 8020: VARYS and CERBERUS conflict
- Port 8202: DAEDALUS and GENDRY conflict  
- Duplicate directories: arwen/eros, gandalf/academic-guide, etc.
- Old atlas/ directory has wrong code (should be atlas-infra)

After deployment, run: curl http://localhost:8022/scan | python3 -m json.tool
```

---

## Expected Outcome

After deployment, PANOPTES will:
1. **Detect all known issues** on first scan
2. **Alert on critical problems** via HERMES
3. **Provide dashboard** at /dashboard
4. **Run daily scans** via cron
5. **Prevent future ATLAS-type incidents**

Health score should start low (due to known issues), then improve as they're fixed.

---

## Summary

| Attribute | Value |
|-----------|-------|
| **Name** | PANOPTES |
| **Meaning** | "The All-Seeing One" (Argus Panoptes - 100-eyed giant) |
| **Domain** | Security Fleet |
| **Port** | 8022 |
| **Role** | System integrity verification |
| **Key Features** | Port scanning, identity verification, registry validation, daily reports |
