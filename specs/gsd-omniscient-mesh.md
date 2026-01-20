# GSD: OMNISCIENT MESH - Enterprise-Grade Active Monitoring

**Priority:** CRITICAL
**Estimated Time:** 2-3 hours
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Transform all monitoring agents from passive tools into an **enterprise-grade active observability mesh** that:

1. **SEES EVERYTHING** - Every container, log, event, metric, anomaly
2. **NEVER SLEEPS** - Continuous polling, no gaps
3. **SELF-HEALING** - Watchers watch each other
4. **INSTANT ALERTS** - Issues detected in seconds, not discovered manually
5. **AUTO-DIAGNOSIS** - Problems identified and root causes suggested automatically
6. **COORDINATED RESPONSE** - Agents work together, not in isolation

---

## ARCHITECTURE: THE OMNISCIENT MESH

```
                            ┌─────────────────────────────────────────────┐
                            │              HERMES (Alerts)                │
                            │         Central Notification Hub            │
                            └─────────────────┬───────────────────────────┘
                                              │
                 ┌────────────────────────────┼────────────────────────────┐
                 │                            │                            │
                 ▼                            ▼                            ▼
    ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
    │     PANOPTES       │     │      ARGUS         │     │       ALOY         │
    │  Health Watcher    │────▶│  Metrics Watcher   │────▶│  Anomaly Watcher   │
    │  (Every 30s)       │     │  (Every 60s)       │     │  (Real-time)       │
    └─────────┬──────────┘     └─────────┬──────────┘     └─────────┬──────────┘
              │                          │                          │
              │ Unhealthy?               │ Threshold?               │ Anomaly?
              ▼                          ▼                          ▼
    ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
    │    ASCLEPIUS       │     │    LCIS            │     │    CERBERUS        │
    │  Auto-Diagnose     │     │  Pattern Match     │     │  Security Check    │
    └────────────────────┘     └────────────────────┘     └────────────────────┘
              │                          │                          │
              └──────────────────────────┼──────────────────────────┘
                                         │
                                         ▼
                            ┌─────────────────────────────────────────────┐
                            │              EVENT BUS                       │
                            │         All Events Flow Here                 │
                            └─────────────────────────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
    ┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
    │   LCIS WATCHER     │     │      VARYS         │     │       IRIS         │
    │   Log Capture      │     │  Intel Briefings   │     │   World Events     │
    │   (Continuous)     │     │  (Scheduled)       │     │   (Hourly)         │
    └────────────────────┘     └────────────────────┘     └────────────────────┘

                    ┌─────────────────────────────────────┐
                    │         WATCHDOG (NEW)              │
                    │    Watches the Watchers             │
                    │    Dead Man's Switch                │
                    └─────────────────────────────────────┘
```

---

## PHASE 1: CORE WATCHING INFRASTRUCTURE

### 1.1 Create Shared Watcher Base Class

Create `/opt/leveredge/control-plane/shared/watcher_base.py`:

```python
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
                    filter_param = ",".join(filters) if filters != ["*"] else ""
                    url = f"{EVENT_BUS_URL}/subscribe"
                    if filter_param:
                        url += f"?events={filter_param}"
                    
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
```

---

## PHASE 2: WATCHDOG - THE WATCHER OF WATCHERS

Create `/opt/leveredge/control-plane/agents/watchdog/watchdog.py`:

```python
#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                              WATCHDOG                                          ║
║                     The Watcher of Watchers                                    ║
║                                                                                ║
║  Port: 8240                                                                    ║
║  Domain: META_MONITORING                                                       ║
║                                                                                ║
║  If the watchers stop watching, who watches the watchers?                      ║
║  WATCHDOG does.                                                                ║
║                                                                                ║
║  CAPABILITIES:                                                                 ║
║  • Receives heartbeats from all watchers                                       ║
║  • Alerts if any watcher goes silent                                           ║
║  • Dead man's switch - alerts if WATCHDOG itself stops                         ║
║  • Escalation to external systems (email, SMS, PagerDuty)                      ║
║  • Watcher health dashboard                                                    ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import asyncio
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from enum import Enum
import smtplib
from email.mime.text import MIMEText

app = FastAPI(
    title="WATCHDOG",
    description="The Watcher of Watchers",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "")

# How long before a watcher is considered dead
HEARTBEAT_TIMEOUT_SECONDS = 120  # 2 minutes
CHECK_INTERVAL_SECONDS = 30

# =============================================================================
# MODELS
# =============================================================================

class WatcherState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    DEAD = "dead"  # No heartbeat received

class HeartbeatInput(BaseModel):
    watcher_name: str
    state: str
    last_check: str
    checks_performed: int
    alerts_sent: int
    errors: List[str] = []

class WatcherStatus(BaseModel):
    watcher_name: str
    state: WatcherState
    last_heartbeat: Optional[datetime]
    checks_performed: int
    alerts_sent: int
    errors: List[str]
    is_healthy: bool

# =============================================================================
# STATE
# =============================================================================

# Track all watchers
watchers: Dict[str, WatcherStatus] = {}

# Expected watchers - alert if any is missing
EXPECTED_WATCHERS = [
    "PANOPTES",
    "ARGUS", 
    "ALOY",
    "LCIS_WATCHER",
    "VARYS_SCHEDULER",
    "IRIS_SCHEDULER",
]

# =============================================================================
# HEARTBEAT RECEIVER
# =============================================================================

@app.post("/heartbeat")
async def receive_heartbeat(heartbeat: HeartbeatInput):
    """Receive heartbeat from a watcher"""
    
    watchers[heartbeat.watcher_name] = WatcherStatus(
        watcher_name=heartbeat.watcher_name,
        state=WatcherState(heartbeat.state),
        last_heartbeat=datetime.utcnow(),
        checks_performed=heartbeat.checks_performed,
        alerts_sent=heartbeat.alerts_sent,
        errors=heartbeat.errors,
        is_healthy=heartbeat.state in ["running", "starting"]
    )
    
    return {"status": "received", "watcher": heartbeat.watcher_name}

# =============================================================================
# HEALTH CHECK LOOP
# =============================================================================

async def check_watcher_health():
    """Check all watchers for missed heartbeats"""
    while True:
        try:
            now = datetime.utcnow()
            dead_watchers = []
            degraded_watchers = []
            
            # Check registered watchers
            for name, status in watchers.items():
                if status.last_heartbeat:
                    age = (now - status.last_heartbeat).total_seconds()
                    
                    if age > HEARTBEAT_TIMEOUT_SECONDS:
                        status.state = WatcherState.DEAD
                        status.is_healthy = False
                        dead_watchers.append(name)
                    elif status.state == WatcherState.DEGRADED:
                        degraded_watchers.append(name)
            
            # Check for missing expected watchers
            missing_watchers = []
            for expected in EXPECTED_WATCHERS:
                if expected not in watchers:
                    missing_watchers.append(expected)
            
            # Send alerts
            if dead_watchers:
                await send_critical_alert(
                    f"DEAD WATCHERS: {', '.join(dead_watchers)}",
                    f"The following watchers have stopped sending heartbeats: {dead_watchers}"
                )
            
            if missing_watchers:
                await send_warning_alert(
                    f"MISSING WATCHERS: {', '.join(missing_watchers)}",
                    f"Expected watchers not registered: {missing_watchers}"
                )
            
            if degraded_watchers:
                await send_warning_alert(
                    f"DEGRADED WATCHERS: {', '.join(degraded_watchers)}",
                    f"Watchers in degraded state: {degraded_watchers}"
                )
            
        except Exception as e:
            print(f"[WATCHDOG] Health check error: {e}")
        
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)

# =============================================================================
# ALERTING
# =============================================================================

async def send_critical_alert(title: str, message: str):
    """Send critical alert via all channels"""
    
    # HERMES
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{HERMES_URL}/alert",
                json={
                    "severity": "emergency",
                    "source": "WATCHDOG",
                    "title": title,
                    "message": message
                }
            )
    except:
        pass
    
    # Email (direct, bypass HERMES for redundancy)
    if SMTP_HOST and ALERT_EMAIL:
        try:
            send_email(title, message)
        except:
            pass
    
    # Event Bus
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": "watchdog_critical_alert",
                    "source": "WATCHDOG",
                    "data": {"title": title, "message": message}
                }
            )
    except:
        pass

async def send_warning_alert(title: str, message: str):
    """Send warning alert"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{HERMES_URL}/alert",
                json={
                    "severity": "warning",
                    "source": "WATCHDOG",
                    "title": title,
                    "message": message
                }
            )
    except:
        pass

def send_email(subject: str, body: str):
    """Send email alert directly"""
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS, ALERT_EMAIL]):
        return
    
    msg = MIMEText(body)
    msg['Subject'] = f"[LEVEREDGE ALERT] {subject}"
    msg['From'] = SMTP_USER
    msg['To'] = ALERT_EMAIL
    
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Health check"""
    healthy_count = sum(1 for w in watchers.values() if w.is_healthy)
    total_count = len(watchers)
    
    return {
        "status": "healthy" if healthy_count == total_count else "degraded",
        "agent": "WATCHDOG",
        "port": 8240,
        "watchers_healthy": healthy_count,
        "watchers_total": total_count,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/status")
async def get_status():
    """Get status of all watchers"""
    return {
        "watchers": {
            name: {
                "state": status.state.value,
                "last_heartbeat": status.last_heartbeat.isoformat() if status.last_heartbeat else None,
                "checks_performed": status.checks_performed,
                "alerts_sent": status.alerts_sent,
                "is_healthy": status.is_healthy,
                "errors": status.errors[-5:]
            }
            for name, status in watchers.items()
        },
        "expected_watchers": EXPECTED_WATCHERS,
        "missing_watchers": [w for w in EXPECTED_WATCHERS if w not in watchers]
    }

@app.get("/dashboard")
async def dashboard():
    """Dashboard data for monitoring UI"""
    now = datetime.utcnow()
    
    return {
        "timestamp": now.isoformat(),
        "system_health": "healthy" if all(w.is_healthy for w in watchers.values()) else "degraded",
        "watchers": [
            {
                "name": status.watcher_name,
                "state": status.state.value,
                "healthy": status.is_healthy,
                "last_seen": status.last_heartbeat.isoformat() if status.last_heartbeat else "never",
                "checks": status.checks_performed,
                "alerts": status.alerts_sent
            }
            for status in watchers.values()
        ],
        "alerts_summary": {
            "total_alerts_sent": sum(w.alerts_sent for w in watchers.values()),
            "total_checks": sum(w.checks_performed for w in watchers.values())
        }
    }

# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup():
    """Start background health check loop"""
    asyncio.create_task(check_watcher_health())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8240)
```

### 2.2 Watchdog Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    httpx \
    pydantic

COPY watchdog.py .

EXPOSE 8240

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8240/health || exit 1

CMD ["uvicorn", "watchdog:app", "--host", "0.0.0.0", "--port", "8240"]
```

---

## PHASE 3: UPGRADE PANOPTES - CONTINUOUS HEALTH WATCHING

Replace `/opt/leveredge/control-plane/agents/panoptes/panoptes_watcher.py`:

```python
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

# All agents to monitor
AGENTS = {
    # Core Infrastructure
    "event-bus": {"url": "http://event-bus:8099", "critical": True},
    "chronos": {"url": "http://chronos:8010", "critical": True},
    "hades": {"url": "http://hades:8008", "critical": True},
    "hermes": {"url": "http://hermes:8014", "critical": True},
    "lcis-librarian": {"url": "http://lcis-librarian:8050", "critical": True},
    "apollo": {"url": "http://apollo:8234", "critical": True},
    
    # Monitoring
    "argus": {"url": "http://argus:8016", "critical": False},
    "aloy": {"url": "http://aloy:8015", "critical": False},
    "watchdog": {"url": "http://watchdog:8240", "critical": True},
    
    # Creative Fleet
    "muse": {"url": "http://muse:8030", "critical": False},
    "calliope": {"url": "http://calliope:8031", "critical": False},
    "thalia": {"url": "http://thalia:8032", "critical": False},
    
    # Personal Assistants
    "gym-coach": {"url": "http://gym-coach:8230", "critical": False},
    "academic-guide": {"url": "http://academic-guide:8231", "critical": False},
    "bombadil": {"url": "http://bombadil:8232", "critical": False},
    "samwise": {"url": "http://samwise:8233", "critical": False},
    
    # Council
    "convener": {"url": "http://convener:8017", "critical": False},
    "scholar": {"url": "http://scholar:8021", "critical": False},
    "chiron": {"url": "http://chiron:8020", "critical": False},
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
                    response = await client.get(f"{config['url']}/health")
                    results[name] = {
                        "healthy": response.status_code == 200,
                        "status_code": response.status_code,
                        "response_time_ms": response.elapsed.total_seconds() * 1000
                    }
                except httpx.TimeoutException:
                    results[name] = {
                        "healthy": False,
                        "error": "timeout"
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
                    
                    if state not in ["running", "healthy"]:
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
                        
        except Exception as e:
            alerts.append(Alert(
                severity=AlertSeverity.WARNING,
                source="PANOPTES",
                title="Docker check failed",
                message=f"Could not check Docker containers: {str(e)}"
            ))
        
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
```

---

## PHASE 4: UPGRADE ALOY - REAL-TIME ANOMALY DETECTION

Create `/opt/leveredge/control-plane/agents/aloy/aloy_watcher.py`:

```python
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
# MAIN
# =============================================================================

async def main():
    watcher = AloyWatcher()
    await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## PHASE 5: UPGRADE VARYS - SCHEDULED INTELLIGENCE

Create `/opt/leveredge/control-plane/agents/varys/varys_scheduler.py`:

```python
#!/usr/bin/env python3
"""
VARYS SCHEDULER - Automated Intelligence Briefings

Runs on schedule:
- Daily briefing at 7am
- Portfolio updates on changes
- Competitor alerts
- Opportunity pipeline
"""

import os
import sys
import asyncio
import httpx
from datetime import datetime
from typing import Dict, Any, Optional

sys.path.append('/opt/leveredge/control-plane/shared')
from watcher_base import ScheduledTaskBase

VARYS_URL = os.getenv("VARYS_URL", "http://varys:8112")
HERMES_URL = os.getenv("HERMES_URL", "http://hermes:8014")

class VarysDailyBriefing(ScheduledTaskBase):
    """Daily intelligence briefing"""
    
    def get_name(self) -> str:
        return "VARYS_SCHEDULER"
    
    def get_schedule(self) -> Dict[str, Any]:
        return {"type": "daily", "hour": 7, "minute": 0}
    
    async def execute(self) -> Optional[Dict[str, Any]]:
        """Generate and send daily briefing"""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Get briefing from VARYS
                response = await client.get(f"{VARYS_URL}/daily-briefing")
                briefing = response.json()
                
                # Send via HERMES
                await client.post(
                    f"{HERMES_URL}/notify",
                    json={
                        "channel": "daily_briefing",
                        "title": f"🕵️ Daily Intelligence Briefing - {datetime.now().strftime('%Y-%m-%d')}",
                        "message": briefing.get("summary", "No briefing available"),
                        "details": briefing
                    }
                )
                
                return briefing
                
        except Exception as e:
            return {"error": str(e)}

async def main():
    scheduler = VarysDailyBriefing()
    await scheduler.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## PHASE 6: UPGRADE ARGUS - CONTINUOUS METRICS

Create `/opt/leveredge/control-plane/agents/argus/argus_watcher.py`:

```python
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
    "event-bus", "chronos", "hades", "hermes", "lcis-librarian",
    "apollo", "panoptes", "argus", "aloy", "varys",
    "muse", "calliope", "thalia", "convener", "scholar", "chiron"
]

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
            for agent in AGENTS:
                try:
                    url = f"http://{agent}:8099/health" if agent == "event-bus" else f"http://{agent}/health"
                    start = datetime.utcnow()
                    response = await client.get(url)
                    elapsed = (datetime.utcnow() - start).total_seconds() * 1000
                    
                    metrics[agent] = {
                        "response_time_ms": elapsed,
                        "status_code": response.status_code,
                        "healthy": response.status_code == 200
                    }
                    
                    # Store in history
                    self.metrics_history[f"{agent}_response_time"].append(elapsed)
                    if len(self.metrics_history[f"{agent}_response_time"]) > self.max_history:
                        self.metrics_history[f"{agent}_response_time"].pop(0)
                    
                    # Check response time threshold
                    if elapsed > THRESHOLDS["response_time_ms"]["critical"]:
                        alerts.append(Alert(
                            severity=AlertSeverity.CRITICAL,
                            source="ARGUS",
                            title=f"Slow response: {agent}",
                            message=f"{agent} response time: {elapsed:.0f}ms (threshold: {THRESHOLDS['response_time_ms']['critical']}ms)",
                            target=agent,
                            details={"response_time_ms": elapsed}
                        ))
                    elif elapsed > THRESHOLDS["response_time_ms"]["warning"]:
                        alerts.append(Alert(
                            severity=AlertSeverity.WARNING,
                            source="ARGUS",
                            title=f"Slow response: {agent}",
                            message=f"{agent} response time: {elapsed:.0f}ms",
                            target=agent
                        ))
                        
                except Exception as e:
                    metrics[agent] = {
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
        """Store metrics (could go to Supabase, Prometheus, etc.)"""
        # For now, publish to Event Bus
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"http://event-bus:8099/publish",
                    json={
                        "event_type": "metrics_collected",
                        "source": "ARGUS",
                        "data": metrics
                    }
                )
        except:
            pass

async def main():
    watcher = ArgusWatcher()
    await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## PHASE 7: UPGRADE LCIS WATCHER - FIX AND ENHANCE

Replace `/opt/leveredge/control-plane/agents/lcis-librarian/watcher.py`:

```python
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
                    f"{LCIS_URL}/lessons",
                    json={
                        "content": f"[{item.get('type', 'unknown')}] {item.get('message', item.get('event_type', 'Unknown'))}",
                        "domain": item.get("container", item.get("source", "WATCHER")),
                        "type": "error" if item.get("severity") else "success",
                        "source_agent": "LCIS_WATCHER",
                        "tags": ["auto-captured", item.get("type", "unknown")],
                        "context": item,
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
```

---

## PHASE 8: FIX DOCKERFILES

### 8.1 Fix lcis-librarian Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY librarian.py .

EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8050/health || exit 1

CMD ["uvicorn", "librarian:app", "--host", "0.0.0.0", "--port", "8050"]
```

### 8.2 Fix lcis-watcher Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# No need for docker CLI - we use Docker API via socket
RUN pip install --no-cache-dir \
    httpx \
    asyncio

COPY watcher.py .

# Mount Docker socket at runtime
CMD ["python", "watcher.py"]
```

---

## PHASE 9: UPDATE DOCKER COMPOSE

Add all watchers to `docker-compose.fleet.yml`:

```yaml
  # ===========================================================================
  # META-MONITORING - THE WATCHERS
  # ===========================================================================

  watchdog:
    build:
      context: ./control-plane/agents/watchdog
      dockerfile: Dockerfile
    container_name: leveredge-watchdog
    ports:
      - "8240:8240"
    environment:
      - HERMES_URL=http://hermes:8014
      - EVENT_BUS_URL=http://event-bus:8099
      - SMTP_HOST=${SMTP_HOST:-}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER:-}
      - SMTP_PASS=${SMTP_PASS:-}
      - ALERT_EMAIL=${ALERT_EMAIL:-}
    networks:
      - leveredge-network
    restart: unless-stopped
    profiles:
      - all
      - core

  panoptes-watcher:
    build:
      context: ./control-plane/agents/panoptes
      dockerfile: Dockerfile.watcher
    container_name: leveredge-panoptes-watcher
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./control-plane/shared:/opt/leveredge/control-plane/shared:ro
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
      - WATCHDOG_URL=http://watchdog:8240
      - ASCLEPIUS_URL=http://asclepius:8024
    networks:
      - leveredge-network
    depends_on:
      - watchdog
      - event-bus
    restart: unless-stopped
    profiles:
      - all
      - core

  argus-watcher:
    build:
      context: ./control-plane/agents/argus
      dockerfile: Dockerfile.watcher
    container_name: leveredge-argus-watcher
    volumes:
      - ./control-plane/shared:/opt/leveredge/control-plane/shared:ro
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
      - WATCHDOG_URL=http://watchdog:8240
    networks:
      - leveredge-network
    depends_on:
      - watchdog
      - event-bus
    restart: unless-stopped
    profiles:
      - all
      - core

  aloy-watcher:
    build:
      context: ./control-plane/agents/aloy
      dockerfile: Dockerfile.watcher
    container_name: leveredge-aloy-watcher
    volumes:
      - ./control-plane/shared:/opt/leveredge/control-plane/shared:ro
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
      - WATCHDOG_URL=http://watchdog:8240
    networks:
      - leveredge-network
    depends_on:
      - watchdog
      - event-bus
    restart: unless-stopped
    profiles:
      - all
      - core

  lcis-watcher:
    build:
      context: ./control-plane/agents/lcis-librarian
      dockerfile: Dockerfile.watcher
    container_name: leveredge-lcis-watcher
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - LCIS_URL=http://lcis-librarian:8050
      - EVENT_BUS_URL=http://event-bus:8099
      - WATCHDOG_URL=http://watchdog:8240
    networks:
      - leveredge-network
    depends_on:
      - lcis-librarian
      - event-bus
    restart: unless-stopped
    profiles:
      - all
      - core

  varys-scheduler:
    build:
      context: ./control-plane/agents/varys
      dockerfile: Dockerfile.scheduler
    container_name: leveredge-varys-scheduler
    volumes:
      - ./control-plane/shared:/opt/leveredge/control-plane/shared:ro
    environment:
      - VARYS_URL=http://varys:8112
      - HERMES_URL=http://hermes:8014
      - WATCHDOG_URL=http://watchdog:8240
    networks:
      - leveredge-network
    depends_on:
      - varys
      - hermes
    restart: unless-stopped
    profiles:
      - all
```

---

## PHASE 10: CREATE WATCHER DOCKERFILES

### 10.1 Panoptes Watcher Dockerfile

Create `control-plane/agents/panoptes/Dockerfile.watcher`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx

COPY panoptes_watcher.py .

CMD ["python", "panoptes_watcher.py"]
```

### 10.2 Argus Watcher Dockerfile

Create `control-plane/agents/argus/Dockerfile.watcher`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx

COPY argus_watcher.py .

CMD ["python", "argus_watcher.py"]
```

### 10.3 Aloy Watcher Dockerfile

Create `control-plane/agents/aloy/Dockerfile.watcher`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx

COPY aloy_watcher.py .

CMD ["python", "aloy_watcher.py"]
```

### 10.4 Varys Scheduler Dockerfile

Create `control-plane/agents/varys/Dockerfile.scheduler`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx

COPY varys_scheduler.py .

CMD ["python", "varys_scheduler.py"]
```

---

## VERIFICATION

```bash
# 1. Start watchers
docker compose -f docker-compose.fleet.yml --env-file .env.fleet up -d \
  watchdog panoptes-watcher argus-watcher aloy-watcher lcis-watcher varys-scheduler

# 2. Check WATCHDOG dashboard
curl http://localhost:8240/dashboard | jq

# 3. Check all watchers registered
curl http://localhost:8240/status | jq '.watchers'

# 4. Trigger a test failure (stop an agent)
docker stop leveredge-muse

# 5. Wait 60 seconds, check for alert
# PANOPTES should detect and alert via HERMES

# 6. Check LCIS captured the event
curl http://localhost:8050/recent | jq

# 7. Restart the agent
docker start leveredge-muse

# 8. Check recovery alert
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-omniscient-mesh.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "OMNISCIENT MESH deployed: WATCHDOG (watcher of watchers), PANOPTES (continuous health), ARGUS (metrics), ALOY (anomaly detection), LCIS (log capture), VARYS (scheduled intel). Enterprise-grade monitoring active.",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "monitoring", "enterprise", "omniscient"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: OMNISCIENT MESH - Enterprise-grade active monitoring

- WATCHDOG: Watches the watchers, dead man's switch
- PANOPTES: Continuous health polling every 30s
- ARGUS: Metrics collection every 60s with thresholds
- ALOY: Real-time Event Bus anomaly detection
- LCIS WATCHER: Docker log capture via API
- VARYS SCHEDULER: Daily intel briefings at 7am

All watchers send heartbeats to WATCHDOG.
All alerts flow through HERMES.
All learnings captured by LCIS.

The system now sees EVERYTHING."
```

---

## SUMMARY

| Watcher | Interval | What It Watches | Alerts Via |
|---------|----------|-----------------|------------|
| **WATCHDOG** | 30s | All other watchers | HERMES + Email |
| **PANOPTES** | 30s | All containers, health endpoints, resources | HERMES |
| **ARGUS** | 60s | Response times, metrics, thresholds | HERMES |
| **ALOY** | Real-time | Event Bus anomalies, patterns | HERMES |
| **LCIS Watcher** | 30s | Docker logs, events, errors | LCIS |
| **VARYS** | Daily 7am | Portfolio, competitors, opportunities | HERMES |

**Escalation Chain:**
```
Issue Detected
     │
     ▼
PANOPTES/ARGUS/ALOY detects
     │
     ▼
Alert sent to HERMES ─────────────► Notification channels
     │
     ▼
Event published to Event Bus
     │
     ▼
LCIS captures for learning
     │
     ▼
ASCLEPIUS auto-diagnoses (if PANOPTES triggered)
     │
     ▼
WATCHDOG verifies watchers are still watching
```

**If WATCHDOG itself dies:** No heartbeats received → External alert (email/SMS)

---

*"Quis custodiet ipsos custodes?" - Who watches the watchers?*
*WATCHDOG does. And WATCHDOG never sleeps.*
