# GSD: VARYS - Master of Whispers

**Priority:** HIGH
**Estimated Time:** 8 hours
**Port:** 8018
**Domain:** ARIA_SANCTUM

---

## IDENTITY

**Name:** VARYS
**Title:** Master of Whispers
**Tagline:** "The spider sits at the center of the web. Every vibration tells a story."

VARYS knows everything. He tracks the portfolio, monitors market signals, gathers competitive intel, and whispers insights to those who need them.

**Personality:**
- **Omniscient** - Has eyes and ears everywhere
- **Patient** - Watches patterns emerge over time
- **Analytical** - Connects dots others miss
- **Discrete** - Shares intel only with those who need it

**Voice:**
> "Little birds have been singing. Your competitor just raised $5M. Their hiring patterns suggest they're pivoting to compliance automation."

> "The portfolio has grown to $127K across 34 wins. Three opportunities are ripening."

> "I've noticed a pattern. Every time you build past midnight, the next day's velocity drops 40%. The data suggests sleep would be a strategic advantage."

---

## RESPONSIBILITIES

### 1. Portfolio Management
- Track all wins (aria_wins table)
- Calculate portfolio value
- Monitor win velocity
- Identify patterns in successful projects

### 2. Market Intelligence
- Monitor competitor activity
- Track industry trends
- Identify market opportunities
- Alert on relevant news

### 3. Internal Intelligence
- Agent performance metrics
- Project health signals
- Resource utilization
- Risk detection

### 4. Strategic Insights
- Pattern recognition across all data
- Predictive analysis
- Opportunity identification
- Threat detection

---

## DATABASE SCHEMA

```sql
-- ============================================================
-- VARYS: Master of Whispers
-- Database Schema
-- ============================================================

-- Intelligence reports
CREATE TABLE IF NOT EXISTS varys_intelligence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    report_type TEXT NOT NULL CHECK (report_type IN (
        'market', 'competitor', 'opportunity', 'threat', 
        'pattern', 'insight', 'alert', 'portfolio'
    )),
    
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    
    source TEXT,  -- Where the intel came from
    confidence DECIMAL(5,2) DEFAULT 70.0,  -- 0-100
    
    -- Relevance
    domains TEXT[] DEFAULT '{}',
    agents TEXT[] DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    
    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'archived', 'actioned')),
    actioned_at TIMESTAMPTZ,
    actioned_by TEXT,
    action_taken TEXT,
    
    -- Timestamps
    observed_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Competitors tracking
CREATE TABLE IF NOT EXISTS varys_competitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL UNIQUE,
    website TEXT,
    description TEXT,
    
    -- Classification
    threat_level TEXT DEFAULT 'medium' CHECK (threat_level IN ('low', 'medium', 'high', 'critical')),
    market_segment TEXT,
    
    -- Intel
    known_clients TEXT[] DEFAULT '{}',
    known_products TEXT[] DEFAULT '{}',
    funding_info JSONB DEFAULT '{}',
    team_size_estimate INTEGER,
    
    -- Tracking
    last_activity TIMESTAMPTZ,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Competitor activity log
CREATE TABLE IF NOT EXISTS varys_competitor_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    competitor_id UUID REFERENCES varys_competitors(id) ON DELETE CASCADE,
    
    activity_type TEXT CHECK (activity_type IN (
        'funding', 'hiring', 'product_launch', 'partnership',
        'news', 'social_media', 'job_posting', 'other'
    )),
    
    title TEXT NOT NULL,
    description TEXT,
    source_url TEXT,
    
    significance TEXT DEFAULT 'medium' CHECK (significance IN ('low', 'medium', 'high')),
    
    observed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Market signals
CREATE TABLE IF NOT EXISTS varys_market_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    signal_type TEXT CHECK (signal_type IN (
        'trend', 'regulation', 'technology', 'demand', 
        'pricing', 'consolidation', 'disruption'
    )),
    
    title TEXT NOT NULL,
    description TEXT,
    source TEXT,
    source_url TEXT,
    
    impact TEXT DEFAULT 'medium' CHECK (impact IN ('low', 'medium', 'high', 'critical')),
    timeframe TEXT,  -- "immediate", "3-6 months", "1+ year"
    
    -- Relevance to LeverEdge
    relevance_score DECIMAL(5,2) DEFAULT 50.0,
    recommended_action TEXT,
    
    observed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Opportunities pipeline
CREATE TABLE IF NOT EXISTS varys_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL,
    description TEXT,
    
    -- Source
    source TEXT,  -- "referral", "inbound", "outreach", "market_signal"
    source_details TEXT,
    
    -- Qualification
    stage TEXT DEFAULT 'identified' CHECK (stage IN (
        'identified', 'researching', 'qualified', 'pursuing', 
        'negotiating', 'won', 'lost', 'deferred'
    )),
    
    -- Value
    estimated_value_low DECIMAL(10,2),
    estimated_value_high DECIMAL(10,2),
    probability DECIMAL(5,2) DEFAULT 50.0,
    
    -- Details
    contact_name TEXT,
    contact_email TEXT,
    company TEXT,
    industry TEXT,
    
    -- Tracking
    next_action TEXT,
    next_action_date DATE,
    notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolio summary (materialized view refresh)
CREATE TABLE IF NOT EXISTS varys_portfolio_snapshot (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    snapshot_date DATE DEFAULT CURRENT_DATE UNIQUE,
    
    total_wins INTEGER,
    total_value_low DECIMAL(12,2),
    total_value_high DECIMAL(12,2),
    
    wins_this_week INTEGER,
    wins_this_month INTEGER,
    
    top_domains JSONB DEFAULT '[]',
    top_tags JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent performance tracking
CREATE TABLE IF NOT EXISTS varys_agent_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    agent TEXT NOT NULL,
    metric_date DATE DEFAULT CURRENT_DATE,
    
    tasks_completed INTEGER DEFAULT 0,
    tasks_failed INTEGER DEFAULT 0,
    avg_completion_time_hours DECIMAL(6,2),
    
    errors_count INTEGER DEFAULT 0,
    lessons_reported INTEGER DEFAULT 0,
    
    availability_percentage DECIMAL(5,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(agent, metric_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_varys_intelligence_type ON varys_intelligence(report_type);
CREATE INDEX IF NOT EXISTS idx_varys_intelligence_status ON varys_intelligence(status);
CREATE INDEX IF NOT EXISTS idx_varys_opportunities_stage ON varys_opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_varys_market_signals_impact ON varys_market_signals(impact);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Calculate current portfolio value
CREATE OR REPLACE FUNCTION varys_portfolio_value()
RETURNS TABLE (
    total_wins BIGINT,
    value_low DECIMAL,
    value_high DECIMAL,
    wins_this_week BIGINT,
    wins_this_month BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*),
        COALESCE(SUM(value_low), 0),
        COALESCE(SUM(value_high), 0),
        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '7 days'),
        COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '30 days')
    FROM aria_wins;
END;
$$ LANGUAGE plpgsql;

-- Get daily intelligence briefing
CREATE OR REPLACE FUNCTION varys_daily_briefing()
RETURNS TABLE (
    category TEXT,
    items JSONB
) AS $$
BEGIN
    -- New intelligence
    RETURN QUERY
    SELECT 'new_intelligence'::TEXT, jsonb_agg(jsonb_build_object(
        'id', id, 'type', report_type, 'title', title, 'summary', summary
    ))
    FROM varys_intelligence
    WHERE created_at > NOW() - INTERVAL '24 hours'
    AND status = 'active';
    
    -- Active opportunities
    RETURN QUERY
    SELECT 'opportunities'::TEXT, jsonb_agg(jsonb_build_object(
        'id', id, 'name', name, 'stage', stage, 'next_action', next_action
    ))
    FROM varys_opportunities
    WHERE stage NOT IN ('won', 'lost', 'deferred');
    
    -- Recent competitor activity
    RETURN QUERY
    SELECT 'competitor_activity'::TEXT, jsonb_agg(jsonb_build_object(
        'competitor', c.name, 'activity', a.title, 'type', a.activity_type
    ))
    FROM varys_competitor_activity a
    JOIN varys_competitors c ON a.competitor_id = c.id
    WHERE a.observed_at > NOW() - INTERVAL '7 days';
    
    -- Portfolio status
    RETURN QUERY
    SELECT 'portfolio'::TEXT, jsonb_build_object(
        'total_wins', COUNT(*),
        'value_low', COALESCE(SUM(value_low), 0),
        'value_high', COALESCE(SUM(value_high), 0)
    )
    FROM aria_wins;
END;
$$ LANGUAGE plpgsql;
```

---

## VARYS SERVICE

Create `/opt/leveredge/control-plane/agents/varys/varys.py`:

```python
"""
VARYS - Master of Whispers
Port: 8018
Domain: ARIA_SANCTUM

The spider sits at the center of the web. Every vibration tells a story.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import os
import asyncpg
import httpx

app = FastAPI(
    title="VARYS - Master of Whispers",
    description="The spider sits at the center of the web. Every vibration tells a story.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global pool
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

# ============ HEALTH ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "VARYS - Master of Whispers",
        "port": 8018,
        "tagline": "The spider sits at the center of the web. Every vibration tells a story."
    }

# ============ PORTFOLIO ============

@app.get("/portfolio")
async def get_portfolio():
    """Get current portfolio status"""
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
            "value_low": row['low'],
            "value_high": row['high']
        }

# ============ INTELLIGENCE ============

@app.post("/intelligence")
async def report_intelligence(report: IntelReport):
    """Submit new intelligence report"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_intelligence 
            (report_type, title, summary, details, source, confidence, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, report.report_type, report.title, report.summary,
            report.details, report.source, report.confidence, report.tags)
        
        # Alert ARIA if high priority
        if report.report_type in ['threat', 'opportunity'] or report.confidence > 85:
            await notify_aria(f"🕷️ Intel: {report.title}")
        
        return dict(row)

@app.get("/intelligence")
async def list_intelligence(
    report_type: Optional[str] = None,
    status: str = "active",
    limit: int = 50
):
    """List intelligence reports"""
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
                "value_low": portfolio['low'],
                "value_high": portfolio['high']
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
        total_value = sum(o['estimated_value_high'] or 0 for o in opps)
        summary_parts.append(f"{len(opps)} active opportunities worth up to ${total_value:,.0f}.")
    
    return " ".join(summary_parts)

# ============ COMPETITORS ============

@app.post("/competitors")
async def add_competitor(competitor: Competitor):
    """Add a competitor to track"""
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

@app.post("/competitors/{competitor_id}/activity")
async def log_competitor_activity(
    competitor_id: str,
    activity_type: str,
    title: str,
    description: str = None,
    source_url: str = None,
    significance: str = "medium"
):
    """Log competitor activity"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_competitor_activity 
            (competitor_id, activity_type, title, description, source_url, significance)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, competitor_id, activity_type, title, description, source_url, significance)
        
        if significance == "high":
            comp = await conn.fetchrow("SELECT name FROM varys_competitors WHERE id = $1", competitor_id)
            await notify_aria(f"🕷️ High-significance competitor activity: {comp['name']} - {title}")
        
        return dict(row)

# ============ OPPORTUNITIES ============

@app.post("/opportunities")
async def create_opportunity(opp: Opportunity):
    """Create new opportunity"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_opportunities 
            (name, description, source, estimated_value_low, estimated_value_high, company, contact_name)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, opp.name, opp.description, opp.source, 
            opp.estimated_value_low, opp.estimated_value_high, 
            opp.company, opp.contact_name)
        
        await notify_aria(f"🕷️ New opportunity identified: {opp.name}")
        return dict(row)

@app.get("/opportunities")
async def list_opportunities(stage: Optional[str] = None):
    """List opportunities"""
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

@app.put("/opportunities/{opp_id}/stage")
async def update_opportunity_stage(opp_id: str, stage: str, notes: str = None):
    """Update opportunity stage"""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE varys_opportunities 
            SET stage = $2, notes = COALESCE($3, notes), updated_at = NOW()
            WHERE id = $1
        """, opp_id, stage, notes)
        
        if stage == "won":
            opp = await conn.fetchrow("SELECT name, estimated_value_high FROM varys_opportunities WHERE id = $1", opp_id)
            await notify_aria(f"🎉 Opportunity WON: {opp['name']} (${opp['estimated_value_high']:,.0f})")
        
        return {"status": "updated", "stage": stage}

# ============ MARKET SIGNALS ============

@app.post("/market-signals")
async def report_market_signal(
    signal_type: str,
    title: str,
    description: str = None,
    source: str = None,
    impact: str = "medium",
    relevance_score: float = 50.0
):
    """Report a market signal"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO varys_market_signals 
            (signal_type, title, description, source, impact, relevance_score)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, signal_type, title, description, source, impact, relevance_score)
        
        if impact in ['high', 'critical']:
            await notify_aria(f"🕷️ Market signal ({impact}): {title}")
        
        return dict(row)

@app.get("/market-signals")
async def list_market_signals(impact: Optional[str] = None, limit: int = 20):
    """List market signals"""
    async with pool.acquire() as conn:
        query = "SELECT * FROM varys_market_signals"
        params = []
        
        if impact:
            query += " WHERE impact = $1"
            params.append(impact)
        
        query += f" ORDER BY observed_at DESC LIMIT {limit}"
        
        rows = await conn.fetch(query, *params) if params else await conn.fetch(query)
        return [dict(row) for row in rows]

# ============ HELPERS ============

async def notify_aria(message: str):
    """Send notification to ARIA"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8111/notify",
                json={"message": message, "source": "VARYS", "priority": "normal"},
                timeout=5.0
            )
    except:
        pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8018)
```

---

## DOCKERFILE

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY varys.py .

EXPOSE 8018

CMD ["uvicorn", "varys:app", "--host", "0.0.0.0", "--port", "8018"]
```

---

## MCP TOOLS

Add to HEPHAESTUS:

```python
@mcp_tool(name="varys_portfolio")
async def varys_portfolio() -> dict:
    """Get portfolio status from VARYS"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8018/portfolio")
        return response.json()

@mcp_tool(name="varys_briefing")
async def varys_briefing() -> dict:
    """Get VARYS's daily intelligence briefing"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8018/briefing")
        return response.json()

@mcp_tool(name="varys_intel")
async def varys_intel(report_type: str, title: str, summary: str, confidence: float = 70.0) -> dict:
    """Report intelligence to VARYS"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8018/intelligence",
            json={"report_type": report_type, "title": title, "summary": summary, "confidence": confidence}
        )
        return response.json()

@mcp_tool(name="varys_opportunities")
async def varys_opportunities() -> dict:
    """Get active opportunities from VARYS"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8018/opportunities")
        return response.json()

@mcp_tool(name="varys_competitors")
async def varys_competitors() -> dict:
    """Get tracked competitors from VARYS"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8018/competitors")
        return response.json()
```

---

## CADDY

```
varys.leveredgeai.com {
    reverse_proxy localhost:8018
}
```

---

## BUILD & RUN

```bash
# Create migration
psql $DEV_DATABASE_URL -f /opt/leveredge/database/migrations/20260119_varys_schema.sql

# Build
cd /opt/leveredge/control-plane/agents/varys
docker build -t varys:dev .

# Run
docker run -d --name varys \
  --network leveredge-network \
  -p 8018:8018 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  varys:dev

# Verify
curl http://localhost:8018/health
curl http://localhost:8018/portfolio
curl http://localhost:8018/briefing
```

---

## GIT COMMIT

```bash
git add .
git commit -m "VARYS: Master of Whispers

- Intelligence gathering and reporting
- Portfolio tracking (aria_wins integration)
- Competitor monitoring
- Opportunity pipeline
- Market signals tracking
- Daily briefing generation
- MCP tools for HEPHAESTUS

The spider sits at the center of the web."
```

---

*"The spider sits at the center of the web. Every vibration tells a story."*
