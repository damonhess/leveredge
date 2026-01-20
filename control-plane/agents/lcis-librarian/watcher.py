#!/usr/bin/env python3
"""
LCIS Watcher - Active monitoring and auto-ingestion
Port: (runs as background service, no HTTP)

Monitors:
- Docker container logs (errors, restarts, failures)
- Event Bus events (all agent activity)
- Git commits and changes
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
]

# Rate limiting - don't spam LCIS
RATE_LIMIT = {}
RATE_LIMIT_SECONDS = 60

# =============================================================================
# WATCHER FUNCTIONS
# =============================================================================

def should_rate_limit(key: str) -> bool:
    """Check if we should rate limit this capture"""
    now = datetime.utcnow()
    if key in RATE_LIMIT:
        last_time = RATE_LIMIT[key]
        if (now - last_time).total_seconds() < RATE_LIMIT_SECONDS:
            return True
    RATE_LIMIT[key] = now
    return False


async def ingest_lesson(content: str, domain: str, lesson_type: str,
                       tags: List[str], source: str, context: Dict = None,
                       severity: str = "medium"):
    """Send lesson to LCIS"""
    # Rate limit key based on content hash
    rate_key = f"{domain}:{lesson_type}:{hash(content[:100])}"
    if should_rate_limit(rate_key):
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{LCIS_URL}/ingest",
                json={
                    "content": content,
                    "domain": domain,
                    "type": lesson_type,
                    "source_agent": source,
                    "source_type": "watcher",
                    "tags": tags + ["auto-captured", "watcher"],
                    "source_context": context or {},
                    "severity": severity
                }
            )
            print(f"[LCIS] Ingested: {content[:80]}...")
    except Exception as e:
        print(f"[LCIS] Ingest failed: {e}")


async def watch_docker_logs():
    """Monitor all Docker container logs"""
    print("[WATCHER] Starting Docker log monitor...")

    while True:
        try:
            # Get all leveredge containers
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}"],
                capture_output=True, text=True
            )
            containers = [c for c in result.stdout.strip().split('\n') if c]

            # Create tasks for each container
            tasks = [watch_container(c) for c in containers if c]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            print(f"[WATCHER] Docker log monitor error: {e}")

        await asyncio.sleep(30)


async def watch_container(container_name: str):
    """Watch a single container's logs for a short time"""
    try:
        process = await asyncio.create_subprocess_exec(
            "docker", "logs", "--tail", "50", container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10)

        # Process stderr (where most errors go)
        if stderr:
            lines = stderr.decode('utf-8', errors='ignore').split('\n')
            for line in lines[-20:]:  # Last 20 lines only
                await process_log_line(container_name, line.strip(), True)

    except asyncio.TimeoutError:
        pass
    except Exception as e:
        print(f"[WATCHER] Error watching {container_name}: {e}")


async def process_log_line(container: str, line: str, is_error: bool):
    """Process a log line for patterns"""
    if not line or len(line) < 10:
        return

    for pattern, error_type in ERROR_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            # Map container to domain
            domain = "THE_KEEP"
            if "aria" in container.lower():
                domain = "ARIA_SANCTUM"
            elif any(x in container.lower() for x in ["varys", "chiron", "scholar"]):
                domain = "CHANCERY"
            elif any(x in container.lower() for x in ["aegis", "panoptes", "sentinel"]):
                domain = "SENTINELS"
            elif any(x in container.lower() for x in ["muse", "calliope", "erato"]):
                domain = "ALCHEMY"

            await ingest_lesson(
                content=f"[{container}] {error_type}: {line[:200]}",
                domain=domain,
                lesson_type="failure",
                tags=[error_type, "docker-log", container],
                source="LCIS-WATCHER",
                context={"container": container, "full_line": line[:500]},
                severity="high" if error_type in ["container_crash", "memory_exceeded"] else "medium"
            )
            break


async def watch_event_bus():
    """Subscribe to Event Bus for all agent activity"""
    print("[WATCHER] Starting Event Bus monitor...")

    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                # Use SSE subscription if available
                async with client.stream("GET", f"{EVENT_BUS_URL}/subscribe/lcis-watcher") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            try:
                                event = json.loads(line[5:])
                                await process_event(event)
                            except json.JSONDecodeError:
                                pass
        except httpx.ConnectError:
            print("[WATCHER] Event Bus not available, retrying in 30s...")
        except Exception as e:
            print(f"[WATCHER] Event Bus error: {e}")

        await asyncio.sleep(30)


async def process_event(event: Dict):
    """Process an event from the Event Bus"""
    event_type = event.get("event_type", event.get("type", ""))
    source = event.get("source", "UNKNOWN")
    data = event.get("data", {})

    # Significant events to capture
    significant_events = [
        "deployment_failed", "deployment_completed",
        "backup_created", "rollback_executed",
        "health_check_failed", "error_detected",
        "build_completed", "build_failed",
        "migration_applied", "migration_failed"
    ]

    if event_type in significant_events:
        lesson_type = "success" if "completed" in event_type or "created" in event_type else "failure"
        severity = "critical" if "failed" in event_type else "low"

        await ingest_lesson(
            content=f"[{source}] {event_type}: {json.dumps(data)[:200]}",
            domain="THE_KEEP",
            lesson_type=lesson_type,
            tags=[event_type, "event-bus", source.lower()],
            source="LCIS-WATCHER",
            context=data,
            severity=severity
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
                parts = result.stdout.strip().split("|", 2)
                commit_hash = parts[0]
                subject = parts[1] if len(parts) > 1 else ""
                body = parts[2] if len(parts) > 2 else ""

                if commit_hash != last_commit and last_commit is not None:
                    last_commit = commit_hash

                    # Determine type from commit message
                    if subject.startswith("fix:") or subject.startswith("fix("):
                        await ingest_lesson(
                            content=f"Git fix: {subject} - {body[:200]}",
                            domain="THE_KEEP",
                            lesson_type="pattern",
                            tags=["git-commit", "fix"],
                            source="LCIS-WATCHER",
                            context={"commit": commit_hash}
                        )
                    elif "fail" in subject.lower() or "error" in subject.lower():
                        await ingest_lesson(
                            content=f"Git failure note: {subject}",
                            domain="THE_KEEP",
                            lesson_type="failure",
                            tags=["git-commit", "failure"],
                            source="LCIS-WATCHER",
                            context={"commit": commit_hash}
                        )
                else:
                    last_commit = commit_hash

        except Exception as e:
            print(f"[WATCHER] Git monitor error: {e}")

        await asyncio.sleep(30)


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run all watchers"""
    print("[LCIS WATCHER] Starting omniscient monitoring...")
    print(f"[LCIS WATCHER] LCIS_URL: {LCIS_URL}")
    print(f"[LCIS WATCHER] EVENT_BUS_URL: {EVENT_BUS_URL}")

    # Wait for services to be ready
    await asyncio.sleep(10)

    await asyncio.gather(
        watch_docker_logs(),
        watch_event_bus(),
        watch_git_commits(),
    )


if __name__ == "__main__":
    asyncio.run(main())
