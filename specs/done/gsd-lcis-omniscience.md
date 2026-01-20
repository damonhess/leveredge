# GSD: LCIS OMNISCIENCE - Active Learning & Mandatory Consultation

**Priority:** CRITICAL
**Estimated Time:** 45-60 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Transform LCIS from passive storage to active intelligence:
1. **WATCH EVERYTHING** - Logs, errors, events, changes
2. **MANDATORY CONSULTATION** - All agents MUST check LCIS before builds/edits
3. **AUTO-CAPTURE** - Every fix, failure, and pattern automatically ingested
4. **PREVENT REPEAT MISTAKES** - Block actions that match known failure patterns

---

## THE PROBLEM

Current LCIS is passive:
- Only captures git commits with `fix:` prefix
- Requires manual `/ingest` calls
- No real-time monitoring
- Agents don't consult before acting
- Same mistakes repeat because knowledge isn't applied

**Result:** We debug the same issues repeatedly. Knowledge captured but never used.

---

## THE SOLUTION: LCIS V2 - OMNISCIENT MODE

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LCIS V2                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  WATCHER    │  │  ORACLE     │  │  ENFORCER   │              │
│  │  (Ingest)   │  │  (Consult)  │  │  (Block)    │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    KNOWLEDGE BASE                        │    │
│  │  - lessons (patterns, fixes, failures)                   │    │
│  │  - rules (mandatory checks, blockers)                    │    │
│  │  - context (recent activity, agent state)                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
   ┌─────────┐          ┌─────────┐          ┌─────────┐
   │ Docker  │          │ Event   │          │ Agents  │
   │ Logs    │          │ Bus     │          │ (all)   │
   └─────────┘          └─────────┘          └─────────┘
```

---

## PHASE 1: LCIS WATCHER - INGEST EVERYTHING

### 1.1 Create Watcher Service

Add to `/opt/leveredge/control-plane/agents/lcis-librarian/watcher.py`:

```python
#!/usr/bin/env python3
"""
LCIS Watcher - Active monitoring and auto-ingestion

Monitors:
- Docker container logs (errors, restarts, failures)
- Event Bus events (all agent activity)
- Git commits and changes
- File system changes in critical paths
- Claude Code session outputs
"""

import os
import sys
import re
import json
import asyncio
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List
import subprocess

LCIS_URL = os.getenv("LCIS_URL", "http://localhost:8050")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://localhost:8099")

# =============================================================================
# PATTERNS TO DETECT
# =============================================================================

ERROR_PATTERNS = [
    # Python errors
    (r"Traceback \(most recent call last\)", "python_traceback"),
    (r"Error: (.+)", "generic_error"),
    (r"Exception: (.+)", "exception"),
    (r"ModuleNotFoundError: (.+)", "import_error"),
    (r"ConnectionRefusedError", "connection_error"),
    (r"TimeoutError", "timeout"),
    
    # Docker errors
    (r"container .+ exited with code [1-9]", "container_crash"),
    (r"OOMKilled", "memory_exceeded"),
    (r"failed to start container", "container_start_fail"),
    
    # Database errors
    (r"duplicate key value violates", "db_duplicate_key"),
    (r"relation .+ does not exist", "db_missing_table"),
    (r"column .+ does not exist", "db_missing_column"),
    
    # API errors
    (r"401 Unauthorized", "auth_error"),
    (r"403 Forbidden", "permission_error"),
    (r"404 Not Found", "not_found"),
    (r"500 Internal Server Error", "server_error"),
    
    # React/Frontend errors
    (r"Cannot read properties of undefined", "js_undefined"),
    (r"state update .+ unmounted component", "react_unmounted"),
    (r"Maximum update depth exceeded", "react_infinite_loop"),
]

FIX_PATTERNS = [
    (r"fixed:? (.+)", "fix_committed"),
    (r"resolved:? (.+)", "issue_resolved"),
    (r"the (?:issue|problem|bug) was (.+)", "root_cause"),
    (r"solution:? (.+)", "solution_found"),
    (r"(?:wrong|incorrect):? (.+) (?:should be|replaced with) (.+)", "correction"),
]

# =============================================================================
# WATCHER FUNCTIONS
# =============================================================================

async def ingest_lesson(content: str, domain: str, lesson_type: str, 
                       tags: List[str], source: str, context: Dict = None):
    """Send lesson to LCIS"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{LCIS_URL}/lessons",
                json={
                    "content": content,
                    "domain": domain,
                    "type": lesson_type,
                    "source_agent": source,
                    "tags": tags,
                    "context": context or {},
                    "auto_captured": True,
                    "captured_at": datetime.utcnow().isoformat()
                }
            )
            print(f"[LCIS] Ingested: {content[:80]}...")
    except Exception as e:
        print(f"[LCIS] Ingest failed: {e}")

async def watch_docker_logs():
    """Monitor all Docker container logs"""
    print("[WATCHER] Starting Docker log monitor...")
    
    # Get all leveredge containers
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=leveredge", "--format", "{{.Names}}"],
        capture_output=True, text=True
    )
    containers = result.stdout.strip().split('\n')
    
    for container in containers:
        if container:
            asyncio.create_task(watch_container(container))

async def watch_container(container_name: str):
    """Watch a single container's logs"""
    process = await asyncio.create_subprocess_exec(
        "docker", "logs", "-f", "--tail", "0", container_name,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    async def read_stream(stream, is_stderr=False):
        while True:
            line = await stream.readline()
            if not line:
                break
            line = line.decode('utf-8', errors='ignore').strip()
            await process_log_line(container_name, line, is_stderr)
    
    await asyncio.gather(
        read_stream(process.stdout),
        read_stream(process.stderr, True)
    )

async def process_log_line(container: str, line: str, is_error: bool):
    """Process a log line for patterns"""
    for pattern, error_type in ERROR_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            await ingest_lesson(
                content=f"[{container}] {error_type}: {line[:200]}",
                domain=container.replace("leveredge-", "").upper(),
                lesson_type="error",
                tags=[error_type, "auto-captured", "docker-log"],
                source="LCIS-WATCHER",
                context={"container": container, "full_line": line}
            )
            break
    
    # Also check for fixes mentioned in logs
    for pattern, fix_type in FIX_PATTERNS:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            await ingest_lesson(
                content=f"[{container}] {fix_type}: {match.group(1)}",
                domain=container.replace("leveredge-", "").upper(),
                lesson_type="fix",
                tags=[fix_type, "auto-captured", "docker-log"],
                source="LCIS-WATCHER"
            )
            break

async def watch_event_bus():
    """Subscribe to Event Bus for all agent activity"""
    print("[WATCHER] Starting Event Bus monitor...")
    
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{EVENT_BUS_URL}/subscribe") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            event = json.loads(line[5:])
                            await process_event(event)
        except Exception as e:
            print(f"[WATCHER] Event Bus connection lost: {e}")
            await asyncio.sleep(5)

async def process_event(event: Dict):
    """Process an event from the Event Bus"""
    event_type = event.get("event_type", "")
    source = event.get("source", "UNKNOWN")
    data = event.get("data", {})
    
    # Capture significant events
    significant_events = [
        "deployment_failed", "deployment_completed",
        "backup_created", "rollback_executed",
        "health_check_failed", "error_detected",
        "build_completed", "build_failed",
        "migration_applied", "migration_failed"
    ]
    
    if event_type in significant_events:
        await ingest_lesson(
            content=f"[{source}] {event_type}: {json.dumps(data)[:200]}",
            domain=source,
            lesson_type="success" if "completed" in event_type else "failure",
            tags=[event_type, "event-bus", "auto-captured"],
            source="LCIS-WATCHER",
            context=data
        )

async def watch_git_commits():
    """Monitor git commits for lessons"""
    print("[WATCHER] Starting Git monitor...")
    
    last_commit = None
    repo_path = "/opt/leveredge"
    
    while True:
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "log", "-1", "--format=%H|%s|%b"],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split("|")
                commit_hash = parts[0]
                subject = parts[1] if len(parts) > 1 else ""
                body = parts[2] if len(parts) > 2 else ""
                
                if commit_hash != last_commit:
                    last_commit = commit_hash
                    
                    # Determine type from commit message
                    if subject.startswith("fix:") or subject.startswith("fix("):
                        await ingest_lesson(
                            content=f"Git fix: {subject} - {body[:200]}",
                            domain="GIT",
                            lesson_type="fix",
                            tags=["git-commit", "fix", "auto-captured"],
                            source="LCIS-WATCHER",
                            context={"commit": commit_hash}
                        )
                    elif "fail" in subject.lower() or "error" in subject.lower():
                        await ingest_lesson(
                            content=f"Git failure note: {subject}",
                            domain="GIT",
                            lesson_type="failure",
                            tags=["git-commit", "failure", "auto-captured"],
                            source="LCIS-WATCHER"
                        )
        except Exception as e:
            print(f"[WATCHER] Git monitor error: {e}")
        
        await asyncio.sleep(10)

async def watch_file_changes():
    """Monitor critical file changes"""
    # Uses inotify on Linux to watch for changes
    # TODO: Implement with watchdog or inotify
    pass

# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run all watchers"""
    print("[LCIS WATCHER] Starting omniscient monitoring...")
    
    await asyncio.gather(
        watch_docker_logs(),
        watch_event_bus(),
        watch_git_commits(),
        # watch_file_changes(),  # TODO
    )

if __name__ == "__main__":
    asyncio.run(main())
```

### 1.2 Watcher Dockerfile

Add `Dockerfile.watcher` to lcis-librarian:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI for log watching
RUN apt-get update && apt-get install -y \
    curl \
    docker.io \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY watcher.py .

CMD ["python", "watcher.py"]
```

### 1.3 Add to Docker Compose

```yaml
  lcis-watcher:
    build:
      context: ./control-plane/agents/lcis-librarian
      dockerfile: Dockerfile.watcher
    container_name: leveredge-lcis-watcher
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock  # Access to Docker logs
      - /opt/leveredge:/opt/leveredge:ro  # Read-only access to repo
    environment:
      - LCIS_URL=http://lcis-librarian:8050
      - EVENT_BUS_URL=http://event-bus:8099
    networks:
      - leveredge-network
    depends_on:
      - lcis-librarian
      - event-bus
    restart: unless-stopped
    profiles:
      - all
      - core
```

---

## PHASE 2: MANDATORY CONSULTATION - PRE-ACTION CHECKS

### 2.1 Add Consultation Endpoint to LCIS

Add to `lcis_librarian.py`:

```python
@app.post("/consult")
async def consult_before_action(request: ConsultRequest):
    """
    MANDATORY check before any build, edit, or deployment.
    
    Returns:
    - relevant_lessons: Past experiences related to this action
    - warnings: Known issues or failure patterns to watch for
    - recommendations: Suggested approaches based on history
    - blockers: If any, action should NOT proceed
    """
    
    # Search for relevant lessons
    relevant = await search_lessons(
        query=f"{request.action} {request.target} {request.context}",
        limit=10
    )
    
    # Check for known failure patterns
    failures = await get_failures_for_target(request.target)
    
    # Check for rules/blockers
    blockers = await check_blockers(request.action, request.target)
    
    # Generate recommendations
    recommendations = await generate_recommendations(
        action=request.action,
        target=request.target,
        lessons=relevant,
        failures=failures
    )
    
    return {
        "consultation_id": generate_id(),
        "action": request.action,
        "target": request.target,
        "relevant_lessons": relevant,
        "warnings": [f.content for f in failures if f.type == "failure"],
        "recommendations": recommendations,
        "blockers": blockers,
        "proceed": len(blockers) == 0,
        "must_acknowledge": len(blockers) > 0 or len(failures) > 3
    }

class ConsultRequest(BaseModel):
    action: str  # "build", "edit", "deploy", "delete", "create"
    target: str  # Service/file/agent being acted upon
    context: Optional[str] = None  # Additional context
    agent: str  # Which agent is asking
```

### 2.2 Add Blocker Rules Table

```sql
-- lcis_rules table for mandatory checks
CREATE TABLE IF NOT EXISTS lcis_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_type TEXT NOT NULL,  -- 'blocker', 'warning', 'recommendation'
    pattern TEXT NOT NULL,     -- Regex or keyword pattern
    target_pattern TEXT,       -- What targets this applies to
    message TEXT NOT NULL,     -- What to tell the agent
    severity TEXT DEFAULT 'warning',  -- 'critical', 'warning', 'info'
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    times_triggered INTEGER DEFAULT 0
);

-- Insert critical rules
INSERT INTO lcis_rules (rule_type, pattern, target_pattern, message, severity) VALUES
('blocker', 'deploy.*prod', '.*', 'Direct PROD deployment blocked. Use APOLLO /promote instead.', 'critical'),
('blocker', 'edit.*/data-plane/prod/', '.*', 'Direct PROD file edit blocked. Edit DEV first, then promote.', 'critical'),
('warning', 'edit.*docker-compose', '.*', 'Docker compose changes require fleet restart.', 'warning'),
('warning', 'edit.*\.env', '.*', 'Environment file changes may require service restart.', 'warning'),
('warning', 'delete', '.*', 'Deletion is permanent. Ensure backup exists.', 'warning'),
('recommendation', 'build.*agent', '.*', 'Check AGENT-REGISTRY.md for port conflicts before building.', 'info'),
('recommendation', 'edit.*supabase', '.*', 'Run migrations in DEV first. Check 20260120_* files for recent schema.', 'info');
```

---

## PHASE 3: AGENT INTEGRATION - FORCED CONSULTATION

### 3.1 Shared Consultation Module

Create `/opt/leveredge/control-plane/shared/lcis_client.py`:

```python
"""
LCIS Client - Mandatory consultation before any action

ALL AGENTS MUST USE THIS before:
- Building anything
- Editing files
- Deploying services
- Creating resources
- Deleting anything

Usage:
    from lcis_client import consult, must_consult

    @must_consult("build", "my-service")
    async def build_service():
        ...
    
    # Or manually:
    result = await consult("edit", "/path/to/file", "Adding feature X")
    if not result.proceed:
        raise BlockedByLCIS(result.blockers)
"""

import os
import httpx
import functools
from dataclasses import dataclass
from typing import Optional, List, Callable, Any

LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")

@dataclass
class ConsultationResult:
    consultation_id: str
    proceed: bool
    blockers: List[str]
    warnings: List[str]
    recommendations: List[str]
    relevant_lessons: List[dict]
    must_acknowledge: bool

class BlockedByLCIS(Exception):
    """Raised when LCIS blocks an action"""
    def __init__(self, blockers: List[str]):
        self.blockers = blockers
        super().__init__(f"Action blocked by LCIS: {blockers}")

async def consult(action: str, target: str, context: str = None, 
                  agent: str = "UNKNOWN") -> ConsultationResult:
    """
    Consult LCIS before taking an action.
    
    Args:
        action: What you're doing (build, edit, deploy, delete, create)
        target: What you're acting on (service name, file path, etc.)
        context: Additional context about why/what
        agent: Your agent name
    
    Returns:
        ConsultationResult with proceed flag and any warnings/blockers
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{LCIS_URL}/consult",
                json={
                    "action": action,
                    "target": target,
                    "context": context,
                    "agent": agent
                }
            )
            data = response.json()
            
            result = ConsultationResult(
                consultation_id=data.get("consultation_id", ""),
                proceed=data.get("proceed", True),
                blockers=data.get("blockers", []),
                warnings=data.get("warnings", []),
                recommendations=data.get("recommendations", []),
                relevant_lessons=data.get("relevant_lessons", []),
                must_acknowledge=data.get("must_acknowledge", False)
            )
            
            # Log consultation
            if result.warnings:
                print(f"[LCIS] Warnings for {action} {target}:")
                for w in result.warnings:
                    print(f"  ⚠️  {w}")
            
            if result.recommendations:
                print(f"[LCIS] Recommendations:")
                for r in result.recommendations:
                    print(f"  💡 {r}")
            
            return result
            
    except Exception as e:
        # If LCIS is down, log but don't block
        print(f"[LCIS] Consultation failed (proceeding with caution): {e}")
        return ConsultationResult(
            consultation_id="offline",
            proceed=True,
            blockers=[],
            warnings=["LCIS offline - proceeding without consultation"],
            recommendations=[],
            relevant_lessons=[],
            must_acknowledge=False
        )

def must_consult(action: str, target: str):
    """
    Decorator that forces LCIS consultation before function execution.
    
    Usage:
        @must_consult("build", "my-agent")
        async def build_my_agent():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            agent_name = kwargs.get("agent", func.__module__.split(".")[-1].upper())
            context = kwargs.get("context", func.__doc__ or "")
            
            result = await consult(action, target, context, agent_name)
            
            if not result.proceed:
                raise BlockedByLCIS(result.blockers)
            
            if result.must_acknowledge:
                # In automated context, log the acknowledgment
                print(f"[LCIS] Acknowledged {len(result.warnings)} warnings for {action} {target}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

async def report_outcome(consultation_id: str, success: bool, 
                         notes: str = None, error: str = None):
    """
    Report the outcome of an action back to LCIS.
    This closes the loop and enables learning.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{LCIS_URL}/outcome",
                json={
                    "consultation_id": consultation_id,
                    "success": success,
                    "notes": notes,
                    "error": error,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
    except:
        pass

# Convenience functions for common actions
async def before_build(target: str, agent: str) -> ConsultationResult:
    return await consult("build", target, agent=agent)

async def before_edit(filepath: str, agent: str) -> ConsultationResult:
    return await consult("edit", filepath, agent=agent)

async def before_deploy(service: str, env: str, agent: str) -> ConsultationResult:
    return await consult("deploy", f"{service}:{env}", agent=agent)

async def before_delete(target: str, agent: str) -> ConsultationResult:
    return await consult("delete", target, agent=agent)
```

### 3.2 Update HEPHAESTUS to Consult LCIS

Add to HEPHAESTUS before any file operation:

```python
from lcis_client import consult, report_outcome, BlockedByLCIS

async def create_file(path: str, content: str, agent: str = "HEPHAESTUS"):
    """Create file with LCIS consultation"""
    
    # Consult LCIS first
    result = await consult("create", path, f"Creating file with {len(content)} bytes", agent)
    
    if not result.proceed:
        raise BlockedByLCIS(result.blockers)
    
    # Show warnings
    for warning in result.warnings:
        print(f"⚠️ LCIS Warning: {warning}")
    
    # Proceed with creation
    try:
        with open(path, 'w') as f:
            f.write(content)
        
        await report_outcome(result.consultation_id, success=True)
        return {"status": "created", "path": path}
        
    except Exception as e:
        await report_outcome(result.consultation_id, success=False, error=str(e))
        raise
```

### 3.3 Update APOLLO to Consult LCIS

Add to APOLLO before deployments:

```python
from lcis_client import consult, report_outcome, BlockedByLCIS

async def execute_deployment(service: str, env: str, ...):
    """Execute deployment with LCIS consultation"""
    
    # Mandatory consultation
    result = await consult("deploy", f"{service}:{env}", 
                          f"Deploying {service} to {env}", "APOLLO")
    
    if not result.proceed:
        raise HTTPException(
            status_code=403,
            detail=f"Deployment blocked by LCIS: {result.blockers}"
        )
    
    # Show relevant past deployment issues
    if result.relevant_lessons:
        print(f"[LCIS] {len(result.relevant_lessons)} relevant past experiences found")
        for lesson in result.relevant_lessons[:3]:
            print(f"  📚 {lesson.get('content', '')[:100]}...")
    
    # Proceed with deployment...
    try:
        # ... deployment logic ...
        await report_outcome(result.consultation_id, success=True)
    except Exception as e:
        await report_outcome(result.consultation_id, success=False, error=str(e))
        raise
```

---

## PHASE 4: CLAUDE CODE INTEGRATION

### 4.1 Pre-GSD Check

Add to GSD execution flow - before running any GSD, consult LCIS:

```python
async def execute_gsd(spec_path: str):
    """Execute a GSD with LCIS consultation"""
    
    # Extract target from spec
    spec_content = read_file(spec_path)
    target = extract_target_from_spec(spec_content)
    
    # Consult LCIS
    result = await consult("build", target, f"Executing GSD: {spec_path}", "CLAUDE_CODE")
    
    if not result.proceed:
        return f"❌ GSD blocked by LCIS:\n" + "\n".join(result.blockers)
    
    # Show relevant lessons
    if result.relevant_lessons:
        print("\n📚 LCIS found relevant past experiences:")
        for lesson in result.relevant_lessons:
            print(f"  - {lesson['content'][:100]}...")
    
    # Show warnings
    if result.warnings:
        print("\n⚠️ LCIS Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    
    # Proceed with GSD...
```

### 4.2 Post-Session Capture

Add session capture for Claude Code/Claude Web:

```python
async def capture_session(session_content: str, outcome: str):
    """Capture learnings from a Claude session"""
    
    # Extract patterns
    errors_found = extract_errors(session_content)
    fixes_applied = extract_fixes(session_content)
    
    # Ingest each learning
    for error in errors_found:
        await ingest_lesson(
            content=f"Session error: {error}",
            domain="CLAUDE_SESSION",
            lesson_type="error",
            tags=["claude-session", "auto-captured"],
            source="SESSION-CAPTURE"
        )
    
    for fix in fixes_applied:
        await ingest_lesson(
            content=f"Session fix: {fix}",
            domain="CLAUDE_SESSION",
            lesson_type="fix",
            tags=["claude-session", "auto-captured"],
            source="SESSION-CAPTURE"
        )
```

---

## PHASE 5: RULES & ENFORCEMENT

### 5.1 Critical Rules to Add

```sql
-- Block dangerous patterns
INSERT INTO lcis_rules (rule_type, pattern, target_pattern, message, severity) VALUES

-- Direct PROD access
('blocker', 'edit.*/data-plane/prod/', '.*', 
 'BLOCKED: Direct PROD edit. Use DEV → promote workflow.', 'critical'),

('blocker', 'create.*/data-plane/prod/', '.*', 
 'BLOCKED: Direct PROD creation. Create in DEV first.', 'critical'),

('blocker', 'deploy.*:prod', '(?!APOLLO).*', 
 'BLOCKED: Only APOLLO can deploy to PROD.', 'critical'),

-- Dangerous operations
('blocker', 'delete.*/opt/leveredge/(?!specs/archive)', '.*',
 'BLOCKED: Deletion of core files. Move to archive instead.', 'critical'),

('blocker', 'edit.*\.env\.fleet', '.*',
 'BLOCKED: Fleet env changes require AEGIS. Use AEGIS to update secrets.', 'critical'),

-- Warnings for risky operations
('warning', 'edit.*docker-compose', '.*',
 'Docker compose changes require: 1) Fleet restart 2) Check port conflicts', 'warning'),

('warning', 'build.*agent', '.*',
 'New agent: 1) Check port in AGENT-REGISTRY 2) Add to fleet compose 3) Create shared symlink', 'warning'),

('warning', 'edit.*migrations/', '.*',
 'Migration edit: 1) Test in DEV Supabase first 2) Backup before PROD', 'warning'),

-- Recommendations
('recommendation', 'edit.*frontend', '.*',
 'Frontend changes: Build in DEV, test at dev-*.leveredgeai.com, then promote', 'info'),

('recommendation', 'build.*api', '.*',
 'API changes: Update OpenAPI docs, add health endpoint, register with PANOPTES', 'info');
```

---

## PHASE 6: VERIFICATION ENDPOINTS

### 6.1 LCIS Status Dashboard

Add to LCIS:

```python
@app.get("/status")
async def lcis_status():
    """LCIS system status and statistics"""
    return {
        "status": "operational",
        "version": "2.0.0",
        "mode": "omniscient",
        "stats": {
            "total_lessons": await count_lessons(),
            "lessons_today": await count_lessons_today(),
            "errors_captured": await count_by_type("error"),
            "fixes_captured": await count_by_type("fix"),
            "consultations_today": await count_consultations_today(),
            "blocks_today": await count_blocks_today(),
            "active_rules": await count_active_rules()
        },
        "watchers": {
            "docker_logs": "active",
            "event_bus": "active",
            "git_commits": "active"
        },
        "last_capture": await get_last_capture_time()
    }

@app.get("/recent")
async def recent_activity(limit: int = 20):
    """Recent LCIS activity"""
    return {
        "lessons": await get_recent_lessons(limit),
        "consultations": await get_recent_consultations(limit),
        "blocks": await get_recent_blocks(limit)
    }
```

---

## VERIFICATION

```bash
# 1. Check LCIS Watcher is running
docker ps | grep lcis-watcher

# 2. Check LCIS status
curl http://localhost:8050/status

# 3. Test consultation (should pass)
curl -X POST http://localhost:8050/consult \
  -H "Content-Type: application/json" \
  -d '{"action": "build", "target": "test-service", "agent": "TEST"}'

# 4. Test blocker (should fail)
curl -X POST http://localhost:8050/consult \
  -H "Content-Type: application/json" \
  -d '{"action": "edit", "target": "/data-plane/prod/something", "agent": "TEST"}'
# Expected: proceed: false, blockers: ["BLOCKED: Direct PROD edit..."]

# 5. Check recent captures
curl http://localhost:8050/recent

# 6. Trigger an error in a container, verify it's captured
docker logs leveredge-test-agent 2>&1 | grep -i error
curl http://localhost:8050/lessons?type=error&limit=5
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-lcis-omniscience.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS (meta!)
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "LCIS V2 OMNISCIENCE deployed: Active watchers for Docker/EventBus/Git, mandatory consultation before all builds/edits/deploys, automatic error/fix capture, blocker rules for PROD protection",
    "domain": "LCIS",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "lcis", "omniscience", "learning-system"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: LCIS V2 OMNISCIENCE - Active learning system

- Watcher service monitors Docker logs, Event Bus, Git commits
- Mandatory consultation before any build/edit/deploy
- Blocker rules prevent direct PROD access
- Auto-capture of errors and fixes
- Shared lcis_client.py for all agents
- Outcome reporting closes the feedback loop

The system now learns from EVERYTHING."
```

---

## SUMMARY

After this build, LCIS will:

| Capability | Before | After |
|------------|--------|-------|
| **Capture errors** | Manual only | Auto from Docker logs |
| **Capture fixes** | git commit hook | Auto from all sources |
| **Pre-action check** | None | Mandatory consultation |
| **Block dangerous ops** | None | Rules-based blocking |
| **Learn from sessions** | Never | Auto-capture patterns |
| **Apply learnings** | Never | Recommendations on consult |

**No more repeat mistakes. The system learns and enforces.**

---

*"Those who cannot remember the past are condemned to repeat it." - LCIS now remembers everything.*
