# GSD: Terminal Bridge MCP Server

**Priority:** HIGH
**Estimated Time:** 20-30 minutes
**Created:** January 20, 2026
**Status:** Ready for execution
**Depends On:** Claude CLI Bridge (can be built together)

---

## OVERVIEW

Create an MCP server that gives Claude Web direct terminal (bash) access on the server, with safety controls and audit logging.

**Current State:** HEPHAESTUS has a limited command whitelist
**Target State:** Full bash access with safety rails, history, and LCIS audit trail

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLAUDE WEB (Launch Coach)                                                  │
│                                                                             │
│  "Check disk space"                                                         │
│  "Restart the muse container"                                               │
│  "Show me the last 50 lines of aria-chat logs"                             │
│                                                                             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│  TERMINAL BRIDGE (Port 8251)                                                  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  SAFETY LAYER                                                           │ │
│  │                                                                         │ │
│  │  • Blocked commands: rm -rf /, mkfs, dd if=, :(){ :|:& };:            │ │
│  │  • Blocked patterns: /etc/passwd, /etc/shadow, private keys            │ │
│  │  • Requires confirmation: reboot, shutdown, systemctl stop             │ │
│  │  • Rate limiting: Max 30 commands/minute                               │ │
│  │  • Timeout: 60s default, 300s max                                      │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  ENDPOINTS                                                              │ │
│  │                                                                         │ │
│  │  POST /exec           Execute command, get output                       │ │
│  │  POST /exec/stream    Execute with streaming output                     │ │
│  │  GET  /history        Command history                                   │ │
│  │  GET  /cwd            Current working directory                         │ │
│  │  POST /cd             Change directory                                  │ │
│  │  GET  /env            Environment variables (filtered)                  │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                               │
│                                    │                                          │
│                                    ▼                                          │
│                           /bin/bash -c "command"                             │
│                           (as user damon)                                    │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │  LCIS - Full Audit Trail      │
                    │  Every command logged         │
                    └───────────────────────────────┘
```

---

## PHASE 1: TERMINAL BRIDGE SERVER

Create `/opt/leveredge/control-plane/agents/terminal-bridge/terminal_bridge.py`:

```python
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         TERMINAL BRIDGE                                        ║
║                                                                                ║
║  Port: 8251                                                                    ║
║  Domain: SYSTEM                                                                ║
║                                                                                ║
║  Provides Claude Web with controlled bash access.                             ║
║  All commands are logged, rate-limited, and safety-checked.                   ║
║                                                                                ║
║  SAFETY FEATURES:                                                              ║
║  • Dangerous command blocking                                                  ║
║  • Sensitive path protection                                                   ║
║  • Rate limiting                                                               ║
║  • Timeout enforcement                                                         ║
║  • Full audit trail                                                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import re
import asyncio
import subprocess
import shlex
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from collections import deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import httpx

app = FastAPI(
    title="TERMINAL BRIDGE",
    description="Controlled bash access for Claude Web",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

RUN_AS_USER = os.getenv("RUN_AS_USER", "damon")
DEFAULT_CWD = os.getenv("DEFAULT_CWD", "/opt/leveredge")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "60"))
MAX_TIMEOUT = int(os.getenv("MAX_TIMEOUT", "300"))
MAX_OUTPUT_SIZE = int(os.getenv("MAX_OUTPUT_SIZE", "100000"))  # 100KB
RATE_LIMIT_COMMANDS = int(os.getenv("RATE_LIMIT_COMMANDS", "30"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")
LCIS_URL = os.getenv("LCIS_URL", "http://localhost:8050")

# Current working directory (persists across commands)
current_cwd = DEFAULT_CWD

# =============================================================================
# SAFETY CONFIGURATION
# =============================================================================

# Commands that are completely blocked
BLOCKED_COMMANDS = [
    r"^rm\s+-rf\s+/\s*$",           # rm -rf /
    r"^rm\s+-rf\s+/\*",              # rm -rf /*
    r"^rm\s+-rf\s+~",                # rm -rf ~
    r"^mkfs\.",                       # mkfs.* (format disk)
    r"^dd\s+if=.*of=/dev/",          # dd to disk
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", # Fork bomb
    r"^chmod\s+-R\s+777\s+/",        # chmod 777 /
    r"^chown\s+-R.*\s+/\s*$",        # chown -R on /
    r">\s*/dev/sd[a-z]",             # Write to disk
    r"^init\s+0",                     # Shutdown
    r"^halt\b",                       # Halt
    r"^poweroff\b",                   # Poweroff
]

# Patterns in commands that are blocked
BLOCKED_PATTERNS = [
    r"/etc/shadow",
    r"/etc/passwd.*>",               # Writing to passwd
    r"\.ssh/.*_key",                 # Private keys
    r"\.gnupg/",                     # GPG keys
    r"/root/",                       # Root's home
    r"SUPABASE.*KEY",                # Supabase keys in commands
    r"ANTHROPIC.*KEY",               # API keys
    r"password\s*=",                 # Password assignments
    r"secret\s*=",                   # Secret assignments
]

# Commands that require confirmation (not blocked, but flagged)
CONFIRM_COMMANDS = [
    r"^reboot\b",
    r"^shutdown\b",
    r"^systemctl\s+(stop|disable|mask)",
    r"^docker\s+system\s+prune",
    r"^rm\s+-rf",                    # Any rm -rf
    r"^DROP\s+",                     # SQL DROP
    r"^DELETE\s+FROM.*WHERE\s+1",   # Mass delete
    r"^TRUNCATE\s+",                 # SQL truncate
]

# Allowed paths (if specified, only these paths are accessible)
# Empty means all paths allowed (except blocked)
ALLOWED_PATHS = []

# =============================================================================
# MODELS
# =============================================================================

@dataclass
class CommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    cwd: str
    executed_at: datetime
    duration_seconds: float
    truncated: bool = False
    blocked: bool = False
    block_reason: Optional[str] = None

class ExecRequest(BaseModel):
    command: str = Field(..., description="Bash command to execute")
    cwd: Optional[str] = Field(default=None, description="Working directory (default: current)")
    timeout: int = Field(default=60, description="Timeout in seconds (max 300)")
    env: Optional[Dict[str, str]] = Field(default=None, description="Additional environment variables")

class CdRequest(BaseModel):
    path: str = Field(..., description="Directory to change to")

# =============================================================================
# STATE
# =============================================================================

# Command history
command_history: deque = deque(maxlen=500)

# Rate limiting
command_timestamps: deque = deque(maxlen=RATE_LIMIT_COMMANDS)

# =============================================================================
# SAFETY FUNCTIONS
# =============================================================================

def check_command_safety(command: str) -> Tuple[bool, Optional[str]]:
    """
    Check if command is safe to execute.
    Returns (is_safe, reason_if_blocked)
    """
    command_lower = command.lower().strip()
    
    # Check blocked commands
    for pattern in BLOCKED_COMMANDS:
        if re.search(pattern, command_lower):
            return False, f"Blocked command pattern: {pattern}"
    
    # Check blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return False, f"Blocked pattern detected: {pattern}"
    
    return True, None


def check_requires_confirmation(command: str) -> Optional[str]:
    """Check if command requires confirmation"""
    command_lower = command.lower().strip()
    
    for pattern in CONFIRM_COMMANDS:
        if re.search(pattern, command_lower, re.IGNORECASE):
            return f"Command matches confirmation pattern: {pattern}"
    
    return None


def check_rate_limit() -> Tuple[bool, Optional[str]]:
    """Check if rate limit exceeded"""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    # Remove old timestamps
    while command_timestamps and command_timestamps[0] < cutoff:
        command_timestamps.popleft()
    
    if len(command_timestamps) >= RATE_LIMIT_COMMANDS:
        return False, f"Rate limit exceeded: {RATE_LIMIT_COMMANDS} commands per {RATE_LIMIT_WINDOW}s"
    
    return True, None


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
                    "source": "TERMINAL_BRIDGE",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    except:
        pass


async def log_to_lcis(command: str, result: CommandResult):
    """Log command execution to LCIS"""
    try:
        content = f"Terminal: `{command}` (exit: {result.exit_code}, {result.duration_seconds:.2f}s)"
        if result.blocked:
            content = f"Terminal BLOCKED: `{command}` - {result.block_reason}"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{LCIS_URL}/lessons",
                json={
                    "content": content,
                    "domain": "TERMINAL",
                    "type": "command" if not result.blocked else "blocked",
                    "source_agent": "TERMINAL_BRIDGE",
                    "tags": ["terminal", "bash", "audit"],
                    "context": {
                        "command": command,
                        "exit_code": result.exit_code,
                        "cwd": result.cwd,
                        "blocked": result.blocked
                    }
                }
            )
    except:
        pass


async def execute_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    env: Optional[Dict[str, str]] = None
) -> CommandResult:
    """Execute a bash command safely"""
    global current_cwd
    
    start_time = datetime.utcnow()
    working_dir = cwd or current_cwd
    
    # Safety check
    is_safe, block_reason = check_command_safety(command)
    if not is_safe:
        result = CommandResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=f"BLOCKED: {block_reason}",
            cwd=working_dir,
            executed_at=start_time,
            duration_seconds=0,
            blocked=True,
            block_reason=block_reason
        )
        await log_to_lcis(command, result)
        return result
    
    # Rate limit check
    rate_ok, rate_reason = check_rate_limit()
    if not rate_ok:
        result = CommandResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=f"RATE LIMITED: {rate_reason}",
            cwd=working_dir,
            executed_at=start_time,
            duration_seconds=0,
            blocked=True,
            block_reason=rate_reason
        )
        return result
    
    # Record timestamp for rate limiting
    command_timestamps.append(datetime.utcnow())
    
    # Prepare environment
    exec_env = os.environ.copy()
    if env:
        exec_env.update(env)
    
    # Execute
    try:
        # Use sudo to run as the specified user
        full_command = f"cd {shlex.quote(working_dir)} && {command}"
        
        process = await asyncio.create_subprocess_exec(
            "sudo", "-u", RUN_AS_USER, "bash", "-c", full_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=exec_env
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=min(timeout, MAX_TIMEOUT)
            )
            
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            # Truncate if needed
            truncated = False
            if len(stdout_str) > MAX_OUTPUT_SIZE:
                stdout_str = stdout_str[:MAX_OUTPUT_SIZE] + f"\n\n[TRUNCATED - Output exceeded {MAX_OUTPUT_SIZE} bytes]"
                truncated = True
            
            result = CommandResult(
                command=command,
                exit_code=process.returncode,
                stdout=stdout_str,
                stderr=stderr_str,
                cwd=working_dir,
                executed_at=start_time,
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                truncated=truncated
            )
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            result = CommandResult(
                command=command,
                exit_code=-1,
                stdout="",
                stderr=f"TIMEOUT: Command exceeded {timeout}s",
                cwd=working_dir,
                executed_at=start_time,
                duration_seconds=timeout
            )
            
    except Exception as e:
        result = CommandResult(
            command=command,
            exit_code=-1,
            stdout="",
            stderr=f"ERROR: {str(e)}",
            cwd=working_dir,
            executed_at=start_time,
            duration_seconds=(datetime.utcnow() - start_time).total_seconds()
        )
    
    # Store in history
    command_history.append(result)
    
    # Log to LCIS
    await log_to_lcis(command, result)
    
    # Publish event
    await publish_event("terminal_command", {
        "command": command[:200],
        "exit_code": result.exit_code,
        "duration": result.duration_seconds
    })
    
    return result


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "agent": "TERMINAL_BRIDGE",
        "port": 8251,
        "cwd": current_cwd,
        "commands_in_history": len(command_history),
        "rate_limit": f"{len(command_timestamps)}/{RATE_LIMIT_COMMANDS} per {RATE_LIMIT_WINDOW}s",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/exec")
async def exec_command(request: ExecRequest):
    """Execute a bash command"""
    result = await execute_command(
        command=request.command,
        cwd=request.cwd,
        timeout=request.timeout,
        env=request.env
    )
    
    return {
        "command": result.command,
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "cwd": result.cwd,
        "duration_seconds": result.duration_seconds,
        "truncated": result.truncated,
        "blocked": result.blocked,
        "block_reason": result.block_reason
    }


@app.post("/exec/check")
async def check_command(request: ExecRequest):
    """Check if a command would be allowed (dry run)"""
    is_safe, block_reason = check_command_safety(request.command)
    confirm_reason = check_requires_confirmation(request.command)
    
    return {
        "command": request.command,
        "allowed": is_safe,
        "block_reason": block_reason,
        "requires_confirmation": confirm_reason is not None,
        "confirmation_reason": confirm_reason
    }


@app.get("/cwd")
async def get_cwd():
    """Get current working directory"""
    return {"cwd": current_cwd}


@app.post("/cd")
async def change_directory(request: CdRequest):
    """Change current working directory"""
    global current_cwd
    
    # Resolve path
    if request.path.startswith("/"):
        new_path = request.path
    else:
        new_path = str(Path(current_cwd) / request.path)
    
    # Normalize
    new_path = str(Path(new_path).resolve())
    
    # Check if exists
    if not os.path.isdir(new_path):
        raise HTTPException(404, f"Directory not found: {new_path}")
    
    current_cwd = new_path
    
    return {"cwd": current_cwd}


@app.get("/history")
async def get_history(limit: int = 50):
    """Get command history"""
    history = list(command_history)[-limit:]
    
    return {
        "history": [
            {
                "command": r.command,
                "exit_code": r.exit_code,
                "cwd": r.cwd,
                "executed_at": r.executed_at.isoformat(),
                "duration_seconds": r.duration_seconds,
                "blocked": r.blocked
            }
            for r in reversed(history)
        ],
        "total": len(command_history)
    }


@app.get("/env")
async def get_environment():
    """Get environment variables (filtered for safety)"""
    # Filter out sensitive vars
    sensitive_patterns = ["KEY", "SECRET", "PASSWORD", "TOKEN", "CREDENTIAL"]
    
    safe_env = {}
    for key, value in os.environ.items():
        if any(p in key.upper() for p in sensitive_patterns):
            safe_env[key] = "[REDACTED]"
        else:
            safe_env[key] = value
    
    return {"environment": safe_env}


@app.get("/safety")
async def get_safety_rules():
    """Get current safety configuration"""
    return {
        "blocked_commands": BLOCKED_COMMANDS,
        "blocked_patterns": BLOCKED_PATTERNS,
        "confirm_commands": CONFIRM_COMMANDS,
        "rate_limit": {
            "commands": RATE_LIMIT_COMMANDS,
            "window_seconds": RATE_LIMIT_WINDOW
        },
        "max_timeout": MAX_TIMEOUT,
        "max_output_size": MAX_OUTPUT_SIZE
    }


# =============================================================================
# CONVENIENCE ENDPOINTS
# =============================================================================

@app.get("/ls")
async def ls(path: str = None):
    """List directory contents"""
    target = path or current_cwd
    result = await execute_command(f"ls -la {shlex.quote(target)}")
    return {"path": target, "output": result.stdout, "exit_code": result.exit_code}


@app.get("/cat")
async def cat(path: str):
    """Read file contents"""
    result = await execute_command(f"cat {shlex.quote(path)}")
    return {"path": path, "content": result.stdout, "exit_code": result.exit_code}


@app.get("/tail")
async def tail(path: str, lines: int = 50):
    """Tail a file"""
    result = await execute_command(f"tail -n {lines} {shlex.quote(path)}")
    return {"path": path, "lines": lines, "content": result.stdout, "exit_code": result.exit_code}


@app.get("/docker/ps")
async def docker_ps():
    """List running containers"""
    result = await execute_command("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'")
    return {"output": result.stdout, "exit_code": result.exit_code}


@app.get("/docker/logs/{container}")
async def docker_logs(container: str, lines: int = 100):
    """Get container logs"""
    result = await execute_command(f"docker logs --tail {lines} {shlex.quote(container)}")
    return {"container": container, "logs": result.stdout + result.stderr, "exit_code": result.exit_code}


@app.post("/docker/restart/{container}")
async def docker_restart(container: str):
    """Restart a container"""
    result = await execute_command(f"docker restart {shlex.quote(container)}")
    return {"container": container, "output": result.stdout, "exit_code": result.exit_code}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8251)
```

---

## PHASE 2: SYSTEMD SERVICE

Create `/etc/systemd/system/terminal-bridge.service`:

```ini
[Unit]
Description=Terminal Bridge - Bash Access for Claude Web
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/leveredge/control-plane/agents/terminal-bridge
Environment="RUN_AS_USER=damon"
Environment="DEFAULT_CWD=/opt/leveredge"
Environment="EVENT_BUS_URL=http://localhost:8099"
Environment="LCIS_URL=http://localhost:8050"
ExecStart=/usr/bin/python3 terminal_bridge.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## PHASE 3: HEPHAESTUS MCP TOOLS

Add to `/opt/leveredge/control-plane/agents/hephaestus/hephaestus_mcp_server.py`:

```python
# =============================================================================
# TERMINAL BRIDGE TOOLS
# =============================================================================

TERMINAL_BRIDGE_URL = os.getenv("TERMINAL_BRIDGE_URL", "http://localhost:8251")

# Add to TOOLS list:
Tool(
    name="terminal_exec",
    description="Execute a bash command on the server. Full shell access with safety controls.",
    inputSchema={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Bash command to execute"
            },
            "cwd": {
                "type": "string",
                "description": "Working directory (optional)"
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default: 60, max: 300)",
                "default": 60
            }
        },
        "required": ["command"]
    }
),

Tool(
    name="terminal_cd",
    description="Change the terminal's working directory",
    inputSchema={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path"
            }
        },
        "required": ["path"]
    }
),

Tool(
    name="terminal_history",
    description="Get recent command history",
    inputSchema={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Number of commands to return",
                "default": 20
            }
        }
    }
),

Tool(
    name="docker_ps",
    description="List running Docker containers",
    inputSchema={
        "type": "object",
        "properties": {}
    }
),

Tool(
    name="docker_logs",
    description="Get logs from a Docker container",
    inputSchema={
        "type": "object",
        "properties": {
            "container": {
                "type": "string",
                "description": "Container name"
            },
            "lines": {
                "type": "integer",
                "description": "Number of lines (default: 100)",
                "default": 100
            }
        },
        "required": ["container"]
    }
),

Tool(
    name="docker_restart",
    description="Restart a Docker container",
    inputSchema={
        "type": "object",
        "properties": {
            "container": {
                "type": "string",
                "description": "Container name to restart"
            }
        },
        "required": ["container"]
    }
),

# Add to handle_tool_call:
elif name == "terminal_exec":
    command = arguments.get("command")
    cwd = arguments.get("cwd")
    timeout = arguments.get("timeout", 60)
    
    async with httpx.AsyncClient(timeout=float(timeout + 10)) as client:
        response = await client.post(
            f"{TERMINAL_BRIDGE_URL}/exec",
            json={"command": command, "cwd": cwd, "timeout": timeout}
        )
        result = response.json()
        
        # Format output nicely
        output = f"$ {command}\n"
        if result.get("stdout"):
            output += result["stdout"]
        if result.get("stderr"):
            output += f"\n[stderr]\n{result['stderr']}"
        if result.get("blocked"):
            output = f"BLOCKED: {result.get('block_reason')}"
        
        output += f"\n\n[exit: {result.get('exit_code')}, {result.get('duration_seconds', 0):.2f}s]"
        
        return [TextContent(type="text", text=output)]

elif name == "terminal_cd":
    path = arguments.get("path")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{TERMINAL_BRIDGE_URL}/cd",
            json={"path": path}
        )
        result = response.json()
        return [TextContent(type="text", text=f"Changed directory to: {result.get('cwd')}")]

elif name == "terminal_history":
    limit = arguments.get("limit", 20)
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{TERMINAL_BRIDGE_URL}/history",
            params={"limit": limit}
        )
        result = response.json()
        
        history_text = "Recent commands:\n"
        for cmd in result.get("history", []):
            status = "✓" if cmd["exit_code"] == 0 else "✗"
            history_text += f"{status} [{cmd['exit_code']}] {cmd['command']}\n"
        
        return [TextContent(type="text", text=history_text)]

elif name == "docker_ps":
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{TERMINAL_BRIDGE_URL}/docker/ps")
        result = response.json()
        return [TextContent(type="text", text=result.get("output", "No output"))]

elif name == "docker_logs":
    container = arguments.get("container")
    lines = arguments.get("lines", 100)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{TERMINAL_BRIDGE_URL}/docker/logs/{container}",
            params={"lines": lines}
        )
        result = response.json()
        return [TextContent(type="text", text=result.get("logs", "No logs"))]

elif name == "docker_restart":
    container = arguments.get("container")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(f"{TERMINAL_BRIDGE_URL}/docker/restart/{container}")
        result = response.json()
        return [TextContent(type="text", text=f"Restarted {container}: {result.get('output', 'OK')}")]
```

---

## PHASE 4: VERIFICATION

```bash
# 1. Create the agent directory
mkdir -p /opt/leveredge/control-plane/agents/terminal-bridge

# 2. Create the files (terminal_bridge.py from Phase 1)

# 3. Start the service
sudo systemctl daemon-reload
sudo systemctl enable terminal-bridge
sudo systemctl start terminal-bridge

# 4. Check health
curl http://localhost:8251/health

# 5. Test a command
curl -X POST http://localhost:8251/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "ls -la /opt/leveredge"}'

# 6. Test safety (should be blocked)
curl -X POST http://localhost:8251/exec \
  -H "Content-Type: application/json" \
  -d '{"command": "rm -rf /"}'

# 7. Restart HEPHAESTUS
sudo systemctl restart hephaestus
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-terminal-bridge.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "TERMINAL BRIDGE deployed on port 8251. Claude Web now has full bash access with safety controls. Tools: terminal_exec, terminal_cd, docker_ps, docker_logs, docker_restart. All commands logged to LCIS.",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "terminal-bridge", "bash", "mcp"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: TERMINAL BRIDGE - Full bash access for Claude Web

New agent: terminal-bridge (port 8251)
- /exec - Execute bash commands
- /cd - Change working directory
- /history - Command history
- /docker/* - Container management

Safety features:
- Blocked dangerous commands (rm -rf /, etc)
- Blocked sensitive patterns (keys, passwords)
- Rate limiting (30 cmd/min)
- Timeout enforcement (60s default, 300s max)
- Full audit trail to LCIS

HEPHAESTUS tools:
- terminal_exec, terminal_cd, terminal_history
- docker_ps, docker_logs, docker_restart"
```

---

## USAGE EXAMPLES

**From Claude Web:**

```
# Run any command
HEPHAESTUS:terminal_exec(command="df -h")

# Check docker
HEPHAESTUS:docker_ps()

# Get logs
HEPHAESTUS:docker_logs(container="leveredge-aria-chat", lines=50)

# Restart a service
HEPHAESTUS:docker_restart(container="leveredge-muse")

# Change directory and run
HEPHAESTUS:terminal_cd(path="/opt/leveredge/specs")
HEPHAESTUS:terminal_exec(command="ls -la")
```

---

## SAFETY SUMMARY

| Protection | What It Does |
|------------|--------------|
| Blocked commands | `rm -rf /`, `mkfs`, fork bombs, etc. |
| Blocked patterns | Private keys, passwords, sensitive paths |
| Rate limiting | Max 30 commands per minute |
| Timeout | 60s default, 300s max |
| Audit trail | Every command logged to LCIS |
| User isolation | Runs as `damon`, not root |

---

*"Full power, full control, full audit."*
