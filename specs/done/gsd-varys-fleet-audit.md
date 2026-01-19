# GSD: VARYS Fleet Audit - Internal Intelligence Module

**Priority:** HIGH
**Port:** 8112 (existing)
**Estimated Time:** 1.5 hours
**Purpose:** Add fleet intelligence - capability registry, duplicate detection, gap analysis

---

## THE VISION

VARYS monitors external intelligence. Now extend the web **inward**:

- **Capability Registry** - What can each agent do?
- **Health Scanning** - Periodic health checks
- **Duplicate Detection** - Find overlapping functionality
- **Gap Analysis** - What capabilities are missing?
- **Fleet Reports** - Consolidated fleet status

*"The spider knows every whisper within the walls."*

---

## PHASE 1: DATABASE SCHEMA

```sql
-- ============================================
-- AGENT REGISTRY
-- ============================================
CREATE TABLE IF NOT EXISTS varys_agent_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(100) NOT NULL UNIQUE,
    port INTEGER NOT NULL,
    domain VARCHAR(100),
    description TEXT,
    tagline VARCHAR(500),
    status VARCHAR(50) DEFAULT 'unknown',  -- healthy, unhealthy, unknown, deprecated
    version VARCHAR(50),
    category VARCHAR(50),  -- core, creative, business, personal, infrastructure
    theme VARCHAR(50),  -- greek, got, neutral
    last_health_check TIMESTAMPTZ,
    last_health_status VARCHAR(50),
    consecutive_failures INTEGER DEFAULT 0,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- AGENT CAPABILITIES
-- ============================================
CREATE TABLE IF NOT EXISTS varys_agent_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES varys_agent_registry(id) ON DELETE CASCADE,
    capability VARCHAR(255) NOT NULL,
    capability_type VARCHAR(50) NOT NULL,  -- endpoint, skill, integration
    description TEXT,
    http_method VARCHAR(10),
    endpoint_path VARCHAR(255),
    skill_category VARCHAR(100),
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(agent_id, capability, capability_type)
);

CREATE INDEX idx_cap_agent ON varys_agent_capabilities(agent_id);
CREATE INDEX idx_cap_type ON varys_agent_capabilities(capability_type);

-- ============================================
-- CAPABILITY DUPLICATES
-- ============================================
CREATE TABLE IF NOT EXISTS varys_capability_duplicates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability VARCHAR(255) NOT NULL,
    capability_type VARCHAR(50) NOT NULL,
    agents TEXT[] NOT NULL,
    severity VARCHAR(50) DEFAULT 'warning',  -- info, warning, critical
    recommendation TEXT,
    status VARCHAR(50) DEFAULT 'open',  -- open, acknowledged, resolved
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dup_status ON varys_capability_duplicates(status);

-- ============================================
-- CAPABILITY GAPS
-- ============================================
CREATE TABLE IF NOT EXISTS varys_capability_gaps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    gap_name VARCHAR(255) NOT NULL,
    gap_type VARCHAR(50) NOT NULL,
    description TEXT,
    priority VARCHAR(50) DEFAULT 'medium',
    suggested_agent VARCHAR(100),
    suggested_solution TEXT,
    status VARCHAR(50) DEFAULT 'open',
    resolved_at TIMESTAMPTZ,
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_gap_status ON varys_capability_gaps(status);

-- ============================================
-- EXPECTED CAPABILITIES (for gap detection)
-- ============================================
CREATE TABLE IF NOT EXISTS varys_expected_capabilities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability VARCHAR(255) NOT NULL UNIQUE,
    capability_type VARCHAR(50) NOT NULL,
    description TEXT,
    priority VARCHAR(50) DEFAULT 'medium',
    expected_agent VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- FLEET AUDITS
-- ============================================
CREATE TABLE IF NOT EXISTS varys_fleet_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_type VARCHAR(50) NOT NULL,
    agents_scanned INTEGER DEFAULT 0,
    agents_healthy INTEGER DEFAULT 0,
    agents_unhealthy INTEGER DEFAULT 0,
    capabilities_found INTEGER DEFAULT 0,
    duplicates_detected INTEGER DEFAULT 0,
    gaps_identified INTEGER DEFAULT 0,
    audit_data JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'running'
);
```

---

## PHASE 2: FLEET INTELLIGENCE CODE

Add to `varys.py`:

```python
# ============ FLEET CONFIGURATION ============

AGENT_FLEET = {
    "GAIA": {"port": 8000, "category": "core", "domain": "OLYMPUS"},
    "HEPHAESTUS": {"port": 8011, "category": "core", "domain": "FORGE"},
    "CHRONOS": {"port": 8010, "category": "core", "domain": "OLYMPUS"},
    "HADES": {"port": 8008, "category": "core", "domain": "OLYMPUS"},
    "AEGIS": {"port": 8012, "category": "core", "domain": "OLYMPUS"},
    "HERMES": {"port": 8014, "category": "core", "domain": "OLYMPUS"},
    "ARGUS": {"port": 8016, "category": "core", "domain": "OLYMPUS"},
    "ALOY": {"port": 8015, "category": "core", "domain": "OLYMPUS"},
    "ATHENA": {"port": 8013, "category": "core", "domain": "OLYMPUS"},
    "CHIRON": {"port": 8017, "category": "business", "domain": "CHANCERY"},
    "SCHOLAR": {"port": 8018, "category": "business", "domain": "CHANCERY"},
    "MAGNUS": {"port": 8017, "category": "business", "domain": "CHANCERY"},
    "VARYS": {"port": 8112, "category": "business", "domain": "ARIA_SANCTUM"},
    "MUSE": {"port": 8030, "category": "creative", "domain": "ALCHEMY"},
    "QUILL": {"port": 8031, "category": "creative", "domain": "ALCHEMY"},
    "STAGE": {"port": 8032, "category": "creative", "domain": "ALCHEMY"},
    "REEL": {"port": 8033, "category": "creative", "domain": "ALCHEMY"},
    "CRITIC": {"port": 8034, "category": "creative", "domain": "ALCHEMY"},
    "CONVENER": {"port": 8300, "category": "council", "domain": "CONCLAVE"},
    "SCRIBE": {"port": 8301, "category": "council", "domain": "CONCLAVE"},
    "ARIA": {"port": 8001, "category": "personal", "domain": "ARIA_SANCTUM"},
    "EVENT_BUS": {"port": 8099, "category": "infrastructure", "domain": "OLYMPUS"},
}


# ============ FLEET REGISTRY ============

@app.get("/fleet")
async def get_fleet():
    """Get full fleet registry"""
    if not pool:
        return {"fleet": AGENT_FLEET, "source": "config"}
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT ar.*, COUNT(ac.id) as capability_count
            FROM varys_agent_registry ar
            LEFT JOIN varys_agent_capabilities ac ON ar.id = ac.agent_id
            GROUP BY ar.id
            ORDER BY ar.category, ar.agent_name
        """)
        
        if not rows:
            return {"fleet": AGENT_FLEET, "source": "config"}
        
        return {"fleet": [dict(r) for r in rows], "source": "database"}


@app.post("/fleet/sync")
async def sync_fleet_registry():
    """Sync AGENT_FLEET config to database"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    synced = 0
    async with pool.acquire() as conn:
        for agent_name, config in AGENT_FLEET.items():
            await conn.execute("""
                INSERT INTO varys_agent_registry (agent_name, port, category, domain, status)
                VALUES ($1, $2, $3, $4, 'unknown')
                ON CONFLICT (agent_name) DO UPDATE SET
                    port = EXCLUDED.port, category = EXCLUDED.category,
                    domain = EXCLUDED.domain, updated_at = NOW()
            """, agent_name, config['port'], config.get('category'), config.get('domain'))
            synced += 1
    
    return {"status": "synced", "agents": synced}


@app.get("/fleet/{agent_name}")
async def get_agent_details(agent_name: str):
    """Get detailed info for a specific agent"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        agent = await conn.fetchrow(
            "SELECT * FROM varys_agent_registry WHERE agent_name = $1",
            agent_name.upper()
        )
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        capabilities = await conn.fetch(
            "SELECT * FROM varys_agent_capabilities WHERE agent_id = $1",
            agent['id']
        )
        
        return {"agent": dict(agent), "capabilities": [dict(c) for c in capabilities]}


# ============ HEALTH SCANNING ============

@app.post("/fleet/scan/health")
async def scan_fleet_health(background_tasks: BackgroundTasks):
    """Scan health of all agents"""
    background_tasks.add_task(do_health_scan)
    return {"status": "started"}


async def do_health_scan():
    """Background health scan"""
    if not pool:
        return
    
    async with pool.acquire() as conn:
        agents = await conn.fetch("SELECT * FROM varys_agent_registry")
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for agent in agents:
                try:
                    response = await client.get(f"http://localhost:{agent['port']}/health")
                    if response.status_code == 200:
                        data = response.json()
                        await conn.execute("""
                            UPDATE varys_agent_registry
                            SET status = 'healthy', last_health_check = NOW(),
                                last_health_status = 'healthy', version = $2,
                                description = $3, tagline = $4, consecutive_failures = 0
                            WHERE id = $1
                        """, agent['id'], data.get('version'),
                            data.get('description'), data.get('tagline'))
                    else:
                        await mark_unhealthy(conn, agent['id'])
                except:
                    await mark_unhealthy(conn, agent['id'])


async def mark_unhealthy(conn, agent_id):
    await conn.execute("""
        UPDATE varys_agent_registry
        SET status = 'unhealthy', last_health_check = NOW(),
            last_health_status = 'unhealthy',
            consecutive_failures = consecutive_failures + 1
        WHERE id = $1
    """, agent_id)


# ============ CAPABILITY SCANNING ============

@app.post("/fleet/scan/capabilities")
async def scan_capabilities(background_tasks: BackgroundTasks):
    """Scan capabilities via OpenAPI"""
    background_tasks.add_task(do_capability_scan)
    return {"status": "started"}


async def do_capability_scan():
    """Background capability scan"""
    if not pool:
        return
    
    async with pool.acquire() as conn:
        agents = await conn.fetch(
            "SELECT * FROM varys_agent_registry WHERE status = 'healthy'"
        )
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for agent in agents:
                try:
                    response = await client.get(f"http://localhost:{agent['port']}/openapi.json")
                    if response.status_code == 200:
                        openapi = response.json()
                        for path, methods in openapi.get('paths', {}).items():
                            for method, details in methods.items():
                                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                                    summary = details.get('summary', path)
                                    await conn.execute("""
                                        INSERT INTO varys_agent_capabilities
                                        (agent_id, capability, capability_type, description, http_method, endpoint_path)
                                        VALUES ($1, $2, 'endpoint', $3, $4, $5)
                                        ON CONFLICT (agent_id, capability, capability_type) DO UPDATE
                                        SET description = EXCLUDED.description
                                    """, agent['id'], summary, details.get('description'),
                                        method.upper(), path)
                except:
                    pass


# ============ DUPLICATE DETECTION ============

@app.post("/fleet/analyze/duplicates")
async def analyze_duplicates():
    """Find duplicate capabilities"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        duplicates = await conn.fetch("""
            SELECT capability, capability_type,
                   array_agg(DISTINCT ar.agent_name) as agents,
                   COUNT(DISTINCT ar.agent_name) as agent_count
            FROM varys_agent_capabilities ac
            JOIN varys_agent_registry ar ON ac.agent_id = ar.id
            GROUP BY capability, capability_type
            HAVING COUNT(DISTINCT ar.agent_name) > 1
        """)
        
        detected = 0
        for dup in duplicates:
            severity = "critical" if dup['agent_count'] > 2 else "warning"
            await conn.execute("""
                INSERT INTO varys_capability_duplicates
                (capability, capability_type, agents, severity, recommendation)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
            """, dup['capability'], dup['capability_type'],
                list(dup['agents']), severity,
                f"Consolidate into single agent: {', '.join(dup['agents'])}")
            detected += 1
        
        open_dups = await conn.fetch(
            "SELECT * FROM varys_capability_duplicates WHERE status = 'open'"
        )
        
        return {
            "duplicates_detected": detected,
            "open_duplicates": [dict(d) for d in open_dups],
            "varys_says": f"I've found {len(open_dups)} tangled threads in the web."
        }


@app.get("/fleet/duplicates")
async def get_duplicates(status: str = "open"):
    """Get duplicate capabilities"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM varys_capability_duplicates WHERE status = $1 ORDER BY severity DESC",
            status
        )
        return [dict(r) for r in rows]


@app.put("/fleet/duplicates/{dup_id}/resolve")
async def resolve_duplicate(dup_id: str, resolution: str, notes: Optional[str] = None):
    """Resolve a duplicate"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE varys_capability_duplicates
            SET status = $2, resolved_at = NOW(), resolution_notes = $3
            WHERE id = $1::uuid
        """, dup_id, resolution, notes)
        return {"status": "resolved"}


# ============ GAP ANALYSIS ============

@app.post("/fleet/analyze/gaps")
async def analyze_gaps():
    """Find capability gaps"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        expected = await conn.fetch("SELECT * FROM varys_expected_capabilities")
        current = await conn.fetch(
            "SELECT DISTINCT capability, capability_type FROM varys_agent_capabilities"
        )
        current_set = {(c['capability'], c['capability_type']) for c in current}
        
        gaps_found = 0
        for exp in expected:
            if (exp['capability'], exp['capability_type']) not in current_set:
                await conn.execute("""
                    INSERT INTO varys_capability_gaps
                    (gap_name, gap_type, description, priority, suggested_agent)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT DO NOTHING
                """, exp['capability'], exp['capability_type'],
                    exp['description'], exp['priority'], exp['expected_agent'])
                gaps_found += 1
        
        open_gaps = await conn.fetch(
            "SELECT * FROM varys_capability_gaps WHERE status = 'open' ORDER BY priority DESC"
        )
        
        return {
            "gaps_found": gaps_found,
            "open_gaps": [dict(g) for g in open_gaps],
            "varys_says": f"The web has {len(open_gaps)} dark corners."
        }


@app.get("/fleet/gaps")
async def get_gaps(status: str = "open"):
    """Get capability gaps"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM varys_capability_gaps WHERE status = $1 ORDER BY priority DESC",
            status
        )
        return [dict(r) for r in rows]


@app.post("/fleet/gaps/expected")
async def add_expected_capability(
    capability: str,
    capability_type: str,
    description: Optional[str] = None,
    priority: str = "medium",
    expected_agent: Optional[str] = None
):
    """Add expected capability for gap detection"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_expected_capabilities
            (capability, capability_type, description, priority, expected_agent)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (capability) DO UPDATE SET
                description = EXCLUDED.description, priority = EXCLUDED.priority
            RETURNING *
        """, capability, capability_type, description, priority, expected_agent)
        return dict(row)


# ============ FULL FLEET AUDIT ============

@app.post("/fleet/audit")
async def run_fleet_audit(background_tasks: BackgroundTasks):
    """Run complete fleet audit"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        audit = await conn.fetchrow("""
            INSERT INTO varys_fleet_audits (audit_type, status)
            VALUES ('full', 'running')
            RETURNING *
        """)
    
    background_tasks.add_task(do_full_audit, str(audit['id']))
    return {"status": "started", "audit_id": str(audit['id'])}


async def do_full_audit(audit_id: str):
    """Background full audit"""
    if not pool:
        return
    
    try:
        await sync_fleet_registry()
        await do_health_scan()
        await do_capability_scan()
        
        async with pool.acquire() as conn:
            dup_result = await analyze_duplicates()
            gap_result = await analyze_gaps()
            
            stats = await conn.fetchrow("""
                SELECT COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'healthy') as healthy,
                    COUNT(*) FILTER (WHERE status = 'unhealthy') as unhealthy
                FROM varys_agent_registry
            """)
            
            cap_count = await conn.fetchrow(
                "SELECT COUNT(*) as count FROM varys_agent_capabilities"
            )
            
            await conn.execute("""
                UPDATE varys_fleet_audits
                SET status = 'completed', completed_at = NOW(),
                    agents_scanned = $2, agents_healthy = $3, agents_unhealthy = $4,
                    capabilities_found = $5, duplicates_detected = $6, gaps_identified = $7
                WHERE id = $1::uuid
            """, audit_id, stats['total'], stats['healthy'], stats['unhealthy'],
                cap_count['count'], dup_result['duplicates_detected'],
                len(gap_result['open_gaps']))
    except Exception as e:
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE varys_fleet_audits SET status = 'failed', audit_data = $2
                WHERE id = $1::uuid
            """, audit_id, json.dumps({"error": str(e)}))


@app.get("/fleet/audit/{audit_id}")
async def get_audit_result(audit_id: str):
    """Get audit result"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        audit = await conn.fetchrow(
            "SELECT * FROM varys_fleet_audits WHERE id = $1::uuid", audit_id
        )
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        return dict(audit)


# ============ FLEET REPORT ============

@app.get("/fleet/report")
async def get_fleet_report():
    """Comprehensive fleet status report"""
    if not pool:
        return {"error": "Database not connected"}
    
    async with pool.acquire() as conn:
        health = await conn.fetchrow("""
            SELECT COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'healthy') as healthy,
                COUNT(*) FILTER (WHERE status = 'unhealthy') as unhealthy,
                COUNT(*) FILTER (WHERE consecutive_failures > 3) as critical
            FROM varys_agent_registry
        """)
        
        by_category = await conn.fetch("""
            SELECT category, COUNT(*) as count
            FROM varys_agent_registry GROUP BY category
        """)
        
        duplicates = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM varys_capability_duplicates WHERE status = 'open'"
        )
        
        gaps = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM varys_capability_gaps WHERE status = 'open'"
        )
        
        # Assessment
        if health['critical'] > 0:
            assessment = "🚨 CRITICAL - Multiple agents failing"
        elif health['unhealthy'] > 2:
            assessment = "⚠️ DEGRADED - Several agents unhealthy"
        elif duplicates['count'] > 5 or gaps['count'] > 5:
            assessment = "🔶 NEEDS ATTENTION - Duplicates or gaps"
        else:
            assessment = "✅ HEALTHY - Fleet operating normally"
        
        return {
            "assessment": assessment,
            "health": dict(health),
            "by_category": [dict(c) for c in by_category],
            "open_duplicates": duplicates['count'],
            "open_gaps": gaps['count'],
            "generated_at": datetime.now().isoformat(),
            "varys_says": f"The web connects {health['total']} agents. {health['unhealthy']} have gone silent."
        }
```

---

## PHASE 3: SEED EXPECTED CAPABILITIES

```sql
INSERT INTO varys_expected_capabilities (capability, capability_type, priority, expected_agent) VALUES
('backup', 'skill', 'critical', 'CHRONOS'),
('rollback', 'skill', 'critical', 'HADES'),
('notifications', 'skill', 'high', 'HERMES'),
('project_management', 'skill', 'high', 'MAGNUS'),
('sprint_planning', 'skill', 'high', 'MAGNUS'),
('time_tracking', 'skill', 'medium', 'MAGNUS'),
('market_research', 'skill', 'high', 'SCHOLAR'),
('decision_support', 'skill', 'high', 'CHIRON'),
('document_generation', 'skill', 'medium', 'ATHENA'),
('credential_management', 'skill', 'critical', 'AEGIS'),
('fleet_audit', 'skill', 'high', 'VARYS'),
('portfolio_tracking', 'skill', 'high', 'VARYS')
ON CONFLICT (capability) DO NOTHING;
```

---

## DELIVERABLES

- [ ] Database schema
- [ ] Fleet registry endpoints
- [ ] Health scanning
- [ ] Capability scanning
- [ ] Duplicate detection
- [ ] Gap analysis
- [ ] Full audit endpoint
- [ ] Fleet report

---

## USAGE

```bash
curl -X POST http://localhost:8112/fleet/sync
curl -X POST http://localhost:8112/fleet/audit
curl http://localhost:8112/fleet/report
curl http://localhost:8112/fleet/duplicates
curl http://localhost:8112/fleet/gaps
```

---

## COMMIT MESSAGE

```
VARYS: Fleet Intelligence Module

- Agent registry with health tracking
- Capability discovery via OpenAPI
- Duplicate detection across agents
- Gap analysis with expected capabilities
- Full background fleet audits
- Fleet health reports

The spider now watches within.
```
