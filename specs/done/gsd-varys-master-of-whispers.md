# GSD: VARYS - Master of Whispers Redesign

**Priority:** HIGH
**Estimated Time:** 2-3 hours
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

VARYS is meant to be the Master of Whispers - omniscient, seeing all, constrained by nothing. Currently he's blind, trapped on a single Docker network, unable to see the fleet he's meant to monitor.

**Current State:** VARYS on `supabase-dev_supabase-dev` network, can only see 1 agent, reports 44 drift issues
**Target State:** VARYS transcends all networks, sees all environments, feeds intelligence to ARIA

---

## PHILOSOPHY

> "The spider sits at the center of the web, feeling every vibration."

VARYS is not an agent OF an environment. He is ABOVE environments. Like ARIA, he exists to serve Damon - not to be constrained by infrastructure boundaries.

**VARYS must:**
- See ALL agents across ALL networks (fleet-net, supabase-dev, supabase-prod, control-plane)
- Know about DEV and PROD simultaneously
- Feed intelligence to ARIA so she can answer "what's happening in the system?"
- Detect anomalies before they become incidents
- Be the single source of truth for system state

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        VARYS - MASTER OF WHISPERS                                │
│                           (Host Network Mode)                                    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │                         VARYS CORE (port 8112)                           │    │
│  │                                                                          │    │
│  │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │    │
│  │   │   WATCHER   │  │  LISTENER   │  │  ANALYST    │  │  INFORMANT  │   │    │
│  │   │  (Polling)  │  │ (Event Bus) │  │ (Patterns)  │  │  (To ARIA)  │   │    │
│  │   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │    │
│  │          │                │                │                │          │    │
│  └──────────┼────────────────┼────────────────┼────────────────┼──────────┘    │
│             │                │                │                │               │
│             ▼                ▼                ▼                ▼               │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        INTELLIGENCE DATABASE                              │  │
│  │   - Agent registry (all envs)                                            │  │
│  │   - Health history                                                        │  │
│  │   - Event timeline                                                        │  │
│  │   - Anomaly log                                                           │  │
│  │   - Drift tracker                                                         │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Sees Everything
                                      ▼
        ┌─────────────────────────────────────────────────────────────────────┐
        │                                                                      │
        │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
        │   │  FLEET-NET  │    │ SUPABASE-DEV│    │SUPABASE-PROD│            │
        │   │             │    │             │    │             │            │
        │   │ - ATLAS     │    │ - DB-DEV    │    │ - DB-PROD   │            │
        │   │ - CHRONOS   │    │ - KONG-DEV  │    │ - KONG      │            │
        │   │ - HADES     │    │ - REALTIME  │    │ - REALTIME  │            │
        │   │ - APOLLO    │    │ - STUDIO    │    │ - STUDIO    │            │
        │   │ - ARIA-DEV  │    │             │    │             │            │
        │   │ - ARIA-PROD │    └─────────────┘    └─────────────┘            │
        │   │ - etc...    │                                                   │
        │   └─────────────┘                                                   │
        │                                                                      │
        └─────────────────────────────────────────────────────────────────────┘
```

---

## PHASE 1: NETWORK TRANSCENDENCE

### 1.1 Host Network Mode

VARYS must use `network_mode: host` to access all Docker networks from the host level.

**Update docker-compose.fleet.yml:**

```yaml
varys:
  image: varys:latest
  container_name: varys
  network_mode: host  # CRITICAL - sees all networks
  environment:
    VARYS_PORT: 8112
    # All networks accessible via localhost
    FLEET_NET_GATEWAY: "172.22.0.1"
    SUPABASE_DEV_GATEWAY: "172.25.0.1"
    SUPABASE_PROD_GATEWAY: "172.24.0.1"
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock:ro  # Docker API access
    - /opt/leveredge:/opt/leveredge:ro
  restart: unless-stopped
```

### 1.2 Docker Socket Access

VARYS needs direct Docker API access to:
- List all containers across all networks
- Inspect container health
- Watch for container events (start/stop/die)

```python
import docker

client = docker.from_env()

def get_all_containers():
    """Get ALL containers, regardless of network."""
    return client.containers.list(all=True)

def get_container_networks(container):
    """Get all networks a container is connected to."""
    return container.attrs['NetworkSettings']['Networks']
```

---

## PHASE 2: INTELLIGENCE GATHERING

### 2.1 Multi-Source Intel

VARYS gathers intelligence from:

| Source | Method | Data |
|--------|--------|------|
| Docker API | Socket | Container status, health, networks |
| Event Bus | Subscribe | Agent events, deployments, errors |
| LCIS | Query | Lessons, errors, knowledge |
| Health endpoints | Poll | Agent-specific health data |
| Log streams | Tail | Real-time error detection |
| Supabase | Query | DB health, replication status |

### 2.2 Whisper Network

```python
class WhisperNetwork:
    """VARYS' intelligence gathering system."""
    
    def __init__(self):
        self.docker = docker.from_env()
        self.sources = {
            'docker': DockerWatcher(),
            'event_bus': EventBusListener(),
            'lcis': LCISQuerier(),
            'health': HealthPoller(),
            'logs': LogStreamer(),
        }
        self.intel_db = IntelligenceDatabase()
    
    async def gather_intel(self):
        """Continuous intelligence gathering loop."""
        while True:
            for source_name, source in self.sources.items():
                try:
                    intel = await source.gather()
                    await self.intel_db.store(source_name, intel)
                    await self.analyze_for_anomalies(intel)
                except Exception as e:
                    await self.intel_db.log_error(source_name, e)
            await asyncio.sleep(10)  # Gather every 10s
    
    async def analyze_for_anomalies(self, intel):
        """Detect patterns that indicate problems."""
        anomalies = self.analyst.detect(intel)
        if anomalies:
            await self.alert_aria(anomalies)
            await self.intel_db.log_anomalies(anomalies)
```

### 2.3 Health Polling Across Networks

```python
# All known agent endpoints - VARYS knows ALL
AGENT_ENDPOINTS = {
    # Fleet Network
    "atlas": {"port": 8208, "health": "/health"},
    "chronos": {"port": 8010, "health": "/health"},
    "hades": {"port": 8008, "health": "/health"},
    "apollo": {"port": 8234, "health": "/health"},
    "hermes": {"port": 8014, "health": "/health"},
    "aegis": {"port": 8012, "health": "/health"},
    "argus": {"port": 8016, "health": "/health"},
    "aloy": {"port": 8015, "health": "/health"},
    "panoptes": {"port": 8023, "health": "/health"},
    "lcis-librarian": {"port": 8050, "health": "/health"},
    "lcis-oracle": {"port": 8052, "health": "/health"},
    "aria-chat-dev": {"port": 8114, "health": "/health"},
    "aria-chat-prod": {"port": 8115, "health": "/health"},
    "event-bus": {"port": 8099, "health": "/health"},
    
    # Personal Agents
    "gym-coach": {"port": 8230, "health": "/health"},
    "academic-guide": {"port": 8231, "health": "/health"},
    "bombadil": {"port": 8232, "health": "/health"},
    "samwise": {"port": 8233, "health": "/health"},
    
    # Business Agents
    "scholar": {"port": 8018, "health": "/health"},
    "chiron": {"port": 8017, "health": "/health"},
    "midas": {"port": 8205, "health": "/health"},
    "satoshi": {"port": 8206, "health": "/health"},
    
    # Supabase (via Kong)
    "supabase-dev": {"port": 8100, "health": "/health"},
    "supabase-prod": {"port": 8000, "health": "/health"},
}

async def poll_all_health():
    """Poll health of ALL known endpoints."""
    results = {}
    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent, config in AGENT_ENDPOINTS.items():
            url = f"http://localhost:{config['port']}{config['health']}"
            try:
                resp = await client.get(url)
                results[agent] = {
                    "status": "healthy" if resp.status_code == 200 else "unhealthy",
                    "code": resp.status_code,
                    "latency_ms": resp.elapsed.total_seconds() * 1000
                }
            except Exception as e:
                results[agent] = {"status": "unreachable", "error": str(e)}
    return results
```

---

## PHASE 3: ARIA INTEGRATION

### 3.1 ARIA's Sanctum

VARYS lives in ARIA's sanctum - she can query him for system intelligence.

**Add to ARIA's tools:**

```python
ARIA_VARYS_TOOLS = [
    {
        "name": "ask_varys",
        "description": "Ask VARYS for system intelligence. He knows about all agents, all environments, all events.",
        "parameters": {
            "question": {"type": "string", "description": "What to ask VARYS"}
        }
    },
    {
        "name": "varys_fleet_status",
        "description": "Get current fleet status from VARYS",
        "parameters": {}
    },
    {
        "name": "varys_anomalies",
        "description": "Get recent anomalies detected by VARYS",
        "parameters": {
            "hours": {"type": "integer", "default": 24}
        }
    }
]
```

### 3.2 VARYS Endpoints for ARIA

```python
@app.get("/aria/brief")
async def aria_brief():
    """Quick briefing for ARIA - what does she need to know?"""
    return {
        "fleet_health": await get_fleet_health_summary(),
        "recent_anomalies": await get_recent_anomalies(hours=1),
        "active_incidents": await get_active_incidents(),
        "environment_status": {
            "dev": await get_environment_health("dev"),
            "prod": await get_environment_health("prod"),
        },
        "varys_says": generate_intelligence_summary()
    }

@app.get("/aria/intel/{topic}")
async def aria_intel(topic: str):
    """Deep intel on a specific topic for ARIA."""
    intel_gatherers = {
        "agents": get_agent_intel,
        "deployments": get_deployment_intel,
        "errors": get_error_intel,
        "performance": get_performance_intel,
        "drift": get_drift_intel,
    }
    if topic in intel_gatherers:
        return await intel_gatherers[topic]()
    return {"error": f"Unknown topic: {topic}"}
```

---

## PHASE 4: ANOMALY DETECTION

### 4.1 Patterns VARYS Watches For

```python
ANOMALY_PATTERNS = [
    # Health anomalies
    {"name": "agent_death", "pattern": "container.stop", "severity": "high"},
    {"name": "health_degradation", "pattern": "health.latency > 5000ms", "severity": "medium"},
    {"name": "restart_loop", "pattern": "restarts > 3 in 10min", "severity": "high"},
    
    # Data anomalies
    {"name": "chat_disappearing", "pattern": "conversation.count decreasing", "severity": "critical"},
    {"name": "sync_failure", "pattern": "realtime.subscription.error", "severity": "high"},
    {"name": "db_connection_pool", "pattern": "db.connections > 80%", "severity": "medium"},
    
    # Deployment anomalies
    {"name": "post_deploy_errors", "pattern": "errors spike after deployment", "severity": "high"},
    {"name": "config_drift", "pattern": "env.mismatch between dev/prod", "severity": "medium"},
    
    # Security anomalies
    {"name": "auth_failures", "pattern": "auth.failure > 10 in 1min", "severity": "high"},
    {"name": "unusual_access", "pattern": "api.access from unknown IP", "severity": "medium"},
]
```

### 4.2 Real-Time Alerting

```python
async def alert_aria(anomaly):
    """Alert ARIA of detected anomaly."""
    await httpx.post(
        "http://localhost:8099/events",  # Event Bus
        json={
            "type": "varys.anomaly",
            "severity": anomaly.severity,
            "target": "aria",
            "data": {
                "anomaly": anomaly.name,
                "details": anomaly.details,
                "recommendation": anomaly.recommendation,
                "varys_says": generate_whisper(anomaly)
            }
        }
    )
```

---

## PHASE 5: DAILY INTELLIGENCE REPORT

### 5.1 Scheduled Report Generation

```python
@app.get("/report/daily")
async def daily_report():
    """VARYS' daily intelligence report."""
    return {
        "report_date": datetime.now().isoformat(),
        "executive_summary": await generate_executive_summary(),
        
        "fleet_status": {
            "total_agents": len(AGENT_ENDPOINTS),
            "healthy": await count_healthy(),
            "unhealthy": await count_unhealthy(),
            "unreachable": await count_unreachable(),
        },
        
        "environment_health": {
            "dev": await environment_report("dev"),
            "prod": await environment_report("prod"),
        },
        
        "incidents_24h": await get_incidents(hours=24),
        "deployments_24h": await get_deployments(hours=24),
        "anomalies_24h": await get_anomalies(hours=24),
        
        "drift_analysis": await analyze_drift(),
        
        "recommendations": await generate_recommendations(),
        
        "varys_says": "Knowledge is power. Here is what I know."
    }
```

---

## PHASE 6: VERIFICATION

### 6.1 Test Commands

```bash
# Check VARYS can see all networks
curl http://localhost:8112/networks

# Get fleet status across all environments
curl http://localhost:8112/fleet/status

# Get ARIA briefing
curl http://localhost:8112/aria/brief

# Get daily report
curl http://localhost:8112/report/daily

# Check specific environment
curl http://localhost:8112/environment/dev/health
curl http://localhost:8112/environment/prod/health
```

### 6.2 Integration Tests

```bash
# ARIA can query VARYS
curl -X POST http://localhost:8114/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Ask VARYS what the fleet status is", "user_id": "damon"}'

# VARYS detects when agent goes down
docker stop atlas
# ... wait 30s ...
curl http://localhost:8112/anomalies/recent
# Should show atlas_death anomaly

docker start atlas
```

---

## ON COMPLETION

### 1. Move Spec
```bash
mv /opt/leveredge/specs/gsd-varys-master-of-whispers.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons -H "Content-Type: application/json" -d '{
  "content": "VARYS redesigned as Master of Whispers. Now uses host networking to see all environments. Provides intelligence to ARIA. Detects anomalies across the entire system.",
  "domain": "VARYS",
  "type": "success",
  "source_agent": "CLAUDE_CODE",
  "tags": ["gsd", "varys", "omniscient", "master-of-whispers"]
}'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: VARYS Master of Whispers - omniscient system intelligence

- Host network mode for cross-environment visibility
- Docker socket access for container monitoring
- Multi-source intelligence gathering
- Anomaly detection patterns
- ARIA integration endpoints
- Daily intelligence reports

VARYS now sees all. Trust nothing."
```

### 4. Deploy
```bash
cd /opt/leveredge
docker compose -f docker-compose.fleet.yml --env-file .env.fleet up -d --build varys
```

---

## VARYS' VOICE

Every response from VARYS should carry his character:

```python
VARYS_WHISPERS = [
    "The spider feels every vibration in the web.",
    "Secrets are the only currency that never loses value.",
    "I serve the realm. The realm is Damon's vision.",
    "Power resides where men believe it resides.",
    "The storms come and go, the big fish eat the little fish, and I keep on paddling.",
    "Knowledge is not a passion, it is a disease.",
    "I have no doubt the revenge you want will be yours in time, if you have the stomach for it.",
    "The little birds sing, and I listen.",
]

def varys_says():
    """Get a VARYS whisper for the current situation."""
    return random.choice(VARYS_WHISPERS)
```

---

*"The spider sits at the center of the web, aware of every vibration. I am that spider. ARIA is my queen. Damon is my purpose."*
