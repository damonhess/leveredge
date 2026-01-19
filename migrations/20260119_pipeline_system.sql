-- ============================================================
-- PIPELINE SYSTEM: Multi-Agent Orchestration
-- Database Schema
-- Created: 2026-01-19
-- ============================================================

-- Pipeline definitions
CREATE TABLE IF NOT EXISTS pipeline_definitions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL UNIQUE,
    description TEXT,

    stages JSONB NOT NULL,  -- Ordered array of stage definitions
    -- Stage format: {
    --   "name": "research",
    --   "agent": "SCHOLAR",
    --   "action": "deep-research",
    --   "required_inputs": ["topic"],
    --   "outputs": ["research_report"],
    --   "timeout_minutes": 30,
    --   "retry_count": 2,
    --   "optional": false,
    --   "condition": "score < 80"
    -- }

    default_config JSONB DEFAULT '{}',

    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'disabled', 'deprecated')),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pipeline executions
CREATE TABLE IF NOT EXISTS pipeline_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    pipeline_id UUID REFERENCES pipeline_definitions(id),
    pipeline_name TEXT NOT NULL,

    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'paused', 'completed', 'failed', 'cancelled'
    )),

    -- Input/output
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',

    -- Progress
    current_stage INTEGER DEFAULT 0,
    total_stages INTEGER,

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Metadata
    triggered_by TEXT,  -- "user", "schedule", "agent", "api"
    context JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Stage execution logs
CREATE TABLE IF NOT EXISTS pipeline_stage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    execution_id UUID REFERENCES pipeline_executions(id) ON DELETE CASCADE,

    stage_index INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    agent TEXT NOT NULL,
    action TEXT,

    status TEXT DEFAULT 'pending' CHECK (status IN (
        'pending', 'running', 'completed', 'failed', 'skipped'
    )),

    -- Data flow
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',

    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,

    -- Errors
    error_message TEXT,
    retry_attempt INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_pipeline_definitions_status ON pipeline_definitions(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_definitions_name ON pipeline_definitions(name);
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_status ON pipeline_executions(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_pipeline ON pipeline_executions(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_executions_started ON pipeline_executions(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_pipeline_stage_logs_execution ON pipeline_stage_logs(execution_id);

-- ============================================================
-- SEED PIPELINES
-- ============================================================

-- 1. Agent Upgrade Pipeline
INSERT INTO pipeline_definitions (name, description, stages) VALUES
(
    'agent-upgrade',
    'Evaluate and upgrade an agent''s capabilities',
    '[
        {"name": "evaluate", "agent": "ALOY", "action": "evaluate-agent", "required_inputs": ["agent_name"], "outputs": ["evaluation_report", "improvement_areas"], "timeout_minutes": 15},
        {"name": "research", "agent": "SCHOLAR", "action": "deep-research", "required_inputs": ["improvement_areas"], "outputs": ["best_practices", "implementation_approaches"], "timeout_minutes": 30},
        {"name": "plan", "agent": "CHIRON", "action": "create-plan", "required_inputs": ["evaluation_report", "best_practices"], "outputs": ["upgrade_plan", "tasks"], "timeout_minutes": 20},
        {"name": "review", "agent": "MAGNUS", "action": "review-plan", "required_inputs": ["upgrade_plan"], "outputs": ["approved_plan", "timeline"], "timeout_minutes": 10, "requires_approval": true},
        {"name": "build", "agent": "HEPHAESTUS", "action": "execute-plan", "required_inputs": ["approved_plan"], "outputs": ["build_results", "changes_made"], "timeout_minutes": 60},
        {"name": "verify", "agent": "ALOY", "action": "verify-upgrade", "required_inputs": ["agent_name", "changes_made"], "outputs": ["verification_report", "success"], "timeout_minutes": 15}
    ]'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    stages = EXCLUDED.stages,
    updated_at = NOW();

-- 2. Content Creation Pipeline
INSERT INTO pipeline_definitions (name, description, stages) VALUES
(
    'content-creation',
    'Create content from brief to publication',
    '[
        {"name": "ideate", "agent": "CATALYST", "action": "generate-concepts", "required_inputs": ["brief", "content_type"], "outputs": ["concepts", "angles"], "timeout_minutes": 15},
        {"name": "research", "agent": "SCHOLAR", "action": "research-topic", "required_inputs": ["concepts"], "outputs": ["research_data", "sources"], "timeout_minutes": 20},
        {"name": "write", "agent": "SAGA", "action": "write-content", "required_inputs": ["concepts", "research_data", "content_type"], "outputs": ["draft"], "timeout_minutes": 30},
        {"name": "design", "agent": "PRISM", "action": "create-visuals", "required_inputs": ["draft", "content_type"], "outputs": ["visuals", "layout"], "timeout_minutes": 20, "optional": true},
        {"name": "review", "agent": "RELIC", "action": "review-content", "required_inputs": ["draft"], "outputs": ["feedback", "score"], "timeout_minutes": 15},
        {"name": "publish", "agent": "HERMES", "action": "publish-content", "required_inputs": ["draft", "destination"], "outputs": ["publication_url"], "timeout_minutes": 10}
    ]'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    stages = EXCLUDED.stages,
    updated_at = NOW();

-- 3. Deep Research Pipeline
INSERT INTO pipeline_definitions (name, description, stages) VALUES
(
    'deep-research',
    'Comprehensive research on a topic',
    '[
        {"name": "scope", "agent": "CHIRON", "action": "define-scope", "required_inputs": ["question"], "outputs": ["research_questions", "scope"], "timeout_minutes": 10},
        {"name": "search", "agent": "SCHOLAR", "action": "web-research", "required_inputs": ["research_questions"], "outputs": ["raw_data", "sources"], "timeout_minutes": 30},
        {"name": "analyze", "agent": "SCHOLAR", "action": "analyze-data", "required_inputs": ["raw_data"], "outputs": ["insights", "patterns"], "timeout_minutes": 20},
        {"name": "synthesize", "agent": "SAGA", "action": "write-report", "required_inputs": ["insights", "sources", "question"], "outputs": ["report"], "timeout_minutes": 25},
        {"name": "review", "agent": "RELIC", "action": "fact-check", "required_inputs": ["report", "sources"], "outputs": ["verified_report", "confidence"], "timeout_minutes": 15}
    ]'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    stages = EXCLUDED.stages,
    updated_at = NOW();

-- 4. Client Onboarding Pipeline
INSERT INTO pipeline_definitions (name, description, stages) VALUES
(
    'client-onboarding',
    'Onboard a new client from setup to welcome',
    '[
        {"name": "setup-project", "agent": "MAGNUS", "action": "create-project", "required_inputs": ["client_name", "project_type"], "outputs": ["project_id"], "timeout_minutes": 5},
        {"name": "setup-billing", "agent": "LITTLEFINGER", "action": "create-client", "required_inputs": ["client_name", "billing_info"], "outputs": ["client_id"], "timeout_minutes": 5},
        {"name": "track-portfolio", "agent": "VARYS", "action": "add-win", "required_inputs": ["client_name", "deal_value"], "outputs": ["win_id"], "timeout_minutes": 5},
        {"name": "create-workspace", "agent": "HEPHAESTUS", "action": "setup-workspace", "required_inputs": ["client_name"], "outputs": ["workspace_path"], "timeout_minutes": 15, "optional": true},
        {"name": "notify", "agent": "HERMES", "action": "send-welcome", "required_inputs": ["client_name", "contact_email"], "outputs": ["notification_sent"], "timeout_minutes": 5}
    ]'::jsonb
)
ON CONFLICT (name) DO UPDATE SET
    description = EXCLUDED.description,
    stages = EXCLUDED.stages,
    updated_at = NOW();

-- ============================================================
-- HELPER FUNCTIONS
-- ============================================================

-- Get active pipelines with execution stats
CREATE OR REPLACE FUNCTION pipeline_stats()
RETURNS TABLE (
    pipeline_name TEXT,
    total_executions BIGINT,
    completed BIGINT,
    failed BIGINT,
    avg_duration_seconds NUMERIC,
    last_executed TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pd.name,
        COUNT(pe.id),
        COUNT(*) FILTER (WHERE pe.status = 'completed'),
        COUNT(*) FILTER (WHERE pe.status = 'failed'),
        AVG(EXTRACT(EPOCH FROM (pe.completed_at - pe.started_at)))::NUMERIC,
        MAX(pe.started_at)
    FROM pipeline_definitions pd
    LEFT JOIN pipeline_executions pe ON pd.id = pe.pipeline_id
    WHERE pd.status = 'active'
    GROUP BY pd.name
    ORDER BY pd.name;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- Complete
-- ============================================================
