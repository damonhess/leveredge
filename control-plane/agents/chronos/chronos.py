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
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
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
            headers={"X-N8N-API-KEY": N8N_API_KEY},
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
                headers={"X-N8N-API-KEY": N8N_API_KEY},
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
    backup_path = Path(row[5])
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
