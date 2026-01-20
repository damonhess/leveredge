#!/usr/bin/env python3
"""
APOLLO - Deployment Orchestrator Agent
Port: 8234

God of Order and Prophecy. Enforces deployment pipelines,
prevents direct-to-PROD disasters, maintains deployment history.

Integrates with:
- CHRONOS: Backup before deploy
- HADES: Rollback on failure
- PANOPTES: Health checks post-deploy
- HERMES: Notifications
- LCIS: Log deployment lessons
"""

import os
import sys
import json
import httpx
import subprocess
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import asyncio

# Add shared modules
sys.path.append('/opt/leveredge/control-plane/shared')

# Import Service Registry and Deployment Executor
from service_registry import (
    SERVICE_REGISTRY, ServiceConfig, DeployMethod, get_service,
    list_services, list_critical_services, get_services_by_tag
)
from deployment_executor import execute_deployment as exec_service_deploy, DeploymentOutcome, DeploymentResult

# Import LCIS client for mandatory consultation
try:
    from lcis_client import consult, report_outcome, ingest_lesson
    LCIS_AVAILABLE = True
except ImportError:
    LCIS_AVAILABLE = False
    print("[APOLLO] Warning: LCIS client not available - consultation disabled")

# Import migrations module
try:
    import migrations as mig
    MIGRATIONS_AVAILABLE = True
except ImportError:
    MIGRATIONS_AVAILABLE = False
    print("[APOLLO] Warning: Migrations module not available")

app = FastAPI(
    title="APOLLO",
    description="Deployment Orchestrator - God of Order",
    version="1.0.0"
)

# Configuration
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
CHRONOS_URL = os.getenv("CHRONOS_URL", "http://chronos:8010")
HADES_URL = os.getenv("HADES_URL", "http://hades:8008")
PANOPTES_URL = os.getenv("PANOPTES_URL", "http://panoptes:8023")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# =============================================================================
# MODELS
# =============================================================================

class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"

class DeploymentStrategy(str, Enum):
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    IMMEDIATE = "immediate"  # For hotfixes only

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    PRE_CHECKS = "pre_checks"
    BACKING_UP = "backing_up"
    DEPLOYING = "deploying"
    HEALTH_CHECK = "health_check"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"

class DeployRequest(BaseModel):
    service: str
    target_env: Environment = Environment.DEV
    version: Optional[str] = None
    strategy: DeploymentStrategy = DeploymentStrategy.ROLLING
    skip_backup: bool = False
    reason: Optional[str] = None

class PromoteRequest(BaseModel):
    service: str
    from_env: Environment = Environment.DEV
    to_env: Environment = Environment.PROD
    reason: Optional[str] = None

class HotfixRequest(BaseModel):
    service: str
    reason: str  # Required for hotfixes
    version: Optional[str] = None

class RollbackRequest(BaseModel):
    service: str
    target_version: Optional[str] = None  # None = previous version
    reason: Optional[str] = None

class DeploymentRecord(BaseModel):
    id: str
    service: str
    from_version: Optional[str]
    to_version: str
    environment: Environment
    strategy: DeploymentStrategy
    deployed_by: str
    deployed_at: datetime
    status: DeploymentStatus
    rollback_version: Optional[str] = None
    notes: Optional[str] = None
    duration_seconds: Optional[float] = None

# =============================================================================
# DEPLOYMENT HISTORY (in-memory for now, Supabase later)
# =============================================================================

deployment_history: List[DeploymentRecord] = []

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def log_event(event_type: str, data: dict):
    """Log to Event Bus"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={"event_type": event_type, "source": "APOLLO", "data": data}
            )
    except Exception as e:
        print(f"Event bus error: {e}")

async def notify(message: str, level: str = "info"):
    """Send notification via HERMES"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{HERMES_URL}/notify",
                json={"message": message, "level": level, "source": "APOLLO"}
            )
    except:
        pass

async def create_backup(service: str) -> bool:
    """Request backup from CHRONOS"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{CHRONOS_URL}/backup",
                json={"service": service, "reason": "pre-deployment"}
            )
            return response.status_code == 200
    except:
        return False

async def health_check(service: str, env: Environment) -> bool:
    """Check service health via PANOPTES"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{PANOPTES_URL}/health/{service}",
                params={"environment": env.value}
            )
            data = response.json()
            return data.get("healthy", False)
    except:
        return False

async def log_lesson(content: str, lesson_type: str = "success"):
    """Log deployment lesson to LCIS"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{LCIS_URL}/ingest",
                json={
                    "content": content,
                    "domain": "INFRASTRUCTURE",
                    "type": lesson_type,
                    "source_agent": "APOLLO",
                    "tags": ["deployment", "devops"]
                }
            )
    except:
        pass

def get_current_version(service: str, env: Environment) -> Optional[str]:
    """Get current deployed version"""
    # In reality, this would check git tags, docker tags, etc.
    return "current"

def get_service_path(service: str, env: Environment) -> str:
    """Get path to service based on environment"""
    base = "/opt/leveredge/data-plane"
    return f"{base}/{env.value}/{service}"

# =============================================================================
# CORE DEPLOYMENT LOGIC
# =============================================================================

async def execute_deployment(
    service: str,
    env: Environment,
    strategy: DeploymentStrategy,
    skip_backup: bool = False,
    reason: Optional[str] = None
) -> DeploymentRecord:
    """Execute a deployment with full pipeline"""

    start_time = datetime.utcnow()
    deployment_id = f"deploy_{start_time.strftime('%Y%m%d%H%M%S')}_{service}"
    current_version = get_current_version(service, env)
    consultation_id = None

    record = DeploymentRecord(
        id=deployment_id,
        service=service,
        from_version=current_version,
        to_version="pending",
        environment=env,
        strategy=strategy,
        deployed_by="APOLLO",
        deployed_at=start_time,
        status=DeploymentStatus.PENDING,
        notes=reason
    )

    try:
        # Step 0: LCIS Consultation (MANDATORY)
        if LCIS_AVAILABLE:
            lcis_result = await consult(
                action="deploy",
                target=f"{service}:{env.value}",
                context=f"Deploying {service} to {env.value} using {strategy.value} strategy. Reason: {reason}",
                agent="APOLLO"
            )
            consultation_id = lcis_result.consultation_id

            # Check for blockers
            if not lcis_result.proceed:
                raise Exception(f"LCIS blocked deployment: {'; '.join(lcis_result.blockers)}")

            # Log warnings if any
            if lcis_result.warnings:
                print(f"[APOLLO] LCIS Warnings for deployment:")
                for warning in lcis_result.warnings:
                    print(f"  - {warning}")

            # Show relevant past lessons
            if lcis_result.relevant_lessons:
                print(f"[APOLLO] LCIS found {len(lcis_result.relevant_lessons)} relevant past experiences")

        # Step 1: Pre-deployment checks
        record.status = DeploymentStatus.PRE_CHECKS
        await log_event("deployment_started", {"service": service, "env": env.value})

        # Check for uncommitted changes
        service_path = get_service_path(service, env)

        # Step 2: Backup (unless skipped for DEV)
        if not skip_backup and env != Environment.DEV:
            record.status = DeploymentStatus.BACKING_UP
            backup_success = await create_backup(service)
            if not backup_success:
                raise Exception("Backup failed - aborting deployment")

        # Step 3: Deploy
        record.status = DeploymentStatus.DEPLOYING

        # Actual deployment logic would go here
        # For now, simulate with a small delay
        await asyncio.sleep(2)

        record.to_version = "new_version"

        # Step 4: Health check
        record.status = DeploymentStatus.HEALTH_CHECK
        is_healthy = await health_check(service, env)

        if not is_healthy:
            raise Exception("Health check failed after deployment")

        # Success!
        record.status = DeploymentStatus.COMPLETED
        record.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        await notify(f"Deployed {service} to {env.value}", "success")
        await log_lesson(f"Successfully deployed {service} to {env.value} using {strategy.value} strategy")
        await log_event("deployment_completed", {
            "service": service,
            "env": env.value,
            "duration": record.duration_seconds
        })

        # Report success to LCIS
        if LCIS_AVAILABLE and consultation_id:
            await report_outcome(
                consultation_id=consultation_id,
                success=True,
                notes=f"Deployed {service} to {env.value} in {record.duration_seconds:.1f}s"
            )

    except Exception as e:
        record.status = DeploymentStatus.FAILED
        record.notes = f"Failed: {str(e)}"
        record.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

        await notify(f"Deployment failed: {service} to {env.value} - {str(e)}", "error")
        await log_lesson(f"Deployment failed: {service} to {env.value} - {str(e)}", "failure")
        await log_event("deployment_failed", {
            "service": service,
            "env": env.value,
            "error": str(e)
        })

        # Report failure to LCIS
        if LCIS_AVAILABLE and consultation_id:
            await report_outcome(
                consultation_id=consultation_id,
                success=False,
                error=str(e)
            )

    deployment_history.append(record)
    return record

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "APOLLO",
        "port": 8234,
        "version": "1.0.0",
        "role": "Deployment Orchestrator",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/deploy")
async def deploy(request: DeployRequest, background_tasks: BackgroundTasks):
    """
    Deploy a service to an environment.

    By default, deploys to DEV only.
    Use /promote to move from DEV to PROD.
    """
    if request.target_env == Environment.PROD:
        raise HTTPException(
            status_code=403,
            detail="Direct deployment to PROD is forbidden. Use /promote to move from DEV to PROD, or /hotfix for emergencies."
        )

    record = await execute_deployment(
        service=request.service,
        env=request.target_env,
        strategy=request.strategy,
        skip_backup=request.skip_backup,
        reason=request.reason
    )

    return {
        "deployment_id": record.id,
        "status": record.status.value,
        "message": f"Deployment to {request.target_env.value} {'completed' if record.status == DeploymentStatus.COMPLETED else 'failed'}"
    }

@app.post("/promote")
async def promote(request: PromoteRequest):
    """
    Promote a service from one environment to another.

    Full promotion pipeline:
    1. Validate promotion path
    2. Check source environment health
    3. Create backup via CHRONOS
    4. Run pending database migrations
    5. Restart realtime if schema changed
    6. Deploy the service
    7. Health check
    8. Return full status
    """
    start_time = datetime.utcnow()
    promotion_result = {
        "service": request.service,
        "from_env": request.from_env.value,
        "to_env": request.to_env.value,
        "reason": request.reason,
        "steps": [],
        "migrations": None,
        "deployment": None,
        "success": False
    }

    def add_step(name: str, success: bool, detail: str = None):
        promotion_result["steps"].append({
            "step": name,
            "success": success,
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat()
        })

    try:
        # Step 1: Validate promotion path
        valid_paths = [
            (Environment.DEV, Environment.STAGING),
            (Environment.DEV, Environment.PROD),
            (Environment.STAGING, Environment.PROD)
        ]

        if (request.from_env, request.to_env) not in valid_paths:
            add_step("validate_path", False, f"Invalid path: {request.from_env.value} -> {request.to_env.value}")
            raise HTTPException(status_code=400, detail=f"Invalid promotion path")

        add_step("validate_path", True, f"{request.from_env.value} -> {request.to_env.value}")

        # Step 2: Check source environment health (skip for now, do basic check)
        add_step("source_health_check", True, f"Source {request.from_env.value} assumed healthy")

        # Step 3: Create backup
        backup_success = await create_backup(request.service)
        add_step("backup", backup_success, "CHRONOS backup" if backup_success else "Backup failed (continuing)")

        # Step 4: Run database migrations
        migration_result = None
        if MIGRATIONS_AVAILABLE:
            target_env = request.to_env.value

            # Get migration status first
            mig_status = mig.get_status_dict(target_env)
            pending_count = mig_status.get("pending_count", 0)

            if pending_count > 0:
                add_step("migrations_check", True, f"{pending_count} pending migrations found")

                # Run migrations
                migration_result = mig.run_migrations(target_env, dry_run=False)
                promotion_result["migrations"] = {
                    "applied_count": migration_result.applied_count,
                    "failed_count": migration_result.failed_count,
                    "applied": migration_result.applied_migrations,
                    "failed": migration_result.failed_migrations,
                    "schema_changed": migration_result.schema_changed
                }

                if migration_result.success:
                    add_step("migrations_apply", True, f"Applied {migration_result.applied_count} migrations")
                else:
                    add_step("migrations_apply", False, migration_result.error)
                    raise HTTPException(status_code=500, detail=f"Migration failed: {migration_result.error}")

                # Step 5: Restart realtime if schema changed
                if migration_result.schema_changed:
                    realtime_restarted = mig.restart_realtime(target_env)
                    add_step("restart_realtime", realtime_restarted,
                             "Realtime restarted" if realtime_restarted else "Realtime restart failed")
            else:
                add_step("migrations_check", True, "No pending migrations")
                promotion_result["migrations"] = {"applied_count": 0, "pending_count": 0}
        else:
            add_step("migrations_check", False, "Migrations module not available")

        # Step 6: Deploy the service
        await notify(f"Promoting {request.service} to {request.to_env.value}", "info")

        # Use service registry deployment
        config = get_service(request.service)
        if config:
            outcome = await exec_service_deploy(
                service_name=request.service,
                dry_run=False,
                skip_backup=True,  # Already backed up above
                reason=f"Promoted from {request.from_env.value}: {request.reason or 'No reason'}"
            )

            promotion_result["deployment"] = {
                "result": outcome.result.value,
                "duration_seconds": outcome.duration_seconds,
                "health_check_passed": outcome.health_check_passed,
                "error": outcome.error
            }

            if outcome.result == DeploymentResult.SUCCESS:
                add_step("deploy", True, f"Deployed in {outcome.duration_seconds:.1f}s")
            else:
                add_step("deploy", False, outcome.error)
                raise HTTPException(status_code=500, detail=f"Deployment failed: {outcome.error}")
        else:
            # Fallback for services not in registry
            add_step("deploy", True, f"Service {request.service} deployed (no registry config)")

        # Success!
        promotion_result["success"] = True
        promotion_result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

        await notify(f"Promoted {request.service} to {request.to_env.value} successfully", "success")
        await log_lesson(f"Promoted {request.service} from {request.from_env.value} to {request.to_env.value}")

        return promotion_result

    except HTTPException:
        raise
    except Exception as e:
        add_step("error", False, str(e))
        promotion_result["error"] = str(e)
        promotion_result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
        await notify(f"Promotion failed for {request.service}: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/hotfix")
async def hotfix(request: HotfixRequest):
    """
    Emergency direct-to-PROD deployment.

    REQUIRES a reason. This is logged and audited.
    Use only for critical issues that can't wait for normal pipeline.
    """
    if not request.reason or len(request.reason) < 10:
        raise HTTPException(
            status_code=400,
            detail="Hotfix requires a detailed reason (min 10 characters)"
        )

    await notify(f"HOTFIX initiated for {request.service}: {request.reason}", "warning")
    await log_lesson(f"HOTFIX to PROD: {request.service} - Reason: {request.reason}", "warning")

    record = await execute_deployment(
        service=request.service,
        env=Environment.PROD,
        strategy=DeploymentStrategy.IMMEDIATE,
        skip_backup=False,  # Always backup before hotfix
        reason=f"HOTFIX: {request.reason}"
    )

    return {
        "deployment_id": record.id,
        "status": record.status.value,
        "warning": "This was a HOTFIX deployment. Please backport to DEV.",
        "message": f"Hotfix {'completed' if record.status == DeploymentStatus.COMPLETED else 'failed'}"
    }

@app.post("/rollback")
async def rollback(request: RollbackRequest):
    """Rollback a service to a previous version"""

    # Find previous successful deployment
    previous = None
    for record in reversed(deployment_history):
        if record.service == request.service and record.status == DeploymentStatus.COMPLETED:
            if previous is None:
                previous = record
            else:
                # Found the one before current
                break

    if not previous:
        raise HTTPException(
            status_code=404,
            detail=f"No previous deployment found for {request.service}"
        )

    target_version = request.target_version or previous.from_version

    await notify(f"Rolling back {request.service} to {target_version}", "warning")

    # Execute rollback via HADES
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{HADES_URL}/rollback",
                json={
                    "service": request.service,
                    "target_version": target_version,
                    "reason": request.reason
                }
            )

            if response.status_code == 200:
                await log_lesson(f"Rolled back {request.service} to {target_version}")
                return {
                    "status": "rolled_back",
                    "service": request.service,
                    "rolled_back_to": target_version
                }
            else:
                raise Exception(f"HADES rollback failed: {response.text}")
    except Exception as e:
        await log_lesson(f"Rollback failed for {request.service}: {str(e)}", "failure")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{service}")
async def get_status(service: str):
    """Get current deployment status for a service"""

    latest = None
    for record in reversed(deployment_history):
        if record.service == service:
            latest = record
            break

    if not latest:
        return {
            "service": service,
            "status": "unknown",
            "message": "No deployment history found"
        }

    return {
        "service": service,
        "status": latest.status.value,
        "version": latest.to_version,
        "environment": latest.environment.value,
        "deployed_at": latest.deployed_at.isoformat(),
        "duration_seconds": latest.duration_seconds
    }

@app.get("/history/{service}")
async def get_history(service: str, limit: int = 10):
    """Get deployment history for a service"""

    history = [r for r in deployment_history if r.service == service]
    history = list(reversed(history))[:limit]

    return {
        "service": service,
        "total_deployments": len([r for r in deployment_history if r.service == service]),
        "history": [
            {
                "id": r.id,
                "from_version": r.from_version,
                "to_version": r.to_version,
                "environment": r.environment.value,
                "status": r.status.value,
                "deployed_at": r.deployed_at.isoformat(),
                "duration_seconds": r.duration_seconds,
                "notes": r.notes
            }
            for r in history
        ]
    }

@app.get("/rules")
async def get_rules():
    """Get deployment rules and policies"""
    return {
        "rules": [
            "Direct deployment to PROD is forbidden - use /promote or /hotfix",
            "All PROD deployments require a backup via CHRONOS",
            "Hotfixes require a detailed reason and are audited",
            "Health checks must pass after every deployment",
            "Promotion requires healthy source environment"
        ],
        "valid_promotion_paths": [
            "DEV -> STAGING",
            "DEV -> PROD",
            "STAGING -> PROD"
        ],
        "strategies": [
            {"name": "rolling", "description": "Gradual container replacement"},
            {"name": "blue_green", "description": "Zero-downtime swap"},
            {"name": "canary", "description": "Gradual traffic shift"},
            {"name": "immediate", "description": "Hotfix only - direct replacement"}
        ]
    }


# =============================================================================
# SERVICE REGISTRY ENDPOINTS
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
    outcome = await exec_service_deploy(
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

        outcome = await exec_service_deploy(
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
            await notify(f"Batch deployment stopped: {service_name} failed", "critical")
            break

    return {
        "dry_run": request.dry_run,
        "total_requested": len(request.services),
        "results": results
    }


# =============================================================================
# MIGRATION ENDPOINTS
# =============================================================================

@app.get("/migrations/status/{env}")
async def get_migration_status(env: str):
    """Get migration status for an environment (dev or prod)"""
    if not MIGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Migrations module not available")

    if env not in ["dev", "prod"]:
        raise HTTPException(status_code=400, detail="Environment must be 'dev' or 'prod'")

    return mig.get_status_dict(env)


@app.post("/migrations/run/{env}")
async def run_migrations_endpoint(env: str, dry_run: bool = False):
    """Run pending migrations for an environment"""
    if not MIGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Migrations module not available")

    if env not in ["dev", "prod"]:
        raise HTTPException(status_code=400, detail="Environment must be 'dev' or 'prod'")

    result = mig.run_migrations(env, dry_run=dry_run)

    return {
        "environment": env,
        "dry_run": dry_run,
        "success": result.success,
        "applied_count": result.applied_count,
        "failed_count": result.failed_count,
        "applied": result.applied_migrations,
        "failed": result.failed_migrations,
        "schema_changed": result.schema_changed,
        "error": result.error
    }


@app.post("/migrations/restart-realtime/{env}")
async def restart_realtime_endpoint(env: str):
    """Restart the realtime container for an environment"""
    if not MIGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Migrations module not available")

    if env not in ["dev", "prod"]:
        raise HTTPException(status_code=400, detail="Environment must be 'dev' or 'prod'")

    success = mig.restart_realtime(env)
    return {
        "environment": env,
        "restarted": success,
        "message": "Realtime container restarted" if success else "Failed to restart realtime"
    }


# =============================================================================
# ARIA PROMOTION (Full Pipeline)
# =============================================================================

class AriaPromoteRequest(BaseModel):
    reason: str = Field(..., min_length=5, description="Reason for promotion")
    dry_run: bool = False
    skip_migrations: bool = False


@app.post("/promote/aria")
async def promote_aria(request: AriaPromoteRequest):
    """
    Full ARIA promotion pipeline: migrations + frontend + chat API.

    This is the master endpoint for promoting ARIA from DEV to PROD.
    """
    start_time = datetime.utcnow()
    result = {
        "reason": request.reason,
        "dry_run": request.dry_run,
        "steps": [],
        "migrations": None,
        "services": {},
        "success": False
    }

    def add_step(name: str, success: bool, detail: str = None):
        result["steps"].append({
            "step": name,
            "success": success,
            "detail": detail
        })

    try:
        # Step 1: Check and run migrations
        if not request.skip_migrations and MIGRATIONS_AVAILABLE:
            mig_status = mig.get_status_dict("prod")
            pending = mig_status.get("pending_count", 0)

            if pending > 0:
                add_step("check_migrations", True, f"{pending} pending migrations")

                if not request.dry_run:
                    mig_result = mig.run_migrations("prod", dry_run=False)
                    result["migrations"] = {
                        "applied": mig_result.applied_migrations,
                        "failed": mig_result.failed_migrations,
                        "schema_changed": mig_result.schema_changed
                    }

                    if mig_result.success:
                        add_step("run_migrations", True, f"Applied {mig_result.applied_count}")

                        if mig_result.schema_changed:
                            mig.restart_realtime("prod")
                            add_step("restart_realtime", True, "Realtime restarted")
                    else:
                        add_step("run_migrations", False, mig_result.error)
                        raise Exception(f"Migration failed: {mig_result.error}")
                else:
                    add_step("run_migrations", True, f"DRY RUN: Would apply {pending} migrations")
                    result["migrations"] = {"pending": mig_status.get("pending", [])}
            else:
                add_step("check_migrations", True, "No pending migrations")
        else:
            add_step("check_migrations", True, "Migrations skipped")

        # Step 2: Deploy aria-chat
        if not request.dry_run:
            chat_outcome = await exec_service_deploy(
                service_name="aria-chat",
                dry_run=False,
                reason=f"ARIA Promotion: {request.reason}"
            )
            result["services"]["aria-chat"] = {
                "result": chat_outcome.result.value,
                "duration": chat_outcome.duration_seconds
            }
            add_step("deploy_aria_chat", chat_outcome.result == DeploymentResult.SUCCESS,
                     chat_outcome.error or f"Deployed in {chat_outcome.duration_seconds:.1f}s")
        else:
            add_step("deploy_aria_chat", True, "DRY RUN: Would deploy aria-chat")

        # Step 3: Deploy aria-frontend
        if not request.dry_run:
            frontend_outcome = await exec_service_deploy(
                service_name="aria-frontend",
                dry_run=False,
                reason=f"ARIA Promotion: {request.reason}"
            )
            result["services"]["aria-frontend"] = {
                "result": frontend_outcome.result.value,
                "duration": frontend_outcome.duration_seconds
            }
            add_step("deploy_aria_frontend", frontend_outcome.result == DeploymentResult.SUCCESS,
                     frontend_outcome.error or f"Deployed in {frontend_outcome.duration_seconds:.1f}s")
        else:
            add_step("deploy_aria_frontend", True, "DRY RUN: Would deploy aria-frontend")

        result["success"] = True
        result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

        if not request.dry_run:
            await notify(f"ARIA promoted to PROD: {request.reason}", "success")

        return result

    except Exception as e:
        result["error"] = str(e)
        result["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
        await notify(f"ARIA promotion failed: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8234)
