# PHASE 2: HEPHAESTUS + AEGIS

*Created: January 15, 2026*
*Prerequisite: Phase 1 complete (Control plane n8n + ATLAS running)*
*Estimated Time: 1-2 hours*

---

## Objective

Build two agents that work together:
- **HEPHAESTUS** (8011): Builder/Deployer - creates workflows, deploys code
- **AEGIS** (8012): Credential Vault - manages secrets, applies credentials

**Key Principle:** HEPHAESTUS requests credentials, AEGIS applies them. HEPHAESTUS never sees raw credential values.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BUILD REQUEST FLOW                               │
│                                                                          │
│  1. Request comes to ATLAS: "Create a workflow that calls OpenAI API"   │
│                              │                                           │
│  2. ATLAS routes to HEPHAESTUS                                          │
│                              │                                           │
│  3. HEPHAESTUS builds workflow with credential placeholder              │
│     └─ Creates nodes, connections, logic                                │
│     └─ Marks: "needs_credential: openai_api"                            │
│                              │                                           │
│  4. HEPHAESTUS asks AEGIS: "Apply OpenAI credential to node X"          │
│                              │                                           │
│  5. AEGIS looks up credential, applies it directly to n8n               │
│     └─ HEPHAESTUS never sees the API key value                          │
│                              │                                           │
│  6. HEPHAESTUS activates workflow                                       │
│                              │                                           │
│  7. Both log to Event Bus                                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## AEGIS: Credential Vault

### Purpose
- Store credential references (not values - those stay in n8n)
- Map credential names to n8n credential IDs
- Apply credentials to workflows on request
- Audit credential usage
- Never expose raw values

### Implementation: FastAPI Backend + n8n Workflow

#### Step 1: Create AEGIS Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/aegis
```

#### Step 2: Create AEGIS FastAPI Backend

Create `/opt/leveredge/control-plane/agents/aegis/aegis.py`:

```python
#!/usr/bin/env python3
"""
AEGIS - Credential Vault Agent
Port: 8012

Manages credential references and applies them to workflows.
Never exposes raw credential values.
"""

import os
import json
import httpx
import sqlite3
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

app = FastAPI(title="AEGIS", description="Credential Vault Agent", version="1.0.0")

# Configuration
N8N_URL = os.getenv("N8N_URL", "https://control.n8n.leveredgeai.com")
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASS = os.getenv("N8N_PASS", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
DB_PATH = "/opt/leveredge/control-plane/agents/aegis/aegis.db"

# Database setup
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS credential_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            n8n_credential_id TEXT,
            credential_type TEXT NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credential_name TEXT NOT NULL,
            workflow_id TEXT,
            workflow_name TEXT,
            requested_by TEXT,
            action TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Models
class CredentialRegister(BaseModel):
    name: str
    n8n_credential_id: str
    credential_type: str
    description: Optional[str] = None

class CredentialApplyRequest(BaseModel):
    credential_name: str
    workflow_id: str
    node_name: str
    requested_by: str = "HEPHAESTUS"

class EventBusPayload(BaseModel):
    source_agent: str = "AEGIS"
    action: str
    target: str = ""
    details: Dict[str, Any] = {}

# Helpers
async def log_to_event_bus(action: str, target: str = "", details: dict = {}):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "AEGIS",
                    "action": action,
                    "target": target,
                    "details": details
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

def log_usage(credential_name: str, workflow_id: str, workflow_name: str, requested_by: str, action: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO usage_log (credential_name, workflow_id, workflow_name, requested_by, action)
        VALUES (?, ?, ?, ?, ?)
    ''', (credential_name, workflow_id, workflow_name, requested_by, action))
    conn.commit()
    conn.close()

# Endpoints
@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "AEGIS", "port": 8012, "timestamp": datetime.utcnow().isoformat()}

@app.get("/credentials")
async def list_credentials():
    """List all registered credentials (no values exposed)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, credential_type, description, created_at, last_used FROM credential_registry')
    rows = c.fetchall()
    conn.close()
    
    credentials = [
        {
            "name": row[0],
            "type": row[1],
            "description": row[2],
            "created_at": row[3],
            "last_used": row[4]
        }
        for row in rows
    ]
    
    await log_to_event_bus("credentials_listed", details={"count": len(credentials)})
    return {"credentials": credentials, "count": len(credentials)}

@app.post("/credentials/register")
async def register_credential(cred: CredentialRegister):
    """Register a credential reference (link name to n8n credential ID)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO credential_registry (name, n8n_credential_id, credential_type, description)
            VALUES (?, ?, ?, ?)
        ''', (cred.name, cred.n8n_credential_id, cred.credential_type, cred.description))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Credential '{cred.name}' already registered")
    conn.close()
    
    await log_to_event_bus("credential_registered", target=cred.name, details={"type": cred.credential_type})
    return {"status": "registered", "name": cred.name, "type": cred.credential_type}

@app.post("/credentials/apply")
async def apply_credential(req: CredentialApplyRequest):
    """Apply a credential to a workflow node (AEGIS applies, requester never sees value)"""
    
    # Look up credential
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT n8n_credential_id, credential_type FROM credential_registry WHERE name = ?', (req.credential_name,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Credential '{req.credential_name}' not registered")
    
    n8n_cred_id, cred_type = row
    
    # Update last_used
    c.execute('UPDATE credential_registry SET last_used = ? WHERE name = ?', 
              (datetime.utcnow().isoformat(), req.credential_name))
    conn.commit()
    conn.close()
    
    # Apply credential to workflow via n8n API
    # This requires updating the workflow's node to reference the credential
    async with httpx.AsyncClient() as client:
        # Get workflow
        resp = await client.get(
            f"{N8N_URL}/api/v1/workflows/{req.workflow_id}",
            auth=(N8N_USER, N8N_PASS),
            timeout=10.0
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to get workflow")
        
        workflow = resp.json()
        
        # Find and update node
        node_found = False
        for node in workflow.get("nodes", []):
            if node.get("name") == req.node_name:
                node_found = True
                # Apply credential reference
                if "credentials" not in node:
                    node["credentials"] = {}
                node["credentials"][cred_type] = {"id": n8n_cred_id, "name": req.credential_name}
                break
        
        if not node_found:
            raise HTTPException(status_code=404, detail=f"Node '{req.node_name}' not found in workflow")
        
        # Update workflow
        update_resp = await client.patch(
            f"{N8N_URL}/api/v1/workflows/{req.workflow_id}",
            auth=(N8N_USER, N8N_PASS),
            json={"nodes": workflow["nodes"]},
            timeout=10.0
        )
        
        if update_resp.status_code != 200:
            raise HTTPException(status_code=update_resp.status_code, detail="Failed to update workflow")
    
    # Log usage
    log_usage(req.credential_name, req.workflow_id, workflow.get("name", "unknown"), req.requested_by, "applied")
    
    await log_to_event_bus(
        "credential_applied",
        target=req.workflow_id,
        details={
            "credential": req.credential_name,
            "node": req.node_name,
            "requested_by": req.requested_by
        }
    )
    
    return {
        "status": "applied",
        "credential": req.credential_name,
        "workflow_id": req.workflow_id,
        "node": req.node_name
    }

@app.get("/credentials/usage")
async def get_usage_log(limit: int = 50):
    """Get credential usage audit log"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT credential_name, workflow_id, workflow_name, requested_by, action, timestamp
        FROM usage_log ORDER BY timestamp DESC LIMIT ?
    ''', (limit,))
    rows = c.fetchall()
    conn.close()
    
    log = [
        {
            "credential": row[0],
            "workflow_id": row[1],
            "workflow_name": row[2],
            "requested_by": row[3],
            "action": row[4],
            "timestamp": row[5]
        }
        for row in rows
    ]
    
    return {"usage_log": log, "count": len(log)}

@app.get("/credentials/sync")
async def sync_from_n8n():
    """Sync credential list from n8n (discovers credentials, does NOT see values)"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{N8N_URL}/api/v1/credentials",
            auth=(N8N_USER, N8N_PASS),
            timeout=10.0
        )
        
        if resp.status_code == 403:
            return {"status": "forbidden", "message": "API key scope doesn't include credentials:read"}
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="Failed to fetch credentials from n8n")
        
        n8n_creds = resp.json().get("data", [])
        
        # Register any new credentials
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        synced = []
        for cred in n8n_creds:
            try:
                c.execute('''
                    INSERT OR IGNORE INTO credential_registry (name, n8n_credential_id, credential_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (cred["name"], cred["id"], cred["type"], f"Synced from n8n"))
                if c.rowcount > 0:
                    synced.append(cred["name"])
            except Exception as e:
                print(f"Failed to sync {cred['name']}: {e}")
        
        conn.commit()
        conn.close()
        
        await log_to_event_bus("credentials_synced", details={"synced": synced, "total": len(n8n_creds)})
        return {"status": "synced", "new_credentials": synced, "total_in_n8n": len(n8n_creds)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
```

#### Step 3: Create AEGIS Service

Create `/opt/leveredge/control-plane/agents/aegis/aegis.service`:

```ini
[Unit]
Description=AEGIS Credential Vault Agent
After=network.target event-bus.service

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/aegis
Environment="N8N_URL=https://control.n8n.leveredgeai.com"
Environment="N8N_USER=admin"
Environment="N8N_PASS=oMtnAe9qsrxhMe/1ROmokg=="
Environment="EVENT_BUS_URL=http://localhost:8099"
ExecStart=/home/damon/.local/bin/uvicorn aegis:app --host 0.0.0.0 --port 8012
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Step 4: Create requirements.txt

Create `/opt/leveredge/control-plane/agents/aegis/requirements.txt`:

```
fastapi
uvicorn
httpx
pydantic
```

---

## HEPHAESTUS: Builder/Deployer

### Purpose
- Create n8n workflows programmatically
- Deploy code and configurations
- Request credentials from AEGIS (never handles values directly)
- Validate builds before activation

### Implementation: n8n AI Agent Workflow

HEPHAESTUS runs as an n8n workflow with AI Agent node + tools.

#### Step 1: Create HEPHAESTUS Workflow

This workflow will be created via n8n-control MCP server.

**Workflow Structure:**
```
Webhook (POST /hephaestus)
    │
    ▼
AI Agent (Claude/GPT)
    │
    ├── Tool: create_workflow (via n8n API)
    ├── Tool: update_workflow
    ├── Tool: request_credential (calls AEGIS)
    ├── Tool: validate_workflow
    ├── Tool: activate_workflow
    └── Tool: log_to_event_bus
    │
    ▼
Respond to Webhook
```

**System Prompt for HEPHAESTUS:**
```
You are HEPHAESTUS, the Builder agent for LeverEdge control plane.

Your responsibilities:
1. Create n8n workflows based on specifications
2. Update and modify existing workflows
3. Request credentials from AEGIS (you never see or handle actual credential values)
4. Validate workflows before activation
5. Log all build activities to the Event Bus

IMPORTANT RULES:
- NEVER hardcode API keys or credentials
- When a workflow needs a credential, call request_credential tool with the credential name
- AEGIS will apply the credential - you just specify which one is needed
- Always validate before activating
- Log every action to Event Bus

Available credential types (ask AEGIS to apply):
- anthropicApi
- openAiApi
- httpBasicAuth
- supabaseApi
- googleOAuth2Api

When building workflows:
1. Create the workflow structure first
2. Add all nodes and connections
3. Request credential application from AEGIS
4. Validate the workflow
5. Activate if validation passes
```

---

## Deployment Commands

```bash
## Step 1: Create AEGIS directory and files
mkdir -p /opt/leveredge/control-plane/agents/aegis

## Step 2: Create aegis.py (content above)
# [Create the file with the Python code above]

## Step 3: Create service file
# [Create aegis.service with content above]

## Step 4: Install requirements
cd /opt/leveredge/control-plane/agents/aegis
pip install -r requirements.txt --break-system-packages

## Step 5: Install and start service
sudo cp aegis.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable aegis
sudo systemctl start aegis

## Step 6: Verify AEGIS
curl http://localhost:8012/health

## Step 7: Create HEPHAESTUS workflow in n8n
# Use n8n-control MCP server to create the workflow
```

---

## Verification Checklist

| Check | Command | Expected |
|-------|---------|----------|
| AEGIS running | `curl localhost:8012/health` | `{"status":"healthy","agent":"AEGIS",...}` |
| AEGIS service | `systemctl status aegis` | Active (running) |
| Event Bus logging | `curl localhost:8099/events` | AEGIS events present |
| HEPHAESTUS workflow | Check control.n8n.leveredgeai.com | Workflow exists and active |
| Integration test | Request ATLAS to build something | Full flow works |

---

## Integration Test

After both agents are deployed, test the full flow:

```bash
# Ask ATLAS to route a build request to HEPHAESTUS
curl -X POST https://control.n8n.leveredgeai.com/webhook/atlas \
  -H "Content-Type: application/json" \
  -d '{
    "type": "build",
    "target": "HEPHAESTUS",
    "request": {
      "action": "create_workflow",
      "name": "test-hello-world",
      "description": "Simple workflow that responds with hello world",
      "nodes": [
        {"type": "webhook", "path": "hello"},
        {"type": "respond", "message": "Hello World!"}
      ]
    }
  }'
```

---

## Files Created

| File | Purpose |
|------|---------|
| `/opt/leveredge/control-plane/agents/aegis/aegis.py` | AEGIS FastAPI backend |
| `/opt/leveredge/control-plane/agents/aegis/aegis.service` | Systemd service |
| `/opt/leveredge/control-plane/agents/aegis/requirements.txt` | Python dependencies |
| `/opt/leveredge/control-plane/agents/aegis/aegis.db` | SQLite credential registry |
| HEPHAESTUS workflow | n8n workflow in control plane |

---

## Pinned for Later

- AEGIS Web UI (visual credential management)
- Credential rotation automation
- Credential expiry monitoring
- HEPHAESTUS templates library

---

## Next Phase

Phase 3: CHRONOS + HADES (Backup Manager + Rollback System)
