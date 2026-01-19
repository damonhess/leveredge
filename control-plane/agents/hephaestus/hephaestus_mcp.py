#!/usr/bin/env python3
"""
HEPHAESTUS MCP Server
Port: 8011

Dumb executor - no LLM reasoning.
Claude Desktop/Code provides exact specs, HEPHAESTUS executes.
"""

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List

import httpx
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

app = FastAPI(title="HEPHAESTUS", description="Builder MCP Server with Orchestration", version="1.1.0")

# Configuration
N8N_URLS = {
    "control": os.getenv("N8N_CONTROL_URL", "https://control.n8n.leveredgeai.com"),
    "prod": os.getenv("N8N_PROD_URL", "https://n8n.leveredgeai.com"),
    "dev": os.getenv("N8N_DEV_URL", "https://dev.n8n.leveredgeai.com"),
}
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
ATLAS_URL = os.getenv("ATLAS_URL", "http://atlas:8007")

# Permission patterns
TIER_0_FORBIDDEN = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"DROP\s+DATABASE",
    r"DELETE\s+FROM\s+(?!leveredge)",
    r"/etc/",
    r"/root/",
    r"systemctl\s+(?!status)",
    r"chmod\s+777",
    r"curl.*\|.*sh",
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


# Models
class WorkflowCreate(BaseModel):
    workflow_json: dict
    target: str = "control"


class WorkflowUpdate(BaseModel):
    updates: dict
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


class ParallelOrchestration(BaseModel):
    """Request for parallel orchestration via ATLAS."""
    tasks: List[dict]  # List of {"chain": "...", "input": {...}}
    concurrency: int = 5
    callback_url: Optional[str] = None


class GitCommit(BaseModel):
    repo_path: str
    message: str
    files: Optional[List[str]] = None


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


def check_command_allowed(command: str) -> tuple:
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
            headers={"X-N8N-API-KEY": N8N_API_KEY},
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
async def list_workflows(target: str = Query("control")):
    """List all workflows in target instance"""
    n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{n8n_url}/api/v1/workflows",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=30.0
        )

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        return resp.json()


@app.get("/tools/workflow/{workflow_id}")
async def get_workflow(workflow_id: str, target: str = Query("control")):
    """Get workflow details"""
    n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=30.0
        )

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        return resp.json()


@app.patch("/tools/workflow/{workflow_id}")
async def update_workflow(workflow_id: str, req: WorkflowUpdate):
    """Update an existing workflow"""
    n8n_url = N8N_URLS.get(req.target, N8N_URLS["control"])

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            json=req.updates,
            timeout=30.0
        )

        if resp.status_code != 200:
            await log_event("workflow_update_failed", workflow_id, {"error": resp.text}, "failed")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        result = resp.json()
        await log_event("workflow_updated", workflow_id, {"target": req.target})
        return result


@app.delete("/tools/workflow/{workflow_id}")
async def delete_workflow(workflow_id: str, target: str = Query("control")):
    """Delete a workflow"""
    n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            timeout=30.0
        )

        if resp.status_code not in [200, 204]:
            await log_event("workflow_delete_failed", workflow_id, {"error": resp.text}, "failed")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        await log_event("workflow_deleted", workflow_id, {"target": target})
        return {"status": "deleted", "workflow_id": workflow_id}


@app.patch("/tools/workflow/{workflow_id}/activate")
async def activate_workflow(workflow_id: str, target: str = Query("control")):
    """Activate a workflow"""
    n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            json={"active": True},
            timeout=10.0
        )

        if resp.status_code != 200:
            await log_event("workflow_activate_failed", workflow_id, {"error": resp.text}, "failed")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        await log_event("workflow_activated", workflow_id, {"target": target})
        return resp.json()


@app.patch("/tools/workflow/{workflow_id}/deactivate")
async def deactivate_workflow(workflow_id: str, target: str = Query("control")):
    """Deactivate a workflow"""
    n8n_url = N8N_URLS.get(target, N8N_URLS["control"])

    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{n8n_url}/api/v1/workflows/{workflow_id}",
            headers={"X-N8N-API-KEY": N8N_API_KEY},
            json={"active": False},
            timeout=10.0
        )

        if resp.status_code != 200:
            await log_event("workflow_deactivate_failed", workflow_id, {"error": resp.text}, "failed")
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        await log_event("workflow_deactivated", workflow_id, {"target": target})
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
async def read_file(path: str = Query(...)):
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


@app.put("/tools/file/update")
async def update_file(req: FileCreate):
    """Update a file"""
    if not check_path_allowed(req.path):
        await log_event("file_update_blocked", req.path, {"reason": "Path not allowed"}, "blocked")
        raise HTTPException(status_code=403, detail=f"Path not allowed: {req.path}")

    try:
        path = Path(req.path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {req.path}")

        path.write_text(req.content)

        await log_event("file_updated", req.path, {"size": len(req.content)})
        return {"status": "updated", "path": req.path, "size": len(req.content)}
    except HTTPException:
        raise
    except Exception as e:
        await log_event("file_update_failed", req.path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/tools/file/delete")
async def delete_file(path: str = Query(...)):
    """Delete a file"""
    if not check_path_allowed(path):
        await log_event("file_delete_blocked", path, {"reason": "Path not allowed"}, "blocked")
        raise HTTPException(status_code=403, detail=f"Path not allowed: {path}")

    try:
        p = Path(path)
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {path}")

        p.unlink()

        await log_event("file_deleted", path)
        return {"status": "deleted", "path": path}
    except HTTPException:
        raise
    except Exception as e:
        await log_event("file_delete_failed", path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tools/file/list")
async def list_directory(path: str = Query(...)):
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
    except HTTPException:
        raise
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


@app.post("/tools/command/script")
async def run_script(script_path: str, args: List[str] = []):
    """Execute a script file"""
    if not check_path_allowed(script_path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {script_path}")

    try:
        cmd = [script_path] + args
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        await log_event("script_executed", script_path, {
            "exit_code": result.returncode,
            "args": args
        })

        return {
            "status": "completed",
            "script": script_path,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        await log_event("script_timeout", script_path, {"timeout": 300}, "failed")
        raise HTTPException(status_code=408, detail="Script timed out after 300 seconds")
    except Exception as e:
        await log_event("script_failed", script_path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))


# ============ GIT TOOLS ============

@app.get("/tools/git/status")
async def git_status(repo_path: str = Query(...)):
    """Get git status"""
    if not check_path_allowed(repo_path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {repo_path}")

    try:
        result = subprocess.run(
            "git status --porcelain",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return {
            "repo": repo_path,
            "status": result.stdout,
            "clean": len(result.stdout.strip()) == 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/git/add")
async def git_add(repo_path: str, files: List[str] = []):
    """Stage files"""
    if not check_path_allowed(repo_path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {repo_path}")

    try:
        add_target = " ".join(files) if files else "."
        result = subprocess.run(
            f"git add {add_target}",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        await log_event("git_add", repo_path, {"files": files or ["."]})
        return {
            "status": "staged",
            "repo": repo_path,
            "files": files or ["."],
            "output": result.stdout
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/git/commit")
async def git_commit(req: GitCommit):
    """Commit changes to git repo"""
    if not check_path_allowed(req.repo_path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {req.repo_path}")

    try:
        # Add files
        add_target = " ".join(req.files) if req.files else "."
        subprocess.run(f"git add {add_target}", shell=True, cwd=req.repo_path, check=True)

        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", req.message],
            cwd=req.repo_path,
            capture_output=True,
            text=True
        )

        await log_event("git_commit", req.repo_path, {"message": req.message})

        return {
            "status": "committed",
            "repo": req.repo_path,
            "message": req.message,
            "output": result.stdout
        }
    except subprocess.CalledProcessError as e:
        await log_event("git_commit_failed", req.repo_path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=f"Git error: {e.stderr if hasattr(e, 'stderr') else str(e)}")
    except Exception as e:
        await log_event("git_commit_failed", req.repo_path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/git/pull")
async def git_pull(repo_path: str):
    """Pull from remote"""
    if not check_path_allowed(repo_path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {repo_path}")

    try:
        result = subprocess.run(
            "git pull",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        await log_event("git_pull", repo_path)
        return {
            "status": "pulled",
            "repo": repo_path,
            "output": result.stdout
        }
    except Exception as e:
        await log_event("git_pull_failed", repo_path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/git/push")
async def git_push(repo_path: str):
    """Push to remote"""
    if not check_path_allowed(repo_path):
        raise HTTPException(status_code=403, detail=f"Path not allowed: {repo_path}")

    try:
        result = subprocess.run(
            "git push",
            shell=True,
            cwd=repo_path,
            capture_output=True,
            text=True
        )

        await log_event("git_push", repo_path)
        return {
            "status": "pushed",
            "repo": repo_path,
            "output": result.stdout
        }
    except Exception as e:
        await log_event("git_push_failed", repo_path, {"error": str(e)}, "failed")
        raise HTTPException(status_code=500, detail=str(e))


# ============ AGENT TOOLS ============

@app.post("/tools/agent/call")
async def call_agent(req: AgentCall):
    """Call another agent's webhook or HTTP endpoint"""
    # Webhook-based agents (n8n workflows)
    webhook_agents = {
        "atlas": "https://control.n8n.leveredgeai.com/webhook/atlas",
        "aegis": "https://control.n8n.leveredgeai.com/webhook/aegis",
        "chronos": "https://control.n8n.leveredgeai.com/webhook/chronos",
        "hades": "https://control.n8n.leveredgeai.com/webhook/hades",
    }

    # HTTP-based agents (Python FastAPI services)
    http_agents = {
        "scholar": {"base_url": "http://scholar:8018", "port": 8018},
        "chiron": {"base_url": "http://chiron:8017", "port": 8017},
    }

    agent_lower = req.agent.lower()

    # Check if it's an HTTP-based agent (SCHOLAR, CHIRON)
    if agent_lower in http_agents:
        agent_config = http_agents[agent_lower]
        # Map action to endpoint - HTTP agents use REST endpoints
        # Actions map to endpoints: deep-research -> /deep-research, sprint-plan -> /sprint-plan
        endpoint = f"/{req.action.replace('_', '-')}"
        url = f"{agent_config['base_url']}{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(
                    url,
                    json=req.payload,
                    timeout=120.0  # Longer timeout for LLM-powered agents
                )
                await log_event("agent_called", req.agent, {"action": req.action, "type": "http"})
                return resp.json()
            except httpx.TimeoutException:
                await log_event("agent_timeout", req.agent, {"action": req.action}, "failed")
                raise HTTPException(status_code=504, detail=f"Agent {req.agent} timed out")
            except Exception as e:
                await log_event("agent_error", req.agent, {"action": req.action, "error": str(e)}, "failed")
                raise HTTPException(status_code=502, detail=f"Agent {req.agent} error: {str(e)}")

    # Check if it's a webhook-based agent
    url = webhook_agents.get(agent_lower)
    if not url:
        available_agents = list(webhook_agents.keys()) + list(http_agents.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Unknown agent: {req.agent}. Available: {', '.join(available_agents)}"
        )

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json={"action": req.action, **req.payload},
            timeout=90.0
        )

        await log_event("agent_called", req.agent, {"action": req.action, "type": "webhook"})
        return resp.json()


@app.get("/tools/agent/health/{agent}")
async def get_agent_health(agent: str):
    """Check an agent's health"""
    ports = {
        "event-bus": 8099,
        "atlas": None,
        "hades": 8008,
        "argus": 8009,
        "chronos": 8010,
        "hephaestus": 8011,
        "aegis": 8012,
        "chiron": 8017,
        "scholar": 8018,
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


@app.get("/tools/agent/list")
async def list_agents():
    """List all agents and their status"""
    agents = {
        "event-bus": 8099,
        "hades": 8008,
        "argus": 8009,
        "chronos": 8010,
        "hephaestus": 8011,
        "aegis": 8012,
        "chiron": 8017,
        "scholar": 8018,
    }

    results = []
    async with httpx.AsyncClient() as client:
        for agent, port in agents.items():
            try:
                resp = await client.get(f"http://localhost:{port}/health", timeout=2.0)
                results.append({"agent": agent, "port": port, "status": "healthy"})
            except Exception:
                results.append({"agent": agent, "port": port, "status": "unreachable"})

    # Add workflow-only agents
    results.append({"agent": "atlas", "port": None, "status": "workflow-only"})
    results.append({"agent": "gaia", "port": None, "status": "workflow-only"})

    return {"agents": results}


# ============ ORCHESTRATION TOOLS ============

@app.post("/tools/orchestrate/parallel")
async def orchestrate_parallel(req: ParallelOrchestration):
    """
    Execute multiple chains in parallel via ATLAS.

    This is a convenience wrapper around ATLAS /execute-parallel.
    Returns immediately with batch_id for tracking.

    Example:
    ```json
    {
        "tasks": [
            {"chain": "research-and-plan", "input": {"topic": "AI agents"}},
            {"chain": "research-and-plan", "input": {"topic": "MCP servers"}}
        ],
        "concurrency": 5
    }
    ```
    """
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{ATLAS_URL}/execute-parallel",
                json={
                    "tasks": req.tasks,
                    "concurrency": req.concurrency,
                    "callback_url": req.callback_url,
                    "source": "hephaestus"
                },
                timeout=30.0
            )
            resp.raise_for_status()
            result = resp.json()
            await log_event("orchestrate_parallel", "atlas", {"batch_id": result.get("batch_id"), "tasks": len(req.tasks)})
            return result
        except httpx.TimeoutException:
            await log_event("orchestrate_parallel_timeout", "atlas", {}, "failed")
            raise HTTPException(status_code=504, detail="ATLAS timeout")
        except Exception as e:
            await log_event("orchestrate_parallel_error", "atlas", {"error": str(e)}, "failed")
            raise HTTPException(status_code=502, detail=f"ATLAS error: {str(e)}")


@app.get("/tools/orchestrate/batch/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get status of a parallel batch execution from ATLAS."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{ATLAS_URL}/batch/{batch_id}/status",
                timeout=10.0
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"ATLAS error: {str(e)}")


@app.get("/tools/orchestrate/batch/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Get full results of a parallel batch execution from ATLAS."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{ATLAS_URL}/batch/{batch_id}/results",
                timeout=30.0
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"ATLAS error: {str(e)}")


# ============ LCIS INTEGRATION ============

LCIS_LIBRARIAN_URL = os.getenv("LCIS_LIBRARIAN_URL", "http://localhost:8050")
LCIS_ORACLE_URL = os.getenv("LCIS_ORACLE_URL", "http://localhost:8052")


class LCISConsultRequest(BaseModel):
    """Request for LCIS Oracle consultation"""
    action: str
    domain: Optional[str] = None
    context: Optional[str] = None


class LCISReportRequest(BaseModel):
    """Request for reporting a lesson to LCIS"""
    content: str
    type: str  # failure, success, warning, insight, anti_pattern
    domain: str
    title: Optional[str] = None
    context: Optional[str] = None
    outcome: Optional[str] = None
    solution: Optional[str] = None
    severity: str = "medium"  # critical, high, medium, low
    tags: List[str] = []


@app.post("/tools/lcis/consult")
async def lcis_consult(req: LCISConsultRequest):
    """
    REQUIRED before significant actions.

    Consult LCIS Oracle for:
    - Blocking rules
    - Relevant warnings (past failures)
    - Recommendations (success patterns)
    - Playbooks (step-by-step guides)

    Example:
        result = await lcis_consult({
            "action": "Update ARIA system prompt",
            "domain": "ARIA_SANCTUM",
            "context": "User wants personality change"
        })
        if result["blocked"]:
            return f"BLOCKED: {result['blocked_by']['reason']}"
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LCIS_ORACLE_URL}/consult",
                json={
                    "action": req.action,
                    "domain": req.domain,
                    "agent": "CLAUDE_CODE",
                    "context": req.context
                },
                timeout=10.0
            )
            result = response.json()
            await log_event("lcis_consult", req.action[:50], {"blocked": result.get("blocked", False)})
            return result
    except Exception as e:
        await log_event("lcis_consult_error", req.action[:50], {"error": str(e)}, "failed")
        return {"error": str(e), "proceed": True, "warnings": ["LCIS unavailable"]}


@app.post("/tools/lcis/report")
async def lcis_report(req: LCISReportRequest):
    """
    Report a lesson learned to LCIS.

    Types: failure, success, warning, insight, anti_pattern
    Severity: critical, high, medium, low

    Example (failure):
        await lcis_report({
            "content": "Docker restart doesn't reload baked files",
            "type": "failure",
            "domain": "THE_KEEP",
            "title": "Prompt not updating after restart",
            "context": "Tried to update ARIA prompt",
            "outcome": "Prompt unchanged",
            "solution": "Rebuild Docker image instead",
            "severity": "high",
            "tags": ["docker", "aria", "prompt"]
        })

    Example (success):
        await lcis_report({
            "content": "Volume mount allows hot-reload of config files",
            "type": "success",
            "domain": "THE_KEEP",
            "title": "Hot-reload config pattern",
            "solution": "Mount config as volume instead of baking",
            "tags": ["docker", "config", "pattern"]
        })
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{LCIS_LIBRARIAN_URL}/ingest",
                json={
                    "content": req.content,
                    "type": req.type,
                    "domain": req.domain,
                    "title": req.title,
                    "context": req.context,
                    "outcome": req.outcome,
                    "solution": req.solution,
                    "severity": req.severity,
                    "tags": req.tags,
                    "source_agent": "CLAUDE_CODE",
                    "source_type": "claude_code"
                },
                timeout=10.0
            )
            result = response.json()
            await log_event("lcis_report", req.type, {"domain": req.domain, "id": result.get("id")})
            return result
    except Exception as e:
        await log_event("lcis_report_error", req.type, {"error": str(e)}, "failed")
        return {"error": str(e), "status": "failed"}


@app.get("/tools/lcis/rules")
async def lcis_rules():
    """Get all active LCIS rules that will block or warn."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LCIS_ORACLE_URL}/rules",
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e), "rules": []}


@app.get("/tools/lcis/context")
async def lcis_context():
    """
    Get full LCIS context for current session.

    Returns:
    - critical_failures: Things to avoid
    - active_rules: Enforced constraints
    - recent_successes: Patterns to follow
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LCIS_ORACLE_URL}/context/claude-code",
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/tools/lcis/dashboard")
async def lcis_dashboard():
    """Get LCIS dashboard metrics."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{LCIS_LIBRARIAN_URL}/dashboard",
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e)}


# ============ MAGNUS PM TOOLS ============

MAGNUS_URL = os.getenv("MAGNUS_URL", "http://localhost:8019")


@app.get("/tools/magnus/status")
async def magnus_status():
    """
    Get MAGNUS's assessment of the board.

    Returns current project status, overdue tasks, blockers, and days to launch.
    MAGNUS speaks like a chess grandmaster - calculating, patient, precise.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MAGNUS_URL}/status", timeout=10.0)
            return response.json()
    except Exception as e:
        return {"error": str(e), "magnus_says": "Cannot assess the board - connection failed"}


@app.get("/tools/magnus/projects")
async def magnus_projects(status: Optional[str] = None):
    """
    List all projects with summaries.

    Optional filter by status: planning, active, on_hold, completed, cancelled
    """
    try:
        params = {"status": status} if status else {}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MAGNUS_URL}/projects", params=params, timeout=10.0)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


class MagnusProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_end: Optional[str] = None
    client_name: Optional[str] = None
    template: Optional[str] = None
    priority: int = 50


@app.post("/tools/magnus/projects")
async def magnus_create_project(project: MagnusProjectCreate):
    """
    Create a new project.

    Args:
        name: Project name
        description: Project description
        target_end: Target end date (YYYY-MM-DD)
        client_name: Client name (if external project)
        template: Template to use (automation_project, agent_development)
        priority: 1-100, higher = more important
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MAGNUS_URL}/projects",
                json=project.model_dump(exclude_none=True),
                timeout=10.0
            )
            await log_event("magnus_project_created", project.name, {})
            return response.json()
    except Exception as e:
        return {"error": str(e)}


class MagnusTaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    assigned_agent: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"
    estimated_hours: Optional[float] = None


@app.post("/tools/magnus/tasks")
async def magnus_create_task(task: MagnusTaskCreate):
    """
    Create a new task.

    Args:
        project_id: UUID of the project
        title: Task title
        description: Task description
        assigned_agent: Agent to assign (CHRONOS, HERMES, etc.)
        due_date: Due date (YYYY-MM-DD)
        priority: critical, high, medium, low
        estimated_hours: Estimated hours to complete
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MAGNUS_URL}/tasks",
                json=task.model_dump(exclude_none=True),
                timeout=10.0
            )
            await log_event("magnus_task_created", task.title[:50], {"project_id": task.project_id})
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/tools/magnus/tasks")
async def magnus_list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    overdue: bool = False
):
    """
    List tasks with optional filters.

    Args:
        project_id: Filter by project UUID
        status: Filter by status (todo, in_progress, blocked, review, done)
        assigned_agent: Filter by assigned agent
        overdue: If True, only return overdue tasks
    """
    try:
        params = {}
        if project_id:
            params["project_id"] = project_id
        if status:
            params["status"] = status
        if assigned_agent:
            params["assigned_agent"] = assigned_agent
        if overdue:
            params["overdue"] = "true"

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MAGNUS_URL}/tasks", params=params, timeout=10.0)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.post("/tools/magnus/tasks/{task_id}/complete")
async def magnus_complete_task(task_id: str, notes: Optional[str] = None):
    """
    Mark a task as complete.

    Args:
        task_id: UUID of the task
        notes: Optional completion notes
    """
    try:
        async with httpx.AsyncClient() as client:
            params = {"notes": notes} if notes else {}
            response = await client.post(
                f"{MAGNUS_URL}/tasks/{task_id}/complete",
                params=params,
                timeout=10.0
            )
            await log_event("magnus_task_completed", task_id, {})
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.post("/tools/magnus/standup")
async def magnus_standup():
    """
    Generate a daily standup summary.

    Returns:
    - Overall health status
    - Days to launch
    - Project summaries
    - Overdue tasks
    - Open blockers
    - Pending decisions
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{MAGNUS_URL}/standup/generate", timeout=30.0)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/tools/magnus/blockers")
async def magnus_blockers(status: str = "open"):
    """
    List blockers.

    Args:
        status: Filter by status (open, escalated, resolved)
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MAGNUS_URL}/blockers",
                params={"status": status},
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/tools/magnus/templates")
async def magnus_templates():
    """List available project templates."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MAGNUS_URL}/templates", timeout=10.0)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/tools/magnus/connections")
async def magnus_connections():
    """List PM tool connections (Leantime, OpenProject, etc.)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MAGNUS_URL}/connections", timeout=10.0)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.get("/tools/magnus/agents/workload")
async def magnus_agent_workload():
    """Get current agent workloads."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{MAGNUS_URL}/agents/workload", timeout=10.0)
            return response.json()
    except Exception as e:
        return {"error": str(e)}


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


@app.get("/")
async def root():
    return {
        "name": "HEPHAESTUS",
        "description": "Builder MCP Server with Orchestration",
        "version": "1.1.0",
        "endpoints": {
            "health": "/health",
            "workflows": "/tools/workflow/*",
            "files": "/tools/file/*",
            "commands": "/tools/command/*",
            "git": "/tools/git/*",
            "agents": "/tools/agent/*",
            "orchestrate": "/tools/orchestrate/*",
            "lcis": "/tools/lcis/*"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
