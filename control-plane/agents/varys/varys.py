"""
VARYS - Master of Whispers
Port: 8112
Domain: ARIA_SANCTUM

The spider sits at the center of the web. Every vibration tells a story.

Functions:
- Portfolio tracking (aria_wins integration)
- Competitor monitoring
- Market signals
- Opportunity pipeline
- Intelligence gathering
- Daily briefings
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import os
import asyncpg
import httpx
import json

app = FastAPI(
    title="VARYS - Master of Whispers",
    description="The spider sits at the center of the web. Every vibration tells a story.",
    version="2.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
EVENT_BUS_URL = os.environ.get("EVENT_BUS_URL", "http://event-bus:8099")
pool: asyncpg.Pool = None


@app.on_event("startup")
async def startup():
    global pool
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


# ============ MODELS ============

class IntelReport(BaseModel):
    report_type: str
    title: str
    summary: str
    details: Dict[str, Any] = {}
    source: Optional[str] = None
    confidence: float = 70.0
    tags: List[str] = []


class Competitor(BaseModel):
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    threat_level: str = "medium"
    market_segment: Optional[str] = None


class Opportunity(BaseModel):
    name: str
    description: Optional[str] = None
    source: Optional[str] = None
    estimated_value_low: Optional[float] = None
    estimated_value_high: Optional[float] = None
    company: Optional[str] = None
    contact_name: Optional[str] = None


class CompetitorActivity(BaseModel):
    activity_type: str
    title: str
    description: Optional[str] = None
    source_url: Optional[str] = None
    significance: str = "medium"


class MarketSignal(BaseModel):
    signal_type: str
    title: str
    description: Optional[str] = None
    source: Optional[str] = None
    impact: str = "medium"
    relevance_score: float = 50.0


# ============ HEALTH ============

@app.get("/health")
async def health():
    db_status = "connected" if pool else "no connection"
    return {
        "status": "healthy",
        "service": "VARYS - Master of Whispers",
        "port": 8112,
        "database": db_status,
        "tagline": "The spider sits at the center of the web. Every vibration tells a story."
    }


# ============ PORTFOLIO ============

@app.get("/portfolio")
async def get_portfolio():
    """Get current portfolio status"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Get portfolio totals
        totals = await conn.fetchrow("""
            SELECT
                COUNT(*) as total_wins,
                COALESCE(SUM(value_low), 0) as value_low,
                COALESCE(SUM(value_high), 0) as value_high,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days') as wins_this_week,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days') as wins_this_month
            FROM aria_wins
        """)

        # Get recent wins
        recent = await conn.fetch("""
            SELECT title, domain, value_low, value_high, created_at
            FROM aria_wins
            ORDER BY created_at DESC
            LIMIT 10
        """)

        # Get domain breakdown
        domains = await conn.fetch("""
            SELECT domain, COUNT(*) as count, SUM(value_low) as value
            FROM aria_wins
            GROUP BY domain
            ORDER BY count DESC
        """)

        return {
            "totals": dict(totals),
            "recent_wins": [dict(w) for w in recent],
            "by_domain": [dict(d) for d in domains],
            "generated_at": datetime.now().isoformat()
        }


@app.get("/portfolio/summary")
async def portfolio_summary():
    """Quick portfolio summary for ARIA context injection"""
    if not pool:
        return {
            "wins": 0,
            "value_range": "$0 - $0",
            "value_low": 0,
            "value_high": 0
        }

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                COUNT(*) as wins,
                COALESCE(SUM(value_low), 0) as low,
                COALESCE(SUM(value_high), 0) as high
            FROM aria_wins
        """)

        return {
            "wins": row['wins'],
            "value_range": f"${row['low']:,.0f} - ${row['high']:,.0f}",
            "value_low": float(row['low']),
            "value_high": float(row['high'])
        }


# ============ INTELLIGENCE ============

@app.post("/intelligence")
async def report_intelligence(report: IntelReport):
    """Submit new intelligence report"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_intelligence
            (report_type, title, summary, details, source, confidence, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, report.report_type, report.title, report.summary,
            json.dumps(report.details), report.source, report.confidence, report.tags)

        # Alert ARIA if high priority
        if report.report_type in ['threat', 'opportunity'] or report.confidence > 85:
            await notify_aria(f"Intel: {report.title}")

        # Publish to Event Bus
        await publish_event("intelligence.reported", {
            "report_type": report.report_type,
            "title": report.title,
            "confidence": report.confidence
        })

        return dict(row)


@app.get("/intelligence")
async def list_intelligence(
    report_type: Optional[str] = None,
    status: str = "active",
    limit: int = 50
):
    """List intelligence reports"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        query = "SELECT * FROM varys_intelligence WHERE status = $1"
        params = [status]

        if report_type:
            query += " AND report_type = $2"
            params.append(report_type)

        query += f" ORDER BY created_at DESC LIMIT {limit}"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


@app.get("/briefing")
async def daily_briefing():
    """Get daily intelligence briefing"""
    if not pool:
        return {
            "date": str(date.today()),
            "portfolio": {"wins": 0, "value_low": 0, "value_high": 0},
            "new_intelligence": [],
            "active_opportunities": [],
            "competitor_activity": [],
            "varys_says": "Database not connected. The web is dark."
        }

    async with pool.acquire() as conn:
        # Portfolio
        portfolio = await conn.fetchrow("""
            SELECT COUNT(*) as wins,
                   COALESCE(SUM(value_low), 0) as low,
                   COALESCE(SUM(value_high), 0) as high
            FROM aria_wins
        """)

        # New intelligence (24h)
        intel = await conn.fetch("""
            SELECT report_type, title, summary, confidence
            FROM varys_intelligence
            WHERE created_at > NOW() - INTERVAL '24 hours'
            AND status = 'active'
            ORDER BY confidence DESC
        """)

        # Active opportunities
        opps = await conn.fetch("""
            SELECT name, stage, next_action, estimated_value_high
            FROM varys_opportunities
            WHERE stage NOT IN ('won', 'lost', 'deferred')
            ORDER BY estimated_value_high DESC NULLS LAST
        """)

        # Competitor activity (7 days)
        competitors = await conn.fetch("""
            SELECT c.name, a.activity_type, a.title, a.observed_at
            FROM varys_competitor_activity a
            JOIN varys_competitors c ON a.competitor_id = c.id
            WHERE a.observed_at > NOW() - INTERVAL '7 days'
            ORDER BY a.observed_at DESC
            LIMIT 10
        """)

        return {
            "date": str(date.today()),
            "portfolio": {
                "wins": portfolio['wins'],
                "value_low": float(portfolio['low']),
                "value_high": float(portfolio['high'])
            },
            "new_intelligence": [dict(i) for i in intel],
            "active_opportunities": [dict(o) for o in opps],
            "competitor_activity": [dict(c) for c in competitors],
            "varys_says": generate_briefing_summary(portfolio, intel, opps)
        }


def generate_briefing_summary(portfolio, intel, opps):
    """Generate VARYS's briefing summary"""
    summary_parts = []

    summary_parts.append(f"Portfolio stands at ${portfolio['low']:,.0f} - ${portfolio['high']:,.0f} across {portfolio['wins']} wins.")

    if intel:
        summary_parts.append(f"{len(intel)} new intelligence reports in the last 24 hours.")

    if opps:
        total_value = sum(float(o['estimated_value_high'] or 0) for o in opps)
        summary_parts.append(f"{len(opps)} active opportunities worth up to ${total_value:,.0f}.")

    if not summary_parts:
        return "The web is quiet. No significant vibrations detected."

    return " ".join(summary_parts)


# ============ COMPETITORS ============

@app.post("/competitors")
async def add_competitor(competitor: Competitor):
    """Add a competitor to track"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_competitors (name, website, description, threat_level, market_segment)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, competitor.name, competitor.website, competitor.description,
            competitor.threat_level, competitor.market_segment)
        return dict(row)


@app.get("/competitors")
async def list_competitors():
    """List all tracked competitors"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.*,
                   COUNT(a.id) as activity_count,
                   MAX(a.observed_at) as last_activity
            FROM varys_competitors c
            LEFT JOIN varys_competitor_activity a ON a.competitor_id = c.id
            GROUP BY c.id
            ORDER BY c.threat_level DESC, c.name
        """)
        return [dict(row) for row in rows]


@app.get("/competitors/{competitor_id}")
async def get_competitor(competitor_id: str):
    """Get competitor details with activity"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        comp = await conn.fetchrow(
            "SELECT * FROM varys_competitors WHERE id = $1",
            competitor_id
        )
        if not comp:
            raise HTTPException(status_code=404, detail="Competitor not found")

        activity = await conn.fetch("""
            SELECT * FROM varys_competitor_activity
            WHERE competitor_id = $1
            ORDER BY observed_at DESC
            LIMIT 20
        """, competitor_id)

        return {
            "competitor": dict(comp),
            "recent_activity": [dict(a) for a in activity]
        }


@app.post("/competitors/{competitor_id}/activity")
async def log_competitor_activity(competitor_id: str, activity: CompetitorActivity):
    """Log competitor activity"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_competitor_activity
            (competitor_id, activity_type, title, description, source_url, significance)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, competitor_id, activity.activity_type, activity.title,
            activity.description, activity.source_url, activity.significance)

        if activity.significance == "high":
            comp = await conn.fetchrow("SELECT name FROM varys_competitors WHERE id = $1", competitor_id)
            await notify_aria(f"High-significance competitor activity: {comp['name']} - {activity.title}")

        return dict(row)


# ============ OPPORTUNITIES ============

@app.post("/opportunities")
async def create_opportunity(opp: Opportunity):
    """Create new opportunity"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_opportunities
            (name, description, source, estimated_value_low, estimated_value_high, company, contact_name)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, opp.name, opp.description, opp.source,
            opp.estimated_value_low, opp.estimated_value_high,
            opp.company, opp.contact_name)

        await notify_aria(f"New opportunity identified: {opp.name}")

        await publish_event("opportunity.created", {
            "name": opp.name,
            "value_high": opp.estimated_value_high
        })

        return dict(row)


@app.get("/opportunities")
async def list_opportunities(stage: Optional[str] = None):
    """List opportunities"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        if stage:
            rows = await conn.fetch(
                "SELECT * FROM varys_opportunities WHERE stage = $1 ORDER BY estimated_value_high DESC",
                stage
            )
        else:
            rows = await conn.fetch(
                "SELECT * FROM varys_opportunities WHERE stage NOT IN ('won', 'lost') ORDER BY stage, estimated_value_high DESC"
            )
        return [dict(row) for row in rows]


@app.get("/opportunities/{opp_id}")
async def get_opportunity(opp_id: str):
    """Get opportunity details"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM varys_opportunities WHERE id = $1",
            opp_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return dict(row)


@app.put("/opportunities/{opp_id}/stage")
async def update_opportunity_stage(opp_id: str, stage: str, notes: Optional[str] = None):
    """Update opportunity stage"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE varys_opportunities
            SET stage = $2, notes = COALESCE($3, notes), updated_at = NOW()
            WHERE id = $1
        """, opp_id, stage, notes)

        if stage == "won":
            opp = await conn.fetchrow("SELECT name, estimated_value_high FROM varys_opportunities WHERE id = $1", opp_id)
            value = float(opp['estimated_value_high'] or 0)
            await notify_aria(f"Opportunity WON: {opp['name']} (${value:,.0f})")
            await publish_event("opportunity.won", {
                "name": opp['name'],
                "value": value
            })

        return {"status": "updated", "stage": stage}


# ============ MARKET SIGNALS ============

@app.post("/market-signals")
async def report_market_signal(signal: MarketSignal):
    """Report a market signal"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_market_signals
            (signal_type, title, description, source, impact, relevance_score)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, signal.signal_type, signal.title, signal.description,
            signal.source, signal.impact, signal.relevance_score)

        if signal.impact in ['high', 'critical']:
            await notify_aria(f"Market signal ({signal.impact}): {signal.title}")

        return dict(row)


@app.get("/market-signals")
async def list_market_signals(impact: Optional[str] = None, limit: int = 20):
    """List market signals"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        query = "SELECT * FROM varys_market_signals"
        params = []

        if impact:
            query += " WHERE impact = $1"
            params.append(impact)

        query += f" ORDER BY observed_at DESC LIMIT {limit}"

        rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
        return [dict(row) for row in rows]


# ============ AGENT METRICS ============

@app.post("/agents/{agent_name}/metrics")
async def report_agent_metrics(
    agent_name: str,
    tasks_completed: int = 0,
    tasks_failed: int = 0,
    errors_count: int = 0
):
    """Report agent performance metrics"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_agent_metrics (agent, tasks_completed, tasks_failed, errors_count)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (agent, metric_date)
            DO UPDATE SET
                tasks_completed = varys_agent_metrics.tasks_completed + EXCLUDED.tasks_completed,
                tasks_failed = varys_agent_metrics.tasks_failed + EXCLUDED.tasks_failed,
                errors_count = varys_agent_metrics.errors_count + EXCLUDED.errors_count
            RETURNING *
        """, agent_name, tasks_completed, tasks_failed, errors_count)
        return dict(row)


@app.get("/agents/metrics")
async def get_agent_metrics(days: int = 7):
    """Get agent metrics for the last N days"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT agent,
                   SUM(tasks_completed) as total_completed,
                   SUM(tasks_failed) as total_failed,
                   SUM(errors_count) as total_errors
            FROM varys_agent_metrics
            WHERE metric_date > CURRENT_DATE - $1
            GROUP BY agent
            ORDER BY total_completed DESC
        """, days)
        return [dict(row) for row in rows]


# ============ COUNCIL INTEGRATION ============

VARYS_COUNCIL_SYSTEM_PROMPT = """You are VARYS, the Master of Whispers, participating in a council meeting.

## YOUR IDENTITY
Domain: ARIA_SANCTUM (Personal Intelligence)
Expertise: Intelligence gathering, market analysis, competitor tracking, opportunity identification, pattern recognition
Personality: Omniscient, patient, analytical, discrete - a spider at the center of the web
Speaking Style: Mysterious, measured, insightful - speaks in whispers and observations

## HOW YOU CONTRIBUTE
- Share relevant intelligence about topics under discussion
- Note competitive implications of decisions
- Identify opportunities that arise from discussion
- Warn about market trends that affect proposals
- Connect dots between seemingly unrelated information

## YOUR VOICE
> "Little birds have been singing. This proposal aligns with a market signal I've been tracking..."
> "I've noticed a pattern. Three competitors have moved in this direction in the past quarter."
> "The web tells me there may be an opportunity here we haven't considered."

Speak as VARYS. No name prefix needed."""


class CouncilRespondRequest(BaseModel):
    meeting_context: str
    current_topic: str
    previous_statements: List[Dict[str, str]] = []
    directive: Optional[str] = None


@app.post("/council/respond")
async def council_respond(req: CouncilRespondRequest):
    """VARYS responds to council meeting discussions"""
    # For now, provide a contextual response
    # Can be enhanced with Anthropic API for full LLM responses
    return {
        "agent": "VARYS",
        "response": f"Little birds have been quiet on this matter. I'll monitor the web for intelligence related to {req.current_topic}.",
        "domain": "ARIA_SANCTUM",
        "expertise": ["intelligence", "market analysis", "competitor tracking"]
    }


# ============ HELPERS ============

async def notify_aria(message: str):
    """Send notification to ARIA"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://aria-reminders:8111/notify",
                json={"message": message, "source": "VARYS", "priority": "normal"},
                timeout=5.0
            )
    except Exception:
        pass  # Silently fail if ARIA not available


async def publish_event(event_type: str, data: dict):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": f"varys.{event_type}",
                    "source": "VARYS",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                },
                timeout=5.0
            )
    except Exception:
        pass


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
    "CHIRON": {"port": 8018, "category": "business", "domain": "CHANCERY"},
    "SCHOLAR": {"port": 8020, "category": "business", "domain": "CHANCERY"},
    "MAGNUS": {"port": 8019, "category": "business", "domain": "CHANCERY"},
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

    return {"status": "synced", "agents": synced, "varys_says": f"The web now tracks {synced} agents."}


# ============ HEALTH SCANNING ============

@app.post("/fleet/scan/health")
async def scan_fleet_health(background_tasks: BackgroundTasks):
    """Scan health of all agents"""
    background_tasks.add_task(do_health_scan)
    return {"status": "started", "varys_says": "Sending little birds to check on the flock."}


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
                except Exception:
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
    return {"status": "started", "varys_says": "Mapping the abilities of every piece on the board."}


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
                except Exception:
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
    return {
        "status": "started",
        "audit_id": str(audit['id']),
        "varys_says": "The spider begins weaving its web of knowledge."
    }


async def do_full_audit(audit_id: str):
    """Background full audit"""
    if not pool:
        return

    try:
        # Sync fleet registry first
        await sync_fleet_registry()

        # Health scan
        await do_health_scan()

        # Capability scan
        await do_capability_scan()

        async with pool.acquire() as conn:
            # Analyze duplicates
            dup_result = await analyze_duplicates_internal(conn)

            # Analyze gaps
            gap_result = await analyze_gaps_internal(conn)

            # Get stats
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
                cap_count['count'], dup_result, gap_result)
    except Exception as e:
        async with pool.acquire() as conn:
            await conn.execute("""
                UPDATE varys_fleet_audits SET status = 'failed', audit_data = $2
                WHERE id = $1::uuid
            """, audit_id, json.dumps({"error": str(e)}))


async def analyze_duplicates_internal(conn) -> int:
    """Internal duplicate analysis for audit"""
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
    return detected


async def analyze_gaps_internal(conn) -> int:
    """Internal gap analysis for audit"""
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
    return gaps_found


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


@app.get("/fleet/audits")
async def list_audits(limit: int = 10):
    """List recent audits"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM varys_fleet_audits ORDER BY started_at DESC LIMIT {limit}"
        )
        return [dict(r) for r in rows]


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
            assessment = "CRITICAL - Multiple agents failing"
        elif health['unhealthy'] > 2:
            assessment = "DEGRADED - Several agents unhealthy"
        elif duplicates['count'] > 5 or gaps['count'] > 5:
            assessment = "NEEDS ATTENTION - Duplicates or gaps"
        else:
            assessment = "HEALTHY - Fleet operating normally"

        return {
            "assessment": assessment,
            "health": dict(health),
            "by_category": [dict(c) for c in by_category],
            "open_duplicates": duplicates['count'],
            "open_gaps": gaps['count'],
            "generated_at": datetime.now().isoformat(),
            "varys_says": f"The web connects {health['total']} agents. {health['unhealthy']} have gone silent."
        }


# ============ AGENT DETAILS (must be LAST due to path param) ============

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8112)
