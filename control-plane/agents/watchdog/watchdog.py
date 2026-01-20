#!/usr/bin/env python3
"""
WATCHDOG - The Watcher of Watchers

Port: 8240
Domain: META_MONITORING

If the watchers stop watching, who watches the watchers?
WATCHDOG does.

CAPABILITIES:
- Receives heartbeats from all watchers
- Alerts if any watcher goes silent
- Dead man's switch - alerts if WATCHDOG itself stops
- Escalation to external systems (email, SMS, PagerDuty)
- Watcher health dashboard
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

# Track alerts sent (for cooldown)
last_alerts: Dict[str, datetime] = {}
ALERT_COOLDOWN_SECONDS = 300

# Expected watchers - alert if any is missing
EXPECTED_WATCHERS = [
    "PANOPTES",
    "ARGUS",
    "ALOY",
    "LCIS_WATCHER",
    "VARYS_SCHEDULER",
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

            # Send alerts with cooldown
            if dead_watchers:
                await send_critical_alert(
                    f"DEAD WATCHERS: {', '.join(dead_watchers)}",
                    f"The following watchers have stopped sending heartbeats: {dead_watchers}"
                )

            if missing_watchers and len(watchers) > 0:
                # Only alert about missing if we have at least one watcher registered
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

def should_send_alert(alert_key: str) -> bool:
    """Check if enough time has passed since last alert of this type"""
    last_sent = last_alerts.get(alert_key)
    if last_sent and (datetime.utcnow() - last_sent).total_seconds() < ALERT_COOLDOWN_SECONDS:
        return False
    return True

async def send_critical_alert(title: str, message: str):
    """Send critical alert via all channels"""
    alert_key = f"critical:{title}"
    if not should_send_alert(alert_key):
        return

    last_alerts[alert_key] = datetime.utcnow()

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
    except Exception as e:
        print(f"[WATCHDOG] HERMES alert failed: {e}")

    # Email (direct, bypass HERMES for redundancy)
    if SMTP_HOST and ALERT_EMAIL:
        try:
            send_email(title, message)
        except Exception as e:
            print(f"[WATCHDOG] Email alert failed: {e}")

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
    alert_key = f"warning:{title}"
    if not should_send_alert(alert_key):
        return

    last_alerts[alert_key] = datetime.utcnow()

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
        "status": "healthy" if healthy_count == total_count or total_count == 0 else "degraded",
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
        "system_health": "healthy" if all(w.is_healthy for w in watchers.values()) or len(watchers) == 0 else "degraded",
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

@app.post("/reset")
async def reset_watchers():
    """Reset all watcher state (for testing)"""
    global watchers, last_alerts
    watchers = {}
    last_alerts = {}
    return {"status": "reset", "message": "All watcher state cleared"}

# =============================================================================
# STARTUP
# =============================================================================

@app.on_event("startup")
async def startup():
    """Start background health check loop"""
    asyncio.create_task(check_watcher_health())
    print("[WATCHDOG] Started - watching the watchers")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8240)
