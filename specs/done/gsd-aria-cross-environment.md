# GSD: ARIA Cross-Environment Awareness

**Priority:** HIGH
**Estimated Time:** 45-60 minutes
**Created:** January 20, 2026
**Status:** Ready for execution

---

## OVERVIEW

ARIA needs to know which environment she's in AND be able to query the other environment. Each environment has its own knowledge base, but ARIA can access both.

**Current State:** ARIA dev and prod are isolated silos with no cross-visibility
**Target State:** ARIA in either environment can answer questions about both, with clear awareness of which is which

---

## USE CASES

| User Location | User Asks | ARIA Does |
|---------------|-----------|-----------|
| PROD | "What's happening in dev?" | Queries DEV LCIS, DEV Event Bus |
| PROD | "Is the dev fleet healthy?" | Checks DEV agent health endpoints |
| DEV | "Any errors in production?" | Queries PROD LCIS for error lessons |
| DEV | "What's prod ARIA's status?" | Checks PROD aria-chat health |
| Either | "Where am I?" | "You're talking to me in [dev/prod]" |

---

## PHASE 1: ENVIRONMENT CONFIGURATION

### 1.1 Update docker-compose.fleet.yml

Add to aria-chat-dev:
```yaml
environment:
  ARIA_ENVIRONMENT: "dev"
  PRIMARY_LCIS_URL: "http://lcis-librarian:8050"
  PRIMARY_EVENT_BUS_URL: "http://event-bus:8099"
  CROSS_LCIS_URL: "http://lcis-librarian:8050"
  CROSS_EVENT_BUS_URL: "http://event-bus:8099"
  CROSS_ENVIRONMENT: "prod"
```

Add to aria-chat-prod:
```yaml
environment:
  ARIA_ENVIRONMENT: "prod"
  PRIMARY_LCIS_URL: "http://lcis-librarian:8050"
  PRIMARY_EVENT_BUS_URL: "http://event-bus:8099"
  CROSS_LCIS_URL: "http://lcis-librarian:8050"
  CROSS_EVENT_BUS_URL: "http://event-bus:8099"
  CROSS_ENVIRONMENT: "dev"
```

---

## PHASE 2: ARIA CHAT SERVICE UPDATES

### 2.1 Add Cross-Environment Functions to aria_chat.py

```python
import os
import httpx

ARIA_ENVIRONMENT = os.getenv("ARIA_ENVIRONMENT", "unknown")
CROSS_ENVIRONMENT = os.getenv("CROSS_ENVIRONMENT", "unknown")
PRIMARY_LCIS_URL = os.getenv("PRIMARY_LCIS_URL", "http://lcis-librarian:8050")
CROSS_LCIS_URL = os.getenv("CROSS_LCIS_URL", "http://lcis-librarian:8050")
PRIMARY_EVENT_BUS_URL = os.getenv("PRIMARY_EVENT_BUS_URL", "http://event-bus:8099")
CROSS_EVENT_BUS_URL = os.getenv("CROSS_EVENT_BUS_URL", "http://event-bus:8099")

AGENT_HEALTH_ENDPOINTS = {
    "dev": {
        "aria-chat": "http://aria-chat-dev:8113/health",
        "event-bus": "http://event-bus:8099/health",
        "lcis": "http://lcis-librarian:8050/health",
    },
    "prod": {
        "aria-chat": "http://aria-chat-prod:8113/health",
        "event-bus": "http://event-bus:8099/health",
        "lcis": "http://lcis-librarian:8050/health",
    }
}

async def get_environment_info():
    return {
        "current_environment": ARIA_ENVIRONMENT,
        "cross_environment": CROSS_ENVIRONMENT,
        "message": f"I am ARIA running in {ARIA_ENVIRONMENT}. I can also access {CROSS_ENVIRONMENT}."
    }

async def query_lcis(query: str, environment: str = "current"):
    if environment == "current" or environment == ARIA_ENVIRONMENT:
        url = PRIMARY_LCIS_URL
        env_label = ARIA_ENVIRONMENT
    else:
        url = CROSS_LCIS_URL
        env_label = CROSS_ENVIRONMENT
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/search", params={"q": query, "limit": 10})
            return {"environment": env_label, "results": response.json()}
    except Exception as e:
        return {"error": str(e), "environment": env_label}

async def check_environment_health(environment: str = "current"):
    env_key = ARIA_ENVIRONMENT if environment == "current" else CROSS_ENVIRONMENT
    endpoints = AGENT_HEALTH_ENDPOINTS.get(env_key, {})
    results = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent, url in endpoints.items():
            try:
                response = await client.get(url)
                results[agent] = {"status": "healthy" if response.status_code == 200 else "unhealthy"}
            except:
                results[agent] = {"status": "unreachable"}
    
    return {"environment": env_key, "agents": results}
```

### 2.2 Add API Endpoints

```python
@app.get("/environment")
async def get_environment():
    return await get_environment_info()

@app.get("/query/lcis")
async def api_query_lcis(q: str, env: str = "current"):
    return await query_lcis(q, env)

@app.get("/health/{environment}")
async def api_environment_health(environment: str):
    return await check_environment_health(environment)
```

---

## PHASE 3: SYSTEM PROMPT UPDATE

Add to ARIA's system prompt:

```
## Environment Awareness

You are ARIA running in **{ARIA_ENVIRONMENT}** environment.

- Primary environment ({ARIA_ENVIRONMENT}): Full read-write access
- Cross environment ({CROSS_ENVIRONMENT}): Read-only query access

When users ask "Where am I?" say "You're talking to me in {ARIA_ENVIRONMENT}"
When users ask about the other environment, query it using cross-environment access.

### Agent Fleet:
| Agent | Port | Purpose |
|-------|------|---------|
| ATLAS | 8208 | Orchestrator |
| CHRONOS | 8010 | Backups |
| HADES | 8008 | Rollback |
| PANOPTES | 8023 | Health |
| ARGUS | 8016 | Metrics |
| LCIS | 8050 | Knowledge |
| APOLLO | 8234 | Deployment |
```

---

## PHASE 4: VERIFICATION

```bash
# Check DEV ARIA environment
curl http://localhost:8114/environment

# Check PROD ARIA environment  
curl http://localhost:8115/environment

# Query cross-environment from DEV
curl "http://localhost:8114/query/lcis?q=deployment&env=cross"

# Check PROD health from DEV
curl http://localhost:8114/health/prod
```

---

## ON COMPLETION

### 1. Move Spec
```bash
mv /opt/leveredge/specs/gsd-aria-cross-environment.md /opt/leveredge/specs/done/
```

### 2. Log to LCIS
```bash
curl -X POST http://localhost:8050/lessons -H "Content-Type: application/json" -d '{
  "content": "ARIA Cross-Environment Awareness deployed. Both DEV and PROD ARIA can query each other.",
  "domain": "ARIA",
  "type": "success",
  "source_agent": "CLAUDE_CODE",
  "tags": ["gsd", "aria", "cross-environment"]
}'
```

### 3. Git Commit
```bash
git add -A
git commit -m "feat: ARIA Cross-Environment Awareness - can query dev from prod and vice versa"
```

### 4. Redeploy
```bash
docker compose -f docker-compose.fleet.yml up -d --build aria-chat-dev aria-chat-prod
```

---

*"One ARIA, two worlds, complete awareness."*
