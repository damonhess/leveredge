-- Migration 000004: Views and Helper Functions

-- LLM Cost Summary View (uses PROD column names: agent_source, cost_usd)
CREATE OR REPLACE VIEW llm_cost_summary AS
SELECT
    date_trunc('day', created_at) as day,
    COALESCE(agent_source, 'unknown') as agent_name,
    model,
    COUNT(*) as calls,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    SUM(COALESCE(cost_usd, 0)) as total_cost
FROM llm_usage
GROUP BY 1, 2, 3
ORDER BY 1 DESC, total_cost DESC;

-- Daily Cost Totals View
CREATE OR REPLACE VIEW llm_daily_costs AS
SELECT
    date_trunc('day', created_at) as day,
    SUM(COALESCE(cost_usd, 0)) as total_cost,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    COUNT(*) as total_calls
FROM llm_usage
GROUP BY 1
ORDER BY 1 DESC;

-- AEGIS Expiring Credentials View
CREATE OR REPLACE VIEW aegis_expiring_credentials AS
SELECT
    name,
    provider,
    status,
    expires_at,
    EXTRACT(EPOCH FROM (expires_at - NOW()))/3600 as hours_until_expiry
FROM aegis_credentials_v2
WHERE expires_at IS NOT NULL
  AND expires_at < NOW() + INTERVAL '30 days'
  AND status NOT IN ('retired', 'expired')
ORDER BY expires_at;

-- Portfolio Summary View
CREATE OR REPLACE VIEW portfolio_summary AS
SELECT
    COUNT(*) as total_wins,
    COALESCE(SUM(value_low), 0) as total_low,
    COALESCE(SUM(value_high), 0) as total_high,
    COUNT(DISTINCT category) as categories
FROM aria_wins;

-- Agent Health View (placeholder - populated by monitoring)
CREATE TABLE IF NOT EXISTS agent_health (
    agent_name TEXT PRIMARY KEY,
    port INT,
    status TEXT DEFAULT 'unknown',
    last_check TIMESTAMPTZ,
    response_time_ms INT,
    error_message TEXT
);

-- Helper function: Update timestamps
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to BASE TABLES with updated_at (not views)
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables tb ON c.table_name = tb.table_name AND c.table_schema = tb.table_schema
        WHERE c.column_name = 'updated_at'
          AND c.table_schema = 'public'
          AND tb.table_type = 'BASE TABLE'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
            BEFORE UPDATE ON %I
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
        ', t, t, t, t);
    END LOOP;
END $$;

-- HADES operations table (for rollback tracking)
CREATE TABLE IF NOT EXISTS hades_operations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    operation_type TEXT NOT NULL,
    target TEXT NOT NULL,
    previous_state JSONB,
    new_state JSONB,
    rollback_command TEXT,
    executed_by TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    rolled_back BOOLEAN DEFAULT FALSE,
    rolled_back_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_hades_operations_ts ON hades_operations(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_hades_operations_type ON hades_operations(operation_type);

SELECT 'Views and functions migration complete' as status;
