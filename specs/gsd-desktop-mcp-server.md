# GSD: Claude Desktop MCP Server (Laptop → VPS)

**Priority:** HIGH
**Time:** ~30 min
**Location:** `C:\Users\damon\OneDrive\Documents\Projects\leveredge-desktop-mcp\`
**Purpose:** Let Claude Desktop command your VPS via MCP, all on Max subscription

---

## WHAT THIS DOES

```
Claude Desktop (laptop, Max)
    │
    ▼
MCP Server (Python, laptop)
    │
    ├─► SSH to VPS (run commands, read/write files)
    ├─► Coach Channel (send instructions, receive responses)
    ├─► Council Guest (join meetings, speak, vote)
    └─► Direct Supabase queries (portfolio, knowledge)
```

**All Max. No API credits.**

---

## PHASE 1: PROJECT SETUP

Create on your laptop:

```
C:\Users\damon\OneDrive\Documents\Projects\leveredge-desktop-mcp\
├── server.py           # Main MCP server
├── ssh_tools.py        # VPS SSH operations
├── coach_channel.py    # Coach Channel tools
├── council_tools.py    # Council guest tools
├── supabase_tools.py   # Direct DB queries
├── config.py           # Connection settings
├── requirements.txt
└── README.md
```

---

## PHASE 2: DEPENDENCIES

**requirements.txt:**
```
mcp
paramiko
asyncpg
httpx
python-dotenv
```

---

## PHASE 3: CONFIG

**config.py:**
```python
import os
from dotenv import load_dotenv

load_dotenv()

# VPS SSH
VPS_HOST = os.getenv("VPS_HOST", "your-vps-ip")
VPS_USER = os.getenv("VPS_USER", "damon")
VPS_KEY_PATH = os.getenv("VPS_KEY_PATH", r"C:\Users\damon\.ssh\id_rsa")

# Supabase (PROD)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Database direct (for Coach Channel, Council)
DATABASE_URL = os.getenv("DATABASE_URL")  # postgresql://...

# Guest identity
GUEST_NAME = "DESKTOP_COACH"
```

**.env (create this, don't commit):**
```
VPS_HOST=xxx.xxx.xxx.xxx
VPS_USER=damon
VPS_KEY_PATH=C:\Users\damon\.ssh\id_rsa
DATABASE_URL=postgresql://postgres:PASSWORD@xxx.xxx.xxx.xxx:54322/postgres
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key
```

---

## PHASE 4: SSH TOOLS

**ssh_tools.py:**
```python
import paramiko
from config import VPS_HOST, VPS_USER, VPS_KEY_PATH

def get_ssh_client():
    """Create SSH connection to VPS."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=VPS_HOST,
        username=VPS_USER,
        key_filename=VPS_KEY_PATH
    )
    return client

def run_command(command: str, working_dir: str = "/opt/leveredge") -> dict:
    """Run a command on the VPS."""
    client = get_ssh_client()
    try:
        full_cmd = f"cd {working_dir} && {command}"
        stdin, stdout, stderr = client.exec_command(full_cmd)
        return {
            "stdout": stdout.read().decode(),
            "stderr": stderr.read().decode(),
            "exit_code": stdout.channel.recv_exit_status()
        }
    finally:
        client.close()

def read_file(path: str) -> str:
    """Read a file from VPS."""
    result = run_command(f"cat {path}")
    if result["exit_code"] != 0:
        raise Exception(f"Failed to read {path}: {result['stderr']}")
    return result["stdout"]

def write_file(path: str, content: str) -> dict:
    """Write content to a file on VPS."""
    # Escape content for shell
    import shlex
    escaped = shlex.quote(content)
    result = run_command(f"echo {escaped} > {path}")
    return {"status": "written", "path": path}

def list_directory(path: str) -> list:
    """List directory contents on VPS."""
    result = run_command(f"ls -la {path}")
    return result["stdout"].split("\n")

def docker_ps() -> str:
    """Get running containers."""
    result = run_command("docker ps --format 'table {{.Names}}\t{{.Status}}'")
    return result["stdout"]

def docker_logs(container: str, tail: int = 50) -> str:
    """Get container logs."""
    result = run_command(f"docker logs {container} --tail {tail} 2>&1")
    return result["stdout"]

def git_status() -> str:
    """Get git status."""
    result = run_command("git status --short")
    return result["stdout"]

def git_log(n: int = 10) -> str:
    """Get recent commits."""
    result = run_command(f"git log --oneline -n {n}")
    return result["stdout"]
```

---

## PHASE 5: COACH CHANNEL TOOLS

**coach_channel.py:**
```python
import asyncpg
import asyncio
from config import DATABASE_URL, GUEST_NAME
from datetime import datetime
import json

async def get_pool():
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

async def coach_send(
    message: str,
    message_type: str = "instruction",
    subject: str = None,
    to_agent: str = "CLAUDE_CODE"
) -> dict:
    """Send instruction to Claude Code or other agent."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO coach_channel 
            (from_agent, to_agent, message_type, subject, content)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, created_at
        """, GUEST_NAME, to_agent, message_type, subject, message)
        
        return {
            "status": "sent",
            "message_id": str(row['id']),
            "to": to_agent,
            "created_at": row['created_at'].isoformat()
        }

async def coach_receive(limit: int = 10, status: str = "pending") -> dict:
    """Receive messages sent to DESKTOP_COACH."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, from_agent, message_type, subject, content, 
                   context, reference_id, status, created_at
            FROM coach_channel
            WHERE to_agent = $1
            AND ($2 = 'all' OR status = $2)
            ORDER BY created_at DESC
            LIMIT $3
        """, GUEST_NAME, status, limit)
        
        messages = [dict(r) for r in rows]
        
        # Mark as read
        if messages:
            ids = [m['id'] for m in messages if m['status'] == 'pending']
            if ids:
                await conn.execute("""
                    UPDATE coach_channel
                    SET status = 'read', read_at = NOW()
                    WHERE id = ANY($1::uuid[])
                """, ids)
        
        return {"messages": messages, "count": len(messages)}

async def coach_status() -> dict:
    """Get coach channel status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        unread = await conn.fetchval("""
            SELECT COUNT(*) FROM coach_channel 
            WHERE to_agent = $1 AND status = 'pending'
        """, GUEST_NAME)
        
        recent = await conn.fetch("""
            SELECT from_agent, message_type, subject, created_at
            FROM coach_channel
            WHERE to_agent = $1
            ORDER BY created_at DESC
            LIMIT 5
        """, GUEST_NAME)
        
        return {
            "unread": unread,
            "recent": [dict(r) for r in recent]
        }

# Sync wrappers for MCP
def send_sync(message, message_type="instruction", subject=None, to_agent="CLAUDE_CODE"):
    return asyncio.run(coach_send(message, message_type, subject, to_agent))

def receive_sync(limit=10, status="pending"):
    return asyncio.run(coach_receive(limit, status))

def status_sync():
    return asyncio.run(coach_status())
```

---

## PHASE 6: COUNCIL TOOLS

**council_tools.py:**
```python
import asyncpg
import asyncio
from config import DATABASE_URL, GUEST_NAME
import json

async def get_pool():
    return await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

async def council_list_meetings(status: str = "active") -> list:
    """List council meetings I'm invited to."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, topic, status, created_at
            FROM council_meetings
            WHERE $1 = ANY(invited_guests) OR invited_guests IS NULL
            AND status = $2
            ORDER BY created_at DESC
            LIMIT 10
        """, GUEST_NAME, status)
        return [dict(r) for r in rows]

async def council_join(meeting_id: str) -> dict:
    """Join a council meeting as guest."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO council_guests (meeting_id, guest_name, status)
            VALUES ($1::uuid, $2, 'active')
            RETURNING id
        """, meeting_id, GUEST_NAME)
        return {"guest_id": str(row['id']), "status": "joined"}

async def council_speak(meeting_id: str, message: str) -> dict:
    """Contribute to council discussion."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO council_transcript (meeting_id, speaker, content, speaker_type)
            VALUES ($1::uuid, $2, $3, 'guest')
        """, meeting_id, GUEST_NAME, message)
        return {"status": "recorded", "speaker": GUEST_NAME}

async def council_listen(meeting_id: str, since_id: str = None) -> list:
    """Get recent council discussion."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if since_id:
            rows = await conn.fetch("""
                SELECT id, speaker, content, speaker_type, created_at
                FROM council_transcript
                WHERE meeting_id = $1::uuid AND id > $2::uuid
                ORDER BY created_at ASC
            """, meeting_id, since_id)
        else:
            rows = await conn.fetch("""
                SELECT id, speaker, content, speaker_type, created_at
                FROM council_transcript
                WHERE meeting_id = $1::uuid
                ORDER BY created_at DESC
                LIMIT 20
            """, meeting_id)
        return [dict(r) for r in rows]

async def council_vote(meeting_id: str, decision_id: str, vote: str, rationale: str = None) -> dict:
    """Cast advisory vote on a decision."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO council_votes (meeting_id, decision_id, voter, vote, rationale, voter_type)
            VALUES ($1::uuid, $2::uuid, $3, $4, $5, 'guest')
        """, meeting_id, decision_id, GUEST_NAME, vote, rationale)
        return {"status": "voted", "vote": vote}

async def council_leave(meeting_id: str) -> dict:
    """Leave council meeting."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE council_guests
            SET status = 'left', left_at = NOW()
            WHERE meeting_id = $1::uuid AND guest_name = $2
        """, meeting_id, GUEST_NAME)
        return {"status": "left"}

# Sync wrappers
def list_meetings_sync(status="active"):
    return asyncio.run(council_list_meetings(status))

def join_sync(meeting_id):
    return asyncio.run(council_join(meeting_id))

def speak_sync(meeting_id, message):
    return asyncio.run(council_speak(meeting_id, message))

def listen_sync(meeting_id, since_id=None):
    return asyncio.run(council_listen(meeting_id, since_id))

def vote_sync(meeting_id, decision_id, vote, rationale=None):
    return asyncio.run(council_vote(meeting_id, decision_id, vote, rationale))

def leave_sync(meeting_id):
    return asyncio.run(council_leave(meeting_id))
```

---

## PHASE 7: MAIN MCP SERVER

**server.py:**
```python
#!/usr/bin/env python3
"""
LeverEdge Desktop MCP Server
Claude Desktop → VPS via SSH, Coach Channel, Council
"""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import json

import ssh_tools
import coach_channel
import council_tools

server = Server("leveredge-desktop")

# ============ SSH/VPS TOOLS ============

@server.tool()
async def vps_command(command: str, working_dir: str = "/opt/leveredge") -> str:
    """Run a command on the LeverEdge VPS."""
    result = ssh_tools.run_command(command, working_dir)
    return json.dumps(result, indent=2)

@server.tool()
async def vps_read_file(path: str) -> str:
    """Read a file from the VPS."""
    return ssh_tools.read_file(path)

@server.tool()
async def vps_write_file(path: str, content: str) -> str:
    """Write content to a file on the VPS."""
    result = ssh_tools.write_file(path, content)
    return json.dumps(result)

@server.tool()
async def vps_list_directory(path: str = "/opt/leveredge") -> str:
    """List directory contents on VPS."""
    result = ssh_tools.list_directory(path)
    return "\n".join(result)

@server.tool()
async def vps_docker_ps() -> str:
    """Get running Docker containers on VPS."""
    return ssh_tools.docker_ps()

@server.tool()
async def vps_docker_logs(container: str, tail: int = 50) -> str:
    """Get logs from a Docker container."""
    return ssh_tools.docker_logs(container, tail)

@server.tool()
async def vps_git_status() -> str:
    """Get git status of /opt/leveredge."""
    return ssh_tools.git_status()

@server.tool()
async def vps_git_log(n: int = 10) -> str:
    """Get recent git commits."""
    return ssh_tools.git_log(n)

# ============ COACH CHANNEL TOOLS ============

@server.tool()
async def coach_send(
    message: str,
    message_type: str = "instruction",
    subject: str = None,
    to_agent: str = "CLAUDE_CODE"
) -> str:
    """Send instruction to Claude Code or other agent via Coach Channel."""
    result = coach_channel.send_sync(message, message_type, subject, to_agent)
    return json.dumps(result, indent=2)

@server.tool()
async def coach_receive(limit: int = 10, status: str = "pending") -> str:
    """Receive messages from Coach Channel."""
    result = coach_channel.receive_sync(limit, status)
    return json.dumps(result, indent=2, default=str)

@server.tool()
async def coach_status() -> str:
    """Get Coach Channel status - unread count, recent messages."""
    result = coach_channel.status_sync()
    return json.dumps(result, indent=2, default=str)

# ============ COUNCIL TOOLS ============

@server.tool()
async def council_list_meetings(status: str = "active") -> str:
    """List council meetings I'm invited to."""
    result = council_tools.list_meetings_sync(status)
    return json.dumps(result, indent=2, default=str)

@server.tool()
async def council_join(meeting_id: str) -> str:
    """Join a council meeting as DESKTOP_COACH."""
    result = council_tools.join_sync(meeting_id)
    return json.dumps(result, indent=2)

@server.tool()
async def council_speak(meeting_id: str, message: str) -> str:
    """Contribute to council discussion."""
    result = council_tools.speak_sync(meeting_id, message)
    return json.dumps(result, indent=2)

@server.tool()
async def council_listen(meeting_id: str, since_id: str = None) -> str:
    """Get recent council discussion."""
    result = council_tools.listen_sync(meeting_id, since_id)
    return json.dumps(result, indent=2, default=str)

@server.tool()
async def council_vote(meeting_id: str, decision_id: str, vote: str, rationale: str = None) -> str:
    """Cast advisory vote on a council decision."""
    result = council_tools.vote_sync(meeting_id, decision_id, vote, rationale)
    return json.dumps(result, indent=2)

@server.tool()
async def council_leave(meeting_id: str) -> str:
    """Leave council meeting gracefully."""
    result = council_tools.leave_sync(meeting_id)
    return json.dumps(result, indent=2)

# ============ RUN SERVER ============

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## PHASE 8: CLAUDE DESKTOP CONFIG

Add to Claude Desktop's MCP config (usually `%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "leveredge": {
      "command": "python",
      "args": ["C:\\Users\\damon\\OneDrive\\Documents\\Projects\\leveredge-desktop-mcp\\server.py"],
      "env": {
        "VPS_HOST": "your-vps-ip",
        "VPS_USER": "damon",
        "VPS_KEY_PATH": "C:\\Users\\damon\\.ssh\\id_rsa",
        "DATABASE_URL": "postgresql://postgres:PASSWORD@your-vps-ip:54322/postgres"
      }
    }
  }
}
```

---

## PHASE 9: TEST

1. Install dependencies:
```powershell
cd C:\Users\damon\OneDrive\Documents\Projects\leveredge-desktop-mcp
pip install -r requirements.txt
```

2. Test SSH connection:
```powershell
python -c "from ssh_tools import docker_ps; print(docker_ps())"
```

3. Restart Claude Desktop

4. In Claude Desktop, try:
- "List the docker containers on my VPS"
- "Read /opt/leveredge/LESSONS-SCRATCH.md"
- "Check coach channel status"

---

## DELIVERABLES

- [ ] Project folder created
- [ ] All Python files written
- [ ] requirements.txt installed
- [ ] .env configured with VPS credentials
- [ ] SSH connection tested
- [ ] Claude Desktop config updated
- [ ] Tools working in Claude Desktop

---

## TOOLS SUMMARY

| Tool | Purpose |
|------|---------|
| vps_command | Run any command on VPS |
| vps_read_file | Read file from VPS |
| vps_write_file | Write file to VPS |
| vps_list_directory | List VPS directory |
| vps_docker_ps | Show running containers |
| vps_docker_logs | Get container logs |
| vps_git_status | Git status |
| vps_git_log | Recent commits |
| coach_send | Send instruction to Claude Code |
| coach_receive | Get responses |
| coach_status | Check unread messages |
| council_list_meetings | See available meetings |
| council_join | Join as guest |
| council_speak | Contribute to discussion |
| council_listen | Follow discussion |
| council_vote | Cast advisory vote |
| council_leave | Leave meeting |

---

**Claude Desktop becomes a full command center for LeverEdge. All on Max.**
