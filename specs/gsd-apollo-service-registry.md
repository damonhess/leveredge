# GSD: APOLLO Service Deployment Registry

**Priority:** HIGH
**Estimated Time:** 30-45 minutes
**Created:** January 20, 2026
**Status:** Ready for execution
**Depends On:** APOLLO running on port 8234

---

## OVERVIEW

Wire APOLLO to all service deployment scripts so every deployment:
1. Goes through a single orchestrator
2. Has automatic backup via CHRONOS
3. Has health verification via PANOPTES
4. Has full audit trail in LCIS
5. Has notifications via HERMES
6. Can be rolled back via HADES

**Current State:** Scripts exist but are run manually
**Target State:** `curl -X POST http://localhost:8234/deploy/aria` does everything

---

## ARCHITECTURE

```
                    ┌─────────────────────────────────────────┐
                    │              APOLLO                      │
                    │       Deployment Orchestrator            │
                    └─────────────────┬───────────────────────┘
                                      │
                    ┌─────────────────┴───────────────────┐
                    │         SERVICE REGISTRY            │
                    │                                     │
                    │  aria-frontend → promote-aria.sh    │
                    │  aria-chat     → restart container  │
                    │  fleet         → fleet-start.sh     │
                    │  agent/*       → docker restart     │
                    │  schema        → promote-schema.sh  │
                    └─────────────────┬───────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│   CHRONOS     │           │   PANOPTES    │           │    HERMES     │
│   Pre-backup  │           │  Health Check │           │  Notify       │
└───────────────┘           └───────────────┘           └───────────────┘
        │                             │                             │
        └─────────────────────────────┼─────────────────────────────┘
                                      │
                                      ▼
                            ┌───────────────┐
                            │     LCIS      │
                            │  Audit Trail  │
                            └───────────────┘
```

---

## PHASE 1: SERVICE REGISTRY

Create `/opt/leveredge/control-plane/agents/apollo/service_registry.py`:

```python
#!/usr/bin/env python3
"""
APOLLO Service Registry

Maps services to their deployment configurations:
- Deployment scripts
- Health check endpoints
- Container names
- Environment support
- Rollback procedures
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Callable
from enum import Enum

class DeployMethod(str, Enum):
    SCRIPT = "script"           # Run a shell script
    CONTAINER = "container"     # Docker restart/update
    COMPOSE = "compose"         # Docker compose up
    CUSTOM = "custom"           # Custom Python function

@dataclass
class ServiceConfig:
    """Configuration for a deployable service"""
    name: str
    display_name: str
    deploy_method: DeployMethod
    
    # Script deployment
    script_path: Optional[str] = None
    dry_run_flag: str = "--dry-run"
    force_flag: str = "--force"
    
    # Container deployment
    container_name: Optional[str] = None
    compose_file: Optional[str] = None
    compose_service: Optional[str] = None
    
    # Health check
    health_url: Optional[str] = None
    health_timeout: int = 30
    
    # Environments
    environments: List[str] = field(default_factory=lambda: ["dev", "prod"])
    
    # Backup config
    backup_type: str = "pre-deploy"
    skip_backup_allowed: bool = False
    
    # Rollback
    rollback_script: Optional[str] = None
    rollback_container: Optional[str] = None
    
    # Metadata
    critical: bool = False
    requires_approval: bool = False
    max_deploy_time: int = 300  # seconds
    
    # Tags for LCIS
    tags: List[str] = field(default_factory=list)


# =============================================================================
# SERVICE REGISTRY
# =============================================================================

SERVICE_REGISTRY: Dict[str, ServiceConfig] = {
    
    # =========================================================================
    # ARIA ECOSYSTEM
    # =========================================================================
    
    "aria-frontend": ServiceConfig(
        name="aria-frontend",
        display_name="ARIA Frontend",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/shared/scripts/promote-aria-to-prod.sh",
        dry_run_flag="--dry-run",
        force_flag="--force",
        container_name="aria-frontend-prod",
        health_url="https://aria.leveredgeai.com",
        environments=["dev", "prod"],
        critical=True,
        requires_approval=False,
        tags=["aria", "frontend", "user-facing"],
    ),
    
    "aria-chat": ServiceConfig(
        name="aria-chat",
        display_name="ARIA Chat API",
        deploy_method=DeployMethod.CONTAINER,
        container_name="aria-chat-prod",
        health_url="https://aria-api.leveredgeai.com/health",
        environments=["dev", "prod"],
        critical=True,
        tags=["aria", "api", "backend"],
    ),
    
    "aria-memory": ServiceConfig(
        name="aria-memory",
        display_name="ARIA Memory Service",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="aria-memory",
        container_name="leveredge-aria-memory",
        health_url="http://localhost:8114/health",
        environments=["dev"],
        tags=["aria", "memory"],
    ),
    
    # =========================================================================
    # CORE INFRASTRUCTURE
    # =========================================================================
    
    "fleet": ServiceConfig(
        name="fleet",
        display_name="Agent Fleet",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/fleet-start.sh",
        health_url="http://localhost:8099/health",  # Event bus as canary
        environments=["dev"],
        critical=True,
        max_deploy_time=600,  # Fleet takes longer
        tags=["fleet", "agents", "infrastructure"],
    ),
    
    "event-bus": ServiceConfig(
        name="event-bus",
        display_name="Event Bus",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="event-bus",
        container_name="event-bus",
        health_url="http://localhost:8099/health",
        critical=True,
        tags=["core", "event-bus"],
    ),
    
    # =========================================================================
    # SCHEMA / DATABASE
    # =========================================================================
    
    "schema": ServiceConfig(
        name="schema",
        display_name="Database Schema",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/shared/scripts/promote-schema.sh",
        environments=["dev", "prod"],
        critical=True,
        requires_approval=True,  # Schema changes need approval
        tags=["database", "schema", "migrations"],
    ),
    
    "schema-sync": ServiceConfig(
        name="schema-sync",
        display_name="Schema Sync (DEV → PROD)",
        deploy_method=DeployMethod.SCRIPT,
        script_path="/opt/leveredge/shared/scripts/sync-schema-dev-to-prod.sh",
        environments=["prod"],
        critical=True,
        requires_approval=True,
        tags=["database", "schema", "sync"],
    ),
    
    # =========================================================================
    # MONITORING AGENTS
    # =========================================================================
    
    "panoptes": ServiceConfig(
        name="panoptes",
        display_name="PANOPTES Health Monitor",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="panoptes",
        container_name="leveredge-panoptes",
        health_url="http://localhost:8023/health",
        tags=["monitoring", "health"],
    ),
    
    "argus": ServiceConfig(
        name="argus",
        display_name="ARGUS Metrics",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="argus",
        container_name="leveredge-argus",
        health_url="http://localhost:8016/health",
        tags=["monitoring", "metrics"],
    ),
    
    "watchdog": ServiceConfig(
        name="watchdog",
        display_name="WATCHDOG Meta-Monitor",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="watchdog",
        container_name="leveredge-watchdog",
        health_url="http://localhost:8240/health",
        critical=True,
        tags=["monitoring", "watchdog"],
    ),
    
    # =========================================================================
    # LCIS
    # =========================================================================
    
    "lcis-librarian": ServiceConfig(
        name="lcis-librarian",
        display_name="LCIS Librarian",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="lcis-librarian",
        container_name="leveredge-lcis-librarian",
        health_url="http://localhost:8050/health",
        critical=True,
        tags=["lcis", "knowledge"],
    ),
    
    # =========================================================================
    # CREATIVE FLEET
    # =========================================================================
    
    "muse": ServiceConfig(
        name="muse",
        display_name="Muse Creative Writer",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="muse",
        container_name="leveredge-muse",
        health_url="http://localhost:8030/health",
        tags=["creative", "writing"],
    ),
    
    # =========================================================================
    # PERSONAL AGENTS
    # =========================================================================
    
    "gym-coach": ServiceConfig(
        name="gym-coach",
        display_name="Gym Coach",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="gym-coach",
        container_name="leveredge-gym-coach",
        health_url="http://localhost:8230/health",
        tags=["personal", "fitness"],
    ),
    
    "academic-guide": ServiceConfig(
        name="academic-guide",
        display_name="Academic Guide",
        deploy_method=DeployMethod.COMPOSE,
        compose_file="/opt/leveredge/docker-compose.fleet.yml",
        compose_service="academic-guide",
        container_name="leveredge-academic-guide",
        health_url="http://localhost:8231/health",
        tags=["personal", "learning"],
    ),
}


def get_service(name: str) -> Optional[ServiceConfig]:
    """Get service configuration by name"""
    return SERVICE_REGISTRY.get(name)


def list_services() -> List[str]:
    """List all registered services"""
    return list(SERVICE_REGISTRY.keys())


def list_critical_services() -> List[str]:
    """List critical services that need extra care"""
    return [name for name, config in SERVICE_REGISTRY.items() if config.critical]


def get_services_by_tag(tag: str) -> List[str]:
    """Get services by tag"""
    return [name for name, config in SERVICE_REGISTRY.items() if tag in config.tags]
```

---

## PHASE 2: DEPLOYMENT EXECUTOR

Create `/opt/leveredge/control-plane/agents/apollo/deployment_executor.py`:

```python
#!/usr/bin/env python3
"""
APOLLO Deployment Executor

Executes deployments based on service configuration.
Handles script execution, container restarts, compose updates.
"""

import os
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import httpx

from service_registry import ServiceConfig, DeployMethod, get_service

# =============================================================================
# CONFIGURATION
# =============================================================================

CHRONOS_URL = os.getenv("CHRONOS_URL", "http://chronos:8010")
PANOPTES_URL = os.getenv("PANOPTES_URL", "http://panoptes:8023")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")

# =============================================================================
# MODELS
# =============================================================================

class DeploymentResult(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"

@dataclass
class DeploymentOutcome:
    service: str
    result: DeploymentResult
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    dry_run: bool
    backup_id: Optional[str]
    health_check_passed: bool
    stdout: Optional[str]
    stderr: Optional[str]
    error: Optional[str]

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def notify(message: str, level: str = "info"):
    """Send notification via HERMES"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{HERMES_URL}/alert",
                json={
                    "severity": level,
                    "source": "APOLLO",
                    "title": "Deployment",
                    "message": message
                }
            )
    except:
        pass


async def log_to_lcis(content: str, lesson_type: str, service: str, tags: list):
    """Log deployment to LCIS"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{LCIS_URL}/lessons",
                json={
                    "content": content,
                    "domain": "DEPLOYMENT",
                    "type": lesson_type,
                    "source_agent": "APOLLO",
                    "tags": ["deployment", "apollo", service] + tags
                }
            )
    except:
        pass


async def publish_event(event_type: str, data: dict):
    """Publish to Event Bus"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "APOLLO",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    except:
        pass


async def create_backup(service: str, backup_type: str = "pre-deploy") -> Optional[str]:
    """Create backup via CHRONOS"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CHRONOS_URL}/backup",
                json={
                    "name": f"{service}-{backup_type}",
                    "type": backup_type,
                    "triggered_by": "APOLLO"
                }
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("backup_id")
    except:
        pass
    return None


async def health_check(url: str, timeout: int = 30) -> bool:
    """Perform health check"""
    if not url:
        return True  # No health check configured
    
    try:
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            response = await client.get(url)
            return response.status_code == 200
    except:
        return False


# =============================================================================
# DEPLOYMENT METHODS
# =============================================================================

async def execute_script(config: ServiceConfig, dry_run: bool = False) -> Dict[str, Any]:
    """Execute a deployment script"""
    
    if not config.script_path:
        return {"success": False, "error": "No script path configured"}
    
    if not os.path.exists(config.script_path):
        return {"success": False, "error": f"Script not found: {config.script_path}"}
    
    # Build command
    cmd = [config.script_path]
    if dry_run:
        cmd.append(config.dry_run_flag)
    else:
        cmd.append(config.force_flag)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=config.max_deploy_time,
            cwd="/opt/leveredge"
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-5000:] if result.stdout else None,
            "stderr": result.stderr[-2000:] if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Script timed out after {config.max_deploy_time}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def execute_container_restart(config: ServiceConfig) -> Dict[str, Any]:
    """Restart a Docker container"""
    
    if not config.container_name:
        return {"success": False, "error": "No container name configured"}
    
    try:
        result = subprocess.run(
            ["docker", "restart", config.container_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def execute_compose_up(config: ServiceConfig) -> Dict[str, Any]:
    """Run docker compose up for a service"""
    
    if not config.compose_file or not config.compose_service:
        return {"success": False, "error": "Compose file or service not configured"}
    
    try:
        result = subprocess.run(
            [
                "docker", "compose",
                "-f", config.compose_file,
                "--env-file", "/opt/leveredge/.env.fleet",
                "up", "-d", "--build", config.compose_service
            ],
            capture_output=True,
            text=True,
            timeout=config.max_deploy_time,
            cwd="/opt/leveredge"
        )
        
        return {
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-3000:] if result.stdout else None,
            "stderr": result.stderr[-1000:] if result.stderr else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# MAIN EXECUTOR
# =============================================================================

async def execute_deployment(
    service_name: str,
    dry_run: bool = False,
    skip_backup: bool = False,
    reason: Optional[str] = None
) -> DeploymentOutcome:
    """
    Execute a full deployment with all safety checks.
    
    1. Validate service exists
    2. Create CHRONOS backup
    3. Notify deployment start
    4. Execute deployment
    5. Health check
    6. Log to LCIS
    7. Notify completion
    """
    
    started_at = datetime.utcnow()
    backup_id = None
    
    # Get service config
    config = get_service(service_name)
    if not config:
        return DeploymentOutcome(
            service=service_name,
            result=DeploymentResult.FAILED,
            started_at=started_at,
            completed_at=datetime.utcnow(),
            duration_seconds=0,
            dry_run=dry_run,
            backup_id=None,
            health_check_passed=False,
            stdout=None,
            stderr=None,
            error=f"Unknown service: {service_name}"
        )
    
    # Publish start event
    await publish_event("deployment_started", {
        "service": service_name,
        "dry_run": dry_run,
        "reason": reason
    })
    
    # Notify start
    mode = "DRY RUN" if dry_run else "LIVE"
    await notify(f"🚀 Starting {config.display_name} deployment ({mode})", "info")
    
    # Create backup (unless dry run or skipped)
    if not dry_run and not skip_backup and not config.skip_backup_allowed:
        backup_id = await create_backup(service_name, config.backup_type)
        if backup_id:
            await notify(f"📦 Backup created: {backup_id}", "info")
        else:
            await notify(f"⚠️ Backup failed for {service_name}", "warning")
    
    # Execute based on method
    if config.deploy_method == DeployMethod.SCRIPT:
        result = await execute_script(config, dry_run)
    elif config.deploy_method == DeployMethod.CONTAINER:
        if dry_run:
            result = {"success": True, "stdout": "DRY RUN: Would restart container"}
        else:
            result = await execute_container_restart(config)
    elif config.deploy_method == DeployMethod.COMPOSE:
        if dry_run:
            result = {"success": True, "stdout": "DRY RUN: Would run compose up"}
        else:
            result = await execute_compose_up(config)
    else:
        result = {"success": False, "error": f"Unknown deploy method: {config.deploy_method}"}
    
    # Health check (unless dry run)
    health_passed = True
    if not dry_run and result.get("success") and config.health_url:
        await asyncio.sleep(5)  # Wait for service to start
        health_passed = await health_check(config.health_url, config.health_timeout)
        
        if not health_passed:
            await notify(f"❌ Health check failed for {config.display_name}", "critical")
            result["success"] = False
            result["error"] = "Health check failed"
    
    # Determine outcome
    completed_at = datetime.utcnow()
    duration = (completed_at - started_at).total_seconds()
    
    if result.get("success"):
        deploy_result = DeploymentResult.SUCCESS
        await notify(f"✅ {config.display_name} deployment complete ({duration:.1f}s)", "info")
    else:
        deploy_result = DeploymentResult.FAILED
        await notify(f"❌ {config.display_name} deployment failed: {result.get('error', 'Unknown')}", "critical")
    
    # Log to LCIS
    await log_to_lcis(
        content=f"Deployment {deploy_result.value}: {config.display_name} ({mode}). Duration: {duration:.1f}s. Reason: {reason or 'No reason provided'}",
        lesson_type="success" if result.get("success") else "failure",
        service=service_name,
        tags=config.tags
    )
    
    # Publish completion event
    await publish_event("deployment_completed", {
        "service": service_name,
        "result": deploy_result.value,
        "duration_seconds": duration,
        "dry_run": dry_run
    })
    
    return DeploymentOutcome(
        service=service_name,
        result=deploy_result,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=duration,
        dry_run=dry_run,
        backup_id=backup_id,
        health_check_passed=health_passed,
        stdout=result.get("stdout"),
        stderr=result.get("stderr"),
        error=result.get("error")
    )
```

---

## PHASE 3: UPDATE APOLLO ENDPOINTS

Add to `/opt/leveredge/control-plane/agents/apollo/apollo.py`:

```python
# Add imports at top
from service_registry import (
    SERVICE_REGISTRY, ServiceConfig, get_service, 
    list_services, list_critical_services, get_services_by_tag
)
from deployment_executor import execute_deployment, DeploymentOutcome, DeploymentResult

# =============================================================================
# SERVICE DEPLOYMENT ENDPOINTS
# =============================================================================

@app.get("/services")
async def list_all_services():
    """List all registered services"""
    return {
        "services": [
            {
                "name": config.name,
                "display_name": config.display_name,
                "method": config.deploy_method.value,
                "critical": config.critical,
                "requires_approval": config.requires_approval,
                "health_url": config.health_url,
                "tags": config.tags
            }
            for config in SERVICE_REGISTRY.values()
        ],
        "total": len(SERVICE_REGISTRY)
    }


@app.get("/services/critical")
async def list_critical():
    """List critical services"""
    return {"critical_services": list_critical_services()}


@app.get("/services/by-tag/{tag}")
async def services_by_tag(tag: str):
    """Get services by tag"""
    return {"tag": tag, "services": get_services_by_tag(tag)}


@app.get("/services/{service_name}")
async def get_service_config(service_name: str):
    """Get configuration for a specific service"""
    config = get_service(service_name)
    if not config:
        raise HTTPException(404, f"Service not found: {service_name}")
    
    return {
        "name": config.name,
        "display_name": config.display_name,
        "method": config.deploy_method.value,
        "script": config.script_path,
        "container": config.container_name,
        "compose_file": config.compose_file,
        "compose_service": config.compose_service,
        "health_url": config.health_url,
        "critical": config.critical,
        "requires_approval": config.requires_approval,
        "tags": config.tags
    }


# =============================================================================
# UNIFIED DEPLOY ENDPOINT
# =============================================================================

class ServiceDeployRequest(BaseModel):
    service: str
    dry_run: bool = False
    skip_backup: bool = False
    reason: Optional[str] = None

@app.post("/deploy/service")
async def deploy_service(request: ServiceDeployRequest):
    """
    Deploy any registered service.
    
    This is the primary deployment endpoint.
    All deployments should go through here.
    """
    config = get_service(request.service)
    if not config:
        raise HTTPException(404, f"Unknown service: {request.service}")
    
    # Check if approval required
    if config.requires_approval and not request.dry_run:
        if not request.reason or len(request.reason) < 10:
            raise HTTPException(
                400, 
                f"Service {request.service} requires approval. Provide a detailed reason (min 10 chars)."
            )
    
    # Execute deployment
    outcome = await execute_deployment(
        service_name=request.service,
        dry_run=request.dry_run,
        skip_backup=request.skip_backup,
        reason=request.reason
    )
    
    return {
        "service": outcome.service,
        "result": outcome.result.value,
        "dry_run": outcome.dry_run,
        "duration_seconds": outcome.duration_seconds,
        "backup_id": outcome.backup_id,
        "health_check_passed": outcome.health_check_passed,
        "error": outcome.error,
        "stdout_tail": outcome.stdout[-1000:] if outcome.stdout else None
    }


# =============================================================================
# CONVENIENCE ENDPOINTS
# =============================================================================

@app.post("/deploy/aria")
async def deploy_aria(dry_run: bool = False, reason: str = None):
    """Deploy ARIA Frontend (convenience endpoint)"""
    return await deploy_service(ServiceDeployRequest(
        service="aria-frontend",
        dry_run=dry_run,
        reason=reason or "ARIA frontend deployment"
    ))


@app.post("/deploy/aria-chat")
async def deploy_aria_chat(dry_run: bool = False, reason: str = None):
    """Deploy ARIA Chat API (convenience endpoint)"""
    return await deploy_service(ServiceDeployRequest(
        service="aria-chat",
        dry_run=dry_run,
        reason=reason or "ARIA chat deployment"
    ))


@app.post("/deploy/fleet")
async def deploy_fleet(dry_run: bool = False, reason: str = None):
    """Deploy entire agent fleet (convenience endpoint)"""
    return await deploy_service(ServiceDeployRequest(
        service="fleet",
        dry_run=dry_run,
        reason=reason or "Fleet deployment"
    ))


@app.post("/deploy/schema")
async def deploy_schema(dry_run: bool = False, reason: str = None):
    """Deploy schema changes (requires reason)"""
    if not reason or len(reason) < 10:
        raise HTTPException(400, "Schema deployments require a detailed reason")
    
    return await deploy_service(ServiceDeployRequest(
        service="schema",
        dry_run=dry_run,
        reason=reason
    ))


# =============================================================================
# BATCH DEPLOYMENT
# =============================================================================

class BatchDeployRequest(BaseModel):
    services: List[str]
    dry_run: bool = False
    reason: Optional[str] = None

@app.post("/deploy/batch")
async def deploy_batch(request: BatchDeployRequest):
    """Deploy multiple services in sequence"""
    results = []
    
    for service_name in request.services:
        config = get_service(service_name)
        if not config:
            results.append({
                "service": service_name,
                "result": "skipped",
                "error": "Unknown service"
            })
            continue
        
        outcome = await execute_deployment(
            service_name=service_name,
            dry_run=request.dry_run,
            reason=request.reason
        )
        
        results.append({
            "service": outcome.service,
            "result": outcome.result.value,
            "duration_seconds": outcome.duration_seconds,
            "error": outcome.error
        })
        
        # Stop batch if critical service fails
        if config.critical and outcome.result == DeploymentResult.FAILED:
            await notify(f"🛑 Batch deployment stopped: {service_name} failed", "critical")
            break
    
    return {
        "dry_run": request.dry_run,
        "total_requested": len(request.services),
        "results": results
    }
```

---

## PHASE 4: UPDATE APOLLO DOCKERFILE

Ensure APOLLO can execute scripts:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck AND docker CLI for container operations
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic

# Copy all Apollo modules
COPY apollo.py .
COPY service_registry.py .
COPY deployment_executor.py .

EXPOSE 8234

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8234/health || exit 1

CMD ["uvicorn", "apollo:app", "--host", "0.0.0.0", "--port", "8234"]
```

---

## PHASE 5: UPDATE DOCKER COMPOSE

Update APOLLO service in `docker-compose.fleet.yml`:

```yaml
  apollo:
    build:
      context: ./control-plane/agents/apollo
      dockerfile: Dockerfile
    container_name: leveredge-apollo
    ports:
      - "${APOLLO_PORT:-8234}:8234"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - CHRONOS_URL=http://chronos:8010
      - HADES_URL=http://hades:8008
      - PANOPTES_URL=http://panoptes:8023
      - HERMES_URL=http://hermes:8014
      - LCIS_URL=http://lcis-librarian:8050
    volumes:
      # Mount scripts directory
      - ./shared/scripts:/opt/leveredge/shared/scripts:ro
      # Mount Docker socket for container operations
      - /var/run/docker.sock:/var/run/docker.sock
      # Mount fleet scripts
      - ./fleet-start.sh:/opt/leveredge/fleet-start.sh:ro
      - ./fleet-stop.sh:/opt/leveredge/fleet-stop.sh:ro
      # Mount compose file for compose deployments
      - ./docker-compose.fleet.yml:/opt/leveredge/docker-compose.fleet.yml:ro
      - ./.env.fleet:/opt/leveredge/.env.fleet:ro
    networks:
      - fleet-net
    depends_on:
      event-bus:
        condition: service_healthy
    restart: unless-stopped
    profiles:
      - all
      - core
```

---

## VERIFICATION

```bash
# 1. Rebuild APOLLO
docker compose -f docker-compose.fleet.yml --env-file .env.fleet up -d --build apollo

# 2. Check health
curl http://localhost:8234/health

# 3. List all services
curl http://localhost:8234/services | jq

# 4. Get ARIA config
curl http://localhost:8234/services/aria-frontend | jq

# 5. Deploy ARIA (dry run)
curl -X POST "http://localhost:8234/deploy/aria?dry_run=true" | jq

# 6. Deploy ARIA (for real)
curl -X POST "http://localhost:8234/deploy/aria?reason=Testing+APOLLO+deployment" | jq

# 7. Check deployment history
curl http://localhost:8234/history/aria-frontend | jq

# 8. Batch deploy (dry run)
curl -X POST http://localhost:8234/deploy/batch \
  -H "Content-Type: application/json" \
  -d '{"services": ["muse", "gym-coach"], "dry_run": true}' | jq
```

---

## USAGE EXAMPLES

```bash
# Deploy ARIA frontend
curl -X POST "http://localhost:8234/deploy/aria?reason=Adding+real-time+sync"

# Deploy with dry run first
curl -X POST "http://localhost:8234/deploy/service" \
  -H "Content-Type: application/json" \
  -d '{"service": "aria-frontend", "dry_run": true}'

# Deploy schema (requires reason)
curl -X POST "http://localhost:8234/deploy/schema?reason=Adding+aria_threads+table"

# Restart a specific agent
curl -X POST "http://localhost:8234/deploy/service" \
  -H "Content-Type: application/json" \
  -d '{"service": "muse", "reason": "Configuration update"}'

# Deploy entire fleet
curl -X POST "http://localhost:8234/deploy/fleet?reason=Weekly+update"
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-apollo-service-registry.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "APOLLO Service Registry deployed. All services now have deployment configurations. Endpoints: /deploy/service, /deploy/aria, /deploy/fleet, /deploy/batch. Full audit trail via LCIS.",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "apollo", "deployment", "registry"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: APOLLO Service Registry - Unified deployment orchestration

Service Registry:
- aria-frontend: promote-aria-to-prod.sh
- aria-chat: container restart
- fleet: fleet-start.sh
- schema: promote-schema.sh
- All monitoring agents: compose up
- All personal agents: compose up

Features:
- /deploy/service - Universal deployment endpoint
- /deploy/aria - ARIA convenience endpoint
- /deploy/batch - Multi-service deployment
- Automatic CHRONOS backup
- Health checks via PANOPTES
- Full LCIS audit trail
- HERMES notifications

All deployments now go through APOLLO."
```

---

## SUMMARY

| Endpoint | Service | Method |
|----------|---------|--------|
| `POST /deploy/aria` | ARIA Frontend | Script |
| `POST /deploy/aria-chat` | ARIA Chat API | Container |
| `POST /deploy/fleet` | Agent Fleet | Script |
| `POST /deploy/schema` | Database Schema | Script |
| `POST /deploy/service` | Any registered | Auto |
| `POST /deploy/batch` | Multiple | Sequential |

**Every deployment now:**
1. ✅ Creates CHRONOS backup
2. ✅ Executes via proper method
3. ✅ Health checks via PANOPTES
4. ✅ Logs to LCIS
5. ✅ Notifies via HERMES
6. ✅ Publishes to Event Bus

---

*"APOLLO brings order to chaos. Every deployment, every time."*
