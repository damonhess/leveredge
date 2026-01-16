# HEPHAESTUS MCP SERVER

*Created: January 15, 2026*
*Type: Dumb Executor (Option A)*
*Port: 8011*

---

## Overview

HEPHAESTUS MCP is a Model Context Protocol server that exposes execution tools to Claude Desktop and Claude Code. It does NOT contain LLM reasoning - it executes specs literally.

**Philosophy:** Claude Desktop/Code does the thinking, HEPHAESTUS does the doing.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HEPHAESTUS MCP SERVER                        │
│                                                                  │
│  Claude Desktop ─────┐                                          │
│                      ├──→ MCP Protocol ──→ FastAPI (8011)       │
│  Claude Code ────────┘                          │               │
│                                                 │               │
│                                                 ▼               │
│                                    ┌────────────────────────┐   │
│                                    │   Permission Check     │   │
│                                    │   (Tier 0/1/2)         │   │
│                                    └───────────┬────────────┘   │
│                                                │               │
│                    ┌───────────────────────────┼───────────────┐│
│                    │               │           │               ││
│                    ▼               ▼           ▼               ▼│
│              ┌─────────┐    ┌──────────┐ ┌─────────┐    ┌──────┐│
│              │ n8n API │    │ File Ops │ │ Command │    │ Git  ││
│              │ Tools   │    │          │ │ Execute │    │ Ops  ││
│              └─────────┘    └──────────┘ └─────────┘    └──────┘│
│                    │               │           │               ││
│                    └───────────────┼───────────────────────────┘│
│                                    ▼                            │
│                            ┌─────────────┐                      │
│                            │  Event Bus  │                      │
│                            │   (8099)    │                      │
│                            └─────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## MCP Tools Exposed

### Workflow Operations

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_workflow` | Create n8n workflow | `workflow_json`, `target` (control/prod/dev) |
| `update_workflow` | Update existing workflow | `workflow_id`, `updates`, `target` |
| `delete_workflow` | Delete workflow | `workflow_id`, `target` |
| `activate_workflow` | Activate workflow | `workflow_id`, `target` |
| `deactivate_workflow` | Deactivate workflow | `workflow_id`, `target` |
| `list_workflows` | List all workflows | `target` |
| `get_workflow` | Get workflow details | `workflow_id`, `target` |

### File Operations

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_file` | Create file | `path`, `content` |
| `read_file` | Read file contents | `path` |
| `update_file` | Update file | `path`, `content` |
| `delete_file` | Delete file | `path` |
| `list_directory` | List directory contents | `path` |

### Command Execution

| Tool | Description | Parameters |
|------|-------------|------------|
| `run_command` | Execute shell command | `command`, `working_dir` |
| `run_script` | Execute script file | `script_path`, `args` |

### Git Operations

| Tool | Description | Parameters |
|------|-------------|------------|
| `git_status` | Get git status | `repo_path` |
| `git_add` | Stage files | `repo_path`, `files` |
| `git_commit` | Commit changes | `repo_path`, `message` |
| `git_pull` | Pull from remote | `repo_path` |
| `git_push` | Push to remote | `repo_path` |

### Agent Operations

| Tool | Description | Parameters |
|------|-------------|------------|
| `call_agent` | Call another agent webhook | `agent`, `action`, `payload` |
| `get_agent_health` | Check agent health | `agent` |
| `list_agents` | List all agents and status | - |

---

## Permission Tiers

```python
TIER_0_FORBIDDEN = [
    # Patterns that are NEVER allowed
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"DROP\s+DATABASE",
    r"DELETE\s+FROM\s+(?!leveredge)",  # Only leveredge tables allowed
    r"/etc/",
    r"/root/",
    r"systemctl\s+(?!status)",  # Only status allowed without approval
    r"chmod\s+777",
    r"curl.*\|.*sh",  # No pipe to shell
]

TIER_1_ALLOWED_PATHS = [
    "/opt/leveredge/",
    "/home/damon/shared/",
    "/tmp/leveredge/",
]

TIER_1_ALLOWED_COMMANDS = [
    r"^ls\s",
    r"^cat\s",
    r"^grep\s",
    r"^find\s",
    r"^head\s",
    r"^tail\s",
    r"^wc\s",
    r"^curl\s+http://localhost",
    r"^docker\s+ps",
    r"^docker\s+logs",
    r"^docker\s+exec.*curl",
    r"^git\s",
    r"^pip\s+install.*--break-system-packages",
    r"^python3?\s",
    r"^mkdir\s+-p\s+/opt/leveredge/",
    r"^cp\s+.*\s+/opt/leveredge/",
    r"^mv\s+.*\s+/opt/leveredge/",
]

TIER_2_REQUIRES_APPROVAL = [
    r"^sudo\s",
    r"^systemctl\s+(?!status)",
    r"^docker\s+(?!ps|logs)",
    r"^rm\s",
    r"DELETE\s+FROM",
]
```

---

## Implementation

### Directory Structure

```
/opt/leveredge/control-plane/agents/hephaestus/
├── hephaestus_mcp.py      # MCP server implementation
├── permissions.py          # Permission checking logic
├── tools/
│   ├── workflow_tools.py   # n8n API operations
│   ├── file_tools.py       # File system operations
│   ├── command_tools.py    # Shell execution
│   ├── git_tools.py        # Git operations
│   └── agent_tools.py      # Inter-agent communication
├── requirements.txt
├── Dockerfile
└── hephaestus-mcp.service
```

### Main Server Code

```python
#!/usr/bin/env python3
"""
HEPHAESTUS MCP Server
Port: 8011

Dumb executor - no LLM reasoning.
Claude Desktop/Code provides exact specs, HEPHAESTUS executes.
"""

import os
import re
import json
import httpx
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# MCP Protocol imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = FastAPI(title="HEPHAESTUS", description="Builder MCP Server", version="1.0.0")
mcp_server = Server("hephaestus")

# Configuration
N8N_URLS = {
    "control": os.getenv("N8N_CONTROL_URL", "https://control.n8n.leveredgeai.com"),
    "prod": os.getenv("N8N_PROD_URL", "https://n8n.leveredgeai.com"),
    "dev": os.getenv("N8N_DEV_URL", "https://dev.n8n.leveredgeai.com"),
}
N8N_USER = os.getenv("N8N_USER", "admin")
N8N_PASS = os.getenv("N8N_PASS", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")

# Permission patterns
TIER_0_FORBIDDEN = [
    r"rm\s+-rf\s+/",
    r"DROP\s+DATABASE",
    r"/etc/",
    r"/root/",
    r"chmod\s+777",
]

TIER_1_ALLOWED_PATHS = [
    "/opt/leveredge/",
    "/home/damon/shared/",
    "/tmp/leveredge/",
]

# Models
class WorkflowCreate(BaseModel):
    workflow_json: dict
    target: str = "control"

class FileCreate(BaseModel):
    path: str
    content: str

class CommandRun(BaseModel):
    command: str
    working_dir: str = "/opt/leveredge"

class AgentCall(BaseModel):
    agent: str
    action: str
    payload: dict = {}

# Helpers
async def log_event(action: str, target: str = "", details: dict = {}, status: str = "success"):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "HEPHAESTUS",
                    "action": action,
                    "target": target,
                    "details": {**details, "status": status}
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus log failed: {e}")

def check_path_allowed(path: str) -> bool:
    """Check if path is within allowed directories"""
    path = os.path.abspath(path)
    return any(path.startswith(allowed) for allowed in TIER_1_ALLOWED_PATHS)

def check_command_allowed(command: str) -> tuple[bool, str]:
    """Check command against permission tiers. Returns (allowed, reason)"""
    # Check TIER 0 - Forbidden
    for pattern in TIER_0_FORBIDDEN:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"FORBIDDEN: Matches blocked pattern"
    
    # Check TIER 1 - Allowed
    for pattern in TIER_1_ALLOWED_COMMANDS:
        if re.match(pattern, command):
            return True, "TIER_1: Pre-approved"
    
    # Check TIER 2 - Requires approval
    for pattern in TIER_2_REQUIRES_APPROVAL:
        if re.search(pattern, command, re.IGNORECASE):
            return False, "TIER_2: Requires human approval"
    
    # Default: not in whitelist
    return False, "NOT_WHITELISTED: Command not in approved list"

# ============ WORKFLOW TOOLS ============

@app.post("/tools/workflow/create")
async def create_workflow(req: WorkflowCreate):
    """Create a new n8n workflow"""
    n8n_url = N8N_URLS.get(req.target, N8N_URLS["control"])
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{n8n_url}/api/v1/workflows",
            auth=(N8N_USER, N8N_PASS),
            json=req.workflow_json,
            timeout=30.0
        )
        
        if resp.status_code not in [200, 201]:
            await log_event("workflow_create_failed", req.target, {"error": resp.text}, "failed")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        result = resp.json()
        await log_event("workflow_created", req.target, {"workflow_id": result.get("id"), "name": result.get("name")})
        return result

@app.get("/tools/workflow/list")
async def list_workflows(target: str = "control"):
    """List all workflows in target instance"""
    n8n_url = N8N_URLS.get(target, N8N_URLS["control"])
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{n8n_url}/api/v1/workflows",
            auth=(N8N_USER, N8N_PASS),
            timeout=30.0
        )
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        return resp.json()

@app.patch("/tools/workflow/{workflow_id}/activate")
async def activate_workflow(workflow_id: str, target: str = "control"):
    """Activate a workflow"""
    n8n_url = N8N_URLS.get(target, N8N_URLS["control"])
    
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            auth=(N8N_USER, N8N_PASS),
            json={"active": True},
            timeout=10.0
        )
        
        if resp.status_code != 200:
            await log_event("workflow_activate_failed", workflow_id, {"error": resp.text}, "failed")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        await log_event("workflow_activated", workflow_id, {"target": target})
        return resp.json()

# ============ FILE TOOLS ============

@app.post("/tools/file/create")
async def create_file(req: FileCreate):
    """Create a file at specified path"""
    if not check_path_allowed(req.path):
        await log_event("file_create_blocked", req.path, {"reason": "Path not allowed"}, "blocked")
        raise HTTPException(status_code=403, detail=f"Path not allowed: {req.path}")
    
    try:
        path = Path(req.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(req.content)
        
        await log_event("file_created", req.path, {"size": len(req.content)})
        return {"status": "created", "path": req.path, "size": len(req.content)}
    except Exception as e:
        await log_event("file_create_failed", req.path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/file/read")
async def read_file(path: str):
    """Read a file"""
    if not check_path_allowed(path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {path}")
    
    try:
        content = Path(path).read_text()
        return {"path": path, "content": content, "size": len(content)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/file/list")
async def list_directory(path: str):
    """List directory contents"""
    if not check_path_allowed(path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {path}")
    
    try:
        p = Path(path)
        if not p.is_dir():
            raise HTTPException(status_code=400, detail=f"Not a directory: {path}")
        
        entries = []
        for entry in p.iterdir():
            entries.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size": entry.stat().st_size if entry.is_file() else None
            })
        
        return {"path": path, "entries": entries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============ COMMAND TOOLS ============

@app.post("/tools/command/run")
async def run_command(req: CommandRun):
    """Execute a shell command"""
    allowed, reason = check_command_allowed(req.command)
    
    if not allowed:
        await log_event("command_blocked", req.command, {"reason": reason}, "blocked")
        
        if "TIER_2" in reason:
            # Queue for approval (future: send to HERMES)
            return {
                "status": "pending_approval",
                "command": req.command,
                "reason": reason,
                "message": "Command requires human approval. Implement HERMES integration."
            }
        
        raise HTTPException(status_code=403, detail=reason)
    
    try:
        result = subprocess.run(
            req.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=req.working_dir
        )
        
        await log_event("command_executed", req.command, {
            "exit_code": result.returncode,
            "working_dir": req.working_dir
        })
        
        return {
            "status": "completed",
            "command": req.command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        await log_event("command_timeout", req.command, {"timeout": 60}, "failed")
        raise HTTPException(status_code=408, detail="Command timed out after 60 seconds")
    except Exception as e:
        await log_event("command_failed", req.command, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))

# ============ GIT TOOLS ============

@app.post("/tools/git/commit")
async def git_commit(repo_path: str, message: str, files: List[str] = None):
    """Commit changes to git repo"""
    if not check_path_allowed(repo_path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {repo_path}")
    
    try:
        # Add files
        add_cmd = f"git add {' '.join(files) if files else '.'}"
        subprocess.run(add_cmd, shell=True, cwd=repo_path, check=True)
        
        # Commit
        commit_cmd = f'git commit -m "{message}"'
        result = subprocess.run(commit_cmd, shell=True, cwd=repo_path, capture_output=True, text=True)
        
        await log_event("git_commit", repo_path, {"message": message})
        
        return {
            "status": "committed",
            "repo": repo_path,
            "message": message,
            "output": result.stdout
        }
    except Exception as e:
        await log_event("git_commit_failed", repo_path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))

# ============ AGENT TOOLS ============

@app.post("/tools/agent/call")
async def call_agent(req: AgentCall):
    """Call another agent's webhook"""
    agent_urls = {
        "atlas": "https://control.n8n.leveredgeai.com/webhook/atlas",
        "aegis": "https://control.n8n.leveredgeai.com/webhook/aegis",
        "chronos": "https://control.n8n.leveredgeai.com/webhook/chronos",
        "hades": "https://control.n8n.leveredgeai.com/webhook/hades",
    }
    
    url = agent_urls.get(req.agent.lower())
    if not url:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {req.agent}")
    
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"action": req.action, **req.payload},
            timeout=90.0  # AI agents can be slow
        )
        
        await log_event("agent_called", req.agent, {"action": req.action})
        return resp.json()

@app.get("/tools/agent/health/{agent}")
async def get_agent_health(agent: str):
    """Check an agent's health"""
    ports = {
        "event-bus": 8099,
        "atlas": None,  # Workflow, no port
        "hades": 8008,
        "argus": 8009,
        "chronos": 8010,
        "hephaestus": 8011,
        "aegis": 8012,
    }
    
    port = ports.get(agent.lower())
    if port is None:
        return {"agent": agent, "status": "workflow-only", "message": "Agent runs as n8n workflow"}
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:{port}/health", timeout=5.0)
            return resp.json()
    except Exception as e:
        return {"agent": agent, "status": "unreachable", "error": str(e)}

# ============ HEALTH ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "HEPHAESTUS",
        "port": 8011,
        "mode": "dumb_executor",
        "timestamp": datetime.utcnow().isoformat()
    }

# ============ MCP PROTOCOL ============

@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(name="create_workflow", description="Create n8n workflow", inputSchema={
            "type": "object",
            "properties": {
                "workflow_json": {"type": "object"},
                "target": {"type": "string", "enum": ["control", "prod", "dev"]}
            },
            "required": ["workflow_json"]
        }),
        Tool(name="create_file", description="Create file at path", inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }),
        Tool(name="run_command", description="Execute shell command", inputSchema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "working_dir": {"type": "string"}
            },
            "required": ["command"]
        }),
        Tool(name="call_agent", description="Call another agent", inputSchema={
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "action": {"type": "string"},
                "payload": {"type": "object"}
            },
            "required": ["agent", "action"]
        }),
        Tool(name="git_commit", description="Commit to git repo", inputSchema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string"},
                "message": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["repo_path", "message"]
        }),
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle MCP tool calls by routing to FastAPI endpoints"""
    # Route to appropriate handler
    # This is the bridge between MCP protocol and our FastAPI handlers
    pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
```

---

## Deployment

### Step 1: Create Files

```bash
mkdir -p /opt/leveredge/control-plane/agents/hephaestus
# Create hephaestus_mcp.py with content above
```

### Step 2: Requirements

```
fastapi
uvicorn
httpx
pydantic
mcp
```

### Step 3: Service File

```ini
[Unit]
Description=HEPHAESTUS MCP Builder Agent
After=network.target event-bus.service

[Service]
Type=simple
User=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/hephaestus
Environment="N8N_CONTROL_URL=https://control.n8n.leveredgeai.com"
Environment="N8N_PROD_URL=https://n8n.leveredgeai.com"
Environment="N8N_USER=admin"
Environment="N8N_PASS=oMtnAe9qsrxhMe/1ROmokg=="
Environment="EVENT_BUS_URL=http://localhost:8099"
ExecStart=/home/damon/.local/bin/uvicorn hephaestus_mcp:app --host 0.0.0.0 --port 8011
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 4: MCP Client Configuration

Add to Claude Desktop's MCP config (`~/.config/claude-desktop/mcp.json` or similar):

```json
{
  "mcpServers": {
    "hephaestus": {
      "command": "curl",
      "args": ["-X", "POST", "https://control.n8n.leveredgeai.com/webhook/hephaestus-mcp"],
      "env": {}
    }
  }
}
```

**OR** for direct HTTP MCP (if supported):

```json
{
  "mcpServers": {
    "hephaestus": {
      "url": "https://hephaestus.leveredgeai.com",
      "transport": "http"
    }
  }
}
```

---

## Verification

```bash
# Health check
curl http://localhost:8011/health

# List workflows
curl http://localhost:8011/tools/workflow/list?target=control

# Create test file
curl -X POST http://localhost:8011/tools/file/create \
  -H "Content-Type: application/json" \
  -d '{"path": "/opt/leveredge/test.txt", "content": "Hello from HEPHAESTUS"}'

# Run allowed command
curl -X POST http://localhost:8011/tools/command/run \
  -H "Content-Type: application/json" \
  -d '{"command": "ls -la /opt/leveredge/"}'

# Try forbidden command (should fail)
curl -X POST http://localhost:8011/tools/command/run \
  -H "Content-Type: application/json" \
  -d '{"command": "rm -rf /"}'
```

---

## Next Steps After Deployment

1. Expose via Cloudflare Tunnel (so Claude Desktop on laptop can reach it)
2. Add to Claude Desktop MCP config
3. Add to Claude Code MCP config  
4. Test round-trip: Claude Desktop → HEPHAESTUS → Server → Result
