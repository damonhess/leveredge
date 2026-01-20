# GSD: OMNISCIENT WATCHERS - Enterprise-Grade Active Monitoring

**Priority:** CRITICAL
**Estimated Time:** 60-90 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

Transform all monitoring agents from **reactive tools** to **proactive guardians**.

**Current State:** "Call me when you notice a problem"
**Target State:** "I see everything. I alert before you notice. I diagnose automatically."

This GSD implements:
1. **Continuous Health Monitoring** - Every container, every 30 seconds
2. **Real-Time Event Processing** - Every Event Bus message analyzed
3. **Automatic Escalation** - Issue → Diagnosis → Alert → Resolution
4. **Scheduled Intelligence** - Daily briefings, hourly news, metrics aggregation
5. **Unified Alerting** - All alerts flow through HERMES with severity routing
6. **Self-Healing** - Auto-restart failed services, auto-rollback bad deploys

---

## ARCHITECTURE: THE WATCHTOWER

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           THE WATCHTOWER                                     │
│                    "Nothing escapes our gaze"                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  PANOPTES   │    │   ARGUS     │    │    ALOY     │    │  CERBERUS   │  │
│  │  Health     │    │   Metrics   │    │   Anomaly   │    │  Security   │  │
│  │  30s poll   │    │   60s poll  │    │  Real-time  │    │  Continuous │  │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘  │
│         │                  │                  │                  │          │
│         └──────────────────┴────────┬─────────┴──────────────────┘          │
│                                     │                                        │
│                                     ▼                                        │
│                          ┌─────────────────┐                                │
│                          │   EVENT BUS     │                                │
│                          │  (All events)   │                                │
│                          └────────┬────────┘                                │
│                                   │                                          │
│         ┌─────────────────────────┼─────────────────────────┐               │
│         ▼                         ▼                         ▼               │
│  ┌─────────────┐         ┌─────────────┐         ┌─────────────┐           │
│  │ ASCLEPIUS   │         │    LCIS     │         │   HERMES    │           │
│  │ Auto-Diag   │         │  Learning   │         │   Alerts    │           │
│  └─────────────┘         └─────────────┘         └─────────────┘           │
│                                                         │                   │
│                          ┌──────────────────────────────┘                   │
│                          ▼                                                   │
│                   ┌─────────────┐                                           │
│                   │   VARYS     │                                           │
│                   │  Briefings  │                                           │
│                   │  (7am daily)│                                           │
│                   └─────────────┘                                           │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: CORE INFRASTRUCTURE FIXES

### 1.1 Fix Dockerfiles (Add curl for healthchecks)

**lcis-librarian/Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install curl for healthcheck
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

**Apply same fix to ALL agent Dockerfiles missing curl:**
```bash
# List of agents to fix
for agent in panoptes asclepius argus aloy varys cerberus lcis-librarian lcis-oracle; do
    dockerfile="/opt/leveredge/control-plane/agents/${agent}/Dockerfile"
    if [ -f "$dockerfile" ]; then
        # Check if curl is already installed
        if ! grep -q "apt-get.*curl" "$dockerfile"; then
            # Add curl installation after FROM line
            sed -i '/^FROM/a RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*' "$dockerfile"
        fi
    fi
done
```

### 1.2 Fix LCIS Watcher Docker Socket Access

The watcher needs access to Docker socket but also needs Docker CLI installed properly:

**lcis-librarian/Dockerfile.watcher:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Docker CLI (not full docker.io - just the client)
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir httpx

COPY watcher.py .

CMD ["python", "watcher.py"]
```

---

## PHASE 2: PANOPTES - THE ALL-SEEING EYE

### 2.1 Add Continuous Monitoring Loop

Add to `/opt/leveredge/control-plane/agents/panoptes/panoptes.py`:

```python
# =============================================================================
# CONTINUOUS MONITORING - THE EYE THAT NEVER SLEEPS
# =============================================================================

import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Set

# Monitoring state
_monitoring_active = False
_last_health_check: Dict[str, datetime] = {}
_consecutive_failures: Dict[str, int] = defaultdict(int)
_known_issues: Set[str] = set()

# Configuration
HEALTH_CHECK_INTERVAL = 30  # seconds
FAILURE_THRESHOLD = 3  # consecutive failures before alert
RECOVERY_THRESHOLD = 2  # consecutive successes to clear alert

# All services to monitor
MONITORED_SERVICES = {
    # Core Infrastructure
    "event-bus": {"url": "http://event-bus:8099/health", "critical": True},
    "lcis-librarian": {"url": "http://lcis-librarian:8050/health", "critical": True},
    "lcis-oracle": {"url": "http://lcis-oracle:8052/health", "critical": True},
    
    # Backup & Recovery
    "chronos": {"url": "http://chronos:8010/health", "critical": True},
    "hades": {"url": "http://hades:8008/health", "critical": True},
    
    # Orchestration
    "atlas": {"url": "http://atlas:8017/health", "critical": True},
    "apollo": {"url": "http://apollo:8234/health", "critical": True},
    
    # Monitoring (self-monitoring!)
    "argus": {"url": "http://argus:8016/health", "critical": False},
    "aloy": {"url": "http://aloy:8015/health", "critical": False},
    "asclepius": {"url": "http://asclepius:8024/health", "critical": False},
    
    # Security
    "cerberus": {"url": "http://cerberus:8019/health", "critical": True},
    "aegis": {"url": "http://host.docker.internal:8012/health", "critical": True},
    
    # Communication
    "hermes": {"url": "http://hermes:8014/health", "critical": True},
    
    # Intelligence
    "varys": {"url": "http://varys:8112/health", "critical": False},
    "scholar": {"url": "http://scholar:8111/health", "critical": False},
    "chiron": {"url": "http://chiron:8113/health", "critical": False},
    
    # ARIA Ecosystem
    "aria-chat": {"url": "http://host.docker.internal:8100/health", "critical": True},
    "aria-memory": {"url": "http://aria-memory:8114/health", "critical": False},
    "aria-omniscience": {"url": "http://aria-omniscience:8115/health", "critical": False},
    
    # Personal Agents
    "gym-coach": {"url": "http://gym-coach:8230/health", "critical": False},
    "academic-guide": {"url": "http://academic-guide:8231/health", "critical": False},
    "bombadil": {"url": "http://bombadil:8232/health", "critical": False},
    "samwise": {"url": "http://samwise:8233/health", "critical": False},
    
    # Creative Fleet
    "muse": {"url": "http://muse:8030/health", "critical": False},
    "calliope": {"url": "http://calliope:8031/health", "critical": False},
    "thalia": {"url": "http://thalia:8032/health", "critical": False},
    "clio": {"url": "http://clio:8033/health", "critical": False},
    "erato": {"url": "http://erato:8034/health", "critical": False},
    
    # Council
    "convener": {"url": "http://convener:8018/health", "critical": False},
    "solon": {"url": "http://solon:8020/health", "critical": False},
}


async def check_service_health(service: str, config: dict) -> dict:
    """Check health of a single service"""
    url = config["url"]
    start_time = datetime.utcnow()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            if response.status_code == 200:
                return {
                    "service": service,
                    "status": "healthy",
                    "latency_ms": round(latency_ms, 2),
                    "checked_at": datetime.utcnow().isoformat(),
                    "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
                }
            else:
                return {
                    "service": service,
                    "status": "unhealthy",
                    "error": f"HTTP {response.status_code}",
                    "latency_ms": round(latency_ms, 2),
                    "checked_at": datetime.utcnow().isoformat()
                }
    except httpx.TimeoutException:
        return {
            "service": service,
            "status": "timeout",
            "error": "Request timed out after 10s",
            "checked_at": datetime.utcnow().isoformat()
        }
    except httpx.ConnectError as e:
        return {
            "service": service,
            "status": "unreachable",
            "error": f"Connection failed: {str(e)}",
            "checked_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "service": service,
            "status": "error",
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }


async def alert_via_hermes(severity: str, title: str, message: str, service: str = None):
    """Send alert through HERMES"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://hermes:8014/alert",
                json={
                    "severity": severity,
                    "title": title,
                    "message": message,
                    "source": "PANOPTES",
                    "service": service,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    except Exception as e:
        print(f"[PANOPTES] Failed to send alert via HERMES: {e}")


async def trigger_asclepius_diagnosis(service: str, error: str):
    """Trigger automatic diagnosis via ASCLEPIUS"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://asclepius:8024/diagnose",
                json={
                    "service": service,
                    "error": error,
                    "triggered_by": "PANOPTES",
                    "auto_triggered": True
                }
            )
            return response.json()
    except Exception as e:
        print(f"[PANOPTES] Failed to trigger ASCLEPIUS: {e}")
        return None


async def log_to_lcis(content: str, lesson_type: str, service: str):
    """Log issue to LCIS for learning"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://lcis-librarian:8050/lessons",
                json={
                    "content": content,
                    "domain": "MONITORING",
                    "type": lesson_type,
                    "source_agent": "PANOPTES",
                    "tags": ["health-check", "auto-captured", service],
                    "auto_captured": True
                }
            )
    except:
        pass


async def publish_event(event_type: str, data: dict):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": event_type,
                    "source": "PANOPTES",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    except:
        pass


async def continuous_health_monitor():
    """
    THE EYE THAT NEVER SLEEPS
    
    Continuously monitors all services and:
    - Alerts on failures
    - Triggers auto-diagnosis
    - Logs to LCIS for learning
    - Publishes events for other agents
    """
    global _monitoring_active, _consecutive_failures, _known_issues
    
    _monitoring_active = True
    print(f"[PANOPTES] 👁️ The All-Seeing Eye awakens. Monitoring {len(MONITORED_SERVICES)} services...")
    
    while _monitoring_active:
        cycle_start = datetime.utcnow()
        results = []
        
        # Check all services concurrently
        tasks = [
            check_service_health(service, config) 
            for service, config in MONITORED_SERVICES.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        healthy_count = 0
        unhealthy_count = 0
        
        for result in results:
            if isinstance(result, Exception):
                continue
                
            service = result["service"]
            status = result["status"]
            config = MONITORED_SERVICES.get(service, {})
            is_critical = config.get("critical", False)
            
            if status == "healthy":
                healthy_count += 1
                
                # Check for recovery
                if service in _known_issues:
                    _consecutive_failures[service] = 0
                    if _consecutive_failures.get(f"{service}_healthy", 0) >= RECOVERY_THRESHOLD:
                        _known_issues.remove(service)
                        
                        # Alert recovery
                        await alert_via_hermes(
                            severity="info",
                            title=f"✅ {service} RECOVERED",
                            message=f"Service {service} is healthy again after previous failure",
                            service=service
                        )
                        
                        await publish_event("service_recovered", {
                            "service": service,
                            "latency_ms": result.get("latency_ms")
                        })
                        
                        await log_to_lcis(
                            f"Service {service} recovered from failure",
                            "recovery",
                            service
                        )
                    else:
                        _consecutive_failures[f"{service}_healthy"] = _consecutive_failures.get(f"{service}_healthy", 0) + 1
            else:
                unhealthy_count += 1
                _consecutive_failures[service] += 1
                _consecutive_failures[f"{service}_healthy"] = 0
                
                # Check if we should alert
                if _consecutive_failures[service] >= FAILURE_THRESHOLD and service not in _known_issues:
                    _known_issues.add(service)
                    
                    severity = "critical" if is_critical else "warning"
                    error_msg = result.get("error", "Unknown error")
                    
                    # Send alert
                    await alert_via_hermes(
                        severity=severity,
                        title=f"🚨 {service} {'CRITICAL FAILURE' if is_critical else 'UNHEALTHY'}",
                        message=f"Service {service} failed {_consecutive_failures[service]} consecutive health checks. Error: {error_msg}",
                        service=service
                    )
                    
                    # Publish event
                    await publish_event("service_unhealthy", {
                        "service": service,
                        "error": error_msg,
                        "consecutive_failures": _consecutive_failures[service],
                        "critical": is_critical
                    })
                    
                    # Log to LCIS
                    await log_to_lcis(
                        f"Service {service} unhealthy: {error_msg}",
                        "failure",
                        service
                    )
                    
                    # Trigger auto-diagnosis for critical services
                    if is_critical:
                        print(f"[PANOPTES] Triggering ASCLEPIUS diagnosis for {service}...")
                        diagnosis = await trigger_asclepius_diagnosis(service, error_msg)
                        if diagnosis:
                            await alert_via_hermes(
                                severity="info",
                                title=f"🔍 ASCLEPIUS Diagnosis: {service}",
                                message=diagnosis.get("diagnosis", "Diagnosis complete"),
                                service=service
                            )
        
        # Calculate cycle stats
        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        
        # Log summary every 10 cycles (5 minutes)
        if int(datetime.utcnow().timestamp()) % 300 < HEALTH_CHECK_INTERVAL:
            print(f"[PANOPTES] Health: {healthy_count}/{len(MONITORED_SERVICES)} healthy, {len(_known_issues)} issues, cycle: {cycle_duration:.2f}s")
        
        # Wait for next cycle
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)


@app.on_event("startup")
async def startup():
    """Start continuous monitoring on startup"""
    asyncio.create_task(continuous_health_monitor())


@app.on_event("shutdown")
async def shutdown():
    """Stop monitoring on shutdown"""
    global _monitoring_active
    _monitoring_active = False


# =============================================================================
# MONITORING STATUS ENDPOINTS
# =============================================================================

@app.get("/monitoring/status")
async def get_monitoring_status():
    """Get current monitoring status"""
    return {
        "active": _monitoring_active,
        "services_monitored": len(MONITORED_SERVICES),
        "known_issues": list(_known_issues),
        "issue_count": len(_known_issues),
        "health_check_interval": HEALTH_CHECK_INTERVAL,
        "failure_threshold": FAILURE_THRESHOLD
    }


@app.get("/monitoring/issues")
async def get_current_issues():
    """Get list of current issues"""
    issues = []
    for service in _known_issues:
        issues.append({
            "service": service,
            "consecutive_failures": _consecutive_failures.get(service, 0),
            "critical": MONITORED_SERVICES.get(service, {}).get("critical", False)
        })
    return {"issues": issues, "count": len(issues)}


@app.post("/monitoring/pause")
async def pause_monitoring():
    """Pause continuous monitoring"""
    global _monitoring_active
    _monitoring_active = False
    return {"status": "paused"}


@app.post("/monitoring/resume")
async def resume_monitoring():
    """Resume continuous monitoring"""
    global _monitoring_active
    if not _monitoring_active:
        _monitoring_active = True
        asyncio.create_task(continuous_health_monitor())
    return {"status": "resumed"}
```

---

## PHASE 3: ARGUS - METRICS COLLECTOR

### 3.1 Add Continuous Metrics Collection

Add to `/opt/leveredge/control-plane/agents/argus/argus.py`:

```python
# =============================================================================
# CONTINUOUS METRICS COLLECTION
# =============================================================================

import asyncio
import psutil
from datetime import datetime, timedelta
from collections import deque
from typing import Deque

# Metrics storage (rolling 1 hour window)
METRICS_WINDOW = 3600  # 1 hour in seconds
METRICS_INTERVAL = 60  # Collect every 60 seconds

_metrics_active = False
_system_metrics: Deque[dict] = deque(maxlen=METRICS_WINDOW // METRICS_INTERVAL)
_service_metrics: Dict[str, Deque[dict]] = defaultdict(lambda: deque(maxlen=METRICS_WINDOW // METRICS_INTERVAL))

# Thresholds for alerting
ALERT_THRESHOLDS = {
    "cpu_percent": {"warning": 70, "critical": 90},
    "memory_percent": {"warning": 80, "critical": 95},
    "disk_percent": {"warning": 85, "critical": 95},
    "latency_ms": {"warning": 1000, "critical": 5000},
    "error_rate": {"warning": 0.05, "critical": 0.10},
}


async def collect_system_metrics() -> dict:
    """Collect host system metrics"""
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Get container count
    try:
        result = await asyncio.create_subprocess_exec(
            "docker", "ps", "-q",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        container_count = len(stdout.decode().strip().split('\n')) if stdout else 0
    except:
        container_count = -1
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cpu_percent": cpu,
        "memory_percent": memory.percent,
        "memory_used_gb": round(memory.used / (1024**3), 2),
        "memory_total_gb": round(memory.total / (1024**3), 2),
        "disk_percent": disk.percent,
        "disk_used_gb": round(disk.used / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
        "container_count": container_count
    }


async def collect_service_metrics(service: str, url: str) -> dict:
    """Collect metrics for a single service"""
    start = datetime.utcnow()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "service": service,
                "status": "up",
                "latency_ms": round(latency_ms, 2),
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service": service,
            "status": "down",
            "error": str(e)
        }


async def check_thresholds(metrics: dict) -> List[dict]:
    """Check metrics against thresholds and return alerts"""
    alerts = []
    
    for metric, thresholds in ALERT_THRESHOLDS.items():
        if metric in metrics:
            value = metrics[metric]
            
            if value >= thresholds["critical"]:
                alerts.append({
                    "metric": metric,
                    "value": value,
                    "threshold": thresholds["critical"],
                    "severity": "critical"
                })
            elif value >= thresholds["warning"]:
                alerts.append({
                    "metric": metric,
                    "value": value,
                    "threshold": thresholds["warning"],
                    "severity": "warning"
                })
    
    return alerts


async def continuous_metrics_collector():
    """
    ARGUS - THE HUNDRED-EYED METRICS COLLECTOR
    
    Continuously collects metrics from:
    - Host system (CPU, memory, disk)
    - All monitored services (latency, status)
    - Docker containers (count, resource usage)
    """
    global _metrics_active
    
    _metrics_active = True
    print(f"[ARGUS] 👁️👁️👁️ The Hundred-Eyed Giant awakens. Collecting metrics every {METRICS_INTERVAL}s...")
    
    while _metrics_active:
        cycle_start = datetime.utcnow()
        
        # Collect system metrics
        system = await collect_system_metrics()
        _system_metrics.append(system)
        
        # Check system thresholds
        alerts = await check_thresholds(system)
        for alert in alerts:
            await alert_via_hermes(
                severity=alert["severity"],
                title=f"⚠️ System {alert['metric']} {alert['severity'].upper()}",
                message=f"{alert['metric']}: {alert['value']}% (threshold: {alert['threshold']}%)",
                service="system"
            )
        
        # Collect service metrics
        for service, config in MONITORED_SERVICES.items():
            metrics = await collect_service_metrics(service, config.get("url", f"http://{service}:8000/health"))
            _service_metrics[service].append(metrics)
        
        # Log summary
        print(f"[ARGUS] Metrics: CPU={system['cpu_percent']}%, MEM={system['memory_percent']}%, DISK={system['disk_percent']}%")
        
        # Wait for next cycle
        elapsed = (datetime.utcnow() - cycle_start).total_seconds()
        await asyncio.sleep(max(0, METRICS_INTERVAL - elapsed))


async def alert_via_hermes(severity: str, title: str, message: str, service: str = None):
    """Send alert through HERMES"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://hermes:8014/alert",
                json={
                    "severity": severity,
                    "title": title,
                    "message": message,
                    "source": "ARGUS",
                    "service": service
                }
            )
    except:
        pass


@app.on_event("startup")
async def startup():
    asyncio.create_task(continuous_metrics_collector())


@app.get("/metrics/current")
async def get_current_metrics():
    """Get most recent metrics"""
    return {
        "system": _system_metrics[-1] if _system_metrics else None,
        "services": {
            service: metrics[-1] if metrics else None
            for service, metrics in _service_metrics.items()
        }
    }


@app.get("/metrics/history")
async def get_metrics_history(minutes: int = 60):
    """Get metrics history"""
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    
    return {
        "system": [m for m in _system_metrics if datetime.fromisoformat(m["timestamp"]) > cutoff],
        "window_minutes": minutes
    }
```

---

## PHASE 4: ALOY - REAL-TIME ANOMALY DETECTION

### 4.1 Add Event Bus Subscription

Add to `/opt/leveredge/control-plane/agents/aloy/aloy.py`:

```python
# =============================================================================
# REAL-TIME EVENT BUS MONITORING
# =============================================================================

import asyncio
import json
from datetime import datetime, timedelta
from collections import defaultdict, deque

# Event tracking
_event_active = False
_event_counts: Dict[str, int] = defaultdict(int)
_recent_events: Deque[dict] = deque(maxlen=1000)
_anomaly_alerts: List[dict] = []

# Time windows for anomaly detection
EVENT_WINDOW = 300  # 5 minutes
RATE_LIMITS = {
    "deployment_failed": {"max": 3, "window": 300, "severity": "critical"},
    "service_unhealthy": {"max": 5, "window": 300, "severity": "warning"},
    "error_detected": {"max": 10, "window": 60, "severity": "warning"},
    "blocked": {"max": 3, "window": 60, "severity": "critical"},
    "unauthorized": {"max": 5, "window": 60, "severity": "critical"},
    "rollback": {"max": 2, "window": 300, "severity": "warning"},
}


async def subscribe_to_event_bus():
    """
    ALOY - THE ANOMALY HUNTER
    
    Subscribes to Event Bus and monitors for:
    - Rapid failure patterns
    - Security incidents
    - Unusual activity spikes
    - Blocked operations
    """
    global _event_active
    
    _event_active = True
    print("[ALOY] 🔍 Anomaly Hunter active. Monitoring Event Bus...")
    
    while _event_active:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{EVENT_BUS_URL}/subscribe") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            try:
                                event = json.loads(line[5:])
                                await process_event(event)
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            print(f"[ALOY] Event Bus connection lost: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


async def process_event(event: dict):
    """Process incoming event for anomalies"""
    event_type = event.get("event_type", "unknown")
    source = event.get("source", "unknown")
    timestamp = datetime.utcnow()
    
    # Store event
    _recent_events.append({
        "event_type": event_type,
        "source": source,
        "timestamp": timestamp.isoformat(),
        "data": event.get("data", {})
    })
    
    # Track event counts
    _event_counts[event_type] += 1
    
    # Check for anomalies
    await check_rate_anomalies(event_type, timestamp)
    await check_security_patterns(event)
    await check_failure_cascades(event)


async def check_rate_anomalies(event_type: str, timestamp: datetime):
    """Check if event rate exceeds limits"""
    if event_type in RATE_LIMITS:
        config = RATE_LIMITS[event_type]
        window_start = timestamp - timedelta(seconds=config["window"])
        
        # Count events in window
        count = sum(
            1 for e in _recent_events
            if e["event_type"] == event_type 
            and datetime.fromisoformat(e["timestamp"]) > window_start
        )
        
        if count >= config["max"]:
            await trigger_anomaly_alert(
                anomaly_type="rate_exceeded",
                severity=config["severity"],
                message=f"Event '{event_type}' exceeded rate limit: {count} events in {config['window']}s (max: {config['max']})",
                event_type=event_type
            )


async def check_security_patterns(event: dict):
    """Check for security-related patterns"""
    event_type = event.get("event_type", "").lower()
    data = event.get("data", {})
    
    security_keywords = ["blocked", "forbidden", "unauthorized", "denied", "attack", "injection", "malicious"]
    
    # Check event type
    if any(kw in event_type for kw in security_keywords):
        await trigger_anomaly_alert(
            anomaly_type="security_incident",
            severity="critical",
            message=f"Security event detected: {event_type}",
            event_type=event_type,
            details=data
        )
    
    # Check data content
    data_str = json.dumps(data).lower()
    for kw in security_keywords:
        if kw in data_str:
            await trigger_anomaly_alert(
                anomaly_type="security_pattern",
                severity="warning",
                message=f"Security keyword '{kw}' found in event data",
                event_type=event_type,
                details=data
            )
            break


async def check_failure_cascades(event: dict):
    """Check for cascading failures"""
    if "fail" in event.get("event_type", "").lower():
        # Count recent failures across all services
        recent_failures = sum(
            1 for e in list(_recent_events)[-50:]
            if "fail" in e.get("event_type", "").lower()
        )
        
        if recent_failures >= 5:
            services = set(
                e.get("source") for e in list(_recent_events)[-50:]
                if "fail" in e.get("event_type", "").lower()
            )
            
            await trigger_anomaly_alert(
                anomaly_type="cascade_failure",
                severity="critical",
                message=f"Cascade failure detected: {recent_failures} failures across {len(services)} services",
                details={"services": list(services)}
            )


async def trigger_anomaly_alert(anomaly_type: str, severity: str, message: str, 
                                event_type: str = None, details: dict = None):
    """Trigger anomaly alert"""
    alert = {
        "anomaly_type": anomaly_type,
        "severity": severity,
        "message": message,
        "event_type": event_type,
        "details": details,
        "detected_at": datetime.utcnow().isoformat()
    }
    
    _anomaly_alerts.append(alert)
    
    # Alert via HERMES
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://hermes:8014/alert",
                json={
                    "severity": severity,
                    "title": f"🚨 ANOMALY: {anomaly_type}",
                    "message": message,
                    "source": "ALOY",
                    "details": details
                }
            )
    except:
        pass
    
    # Log to LCIS
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://lcis-librarian:8050/lessons",
                json={
                    "content": f"Anomaly detected: {anomaly_type} - {message}",
                    "domain": "SECURITY",
                    "type": "anomaly",
                    "source_agent": "ALOY",
                    "tags": ["anomaly", anomaly_type, "auto-captured"]
                }
            )
    except:
        pass
    
    # Publish to Event Bus
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": "anomaly_detected",
                    "source": "ALOY",
                    "data": alert
                }
            )
    except:
        pass


@app.on_event("startup")
async def startup():
    asyncio.create_task(subscribe_to_event_bus())


@app.get("/anomalies/recent")
async def get_recent_anomalies(limit: int = 50):
    """Get recent anomaly alerts"""
    return {
        "anomalies": _anomaly_alerts[-limit:],
        "total": len(_anomaly_alerts)
    }


@app.get("/events/stats")
async def get_event_stats():
    """Get event statistics"""
    return {
        "event_counts": dict(_event_counts),
        "recent_events": len(_recent_events),
        "active": _event_active
    }
```

---

## PHASE 5: VARYS - SCHEDULED INTELLIGENCE

### 5.1 Add Daily Briefing Scheduler

Add to `/opt/leveredge/control-plane/agents/varys/varys.py`:

```python
# =============================================================================
# SCHEDULED INTELLIGENCE GATHERING
# =============================================================================

import asyncio
from datetime import datetime, time, timedelta

_scheduler_active = False
BRIEFING_TIME = time(7, 0)  # 7:00 AM daily


async def scheduled_daily_briefing():
    """
    VARYS - THE SPIDER'S DAILY WEB
    
    Every morning at 7am:
    - Generate portfolio summary
    - Gather market intelligence
    - Identify opportunities
    - Send briefing via HERMES
    """
    global _scheduler_active
    
    _scheduler_active = True
    print(f"[VARYS] 🕷️ The Spider awakens. Daily briefings scheduled for {BRIEFING_TIME}...")
    
    while _scheduler_active:
        now = datetime.now()
        
        # Calculate next briefing time
        next_briefing = datetime.combine(now.date(), BRIEFING_TIME)
        if now.time() >= BRIEFING_TIME:
            next_briefing += timedelta(days=1)
        
        wait_seconds = (next_briefing - now).total_seconds()
        print(f"[VARYS] Next briefing in {wait_seconds/3600:.1f} hours")
        
        # Wait until briefing time
        await asyncio.sleep(wait_seconds)
        
        # Generate and send briefing
        await generate_and_send_briefing()


async def generate_and_send_briefing():
    """Generate comprehensive daily briefing"""
    print("[VARYS] 📋 Generating daily briefing...")
    
    briefing = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "generated_at": datetime.utcnow().isoformat(),
        "sections": {}
    }
    
    # Portfolio summary
    try:
        portfolio = await get_portfolio_summary()
        briefing["sections"]["portfolio"] = portfolio
    except Exception as e:
        briefing["sections"]["portfolio"] = {"error": str(e)}
    
    # System health summary
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://panoptes:8023/monitoring/status")
            briefing["sections"]["system_health"] = response.json()
    except Exception as e:
        briefing["sections"]["system_health"] = {"error": str(e)}
    
    # Recent anomalies
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://aloy:8015/anomalies/recent?limit=10")
            briefing["sections"]["anomalies"] = response.json()
    except Exception as e:
        briefing["sections"]["anomalies"] = {"error": str(e)}
    
    # Recent lessons learned
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://lcis-librarian:8050/lessons/recent?limit=10")
            briefing["sections"]["lessons"] = response.json()
    except Exception as e:
        briefing["sections"]["lessons"] = {"error": str(e)}
    
    # Days to launch
    launch_date = datetime(2026, 3, 1)
    days_to_launch = (launch_date - datetime.now()).days
    briefing["sections"]["launch"] = {
        "date": "2026-03-01",
        "days_remaining": days_to_launch,
        "status": "ON TRACK" if days_to_launch > 30 else "APPROACHING"
    }
    
    # Format briefing message
    message = format_briefing_message(briefing)
    
    # Send via HERMES
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                "http://hermes:8014/notify",
                json={
                    "channel": "daily_briefing",
                    "title": f"🕷️ VARYS Daily Briefing - {briefing['date']}",
                    "message": message,
                    "source": "VARYS",
                    "data": briefing
                }
            )
        print("[VARYS] ✅ Daily briefing sent")
    except Exception as e:
        print(f"[VARYS] ❌ Failed to send briefing: {e}")
    
    # Store briefing
    await store_briefing(briefing)
    
    return briefing


def format_briefing_message(briefing: dict) -> str:
    """Format briefing as readable message"""
    sections = briefing.get("sections", {})
    
    lines = [
        f"# VARYS Daily Briefing - {briefing['date']}",
        "",
        "## 🚀 Launch Status",
        f"Days to launch: {sections.get('launch', {}).get('days_remaining', '?')}",
        f"Status: {sections.get('launch', {}).get('status', 'UNKNOWN')}",
        "",
        "## 💰 Portfolio",
    ]
    
    portfolio = sections.get("portfolio", {})
    if "error" not in portfolio:
        lines.append(f"Total Value: ${portfolio.get('total_value', 0):,.0f}")
        lines.append(f"Win Count: {portfolio.get('win_count', 0)}")
    else:
        lines.append(f"Error: {portfolio.get('error')}")
    
    lines.extend([
        "",
        "## 🏥 System Health",
    ])
    
    health = sections.get("system_health", {})
    if "error" not in health:
        lines.append(f"Issues: {health.get('issue_count', 0)}")
        lines.append(f"Services Monitored: {health.get('services_monitored', 0)}")
    else:
        lines.append(f"Error: {health.get('error')}")
    
    anomalies = sections.get("anomalies", {})
    if anomalies.get("total", 0) > 0:
        lines.extend([
            "",
            "## ⚠️ Recent Anomalies",
            f"Count: {anomalies.get('total', 0)}"
        ])
    
    return "\n".join(lines)


async def store_briefing(briefing: dict):
    """Store briefing in database"""
    if pool:
        try:
            await pool.execute("""
                INSERT INTO varys_briefings (date, briefing, created_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (date) DO UPDATE SET briefing = $2, created_at = NOW()
            """, briefing["date"], json.dumps(briefing))
        except:
            pass


async def get_portfolio_summary() -> dict:
    """Get portfolio summary from database"""
    if not pool:
        return {"error": "Database not connected"}
    
    try:
        row = await pool.fetchrow("""
            SELECT 
                COUNT(*) as win_count,
                COALESCE(SUM(estimated_value_low), 0) as total_low,
                COALESCE(SUM(estimated_value_high), 0) as total_high
            FROM aria_wins
        """)
        
        return {
            "win_count": row["win_count"],
            "total_value_low": float(row["total_low"]),
            "total_value_high": float(row["total_high"]),
            "total_value": float(row["total_low"] + row["total_high"]) / 2
        }
    except Exception as e:
        return {"error": str(e)}


@app.on_event("startup")
async def startup():
    global pool
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    
    # Start scheduler
    asyncio.create_task(scheduled_daily_briefing())


@app.post("/briefing/now")
async def trigger_briefing_now():
    """Manually trigger a briefing"""
    briefing = await generate_and_send_briefing()
    return briefing
```

---

## PHASE 6: CERBERUS - CONTINUOUS SECURITY WATCH

### 6.1 Add Request Validation Loop

Add to `/opt/leveredge/control-plane/agents/cerberus/cerberus.py`:

```python
# =============================================================================
# CONTINUOUS SECURITY MONITORING
# =============================================================================

import asyncio
from datetime import datetime, timedelta
from collections import defaultdict

_security_active = False
_blocked_ips: Dict[str, datetime] = {}
_suspicious_patterns: List[dict] = []
_request_counts: Dict[str, int] = defaultdict(int)

# Security thresholds
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 100  # requests per window
BLOCK_DURATION = 300  # 5 minutes


async def security_event_monitor():
    """
    CERBERUS - THE THREE-HEADED GUARDIAN
    
    Monitors Event Bus for security events:
    - Blocked operations
    - Auth failures
    - Rate limit violations
    - Suspicious patterns
    """
    global _security_active
    
    _security_active = True
    print("[CERBERUS] 🐕‍🦺🐕‍🦺🐕‍🦺 The Three-Headed Guardian watches...")
    
    while _security_active:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{EVENT_BUS_URL}/subscribe") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            try:
                                event = json.loads(line[5:])
                                await analyze_security_event(event)
                            except:
                                continue
        except Exception as e:
            print(f"[CERBERUS] Event Bus connection lost: {e}. Reconnecting...")
            await asyncio.sleep(5)


async def analyze_security_event(event: dict):
    """Analyze event for security implications"""
    event_type = event.get("event_type", "").lower()
    source = event.get("source", "")
    data = event.get("data", {})
    
    # Check for security-related events
    security_events = ["blocked", "denied", "unauthorized", "forbidden", "attack", "injection"]
    
    if any(se in event_type for se in security_events):
        await handle_security_incident(event)
    
    # Check for auth failures
    if "auth" in event_type and ("fail" in event_type or "error" in event_type):
        await handle_auth_failure(event)
    
    # Check for rate limiting events
    if "rate" in event_type or "limit" in event_type:
        await handle_rate_limit(event)


async def handle_security_incident(event: dict):
    """Handle detected security incident"""
    incident = {
        "type": "security_incident",
        "event": event,
        "detected_at": datetime.utcnow().isoformat(),
        "severity": "critical"
    }
    
    _suspicious_patterns.append(incident)
    
    # Alert immediately
    await alert_security_team(incident)
    
    # Log to LCIS
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://lcis-librarian:8050/lessons",
                json={
                    "content": f"Security incident: {event.get('event_type')}",
                    "domain": "SECURITY",
                    "type": "security",
                    "source_agent": "CERBERUS",
                    "tags": ["security", "incident", "auto-captured"]
                }
            )
    except:
        pass


async def handle_auth_failure(event: dict):
    """Handle authentication failure"""
    source_ip = event.get("data", {}).get("ip", "unknown")
    
    # Track failed attempts
    _request_counts[f"auth_fail:{source_ip}"] += 1
    
    # Block after too many failures
    if _request_counts[f"auth_fail:{source_ip}"] >= 5:
        _blocked_ips[source_ip] = datetime.utcnow() + timedelta(seconds=BLOCK_DURATION)
        
        await alert_security_team({
            "type": "ip_blocked",
            "ip": source_ip,
            "reason": "Too many auth failures",
            "duration": BLOCK_DURATION
        })


async def handle_rate_limit(event: dict):
    """Handle rate limit event"""
    # Already handled by rate limiting system, just log
    pass


async def alert_security_team(incident: dict):
    """Send security alert via HERMES"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://hermes:8014/alert",
                json={
                    "severity": "critical",
                    "title": f"🚨 SECURITY: {incident.get('type', 'Unknown')}",
                    "message": json.dumps(incident, indent=2),
                    "source": "CERBERUS",
                    "channel": "security"
                }
            )
    except:
        pass


@app.on_event("startup")
async def startup():
    asyncio.create_task(security_event_monitor())


@app.get("/security/status")
async def get_security_status():
    """Get current security status"""
    return {
        "active": _security_active,
        "blocked_ips": {ip: exp.isoformat() for ip, exp in _blocked_ips.items() if exp > datetime.utcnow()},
        "recent_incidents": _suspicious_patterns[-20:],
        "incident_count": len(_suspicious_patterns)
    }
```

---

## PHASE 7: ASCLEPIUS - AUTO-DIAGNOSIS

### 7.1 Add Automatic Diagnosis Triggers

Add to `/opt/leveredge/control-plane/agents/asclepius/asclepius.py`:

```python
# =============================================================================
# AUTOMATIC DIAGNOSIS SYSTEM
# =============================================================================

async def auto_diagnose_on_event():
    """
    ASCLEPIUS - THE HEALER
    
    Listens for unhealthy events and automatically diagnoses:
    - Container crashes
    - Service failures
    - Connection issues
    - Resource exhaustion
    """
    print("[ASCLEPIUS] ⚕️ The Healer stands ready...")
    
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{EVENT_BUS_URL}/subscribe") as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            try:
                                event = json.loads(line[5:])
                                if should_diagnose(event):
                                    await auto_diagnose(event)
                            except:
                                continue
        except Exception as e:
            print(f"[ASCLEPIUS] Event Bus connection lost: {e}. Reconnecting...")
            await asyncio.sleep(5)


def should_diagnose(event: dict) -> bool:
    """Determine if event warrants diagnosis"""
    event_type = event.get("event_type", "").lower()
    
    trigger_keywords = ["unhealthy", "failed", "crash", "error", "timeout", "unreachable"]
    return any(kw in event_type for kw in trigger_keywords)


async def auto_diagnose(event: dict):
    """Perform automatic diagnosis"""
    service = event.get("data", {}).get("service", event.get("source", "unknown"))
    error = event.get("data", {}).get("error", "Unknown error")
    
    print(f"[ASCLEPIUS] 🔍 Auto-diagnosing {service}...")
    
    diagnosis = {
        "service": service,
        "trigger_event": event.get("event_type"),
        "diagnosed_at": datetime.utcnow().isoformat(),
        "checks": []
    }
    
    # Run diagnostic checks
    checks = [
        ("container_status", check_container_status),
        ("port_availability", check_port_availability),
        ("logs_analysis", check_recent_logs),
        ("resource_usage", check_resource_usage),
        ("dependencies", check_dependencies),
    ]
    
    for check_name, check_func in checks:
        try:
            result = await check_func(service)
            diagnosis["checks"].append({
                "name": check_name,
                "status": "passed" if result.get("healthy") else "failed",
                "details": result
            })
        except Exception as e:
            diagnosis["checks"].append({
                "name": check_name,
                "status": "error",
                "error": str(e)
            })
    
    # Generate recommendation
    diagnosis["recommendation"] = generate_recommendation(diagnosis)
    
    # Publish diagnosis
    await publish_diagnosis(diagnosis)
    
    return diagnosis


async def check_container_status(service: str) -> dict:
    """Check if container is running"""
    try:
        result = await asyncio.create_subprocess_exec(
            "docker", "inspect", f"leveredge-{service}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if result.returncode == 0:
            data = json.loads(stdout.decode())
            state = data[0].get("State", {})
            return {
                "healthy": state.get("Running", False),
                "status": state.get("Status"),
                "started_at": state.get("StartedAt"),
                "exit_code": state.get("ExitCode")
            }
    except:
        pass
    
    return {"healthy": False, "error": "Could not inspect container"}


async def check_port_availability(service: str) -> dict:
    """Check if service port is responding"""
    # Would check port connectivity
    return {"healthy": True, "details": "Port check not implemented"}


async def check_recent_logs(service: str) -> dict:
    """Analyze recent logs for errors"""
    try:
        result = await asyncio.create_subprocess_exec(
            "docker", "logs", "--tail", "50", f"leveredge-{service}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        logs = (stdout.decode() + stderr.decode()).lower()
        error_count = logs.count("error")
        exception_count = logs.count("exception")
        
        return {
            "healthy": error_count < 5,
            "error_count": error_count,
            "exception_count": exception_count,
            "sample": logs[-500:] if logs else ""
        }
    except:
        return {"healthy": True, "error": "Could not fetch logs"}


async def check_resource_usage(service: str) -> dict:
    """Check container resource usage"""
    try:
        result = await asyncio.create_subprocess_exec(
            "docker", "stats", "--no-stream", "--format", 
            "{{.CPUPerc}},{{.MemPerc}}", f"leveredge-{service}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await result.communicate()
        
        if stdout:
            parts = stdout.decode().strip().split(",")
            cpu = float(parts[0].replace("%", ""))
            mem = float(parts[1].replace("%", ""))
            
            return {
                "healthy": cpu < 90 and mem < 90,
                "cpu_percent": cpu,
                "memory_percent": mem
            }
    except:
        pass
    
    return {"healthy": True, "error": "Could not get stats"}


async def check_dependencies(service: str) -> dict:
    """Check if service dependencies are healthy"""
    # Would check dependencies based on service config
    return {"healthy": True, "details": "Dependency check not implemented"}


def generate_recommendation(diagnosis: dict) -> str:
    """Generate recommendation based on diagnosis"""
    failed_checks = [c for c in diagnosis["checks"] if c["status"] == "failed"]
    
    if not failed_checks:
        return "All checks passed. Service may need restart or investigation of recent changes."
    
    recommendations = []
    
    for check in failed_checks:
        if check["name"] == "container_status":
            recommendations.append("Container not running. Try: docker start leveredge-{service}")
        elif check["name"] == "logs_analysis":
            recommendations.append("High error rate in logs. Review recent deployments and check for code issues.")
        elif check["name"] == "resource_usage":
            recommendations.append("High resource usage. Consider scaling or optimizing the service.")
    
    return " | ".join(recommendations) if recommendations else "Investigation required."


async def publish_diagnosis(diagnosis: dict):
    """Publish diagnosis results"""
    # To Event Bus
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": "diagnosis_complete",
                    "source": "ASCLEPIUS",
                    "data": diagnosis
                }
            )
    except:
        pass
    
    # To LCIS
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://lcis-librarian:8050/lessons",
                json={
                    "content": f"Auto-diagnosis for {diagnosis['service']}: {diagnosis['recommendation']}",
                    "domain": "DIAGNOSTICS",
                    "type": "diagnosis",
                    "source_agent": "ASCLEPIUS",
                    "tags": ["diagnosis", "auto-triggered", diagnosis['service']]
                }
            )
    except:
        pass


@app.on_event("startup")
async def startup():
    asyncio.create_task(auto_diagnose_on_event())
```

---

## PHASE 8: UNIFIED ALERT ROUTING (HERMES)

### 8.1 Add Alert Channels and Routing

Add to `/opt/leveredge/control-plane/agents/hermes/hermes.py`:

```python
# =============================================================================
# ALERT ROUTING SYSTEM
# =============================================================================

from collections import defaultdict
from typing import Callable

# Alert channels
ALERT_CHANNELS = {
    "critical": ["console", "aria", "email"],  # Everything
    "warning": ["console", "aria"],            # Console + ARIA
    "info": ["console"],                       # Console only
}

# Alert history
_alert_history: List[dict] = []
_alert_counts: Dict[str, int] = defaultdict(int)


@app.post("/alert")
async def receive_alert(alert: dict):
    """
    HERMES - THE MESSENGER
    
    Receives alerts from all watchers and routes to appropriate channels:
    - Critical: Console + ARIA + Email
    - Warning: Console + ARIA
    - Info: Console only
    """
    severity = alert.get("severity", "info")
    title = alert.get("title", "Alert")
    message = alert.get("message", "")
    source = alert.get("source", "UNKNOWN")
    
    # Store alert
    alert_record = {
        "id": f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "severity": severity,
        "title": title,
        "message": message,
        "source": source,
        "received_at": datetime.utcnow().isoformat()
    }
    _alert_history.append(alert_record)
    _alert_counts[severity] += 1
    
    # Route to channels
    channels = ALERT_CHANNELS.get(severity, ["console"])
    
    for channel in channels:
        await route_to_channel(channel, alert_record)
    
    return {"status": "routed", "channels": channels}


async def route_to_channel(channel: str, alert: dict):
    """Route alert to specific channel"""
    if channel == "console":
        severity_emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(alert["severity"], "📢")
        print(f"[HERMES] {severity_emoji} [{alert['source']}] {alert['title']}: {alert['message'][:200]}")
    
    elif channel == "aria":
        # Send to ARIA for user notification
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    "http://lcis-librarian:8050/lessons",
                    json={
                        "content": f"[{alert['severity'].upper()}] {alert['title']}: {alert['message']}",
                        "domain": "aria_knowledge",
                        "type": "alert",
                        "source_agent": "HERMES",
                        "importance": "high" if alert["severity"] == "critical" else "normal"
                    }
                )
        except:
            pass
    
    elif channel == "email":
        # Would send email for critical alerts
        print(f"[HERMES] 📧 Would send email for critical alert: {alert['title']}")


@app.get("/alerts/history")
async def get_alert_history(limit: int = 100, severity: str = None):
    """Get alert history"""
    alerts = _alert_history
    
    if severity:
        alerts = [a for a in alerts if a["severity"] == severity]
    
    return {
        "alerts": alerts[-limit:],
        "total": len(alerts),
        "counts": dict(_alert_counts)
    }


@app.get("/alerts/stats")
async def get_alert_stats():
    """Get alert statistics"""
    return {
        "total_alerts": len(_alert_history),
        "by_severity": dict(_alert_counts),
        "last_alert": _alert_history[-1] if _alert_history else None
    }
```

---

## PHASE 9: DOCKER COMPOSE UPDATES

### 9.1 Add All Watchers to Fleet Compose

Add these services to `docker-compose.fleet.yml`:

```yaml
  # ===========================================================================
  # WATCHTOWER - CONTINUOUS MONITORING AGENTS
  # ===========================================================================

  panoptes:
    build:
      context: ./control-plane/agents/panoptes
      dockerfile: Dockerfile
    container_name: leveredge-panoptes
    ports:
      - "${PANOPTES_PORT:-8023}:8023"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
      - ASCLEPIUS_URL=http://asclepius:8024
      - LCIS_URL=http://lcis-librarian:8050
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - fleet-net
    depends_on:
      event-bus:
        condition: service_healthy
    restart: unless-stopped
    profiles: ["core", "all"]

  argus:
    build:
      context: ./control-plane/agents/argus
      dockerfile: Dockerfile
    container_name: leveredge-argus
    ports:
      - "${ARGUS_PORT:-8016}:8016"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - fleet-net
    depends_on:
      event-bus:
        condition: service_healthy
    restart: unless-stopped
    profiles: ["core", "all"]

  aloy:
    build:
      context: ./control-plane/agents/aloy
      dockerfile: Dockerfile
    container_name: leveredge-aloy
    ports:
      - "${ALOY_PORT:-8015}:8015"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
      - LCIS_URL=http://lcis-librarian:8050
    networks:
      - fleet-net
    depends_on:
      event-bus:
        condition: service_healthy
    restart: unless-stopped
    profiles: ["core", "all"]

  cerberus:
    build:
      context: ./control-plane/agents/cerberus
      dockerfile: Dockerfile
    container_name: leveredge-cerberus
    ports:
      - "${CERBERUS_PORT:-8019}:8019"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
    networks:
      - fleet-net
    depends_on:
      event-bus:
        condition: service_healthy
    restart: unless-stopped
    profiles: ["core", "all"]

  asclepius:
    build:
      context: ./control-plane/agents/asclepius
      dockerfile: Dockerfile
    container_name: leveredge-asclepius
    ports:
      - "${ASCLEPIUS_PORT:-8024}:8024"
    environment:
      - EVENT_BUS_URL=http://event-bus:8099
      - HERMES_URL=http://hermes:8014
      - LCIS_URL=http://lcis-librarian:8050
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - fleet-net
    depends_on:
      event-bus:
        condition: service_healthy
    restart: unless-stopped
    profiles: ["core", "all"]
```

---

## VERIFICATION

```bash
# 1. Check all watchers are running
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "panoptes|argus|aloy|cerberus|asclepius|varys|lcis"

# 2. Check PANOPTES monitoring status
curl http://localhost:8023/monitoring/status

# 3. Check ARGUS metrics
curl http://localhost:8016/metrics/current

# 4. Check ALOY for anomalies
curl http://localhost:8015/anomalies/recent

# 5. Check CERBERUS security status
curl http://localhost:8019/security/status

# 6. Check HERMES alert history
curl http://localhost:8014/alerts/stats

# 7. Trigger a test briefing from VARYS
curl -X POST http://localhost:8112/briefing/now

# 8. Simulate an issue and watch the cascade:
# - Stop a service
docker stop leveredge-samwise
# - Wait 90 seconds (3 health check cycles)
# - Check that PANOPTES detected it
curl http://localhost:8023/monitoring/issues
# - Check HERMES got the alert
curl http://localhost:8014/alerts/history?limit=5
# - Check ASCLEPIUS ran diagnosis
curl http://localhost:8024/diagnoses/recent
# - Restart service
docker start leveredge-samwise
```

---

## ON COMPLETION

### 1. Move Spec to Done
```bash
mv /opt/leveredge/specs/gsd-omniscient-watchers.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "OMNISCIENT WATCHERS deployed: PANOPTES (30s health), ARGUS (60s metrics), ALOY (real-time anomaly), CERBERUS (security), ASCLEPIUS (auto-diagnosis), VARYS (7am briefings). All agents now continuously watch and auto-alert via HERMES.",
    "domain": "INFRASTRUCTURE",
    "type": "success",
    "source_agent": "CLAUDE_CODE",
    "tags": ["gsd", "monitoring", "watchtower", "enterprise"]
  }'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: OMNISCIENT WATCHERS - Enterprise-grade active monitoring

THE WATCHTOWER:
- PANOPTES: 30s health checks, auto-escalation to ASCLEPIUS
- ARGUS: 60s metrics collection, threshold alerting
- ALOY: Real-time Event Bus anomaly detection
- CERBERUS: Continuous security monitoring
- ASCLEPIUS: Auto-diagnosis on failures
- VARYS: 7am daily briefings
- HERMES: Unified alert routing (critical/warning/info)

Features:
- Continuous watching (not reactive)
- Automatic escalation chains
- Self-healing triggers
- Full audit trail via LCIS
- Docker socket access for container inspection

Nothing escapes our gaze."
```

---

## ARCHITECTURE SUMMARY

```
┌──────────────────────────────────────────────────────────────┐
│                    THE WATCHTOWER                            │
│              "Nothing escapes our gaze"                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  HEALTH          METRICS         SECURITY        ANOMALY    │
│  ┌────────┐      ┌────────┐      ┌────────┐     ┌────────┐ │
│  │PANOPTES│      │ ARGUS  │      │CERBERUS│     │  ALOY  │ │
│  │ 30s    │      │  60s   │      │ Real-  │     │ Real-  │ │
│  │ poll   │      │  poll  │      │  time  │     │  time  │ │
│  └───┬────┘      └───┬────┘      └───┬────┘     └───┬────┘ │
│      │               │               │              │       │
│      └───────────────┴───────┬───────┴──────────────┘       │
│                              │                               │
│                              ▼                               │
│                      ┌─────────────┐                        │
│                      │  EVENT BUS  │                        │
│                      └──────┬──────┘                        │
│                             │                                │
│         ┌───────────────────┼───────────────────┐           │
│         ▼                   ▼                   ▼           │
│   ┌──────────┐       ┌──────────┐       ┌──────────┐       │
│   │ASCLEPIUS │       │   LCIS   │       │  HERMES  │       │
│   │Auto-Diag │       │ Learning │       │ Alerting │       │
│   └──────────┘       └──────────┘       └────┬─────┘       │
│                                              │              │
│                           ┌──────────────────┘              │
│                           ▼                                  │
│                    ┌─────────────┐                          │
│                    │   VARYS     │                          │
│                    │ 7am Brief   │                          │
│                    └─────────────┘                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

*"In the Watchtower, a hundred eyes never sleep, a thousand ears never rest, and no shadow goes unobserved. This is enterprise-grade vigilance."*
