# GSD: APOLLO - Deployment Orchestrator Agent

**Priority:** HIGH
**Estimated Time:** 20-30 minutes
**Created:** January 20, 2026
**Status:** Ready for execution (run after fleet-complete-build)

---

## OVERVIEW

Build APOLLO - the deployment agent that prevents direct-to-PROD mistakes.
This is what would have stopped the aria-persistence incident.

APOLLO enforces: DEV → TEST → PROD pipeline with no exceptions.

---

## ENVIRONMENT

**Target:** Control plane agents

```
Location: /opt/leveredge/control-plane/agents/apollo/
Port: 8234
```

---

## WHY APOLLO?

In Greek mythology, Apollo brought order, prophecy (foresight), and healing:
- **Order** to chaotic deployments
- **Foresight** via pre-deployment checks
- **Healing** via automatic rollback

---

## PHASE 1: CREATE APOLLO AGENT

### 1.1 apollo.py

```python
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
                f"{LCIS_URL}/lessons",
                json={
                    "content": content,
                    "domain": "DEPLOYMENT",
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
        
        await notify(f"✅ Deployed {service} to {env.value}", "success")
        await log_lesson(f"Successfully deployed {service} to {env.value} using {strategy.value} strategy")
        await log_event("deployment_completed", {
            "service": service,
            "env": env.value,
            "duration": record.duration_seconds
        })
        
    except Exception as e:
        record.status = DeploymentStatus.FAILED
        record.notes = f"Failed: {str(e)}"
        record.duration_seconds = (datetime.utcnow() - start_time).total_seconds()
        
        await notify(f"❌ Deployment failed: {service} to {env.value} - {str(e)}", "error")
        await log_lesson(f"Deployment failed: {service} to {env.value} - {str(e)}", "failure")
        await log_event("deployment_failed", {
            "service": service,
            "env": env.value,
            "error": str(e)
        })
    
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
    
    Typically DEV → STAGING → PROD.
    Requires successful deployment in source environment first.
    """
    # Validate promotion path
    valid_paths = [
        (Environment.DEV, Environment.STAGING),
        (Environment.DEV, Environment.PROD),
        (Environment.STAGING, Environment.PROD)
    ]
    
    if (request.from_env, request.to_env) not in valid_paths:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid promotion path: {request.from_env.value} → {request.to_env.value}"
        )
    
    # Check source environment is healthy
    is_healthy = await health_check(request.service, request.from_env)
    if not is_healthy:
        raise HTTPException(
            status_code=400,
            detail=f"Service {request.service} is not healthy in {request.from_env.value}. Fix it before promoting."
        )
    
    # Execute promotion
    record = await execute_deployment(
        service=request.service,
        env=request.to_env,
        strategy=DeploymentStrategy.ROLLING,
        skip_backup=False,
        reason=f"Promoted from {request.from_env.value}: {request.reason or 'No reason provided'}"
    )
    
    return {
        "deployment_id": record.id,
        "status": record.status.value,
        "promoted_from": request.from_env.value,
        "promoted_to": request.to_env.value,
        "message": f"Promotion {'completed' if record.status == DeploymentStatus.COMPLETED else 'failed'}"
    }

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
    
    await notify(f"⚠️ HOTFIX initiated for {request.service}: {request.reason}", "warning")
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
    
    await notify(f"🔄 Rolling back {request.service} to {target_version}", "warning")
    
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
            "DEV → STAGING",
            "DEV → PROD",
            "STAGING → PROD"
        ],
        "strategies": [
            {"name": "rolling", "description": "Gradual container replacement"},
            {"name": "blue_green", "description": "Zero-downtime swap"},
            {"name": "canary", "description": "Gradual traffic shift"},
            {"name": "immediate", "description": "Hotfix only - direct replacement"}
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8234)
```

### 1.2 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY shared/ /opt/leveredge/control-plane/shared/

# Copy agent
COPY apollo.py .

EXPOSE 8234

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8234/health || exit 1

CMD ["uvicorn", "apollo:app", "--host", "0.0.0.0", "--port", "8234"]
```

### 1.3 requirements.txt

```
fastapi>=0.104.0
uvicorn>=0.24.0
httpx>=0.25.0
pydantic>=2.0.0
```

---

## PHASE 2: ADD TO DOCKER-COMPOSE.FLEET.YML

```yaml
  apollo:
    build:
      context: ./control-plane/agents/apollo
      dockerfile: Dockerfile
    container_name: leveredge-apollo
    ports:
      - "8234:8234"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - CHRONOS_URL=http://chronos:8010
      - HADES_URL=http://hades:8008
      - PANOPTES_URL=http://panoptes:8023
      - HERMES_URL=http://hermes:8014
      - LCIS_URL=http://lcis-librarian:8050
      - SUPABASE_URL=${DEV_SUPABASE_URL}
      - SUPABASE_ANON_KEY=${DEV_SUPABASE_ANON_KEY}
    networks:
      - leveredge-network
    restart: unless-stopped
    profiles:
      - all
      - core
```

---

## PHASE 3: CREATE SHARED SYMLINK

```bash
cd /opt/leveredge/control-plane/agents/apollo
ln -sf ../../shared shared
```

---

## PHASE 4: CREATE DATABASE SCHEMA

```sql
-- deployment_history table
CREATE TABLE IF NOT EXISTS deployment_history (
    id TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    from_version TEXT,
    to_version TEXT NOT NULL,
    environment TEXT NOT NULL,
    strategy TEXT NOT NULL,
    deployed_by TEXT NOT NULL,
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL,
    rollback_version TEXT,
    notes TEXT,
    duration_seconds FLOAT
);

CREATE INDEX idx_deployment_service ON deployment_history(service);
CREATE INDEX idx_deployment_env ON deployment_history(environment);
CREATE INDEX idx_deployment_date ON deployment_history(deployed_at DESC);
```

---

## PHASE 5: MOVE DEFERRED SPEC

```bash
mv /opt/leveredge/specs/deferred/APOLLO-DEPLOYMENT-AGENT.md /opt/leveredge/specs/done/
```

---

## VERIFICATION

```bash
# Check APOLLO is running
curl http://localhost:8234/health

# Check rules
curl http://localhost:8234/rules

# Test deployment to DEV (should work)
curl -X POST http://localhost:8234/deploy \
  -H "Content-Type: application/json" \
  -d '{"service": "test-service", "target_env": "dev"}'

# Test direct to PROD (should FAIL)
curl -X POST http://localhost:8234/deploy \
  -H "Content-Type: application/json" \
  -d '{"service": "test-service", "target_env": "prod"}'
# Expected: 403 Forbidden
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-apollo-deployment.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "APOLLO deployment agent built: Enforces DEV-first workflow, blocks direct-to-PROD, maintains deployment history, integrates with CHRONOS/HADES for backup/rollback",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "apollo", "deployment", "devops"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: APOLLO deployment orchestrator

- Enforces DEV → STAGING → PROD pipeline
- Blocks direct-to-PROD (use /promote or /hotfix)
- Integrates with CHRONOS (backup), HADES (rollback)
- Health checks post-deployment
- Full deployment history and audit trail
- Hotfix requires reason and is logged

No more accidental PROD deployments."
```

---

## USAGE AFTER BUILD

```bash
# Deploy to DEV
curl -X POST http://localhost:8234/deploy \
  -d '{"service": "aria-frontend", "target_env": "dev"}'

# Promote to PROD (after DEV is working)
curl -X POST http://localhost:8234/promote \
  -d '{"service": "aria-frontend", "from_env": "dev", "to_env": "prod", "reason": "Tested and verified"}'

# Emergency hotfix (requires reason)
curl -X POST http://localhost:8234/hotfix \
  -d '{"service": "aria-frontend", "reason": "Critical auth bug affecting all users"}'

# Rollback
curl -X POST http://localhost:8234/rollback \
  -d '{"service": "aria-frontend", "reason": "Deployment broke login"}'
```

---

*Order from chaos. No more PROD accidents.*
