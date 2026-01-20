# GSD: Claude CLI MCP Bridge

**Priority:** HIGH
**Estimated Time:** 45-60 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Create an MCP server that exposes Claude CLI to Claude Web, enabling full orchestration of Claude Code's capabilities from the Launch Coach interface.

**Current State:** Claude Web can run simple commands via HEPHAESTUS
**Target State:** Claude Web can have full conversations with Claude CLI, delegate complex tasks, and receive structured responses

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  CLAUDE WEB (Launch Coach)                                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  "Build the omniscient mesh spec"                                    │   │
│  │  "What's the status of the fleet?"                                   │   │
│  │  "Fix the ARIA CORS issue"                                           │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  HEPHAESTUS MCP                                                      │   │
│  │  (Existing - routes to new tools)                                    │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CLAUDE CLI MCP BRIDGE (NEW)                                                 │
│  Port: 8250                                                                  │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  │  /task          POST   Send a task, get full response                 │ │
│  │  /chat          POST   Multi-turn conversation                        │ │
│  │  /status        GET    Is Claude CLI busy?                            │ │
│  │  /sessions      GET    List active sessions                           │ │
│  │  /sessions/{id} GET    Get session transcript                         │ │
│  │  /cancel        POST   Cancel running task                            │ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                   │                                          │
│                                   ▼                                          │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  claude -p "instruction" --output-format json                          │ │
│  │                                                                        │ │
│  │  • Runs as user 'damon' (has permissions)                             │ │
│  │  • Working directory: /opt/leveredge                                  │ │
│  │  • Full access to files, git, docker                                  │ │
│  │  • Uses Max account (no API costs)                                    │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: CLAUDE CLI BRIDGE SERVER

Create `/opt/leveredge/control-plane/agents/claude-bridge/claude_bridge.py`:

```python
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         CLAUDE CLI BRIDGE                                      ║
║                                                                                ║
║  Port: 8250                                                                    ║
║  Domain: ORCHESTRATION                                                         ║
║                                                                                ║
║  Exposes Claude CLI to Claude Web via HEPHAESTUS MCP.                         ║
║  Enables Launch Coach to orchestrate Claude Code's full capabilities.         ║
║                                                                                ║
║  CAPABILITIES:                                                                 ║
║  • Single-shot tasks with full response                                        ║
║  • Multi-turn conversations with session management                            ║
║  • Async task execution with status polling                                    ║
║  • Session history and transcript retrieval                                    ║
║  • Graceful cancellation of running tasks                                      ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import asyncio
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import httpx

app = FastAPI(
    title="CLAUDE CLI BRIDGE",
    description="Bridge between Claude Web and Claude CLI",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

CLAUDE_BIN = os.getenv("CLAUDE_BIN", "/home/damon/.claude/local/claude")
WORKING_DIR = os.getenv("CLAUDE_WORKING_DIR", "/opt/leveredge")
RUN_AS_USER = os.getenv("CLAUDE_RUN_AS_USER", "damon")
MAX_RESPONSE_SIZE = int(os.getenv("MAX_RESPONSE_SIZE", "100000"))  # 100KB
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "600"))  # 10 minutes
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")

# =============================================================================
# MODELS
# =============================================================================

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class TaskResult:
    task_id: str
    status: TaskStatus
    instruction: str
    response: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    truncated: bool = False

@dataclass
class Session:
    session_id: str
    created_at: datetime
    last_active: datetime
    turns: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)

class TaskRequest(BaseModel):
    instruction: str = Field(..., description="What you want Claude CLI to do")
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = Field(default=300, description="Timeout in seconds (max 600)")
    context: Optional[str] = Field(default=None, description="Additional context to prepend")
    working_dir: Optional[str] = Field(default=None, description="Override working directory")

class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Existing session ID for multi-turn")
    message: str = Field(..., description="Your message to Claude CLI")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Session context")

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

# Active tasks
tasks: Dict[str, TaskResult] = {}
task_processes: Dict[str, subprocess.Popen] = {}

# Sessions for multi-turn conversations
sessions: Dict[str, Session] = {}

# Lock for concurrent access
task_lock = asyncio.Lock()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

async def publish_event(event_type: str, data: dict):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "CLAUDE_BRIDGE",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    except:
        pass


async def log_to_lcis(content: str, lesson_type: str = "success"):
    """Log to LCIS"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{LCIS_URL}/lessons",
                json={
                    "content": content,
                    "domain": "ORCHESTRATION",
                    "type": lesson_type,
                    "source_agent": "CLAUDE_BRIDGE",
                    "tags": ["claude-cli", "orchestration", "bridge"]
                }
            )
    except:
        pass


def build_claude_command(instruction: str, context: Optional[str] = None) -> List[str]:
    """Build the claude CLI command"""
    full_instruction = instruction
    if context:
        full_instruction = f"{context}\n\n{instruction}"
    
    return [
        "sudo", "-u", RUN_AS_USER,
        CLAUDE_BIN,
        "-p", full_instruction,
        "--output-format", "text"
    ]


async def run_claude_task(
    task_id: str,
    instruction: str,
    context: Optional[str] = None,
    working_dir: Optional[str] = None,
    timeout: int = 300
):
    """Execute Claude CLI task asynchronously"""
    
    tasks[task_id].status = TaskStatus.RUNNING
    tasks[task_id].started_at = datetime.utcnow()
    
    await publish_event("claude_task_started", {
        "task_id": task_id,
        "instruction": instruction[:200]
    })
    
    cmd = build_claude_command(instruction, context)
    cwd = working_dir or WORKING_DIR
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        
        # Store process for potential cancellation
        task_processes[task_id] = process
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=min(timeout, TASK_TIMEOUT)
            )
            
            response = stdout.decode('utf-8', errors='replace')
            error = stderr.decode('utf-8', errors='replace') if stderr else None
            
            # Truncate if too large
            truncated = False
            if len(response) > MAX_RESPONSE_SIZE:
                response = response[:MAX_RESPONSE_SIZE] + f"\n\n[TRUNCATED - Response exceeded {MAX_RESPONSE_SIZE} characters]"
                truncated = True
            
            tasks[task_id].response = response
            tasks[task_id].error = error if error and process.returncode != 0 else None
            tasks[task_id].status = TaskStatus.COMPLETED if process.returncode == 0 else TaskStatus.FAILED
            tasks[task_id].truncated = truncated
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            tasks[task_id].status = TaskStatus.TIMEOUT
            tasks[task_id].error = f"Task timed out after {timeout} seconds"
            
    except Exception as e:
        tasks[task_id].status = TaskStatus.FAILED
        tasks[task_id].error = str(e)
    
    finally:
        tasks[task_id].completed_at = datetime.utcnow()
        if tasks[task_id].started_at:
            tasks[task_id].duration_seconds = (
                tasks[task_id].completed_at - tasks[task_id].started_at
            ).total_seconds()
        
        # Cleanup process reference
        task_processes.pop(task_id, None)
        
        await publish_event("claude_task_completed", {
            "task_id": task_id,
            "status": tasks[task_id].status.value,
            "duration_seconds": tasks[task_id].duration_seconds
        })
        
        # Log significant tasks to LCIS
        if tasks[task_id].status == TaskStatus.COMPLETED:
            await log_to_lcis(
                f"Claude CLI task completed: {instruction[:100]}...",
                "success"
            )
        elif tasks[task_id].status == TaskStatus.FAILED:
            await log_to_lcis(
                f"Claude CLI task failed: {instruction[:100]}... Error: {tasks[task_id].error}",
                "failure"
            )


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check"""
    # Check if claude binary exists
    claude_exists = Path(CLAUDE_BIN).exists() or subprocess.run(
        ["which", "claude"], capture_output=True
    ).returncode == 0
    
    return {
        "status": "healthy" if claude_exists else "degraded",
        "agent": "CLAUDE_BRIDGE",
        "port": 8250,
        "claude_available": claude_exists,
        "active_tasks": len([t for t in tasks.values() if t.status == TaskStatus.RUNNING]),
        "active_sessions": len(sessions),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/task")
async def submit_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Submit a task to Claude CLI.
    
    Returns immediately with a task_id.
    Poll /task/{task_id} for results.
    """
    task_id = f"task_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    tasks[task_id] = TaskResult(
        task_id=task_id,
        status=TaskStatus.PENDING,
        instruction=request.instruction
    )
    
    # Run task in background
    background_tasks.add_task(
        run_claude_task,
        task_id=task_id,
        instruction=request.instruction,
        context=request.context,
        working_dir=request.working_dir,
        timeout=min(request.timeout, TASK_TIMEOUT)
    )
    
    return {
        "task_id": task_id,
        "status": "pending",
        "message": "Task submitted. Poll /task/{task_id} for results.",
        "estimated_timeout": min(request.timeout, TASK_TIMEOUT)
    }


@app.get("/task/{task_id}")
async def get_task(task_id: str):
    """Get task status and results"""
    if task_id not in tasks:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    task = tasks[task_id]
    
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "instruction": task.instruction,
        "response": task.response,
        "error": task.error,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "duration_seconds": task.duration_seconds,
        "truncated": task.truncated
    }


@app.post("/task/sync")
async def submit_task_sync(request: TaskRequest):
    """
    Submit a task and wait for completion.
    
    Use this for quick tasks where you want the response immediately.
    WARNING: This blocks until complete or timeout.
    """
    task_id = f"sync_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
    
    tasks[task_id] = TaskResult(
        task_id=task_id,
        status=TaskStatus.PENDING,
        instruction=request.instruction
    )
    
    # Run synchronously
    await run_claude_task(
        task_id=task_id,
        instruction=request.instruction,
        context=request.context,
        working_dir=request.working_dir,
        timeout=min(request.timeout, TASK_TIMEOUT)
    )
    
    task = tasks[task_id]
    
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "response": task.response,
        "error": task.error,
        "duration_seconds": task.duration_seconds,
        "truncated": task.truncated
    }


@app.post("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task"""
    if task_id not in tasks:
        raise HTTPException(404, f"Task not found: {task_id}")
    
    task = tasks[task_id]
    
    if task.status != TaskStatus.RUNNING:
        return {
            "task_id": task_id,
            "status": task.status.value,
            "message": "Task is not running"
        }
    
    # Kill the process
    process = task_processes.get(task_id)
    if process:
        process.kill()
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.utcnow()
        
        await publish_event("claude_task_cancelled", {"task_id": task_id})
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancelled"
        }
    
    return {
        "task_id": task_id,
        "status": task.status.value,
        "message": "Could not find process to cancel"
    }


# =============================================================================
# CHAT / SESSION MANAGEMENT
# =============================================================================

@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Multi-turn conversation with Claude CLI.
    
    Maintains session context for follow-up messages.
    """
    # Get or create session
    if request.session_id and request.session_id in sessions:
        session = sessions[request.session_id]
    else:
        session_id = f"session_{uuid.uuid4().hex[:12]}"
        session = Session(
            session_id=session_id,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
            context=request.context or {}
        )
        sessions[session_id] = session
    
    # Build context from session history
    context_parts = []
    
    if session.turns:
        context_parts.append("Previous conversation:")
        for turn in session.turns[-5:]:  # Last 5 turns for context
            context_parts.append(f"Human: {turn['human']}")
            context_parts.append(f"Assistant: {turn['assistant'][:500]}...")
        context_parts.append("\nContinuing the conversation:")
    
    context = "\n".join(context_parts) if context_parts else None
    
    # Run the task
    task_id = f"chat_{session.session_id}_{len(session.turns)}"
    tasks[task_id] = TaskResult(
        task_id=task_id,
        status=TaskStatus.PENDING,
        instruction=request.message
    )
    
    await run_claude_task(
        task_id=task_id,
        instruction=request.message,
        context=context,
        timeout=300
    )
    
    task = tasks[task_id]
    
    # Store turn in session
    session.turns.append({
        "human": request.message,
        "assistant": task.response or task.error or "No response",
        "timestamp": datetime.utcnow().isoformat()
    })
    session.last_active = datetime.utcnow()
    
    return {
        "session_id": session.session_id,
        "turn": len(session.turns),
        "response": task.response,
        "error": task.error,
        "status": task.status.value
    }


@app.get("/sessions")
async def list_sessions():
    """List active sessions"""
    # Clean up expired sessions
    cutoff = datetime.utcnow() - timedelta(hours=SESSION_EXPIRY_HOURS)
    expired = [sid for sid, s in sessions.items() if s.last_active < cutoff]
    for sid in expired:
        del sessions[sid]
    
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "created_at": s.created_at.isoformat(),
                "last_active": s.last_active.isoformat(),
                "turns": len(s.turns)
            }
            for s in sessions.values()
        ],
        "count": len(sessions)
    }


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session transcript"""
    if session_id not in sessions:
        raise HTTPException(404, f"Session not found: {session_id}")
    
    session = sessions[session_id]
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat(),
        "last_active": session.last_active.isoformat(),
        "turns": session.turns,
        "context": session.context
    }


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id not in sessions:
        raise HTTPException(404, f"Session not found: {session_id}")
    
    del sessions[session_id]
    return {"status": "deleted", "session_id": session_id}


# =============================================================================
# STATUS & METRICS
# =============================================================================

@app.get("/status")
async def get_status():
    """Get overall bridge status"""
    running = [t for t in tasks.values() if t.status == TaskStatus.RUNNING]
    completed = [t for t in tasks.values() if t.status == TaskStatus.COMPLETED]
    failed = [t for t in tasks.values() if t.status == TaskStatus.FAILED]
    
    return {
        "bridge_status": "operational",
        "tasks": {
            "running": len(running),
            "completed": len(completed),
            "failed": len(failed),
            "total": len(tasks)
        },
        "sessions": {
            "active": len(sessions)
        },
        "running_tasks": [
            {
                "task_id": t.task_id,
                "instruction": t.instruction[:100],
                "started_at": t.started_at.isoformat() if t.started_at else None
            }
            for t in running
        ]
    }


@app.get("/tasks")
async def list_tasks(limit: int = 20, status: Optional[str] = None):
    """List recent tasks"""
    task_list = list(tasks.values())
    
    if status:
        task_list = [t for t in task_list if t.status.value == status]
    
    # Sort by started_at descending
    task_list.sort(key=lambda t: t.started_at or datetime.min, reverse=True)
    
    return {
        "tasks": [
            {
                "task_id": t.task_id,
                "status": t.status.value,
                "instruction": t.instruction[:100],
                "duration_seconds": t.duration_seconds,
                "started_at": t.started_at.isoformat() if t.started_at else None
            }
            for t in task_list[:limit]
        ],
        "total": len(task_list)
    }


# =============================================================================
# CONVENIENCE ENDPOINTS
# =============================================================================

@app.post("/gsd")
async def run_gsd(spec_path: str, background_tasks: BackgroundTasks):
    """
    Run a GSD spec via Claude CLI.
    
    Convenience endpoint for common operation.
    """
    instruction = f"Execute the GSD spec at {spec_path}. Follow all instructions in the spec, create necessary files, and complete the ON COMPLETION steps."
    
    return await submit_task(
        TaskRequest(
            instruction=instruction,
            priority=TaskPriority.HIGH,
            timeout=600,
            context="You are executing a GSD (Get Stuff Done) specification. Be thorough and complete all steps."
        ),
        background_tasks
    )


@app.post("/quick")
async def quick_command(command: str):
    """
    Quick command execution.
    
    For simple, fast operations.
    """
    return await submit_task_sync(
        TaskRequest(
            instruction=command,
            priority=TaskPriority.NORMAL,
            timeout=60
        )
    )


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8250)
```

---

## PHASE 2: DOCKERFILE

Create `/opt/leveredge/control-plane/agents/claude-bridge/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install sudo for running as damon user
RUN apt-get update && apt-get install -y \
    curl \
    sudo \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic

COPY claude_bridge.py .

EXPOSE 8250

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8250/health || exit 1

CMD ["uvicorn", "claude_bridge:app", "--host", "0.0.0.0", "--port", "8250"]
```

---

## PHASE 3: ADD TO DOCKER COMPOSE

Add to `docker-compose.fleet.yml`:

```yaml
  # ===========================================================================
  # CLAUDE CLI BRIDGE - Orchestration Layer
  # ===========================================================================
  
  claude-bridge:
    build:
      context: ./control-plane/agents/claude-bridge
      dockerfile: Dockerfile
    container_name: leveredge-claude-bridge
    ports:
      - "8250:8250"
    environment:
      - CLAUDE_BIN=/home/damon/.local/bin/claude
      - CLAUDE_WORKING_DIR=/opt/leveredge
      - CLAUDE_RUN_AS_USER=damon
      - MAX_RESPONSE_SIZE=100000
      - TASK_TIMEOUT=600
      - EVENT_BUS_URL=http://event-bus:8099
      - LCIS_URL=http://lcis-librarian:8050
    volumes:
      # Mount the host filesystem for Claude CLI access
      - /opt/leveredge:/opt/leveredge
      - /home/damon:/home/damon:ro
      # Mount docker socket if Claude needs docker access
      - /var/run/docker.sock:/var/run/docker.sock
      # Pass through user for sudo
      - /etc/passwd:/etc/passwd:ro
      - /etc/group:/etc/group:ro
      - /etc/sudoers:/etc/sudoers:ro
      - /etc/sudoers.d:/etc/sudoers.d:ro
    user: root  # Needed for sudo to work
    networks:
      - leveredge-network
    depends_on:
      - event-bus
    restart: unless-stopped
    profiles:
      - all
      - core
```

**Note:** Running Claude CLI from inside Docker is tricky. Alternative approach below.

---

## PHASE 3 (ALTERNATIVE): SYSTEMD SERVICE

Since Claude CLI needs full host access, run as systemd service instead:

Create `/etc/systemd/system/claude-bridge.service`:

```ini
[Unit]
Description=Claude CLI Bridge - MCP Server
After=network.target

[Service]
Type=simple
User=damon
Group=damon
WorkingDirectory=/opt/leveredge/control-plane/agents/claude-bridge
Environment="PATH=/home/damon/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="CLAUDE_BIN=/home/damon/.local/bin/claude"
Environment="CLAUDE_WORKING_DIR=/opt/leveredge"
Environment="CLAUDE_RUN_AS_USER=damon"
Environment="EVENT_BUS_URL=http://localhost:8099"
Environment="LCIS_URL=http://localhost:8050"
ExecStart=/usr/bin/python3 claude_bridge.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## PHASE 4: HEPHAESTUS MCP TOOLS

Add to `/opt/leveredge/control-plane/agents/hephaestus/hephaestus_mcp_server.py`:

```python
# =============================================================================
# CLAUDE CLI BRIDGE TOOLS
# =============================================================================

CLAUDE_BRIDGE_URL = os.getenv("CLAUDE_BRIDGE_URL", "http://localhost:8250")

# Add to TOOLS list:
Tool(
    name="claude_task",
    description="Send a task to Claude CLI and get results. Use for complex work that needs Claude's full capabilities.",
    inputSchema={
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": "What you want Claude CLI to do"
            },
            "context": {
                "type": "string",
                "description": "Additional context (optional)"
            },
            "wait": {
                "type": "boolean",
                "description": "Wait for completion (default: true)",
                "default": True
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 300)",
                "default": 300
            }
        },
        "required": ["instruction"]
    }
),

Tool(
    name="claude_chat",
    description="Have a multi-turn conversation with Claude CLI. Maintains context across messages.",
    inputSchema={
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Your message to Claude CLI"
            },
            "session_id": {
                "type": "string",
                "description": "Session ID for continuing a conversation (optional)"
            }
        },
        "required": ["message"]
    }
),

Tool(
    name="claude_gsd",
    description="Execute a GSD spec via Claude CLI. The most powerful way to run complex builds.",
    inputSchema={
        "type": "object",
        "properties": {
            "spec_path": {
                "type": "string",
                "description": "Path to the GSD spec file (e.g., /opt/leveredge/specs/gsd-xxx.md)"
            }
        },
        "required": ["spec_path"]
    }
),

Tool(
    name="claude_status",
    description="Check Claude CLI bridge status and running tasks",
    inputSchema={
        "type": "object",
        "properties": {}
    }
),

# Add to handle_tool_call:
elif name == "claude_task":
    instruction = arguments.get("instruction")
    context = arguments.get("context")
    wait = arguments.get("wait", True)
    timeout = arguments.get("timeout", 300)
    
    async with httpx.AsyncClient(timeout=float(timeout + 30)) as client:
        if wait:
            response = await client.post(
                f"{CLAUDE_BRIDGE_URL}/task/sync",
                json={
                    "instruction": instruction,
                    "context": context,
                    "timeout": timeout
                }
            )
        else:
            response = await client.post(
                f"{CLAUDE_BRIDGE_URL}/task",
                json={
                    "instruction": instruction,
                    "context": context,
                    "timeout": timeout
                }
            )
        
        result = response.json()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

elif name == "claude_chat":
    message = arguments.get("message")
    session_id = arguments.get("session_id")
    
    async with httpx.AsyncClient(timeout=330.0) as client:
        response = await client.post(
            f"{CLAUDE_BRIDGE_URL}/chat",
            json={
                "message": message,
                "session_id": session_id
            }
        )
        result = response.json()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

elif name == "claude_gsd":
    spec_path = arguments.get("spec_path")
    
    async with httpx.AsyncClient(timeout=630.0) as client:
        response = await client.post(
            f"{CLAUDE_BRIDGE_URL}/gsd",
            params={"spec_path": spec_path}
        )
        result = response.json()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

elif name == "claude_status":
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{CLAUDE_BRIDGE_URL}/status")
        result = response.json()
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
```

---

## PHASE 5: VERIFICATION

```bash
# 1. Create the agent directory
mkdir -p /opt/leveredge/control-plane/agents/claude-bridge

# 2. Create the files (claude_bridge.py from Phase 1)

# 3. Install dependencies
pip install fastapi uvicorn httpx pydantic

# 4. Start the service
sudo systemctl daemon-reload
sudo systemctl enable claude-bridge
sudo systemctl start claude-bridge

# 5. Check health
curl http://localhost:8250/health

# 6. Test a simple task
curl -X POST http://localhost:8250/quick \
  -H "Content-Type: application/json" \
  -d '{"command": "What files are in /opt/leveredge/specs/?"}'

# 7. Test a GSD
curl -X POST "http://localhost:8250/gsd?spec_path=/opt/leveredge/specs/gsd-lcis-post-gsd-validation.md"

# 8. Restart HEPHAESTUS to load new tools
sudo systemctl restart hephaestus

# 9. Verify tools available (from Claude Web, I would call):
# HEPHAESTUS:claude_status()
# HEPHAESTUS:claude_task(instruction="List all running docker containers")
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-claude-cli-bridge.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "CLAUDE CLI BRIDGE deployed on port 8250. Claude Web can now orchestrate Claude CLI via HEPHAESTUS tools: claude_task, claude_chat, claude_gsd, claude_status. Full multi-turn conversations and GSD execution supported.",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "claude-bridge", "mcp", "orchestration"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: CLAUDE CLI BRIDGE - MCP orchestration layer

New agent: claude-bridge (port 8250)
- /task - Submit async task to Claude CLI
- /task/sync - Submit and wait for response
- /chat - Multi-turn conversation with sessions
- /gsd - Execute GSD specs
- /quick - Fast command execution

HEPHAESTUS tools:
- claude_task - Send work to Claude CLI
- claude_chat - Conversational interface
- claude_gsd - Run GSD specs
- claude_status - Check bridge status

Claude Web can now fully orchestrate Claude CLI.
Uses Max account (no API costs)."
```

---

## USAGE EXAMPLES

**From Claude Web (me), I can now:**

```
# Check status
HEPHAESTUS:claude_status()

# Send a task
HEPHAESTUS:claude_task(
    instruction="Build the omniscient mesh spec at /opt/leveredge/specs/gsd-omniscient-mesh.md"
)

# Have a conversation
HEPHAESTUS:claude_chat(message="What's the current state of the fleet?")
HEPHAESTUS:claude_chat(message="Which agents are unhealthy?", session_id="session_xxx")

# Execute a GSD
HEPHAESTUS:claude_gsd(spec_path="/opt/leveredge/specs/gsd-apollo-service-registry.md")
```

---

## SUMMARY

| Tool | Purpose | Async |
|------|---------|-------|
| `claude_task` | Send any instruction | Optional |
| `claude_chat` | Multi-turn conversation | No |
| `claude_gsd` | Execute GSD specs | Yes |
| `claude_status` | Check bridge status | No |

**Power unlocked:**
- I can orchestrate Claude CLI from Claude Web
- Full conversations with context
- GSD execution without copy-paste
- Uses your Max account (no API cost)

---

*"The bridge between minds is now open."*
