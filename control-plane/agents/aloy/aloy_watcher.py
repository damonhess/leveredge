#!/usr/bin/env python3
"""
ALOY WATCHER - Real-Time Anomaly Detection

Subscribes to Event Bus and watches for:
- Unusual patterns
- Security violations
- Mass operations
- Error spikes
- Forbidden actions
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

sys.path.append('/opt/leveredge/control-plane/shared')
from watcher_base import EventSubscriberBase, Alert, AlertSeverity

# =============================================================================
# CONFIGURATION
# =============================================================================

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
WATCHDOG_URL = os.getenv("WATCHDOG_URL", "http://watchdog:8240")

# =============================================================================
# ANOMALY RULES
# =============================================================================

ANOMALY_RULES = {
    "high_error_rate": {
        "description": "More than 10 errors in 5 minutes",
        "window_seconds": 300,
        "threshold": 10,
        "severity": AlertSeverity.WARNING,
        "patterns": ["error", "failed", "exception"]
    },
    "mass_deletion": {
        "description": "More than 5 delete operations in 1 minute",
        "window_seconds": 60,
        "threshold": 5,
        "severity": AlertSeverity.CRITICAL,
        "patterns": ["delete", "remove", "drop"]
    },
    "security_violation": {
        "description": "Security-related events",
        "window_seconds": 60,
        "threshold": 1,
        "severity": AlertSeverity.CRITICAL,
        "patterns": ["blocked", "forbidden", "unauthorized", "denied", "violation"]
    },
    "rapid_changes": {
        "description": "More than 30 changes in 1 minute",
        "window_seconds": 60,
        "threshold": 30,
        "severity": AlertSeverity.WARNING,
        "patterns": ["create", "update", "modify", "change"]
    },
    "deployment_failure": {
        "description": "Deployment failures",
        "window_seconds": 300,
        "threshold": 1,
        "severity": AlertSeverity.CRITICAL,
        "patterns": ["deployment_failed", "deploy_error", "rollback"]
    },
    "auth_failures": {
        "description": "Multiple auth failures",
        "window_seconds": 300,
        "threshold": 5,
        "severity": AlertSeverity.WARNING,
        "patterns": ["auth_failed", "login_failed", "token_invalid"]
    }
}

# =============================================================================
# ALOY WATCHER
# =============================================================================

class AloyWatcher(EventSubscriberBase):
    """Real-time anomaly detection via Event Bus subscription"""

    def __init__(self):
        super().__init__()
        # Event windows for rate-based rules
        self.event_windows: Dict[str, List[datetime]] = defaultdict(list)
        # Track triggered alerts to prevent spam
        self.triggered_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = 300  # 5 minutes

    def get_name(self) -> str:
        return "ALOY"

    def get_event_filters(self) -> List[str]:
        return ["*"]  # Subscribe to all events

    async def handle_event(self, event: Dict[str, Any]) -> Optional[Alert]:
        """Process an event and check for anomalies"""

        event_type = event.get("event_type", "").lower()
        event_data = event.get("data", {})
        event_str = json.dumps(event).lower()

        # Check each rule
        for rule_name, rule in ANOMALY_RULES.items():
            # Check if event matches any pattern
            matched = False
            for pattern in rule["patterns"]:
                if pattern in event_type or pattern in event_str:
                    matched = True
                    break

            if not matched:
                continue

            # Add to window
            now = datetime.utcnow()
            self.event_windows[rule_name].append(now)

            # Clean old events from window
            cutoff = now - timedelta(seconds=rule["window_seconds"])
            self.event_windows[rule_name] = [
                t for t in self.event_windows[rule_name] if t > cutoff
            ]

            # Check threshold
            if len(self.event_windows[rule_name]) >= rule["threshold"]:
                # Check cooldown
                last_triggered = self.triggered_alerts.get(rule_name)
                if last_triggered and (now - last_triggered).seconds < self.alert_cooldown:
                    continue

                self.triggered_alerts[rule_name] = now

                return Alert(
                    severity=rule["severity"],
                    source="ALOY",
                    title=f"ANOMALY: {rule_name}",
                    message=rule["description"],
                    details={
                        "rule": rule_name,
                        "count": len(self.event_windows[rule_name]),
                        "window_seconds": rule["window_seconds"],
                        "threshold": rule["threshold"],
                        "triggering_event": event
                    }
                )

        return None

# =============================================================================
# HEARTBEAT SENDER
# =============================================================================

import httpx

async def send_heartbeats(watcher: AloyWatcher):
    """Send periodic heartbeats to WATCHDOG"""
    while watcher.running:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{WATCHDOG_URL}/heartbeat",
                    json={
                        "watcher_name": "ALOY",
                        "state": "running",
                        "last_check": datetime.utcnow().isoformat(),
                        "checks_performed": watcher.events_processed,
                        "alerts_sent": len(watcher.triggered_alerts),
                        "errors": watcher.errors[-10:]
                    }
                )
        except:
            pass
        await asyncio.sleep(30)

# =============================================================================
# MAIN
# =============================================================================

async def main():
    watcher = AloyWatcher()

    # Run both event subscription and heartbeat sending
    await asyncio.gather(
        watcher.run(),
        send_heartbeats(watcher)
    )

if __name__ == "__main__":
    asyncio.run(main())
