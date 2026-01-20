#!/usr/bin/env python3
"""
LCIS WATCHER - Comprehensive Log and Event Capture

Watches:
- Docker container logs (via API, not CLI)
- Event Bus events
- Git commits
- File changes
- Error patterns

Captures everything and sends to LCIS Librarian.
"""

import os
import sys
import asyncio
import json
import re
import httpx
from datetime import datetime
from typing import Dict, Any, List, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================

LCIS_URL = os.getenv("LCIS_URL", "http://lcis-librarian:8050")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "/var/run/docker.sock")
WATCHDOG_URL = os.getenv("WATCHDOG_URL", "http://watchdog:8240")

# Patterns to capture
ERROR_PATTERNS = [
    (r"Traceback \(most recent call last\)", "python_traceback", "critical"),
    (r"Error: (.+)", "error", "warning"),
    (r"Exception: (.+)", "exception", "warning"),
    (r"CRITICAL", "critical_log", "critical"),
    (r"FATAL", "fatal_log", "critical"),
    (r"failed to", "failure", "warning"),
    (r"connection refused", "connection_error", "warning"),
    (r"timeout", "timeout", "warning"),
    (r"permission denied", "permission_error", "warning"),
    (r"out of memory", "oom", "critical"),
    (r"disk full", "disk_full", "critical"),
]

FIX_PATTERNS = [
    (r"fixed:?\s*(.+)", "fix"),
    (r"resolved:?\s*(.+)", "fix"),
    (r"solution:?\s*(.+)", "solution"),
    (r"workaround:?\s*(.+)", "workaround"),
]

# =============================================================================
# DOCKER LOG WATCHER (via HTTP API)
# =============================================================================

class DockerLogWatcher:
    """Watch Docker logs via HTTP API (works without docker CLI)"""

    def __init__(self):
        self.last_timestamps: Dict[str, str] = {}

    async def get_containers(self) -> List[Dict[str, Any]]:
        """Get list of containers via Docker API"""
        try:
            # Use Unix socket
            transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                response = await client.get(
                    "/containers/json",
                    params={"filters": json.dumps({"name": ["leveredge"]})}
                )
                return response.json()
        except Exception as e:
            print(f"[LCIS_WATCHER] Docker API error: {e}")
            return []

    async def get_logs(self, container_id: str, since: Optional[str] = None) -> str:
        """Get logs from a container"""
        try:
            transport = httpx.AsyncHTTPTransport(uds=DOCKER_SOCKET)
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
                params = {"stdout": "true", "stderr": "true", "tail": "100"}
                if since:
                    params["since"] = since

                response = await client.get(
                    f"/containers/{container_id}/logs",
                    params=params
                )
                return response.text
        except Exception as e:
            print(f"[LCIS_WATCHER] Log fetch error: {e}")
            return ""

    async def watch_cycle(self) -> List[Dict[str, Any]]:
        """Perform one log collection cycle"""
        captured = []
        containers = await self.get_containers()

        for container in containers:
            container_id = container.get("Id", "")[:12]
            container_name = container.get("Names", ["/unknown"])[0].lstrip("/")

            logs = await self.get_logs(container_id)

            for line in logs.split('\n'):
                # Check error patterns
                for pattern, error_type, severity in ERROR_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        captured.append({
                            "type": "error",
                            "error_type": error_type,
                            "severity": severity,
                            "container": container_name,
                            "message": line[:500],
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        break

                # Check fix patterns
                for pattern, fix_type in FIX_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        captured.append({
                            "type": "fix",
                            "fix_type": fix_type,
                            "container": container_name,
                            "message": match.group(1)[:500] if match.groups() else line[:500],
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        break

        return captured

# =============================================================================
# EVENT BUS WATCHER
# =============================================================================

class EventBusWatcher:
    """Watch Event Bus for significant events"""

    SIGNIFICANT_EVENTS = [
        "deployment_failed", "deployment_completed",
        "backup_created", "rollback_executed",
        "health_check_failed", "agent_crashed",
        "alert_sent", "error_detected",
        "build_completed", "build_failed",
        "lcis_blocked", "security_violation"
    ]

    async def subscribe(self, callback):
        """Subscribe to Event Bus and process events"""
        while True:
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream("GET", f"{EVENT_BUS_URL}/subscribe") as response:
                        async for line in response.aiter_lines():
                            if line.startswith("data:"):
                                try:
                                    event = json.loads(line[5:])
                                    event_type = event.get("event_type", "")

                                    # Capture significant events
                                    if any(sig in event_type for sig in self.SIGNIFICANT_EVENTS):
                                        await callback({
                                            "type": "event",
                                            "event_type": event_type,
                                            "source": event.get("source", "unknown"),
                                            "data": event.get("data", {}),
                                            "timestamp": datetime.utcnow().isoformat()
                                        })
                                except:
                                    pass
            except Exception as e:
                print(f"[LCIS_WATCHER] Event Bus error: {e}")
                await asyncio.sleep(5)

# =============================================================================
# MAIN WATCHER
# =============================================================================

class LCISWatcher:
    """Main watcher orchestrator"""

    def __init__(self):
        self.docker_watcher = DockerLogWatcher()
        self.event_watcher = EventBusWatcher()
        self.running = False
        self.checks_performed = 0
        self.items_captured = 0

    async def ingest(self, item: Dict[str, Any]):
        """Send captured item to LCIS"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{LCIS_URL}/ingest",
                    json={
                        "content": f"[{item.get('type', 'unknown')}] {item.get('message', item.get('event_type', 'Unknown'))}",
                        "domain": item.get("container", item.get("source", "WATCHER")),
                        "type": "error" if item.get("severity") else "success",
                        "source_agent": "LCIS_WATCHER",
                        "tags": ["auto-captured", item.get("type", "unknown")],
                        "source_context": item,
                        "auto_captured": True
                    }
                )
                self.items_captured += 1
        except Exception as e:
            print(f"[LCIS_WATCHER] Ingest error: {e}")

    async def send_heartbeat(self):
        """Send heartbeat to WATCHDOG"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{WATCHDOG_URL}/heartbeat",
                    json={
                        "watcher_name": "LCIS_WATCHER",
                        "state": "running",
                        "last_check": datetime.utcnow().isoformat(),
                        "checks_performed": self.checks_performed,
                        "alerts_sent": self.items_captured,
                        "errors": []
                    }
                )
        except:
            pass

    async def docker_loop(self):
        """Continuous Docker log watching"""
        while self.running:
            try:
                captured = await self.docker_watcher.watch_cycle()
                self.checks_performed += 1

                for item in captured:
                    await self.ingest(item)

                await self.send_heartbeat()

            except Exception as e:
                print(f"[LCIS_WATCHER] Docker loop error: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    async def event_callback(self, item: Dict[str, Any]):
        """Callback for Event Bus events"""
        await self.ingest(item)

    async def run(self):
        """Run all watchers"""
        print("[LCIS_WATCHER] Starting omniscient log capture...")
        self.running = True

        await asyncio.gather(
            self.docker_loop(),
            self.event_watcher.subscribe(self.event_callback)
        )

# =============================================================================
# MAIN
# =============================================================================

async def main():
    watcher = LCISWatcher()
    await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())
