-- Migration 000005: Backup and Monitoring Infrastructure

-- Backup tracking
CREATE TABLE IF NOT EXISTS backup_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_type TEXT NOT NULL, -- 'full', 'schema', 'incremental'
    target TEXT NOT NULL, -- 'prod', 'dev'
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'completed', 'failed', 'verified')),
    verified_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- System health checks
CREATE TABLE IF NOT EXISTS system_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component TEXT NOT NULL, -- 'database', 'n8n', 'agent', 'redis', etc.
    target TEXT NOT NULL, -- specific instance
    status TEXT NOT NULL, -- 'healthy', 'degraded', 'unhealthy', 'unknown'
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    response_time_ms INT,
    details JSONB DEFAULT '{}',
    error_message TEXT
);

-- Event log (system-wide)
CREATE TABLE IF NOT EXISTS system_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    severity TEXT DEFAULT 'info' CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical')),
    message TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Database metrics (for trending)
CREATE TABLE IF NOT EXISTS db_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target TEXT NOT NULL, -- 'prod', 'dev'
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    total_size_bytes BIGINT,
    table_count INT,
    connection_count INT,
    active_queries INT,
    cache_hit_ratio DECIMAL(5,4),
    details JSONB DEFAULT '{}'
);

-- LLM model pricing reference
CREATE TABLE IF NOT EXISTS llm_model_pricing (
    id SERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    input_price_per_million DECIMAL(10,4),
    output_price_per_million DECIMAL(10,4),
    context_window INT,
    effective_date DATE DEFAULT CURRENT_DATE,
    notes TEXT,
    UNIQUE(provider, model_name, effective_date)
);

-- LLM daily summary (aggregated)
CREATE TABLE IF NOT EXISTS llm_daily_summary (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL,
    total_calls INT DEFAULT 0,
    total_input_tokens BIGINT DEFAULT 0,
    total_output_tokens BIGINT DEFAULT 0,
    total_cost DECIMAL(10,4) DEFAULT 0,
    breakdown_by_agent JSONB DEFAULT '{}',
    breakdown_by_model JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(date)
);

-- Build log (for tracking deployments)
CREATE TABLE IF NOT EXISTS build_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name TEXT NOT NULL,
    version TEXT,
    build_type TEXT, -- 'deploy', 'rollback', 'hotfix'
    status TEXT DEFAULT 'pending',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    deployed_by TEXT,
    commit_hash TEXT,
    notes TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_backup_history_target ON backup_history(target, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_health_component ON system_health(component, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_severity ON system_events(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_db_metrics_target ON db_metrics(target, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_llm_daily_summary_date ON llm_daily_summary(date DESC);
CREATE INDEX IF NOT EXISTS idx_build_log_service ON build_log(service_name, started_at DESC);

-- Cleanup old entries function (keep 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_monitoring_data()
RETURNS void AS $$
BEGIN
    DELETE FROM system_health WHERE checked_at < NOW() - INTERVAL '90 days';
    DELETE FROM system_events WHERE created_at < NOW() - INTERVAL '90 days';
    DELETE FROM db_metrics WHERE captured_at < NOW() - INTERVAL '90 days';
    DELETE FROM aegis_health_checks WHERE checked_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Seed LLM pricing
INSERT INTO llm_model_pricing (provider, model_name, input_price_per_million, output_price_per_million, context_window) VALUES
('anthropic', 'claude-3-5-sonnet-20241022', 3.00, 15.00, 200000),
('anthropic', 'claude-3-5-haiku-20241022', 1.00, 5.00, 200000),
('anthropic', 'claude-3-opus-20240229', 15.00, 75.00, 200000),
('openai', 'gpt-4o', 2.50, 10.00, 128000),
('openai', 'gpt-4o-mini', 0.15, 0.60, 128000),
('openai', 'gpt-4-turbo', 10.00, 30.00, 128000),
('google', 'gemini-1.5-pro', 3.50, 10.50, 1000000),
('google', 'gemini-1.5-flash', 0.075, 0.30, 1000000)
ON CONFLICT (provider, model_name, effective_date) DO NOTHING;

SELECT 'Backup and monitoring migration complete' as status;
