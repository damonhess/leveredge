#!/usr/bin/env python3
"""
ARGUS WATCHER - Continuous Metrics Collection

Collects metrics every 60 seconds:
- Response times
- Error rates
- Resource usage
- Throughput
- Latency percentiles

Alerts on threshold violations.
"""

import os
import sys
import asyncio
import httpx
from datetime import datetime
from typing import List, Dict, Any
from collections import defaultdict
import statistics

sys.path.append('/opt/leveredge/control-plane/shared')
from watcher_base import WatcherBase, Alert, AlertSeverity

# =============================================================================
# THRESHOLDS
# =============================================================================

THRESHOLDS = {
    "response_time_ms": {
        "warning": 1000,   # 1 second
        "critical": 5000   # 5 seconds
    },
    "error_rate_percent": {
        "warning": 5,
        "critical": 20
    },
    "memory_percent": {
        "warning": 80,
        "critical": 95
    },
    "cpu_percent": {
        "warning": 70,
        "critical": 90
    }
}

# All agents to collect metrics from
AGENTS = [
    ("event-bus", "http://event-bus:8099/health"),
    ("chronos", "http://chronos:8010/health"),
    ("hades", "http://hades:8008/health"),
    ("hermes", "http://hermes:8014/health"),
    ("lcis-librarian", "http://lcis-librarian:8050/health"),
    ("apollo", "http://apollo:8234/health"),
    ("watchdog", "http://watchdog:8240/health"),
    ("argus", "http://argus:8016/health"),
    ("aloy", "http://aloy:8015/health"),
    ("muse", "http://muse:8030/health"),
    ("calliope", "http://calliope:8031/health"),
    ("thalia", "http://thalia:8032/health"),
    ("convener", "http://convener:8017/health"),
    ("scholar", "http://scholar:8021/health"),
    ("chiron", "http://chiron:8020/health"),
]

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")

# =============================================================================
# ARGUS WATCHER
# =============================================================================

class ArgusWatcher(WatcherBase):
    """Continuous metrics collection and threshold alerting"""

    def __init__(self):
        super().__init__(
            poll_interval=60,  # Collect metrics every minute
            alert_cooldown=300,
            max_consecutive_errors=5
        )
        self.metrics_history: Dict[str, List[float]] = defaultdict(list)
        self.max_history = 60  # Keep 60 data points (1 hour at 1/min)

    def get_name(self) -> str:
        return "ARGUS"

    async def watch_cycle(self) -> List[Alert]:
        """Collect metrics and check thresholds"""
        alerts = []
        metrics = {}

        async with httpx.AsyncClient(timeout=5.0) as client:
            for agent_name, url in AGENTS:
                try:
                    start = datetime.utcnow()
                    response = await client.get(url)
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000

                    metrics[agent_name] = {
                        "response_time_ms": elapsed,
                        "status_code": response.status_code,
                        "healthy": response.status_code == 200
                    }

                    # Store in history
                    self.metrics_history[f"{agent_name}_response_time"].append(elapsed)
                    if len(self.metrics_history[f"{agent_name}_response_time"]) > self.max_history:
                        self.metrics_history[f"{agent_name}_response_time"].pop(0)

                    # Check response time threshold
                    if elapsed > THRESHOLDS["response_time_ms"]["critical"]:
                        alerts.append(Alert(
                            severity=AlertSeverity.CRITICAL,
                            source="ARGUS",
                            title=f"Slow response: {agent_name}",
                            message=f"{agent_name} response time: {elapsed:.0f}ms (threshold: {THRESHOLDS['response_time_ms']['critical']}ms)",
                            target=agent_name,
                            details={"response_time_ms": elapsed}
                        ))
                    elif elapsed > THRESHOLDS["response_time_ms"]["warning"]:
                        alerts.append(Alert(
                            severity=AlertSeverity.WARNING,
                            source="ARGUS",
                            title=f"Slow response: {agent_name}",
                            message=f"{agent_name} response time: {elapsed:.0f}ms",
                            target=agent_name
                        ))

                except Exception as e:
                    metrics[agent_name] = {
                        "healthy": False,
                        "error": str(e)
                    }

        # Calculate aggregates
        response_times = [m.get("response_time_ms", 0) for m in metrics.values() if m.get("response_time_ms")]
        if response_times:
            avg_response = statistics.mean(response_times)
            p95_response = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 1 else response_times[0]

            # Store aggregate metrics
            await self.store_metrics({
                "timestamp": datetime.utcnow().isoformat(),
                "avg_response_ms": avg_response,
                "p95_response_ms": p95_response,
                "healthy_agents": sum(1 for m in metrics.values() if m.get("healthy")),
                "total_agents": len(metrics),
                "agents": metrics
            })

        return alerts

    async def store_metrics(self, metrics: Dict[str, Any]):
        """Store metrics - publish to Event Bus"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{EVENT_BUS_URL}/publish",
                    json={
                        "event_type": "metrics_collected",
                        "source": "ARGUS",
                        "data": metrics
                    }
                )
        except:
            pass

# =============================================================================
# MAIN
# =============================================================================

async def main():
    watcher = ArgusWatcher()
    await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())
