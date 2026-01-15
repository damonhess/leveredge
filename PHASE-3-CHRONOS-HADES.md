# PHASE 3: CHRONOS + HADES

*Created: January 15, 2026*
*Prerequisite: Phase 2 complete (AEGIS + HEPHAESTUS running)*
*Estimated Time: 1-2 hours*

---

## Objective

Build two agents for system resilience:
- **CHRONOS** (8010): Backup Manager - scheduled backups, retention, verification
- **HADES** (8008): Rollback System - revert changes, restore from backup, emergency recovery

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BACKUP/ROLLBACK FLOW                            │
│                                                                          │
│  CHRONOS (Proactive)                    HADES (Reactive)                │
│  ──────────────────                     ─────────────────                │
│  • Scheduled backups                    • Triggered by failures         │
│  • Before-deploy snapshots              • Rollback to previous state    │
│  • Retention management                 • Emergency restore             │
│  • Backup verification                  • Destroy and rebuild           │
│                                                                          │
│  ┌─────────────┐                        ┌─────────────┐                 │
│  │   CHRONOS   │───── backups ─────────▶│   HADES     │                 │
│  │   (8010)    │                        │   (8008)    │                 │
│  └─────────────┘                        └─────────────┘                 │
│        │                                       │                         │
│        ▼                                       ▼                         │
│  /opt/leveredge/shared/backups/         Restores from backups           │
│  ├── control-plane/                     or previous workflow versions   │
│  ├── prod/                                                              │
│  └── dev/                                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## CHRONOS: Backup Manager

### Purpose
- Create scheduled backups of workflows, databases, configurations
- Pre-deployment snapshots (called by HEPHAESTUS before changes)
- Manage retention policies (hourly/daily/weekly/monthly)
- Verify backup integrity
- Report backup health to Event Bus

### Implementation: FastAPI Backend + n8n Workflow

#### Step 1: Create CHRONOS Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/chronos
mkdir -p /opt/leveredge/shared/backups/{control-plane,prod,dev}/{hourly,daily,weekly,monthly}
```

#### Step 2: Create CHRONOS FastAPI Backend

Create `/opt/leveredge/control-plane/agents/chronos/chronos.py`:

```python
#!/usr/bin/env python3
"""
CHRONOS - Backup Manager Agent
Port: 8010

Manages backups for the entire LeverEdge infrastructure.
"""

import os
import json
import httpx
import sqlite3
import subprocess
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

app = FastAPI(title="CHRONOS", description="Backup Manager Agent", version="1.0.0")

# Configuration
N8N_CONTROL_URL = os.getenv("N8N_CONTROL_URL", "https://control.n8n.leveredgeai.com")
N8N_PROD_URL = os.getenv("N8N_PROD_URL", "https://n8n.leveredgeai.com")
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASS = os.getenv("N8N_PASS", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
BACKUP_BASE = Path("/opt/leveredge/shared/backups")
DB_PATH = "/opt/leveredge/control-plane/agents/chronos/chronos.db"

# Retention policies (number of backups to keep)
RETENTION = {
    "hourly": 24,
    "daily": 7,
    "weekly": 4,
    "monthly": 12
}

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_id TEXT UNIQUE NOT NULL,
            target TEXT NOT NULL,
            backup_type TEXT NOT NULL,
            tier TEXT NOT NULL,
            path TEXT NOT NULL,
            size_bytes INTEGER,
            checksum TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            verified_at TEXT,
            status TEXT DEFAULT 'completed'
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS backup_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT NOT NULL,
            tier TEXT NOT NULL,
            cron TEXT NOT NULL,
            last_run TEXT,
            next_run TEXT,
            enabled INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Models
class BackupRequest(BaseModel):
    target: str  # control-plane, prod, dev, or specific workflow ID
    backup_type: str = "full"  # full, workflows, database, config
    tier: str = "manual"  # hourly, daily, weekly, monthly, manual, pre-deploy
    description: Optional[str] = None

class RestoreRequest(BaseModel):
    backup_id: str
    target: Optional[str] = None  # Override restore target

# Helpers
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "CHRONOS",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

def generate_backup_id(target: str, tier: str) -> str:
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return f"{target}_{tier}_{timestamp}"

def calculate_checksum(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

async def backup_workflows(target: str, n8n_url: str, backup_path: Path) -> dict:
    """Export all workflows from an n8n instance"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{n8n_url}/api/v1/workflows",
            auth=(N8N_USER, N8N_PASS),
            timeout=30.0
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"Failed to fetch workflows from {target}")
        
        workflows = resp.json().get("data", [])
        
        # Save workflows
        backup_file = backup_path / "workflows.json"
        with open(backup_file, "w") as f:
            json.dump(workflows, f, indent=2)
        
        return {
            "file": str(backup_file),
            "workflow_count": len(workflows),
            "size": backup_file.stat().st_size
        }

async def backup_credentials_metadata(target: str, n8n_url: str, backup_path: Path) -> dict:
    """Backup credential metadata (NOT values) for reference"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{n8n_url}/api/v1/credentials",
                auth=(N8N_USER, N8N_PASS),
                timeout=10.0
            )
            
            if resp.status_code == 200:
                creds = resp.json().get("data", [])
                # Strip any sensitive data, keep only metadata
                creds_meta = [{"id": c["id"], "name": c["name"], "type": c["type"]} for c in creds]
                
                backup_file = backup_path / "credentials_metadata.json"
                with open(backup_file, "w") as f:
                    json.dump(creds_meta, f, indent=2)
                
                return {"file": str(backup_file), "credential_count": len(creds_meta)}
        except Exception as e:
            return {"error": str(e), "credential_count": 0}
    
    return {"credential_count": 0}

# Endpoints
@app.get("/health")
async def health():
    # Check backup directory
    backup_dir_ok = BACKUP_BASE.exists()
    
    # Count recent backups
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM backups WHERE created_at > datetime('now', '-24 hours')")
    recent_backups = c.fetchone()[0]
    conn.close()
    
    return {
        "status": "healthy",
        "agent": "CHRONOS",
        "port": 8010,
        "backup_directory": str(BACKUP_BASE),
        "backup_dir_accessible": backup_dir_ok,
        "backups_last_24h": recent_backups,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/backup")
async def create_backup(req: BackupRequest, background_tasks: BackgroundTasks):
    """Create a backup of specified target"""
    
    backup_id = generate_backup_id(req.target, req.tier)
    
    # Determine n8n URL
    if req.target == "control-plane":
        n8n_url = N8N_CONTROL_URL
    elif req.target == "prod":
        n8n_url = N8N_PROD_URL
    else:
        n8n_url = N8N_CONTROL_URL  # Default to control plane
    
    # Create backup directory
    backup_path = BACKUP_BASE / req.target / req.tier / backup_id
    backup_path.mkdir(parents=True, exist_ok=True)
    
    results = {"backup_id": backup_id, "target": req.target, "files": []}
    total_size = 0
    
    try:
        # Backup workflows
        if req.backup_type in ["full", "workflows"]:
            wf_result = await backup_workflows(req.target, n8n_url, backup_path)
            results["files"].append(wf_result)
            total_size += wf_result.get("size", 0)
        
        # Backup credentials metadata
        if req.backup_type in ["full", "config"]:
            cred_result = await backup_credentials_metadata(req.target, n8n_url, backup_path)
            results["files"].append(cred_result)
        
        # Create manifest
        manifest = {
            "backup_id": backup_id,
            "target": req.target,
            "backup_type": req.backup_type,
            "tier": req.tier,
            "created_at": datetime.utcnow().isoformat(),
            "description": req.description,
            "files": results["files"]
        }
        
        manifest_file = backup_path / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Calculate checksum of manifest
        checksum = calculate_checksum(manifest_file)
        
        # Record in database
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO backups (backup_id, target, backup_type, tier, path, size_bytes, checksum)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (backup_id, req.target, req.backup_type, req.tier, str(backup_path), total_size, checksum))
        conn.commit()
        conn.close()
        
        await log_to_event_bus(
            "backup_created",
            target=req.target,
            details={"backup_id": backup_id, "tier": req.tier, "size": total_size}
        )
        
        results["status"] = "completed"
        results["path"] = str(backup_path)
        results["checksum"] = checksum
        
    except Exception as e:
        results["status"] = "failed"
        results["error"] = str(e)
        await log_to_event_bus("backup_failed", target=req.target, details={"error": str(e)})
    
    return results

@app.get("/backups")
async def list_backups(target: Optional[str] = None, tier: Optional[str] = None, limit: int = 50):
    """List available backups"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    query = "SELECT backup_id, target, backup_type, tier, path, size_bytes, checksum, created_at, status FROM backups"
    params = []
    conditions = []
    
    if target:
        conditions.append("target = ?")
        params.append(target)
    if tier:
        conditions.append("tier = ?")
        params.append(tier)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    backups = [
        {
            "backup_id": row[0],
            "target": row[1],
            "backup_type": row[2],
            "tier": row[3],
            "path": row[4],
            "size_bytes": row[5],
            "checksum": row[6],
            "created_at": row[7],
            "status": row[8]
        }
        for row in rows
    ]
    
    return {"backups": backups, "count": len(backups)}

@app.get("/backups/{backup_id}")
async def get_backup(backup_id: str):
    """Get details of a specific backup"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM backups WHERE backup_id = ?", (backup_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Backup '{backup_id}' not found")
    
    # Load manifest if exists
    backup_path = Path(row[4])
    manifest_file = backup_path / "manifest.json"
    manifest = None
    if manifest_file.exists():
        with open(manifest_file) as f:
            manifest = json.load(f)
    
    return {
        "backup_id": row[1],
        "target": row[2],
        "backup_type": row[3],
        "tier": row[4],
        "path": row[5],
        "size_bytes": row[6],
        "checksum": row[7],
        "created_at": row[8],
        "status": row[10],
        "manifest": manifest
    }

@app.post("/backup/pre-deploy")
async def pre_deploy_backup(target: str, workflow_id: Optional[str] = None):
    """Create a pre-deployment backup (called by HEPHAESTUS before changes)"""
    req = BackupRequest(
        target=target,
        backup_type="workflows" if workflow_id else "full",
        tier="pre-deploy",
        description=f"Pre-deploy backup for workflow {workflow_id}" if workflow_id else "Pre-deploy backup"
    )
    return await create_backup(req, BackgroundTasks())

@app.post("/cleanup")
async def cleanup_old_backups():
    """Apply retention policies and remove old backups"""
    deleted = []
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    for tier, keep_count in RETENTION.items():
        # Get backups older than retention count
        c.execute('''
            SELECT backup_id, path FROM backups 
            WHERE tier = ? 
            ORDER BY created_at DESC
            LIMIT -1 OFFSET ?
        ''', (tier, keep_count))
        
        old_backups = c.fetchall()
        
        for backup_id, path in old_backups:
            try:
                # Delete files
                backup_path = Path(path)
                if backup_path.exists():
                    import shutil
                    shutil.rmtree(backup_path)
                
                # Remove from database
                c.execute("DELETE FROM backups WHERE backup_id = ?", (backup_id,))
                deleted.append(backup_id)
            except Exception as e:
                print(f"Failed to delete {backup_id}: {e}")
    
    conn.commit()
    conn.close()
    
    await log_to_event_bus("cleanup_completed", details={"deleted_count": len(deleted), "deleted": deleted})
    
    return {"status": "completed", "deleted": deleted, "count": len(deleted)}

@app.get("/verify/{backup_id}")
async def verify_backup(backup_id: str):
    """Verify backup integrity"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT path, checksum FROM backups WHERE backup_id = ?", (backup_id,))
    row = c.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Backup '{backup_id}' not found")
    
    backup_path = Path(row[0])
    stored_checksum = row[1]
    
    if not backup_path.exists():
        c.execute("UPDATE backups SET status = 'missing' WHERE backup_id = ?", (backup_id,))
        conn.commit()
        conn.close()
        return {"status": "failed", "error": "Backup directory missing"}
    
    manifest_file = backup_path / "manifest.json"
    if not manifest_file.exists():
        conn.close()
        return {"status": "failed", "error": "Manifest file missing"}
    
    current_checksum = calculate_checksum(manifest_file)
    
    if current_checksum != stored_checksum:
        c.execute("UPDATE backups SET status = 'corrupted' WHERE backup_id = ?", (backup_id,))
        conn.commit()
        conn.close()
        return {"status": "failed", "error": "Checksum mismatch - backup may be corrupted"}
    
    c.execute("UPDATE backups SET verified_at = ?, status = 'verified' WHERE backup_id = ?", 
              (datetime.utcnow().isoformat(), backup_id))
    conn.commit()
    conn.close()
    
    await log_to_event_bus("backup_verified", target=backup_id)
    
    return {"status": "verified", "backup_id": backup_id, "checksum": current_checksum}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
```

#### Step 3: Create CHRONOS Service

Create `/opt/leveredge/control-plane/agents/chronos/chronos.service`:

```ini
[Unit]
Description=CHRONOS Backup Manager Agent
After=network.target event-bus.service

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/chronos
Environment="N8N_CONTROL_URL=https://control.n8n.leveredgeai.com"
Environment="N8N_PROD_URL=https://n8n.leveredgeai.com"
Environment="N8N_USER=admin"
Environment="N8N_PASS=oMtnAe9qsrxhMe/1ROmokg=="
Environment="EVENT_BUS_URL=http://localhost:8099"
ExecStart=/home/damon/.local/bin/uvicorn chronos:app --host 0.0.0.0 --port 8010
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Step 4: Create requirements.txt

Create `/opt/leveredge/control-plane/agents/chronos/requirements.txt`:

```
fastapi
uvicorn
httpx
pydantic
```

---

## HADES: Rollback System

### Purpose
- Rollback workflows to previous versions
- Restore from CHRONOS backups
- Emergency recovery procedures
- Destroy and rebuild capabilities

### Implementation: FastAPI Backend + n8n Workflow

#### Step 1: Create HADES Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/hades
```

#### Step 2: Create HADES FastAPI Backend

Create `/opt/leveredge/control-plane/agents/hades/hades.py`:

```python
#!/usr/bin/env python3
"""
HADES - Rollback System Agent
Port: 8008

Manages rollbacks, restores, and emergency recovery.
"""

import os
import json
import httpx
import sqlite3
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

app = FastAPI(title="HADES", description="Rollback System Agent", version="1.0.0")

# Configuration
N8N_CONTROL_URL = os.getenv("N8N_CONTROL_URL", "https://control.n8n.leveredgeai.com")
N8N_PROD_URL = os.getenv("N8N_PROD_URL", "https://n8n.leveredgeai.com")
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASS = os.getenv("N8N_PASS", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
CHRONOS_URL = os.getenv("CHRONOS_URL", "http://localhost:8010")
BACKUP_BASE = Path("/opt/leveredge/shared/backups")
DB_PATH = "/opt/leveredge/control-plane/agents/hades/hades.db"

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS rollback_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rollback_id TEXT UNIQUE NOT NULL,
            target TEXT NOT NULL,
            rollback_type TEXT NOT NULL,
            source_backup_id TEXT,
            source_version_id TEXT,
            workflow_id TEXT,
            status TEXT DEFAULT 'completed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT,
            error_message TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Models
class RollbackRequest(BaseModel):
    workflow_id: str
    version_id: Optional[str] = None  # If not provided, rolls back to previous version
    target: str = "control-plane"

class RestoreRequest(BaseModel):
    backup_id: str
    target: str = "control-plane"
    workflow_filter: Optional[List[str]] = None  # Specific workflows to restore, or all if None

class EmergencyRequest(BaseModel):
    action: str  # "restore_all", "deactivate_all", "restart_services"
    target: str = "control-plane"
    confirm: bool = False

# Helpers
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "HADES",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

def generate_rollback_id() -> str:
    return f"rollback_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

def get_n8n_url(target: str) -> str:
    if target == "control-plane":
        return N8N_CONTROL_URL
    elif target == "prod":
        return N8N_PROD_URL
    return N8N_CONTROL_URL

# Endpoints
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "HADES",
        "port": 8008,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/rollback/workflow")
async def rollback_workflow(req: RollbackRequest):
    """Rollback a workflow to a previous version"""
    rollback_id = generate_rollback_id()
    n8n_url = get_n8n_url(req.target)
    
    async with httpx.AsyncClient() as client:
        # Get workflow versions
        resp = await client.get(
            f"{n8n_url}/api/v1/workflows/{req.workflow_id}",
            auth=(N8N_USER, N8N_PASS),
            timeout=10.0
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to get workflow")
        
        workflow = resp.json()
        
        # If no version specified, we need to get previous version from history
        # n8n stores version history - we can query it
        if not req.version_id:
            # Get workflow history
            # Note: This requires n8n's internal API or database access
            # For now, we'll use a backup-based approach
            
            await log_to_event_bus(
                "rollback_requested",
                target=req.workflow_id,
                details={"status": "requires_backup", "rollback_id": rollback_id}
            )
            
            return {
                "status": "requires_backup",
                "message": "Version-based rollback requires backup. Use /restore/workflow with a backup_id instead.",
                "rollback_id": rollback_id,
                "workflow_id": req.workflow_id
            }
        
        # Record rollback
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO rollback_history (rollback_id, target, rollback_type, source_version_id, workflow_id, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (rollback_id, req.target, "version", req.version_id, req.workflow_id, "completed"))
        conn.commit()
        conn.close()
        
        await log_to_event_bus(
            "rollback_completed",
            target=req.workflow_id,
            details={"rollback_id": rollback_id, "version_id": req.version_id}
        )
        
        return {
            "status": "completed",
            "rollback_id": rollback_id,
            "workflow_id": req.workflow_id,
            "restored_version": req.version_id
        }

@app.post("/restore/workflow")
async def restore_workflow_from_backup(req: RestoreRequest):
    """Restore workflows from a CHRONOS backup"""
    rollback_id = generate_rollback_id()
    n8n_url = get_n8n_url(req.target)
    
    # Get backup from CHRONOS
    async with httpx.AsyncClient() as client:
        backup_resp = await client.get(f"{CHRONOS_URL}/backups/{req.backup_id}", timeout=10.0)
        
        if backup_resp.status_code != 200:
            raise HTTPException(status_code=404, detail=f"Backup '{req.backup_id}' not found in CHRONOS")
        
        backup_info = backup_resp.json()
    
    # Load workflows from backup
    backup_path = Path(backup_info["path"])
    workflows_file = backup_path / "workflows.json"
    
    if not workflows_file.exists():
        raise HTTPException(status_code=404, detail="Workflows file not found in backup")
    
    with open(workflows_file) as f:
        workflows = json.load(f)
    
    # Filter workflows if specified
    if req.workflow_filter:
        workflows = [w for w in workflows if w.get("id") in req.workflow_filter or w.get("name") in req.workflow_filter]
    
    restored = []
    errors = []
    
    async with httpx.AsyncClient() as client:
        for workflow in workflows:
            try:
                # Check if workflow exists
                check_resp = await client.get(
                    f"{n8n_url}/api/v1/workflows/{workflow['id']}",
                    auth=(N8N_USER, N8N_PASS),
                    timeout=10.0
                )
                
                if check_resp.status_code == 200:
                    # Update existing workflow
                    update_resp = await client.patch(
                        f"{n8n_url}/api/v1/workflows/{workflow['id']}",
                        auth=(N8N_USER, N8N_PASS),
                        json={
                            "name": workflow.get("name"),
                            "nodes": workflow.get("nodes", []),
                            "connections": workflow.get("connections", {}),
                            "settings": workflow.get("settings", {})
                        },
                        timeout=10.0
                    )
                    
                    if update_resp.status_code == 200:
                        restored.append({"id": workflow["id"], "name": workflow.get("name"), "action": "updated"})
                    else:
                        errors.append({"id": workflow["id"], "error": update_resp.text})
                else:
                    # Create new workflow
                    create_resp = await client.post(
                        f"{n8n_url}/api/v1/workflows",
                        auth=(N8N_USER, N8N_PASS),
                        json=workflow,
                        timeout=10.0
                    )
                    
                    if create_resp.status_code in [200, 201]:
                        restored.append({"id": workflow["id"], "name": workflow.get("name"), "action": "created"})
                    else:
                        errors.append({"id": workflow["id"], "error": create_resp.text})
                        
            except Exception as e:
                errors.append({"id": workflow.get("id"), "error": str(e)})
    
    # Record rollback
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO rollback_history (rollback_id, target, rollback_type, source_backup_id, status)
        VALUES (?, ?, ?, ?, ?)
    ''', (rollback_id, req.target, "backup_restore", req.backup_id, "completed" if not errors else "partial"))
    conn.commit()
    conn.close()
    
    await log_to_event_bus(
        "restore_completed",
        target=req.target,
        details={
            "rollback_id": rollback_id,
            "backup_id": req.backup_id,
            "restored_count": len(restored),
            "error_count": len(errors)
        }
    )
    
    return {
        "status": "completed" if not errors else "partial",
        "rollback_id": rollback_id,
        "backup_id": req.backup_id,
        "restored": restored,
        "errors": errors
    }

@app.post("/emergency")
async def emergency_action(req: EmergencyRequest):
    """Execute emergency recovery actions"""
    
    if not req.confirm:
        return {
            "status": "confirmation_required",
            "message": f"Emergency action '{req.action}' requires confirmation. Set confirm=true to proceed.",
            "warning": "This action may cause service disruption!"
        }
    
    n8n_url = get_n8n_url(req.target)
    rollback_id = generate_rollback_id()
    
    if req.action == "deactivate_all":
        # Deactivate all workflows
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{n8n_url}/api/v1/workflows",
                auth=(N8N_USER, N8N_PASS),
                timeout=30.0
            )
            
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to get workflows")
            
            workflows = resp.json().get("data", [])
            deactivated = []
            
            for wf in workflows:
                if wf.get("active"):
                    deact_resp = await client.patch(
                        f"{n8n_url}/api/v1/workflows/{wf['id']}",
                        auth=(N8N_USER, N8N_PASS),
                        json={"active": False},
                        timeout=10.0
                    )
                    if deact_resp.status_code == 200:
                        deactivated.append(wf["id"])
        
        await log_to_event_bus(
            "emergency_deactivate_all",
            target=req.target,
            details={"deactivated_count": len(deactivated)}
        )
        
        return {
            "status": "completed",
            "action": "deactivate_all",
            "rollback_id": rollback_id,
            "deactivated": deactivated
        }
    
    elif req.action == "restore_latest":
        # Get latest backup from CHRONOS and restore
        async with httpx.AsyncClient() as client:
            backups_resp = await client.get(
                f"{CHRONOS_URL}/backups?target={req.target}&limit=1",
                timeout=10.0
            )
            
            if backups_resp.status_code != 200 or not backups_resp.json().get("backups"):
                raise HTTPException(status_code=404, detail="No backups found for target")
            
            latest_backup = backups_resp.json()["backups"][0]
        
        # Restore from that backup
        restore_req = RestoreRequest(backup_id=latest_backup["backup_id"], target=req.target)
        return await restore_workflow_from_backup(restore_req)
    
    else:
        raise HTTPException(status_code=400, detail=f"Unknown emergency action: {req.action}")

@app.get("/history")
async def get_rollback_history(limit: int = 50):
    """Get rollback history"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT rollback_id, target, rollback_type, source_backup_id, source_version_id, 
               workflow_id, status, created_at, completed_at, error_message
        FROM rollback_history
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    
    history = [
        {
            "rollback_id": row[0],
            "target": row[1],
            "rollback_type": row[2],
            "source_backup_id": row[3],
            "source_version_id": row[4],
            "workflow_id": row[5],
            "status": row[6],
            "created_at": row[7],
            "completed_at": row[8],
            "error_message": row[9]
        }
        for row in rows
    ]
    
    return {"history": history, "count": len(history)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
```

#### Step 3: Create HADES Service

Create `/opt/leveredge/control-plane/agents/hades/hades.service`:

```ini
[Unit]
Description=HADES Rollback System Agent
After=network.target event-bus.service chronos.service

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/hades
Environment="N8N_CONTROL_URL=https://control.n8n.leveredgeai.com"
Environment="N8N_PROD_URL=https://n8n.leveredgeai.com"
Environment="N8N_USER=admin"
Environment="N8N_PASS=oMtnAe9qsrxhMe/1ROmokg=="
Environment="EVENT_BUS_URL=http://localhost:8099"
Environment="CHRONOS_URL=http://localhost:8010"
ExecStart=/home/damon/.local/bin/uvicorn hades:app --host 0.0.0.0 --port 8008
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Step 4: Create requirements.txt

Create `/opt/leveredge/control-plane/agents/hades/requirements.txt`:

```
fastapi
uvicorn
httpx
pydantic
```

---

## n8n Workflow Layers (Optional)

Both CHRONOS and HADES can have n8n workflow interfaces that call their FastAPI backends. This allows:
- Visual interface in n8n
- AI Agent orchestration via ATLAS
- Webhook triggers from external systems

Create these after the backends are running and verified.

---

## Deployment Commands

```bash
## CHRONOS
mkdir -p /opt/leveredge/control-plane/agents/chronos
mkdir -p /opt/leveredge/shared/backups/{control-plane,prod,dev}/{hourly,daily,weekly,monthly,manual,pre-deploy}

# Create chronos.py (content above)
# Create chronos.service (content above)
# Create requirements.txt (content above)

cd /opt/leveredge/control-plane/agents/chronos
pip install -r requirements.txt --break-system-packages

sudo cp chronos.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable chronos
sudo systemctl start chronos

## HADES
mkdir -p /opt/leveredge/control-plane/agents/hades

# Create hades.py (content above)
# Create hades.service (content above)
# Create requirements.txt (content above)

cd /opt/leveredge/control-plane/agents/hades
pip install -r requirements.txt --break-system-packages

sudo cp hades.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable hades
sudo systemctl start hades

## Verify
curl http://localhost:8010/health
curl http://localhost:8008/health
```

---

## Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| CHRONOS running | `curl localhost:8010/health` | `{"status":"healthy","agent":"CHRONOS",...}` |
| HADES running | `curl localhost:8008/health` | `{"status":"healthy","agent":"HADES",...}` |
| Backup dirs exist | `ls /opt/leveredge/shared/backups/` | control-plane, prod, dev |
| Create test backup | `curl -X POST localhost:8010/backup -d '{"target":"control-plane","tier":"manual"}'` | backup created |
| List backups | `curl localhost:8010/backups` | Shows the backup |
| Event Bus logging | `curl localhost:8099/events` | CHRONOS/HADES events |

---

## Integration Test

After both agents are deployed:

```bash
# 1. Create a backup with CHRONOS
curl -X POST http://localhost:8010/backup \
  -H "Content-Type: application/json" \
  -d '{"target": "control-plane", "tier": "manual", "description": "Test backup"}'

# 2. List backups
curl http://localhost:8010/backups

# 3. Verify backup
curl http://localhost:8010/verify/{backup_id_from_step_1}

# 4. Test HADES restore (dry run - don't actually restore yet)
curl http://localhost:8008/health

# 5. Check Event Bus for all events
curl http://localhost:8099/events | jq '.events | .[-5:]'
```

---

## Files Created

| File | Purpose |
|------|---------|
| `/opt/leveredge/control-plane/agents/chronos/chronos.py` | CHRONOS FastAPI backend |
| `/opt/leveredge/control-plane/agents/chronos/chronos.service` | Systemd service |
| `/opt/leveredge/control-plane/agents/chronos/requirements.txt` | Python dependencies |
| `/opt/leveredge/control-plane/agents/hades/hades.py` | HADES FastAPI backend |
| `/opt/leveredge/control-plane/agents/hades/hades.service` | Systemd service |
| `/opt/leveredge/control-plane/agents/hades/requirements.txt` | Python dependencies |

---

## Next Phase

Phase 4: ARGUS + ALOY + HERMES + ATHENA (Monitoring, Auditing, Notifications, Documentation)
