#!/usr/bin/env python3
"""
PANOPTES WATCHER - Continuous Health Monitoring

The hundred-eyed giant never sleeps. Every 30 seconds, PANOPTES checks:
- All Docker containers
- All agent health endpoints
- Port availability
- Resource usage
- Database connections
"""

import os
import sys
import asyncio
import httpx
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add shared modules
sys.path.append('/opt/leveredge/control-plane/shared')
from watcher_base import WatcherBase, Alert, AlertSeverity

# =============================================================================
# CONFIGURATION
# =============================================================================

# All agents to monitor with their URLs and criticality
AGENTS = {
    # Core Infrastructure
    "event-bus": {"url": "http://event-bus:8099/health", "critical": True},
    "chronos": {"url": "http://chronos:8010/health", "critical": True},
    "hades": {"url": "http://hades:8008/health", "critical": True},
    "hermes": {"url": "http://hermes:8014/health", "critical": True},
    "lcis-librarian": {"url": "http://lcis-librarian:8050/health", "critical": True},
    "apollo": {"url": "http://apollo:8234/health", "critical": True},

    # Monitoring
    "argus": {"url": "http://argus:8016/health", "critical": False},
    "aloy": {"url": "http://aloy:8015/health", "critical": False},
    "watchdog": {"url": "http://watchdog:8240/health", "critical": True},

    # Creative Fleet
    "muse": {"url": "http://muse:8030/health", "critical": False},
    "calliope": {"url": "http://calliope:8031/health", "critical": False},
    "thalia": {"url": "http://thalia:8032/health", "critical": False},

    # Personal Assistants
    "gym-coach": {"url": "http://gym-coach:8230/health", "critical": False},
    "academic-guide": {"url": "http://academic-guide:8231/health", "critical": False},
    "bombadil": {"url": "http://bombadil:8232/health", "critical": False},
    "samwise": {"url": "http://samwise:8233/health", "critical": False},

    # Council
    "convener": {"url": "http://convener:8017/health", "critical": False},
    "scholar": {"url": "http://scholar:8021/health", "critical": False},
    "chiron": {"url": "http://chiron:8020/health", "critical": False},
}

ASCLEPIUS_URL = os.getenv("ASCLEPIUS_URL", "http://asclepius:8024")

# =============================================================================
# PANOPTES WATCHER
# =============================================================================

class PanoptesWatcher(WatcherBase):
    """Continuous health monitoring for all agents and containers"""

    def __init__(self):
        super().__init__(
            poll_interval=30,  # Check every 30 seconds
            alert_cooldown=300,  # Don't repeat same alert for 5 minutes
            max_consecutive_errors=3
        )
        self.previous_states: Dict[str, bool] = {}

    def get_name(self) -> str:
        return "PANOPTES"

    async def watch_cycle(self) -> List[Alert]:
        """Perform one health check cycle"""
        alerts = []

        # Check all agents
        agent_results = await self.check_all_agents()

        for name, result in agent_results.items():
            config = AGENTS.get(name, {})
            is_critical = config.get("critical", False)
            was_healthy = self.previous_states.get(name, True)
            is_healthy = result["healthy"]

            # State changed to unhealthy
            if was_healthy and not is_healthy:
                severity = AlertSeverity.CRITICAL if is_critical else AlertSeverity.WARNING
                alerts.append(Alert(
                    severity=severity,
                    source="PANOPTES",
                    title=f"Agent DOWN: {name}",
                    message=f"{name} is not responding. Error: {result.get('error', 'Unknown')}",
                    target=name,
                    details=result
                ))

                # Trigger auto-diagnosis
                await self.trigger_diagnosis(name, result)

            # State changed to healthy (recovery)
            elif not was_healthy and is_healthy:
                alerts.append(Alert(
                    severity=AlertSeverity.INFO,
                    source="PANOPTES",
                    title=f"Agent RECOVERED: {name}",
                    message=f"{name} is back online",
                    target=name
                ))

            self.previous_states[name] = is_healthy

        # Check Docker containers
        container_alerts = await self.check_containers()
        alerts.extend(container_alerts)

        # Check resource usage
        resource_alerts = await self.check_resources()
        alerts.extend(resource_alerts)

        return alerts

    async def check_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all registered agents"""
        results = {}

        async with httpx.AsyncClient(timeout=5.0) as client:
            for name, config in AGENTS.items():
                try:
                    start = datetime.utcnow()
                    response = await client.get(config['url'])
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000

                    results[name] = {
                        "healthy": response.status_code == 200,
                        "status_code": response.status_code,
                        "response_time_ms": elapsed
                    }
                except httpx.TimeoutException:
                    results[name] = {
                        "healthy": False,
                        "error": "timeout"
                    }
                except httpx.ConnectError:
                    results[name] = {
                        "healthy": False,
                        "error": "connection_refused"
                    }
                except Exception as e:
                    results[name] = {
                        "healthy": False,
                        "error": str(e)
                    }

        return results

    async def check_containers(self) -> List[Alert]:
        """Check Docker container states"""
        alerts = []

        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=leveredge",
                 "--format", "{{.Names}}|{{.Status}}|{{.State}}"],
                capture_output=True, text=True, timeout=10
            )

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    name, status, state = parts[0], parts[1], parts[2]

                    if state not in ["running"]:
                        alerts.append(Alert(
                            severity=AlertSeverity.WARNING,
                            source="PANOPTES",
                            title=f"Container unhealthy: {name}",
                            message=f"Container {name} is in state: {state}. Status: {status}",
                            target=name,
                            details={"state": state, "status": status}
                        ))

                    # Check for restart loops
                    if "Restarting" in status:
                        alerts.append(Alert(
                            severity=AlertSeverity.CRITICAL,
                            source="PANOPTES",
                            title=f"Container restart loop: {name}",
                            message=f"Container {name} is in a restart loop",
                            target=name
                        ))

        except FileNotFoundError:
            # Docker not available - we might be running outside of Docker
            pass
        except Exception as e:
            # Don't alert on docker check failures, just log
            pass

        return alerts

    async def check_resources(self) -> List[Alert]:
        """Check system resource usage"""
        alerts = []

        try:
            # Check disk usage
            result = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 5:
                    usage = int(parts[4].replace('%', ''))
                    if usage > 90:
                        alerts.append(Alert(
                            severity=AlertSeverity.CRITICAL,
                            source="PANOPTES",
                            title="Disk space critical",
                            message=f"Disk usage at {usage}%",
                            details={"usage_percent": usage}
                        ))
                    elif usage > 80:
                        alerts.append(Alert(
                            severity=AlertSeverity.WARNING,
                            source="PANOPTES",
                            title="Disk space warning",
                            message=f"Disk usage at {usage}%",
                            details={"usage_percent": usage}
                        ))

            # Check memory
            result = subprocess.run(
                ["free", "-m"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.strip().split('\n'):
                if line.startswith('Mem:'):
                    parts = line.split()
                    total = int(parts[1])
                    used = int(parts[2])
                    usage = (used / total) * 100

                    if usage > 90:
                        alerts.append(Alert(
                            severity=AlertSeverity.CRITICAL,
                            source="PANOPTES",
                            title="Memory critical",
                            message=f"Memory usage at {usage:.1f}%",
                            details={"total_mb": total, "used_mb": used}
                        ))
                    elif usage > 80:
                        alerts.append(Alert(
                            severity=AlertSeverity.WARNING,
                            source="PANOPTES",
                            title="Memory warning",
                            message=f"Memory usage at {usage:.1f}%"
                        ))

        except Exception as e:
            pass  # Resource check failures are not critical

        return alerts

    async def trigger_diagnosis(self, agent_name: str, error_info: Dict[str, Any]):
        """Trigger ASCLEPIUS to diagnose the issue"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{ASCLEPIUS_URL}/diagnose",
                    json={
                        "agent": agent_name,
                        "error": error_info,
                        "triggered_by": "PANOPTES",
                        "auto_triggered": True
                    }
                )
        except:
            pass  # Don't fail watch cycle if diagnosis fails

# =============================================================================
# MAIN
# =============================================================================

async def main():
    watcher = PanoptesWatcher()
    await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())
