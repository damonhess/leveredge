# GSD: SUPABASE COMPLETE - NO LOOSE ENDS

*Prepared: January 18, 2026*
*Purpose: Fix ALL Supabase/database issues in one comprehensive pass*
*Estimated Duration: 4-6 hours*

---

## GOAL

After this GSD, Supabase is:
- ✅ Properly versioned with migrations
- ✅ DEV and PROD schemas identical
- ✅ All data preserved
- ✅ Backups verified and automated
- ✅ Health monitoring in place
- ✅ Connection pooling configured
- ✅ Proper indexes on all tables
- ✅ Environment separation complete
- ✅ Fully documented

**NO MORE LOOSE ENDS.**

---

## SECTION 1: FULL BACKUP (BEFORE ANYTHING)

### 1.1 Backup PROD (Full)

```bash
mkdir -p /opt/leveredge/backups/supabase-complete-$(date +%Y%m%d)
cd /opt/leveredge/backups/supabase-complete-$(date +%Y%m%d)

# Full backup with data
docker exec supabase-db-prod pg_dump -U postgres -d postgres \
    --no-owner --no-acl \
    > prod_full_$(date +%Y%m%d_%H%M%S).sql

# Schema only
docker exec supabase-db-prod pg_dump -U postgres -d postgres \
    --schema-only --no-owner --no-acl -n public \
    > prod_schema_$(date +%Y%m%d).sql

# Verify
ls -la
wc -l prod_full_*.sql
```

### 1.2 Backup DEV (Full)

```bash
docker exec supabase-db-dev pg_dump -U postgres -d postgres \
    --no-owner --no-acl \
    > dev_full_$(date +%Y%m%d_%H%M%S).sql

docker exec supabase-db-dev pg_dump -U postgres -d postgres \
    --schema-only --no-owner --no-acl -n public \
    > dev_schema_$(date +%Y%m%d).sql
```

### 1.3 Backup PROD Data Tables Separately

For critical data tables, create individual backups:

```bash
# List tables with row counts
docker exec supabase-db-prod psql -U postgres -d postgres -c "
SELECT schemaname, tablename, n_tup_ins as rows
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY n_tup_ins DESC;"

# Backup each table with data
for table in aria_knowledge aria_wins aria_portfolio_summary llm_usage aegis_credentials; do
    docker exec supabase-db-prod pg_dump -U postgres -d postgres \
        --data-only -t $table > prod_data_${table}.sql 2>/dev/null || echo "Table $table not found"
done
```

---

## SECTION 2: INSTALL GOLANG-MIGRATE

### 2.1 Download and Install

```bash
curl -L https://github.com/golang-migrate/migrate/releases/download/v4.17.0/migrate.linux-amd64.tar.gz -o /tmp/migrate.tar.gz
cd /tmp && tar xvzf migrate.tar.gz
sudo mv migrate /usr/local/bin/
sudo chmod +x /usr/local/bin/migrate
migrate --version
```

### 2.2 Create Migration Infrastructure

```bash
mkdir -p /opt/leveredge/migrations
```

---

## SECTION 3: COMPLETE DATABASE AUDIT

### 3.1 List ALL Tables in Both Databases

```bash
# Create audit directory
mkdir -p /opt/leveredge/migrations/audit

# PROD tables
docker exec supabase-db-prod psql -U postgres -d postgres -t -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /opt/leveredge/migrations/audit/prod_tables.txt

# DEV tables
docker exec supabase-db-dev psql -U postgres -d postgres -t -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /opt/leveredge/migrations/audit/dev_tables.txt

# Tables in DEV but not PROD
comm -23 /opt/leveredge/migrations/audit/dev_tables.txt /opt/leveredge/migrations/audit/prod_tables.txt > /opt/leveredge/migrations/audit/to_add_to_prod.txt

# Tables in PROD but not DEV
comm -13 /opt/leveredge/migrations/audit/dev_tables.txt /opt/leveredge/migrations/audit/prod_tables.txt > /opt/leveredge/migrations/audit/prod_only.txt

echo "=== Tables to add to PROD ==="
cat /opt/leveredge/migrations/audit/to_add_to_prod.txt

echo -e "\n=== Tables only in PROD ==="
cat /opt/leveredge/migrations/audit/prod_only.txt
```

### 3.2 Get Row Counts for ALL Tables in PROD

```bash
docker exec supabase-db-prod psql -U postgres -d postgres -c "
SELECT 
    relname as table_name,
    n_live_tup as row_count
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY n_live_tup DESC;" > /opt/leveredge/migrations/audit/prod_row_counts.txt

cat /opt/leveredge/migrations/audit/prod_row_counts.txt
```

### 3.3 Get Full Schema Details for ALL Tables

```bash
# DEV full schema
docker exec supabase-db-dev psql -U postgres -d postgres -c "
SELECT 
    t.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name, c.ordinal_position;" > /opt/leveredge/migrations/audit/dev_columns.txt

# PROD full schema
docker exec supabase-db-prod psql -U postgres -d postgres -c "
SELECT 
    t.table_name,
    c.column_name,
    c.data_type,
    c.is_nullable,
    c.column_default
FROM information_schema.tables t
JOIN information_schema.columns c ON t.table_name = c.table_name
WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
ORDER BY t.table_name, c.ordinal_position;" > /opt/leveredge/migrations/audit/prod_columns.txt
```

### 3.4 List ALL Views

```bash
# DEV views
docker exec supabase-db-dev psql -U postgres -d postgres -t -c "
SELECT table_name FROM information_schema.views 
WHERE table_schema = 'public'
ORDER BY table_name;" | tr -d ' ' | grep -v '^$' > /opt/leveredge/migrations/audit/dev_views.txt

# PROD views
docker exec supabase-db-prod psql -U postgres -d postgres -t -c "
SELECT table_name FROM information_schema.views 
WHERE table_schema = 'public'
ORDER BY table_name;" | tr -d ' ' | grep -v '^$' > /opt/leveredge/migrations/audit/prod_views.txt
```

### 3.5 List ALL Indexes

```bash
# DEV indexes
docker exec supabase-db-dev psql -U postgres -d postgres -c "
SELECT indexname, tablename, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;" > /opt/leveredge/migrations/audit/dev_indexes.txt

# PROD indexes
docker exec supabase-db-prod psql -U postgres -d postgres -c "
SELECT indexname, tablename, indexdef 
FROM pg_indexes 
WHERE schemaname = 'public'
ORDER BY tablename, indexname;" > /opt/leveredge/migrations/audit/prod_indexes.txt
```

### 3.6 Generate Audit Report

```bash
cat > /opt/leveredge/migrations/audit/AUDIT_REPORT.md << 'EOF'
# Database Audit Report
Generated: $(date '+%Y-%m-%d %H:%M:%S')

## Summary

### Tables to Add to PROD (from DEV)
$(cat /opt/leveredge/migrations/audit/to_add_to_prod.txt | sed 's/^/- /')

### Tables Only in PROD (verify if needed)
$(cat /opt/leveredge/migrations/audit/prod_only.txt | sed 's/^/- /')

### PROD Row Counts
$(cat /opt/leveredge/migrations/audit/prod_row_counts.txt)

## Action Plan
1. Create migrations for all DEV-only tables
2. Verify PROD-only tables have data worth keeping
3. Add any missing columns to shared tables
4. Sync views and indexes

EOF
```

---

## SECTION 4: CREATE SCHEMA MIGRATIONS TABLE

### 4.1 Create in Both Databases

```bash
# PROD
docker exec supabase-db-prod psql -U postgres -d postgres -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version BIGINT PRIMARY KEY,
    dirty BOOLEAN NOT NULL DEFAULT FALSE
);"

# DEV
docker exec supabase-db-dev psql -U postgres -d postgres -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version BIGINT PRIMARY KEY,
    dirty BOOLEAN NOT NULL DEFAULT FALSE
);"
```

---

## SECTION 5: CREATE ALL MIGRATIONS

### 5.1 Migration 000001 - Baseline (Shared Tables)

This documents tables that exist in BOTH databases:

```bash
cat > /opt/leveredge/migrations/000001_baseline.up.sql << 'EOSQL'
-- Migration 000001: Baseline
-- Documents existing shared schema as of January 18, 2026
-- Both DEV and PROD already have these tables

-- Core ARIA tables
CREATE TABLE IF NOT EXISTS aria_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(category, key)
);

CREATE TABLE IF NOT EXISTS aria_wins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    value_low DECIMAL(10,2),
    value_high DECIMAL(10,2),
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS aria_portfolio_summary (
    id SERIAL PRIMARY KEY,
    total_wins INT,
    total_value_low DECIMAL(12,2),
    total_value_high DECIMAL(12,2),
    categories JSONB,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- AEGIS V1 credentials (basic)
CREATE TABLE IF NOT EXISTS aegis_credentials (
    id SERIAL PRIMARY KEY,
    credential_name TEXT UNIQUE NOT NULL,
    provider TEXT,
    n8n_credential_id TEXT,
    credential_type TEXT,
    description TEXT,
    environment TEXT DEFAULT 'prod',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

-- LLM usage tracking
CREATE TABLE IF NOT EXISTS llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT NOT NULL,
    output_tokens INT NOT NULL,
    estimated_cost_usd DECIMAL(10,6),
    context TEXT,
    operation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for baseline tables
CREATE INDEX IF NOT EXISTS idx_aria_knowledge_category ON aria_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_aria_knowledge_key ON aria_knowledge(key);
CREATE INDEX IF NOT EXISTS idx_aria_wins_category ON aria_wins(category);
CREATE INDEX IF NOT EXISTS idx_aria_wins_completed ON aria_wins(completed_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_agent ON llm_usage(agent_name);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_aegis_creds_provider ON aegis_credentials(provider);

SELECT 'Baseline migration complete' as status;
EOSQL

cat > /opt/leveredge/migrations/000001_baseline.down.sql << 'EOSQL'
-- Cannot rollback baseline - this is the starting point
SELECT 'Cannot rollback baseline' as status;
EOSQL
```

### 5.2 Migration 000002 - AEGIS V2 (Full)

```bash
cat > /opt/leveredge/migrations/000002_aegis_v2.up.sql << 'EOSQL'
-- Migration 000002: AEGIS V2 Enterprise Credential Management

-- Enhanced credentials table
CREATE TABLE IF NOT EXISTS aegis_credentials_v2 (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    credential_type TEXT NOT NULL,
    provider TEXT NOT NULL DEFAULT 'n8n',
    description TEXT,
    encrypted_value TEXT,
    encryption_key_id TEXT,
    provider_credential_id TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expiring', 'expired', 'rotating', 'failed', 'retired')),
    environment TEXT DEFAULT 'prod',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    last_health_check TIMESTAMPTZ,
    rotation_enabled BOOLEAN DEFAULT FALSE,
    rotation_interval_hours INT DEFAULT 720,
    rotation_strategy TEXT DEFAULT 'manual',
    next_rotation_at TIMESTAMPTZ,
    alert_threshold_hours INT DEFAULT 168,
    alert_sent BOOLEAN DEFAULT FALSE,
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

-- Credential versions for rollback
CREATE TABLE IF NOT EXISTS aegis_credential_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    version INT NOT NULL,
    encrypted_value TEXT,
    provider_credential_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    reason TEXT,
    is_current BOOLEAN DEFAULT TRUE,
    UNIQUE(credential_id, version)
);

-- Comprehensive audit log
CREATE TABLE IF NOT EXISTS aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    credential_id UUID,
    credential_name TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    target TEXT,
    details JSONB DEFAULT '{}',
    ip_address TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

-- Rotation history
CREATE TABLE IF NOT EXISTS aegis_rotation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    rotated_at TIMESTAMPTZ DEFAULT NOW(),
    previous_version INT,
    new_version INT,
    trigger TEXT NOT NULL,
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    rolled_back BOOLEAN DEFAULT FALSE,
    rollback_at TIMESTAMPTZ
);

-- Health checks
CREATE TABLE IF NOT EXISTS aegis_health_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials_v2(id) ON DELETE CASCADE,
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT NOT NULL,
    response_time_ms INT,
    details JSONB DEFAULT '{}',
    error_message TEXT
);

-- Provider registry
CREATE TABLE IF NOT EXISTS aegis_providers (
    id SERIAL PRIMARY KEY,
    provider_name TEXT UNIQUE NOT NULL,
    provider_type TEXT NOT NULL,
    base_url TEXT,
    validation_endpoint TEXT,
    credential_fields JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_aegis_v2_status ON aegis_credentials_v2(status);
CREATE INDEX IF NOT EXISTS idx_aegis_v2_expires ON aegis_credentials_v2(expires_at);
CREATE INDEX IF NOT EXISTS idx_aegis_v2_env ON aegis_credentials_v2(environment);
CREATE INDEX IF NOT EXISTS idx_aegis_v2_provider ON aegis_credentials_v2(provider);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_ts ON aegis_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_action ON aegis_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_aegis_audit_cred ON aegis_audit_log(credential_name);
CREATE INDEX IF NOT EXISTS idx_aegis_health_cred ON aegis_health_checks(credential_id);
CREATE INDEX IF NOT EXISTS idx_aegis_health_ts ON aegis_health_checks(checked_at);

-- Seed providers
INSERT INTO aegis_providers (provider_name, provider_type, base_url, validation_endpoint, credential_fields) VALUES
('openai', 'api_key', 'https://api.openai.com/v1', '/models', '{"api_key": {"type": "secret", "required": true}}'),
('anthropic', 'api_key', 'https://api.anthropic.com/v1', '/messages', '{"api_key": {"type": "secret", "required": true}}'),
('github', 'api_key', 'https://api.github.com', '/user', '{"personal_access_token": {"type": "secret", "required": true}}'),
('cloudflare', 'api_key', 'https://api.cloudflare.com/client/v4', '/user/tokens/verify', '{"api_token": {"type": "secret", "required": true}}'),
('telegram', 'api_key', 'https://api.telegram.org', '/getMe', '{"bot_token": {"type": "secret", "required": true}}'),
('google_oauth', 'oauth2', 'https://oauth2.googleapis.com', '/tokeninfo', '{"client_id": {"type": "string"}, "client_secret": {"type": "secret"}, "refresh_token": {"type": "secret"}}'),
('supabase', 'api_key', NULL, NULL, '{"project_url": {"type": "string"}, "anon_key": {"type": "string"}, "service_role_key": {"type": "secret"}}'),
('caddy_basic_auth', 'basic_auth', NULL, NULL, '{"username": {"type": "string"}, "password_hash": {"type": "secret"}}'),
('elevenlabs', 'api_key', 'https://api.elevenlabs.io/v1', '/voices', '{"api_key": {"type": "secret", "required": true}}'),
('sendgrid', 'api_key', 'https://api.sendgrid.com/v3', '/user/profile', '{"api_key": {"type": "secret", "required": true}}'),
('stripe', 'api_key', 'https://api.stripe.com/v1', '/balance', '{"secret_key": {"type": "secret"}, "publishable_key": {"type": "string"}}'),
('fal_ai', 'api_key', 'https://fal.run', '/health', '{"api_key": {"type": "secret", "required": true}}'),
('replicate', 'api_key', 'https://api.replicate.com/v1', '/models', '{"api_token": {"type": "secret", "required": true}}'),
('google_ai', 'api_key', 'https://generativelanguage.googleapis.com/v1', '/models', '{"api_key": {"type": "secret", "required": true}}')
ON CONFLICT (provider_name) DO NOTHING;

SELECT 'AEGIS V2 migration complete' as status;
EOSQL

cat > /opt/leveredge/migrations/000002_aegis_v2.down.sql << 'EOSQL'
-- Rollback AEGIS V2
DROP TABLE IF EXISTS aegis_health_checks CASCADE;
DROP TABLE IF EXISTS aegis_rotation_history CASCADE;
DROP TABLE IF EXISTS aegis_audit_log CASCADE;
DROP TABLE IF EXISTS aegis_credential_versions CASCADE;
DROP TABLE IF EXISTS aegis_credentials_v2 CASCADE;
DROP TABLE IF EXISTS aegis_providers CASCADE;
EOSQL
```

### 5.3 Migration 000003 - CONCLAVE Tables

```bash
cat > /opt/leveredge/migrations/000003_conclave.up.sql << 'EOSQL'
-- Migration 000003: CONCLAVE Council Meeting System

-- Council meetings
CREATE TABLE IF NOT EXISTS conclave_meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    topic TEXT NOT NULL,
    agenda JSONB DEFAULT '[]',
    participants JSONB DEFAULT '[]',
    status TEXT DEFAULT 'CONVENED' CHECK (status IN ('CONVENED', 'IN_SESSION', 'ADJOURNED', 'CANCELLED')),
    chair TEXT DEFAULT 'DAMON',
    facilitator TEXT DEFAULT 'CONVENER',
    current_speaker TEXT,
    turns_elapsed INT DEFAULT 0,
    floor_requests JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    adjourned_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'
);

-- Meeting transcript
CREATE TABLE IF NOT EXISTS conclave_transcript (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES conclave_meetings(id) ON DELETE CASCADE,
    turn_number INT NOT NULL,
    speaker TEXT NOT NULL,
    statement TEXT NOT NULL,
    signals JSONB DEFAULT '[]',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Meeting decisions
CREATE TABLE IF NOT EXISTS conclave_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES conclave_meetings(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    rationale TEXT,
    vote_results JSONB,
    action_items JSONB DEFAULT '[]',
    decided_by TEXT DEFAULT 'DAMON',
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- Advisory votes
CREATE TABLE IF NOT EXISTS conclave_votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES conclave_meetings(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options JSONB DEFAULT '[]',
    votes JSONB DEFAULT '[]',
    status TEXT DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

-- Consultations (private queries)
CREATE TABLE IF NOT EXISTS conclave_consultations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES conclave_meetings(id) ON DELETE CASCADE,
    requester TEXT NOT NULL,
    consulted_agent TEXT NOT NULL,
    question TEXT NOT NULL,
    response TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conclave_meetings_status ON conclave_meetings(status);
CREATE INDEX IF NOT EXISTS idx_conclave_transcript_meeting ON conclave_transcript(meeting_id);
CREATE INDEX IF NOT EXISTS idx_conclave_transcript_turn ON conclave_transcript(meeting_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_conclave_decisions_meeting ON conclave_decisions(meeting_id);

SELECT 'CONCLAVE migration complete' as status;
EOSQL

cat > /opt/leveredge/migrations/000003_conclave.down.sql << 'EOSQL'
DROP TABLE IF EXISTS conclave_consultations CASCADE;
DROP TABLE IF EXISTS conclave_votes CASCADE;
DROP TABLE IF EXISTS conclave_decisions CASCADE;
DROP TABLE IF EXISTS conclave_transcript CASCADE;
DROP TABLE IF EXISTS conclave_meetings CASCADE;
EOSQL
```

### 5.4 Migration 000004 - Views and Functions

```bash
cat > /opt/leveredge/migrations/000004_views_functions.up.sql << 'EOSQL'
-- Migration 000004: Views and Helper Functions

-- LLM Cost Summary View
CREATE OR REPLACE VIEW llm_cost_summary AS
SELECT 
    date_trunc('day', created_at) as day,
    agent_name,
    model,
    COUNT(*) as calls,
    SUM(input_tokens) as total_input,
    SUM(output_tokens) as total_output,
    SUM(estimated_cost_usd) as total_cost
FROM llm_usage
GROUP BY 1, 2, 3
ORDER BY 1 DESC, total_cost DESC;

-- Daily Cost Totals View
CREATE OR REPLACE VIEW llm_daily_costs AS
SELECT 
    date_trunc('day', created_at) as day,
    SUM(estimated_cost_usd) as total_cost,
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

-- Apply to tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN SELECT table_name FROM information_schema.columns 
             WHERE column_name = 'updated_at' AND table_schema = 'public'
    LOOP
        EXECUTE format('
            DROP TRIGGER IF EXISTS update_%I_updated_at ON %I;
            CREATE TRIGGER update_%I_updated_at
            BEFORE UPDATE ON %I
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
        ', t, t, t, t);
    END LOOP;
END $$;

SELECT 'Views and functions migration complete' as status;
EOSQL

cat > /opt/leveredge/migrations/000004_views_functions.down.sql << 'EOSQL'
DROP VIEW IF EXISTS aegis_expiring_credentials;
DROP VIEW IF EXISTS llm_daily_costs;
DROP VIEW IF EXISTS llm_cost_summary;
DROP VIEW IF EXISTS portfolio_summary;
DROP TABLE IF EXISTS agent_health;
DROP FUNCTION IF EXISTS update_updated_at CASCADE;
EOSQL
```

### 5.5 Migration 000005 - Backup and Monitoring Tables

```bash
cat > /opt/leveredge/migrations/000005_backup_monitoring.up.sql << 'EOSQL'
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

-- Indexes
CREATE INDEX IF NOT EXISTS idx_backup_history_target ON backup_history(target, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_health_component ON system_health(component, checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_events_severity ON system_events(severity, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_db_metrics_target ON db_metrics(target, captured_at DESC);

-- Cleanup old entries (keep 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_monitoring_data()
RETURNS void AS $$
BEGIN
    DELETE FROM system_health WHERE checked_at < NOW() - INTERVAL '90 days';
    DELETE FROM system_events WHERE created_at < NOW() - INTERVAL '90 days';
    DELETE FROM db_metrics WHERE captured_at < NOW() - INTERVAL '90 days';
    DELETE FROM aegis_health_checks WHERE checked_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

SELECT 'Backup and monitoring migration complete' as status;
EOSQL

cat > /opt/leveredge/migrations/000005_backup_monitoring.down.sql << 'EOSQL'
DROP FUNCTION IF EXISTS cleanup_old_monitoring_data;
DROP TABLE IF EXISTS db_metrics CASCADE;
DROP TABLE IF EXISTS system_events CASCADE;
DROP TABLE IF EXISTS system_health CASCADE;
DROP TABLE IF EXISTS backup_history CASCADE;
EOSQL
```

### 5.6 Check Audit for Any Additional Tables

After running the audit in Section 3, create additional migrations for any other tables found in DEV but not listed above. Use this template:

```bash
# For each additional table found:
cat > /opt/leveredge/migrations/000006_[table_name].up.sql << 'EOSQL'
-- Migration 000006: [Table Name]
-- Export from DEV: docker exec supabase-db-dev pg_dump -U postgres -d postgres --schema-only -t [table_name]

[paste DDL here]
EOSQL

cat > /opt/leveredge/migrations/000006_[table_name].down.sql << 'EOSQL'
DROP TABLE IF EXISTS [table_name] CASCADE;
EOSQL
```

---

## SECTION 6: APPLY MIGRATIONS

### 6.1 Mark DEV as Current

DEV already has most tables, so mark all migrations as applied:

```bash
# Check what's there
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54323/postgres?sslmode=disable" \
    version

# Force to latest version (tables exist)
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54323/postgres?sslmode=disable" \
    force 5
```

### 6.2 Apply to PROD

```bash
# Check current state
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    version

# Apply all migrations
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    up

# Verify
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    version
```

### 6.3 Verify Schemas Match

```bash
# Regenerate table lists
docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /tmp/prod_after.txt

docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT table_name FROM information_schema.tables 
     WHERE table_schema = 'public' AND table_type = 'BASE TABLE' 
     ORDER BY table_name;" | tr -d ' ' | grep -v '^$' | sort > /tmp/dev_after.txt

# Compare
diff /tmp/prod_after.txt /tmp/dev_after.txt

# Should show no differences (or only expected ones)
```

---

## SECTION 7: CREATE HELPER SCRIPTS

### 7.1 Migration Wrapper Scripts

```bash
# DEV wrapper
cat > /opt/leveredge/shared/scripts/migrate-dev.sh << 'EOF'
#!/bin/bash
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54323/postgres?sslmode=disable" \
    "$@"
EOF

# PROD wrapper
cat > /opt/leveredge/shared/scripts/migrate-prod.sh << 'EOF'
#!/bin/bash
migrate -path /opt/leveredge/migrations \
    -database "postgres://postgres:postgres@localhost:54322/postgres?sslmode=disable" \
    "$@"
EOF

chmod +x /opt/leveredge/shared/scripts/migrate-*.sh

# Symlinks
sudo ln -sf /opt/leveredge/shared/scripts/migrate-dev.sh /usr/local/bin/migrate-dev
sudo ln -sf /opt/leveredge/shared/scripts/migrate-prod.sh /usr/local/bin/migrate-prod
```

### 7.2 New Migration Script

```bash
cat > /opt/leveredge/shared/scripts/new-migration.sh << 'EOF'
#!/bin/bash
set -e

NAME=$1
if [ -z "$NAME" ]; then
    echo "Usage: new-migration <migration_name>"
    echo "Example: new-migration add_user_preferences"
    exit 1
fi

DIR="/opt/leveredge/migrations"
LAST=$(ls -1 "$DIR"/*.up.sql 2>/dev/null | sort -V | tail -1 | grep -oP '\d{6}' | head -1 || echo "0")
NEXT=$(printf "%06d" $((10#$LAST + 1)))

UP="$DIR/${NEXT}_${NAME}.up.sql"
DOWN="$DIR/${NEXT}_${NAME}.down.sql"

cat > "$UP" << EOSQL
-- Migration $NEXT: $NAME
-- Created: $(date '+%Y-%m-%d %H:%M:%S')

-- Add your SQL here

SELECT 'Migration $NEXT complete' as status;
EOSQL

cat > "$DOWN" << EOSQL
-- Rollback $NEXT: $NAME

-- Add rollback SQL here

EOSQL

echo "Created:"
echo "  $UP"
echo "  $DOWN"
echo ""
echo "Workflow:"
echo "  1. Edit the migration files"
echo "  2. migrate-dev up"
echo "  3. Test in DEV"
echo "  4. migrate-prod up"
echo "  5. git add migrations/ && git commit"
EOF

chmod +x /opt/leveredge/shared/scripts/new-migration.sh
sudo ln -sf /opt/leveredge/shared/scripts/new-migration.sh /usr/local/bin/new-migration
```

### 7.3 Backup Script (Enhanced)

```bash
cat > /opt/leveredge/shared/scripts/backup-database.sh << 'EOF'
#!/bin/bash
set -e

TARGET=${1:-prod}
TYPE=${2:-full}
BACKUP_DIR="/opt/leveredge/backups/database"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

if [ "$TARGET" == "prod" ]; then
    CONTAINER="supabase-db-prod"
    PORT="54322"
elif [ "$TARGET" == "dev" ]; then
    CONTAINER="supabase-db-dev"
    PORT="54323"
else
    echo "Usage: backup-database.sh [prod|dev] [full|schema]"
    exit 1
fi

FILENAME="${TARGET}_${TYPE}_${TIMESTAMP}.sql"
FILEPATH="$BACKUP_DIR/$FILENAME"

echo "Backing up $TARGET ($TYPE) to $FILEPATH..."

if [ "$TYPE" == "full" ]; then
    docker exec $CONTAINER pg_dump -U postgres -d postgres --no-owner --no-acl > "$FILEPATH"
elif [ "$TYPE" == "schema" ]; then
    docker exec $CONTAINER pg_dump -U postgres -d postgres --schema-only --no-owner --no-acl > "$FILEPATH"
fi

# Compress
gzip "$FILEPATH"
FILEPATH="${FILEPATH}.gz"

# Get size
SIZE=$(du -h "$FILEPATH" | cut -f1)

echo "Backup complete: $FILEPATH ($SIZE)"

# Log to database (if prod backup)
if [ "$TARGET" == "prod" ]; then
    docker exec supabase-db-prod psql -U postgres -d postgres -c "
    INSERT INTO backup_history (backup_type, target, file_path, file_size_bytes, started_at, completed_at, status)
    VALUES ('$TYPE', '$TARGET', '$FILEPATH', $(stat -f%z "$FILEPATH" 2>/dev/null || stat -c%s "$FILEPATH"), NOW() - INTERVAL '1 minute', NOW(), 'completed');"
fi

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "Done."
EOF

chmod +x /opt/leveredge/shared/scripts/backup-database.sh
sudo ln -sf /opt/leveredge/shared/scripts/backup-database.sh /usr/local/bin/backup-database
```

### 7.4 Database Health Check Script

```bash
cat > /opt/leveredge/shared/scripts/db-health.sh << 'EOF'
#!/bin/bash

echo "=== Database Health Check ==="
echo ""

for TARGET in prod dev; do
    if [ "$TARGET" == "prod" ]; then
        CONTAINER="supabase-db-prod"
    else
        CONTAINER="supabase-db-dev"
    fi
    
    echo "--- $TARGET ---"
    
    # Check container running
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        echo "Container: ✅ Running"
    else
        echo "Container: ❌ Not running"
        continue
    fi
    
    # Check connection
    if docker exec $CONTAINER pg_isready -U postgres > /dev/null 2>&1; then
        echo "Connection: ✅ Ready"
    else
        echo "Connection: ❌ Not ready"
        continue
    fi
    
    # Get stats
    TABLES=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')
    
    SIZE=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT pg_size_pretty(pg_database_size('postgres'));" | tr -d ' ')
    
    CONNECTIONS=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT COUNT(*) FROM pg_stat_activity WHERE datname = 'postgres';" | tr -d ' ')
    
    MIGRATION=$(docker exec $CONTAINER psql -U postgres -d postgres -t -c \
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations;" 2>/dev/null | tr -d ' ' || echo "N/A")
    
    echo "Tables: $TABLES"
    echo "Size: $SIZE"
    echo "Connections: $CONNECTIONS"
    echo "Migration Version: $MIGRATION"
    echo ""
done

# Compare schemas
echo "--- Schema Comparison ---"
PROD_TABLES=$(docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')
DEV_TABLES=$(docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';" | tr -d ' ')

if [ "$PROD_TABLES" == "$DEV_TABLES" ]; then
    echo "Table count: ✅ Match ($PROD_TABLES tables)"
else
    echo "Table count: ⚠️ Mismatch (PROD: $PROD_TABLES, DEV: $DEV_TABLES)"
fi

PROD_VER=$(docker exec supabase-db-prod psql -U postgres -d postgres -t -c \
    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations;" 2>/dev/null | tr -d ' ' || echo "0")
DEV_VER=$(docker exec supabase-db-dev psql -U postgres -d postgres -t -c \
    "SELECT COALESCE(MAX(version), 0) FROM schema_migrations;" 2>/dev/null | tr -d ' ' || echo "0")

if [ "$PROD_VER" == "$DEV_VER" ]; then
    echo "Migration version: ✅ Match (v$PROD_VER)"
else
    echo "Migration version: ⚠️ Mismatch (PROD: v$PROD_VER, DEV: v$DEV_VER)"
fi
EOF

chmod +x /opt/leveredge/shared/scripts/db-health.sh
sudo ln -sf /opt/leveredge/shared/scripts/db-health.sh /usr/local/bin/db-health
```

---

## SECTION 8: AUTOMATED BACKUP VERIFICATION

### 8.1 Create Systemd Timer for Daily Backups

```bash
cat > /opt/leveredge/shared/systemd/db-backup.service << 'EOF'
[Unit]
Description=Database Backup (PROD)

[Service]
Type=oneshot
User=root
ExecStart=/opt/leveredge/shared/scripts/backup-database.sh prod full
StandardOutput=append:/opt/leveredge/logs/db-backup.log
StandardError=append:/opt/leveredge/logs/db-backup.log
EOF

cat > /opt/leveredge/shared/systemd/db-backup.timer << 'EOF'
[Unit]
Description=Daily database backup at 2 AM

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

### 8.2 Create Health Check Timer

```bash
cat > /opt/leveredge/shared/systemd/db-health.service << 'EOF'
[Unit]
Description=Database Health Check

[Service]
Type=oneshot
User=root
ExecStart=/opt/leveredge/shared/scripts/db-health.sh
StandardOutput=append:/opt/leveredge/logs/db-health.log
StandardError=append:/opt/leveredge/logs/db-health.log
EOF

cat > /opt/leveredge/shared/systemd/db-health.timer << 'EOF'
[Unit]
Description=Hourly database health check

[Timer]
OnCalendar=*-*-* *:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF
```

### 8.3 Install Timers

```bash
sudo cp /opt/leveredge/shared/systemd/db-*.service /etc/systemd/system/
sudo cp /opt/leveredge/shared/systemd/db-*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable db-backup.timer db-health.timer
sudo systemctl start db-backup.timer db-health.timer

# Verify
sudo systemctl list-timers | grep db-
```

---

## SECTION 9: DOCUMENTATION

### 9.1 Create Complete Database Documentation

```bash
cat > /opt/leveredge/migrations/README.md << 'EOF'
# LeverEdge Database Management

## Quick Reference

```bash
# Check database health
db-health

# Check migration status
migrate-dev version
migrate-prod version

# Create new migration
new-migration add_something

# Apply migrations
migrate-dev up
migrate-prod up

# Rollback
migrate-dev down 1
migrate-prod down 1

# Backup
backup-database prod full
backup-database prod schema
backup-database dev full
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Supabase Stack                        │
├──────────────────────────┬──────────────────────────────┤
│         PROD             │            DEV               │
│   supabase-db-prod       │     supabase-db-dev         │
│   Port: 54322            │     Port: 54323             │
│   Real data              │     Test data               │
├──────────────────────────┴──────────────────────────────┤
│                   Migration System                       │
│              golang-migrate + SQL files                  │
│              /opt/leveredge/migrations/                  │
└─────────────────────────────────────────────────────────┘
```

## Migration Workflow

1. **Create migration:**
   ```bash
   new-migration add_new_feature
   ```

2. **Edit the SQL files:**
   - `000XXX_add_new_feature.up.sql` - Changes to apply
   - `000XXX_add_new_feature.down.sql` - Rollback

3. **Test in DEV:**
   ```bash
   migrate-dev up
   # Test your changes
   ```

4. **Apply to PROD:**
   ```bash
   backup-database prod full  # Always backup first!
   migrate-prod up
   ```

5. **Commit:**
   ```bash
   git add migrations/
   git commit -m "Migration: add new feature"
   ```

## Rules

- **Never edit applied migrations** - Create a new one instead
- **Always write down migrations** - Even if just a comment
- **Test in DEV first** - Always
- **Backup before PROD changes** - Always
- **One migration = one change** - Keep them focused

## Current Tables

### Core
- `aria_knowledge` - ARIA knowledge storage
- `aria_wins` - Portfolio wins
- `aria_portfolio_summary` - Portfolio aggregates
- `llm_usage` - LLM cost tracking

### AEGIS V2
- `aegis_credentials_v2` - Encrypted credentials
- `aegis_credential_versions` - Version history
- `aegis_audit_log` - Access audit
- `aegis_rotation_history` - Rotation tracking
- `aegis_health_checks` - Health check results
- `aegis_providers` - Provider registry

### CONCLAVE
- `conclave_meetings` - Council meetings
- `conclave_transcript` - Meeting transcripts
- `conclave_decisions` - Recorded decisions
- `conclave_votes` - Advisory votes
- `conclave_consultations` - Private queries

### Monitoring
- `backup_history` - Backup tracking
- `system_health` - Component health
- `system_events` - Event log
- `db_metrics` - Database metrics
- `agent_health` - Agent status

### System
- `schema_migrations` - Migration tracking

## Backups

- **Location:** `/opt/leveredge/backups/database/`
- **Schedule:** Daily at 2 AM (full PROD backup)
- **Retention:** 30 days
- **Manual:** `backup-database prod full`

## Troubleshooting

**Dirty migration state:**
```bash
migrate-dev force <version>
```

**Compare schemas:**
```bash
db-health
```

**Check specific table:**
```bash
docker exec supabase-db-prod psql -U postgres -d postgres -c "\d+ table_name"
```
EOF
```

---

## SECTION 10: FINAL VERIFICATION

### 10.1 Run Full Health Check

```bash
db-health
```

### 10.2 Verify All Migrations Applied

```bash
migrate-dev version
migrate-prod version
# Both should show same version
```

### 10.3 Test Backup and Restore

```bash
# Create backup
backup-database prod full

# Verify backup exists
ls -la /opt/leveredge/backups/database/

# Test restore to temp database (optional but recommended)
# docker exec supabase-db-dev psql -U postgres -c "CREATE DATABASE restore_test;"
# gunzip -c /opt/leveredge/backups/database/prod_full_*.sql.gz | docker exec -i supabase-db-dev psql -U postgres -d restore_test
# docker exec supabase-db-dev psql -U postgres -c "DROP DATABASE restore_test;"
```

### 10.4 Verify Timers Running

```bash
sudo systemctl list-timers | grep -E "(db-backup|db-health)"
```

---

## COMPLETION CHECKLIST

- [ ] Full PROD backup created before changes
- [ ] golang-migrate installed
- [ ] Complete database audit performed
- [ ] All differences documented
- [ ] Migration 000001 (baseline) created
- [ ] Migration 000002 (AEGIS V2) created
- [ ] Migration 000003 (CONCLAVE) created
- [ ] Migration 000004 (views/functions) created
- [ ] Migration 000005 (backup/monitoring) created
- [ ] Any additional migrations created
- [ ] DEV marked at correct version
- [ ] PROD migrations applied
- [ ] Schemas verified to match
- [ ] Helper scripts created and linked
- [ ] Backup timer configured
- [ ] Health check timer configured
- [ ] Documentation complete
- [ ] Git committed

---

## GIT COMMIT

```bash
cd /opt/leveredge
git add migrations/
git add shared/scripts/migrate-*.sh
git add shared/scripts/new-migration.sh
git add shared/scripts/backup-database.sh
git add shared/scripts/db-health.sh
git add shared/systemd/db-*.service
git add shared/systemd/db-*.timer
git commit -m "Complete Supabase overhaul with migration system

- Install golang-migrate for versioned migrations
- Create baseline + 5 migrations syncing DEV → PROD
- AEGIS V2 tables, CONCLAVE tables, monitoring tables
- Views for cost tracking, credentials, portfolio
- Helper scripts: migrate-dev, migrate-prod, new-migration
- Backup script with compression and rotation
- Health check script comparing DEV/PROD
- Systemd timers for daily backup and hourly health
- Complete documentation in migrations/README.md

DEV and PROD schemas now identical and versioned.
No more loose ends."
```

---

## NOTIFICATION

```bash
curl -X POST http://localhost:8014/notify \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "telegram",
    "message": "🗄️ SUPABASE COMPLETE - NO LOOSE ENDS\n\n✅ golang-migrate installed\n✅ 5 migrations created & applied\n✅ DEV/PROD schemas synced\n✅ Automated daily backups\n✅ Hourly health checks\n✅ Helper scripts installed\n\nCommands: migrate-dev, migrate-prod, new-migration, backup-database, db-health",
    "priority": "high"
  }'
```

---

*End of GSD*
*No more drift. No more loose ends. Properly versioned. Fully documented.*
