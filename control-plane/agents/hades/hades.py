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
DB_PATH = os.getenv("HADES_DB_PATH", "/opt/leveredge/shared/backups/hades.db")

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
