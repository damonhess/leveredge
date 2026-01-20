#!/usr/bin/env python3
"""
CLAUDE CLI BRIDGE

Port: 8250
Domain: ORCHESTRATION

Exposes Claude CLI to Claude Web via HEPHAESTUS MCP.
Enables Launch Coach to orchestrate Claude Code's full capabilities.

CAPABILITIES:
- Single-shot tasks with full response
- Multi-turn conversations with session management
- Async task execution with status polling
- Session history and transcript retrieval
- Graceful cancellation of running tasks
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

CLAUDE_BIN = os.getenv("CLAUDE_BIN", "/home/damon/.npm-global/bin/claude")
WORKING_DIR = os.getenv("CLAUDE_WORKING_DIR", "/opt/leveredge")
RUN_AS_USER = os.getenv("CLAUDE_RUN_AS_USER", "damon")
MAX_RESPONSE_SIZE = int(os.getenv("MAX_RESPONSE_SIZE", "100000"))  # 100KB
TASK_TIMEOUT = int(os.getenv("TASK_TIMEOUT", "600"))  # 10 minutes
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "24"))

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
LCIS_URL = os.getenv("LCIS_URL", "http://localhost:8050")

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
task_processes: Dict[str, asyncio.subprocess.Process] = {}

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

    # Run directly as damon (service runs as damon)
    return [
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
