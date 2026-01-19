-- ============================================================
-- VARYS: Master of Whispers
-- Database Schema
-- Created: 2026-01-19
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
        COALESCE(SUM(aria_wins.value_low), 0),
        COALESCE(SUM(aria_wins.value_high), 0),
        COUNT(*) FILTER (WHERE aria_wins.created_at > NOW() - INTERVAL '7 days'),
        COUNT(*) FILTER (WHERE aria_wins.created_at > NOW() - INTERVAL '30 days')
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
        'id', vi.id, 'type', vi.report_type, 'title', vi.title, 'summary', vi.summary
    ))
    FROM varys_intelligence vi
    WHERE vi.created_at > NOW() - INTERVAL '24 hours'
    AND vi.status = 'active';

    -- Active opportunities
    RETURN QUERY
    SELECT 'opportunities'::TEXT, jsonb_agg(jsonb_build_object(
        'id', vo.id, 'name', vo.name, 'stage', vo.stage, 'next_action', vo.next_action
    ))
    FROM varys_opportunities vo
    WHERE vo.stage NOT IN ('won', 'lost', 'deferred');

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
        'value_low', COALESCE(SUM(aw.value_low), 0),
        'value_high', COALESCE(SUM(aw.value_high), 0)
    )
    FROM aria_wins aw;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Complete
-- ============================================================
