# GSD: VARYS Discovery Engine - The All-Seeing Spider

**Priority:** CRITICAL
**Port:** 8112 (existing)
**Time:** 15-20 min
**Purpose:** Make VARYS actually discover and track ALL agents, not just a hardcoded list

---

## THE VISION

VARYS doesn't rely on a static list. VARYS **discovers**.

Three sources of truth:
1. **AGENT-ROUTING.md** - The documented plan
2. **Database registry** - What VARYS has seen
3. **Live port scan** - What's actually running RIGHT NOW

VARYS compares all three and reports:
- ✅ Aligned (documented + registered + running)
- ⚠️ Undocumented (running but not in AGENT-ROUTING.md)
- 👻 Ghost (documented but not responding)
- 🔀 Drift (port mismatch, wrong config)

*"I know what runs in the shadows. Nothing escapes the web."*

---

## PHASE 1: PARSE AGENT-ROUTING.MD

Add to `varys.py`:

```python
import re
from pathlib import Path

AGENT_ROUTING_PATH = "/opt/leveredge/AGENT-ROUTING.md"

def parse_agent_routing() -> Dict[str, Dict[str, Any]]:
    """Parse AGENT-ROUTING.md to extract documented agents"""
    agents = {}
    
    try:
        content = Path(AGENT_ROUTING_PATH).read_text()
        
        # Pattern: ### AGENT_NAME (Description) - Port XXXX
        # Or from tables: | **AGENT** | Domain | PORT |
        # Or: ### AGENT_NAME - Port XXXX
        
        # Match section headers like "### HEPHAESTUS (Builder) - Port 8011"
        header_pattern = r'###\s+([A-Z][A-Z0-9_-]+)\s*\([^)]*\)\s*-\s*Port\s+(\d+)'
        for match in re.finditer(header_pattern, content):
            name = match.group(1)
            port = int(match.group(2))
            agents[name] = {"port": port, "source": "routing_header"}
        
        # Match table rows like "| **GYM-COACH** | Fitness | 8110 |"
        # Or "| GYM-COACH (8110) |"
        table_pattern = r'\|\s*\*?\*?([A-Z][A-Z0-9_-]+)\*?\*?\s*\|[^|]*\|\s*(\d{4})\s*\|'
        for match in re.finditer(table_pattern, content):
            name = match.group(1)
            port = int(match.group(2))
            if name not in agents:
                agents[name] = {"port": port, "source": "routing_table"}
        
        # Match inline port references like "HERACLES (8200)" or "Port: 8200"
        inline_pattern = r'([A-Z][A-Z0-9_-]+)\s*[\(-]\s*(?:Port:?\s*)?(\d{4})\s*[\)]?'
        for match in re.finditer(inline_pattern, content):
            name = match.group(1)
            port = int(match.group(2))
            # Only add if looks like an agent name and port in range
            if len(name) >= 3 and 8000 <= port <= 9000 and name not in agents:
                agents[name] = {"port": port, "source": "routing_inline"}
        
    except Exception as e:
        print(f"[VARYS] Failed to parse AGENT-ROUTING.md: {e}")
    
    return agents


@app.get("/fleet/documented")
async def get_documented_agents():
    """Get agents documented in AGENT-ROUTING.md"""
    agents = parse_agent_routing()
    return {
        "source": AGENT_ROUTING_PATH,
        "agents": agents,
        "count": len(agents)
    }
```

---

## PHASE 2: PORT SCANNER

```python
import asyncio

SCAN_PORT_RANGE = (8000, 8400)  # Scan this range
SCAN_TIMEOUT = 2.0  # Seconds per port
SCAN_BATCH_SIZE = 20  # Concurrent scans


async def scan_port(port: int) -> Optional[Dict[str, Any]]:
    """Scan a single port for a running agent"""
    try:
        async with httpx.AsyncClient(timeout=SCAN_TIMEOUT) as client:
            response = await client.get(f"http://localhost:{port}/health")
            if response.status_code == 200:
                data = response.json()
                return {
                    "port": port,
                    "status": "healthy",
                    "agent": data.get("agent") or data.get("service") or data.get("name") or f"UNKNOWN_{port}",
                    "version": data.get("version"),
                    "tagline": data.get("tagline"),
                    "description": data.get("description"),
                    "raw_health": data
                }
    except:
        pass
    return None


async def scan_port_range(start: int = 8000, end: int = 8400) -> List[Dict[str, Any]]:
    """Scan port range for running agents"""
    discovered = []
    ports = list(range(start, end + 1))
    
    # Scan in batches
    for i in range(0, len(ports), SCAN_BATCH_SIZE):
        batch = ports[i:i + SCAN_BATCH_SIZE]
        tasks = [scan_port(p) for p in batch]
        results = await asyncio.gather(*tasks)
        discovered.extend([r for r in results if r])
    
    return discovered


@app.post("/fleet/discover")
async def discover_agents(
    background_tasks: BackgroundTasks,
    start_port: int = 8000,
    end_port: int = 8400
):
    """Discover running agents via port scan"""
    background_tasks.add_task(do_discovery, start_port, end_port)
    return {
        "status": "started",
        "scanning": f"ports {start_port}-{end_port}",
        "message": "Check /fleet/discovered when complete"
    }


# Store last discovery results
_last_discovery: Dict[str, Any] = {"agents": [], "timestamp": None}


async def do_discovery(start_port: int, end_port: int):
    """Background discovery task"""
    global _last_discovery
    
    discovered = await scan_port_range(start_port, end_port)
    
    _last_discovery = {
        "agents": discovered,
        "timestamp": datetime.now().isoformat(),
        "ports_scanned": end_port - start_port + 1,
        "agents_found": len(discovered)
    }
    
    # Auto-register discovered agents
    if pool:
        async with pool.acquire() as conn:
            for agent in discovered:
                agent_name = agent['agent'].upper().replace(" ", "_").replace("-", "_")
                # Normalize common patterns
                if agent_name.startswith("UNKNOWN_"):
                    agent_name = f"UNKNOWN_{agent['port']}"
                
                await conn.execute("""
                    INSERT INTO varys_agent_registry 
                    (agent_name, port, status, version, description, tagline, 
                     last_health_check, last_health_status, consecutive_failures)
                    VALUES ($1, $2, 'healthy', $3, $4, $5, NOW(), 'healthy', 0)
                    ON CONFLICT (agent_name) DO UPDATE SET
                        port = EXCLUDED.port,
                        status = 'healthy',
                        version = EXCLUDED.version,
                        description = EXCLUDED.description,
                        tagline = EXCLUDED.tagline,
                        last_health_check = NOW(),
                        last_health_status = 'healthy',
                        consecutive_failures = 0,
                        updated_at = NOW()
                """, agent_name, agent['port'], agent.get('version'),
                    agent.get('description'), agent.get('tagline'))
    
    await publish_event("fleet.discovery.completed", {
        "agents_found": len(discovered),
        "ports_scanned": end_port - start_port + 1
    })


@app.get("/fleet/discovered")
async def get_discovered():
    """Get last discovery results"""
    return _last_discovery
```

---

## PHASE 3: DRIFT DETECTION

```python
@app.get("/fleet/drift")
async def detect_drift():
    """Compare documented vs registered vs running - find all drift"""
    
    # 1. Get documented agents (AGENT-ROUTING.md)
    documented = parse_agent_routing()
    
    # 2. Get registered agents (database)
    registered = {}
    if pool:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT agent_name, port, status FROM varys_agent_registry")
            for row in rows:
                registered[row['agent_name']] = {
                    "port": row['port'],
                    "status": row['status']
                }
    
    # 3. Get running agents (last discovery or quick scan)
    running = {}
    for agent in _last_discovery.get('agents', []):
        name = agent['agent'].upper().replace(" ", "_").replace("-", "_")
        running[name] = {"port": agent['port'], "status": "healthy"}
    
    # 4. Analyze drift
    all_agents = set(documented.keys()) | set(registered.keys()) | set(running.keys())
    
    drift_report = {
        "aligned": [],      # In all three, ports match
        "undocumented": [], # Running but not in AGENT-ROUTING.md
        "ghost": [],        # Documented but not running
        "unregistered": [], # Documented but not in database
        "port_mismatch": [],# Port differs between sources
        "unhealthy": []     # Registered but not responding
    }
    
    for agent in sorted(all_agents):
        doc = documented.get(agent)
        reg = registered.get(agent)
        run = running.get(agent)
        
        doc_port = doc['port'] if doc else None
        reg_port = reg['port'] if reg else None
        run_port = run['port'] if run else None
        
        entry = {
            "agent": agent,
            "documented_port": doc_port,
            "registered_port": reg_port,
            "running_port": run_port
        }
        
        # Check alignment
        if doc and reg and run:
            if doc_port == reg_port == run_port:
                drift_report["aligned"].append(entry)
            else:
                entry["issue"] = "Ports don't match across sources"
                drift_report["port_mismatch"].append(entry)
        elif run and not doc:
            entry["issue"] = "Running but not documented in AGENT-ROUTING.md"
            drift_report["undocumented"].append(entry)
        elif doc and not run:
            entry["issue"] = "Documented but not responding"
            drift_report["ghost"].append(entry)
        elif doc and not reg:
            entry["issue"] = "Documented but not in VARYS registry"
            drift_report["unregistered"].append(entry)
        elif reg and not run and reg.get('status') == 'healthy':
            entry["issue"] = "Was healthy, now not responding"
            drift_report["unhealthy"].append(entry)
    
    # Summary
    total_issues = (
        len(drift_report["undocumented"]) +
        len(drift_report["ghost"]) +
        len(drift_report["unregistered"]) +
        len(drift_report["port_mismatch"]) +
        len(drift_report["unhealthy"])
    )
    
    if total_issues == 0:
        assessment = "✅ PERFECT - All systems aligned"
        varys_says = "Every thread of the web is in its place. The realm is orderly."
    elif total_issues <= 3:
        assessment = "🔶 MINOR DRIFT - A few threads out of place"
        varys_says = f"I've found {total_issues} loose threads. Nothing urgent, but worth tidying."
    elif total_issues <= 10:
        assessment = "⚠️ SIGNIFICANT DRIFT - The web needs attention"
        varys_says = f"The web has {total_issues} tangles. Some corners have gone dark."
    else:
        assessment = "🚨 MAJOR DRIFT - Documentation and reality have diverged"
        varys_says = f"The web is in disarray. {total_issues} agents are not where they should be. Trust nothing."
    
    return {
        "assessment": assessment,
        "summary": {
            "documented": len(documented),
            "registered": len(registered),
            "running": len(running),
            "aligned": len(drift_report["aligned"]),
            "total_issues": total_issues
        },
        "drift": drift_report,
        "varys_says": varys_says,
        "recommendation": "Run /fleet/discover first, then /fleet/drift for accurate results",
        "generated_at": datetime.now().isoformat()
    }
```

---

## PHASE 4: COMPREHENSIVE INTEL REPORT

```python
@app.get("/fleet/intel")
async def fleet_intel():
    """The full intelligence report - everything VARYS knows"""
    
    # Run discovery if stale (> 5 min old)
    if not _last_discovery.get('timestamp'):
        return {
            "error": "No discovery data",
            "action": "POST /fleet/discover first",
            "varys_says": "The web is dark. I must send my spiders out first."
        }
    
    documented = parse_agent_routing()
    drift = await detect_drift()
    
    # Get capabilities summary
    capabilities_summary = {}
    if pool:
        async with pool.acquire() as conn:
            caps = await conn.fetch("""
                SELECT ar.agent_name, COUNT(ac.id) as cap_count
                FROM varys_agent_registry ar
                LEFT JOIN varys_agent_capabilities ac ON ar.id = ac.agent_id
                GROUP BY ar.agent_name
            """)
            for row in caps:
                capabilities_summary[row['agent_name']] = row['cap_count']
            
            # Get duplicates
            dups = await conn.fetch(
                "SELECT * FROM varys_capability_duplicates WHERE status = 'open'"
            )
            
            # Get gaps
            gaps = await conn.fetch(
                "SELECT * FROM varys_capability_gaps WHERE status = 'open'"
            )
    
    return {
        "intel_report": "VARYS FLEET INTELLIGENCE",
        "generated_at": datetime.now().isoformat(),
        
        "executive_summary": drift['assessment'],
        
        "fleet_status": {
            "documented_agents": len(documented),
            "registered_agents": drift['summary']['registered'],
            "running_agents": drift['summary']['running'],
            "aligned_agents": drift['summary']['aligned'],
            "drift_issues": drift['summary']['total_issues']
        },
        
        "drift_analysis": drift['drift'],
        
        "capability_coverage": {
            "agents_with_capabilities": len([v for v in capabilities_summary.values() if v > 0]),
            "agents_without_capabilities": len([v for v in capabilities_summary.values() if v == 0]),
            "open_duplicates": len(dups) if pool else 0,
            "open_gaps": len(gaps) if pool else 0
        },
        
        "action_items": generate_action_items(drift, dups if pool else [], gaps if pool else []),
        
        "varys_says": drift['varys_says']
    }


def generate_action_items(drift: dict, dups: list, gaps: list) -> List[str]:
    """Generate prioritized action items"""
    actions = []
    
    # Critical: Port mismatches
    for item in drift['drift'].get('port_mismatch', []):
        actions.append(f"🔴 FIX PORT: {item['agent']} - doc:{item['documented_port']} vs run:{item['running_port']}")
    
    # High: Undocumented agents
    for item in drift['drift'].get('undocumented', []):
        actions.append(f"🟠 DOCUMENT: {item['agent']} running on port {item['running_port']} - add to AGENT-ROUTING.md")
    
    # Medium: Ghost agents
    for item in drift['drift'].get('ghost', []):
        actions.append(f"🟡 CHECK: {item['agent']} documented but not running - start it or remove from docs")
    
    # Low: Duplicates
    for dup in dups[:5]:
        actions.append(f"🔵 CONSOLIDATE: {dup['capability']} exists in multiple agents: {dup['agents']}")
    
    return actions[:15]  # Top 15
```

---

## EXECUTION ORDER

1. Add all code to `/opt/leveredge/control-plane/agents/varys/varys.py`
2. Rebuild container: `docker compose -f docker-compose.control.yml up -d --build varys`
3. Test:
   ```bash
   # Parse AGENT-ROUTING.md
   curl http://localhost:8112/fleet/documented | jq '.count'
   
   # Discover what's actually running
   curl -X POST http://localhost:8112/fleet/discover
   sleep 15
   
   # Check discovery results
   curl http://localhost:8112/fleet/discovered | jq '.agents_found'
   
   # THE BIG ONE - drift detection
   curl http://localhost:8112/fleet/drift | jq '.'
   
   # Full intel report
   curl http://localhost:8112/fleet/intel | jq '.'
   ```
4. Commit

---

## DELIVERABLES

- [x] Parse AGENT-ROUTING.md for documented agents
- [x] Port scanner (8000-8400)
- [x] Auto-register discovered agents
- [x] Drift detection (documented vs registered vs running)
- [x] Full intel report with action items
- [x] VARYS commentary

---

## COMMIT MESSAGE

```
VARYS: Discovery Engine - The All-Seeing Spider

DISCOVERY:
- Parse AGENT-ROUTING.md as source of truth
- Port scan 8000-8400 for running agents
- Auto-register discovered agents

DRIFT DETECTION:
- Compare documented vs registered vs running
- Identify: undocumented, ghost, port mismatch, unhealthy
- Generate prioritized action items

INTEL REPORT:
- /fleet/intel - comprehensive fleet intelligence
- Executive summary with assessment
- Capability coverage analysis

The spider now sees all. Nothing runs without VARYS knowing.
```

---

*"I don't rely on what I'm told. I verify. I discover. I know."*
