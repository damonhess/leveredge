-- =====================================================
-- MEGA GSD JAN 18: Agent Pages Database Schema
-- Target: DEV Supabase
-- =====================================================

-- Agent registry in database (mirrors YAML but queryable)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    tagline TEXT,
    description TEXT,
    version TEXT DEFAULT '1.0',
    port INTEGER,
    category TEXT CHECK (category IN ('infrastructure', 'business', 'creative', 'personal', 'security')),
    domain TEXT CHECK (domain IN ('THE_KEEP', 'PANTHEON', 'SENTINELS', 'CHANCERY', 'ALCHEMY', 'THE_SHIRE', 'ARIA_SANCTUM', 'GAIA')),
    icon TEXT,
    color TEXT,
    is_active BOOLEAN DEFAULT true,
    is_llm_powered BOOLEAN DEFAULT false,
    health_endpoint TEXT DEFAULT '/health',
    capabilities JSONB DEFAULT '[]',
    actions JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent health/status tracking
CREATE TABLE IF NOT EXISTS agent_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    status TEXT CHECK (status IN ('online', 'offline', 'degraded', 'busy')),
    latency_ms INTEGER,
    last_check TIMESTAMPTZ DEFAULT NOW(),
    error_message TEXT,
    metadata JSONB DEFAULT '{}'
);

-- Agent activity log
CREATE TABLE IF NOT EXISTS agent_activity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    status TEXT CHECK (status IN ('started', 'completed', 'failed')),
    input JSONB,
    output JSONB,
    error TEXT,
    duration_ms INTEGER,
    cost DECIMAL(10,6),
    user_id UUID REFERENCES auth.users(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent conversations (chat with specific agent)
CREATE TABLE IF NOT EXISTS agent_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES agent_conversations(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost DECIMAL(10,6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- AEGIS (Credentials) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS aegis_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    display_name TEXT,
    credential_type TEXT CHECK (credential_type IN ('api_key', 'oauth_token', 'password', 'certificate', 'ssh_key', 'database', 'webhook')),
    provider TEXT,
    project TEXT,
    environment TEXT CHECK (environment IN ('dev', 'prod', 'both')),
    n8n_credential_id TEXT,
    vault_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated TIMESTAMPTZ,
    last_used TIMESTAMPTZ,
    last_tested TIMESTAMPTZ,
    test_status TEXT CHECK (test_status IN ('valid', 'invalid', 'untested', 'expired')),
    used_by_agents TEXT[],
    rotation_policy TEXT CHECK (rotation_policy IN ('manual', 'monthly', 'quarterly', 'yearly', 'never')),
    notes TEXT,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials(id) ON DELETE SET NULL,
    action TEXT CHECK (action IN ('created', 'read', 'updated', 'rotated', 'tested', 'revoked', 'deleted')),
    actor TEXT,
    ip_address TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aegis_personal_vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    username TEXT,
    encrypted_password TEXT,
    url TEXT,
    notes TEXT,
    totp_secret TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- CHRONOS (Backups) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS chronos_backups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_id TEXT UNIQUE NOT NULL,
    backup_type TEXT CHECK (backup_type IN ('full', 'incremental', 'manual', 'pre_deploy')),
    status TEXT CHECK (status IN ('running', 'completed', 'failed', 'verified', 'corrupted')),
    components JSONB,
    size_bytes BIGINT,
    duration_ms INTEGER,
    storage_path TEXT,
    tag TEXT,
    triggered_by TEXT,
    verified_at TIMESTAMPTZ,
    verification_status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS chronos_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    cron_expression TEXT NOT NULL,
    backup_type TEXT,
    components JSONB,
    retention_days INTEGER DEFAULT 7,
    is_active BOOLEAN DEFAULT true,
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- HADES (Rollback) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS hades_deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    component TEXT NOT NULL,
    version TEXT NOT NULL,
    previous_version TEXT,
    git_commit TEXT,
    deployed_by TEXT,
    rollback_available BOOLEAN DEFAULT true,
    rollback_backup_id TEXT REFERENCES chronos_backups(backup_id),
    status TEXT CHECK (status IN ('active', 'rolled_back', 'superseded')),
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    rollback_window_ends TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS hades_rollbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deployment_id UUID REFERENCES hades_deployments(id),
    from_version TEXT,
    to_version TEXT,
    reason TEXT,
    initiated_by TEXT,
    status TEXT CHECK (status IN ('pending', 'in_progress', 'completed', 'failed')),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- =====================================================
-- PANOPTES (Integrity) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS panoptes_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_type TEXT CHECK (scan_type IN ('full', 'quick', 'ports', 'agents', 'registry')),
    status TEXT CHECK (status IN ('running', 'completed', 'failed')),
    health_score DECIMAL(5,2),
    total_checks INTEGER,
    passed_checks INTEGER,
    critical_issues INTEGER DEFAULT 0,
    high_issues INTEGER DEFAULT 0,
    medium_issues INTEGER DEFAULT 0,
    low_issues INTEGER DEFAULT 0,
    duration_ms INTEGER,
    triggered_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS panoptes_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES panoptes_scans(id) ON DELETE CASCADE,
    severity TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    category TEXT,
    description TEXT,
    affected_components TEXT[],
    suggested_fix TEXT,
    auto_healable BOOLEAN DEFAULT false,
    status TEXT CHECK (status IN ('open', 'healing', 'healed', 'dismissed', 'manual_required')),
    healed_at TIMESTAMPTZ,
    healed_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- ASCLEPIUS (Healing) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS asclepius_healing_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES panoptes_scans(id),
    status TEXT CHECK (status IN ('pending', 'approved', 'executing', 'completed', 'failed', 'rejected')),
    actions JSONB,
    total_actions INTEGER,
    completed_actions INTEGER DEFAULT 0,
    failed_actions INTEGER DEFAULT 0,
    requires_approval BOOLEAN DEFAULT false,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS asclepius_healing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES asclepius_healing_plans(id),
    issue_id UUID REFERENCES panoptes_issues(id),
    action_type TEXT,
    target TEXT,
    status TEXT CHECK (status IN ('pending', 'executing', 'success', 'failed')),
    error_message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS asclepius_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    issue_pattern TEXT,
    action_type TEXT,
    action_template JSONB,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_duration_ms INTEGER,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- HERMES (Notifications) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS hermes_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    channel_type TEXT CHECK (channel_type IN ('telegram', 'email', 'webhook', 'event_bus', 'slack')),
    config JSONB,
    is_active BOOLEAN DEFAULT true,
    last_used TIMESTAMPTZ,
    last_status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hermes_notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    trigger_event TEXT,
    trigger_condition JSONB,
    channels TEXT[],
    priority TEXT CHECK (priority IN ('low', 'normal', 'high', 'critical')),
    message_template TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hermes_message_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id UUID REFERENCES hermes_channels(id),
    rule_id UUID REFERENCES hermes_notification_rules(id),
    message TEXT,
    priority TEXT,
    status TEXT CHECK (status IN ('pending', 'sent', 'delivered', 'failed')),
    error_message TEXT,
    external_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ
);

-- =====================================================
-- ARGUS (Monitoring) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS argus_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type TEXT,
    component TEXT,
    value DECIMAL(10,4),
    unit TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_argus_metrics_time ON argus_metrics(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_argus_metrics_type ON argus_metrics(metric_type, component);

CREATE TABLE IF NOT EXISTS argus_cost_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id),
    agent_name TEXT,
    action TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost DECIMAL(10,6),
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_argus_costs_time ON argus_cost_tracking(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_argus_costs_agent ON argus_cost_tracking(agent_name);

CREATE TABLE IF NOT EXISTS argus_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type TEXT,
    metric_type TEXT,
    component TEXT,
    condition TEXT,
    threshold_value DECIMAL(10,4),
    current_value DECIMAL(10,4),
    status TEXT CHECK (status IN ('active', 'acknowledged', 'resolved')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ
);

-- =====================================================
-- ALOY (Audit & Anomaly) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS aloy_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT,
    actor TEXT,
    agent_id UUID REFERENCES agents(id),
    resource TEXT,
    action TEXT,
    details JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aloy_audit_time ON aloy_audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aloy_audit_actor ON aloy_audit_events(actor);

CREATE TABLE IF NOT EXISTS aloy_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_type TEXT,
    severity TEXT CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    expected_value TEXT,
    actual_value TEXT,
    affected_component TEXT,
    status TEXT CHECK (status IN ('new', 'investigating', 'dismissed', 'confirmed', 'blocked')),
    investigated_by TEXT,
    resolution TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS aloy_compliance_checks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    check_name TEXT,
    category TEXT,
    status TEXT CHECK (status IN ('pass', 'fail', 'warning', 'not_applicable')),
    details JSONB,
    checked_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- ATLAS (Orchestration) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS atlas_chain_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chain_name TEXT NOT NULL,
    status TEXT CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    input JSONB,
    output JSONB,
    current_step INTEGER DEFAULT 0,
    total_steps INTEGER,
    step_results JSONB DEFAULT '[]',
    total_cost DECIMAL(10,6) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    error_message TEXT,
    triggered_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS atlas_batch_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id TEXT UNIQUE NOT NULL,
    status TEXT CHECK (status IN ('running', 'completed', 'partial', 'failed')),
    total_tasks INTEGER,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    concurrency INTEGER DEFAULT 5,
    total_cost DECIMAL(10,6) DEFAULT 0,
    callback_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- =====================================================
-- SCHOLAR (Research) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS scholar_research_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    title TEXT NOT NULL,
    research_type TEXT,
    query TEXT,
    status TEXT CHECK (status IN ('queued', 'researching', 'completed', 'failed')),
    result JSONB,
    sources_count INTEGER,
    confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
    cost DECIMAL(10,6),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- =====================================================
-- CHIRON (Coaching) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS chiron_commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE,
    status TEXT CHECK (status IN ('active', 'completed', 'missed', 'deferred')),
    priority TEXT CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS chiron_weekly_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    week_start DATE,
    wins JSONB,
    losses JSONB,
    lessons JSONB,
    next_week_goals JSONB,
    analysis JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chiron_sprint_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),
    week_start DATE,
    goals JSONB,
    daily_priorities JSONB,
    time_blocks JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- VARYS (Mission Guardian) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS varys_mission_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_type TEXT UNIQUE CHECK (document_type IN ('MISSION', 'LAUNCH_DATE', 'REVENUE_GOAL', 'BOUNDARIES', 'PORTFOLIO_TARGET')),
    content TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS varys_drift_flags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_hash TEXT,
    commit_message TEXT,
    flag_reason TEXT,
    risk_level TEXT CHECK (risk_level IN ('low', 'medium', 'high')),
    recommendation TEXT,
    status TEXT CHECK (status IN ('new', 'accepted', 'dismissed', 'discussed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS varys_daily_briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brief_date DATE UNIQUE,
    days_to_launch INTEGER,
    focus TEXT,
    tasks JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_agent_health_agent ON agent_health(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_activity_agent ON agent_activity(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_activity_time ON agent_activity(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aegis_creds_project ON aegis_credentials(project);
CREATE INDEX IF NOT EXISTS idx_aegis_creds_provider ON aegis_credentials(provider);
CREATE INDEX IF NOT EXISTS idx_aegis_creds_expires ON aegis_credentials(expires_at);
CREATE INDEX IF NOT EXISTS idx_chronos_backups_time ON chronos_backups(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_panoptes_issues_severity ON panoptes_issues(severity);
CREATE INDEX IF NOT EXISTS idx_panoptes_issues_status ON panoptes_issues(status);

-- =====================================================
-- ROW LEVEL SECURITY
-- =====================================================

ALTER TABLE agent_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE aegis_personal_vault ENABLE ROW LEVEL SECURITY;
ALTER TABLE chiron_commitments ENABLE ROW LEVEL SECURITY;
ALTER TABLE chiron_weekly_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE chiron_sprint_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE scholar_research_projects ENABLE ROW LEVEL SECURITY;

-- Policies for user-specific data
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can access own conversations') THEN
        CREATE POLICY "Users can access own conversations" ON agent_conversations
            FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can access own messages') THEN
        CREATE POLICY "Users can access own messages" ON agent_messages
            FOR ALL USING (conversation_id IN (
                SELECT id FROM agent_conversations WHERE user_id = auth.uid()
            ));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can access own vault') THEN
        CREATE POLICY "Users can access own vault" ON aegis_personal_vault
            FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can access own commitments') THEN
        CREATE POLICY "Users can access own commitments" ON chiron_commitments
            FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can access own reviews') THEN
        CREATE POLICY "Users can access own reviews" ON chiron_weekly_reviews
            FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can access own sprints') THEN
        CREATE POLICY "Users can access own sprints" ON chiron_sprint_plans
            FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Users can access own research') THEN
        CREATE POLICY "Users can access own research" ON scholar_research_projects
            FOR ALL USING (auth.uid() = user_id);
    END IF;
END $$;

-- Migration complete marker
DO $$
BEGIN
    RAISE NOTICE 'Agent Pages Schema Migration completed successfully';
END $$;
