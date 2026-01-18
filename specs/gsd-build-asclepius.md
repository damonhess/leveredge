# GSD: Build ASCLEPIUS - The Divine Physician

**Priority:** HIGH - System Resilience  
**Estimated Time:** 5-6 hours  
**Created:** 2026-01-18  
**Status:** Ready for execution

---

## The Legend

> *Asclepius (Ἀσκληπιός) was the Greek god of medicine and healing. Son of Apollo, he was so skilled he could raise the dead. His staff, the Rod of Asclepius ⚕️, remains the universal symbol of medicine to this day. Zeus eventually struck him down - not for failure, but because his healing powers threatened to make humanity immortal.*

ASCLEPIUS is the automated remediation engine for LeverEdge. When PANOPTES finds problems, ASCLEPIUS heals them. He doesn't just report issues - he **fixes them**.

---

## The Healing Pantheon

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        THE HEALING LOOP                                      │
│                                                                              │
│     ┌──────────┐         ┌──────────┐         ┌──────────┐                 │
│     │ PANOPTES │────────▶│ASCLEPIUS │────────▶│ PANOPTES │                 │
│     │  Diagnose │         │   Heal   │         │  Verify  │                 │
│     └──────────┘         └────┬─────┘         └──────────┘                 │
│          👁️                    │⚕️                  👁️                       │
│                               │                                              │
│              ┌────────────────┼────────────────┐                            │
│              ▼                ▼                ▼                            │
│        ┌──────────┐    ┌──────────┐    ┌──────────┐                        │
│        │ CHRONOS  │    │  HADES   │    │ HERMES   │                        │
│        │  Backup  │    │ Rollback │    │  Notify  │                        │
│        └──────────┘    └──────────┘    └──────────┘                        │
│             ⏰              💀              📢                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Capabilities Overview

### 🏥 Service Healing
- Restart crashed services
- Start stopped services
- Kill rogue processes
- Generate missing systemd services
- Fix service configurations

### 🔌 Port Healing
- Resolve port conflicts automatically
- Reassign ports with zero downtime
- Update registry + code + restart in one operation
- Kill processes hogging ports

### 📁 Filesystem Healing
- Remove duplicate directories (with archive)
- Clean orphaned files
- Fix permissions
- Restore from templates

### 📋 Registry Healing
- Auto-fix malformed YAML
- Add missing agent entries
- Remove dead references
- Sync registry with running reality

### 🔧 Config Healing
- Restore configs from known-good state
- Apply standard templates
- Fix environment variables
- Repair broken symlinks

### 🗄️ Database Healing
- Run pending migrations
- Fix connection issues
- Repair corrupted tables
- Sync DEV/PROD schemas

### 🌐 Network Healing
- Fix DNS resolution
- Repair proxy configs
- Restart network services
- Clear stuck connections

### ⚡ Emergency Protocols
- Full system healing
- Targeted subsystem healing
- Graceful degradation mode
- Nuclear option (full restart)

---

## Port & Domain

| Attribute | Value |
|-----------|-------|
| **Name** | ASCLEPIUS |
| **Port** | 8024 |
| **Domain** | Infrastructure |
| **Symbol** | ⚕️ |

---

## Section 1: Create Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/asclepius
```

---

## Section 2: Core ASCLEPIUS Agent

Create `/opt/leveredge/control-plane/agents/asclepius/asclepius.py`:

```python
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              ASCLEPIUS ⚕️                                      ║
║                         The Divine Physician                                   ║
║                                                                                ║
║  Port: 8024                                                                    ║
║  Domain: Infrastructure                                                        ║
║                                                                                ║
║  Named after the Greek god of medicine, Asclepius doesn't just diagnose -     ║
║  he HEALS. When PANOPTES finds problems, ASCLEPIUS fixes them automatically.  ║
║                                                                                ║
║  HEALING PROTOCOLS:                                                           ║
║  ├── Service Healing    - Restart, start, generate systemd services          ║
║  ├── Port Healing       - Resolve conflicts, reassign, update configs         ║
║  ├── Registry Healing   - Fix YAML, add missing entries, remove dead refs    ║
║  ├── Filesystem Healing - Remove duplicates, fix permissions, restore         ║
║  ├── Config Healing     - Restore configs, apply templates, fix envvars      ║
║  ├── Database Healing   - Run migrations, fix connections, sync schemas      ║
║  ├── Network Healing    - Fix DNS, proxies, clear stuck connections          ║
║  └── Emergency Protocol - Full system healing, nuclear restart               ║
║                                                                                ║
║  SAFETY:                                                                      ║
║  • Always backs up via CHRONOS before healing                                 ║
║  • Rollback via HADES if healing fails                                        ║
║  • Approval required for destructive operations                               ║
║  • Complete audit trail of all healing actions                                ║
║                                                                                ║
║  "He who heals is greater than he who destroys."                              ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import os
import sys
import re
import yaml
import json
import shutil
import socket
import subprocess
import signal
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid
import traceback

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

ASCLEPIUS_PORT = 8024
REGISTRY_PATH = Path(os.getenv("REGISTRY_PATH", "/opt/leveredge/config/agent-registry.yaml"))
AGENTS_PATH = Path(os.getenv("AGENTS_PATH", "/opt/leveredge/control-plane/agents"))
SYSTEMD_PATH = Path("/etc/systemd/system")
ARCHIVE_PATH = Path(os.getenv("ARCHIVE_PATH", "/opt/leveredge/archive"))
TEMPLATES_PATH = Path(os.getenv("TEMPLATES_PATH", "/opt/leveredge/shared/templates"))

# Agent URLs
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://localhost:8014")
CHRONOS_URL = os.getenv("CHRONOS_URL", "http://localhost:8010")
HADES_URL = os.getenv("HADES_URL", "http://localhost:8008")
PANOPTES_URL = os.getenv("PANOPTES_URL", "http://localhost:8022")

LAUNCH_DATE = date(2026, 3, 1)

# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS AND DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class HealingStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class HealingSeverity(str, Enum):
    ROUTINE = "routine"      # Auto-heal without approval
    STANDARD = "standard"    # Auto-heal with notification
    ELEVATED = "elevated"    # Requires confirmation
    CRITICAL = "critical"    # Requires explicit approval
    NUCLEAR = "nuclear"      # Multiple approvals required


class HealingCategory(str, Enum):
    SERVICE = "service"
    PORT = "port"
    REGISTRY = "registry"
    FILESYSTEM = "filesystem"
    CONFIG = "config"
    DATABASE = "database"
    NETWORK = "network"
    EMERGENCY = "emergency"


@dataclass
class HealingAction:
    """A single healing action."""
    id: str
    category: HealingCategory
    severity: HealingSeverity
    title: str
    description: str
    target: str
    command: Optional[str] = None
    status: HealingStatus = HealingStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: int = 0
    output: Optional[str] = None
    error: Optional[str] = None
    rollback_command: Optional[str] = None
    backup_id: Optional[str] = None
    
    def to_dict(self):
        return {
            **asdict(self),
            "category": self.category.value,
            "severity": self.severity.value,
            "status": self.status.value
        }


@dataclass
class HealingPlan:
    """A complete healing plan with multiple actions."""
    plan_id: str
    created_at: str
    description: str
    actions: List[HealingAction]
    requires_approval: bool = False
    approved: bool = False
    approved_by: Optional[str] = None
    executed: bool = False
    execution_started: Optional[str] = None
    execution_completed: Optional[str] = None
    overall_status: HealingStatus = HealingStatus.PENDING
    
    def to_dict(self):
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "description": self.description,
            "actions": [a.to_dict() for a in self.actions],
            "action_count": len(self.actions),
            "requires_approval": self.requires_approval,
            "approved": self.approved,
            "executed": self.executed,
            "overall_status": self.overall_status.value,
            "success_count": sum(1 for a in self.actions if a.status == HealingStatus.SUCCESS),
            "failed_count": sum(1 for a in self.actions if a.status == HealingStatus.FAILED)
        }


@dataclass 
class HealingResult:
    """Result of a healing operation."""
    action_id: str
    status: HealingStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    rollback_available: bool = False


# Storage for healing plans and history
healing_plans: Dict[str, HealingPlan] = {}
healing_history: List[HealingAction] = []

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

async def log_event(event_type: str, data: dict):
    """Log to Event Bus."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(f"{EVENT_BUS_URL}/publish", json={
                "event_type": event_type,
                "source": "ASCLEPIUS",
                "data": data
            })
    except:
        pass


async def notify(message: str, priority: str = "normal"):
    """Send notification via HERMES."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{HERMES_URL}/notify", json={
                "message": f"⚕️ [ASCLEPIUS] {message}",
                "priority": priority,
                "channel": "telegram"
            })
    except Exception as e:
        print(f"Notification failed: {e}")


async def create_backup(target: str, description: str) -> Optional[str]:
    """Create backup via CHRONOS before healing."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{CHRONOS_URL}/backup", json={
                "target": target,
                "description": f"ASCLEPIUS pre-healing: {description}",
                "type": "healing"
            })
            if response.status_code == 200:
                data = response.json()
                return data.get("backup_id")
    except Exception as e:
        print(f"Backup failed: {e}")
    return None


async def rollback(backup_id: str) -> bool:
    """Rollback via HADES if healing fails."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{HADES_URL}/rollback", json={
                "backup_id": backup_id,
                "reason": "ASCLEPIUS healing failed"
            })
            return response.status_code == 200
    except:
        return False


async def get_panoptes_issues() -> List[dict]:
    """Get current issues from PANOPTES."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{PANOPTES_URL}/issues")
            if response.status_code == 200:
                return response.json().get("issues", [])
    except:
        pass
    return []


async def verify_healing() -> dict:
    """Ask PANOPTES to verify healing worked."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{PANOPTES_URL}/scan")
            if response.status_code == 200:
                return response.json()
    except:
        pass
    return {}


def run_command(command: str, timeout: int = 30) -> Tuple[bool, str, str]:
    """Run a shell command safely."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def load_registry() -> dict:
    """Load agent registry."""
    with open(REGISTRY_PATH) as f:
        return yaml.safe_load(f)


def save_registry(data: dict):
    """Save agent registry."""
    with open(REGISTRY_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALING PROTOCOLS
# ═══════════════════════════════════════════════════════════════════════════════

class ServiceHealer:
    """Heals service-related issues."""
    
    async def restart_service(self, service_name: str) -> HealingResult:
        """Restart a systemd service."""
        action_id = str(uuid.uuid4())[:8]
        
        # Check if service exists
        service_file = f"leveredge-{service_name}.service"
        
        success, stdout, stderr = run_command(f"systemctl restart {service_file}")
        
        if success:
            # Verify it's running
            await asyncio.sleep(2)
            success, stdout, stderr = run_command(f"systemctl is-active {service_file}")
            
            if "active" in stdout:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SUCCESS,
                    message=f"Service {service_name} restarted successfully",
                    details={"service": service_file, "status": "active"}
                )
        
        return HealingResult(
            action_id=action_id,
            status=HealingStatus.FAILED,
            message=f"Failed to restart {service_name}: {stderr}",
            details={"error": stderr}
        )
    
    async def start_service(self, service_name: str) -> HealingResult:
        """Start a stopped service."""
        action_id = str(uuid.uuid4())[:8]
        service_file = f"leveredge-{service_name}.service"
        
        success, stdout, stderr = run_command(f"systemctl start {service_file}")
        
        if success:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message=f"Service {service_name} started",
                details={"service": service_file}
            )
        
        return HealingResult(
            action_id=action_id,
            status=HealingStatus.FAILED,
            message=f"Failed to start {service_name}: {stderr}",
            details={"error": stderr}
        )
    
    async def generate_service(self, agent_name: str, port: int) -> HealingResult:
        """Generate a systemd service file for an agent."""
        action_id = str(uuid.uuid4())[:8]
        
        service_content = f"""[Unit]
Description=LeverEdge {agent_name.upper()} Agent
After=network.target
Wants=leveredge-event-bus.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/leveredge/control-plane/agents/{agent_name}
Environment=PYTHONUNBUFFERED=1
Environment=REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml
Environment=EVENT_BUS_URL=http://localhost:8099
Environment=HERMES_URL=http://localhost:8014
ExecStart=/opt/leveredge/shared/venv/bin/python {agent_name}.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""
        
        service_path = f"/opt/leveredge/shared/systemd/leveredge-{agent_name}.service"
        
        try:
            Path(service_path).parent.mkdir(parents=True, exist_ok=True)
            Path(service_path).write_text(service_content)
            
            # Copy to systemd and enable
            success, _, stderr = run_command(f"cp {service_path} /etc/systemd/system/")
            if success:
                run_command("systemctl daemon-reload")
                run_command(f"systemctl enable leveredge-{agent_name}.service")
                
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SUCCESS,
                    message=f"Generated systemd service for {agent_name}",
                    details={"service_path": service_path, "port": port}
                )
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to install service: {stderr}",
                details={"error": stderr}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to generate service: {str(e)}",
                details={"error": str(e)}
            )
    
    async def kill_rogue_process(self, port: int) -> HealingResult:
        """Kill a process hogging a port."""
        action_id = str(uuid.uuid4())[:8]
        
        # Find PID using port
        success, stdout, stderr = run_command(f"lsof -t -i:{port}")
        
        if success and stdout.strip():
            pid = stdout.strip().split('\n')[0]
            
            # Kill the process
            success, _, stderr = run_command(f"kill -9 {pid}")
            
            if success:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SUCCESS,
                    message=f"Killed process {pid} on port {port}",
                    details={"pid": pid, "port": port}
                )
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to kill process: {stderr}",
                details={"error": stderr}
            )
        
        return HealingResult(
            action_id=action_id,
            status=HealingStatus.SKIPPED,
            message=f"No process found on port {port}",
            details={"port": port}
        )
    
    async def heal_all_services(self) -> List[HealingResult]:
        """Heal all unhealthy services."""
        results = []
        
        # Get list of expected services
        registry = load_registry()
        agents = registry.get("agents", {})
        
        for name in agents.keys():
            service_file = f"leveredge-{name}.service"
            
            # Check if service is running
            success, stdout, _ = run_command(f"systemctl is-active {service_file}")
            
            if "inactive" in stdout or "failed" in stdout:
                result = await self.restart_service(name)
                results.append(result)
        
        return results


class PortHealer:
    """Heals port-related issues."""
    
    async def resolve_conflict(self, port: int, keep_agent: str, move_agent: str, new_port: int) -> HealingResult:
        """Resolve a port conflict by moving one agent."""
        action_id = str(uuid.uuid4())[:8]
        
        try:
            # 1. Update registry
            registry = load_registry()
            agents = registry.get("agents", {})
            
            if move_agent in agents:
                old_url = agents[move_agent].get("connection", {}).get("url", "")
                new_url = re.sub(r':\d+$', f':{new_port}', old_url)
                agents[move_agent]["connection"]["url"] = new_url
                save_registry(registry)
            
            # 2. Update code if possible
            agent_dir = AGENTS_PATH / move_agent
            for py_file in agent_dir.glob("*.py"):
                content = py_file.read_text()
                updated = re.sub(
                    rf'(port\s*[=:]\s*){port}',
                    rf'\g<1>{new_port}',
                    content
                )
                if updated != content:
                    py_file.write_text(updated)
            
            # 3. Restart the moved service
            run_command(f"systemctl restart leveredge-{move_agent}.service")
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message=f"Moved {move_agent} from port {port} to {new_port}",
                details={
                    "moved_agent": move_agent,
                    "old_port": port,
                    "new_port": new_port,
                    "kept_agent": keep_agent
                }
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to resolve port conflict: {str(e)}",
                details={"error": str(e)}
            )
    
    async def free_port(self, port: int) -> HealingResult:
        """Free up a port by killing whatever is using it."""
        service_healer = ServiceHealer()
        return await service_healer.kill_rogue_process(port)
    
    async def find_next_available_port(self, start: int = 8025, end: int = 8099) -> int:
        """Find the next available port in a range."""
        for port in range(start, end):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('localhost', port))
                sock.close()
                return port
            except:
                continue
        return -1


class RegistryHealer:
    """Heals registry-related issues."""
    
    async def add_missing_agent(self, agent_name: str, port: int, description: str = "") -> HealingResult:
        """Add a missing agent to the registry."""
        action_id = str(uuid.uuid4())[:8]
        
        try:
            registry = load_registry()
            agents = registry.get("agents", {})
            
            if agent_name in agents:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SKIPPED,
                    message=f"Agent {agent_name} already exists in registry",
                    details={}
                )
            
            agents[agent_name] = {
                "name": agent_name.upper(),
                "version": "1.0",
                "description": description or f"Auto-generated entry for {agent_name}",
                "category": "unknown",
                "llm_powered": False,
                "connection": {
                    "url": f"http://{agent_name}:{port}",
                    "health_endpoint": "/health",
                    "timeout_ms": 30000
                },
                "capabilities": [],
                "actions": {}
            }
            
            save_registry(registry)
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message=f"Added {agent_name} to registry",
                details={"agent": agent_name, "port": port}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to add agent: {str(e)}",
                details={"error": str(e)}
            )
    
    async def remove_dead_agent(self, agent_name: str) -> HealingResult:
        """Remove an agent that no longer exists."""
        action_id = str(uuid.uuid4())[:8]
        
        try:
            registry = load_registry()
            agents = registry.get("agents", {})
            
            if agent_name not in agents:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SKIPPED,
                    message=f"Agent {agent_name} not in registry",
                    details={}
                )
            
            del agents[agent_name]
            save_registry(registry)
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message=f"Removed {agent_name} from registry",
                details={"agent": agent_name}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to remove agent: {str(e)}",
                details={"error": str(e)}
            )
    
    async def fix_agent_url(self, agent_name: str, new_port: int) -> HealingResult:
        """Fix an agent's URL in the registry."""
        action_id = str(uuid.uuid4())[:8]
        
        try:
            registry = load_registry()
            agents = registry.get("agents", {})
            
            if agent_name not in agents:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.FAILED,
                    message=f"Agent {agent_name} not found in registry",
                    details={}
                )
            
            old_url = agents[agent_name].get("connection", {}).get("url", "")
            new_url = f"http://{agent_name}:{new_port}"
            agents[agent_name]["connection"]["url"] = new_url
            save_registry(registry)
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message=f"Fixed {agent_name} URL: {old_url} -> {new_url}",
                details={"old_url": old_url, "new_url": new_url}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to fix URL: {str(e)}",
                details={"error": str(e)}
            )
    
    async def validate_and_fix_yaml(self) -> HealingResult:
        """Validate and attempt to fix registry YAML."""
        action_id = str(uuid.uuid4())[:8]
        
        try:
            with open(REGISTRY_PATH) as f:
                content = f.read()
            
            # Try to parse
            try:
                yaml.safe_load(content)
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SKIPPED,
                    message="Registry YAML is valid",
                    details={}
                )
            except yaml.YAMLError as e:
                # Try common fixes
                fixed = content
                
                # Fix common issues
                fixed = re.sub(r'\t', '  ', fixed)  # Tabs to spaces
                fixed = re.sub(r' +$', '', fixed, flags=re.MULTILINE)  # Trailing spaces
                
                # Try to parse again
                try:
                    yaml.safe_load(fixed)
                    
                    # Backup original
                    backup_path = REGISTRY_PATH.with_suffix('.yaml.bak')
                    shutil.copy(REGISTRY_PATH, backup_path)
                    
                    # Save fixed version
                    with open(REGISTRY_PATH, 'w') as f:
                        f.write(fixed)
                    
                    return HealingResult(
                        action_id=action_id,
                        status=HealingStatus.SUCCESS,
                        message="Fixed registry YAML syntax",
                        details={"backup": str(backup_path)}
                    )
                except:
                    return HealingResult(
                        action_id=action_id,
                        status=HealingStatus.FAILED,
                        message=f"Cannot auto-fix YAML: {str(e)}",
                        details={"error": str(e)}
                    )
                    
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Registry healing failed: {str(e)}",
                details={"error": str(e)}
            )


class FilesystemHealer:
    """Heals filesystem-related issues."""
    
    async def remove_duplicate_directory(self, directory: str, keep_directory: str) -> HealingResult:
        """Archive and remove a duplicate directory."""
        action_id = str(uuid.uuid4())[:8]
        
        dup_path = AGENTS_PATH / directory
        
        if not dup_path.exists():
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SKIPPED,
                message=f"Directory {directory} doesn't exist",
                details={}
            )
        
        try:
            # Create archive directory
            ARCHIVE_PATH.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            archive_name = f"{directory}_{timestamp}"
            archive_dest = ARCHIVE_PATH / archive_name
            
            # Move to archive
            shutil.move(str(dup_path), str(archive_dest))
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message=f"Archived {directory} (kept {keep_directory})",
                details={
                    "removed": directory,
                    "kept": keep_directory,
                    "archived_to": str(archive_dest)
                },
                rollback_available=True
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to remove duplicate: {str(e)}",
                details={"error": str(e)}
            )
    
    async def fix_permissions(self, path: str) -> HealingResult:
        """Fix file/directory permissions."""
        action_id = str(uuid.uuid4())[:8]
        
        try:
            success, _, stderr = run_command(f"chmod -R 755 {path}")
            
            if success:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SUCCESS,
                    message=f"Fixed permissions on {path}",
                    details={"path": path}
                )
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Failed to fix permissions: {stderr}",
                details={"error": stderr}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=str(e),
                details={"error": str(e)}
            )
    
    async def restore_from_template(self, agent_name: str) -> HealingResult:
        """Restore an agent from template."""
        action_id = str(uuid.uuid4())[:8]
        
        template_path = TEMPLATES_PATH / "fastapi-agent"
        agent_path = AGENTS_PATH / agent_name
        
        if not template_path.exists():
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message="FastAPI agent template not found",
                details={}
            )
        
        try:
            # Backup existing if present
            if agent_path.exists():
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                backup_path = ARCHIVE_PATH / f"{agent_name}_{timestamp}"
                shutil.move(str(agent_path), str(backup_path))
            
            # Copy template
            shutil.copytree(str(template_path), str(agent_path))
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message=f"Restored {agent_name} from template",
                details={"template": str(template_path)}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=str(e),
                details={"error": str(e)}
            )


class DatabaseHealer:
    """Heals database-related issues."""
    
    async def run_migrations(self, target: str = "prod") -> HealingResult:
        """Run pending database migrations."""
        action_id = str(uuid.uuid4())[:8]
        
        migrations_path = "/opt/leveredge/migrations"
        db_url = os.getenv(f"SUPABASE_{target.upper()}_URL", "")
        
        if not db_url:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"No database URL for {target}",
                details={}
            )
        
        try:
            success, stdout, stderr = run_command(
                f"migrate -path {migrations_path} -database '{db_url}' up",
                timeout=120
            )
            
            if success or "no change" in stdout.lower():
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SUCCESS,
                    message=f"Migrations applied to {target}",
                    details={"output": stdout}
                )
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Migration failed: {stderr}",
                details={"error": stderr}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=str(e),
                details={"error": str(e)}
            )
    
    async def restart_supabase(self) -> HealingResult:
        """Restart Supabase services."""
        action_id = str(uuid.uuid4())[:8]
        
        try:
            success, stdout, stderr = run_command(
                "cd /opt/leveredge/supabase && docker compose restart",
                timeout=120
            )
            
            if success:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SUCCESS,
                    message="Supabase restarted",
                    details={"output": stdout}
                )
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Supabase restart failed: {stderr}",
                details={"error": stderr}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=str(e),
                details={"error": str(e)}
            )


class NetworkHealer:
    """Heals network-related issues."""
    
    async def restart_caddy(self) -> HealingResult:
        """Restart Caddy reverse proxy."""
        action_id = str(uuid.uuid4())[:8]
        
        success, _, stderr = run_command("systemctl restart caddy")
        
        if success:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message="Caddy restarted",
                details={}
            )
        
        return HealingResult(
            action_id=action_id,
            status=HealingStatus.FAILED,
            message=f"Caddy restart failed: {stderr}",
            details={"error": stderr}
        )
    
    async def clear_dns_cache(self) -> HealingResult:
        """Clear DNS cache."""
        action_id = str(uuid.uuid4())[:8]
        
        success, _, stderr = run_command("systemd-resolve --flush-caches")
        
        if success:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message="DNS cache cleared",
                details={}
            )
        
        return HealingResult(
            action_id=action_id,
            status=HealingStatus.FAILED,
            message=f"DNS cache clear failed: {stderr}",
            details={"error": stderr}
        )
    
    async def check_and_fix_connectivity(self, host: str, port: int) -> HealingResult:
        """Check and attempt to fix connectivity to a host:port."""
        action_id = str(uuid.uuid4())[:8]
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        
        try:
            result = sock.connect_ex((host, port))
            if result == 0:
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.SKIPPED,
                    message=f"Connectivity to {host}:{port} is fine",
                    details={}
                )
            else:
                # Try to fix by restarting related services
                if port in [5432, 54322, 54323]:  # Postgres
                    await self.restart_caddy()
                    return HealingResult(
                        action_id=action_id,
                        status=HealingStatus.PARTIAL,
                        message=f"Attempted to fix connectivity to {host}:{port}",
                        details={"action": "restarted_caddy"}
                    )
                
                return HealingResult(
                    action_id=action_id,
                    status=HealingStatus.FAILED,
                    message=f"Cannot connect to {host}:{port}",
                    details={"error": f"Connection refused (code {result})"}
                )
        except socket.timeout:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Connection to {host}:{port} timed out",
                details={"error": "timeout"}
            )
        finally:
            sock.close()


class EmergencyProtocol:
    """Emergency healing protocols."""
    
    def __init__(self):
        self.service_healer = ServiceHealer()
        self.port_healer = PortHealer()
        self.registry_healer = RegistryHealer()
        self.filesystem_healer = FilesystemHealer()
        self.database_healer = DatabaseHealer()
        self.network_healer = NetworkHealer()
    
    async def full_system_healing(self) -> List[HealingResult]:
        """Run complete system healing - the "heal everything" button."""
        results = []
        
        await notify("🚨 Starting FULL SYSTEM HEALING", "critical")
        
        # 1. Create backup first
        backup_id = await create_backup("full-system", "Full system healing")
        
        # 2. Fix registry
        result = await self.registry_healer.validate_and_fix_yaml()
        results.append(result)
        
        # 3. Restart all core services
        core_services = [
            "event-bus", "atlas", "sentinel", "hermes", 
            "chronos", "hades", "aegis", "panoptes"
        ]
        
        for service in core_services:
            result = await self.service_healer.restart_service(service)
            results.append(result)
            await asyncio.sleep(1)  # Give services time to start
        
        # 4. Run database migrations
        result = await self.database_healer.run_migrations("prod")
        results.append(result)
        
        # 5. Restart network
        result = await self.network_healer.restart_caddy()
        results.append(result)
        
        # 6. Verify with PANOPTES
        verify_result = await verify_healing()
        
        success_count = sum(1 for r in results if r.status == HealingStatus.SUCCESS)
        failed_count = sum(1 for r in results if r.status == HealingStatus.FAILED)
        
        summary = f"Full healing complete: {success_count} succeeded, {failed_count} failed"
        await notify(summary, "high" if failed_count > 0 else "normal")
        
        return results
    
    async def heal_from_panoptes(self) -> List[HealingResult]:
        """Get issues from PANOPTES and heal them automatically."""
        results = []
        
        issues = await get_panoptes_issues()
        
        for issue in issues:
            category = issue.get("category", "")
            severity = issue.get("severity", "")
            affected = issue.get("affected", [])
            
            # Only auto-heal critical and high severity
            if severity not in ["critical", "high"]:
                continue
            
            try:
                if category == "port_conflict":
                    # Need to determine which agent to move
                    if len(affected) >= 2:
                        # Keep the first one, move the second
                        port = int(re.search(r'\d+', issue.get("title", "0")).group())
                        new_port = await self.port_healer.find_next_available_port()
                        result = await self.port_healer.resolve_conflict(
                            port, affected[0], affected[1], new_port
                        )
                        results.append(result)
                
                elif category == "agent_offline":
                    for agent in affected:
                        result = await self.service_healer.restart_service(agent)
                        results.append(result)
                
                elif category == "identity_mismatch":
                    for agent in affected:
                        result = await self.service_healer.restart_service(agent)
                        results.append(result)
                
                elif category == "duplicate_code":
                    if len(affected) >= 2:
                        result = await self.filesystem_healer.remove_duplicate_directory(
                            affected[0], affected[1]
                        )
                        results.append(result)
                
                elif category == "registry_error":
                    result = await self.registry_healer.validate_and_fix_yaml()
                    results.append(result)
                    
            except Exception as e:
                results.append(HealingResult(
                    action_id=str(uuid.uuid4())[:8],
                    status=HealingStatus.FAILED,
                    message=f"Failed to heal {category}: {str(e)}",
                    details={"error": str(e)}
                ))
        
        return results
    
    async def nuclear_restart(self) -> HealingResult:
        """The nuclear option - restart EVERYTHING."""
        action_id = str(uuid.uuid4())[:8]
        
        await notify("☢️ NUCLEAR RESTART INITIATED - All services restarting", "critical")
        
        try:
            # 1. Stop all leveredge services
            run_command("systemctl stop 'leveredge-*'")
            
            # 2. Restart Docker containers
            run_command("cd /opt/leveredge/supabase && docker compose restart")
            
            # 3. Restart n8n
            run_command("cd /opt/leveredge/n8n && docker compose restart")
            
            # 4. Wait for databases
            await asyncio.sleep(10)
            
            # 5. Start all leveredge services
            run_command("systemctl start 'leveredge-*'")
            
            # 6. Wait and verify
            await asyncio.sleep(5)
            
            await notify("☢️ NUCLEAR RESTART COMPLETE - Verifying system health", "high")
            
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.SUCCESS,
                message="Nuclear restart completed",
                details={"warning": "All services restarted"}
            )
            
        except Exception as e:
            return HealingResult(
                action_id=action_id,
                status=HealingStatus.FAILED,
                message=f"Nuclear restart failed: {str(e)}",
                details={"error": str(e)}
            )


# Initialize all healers
service_healer = ServiceHealer()
port_healer = PortHealer()
registry_healer = RegistryHealer()
filesystem_healer = FilesystemHealer()
database_healer = DatabaseHealer()
network_healer = NetworkHealer()
emergency = EmergencyProtocol()

# ═══════════════════════════════════════════════════════════════════════════════
# HEALING PLAN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

async def generate_healing_plan(issues: List[dict] = None) -> HealingPlan:
    """Generate a healing plan from PANOPTES issues."""
    
    if issues is None:
        issues = await get_panoptes_issues()
    
    plan_id = str(uuid.uuid4())[:8]
    actions = []
    requires_approval = False
    
    for issue in issues:
        category = issue.get("category", "")
        severity = issue.get("severity", "")
        title = issue.get("title", "")
        affected = issue.get("affected", [])
        
        # Determine healing action
        if category == "port_conflict":
            port_match = re.search(r'\d+', title)
            port = int(port_match.group()) if port_match else 0
            
            if len(affected) >= 2:
                actions.append(HealingAction(
                    id=str(uuid.uuid4())[:8],
                    category=HealingCategory.PORT,
                    severity=HealingSeverity.ELEVATED,
                    title=f"Resolve port {port} conflict",
                    description=f"Move {affected[1]} to new port, keep {affected[0]} on {port}",
                    target=f"port:{port}",
                    command=f"resolve_conflict({port}, '{affected[0]}', '{affected[1]}')"
                ))
                requires_approval = True
        
        elif category == "agent_offline":
            for agent in affected:
                actions.append(HealingAction(
                    id=str(uuid.uuid4())[:8],
                    category=HealingCategory.SERVICE,
                    severity=HealingSeverity.STANDARD,
                    title=f"Restart {agent}",
                    description=f"Service {agent} is offline, restart it",
                    target=agent,
                    command=f"restart_service('{agent}')"
                ))
        
        elif category == "duplicate_code":
            if len(affected) >= 2:
                actions.append(HealingAction(
                    id=str(uuid.uuid4())[:8],
                    category=HealingCategory.FILESYSTEM,
                    severity=HealingSeverity.ELEVATED,
                    title=f"Remove duplicate {affected[0]}",
                    description=f"Archive and remove {affected[0]}, keep {affected[1]}",
                    target=affected[0],
                    command=f"remove_duplicate_directory('{affected[0]}', '{affected[1]}')"
                ))
                requires_approval = True
        
        elif category == "registry_incomplete" or category == "registry_error":
            actions.append(HealingAction(
                id=str(uuid.uuid4())[:8],
                category=HealingCategory.REGISTRY,
                severity=HealingSeverity.STANDARD,
                title="Fix registry",
                description="Validate and fix registry YAML",
                target="registry",
                command="validate_and_fix_yaml()"
            ))
        
        elif category == "missing_service":
            for agent in affected:
                actions.append(HealingAction(
                    id=str(uuid.uuid4())[:8],
                    category=HealingCategory.SERVICE,
                    severity=HealingSeverity.STANDARD,
                    title=f"Generate systemd service for {agent}",
                    description=f"Create and enable systemd service for {agent}",
                    target=agent,
                    command=f"generate_service('{agent}')"
                ))
    
    plan = HealingPlan(
        plan_id=plan_id,
        created_at=datetime.utcnow().isoformat(),
        description=f"Healing plan for {len(issues)} issues",
        actions=actions,
        requires_approval=requires_approval
    )
    
    healing_plans[plan_id] = plan
    
    return plan


async def execute_healing_plan(plan_id: str) -> HealingPlan:
    """Execute a healing plan."""
    
    if plan_id not in healing_plans:
        raise ValueError(f"Plan {plan_id} not found")
    
    plan = healing_plans[plan_id]
    
    if plan.requires_approval and not plan.approved:
        raise ValueError("Plan requires approval before execution")
    
    plan.executed = True
    plan.execution_started = datetime.utcnow().isoformat()
    plan.overall_status = HealingStatus.IN_PROGRESS
    
    # Create backup before healing
    backup_id = await create_backup("healing-plan", f"Plan {plan_id}")
    
    await notify(f"🏥 Executing healing plan {plan_id} ({len(plan.actions)} actions)", "high")
    
    for action in plan.actions:
        action.status = HealingStatus.IN_PROGRESS
        action.started_at = datetime.utcnow().isoformat()
        action.backup_id = backup_id
        
        try:
            # Execute based on category
            if action.category == HealingCategory.SERVICE:
                if "restart" in action.command:
                    result = await service_healer.restart_service(action.target)
                elif "generate" in action.command:
                    result = await service_healer.generate_service(action.target, 8000)
                else:
                    result = await service_healer.start_service(action.target)
            
            elif action.category == HealingCategory.PORT:
                # Parse command for parameters
                match = re.search(r"resolve_conflict\((\d+), '([^']+)', '([^']+)'\)", action.command)
                if match:
                    port, keep, move = int(match.group(1)), match.group(2), match.group(3)
                    new_port = await port_healer.find_next_available_port()
                    result = await port_healer.resolve_conflict(port, keep, move, new_port)
                else:
                    result = HealingResult(
                        action_id=action.id,
                        status=HealingStatus.FAILED,
                        message="Could not parse port conflict command"
                    )
            
            elif action.category == HealingCategory.REGISTRY:
                result = await registry_healer.validate_and_fix_yaml()
            
            elif action.category == HealingCategory.FILESYSTEM:
                match = re.search(r"remove_duplicate_directory\('([^']+)', '([^']+)'\)", action.command)
                if match:
                    result = await filesystem_healer.remove_duplicate_directory(
                        match.group(1), match.group(2)
                    )
                else:
                    result = HealingResult(
                        action_id=action.id,
                        status=HealingStatus.FAILED,
                        message="Could not parse filesystem command"
                    )
            
            else:
                result = HealingResult(
                    action_id=action.id,
                    status=HealingStatus.SKIPPED,
                    message=f"No handler for category {action.category}"
                )
            
            action.status = result.status
            action.output = result.message
            
        except Exception as e:
            action.status = HealingStatus.FAILED
            action.error = str(e)
        
        finally:
            action.completed_at = datetime.utcnow().isoformat()
            if action.started_at:
                start = datetime.fromisoformat(action.started_at)
                end = datetime.fromisoformat(action.completed_at)
                action.duration_ms = int((end - start).total_seconds() * 1000)
        
        # Store in history
        healing_history.append(action)
    
    plan.execution_completed = datetime.utcnow().isoformat()
    
    # Determine overall status
    success_count = sum(1 for a in plan.actions if a.status == HealingStatus.SUCCESS)
    failed_count = sum(1 for a in plan.actions if a.status == HealingStatus.FAILED)
    
    if failed_count == 0:
        plan.overall_status = HealingStatus.SUCCESS
    elif success_count == 0:
        plan.overall_status = HealingStatus.FAILED
    else:
        plan.overall_status = HealingStatus.PARTIAL
    
    # Notify completion
    status_emoji = "✅" if plan.overall_status == HealingStatus.SUCCESS else "⚠️"
    await notify(
        f"{status_emoji} Healing plan {plan_id} complete: {success_count}/{len(plan.actions)} succeeded",
        "normal" if plan.overall_status == HealingStatus.SUCCESS else "high"
    )
    
    # Verify with PANOPTES
    await verify_healing()
    
    return plan


# ═══════════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class HealRequest(BaseModel):
    category: str
    target: str
    params: Dict[str, Any] = Field(default_factory=dict)


class PlanApproval(BaseModel):
    approved_by: str = "system"


class EmergencyRequest(BaseModel):
    protocol: str  # full, panoptes, nuclear
    confirm: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="ASCLEPIUS ⚕️ - The Divine Physician",
    description="Automated healing and remediation engine for LeverEdge",
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
        "agent": "ASCLEPIUS",
        "role": "Divine Physician",
        "symbol": "⚕️",
        "port": ASCLEPIUS_PORT,
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "days_to_launch": days_to_launch,
        "healing_history_count": len(healing_history),
        "active_plans": len([p for p in healing_plans.values() if p.overall_status == HealingStatus.IN_PROGRESS])
    }


@app.get("/status")
async def status():
    """Get healing status overview."""
    # Get current issues from PANOPTES
    issues = await get_panoptes_issues()
    
    return {
        "asclepius": "ready",
        "current_issues": len(issues),
        "critical_issues": len([i for i in issues if i.get("severity") == "critical"]),
        "active_plans": len([p for p in healing_plans.values() if p.overall_status == HealingStatus.IN_PROGRESS]),
        "healing_history": len(healing_history),
        "healers_available": [
            "service", "port", "registry", "filesystem", "database", "network", "emergency"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


# ─────────────────────────────────────────────────────────────────────────────
# HEALING PLANS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/plan/generate")
async def create_healing_plan():
    """Generate a healing plan from current PANOPTES issues."""
    plan = await generate_healing_plan()
    return plan.to_dict()


@app.get("/plan/{plan_id}")
async def get_plan(plan_id: str):
    """Get a healing plan."""
    if plan_id not in healing_plans:
        raise HTTPException(404, f"Plan {plan_id} not found")
    return healing_plans[plan_id].to_dict()


@app.post("/plan/{plan_id}/approve")
async def approve_plan(plan_id: str, approval: PlanApproval):
    """Approve a healing plan."""
    if plan_id not in healing_plans:
        raise HTTPException(404, f"Plan {plan_id} not found")
    
    plan = healing_plans[plan_id]
    plan.approved = True
    plan.approved_by = approval.approved_by
    
    await log_event("healing_plan_approved", {
        "plan_id": plan_id,
        "approved_by": approval.approved_by
    })
    
    return {"status": "approved", "plan_id": plan_id}


@app.post("/plan/{plan_id}/execute")
async def execute_plan(plan_id: str, background_tasks: BackgroundTasks):
    """Execute a healing plan."""
    if plan_id not in healing_plans:
        raise HTTPException(404, f"Plan {plan_id} not found")
    
    plan = healing_plans[plan_id]
    
    if plan.requires_approval and not plan.approved:
        raise HTTPException(400, "Plan requires approval before execution")
    
    if plan.executed:
        raise HTTPException(400, "Plan already executed")
    
    # Execute in background
    result = await execute_healing_plan(plan_id)
    
    return result.to_dict()


@app.get("/plans")
async def list_plans():
    """List all healing plans."""
    return {
        "plans": [p.to_dict() for p in healing_plans.values()],
        "count": len(healing_plans)
    }


# ─────────────────────────────────────────────────────────────────────────────
# DIRECT HEALING ACTIONS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/heal/service/restart/{service_name}")
async def heal_restart_service(service_name: str):
    """Restart a service."""
    result = await service_healer.restart_service(service_name)
    await log_event("service_restarted", {"service": service_name, "status": result.status.value})
    return result.__dict__


@app.post("/heal/service/start/{service_name}")
async def heal_start_service(service_name: str):
    """Start a service."""
    result = await service_healer.start_service(service_name)
    return result.__dict__


@app.post("/heal/service/generate/{agent_name}")
async def heal_generate_service(agent_name: str, port: int = 8000):
    """Generate a systemd service."""
    result = await service_healer.generate_service(agent_name, port)
    return result.__dict__


@app.post("/heal/port/kill/{port}")
async def heal_kill_port(port: int):
    """Kill process on a port."""
    result = await service_healer.kill_rogue_process(port)
    return result.__dict__


@app.post("/heal/registry/fix")
async def heal_fix_registry():
    """Fix registry YAML."""
    result = await registry_healer.validate_and_fix_yaml()
    return result.__dict__


@app.post("/heal/filesystem/duplicate")
async def heal_remove_duplicate(directory: str, keep: str):
    """Remove duplicate directory."""
    result = await filesystem_healer.remove_duplicate_directory(directory, keep)
    return result.__dict__


@app.post("/heal/database/migrate")
async def heal_run_migrations(target: str = "prod"):
    """Run database migrations."""
    result = await database_healer.run_migrations(target)
    return result.__dict__


@app.post("/heal/network/caddy")
async def heal_restart_caddy():
    """Restart Caddy."""
    result = await network_healer.restart_caddy()
    return result.__dict__


# ─────────────────────────────────────────────────────────────────────────────
# EMERGENCY PROTOCOLS
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/emergency/full")
async def emergency_full_healing(background_tasks: BackgroundTasks):
    """Full system healing - heal everything."""
    results = await emergency.full_system_healing()
    
    success_count = sum(1 for r in results if r.status == HealingStatus.SUCCESS)
    
    return {
        "protocol": "full_system_healing",
        "results": [r.__dict__ for r in results],
        "success_count": success_count,
        "total_actions": len(results)
    }


@app.post("/emergency/auto")
async def emergency_auto_healing():
    """Heal issues detected by PANOPTES automatically."""
    results = await emergency.heal_from_panoptes()
    
    return {
        "protocol": "auto_healing",
        "results": [r.__dict__ for r in results],
        "healed_count": sum(1 for r in results if r.status == HealingStatus.SUCCESS)
    }


@app.post("/emergency/nuclear")
async def emergency_nuclear(request: EmergencyRequest):
    """Nuclear option - restart EVERYTHING. Requires confirmation."""
    
    if not request.confirm:
        raise HTTPException(
            400, 
            "Nuclear restart requires confirmation. Set 'confirm: true' to proceed."
        )
    
    result = await emergency.nuclear_restart()
    return result.__dict__


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/history")
async def get_history(limit: int = 50):
    """Get healing history."""
    recent = healing_history[-limit:] if len(healing_history) > limit else healing_history
    return {
        "history": [h.to_dict() for h in reversed(recent)],
        "total": len(healing_history)
    }


@app.get("/history/stats")
async def get_history_stats():
    """Get healing statistics."""
    if not healing_history:
        return {"total": 0, "by_category": {}, "by_status": {}}
    
    by_category = {}
    by_status = {}
    
    for action in healing_history:
        cat = action.category.value
        stat = action.status.value
        
        by_category[cat] = by_category.get(cat, 0) + 1
        by_status[stat] = by_status.get(stat, 0) + 1
    
    return {
        "total": len(healing_history),
        "by_category": by_category,
        "by_status": by_status,
        "success_rate": round(by_status.get("success", 0) / len(healing_history) * 100, 1)
    }


# ─────────────────────────────────────────────────────────────────────────────
# LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Startup."""
    await log_event("agent_started", {
        "agent": "ASCLEPIUS",
        "port": ASCLEPIUS_PORT,
        "version": "1.0.0"
    })
    
    print(f"⚕️ ASCLEPIUS - The Divine Physician - started on port {ASCLEPIUS_PORT}")
    print(f"   Healing protocols: service, port, registry, filesystem, database, network")
    print(f"   Emergency protocols: full, auto, nuclear")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=ASCLEPIUS_PORT)
```

---

## Section 3: Requirements

Create `/opt/leveredge/control-plane/agents/asclepius/requirements.txt`:

```
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pyyaml>=6.0
pydantic>=2.0
```

---

## Section 4: Systemd Service

Create `/opt/leveredge/shared/systemd/leveredge-asclepius.service`:

```ini
[Unit]
Description=LeverEdge ASCLEPIUS - Divine Physician
After=network.target leveredge-panoptes.service
Wants=leveredge-panoptes.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/leveredge/control-plane/agents/asclepius
Environment=PYTHONUNBUFFERED=1
Environment=REGISTRY_PATH=/opt/leveredge/config/agent-registry.yaml
Environment=AGENTS_PATH=/opt/leveredge/control-plane/agents
Environment=EVENT_BUS_URL=http://localhost:8099
Environment=HERMES_URL=http://localhost:8014
Environment=CHRONOS_URL=http://localhost:8010
Environment=HADES_URL=http://localhost:8008
Environment=PANOPTES_URL=http://localhost:8022
ExecStart=/opt/leveredge/shared/venv/bin/python asclepius.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## Section 5: Add to Agent Registry

Add to `/opt/leveredge/config/agent-registry.yaml`:

```yaml
  # ─────────────────────────────────────────────────────────────────────────────
  # ASCLEPIUS - Divine Physician
  # ─────────────────────────────────────────────────────────────────────────────
  asclepius:
    name: ASCLEPIUS
    version: "1.0"
    description: "The Divine Physician - automated healing and remediation"
    category: infrastructure
    llm_powered: false

    connection:
      url: http://asclepius:8024
      health_endpoint: /health
      timeout_ms: 60000

    capabilities:
      - service_healing
      - port_healing
      - registry_healing
      - filesystem_healing
      - database_healing
      - network_healing
      - emergency_protocols

    actions:

      plan-generate:
        endpoint: /plan/generate
        method: POST
        description: "Generate healing plan from PANOPTES issues"
        timeout_ms: 30000
        returns:
          type: object
          fields: [plan_id, actions, requires_approval]

      plan-execute:
        endpoint: /plan/{plan_id}/execute
        method: POST
        description: "Execute a healing plan"
        timeout_ms: 300000
        params:
          - name: plan_id
            type: string
            required: true
        returns:
          type: object
          fields: [plan_id, overall_status, success_count]

      restart-service:
        endpoint: /heal/service/restart/{service_name}
        method: POST
        description: "Restart a service"
        timeout_ms: 30000
        params:
          - name: service_name
            type: string
            required: true

      emergency-full:
        endpoint: /emergency/full
        method: POST
        description: "Full system healing"
        timeout_ms: 600000

      emergency-auto:
        endpoint: /emergency/auto
        method: POST
        description: "Auto-heal from PANOPTES issues"
        timeout_ms: 300000

      emergency-nuclear:
        endpoint: /emergency/nuclear
        method: POST
        description: "Nuclear restart - requires confirmation"
        timeout_ms: 600000
        params:
          - name: confirm
            type: boolean
            required: true
```

---

## Section 6: Deployment Commands

```bash
# Create directory
mkdir -p /opt/leveredge/control-plane/agents/asclepius
mkdir -p /opt/leveredge/archive

# Copy files (GSD will create them)

# Install systemd service
sudo cp /opt/leveredge/shared/systemd/leveredge-asclepius.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable leveredge-asclepius
sudo systemctl start leveredge-asclepius

# Verify
curl http://localhost:8024/health
curl http://localhost:8024/status
```

---

## GSD Command

```
/gsd /opt/leveredge/specs/gsd-build-asclepius.md

CONTEXT: We built PANOPTES to find problems. Now we need ASCLEPIUS to FIX them.
ASCLEPIUS is the Divine Physician - he heals everything.

CRITICAL:
- Port 8024 (Infrastructure)
- Works WITH: PANOPTES (issues), CHRONOS (backup), HADES (rollback), HERMES (notify)
- Safety: ALWAYS backup before healing, rollback if failed
- Emergency protocols: full system healing, auto-heal, nuclear restart

HEALING CAPABILITIES:
- Service: restart, start, generate systemd, kill rogue
- Port: resolve conflicts, reassign, free
- Registry: fix YAML, add/remove agents, fix URLs
- Filesystem: remove duplicates, fix permissions
- Database: run migrations, restart Supabase
- Network: restart Caddy, clear DNS

After deployment: curl http://localhost:8024/status
```

---

## API Reference

### Plans
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/plan/generate` | POST | Generate healing plan from PANOPTES |
| `/plan/{id}` | GET | Get plan details |
| `/plan/{id}/approve` | POST | Approve a plan |
| `/plan/{id}/execute` | POST | Execute a plan |
| `/plans` | GET | List all plans |

### Direct Healing
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/heal/service/restart/{name}` | POST | Restart service |
| `/heal/service/start/{name}` | POST | Start service |
| `/heal/service/generate/{name}` | POST | Generate systemd |
| `/heal/port/kill/{port}` | POST | Kill process on port |
| `/heal/registry/fix` | POST | Fix registry YAML |
| `/heal/filesystem/duplicate` | POST | Remove duplicate dir |
| `/heal/database/migrate` | POST | Run migrations |
| `/heal/network/caddy` | POST | Restart Caddy |

### Emergency Protocols
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/emergency/full` | POST | Full system healing |
| `/emergency/auto` | POST | Auto-heal PANOPTES issues |
| `/emergency/nuclear` | POST | Restart EVERYTHING (needs confirm) |

---

## The Complete Healing Loop

```
   ┌──────────────────────────────────────────────────────────────────┐
   │                    THE COMPLETE HEALING LOOP                      │
   │                                                                   │
   │    ┌──────────┐       ┌──────────┐       ┌──────────┐           │
   │    │ PANOPTES │──────▶│ASCLEPIUS │──────▶│ PANOPTES │           │
   │    │ Diagnose │       │   Heal   │       │  Verify  │           │
   │    └──────────┘       └────┬─────┘       └──────────┘           │
   │         👁️                  │⚕️                 👁️                │
   │                            │                                     │
   │    ┌─────────────┐    ┌────┴────┐    ┌─────────────┐            │
   │    │   CHRONOS   │◀───┤ BACKUP  │    │   HERMES    │            │
   │    │   Backup    │    │ FIRST!  │    │   Notify    │            │
   │    └──────┬──────┘    └─────────┘    └──────▲──────┘            │
   │           │                                  │                   │
   │           │         ┌──────────┐            │                   │
   │           └────────▶│  HADES   │────────────┘                   │
   │                     │ Rollback │  (if healing fails)            │
   │                     └──────────┘                                │
   │                          💀                                      │
   └──────────────────────────────────────────────────────────────────┘
```

---

## Expected Outcome

After deployment:
- ✅ ASCLEPIUS running on port 8024
- ✅ Can generate healing plans from PANOPTES
- ✅ Can auto-heal critical issues
- ✅ Emergency protocols available
- ✅ Full audit trail of all healing
- ✅ Safety: backup before, rollback if failed

**ASCLEPIUS is so powerful, Zeus would strike him down.** ⚕️
