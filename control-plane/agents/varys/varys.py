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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8112)
