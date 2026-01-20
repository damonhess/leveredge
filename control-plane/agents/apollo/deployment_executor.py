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
                f"{LCIS_URL}/ingest",
                json={
                    "content": content,
                    "domain": "THE_KEEP",
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
        # Check if env file exists
        env_file = "/opt/leveredge/.env.fleet"
        cmd = [
            "docker", "compose",
            "-f", config.compose_file,
        ]

        if os.path.exists(env_file):
            cmd.extend(["--env-file", env_file])

        cmd.extend(["up", "-d", "--build", config.compose_service])

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
    await notify(f"Starting {config.display_name} deployment ({mode})", "info")

    # Create backup (unless dry run or skipped)
    if not dry_run and not skip_backup and not config.skip_backup_allowed:
        backup_id = await create_backup(service_name, config.backup_type)
        if backup_id:
            await notify(f"Backup created: {backup_id}", "info")
        else:
            await notify(f"Backup failed for {service_name}", "warning")

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
            await notify(f"Health check failed for {config.display_name}", "critical")
            result["success"] = False
            result["error"] = "Health check failed"

    # Determine outcome
    completed_at = datetime.utcnow()
    duration = (completed_at - started_at).total_seconds()

    if result.get("success"):
        deploy_result = DeploymentResult.SUCCESS
        await notify(f"{config.display_name} deployment complete ({duration:.1f}s)", "info")
    else:
        deploy_result = DeploymentResult.FAILED
        await notify(f"{config.display_name} deployment failed: {result.get('error', 'Unknown')}", "critical")

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
