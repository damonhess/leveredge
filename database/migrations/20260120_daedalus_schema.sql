-- =============================================================================
-- DAEDALUS - Architect of the Labyrinth
-- Migration: Create DAEDALUS infrastructure strategy tables
-- Date: 2026-01-20
-- =============================================================================

-- Vendor evaluations
CREATE TABLE IF NOT EXISTS daedalus_vendor_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor TEXT NOT NULL,
    category TEXT, -- 'cloud', 'cdn', 'database', 'monitoring'
    evaluation_date DATE DEFAULT CURRENT_DATE,
    scores JSONB, -- { "cost": 8, "performance": 7, "compliance": 9, ... }
    pros TEXT[],
    cons TEXT[],
    use_cases TEXT[],
    pricing_data JSONB,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Architecture decisions
CREATE TABLE IF NOT EXISTS daedalus_architecture_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_type TEXT, -- 'hosting', 'scaling', 'client_setup', 'migration'
    context TEXT,
    options_evaluated JSONB,
    recommendation TEXT,
    rationale TEXT,
    cost_impact DECIMAL,
    risk_assessment TEXT,
    status TEXT CHECK (status IN ('proposed', 'approved', 'implemented', 'rejected')) DEFAULT 'proposed',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    implemented_at TIMESTAMPTZ
);

-- Cost tracking
CREATE TABLE IF NOT EXISTS daedalus_cost_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    month DATE NOT NULL,
    category TEXT NOT NULL, -- 'hosting', 'cdn', 'api', 'monitoring', 'other'
    vendor TEXT NOT NULL,
    amount DECIMAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Client infrastructure configurations
CREATE TABLE IF NOT EXISTS daedalus_client_infrastructure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id UUID, -- Reference to client in main system
    client_name TEXT NOT NULL,
    tier INTEGER DEFAULT 1,
    isolation_level TEXT CHECK (isolation_level IN ('shared', 'database_isolated', 'single_tenant')) DEFAULT 'shared',
    infrastructure JSONB, -- { "server": "...", "database": "...", "addons": [...] }
    monthly_cost DECIMAL,
    compliance_requirements TEXT[],
    status TEXT CHECK (status IN ('planning', 'provisioned', 'active', 'deprecated')) DEFAULT 'planning',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scaling events / trigger history
CREATE TABLE IF NOT EXISTS daedalus_scaling_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_type TEXT, -- 'cpu', 'memory', 'io', 'manual', 'scheduled'
    action_taken TEXT, -- 'scale_up', 'scale_out', 'optimize', 'none'
    before_state JSONB,
    after_state JSONB,
    cost_before DECIMAL,
    cost_after DECIMAL,
    success BOOLEAN DEFAULT true,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_daedalus_vendor_eval_vendor ON daedalus_vendor_evaluations(vendor);
CREATE INDEX IF NOT EXISTS idx_daedalus_vendor_eval_category ON daedalus_vendor_evaluations(category);
CREATE INDEX IF NOT EXISTS idx_daedalus_decisions_type ON daedalus_architecture_decisions(decision_type);
CREATE INDEX IF NOT EXISTS idx_daedalus_decisions_status ON daedalus_architecture_decisions(status);
CREATE INDEX IF NOT EXISTS idx_daedalus_cost_month ON daedalus_cost_tracking(month);
CREATE INDEX IF NOT EXISTS idx_daedalus_cost_vendor ON daedalus_cost_tracking(vendor);
CREATE INDEX IF NOT EXISTS idx_daedalus_client_infra_tier ON daedalus_client_infrastructure(tier);
CREATE INDEX IF NOT EXISTS idx_daedalus_client_infra_status ON daedalus_client_infrastructure(status);

-- Update agents table (if exists)
INSERT INTO agents (name, display_name, tagline, port, category, domain, is_llm_powered, status)
VALUES ('daedalus', 'DAEDALUS', 'Architect of the Labyrinth', 8026, 'infrastructure', 'THE_KEEP', true, 'active')
ON CONFLICT (name) DO UPDATE SET
    port = 8026,
    tagline = 'Architect of the Labyrinth',
    domain = 'THE_KEEP',
    is_llm_powered = true,
    status = 'active';

-- =============================================================================
-- END MIGRATION
-- =============================================================================
