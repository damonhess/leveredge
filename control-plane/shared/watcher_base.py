#!/usr/bin/env python3
"""
WATCHER BASE - Foundation for all monitoring agents

Provides:
- Continuous polling loop
- Heartbeat registration
- Alert escalation
- Self-monitoring
- Graceful shutdown
"""

import os
import asyncio
import httpx
import json
import signal
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
WATCHDOG_URL = os.getenv("WATCHDOG_URL", "http://watchdog:8240")

# =============================================================================
# MODELS
# =============================================================================

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class WatcherState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"

@dataclass
class Alert:
    severity: AlertSeverity
    source: str
    title: str
    message: str
    target: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    alert_id: str = field(default_factory=lambda: f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}")

@dataclass
class Heartbeat:
    watcher_name: str
    state: WatcherState
    last_check: datetime
    checks_performed: int
    alerts_sent: int
    errors: List[str] = field(default_factory=list)

# =============================================================================
# WATCHER BASE CLASS
# =============================================================================

class WatcherBase(ABC):
    """
    Base class for all monitoring agents.

    Subclasses must implement:
    - watch_cycle(): The main monitoring logic
    - get_name(): Watcher identifier

    Provides:
    - Continuous polling loop
    - Heartbeat registration
    - Alert sending
    - Error handling
    - Graceful shutdown
    """

    def __init__(
        self,
        poll_interval: int = 60,
        alert_cooldown: int = 300,
        max_consecutive_errors: int = 5
    ):
        self.poll_interval = poll_interval
        self.alert_cooldown = alert_cooldown
        self.max_consecutive_errors = max_consecutive_errors

        self.state = WatcherState.STARTING
        self.running = False
        self.checks_performed = 0
        self.alerts_sent = 0
        self.consecutive_errors = 0
        self.last_alerts: Dict[str, datetime] = {}  # For cooldown tracking
        self.errors: List[str] = []

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    @abstractmethod
    def get_name(self) -> str:
        """Return the watcher's name"""
        pass

    @abstractmethod
    async def watch_cycle(self) -> List[Alert]:
        """
        Perform one monitoring cycle.
        Returns list of alerts to send.
        """
        pass

    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"[{self.get_name()}] Shutdown signal received")
        self.running = False
        self.state = WatcherState.STOPPED

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert via HERMES with cooldown logic"""

        # Check cooldown
        cooldown_key = f"{alert.source}:{alert.target}:{alert.title}"
        last_sent = self.last_alerts.get(cooldown_key)

        if last_sent and (datetime.utcnow() - last_sent).seconds < self.alert_cooldown:
            logger.debug(f"[{self.get_name()}] Alert suppressed (cooldown): {alert.title}")
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{HERMES_URL}/alert",
                    json={
                        "severity": alert.severity.value,
                        "source": alert.source,
                        "title": alert.title,
                        "message": alert.message,
                        "target": alert.target,
                        "details": alert.details,
                        "alert_id": alert.alert_id,
                        "timestamp": alert.timestamp.isoformat()
                    }
                )

                if response.status_code == 200:
                    self.last_alerts[cooldown_key] = datetime.utcnow()
                    self.alerts_sent += 1
                    logger.info(f"[{self.get_name()}] Alert sent: {alert.title}")
                    return True
                else:
                    logger.error(f"[{self.get_name()}] Alert failed: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"[{self.get_name()}] Alert error: {e}")
            # Try Event Bus as fallback
            await self.publish_event("alert_failed", {
                "alert": alert.title,
                "error": str(e)
            })
            return False

    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to Event Bus"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{EVENT_BUS_URL}/publish",
                    json={
                        "event_type": event_type,
                        "source": self.get_name(),
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        except Exception as e:
            logger.error(f"[{self.get_name()}] Event Bus error: {e}")

    async def send_heartbeat(self):
        """Send heartbeat to WATCHDOG"""
        heartbeat = Heartbeat(
            watcher_name=self.get_name(),
            state=self.state,
            last_check=datetime.utcnow(),
            checks_performed=self.checks_performed,
            alerts_sent=self.alerts_sent,
            errors=self.errors[-10:]  # Last 10 errors
        )

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{WATCHDOG_URL}/heartbeat",
                    json={
                        "watcher_name": heartbeat.watcher_name,
                        "state": heartbeat.state.value,
                        "last_check": heartbeat.last_check.isoformat(),
                        "checks_performed": heartbeat.checks_performed,
                        "alerts_sent": heartbeat.alerts_sent,
                        "errors": heartbeat.errors
                    }
                )
        except Exception as e:
            # Don't let heartbeat failures stop watching
            logger.debug(f"[{self.get_name()}] Heartbeat failed: {e}")

    async def run(self):
        """Main run loop"""
        logger.info(f"[{self.get_name()}] Starting watcher (interval: {self.poll_interval}s)")
        self.running = True
        self.state = WatcherState.RUNNING

        while self.running:
            try:
                # Perform watch cycle
                alerts = await self.watch_cycle()
                self.checks_performed += 1
                self.consecutive_errors = 0

                # Send any alerts
                for alert in alerts:
                    await self.send_alert(alert)

                # Send heartbeat
                await self.send_heartbeat()

                # Publish health event
                await self.publish_event(f"{self.get_name().lower()}_check_complete", {
                    "checks_performed": self.checks_performed,
                    "alerts_generated": len(alerts)
                })

            except Exception as e:
                self.consecutive_errors += 1
                error_msg = f"Watch cycle error: {str(e)}"
                self.errors.append(error_msg)
                logger.error(f"[{self.get_name()}] {error_msg}")

                # If too many consecutive errors, mark as degraded
                if self.consecutive_errors >= self.max_consecutive_errors:
                    self.state = WatcherState.DEGRADED
                    await self.send_alert(Alert(
                        severity=AlertSeverity.CRITICAL,
                        source=self.get_name(),
                        title=f"{self.get_name()} DEGRADED",
                        message=f"Watcher has failed {self.consecutive_errors} consecutive checks",
                        details={"errors": self.errors[-5:]}
                    ))

            # Wait for next cycle
            await asyncio.sleep(self.poll_interval)

        logger.info(f"[{self.get_name()}] Watcher stopped")


# =============================================================================
# EVENT BUS SUBSCRIBER BASE
# =============================================================================

class EventSubscriberBase(ABC):
    """
    Base class for agents that subscribe to Event Bus.

    Subclasses must implement:
    - handle_event(): Process incoming events
    - get_name(): Subscriber identifier
    - get_event_filters(): Which events to subscribe to
    """

    def __init__(self):
        self.running = False
        self.events_processed = 0
        self.errors: List[str] = []

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_event_filters(self) -> List[str]:
        """Return list of event types to subscribe to (or ['*'] for all)"""
        pass

    @abstractmethod
    async def handle_event(self, event: Dict[str, Any]) -> Optional[Alert]:
        """Process an event, optionally return an alert"""
        pass

    async def run(self):
        """Subscribe to Event Bus and process events"""
        logger.info(f"[{self.get_name()}] Starting event subscriber")
        self.running = True
        filters = self.get_event_filters()

        while self.running:
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    # Use /events endpoint (SSE stream) or /agents/{name}/events
                    url = f"{EVENT_BUS_URL}/events"

                    async with client.stream("GET", url) as response:
                        async for line in response.aiter_lines():
                            if not self.running:
                                break

                            if line.startswith("data:"):
                                try:
                                    event = json.loads(line[5:])
                                    alert = await self.handle_event(event)
                                    self.events_processed += 1

                                    if alert:
                                        await self._send_alert(alert)

                                except json.JSONDecodeError:
                                    pass
                                except Exception as e:
                                    self.errors.append(str(e))
                                    logger.error(f"[{self.get_name()}] Event handling error: {e}")

            except Exception as e:
                logger.error(f"[{self.get_name()}] Event Bus connection error: {e}")
                await asyncio.sleep(5)  # Reconnect delay

        logger.info(f"[{self.get_name()}] Event subscriber stopped")

    async def _send_alert(self, alert: Alert):
        """Send alert via HERMES"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{HERMES_URL}/alert",
                    json={
                        "severity": alert.severity.value,
                        "source": alert.source,
                        "title": alert.title,
                        "message": alert.message,
                        "target": alert.target,
                        "details": alert.details
                    }
                )
        except Exception as e:
            logger.error(f"[{self.get_name()}] Alert error: {e}")


# =============================================================================
# SCHEDULED TASK BASE
# =============================================================================

class ScheduledTaskBase(ABC):
    """
    Base class for scheduled tasks (daily briefings, hourly reports, etc.)

    Subclasses must implement:
    - execute(): The task logic
    - get_name(): Task identifier
    - get_schedule(): Cron-like schedule
    """

    def __init__(self):
        self.running = False
        self.last_run: Optional[datetime] = None
        self.run_count = 0
        self.errors: List[str] = []

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_schedule(self) -> Dict[str, Any]:
        """
        Return schedule config:
        {"type": "interval", "seconds": 3600}  # Every hour
        {"type": "daily", "hour": 7, "minute": 0}  # Daily at 7am
        {"type": "cron", "expression": "0 */6 * * *"}  # Every 6 hours
        """
        pass

    @abstractmethod
    async def execute(self) -> Optional[Dict[str, Any]]:
        """Execute the scheduled task, return result"""
        pass

    async def run(self):
        """Run the scheduled task"""
        logger.info(f"[{self.get_name()}] Starting scheduled task")
        self.running = True
        schedule = self.get_schedule()

        while self.running:
            try:
                should_run = self._check_schedule(schedule)

                if should_run:
                    logger.info(f"[{self.get_name()}] Executing scheduled task")
                    result = await self.execute()
                    self.last_run = datetime.utcnow()
                    self.run_count += 1

                    # Publish completion event
                    await self._publish_event(f"{self.get_name().lower()}_completed", {
                        "run_count": self.run_count,
                        "result": result
                    })

                await asyncio.sleep(60)  # Check schedule every minute

            except Exception as e:
                self.errors.append(str(e))
                logger.error(f"[{self.get_name()}] Task error: {e}")
                await asyncio.sleep(60)

        logger.info(f"[{self.get_name()}] Scheduled task stopped")

    def _check_schedule(self, schedule: Dict[str, Any]) -> bool:
        """Check if task should run now"""
        now = datetime.utcnow()
        schedule_type = schedule.get("type", "interval")

        if schedule_type == "interval":
            seconds = schedule.get("seconds", 3600)
            if self.last_run is None:
                return True
            return (now - self.last_run).total_seconds() >= seconds

        elif schedule_type == "daily":
            hour = schedule.get("hour", 7)
            minute = schedule.get("minute", 0)
            if self.last_run and self.last_run.date() == now.date():
                return False  # Already ran today
            return now.hour == hour and now.minute == minute

        return False

    async def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish event to Event Bus"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{EVENT_BUS_URL}/publish",
                    json={
                        "event_type": event_type,
                        "source": self.get_name(),
                        "data": data
                    }
                )
        except:
            pass
