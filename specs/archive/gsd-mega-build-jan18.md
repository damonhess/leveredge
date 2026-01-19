# MEGA GSD: Infrastructure Cleanup + Agent Pages Build

**Priority:** HIGH - Foundation for Launch
**Estimated Time:** 8-12 hours (split across sessions)
**Created:** 2026-01-18
**Days to Launch:** 42

---

## OVERVIEW

This mega build covers:
1. Infrastructure loose ends (password, PANOPTES, technical debt)
2. Database schema for all agent pages
3. DEV environment for Command Center
4. Agent page UI builds (Bolt.new prompts)
5. Documentation and portfolio updates

---

# PHASE 1: INFRASTRUCTURE LOOSE ENDS (2 hours)

---

## 1.1 ARIA Password Reset (5 min)

```bash
cd /home/damon/stack
docker exec -it supabase-db psql -U postgres -d postgres -c "
UPDATE auth.users 
SET encrypted_password = crypt('YOUR_NEW_PASSWORD', gen_salt('bf'))
WHERE email = 'damonhess@hotmail.com';
"
```

## 1.2 Fix PANOPTES Medium Issues (30 min)

### Get Current Issues
```bash
curl http://localhost:8023/status | python3 -m json.tool
curl http://localhost:8023/issues | python3 -c "
import json, sys
data = json.load(sys.stdin)
for issue in data.get('issues', []):
    print(f\"{issue.get('severity')}: {issue.get('description')}\")
"
```

### Update Registry URLs to localhost
Edit `/opt/leveredge/config/agent-registry.yaml` - change all systemd agents from:
```yaml
url: http://agentname:PORT
```
To:
```yaml
url: http://localhost:PORT
```

Agents needing localhost URLs (systemd-based):
- panoptes (8023), asclepius (8024), hermes (8014), chronos (8010)
- hades (8008), aegis (8012), argus (8016), aloy (8015)
- athena (8013), atlas (8007), sentinel (8019), event-bus (8099)

### Rescan
```bash
sudo systemctl restart leveredge-panoptes
sleep 5
curl -X POST http://localhost:8023/scan | python3 -m json.tool | grep health_score
```

## 1.3 Technical Debt Cleanup (30 min)

### Storage Cleanup
```bash
# Clean old backups (keep last 7 days)
find /opt/leveredge/shared/backups -type f -mtime +7 -delete
find /opt/leveredge/archive -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null

# Docker cleanup
cd /home/damon/stack
docker system prune -f
```

### Create Cron Jobs
```bash
crontab -e
```

Add:
```cron
# PANOPTES daily scan at 6 AM
0 6 * * * curl -X POST http://localhost:8023/scan > /dev/null 2>&1

# ASCLEPIUS auto-heal at 6:30 AM
30 6 * * * curl -X POST http://localhost:8024/emergency/auto > /dev/null 2>&1

# Weekly backup cleanup (Sunday 3 AM)
0 3 * * 0 find /opt/leveredge/shared/backups -type f -mtime +7 -delete
```

## 1.4 Check Disk Space
```bash
df -h /opt/leveredge
du -sh /opt/leveredge/shared/backups/*
```

---

# PHASE 2: DATABASE SCHEMA FOR AGENT PAGES (1 hour)

---

## 2.1 Core Agent Tables

Run in DEV Supabase SQL Editor:

```sql
-- =====================================================
-- AGENT INFRASTRUCTURE TABLES
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
    provider TEXT, -- OpenAI, Google, AWS, etc.
    project TEXT, -- LeverEdge, Personal, Client-X
    environment TEXT CHECK (environment IN ('dev', 'prod', 'both')),
    -- Never store actual secrets here - reference n8n credential ID or vault
    n8n_credential_id TEXT,
    vault_path TEXT,
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    last_rotated TIMESTAMPTZ,
    last_used TIMESTAMPTZ,
    last_tested TIMESTAMPTZ,
    test_status TEXT CHECK (test_status IN ('valid', 'invalid', 'untested', 'expired')),
    used_by_agents TEXT[], -- Which agents use this credential
    rotation_policy TEXT CHECK (rotation_policy IN ('manual', 'monthly', 'quarterly', 'yearly', 'never')),
    notes TEXT,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS aegis_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    credential_id UUID REFERENCES aegis_credentials(id) ON DELETE SET NULL,
    action TEXT CHECK (action IN ('created', 'read', 'updated', 'rotated', 'tested', 'revoked', 'deleted')),
    actor TEXT, -- Agent name or user
    ip_address TEXT,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Personal vault (for password manager features)
CREATE TABLE IF NOT EXISTS aegis_personal_vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT, -- bank, email, subscription, social, etc.
    username TEXT,
    -- Encrypted password stored here (or vault reference)
    encrypted_password TEXT,
    url TEXT,
    notes TEXT,
    totp_secret TEXT, -- 2FA backup
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- CHRONOS (Backups) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS chronos_backups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backup_id TEXT UNIQUE NOT NULL, -- e.g., "backup-20260118-060000"
    backup_type TEXT CHECK (backup_type IN ('full', 'incremental', 'manual', 'pre_deploy')),
    status TEXT CHECK (status IN ('running', 'completed', 'failed', 'verified', 'corrupted')),
    components JSONB, -- {supabase: true, n8n: true, agents: true}
    size_bytes BIGINT,
    duration_ms INTEGER,
    storage_path TEXT,
    tag TEXT, -- e.g., "pre-deploy-aria-v3"
    triggered_by TEXT, -- 'scheduled', 'manual', 'pre_deploy'
    verified_at TIMESTAMPTZ,
    verification_status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ -- When to auto-delete
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
    component TEXT NOT NULL, -- 'aria-frontend', 'n8n-workflows', 'agent-config'
    version TEXT NOT NULL,
    previous_version TEXT,
    git_commit TEXT,
    deployed_by TEXT,
    rollback_available BOOLEAN DEFAULT true,
    rollback_backup_id TEXT REFERENCES chronos_backups(backup_id),
    status TEXT CHECK (status IN ('active', 'rolled_back', 'superseded')),
    deployed_at TIMESTAMPTZ DEFAULT NOW(),
    rollback_window_ends TIMESTAMPTZ -- After this, rollback may be risky
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
    category TEXT, -- 'port_conflict', 'agent_offline', 'missing_service', etc.
    description TEXT,
    affected_components TEXT[],
    suggested_fix TEXT,
    auto_healable BOOLEAN DEFAULT false,
    status TEXT CHECK (status IN ('open', 'healing', 'healed', 'dismissed', 'manual_required')),
    healed_at TIMESTAMPTZ,
    healed_by TEXT, -- 'ASCLEPIUS' or 'manual'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- ASCLEPIUS (Healing) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS asclepius_healing_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES panoptes_scans(id),
    status TEXT CHECK (status IN ('pending', 'approved', 'executing', 'completed', 'failed', 'rejected')),
    actions JSONB, -- [{action: 'restart_service', target: 'chronos', risk: 'low'}]
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
    action_type TEXT, -- 'restart_service', 'port_reassign', 'disk_cleanup', 'config_fix'
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
    issue_pattern TEXT, -- Regex or condition to match
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
    config JSONB, -- {chat_id: '...', webhook_url: '...'}
    is_active BOOLEAN DEFAULT true,
    last_used TIMESTAMPTZ,
    last_status TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hermes_notification_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    trigger_event TEXT, -- 'panoptes.critical', 'backup.failed', etc.
    trigger_condition JSONB, -- Additional conditions
    channels TEXT[], -- Channel names to notify
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
    external_id TEXT, -- Telegram message_id, etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    delivered_at TIMESTAMPTZ
);

-- =====================================================
-- ARGUS (Monitoring) Tables
-- =====================================================

CREATE TABLE IF NOT EXISTS argus_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    metric_type TEXT, -- 'cpu', 'memory', 'disk', 'network', 'latency'
    component TEXT, -- 'system', agent name, etc.
    value DECIMAL(10,4),
    unit TEXT, -- 'percent', 'bytes', 'ms'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Partition by time for performance
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
    alert_type TEXT, -- 'threshold', 'anomaly', 'availability'
    metric_type TEXT,
    component TEXT,
    condition TEXT, -- 'cpu > 90', 'cost > 5'
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
    event_type TEXT, -- 'login', 'credential_access', 'config_change', etc.
    actor TEXT, -- User or agent
    agent_id UUID REFERENCES agents(id),
    resource TEXT, -- What was accessed
    action TEXT, -- What was done
    details JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aloy_audit_time ON aloy_audit_events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aloy_audit_actor ON aloy_audit_events(actor);

CREATE TABLE IF NOT EXISTS aloy_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_type TEXT, -- 'unusual_access', 'spike', 'pattern_deviation'
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
    category TEXT, -- 'access_control', 'credential_rotation', 'backup', 'security'
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
    research_type TEXT, -- 'deep_research', 'competitors', 'market_size', etc.
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
CREATE POLICY "Users can access own conversations" ON agent_conversations
    FOR ALL USING (auth.uid() = user_id);
    
CREATE POLICY "Users can access own messages" ON agent_messages
    FOR ALL USING (conversation_id IN (
        SELECT id FROM agent_conversations WHERE user_id = auth.uid()
    ));

CREATE POLICY "Users can access own vault" ON aegis_personal_vault
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access own commitments" ON chiron_commitments
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access own reviews" ON chiron_weekly_reviews
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access own sprints" ON chiron_sprint_plans
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can access own research" ON scholar_research_projects
    FOR ALL USING (auth.uid() = user_id);
```

## 2.2 Seed Agent Data

```sql
-- Insert all agents into the agents table
INSERT INTO agents (name, display_name, tagline, port, category, domain, is_llm_powered) VALUES
-- Infrastructure - THE KEEP
('aegis', 'AEGIS', 'Guardian of Secrets', 8012, 'infrastructure', 'THE_KEEP', false),
('chronos', 'CHRONOS', 'Master of Time', 8010, 'infrastructure', 'THE_KEEP', false),
('hades', 'HADES', 'Lord of the Underworld', 8008, 'infrastructure', 'THE_KEEP', false),
('hermes', 'HERMES', 'Messenger of the Gods', 8014, 'infrastructure', 'THE_KEEP', false),
('argus', 'ARGUS', 'The Watchful Guardian', 8016, 'infrastructure', 'THE_KEEP', false),
('aloy', 'ALOY', 'The Anomaly Hunter', 8015, 'infrastructure', 'THE_KEEP', false),

-- Infrastructure - PANTHEON
('atlas', 'ATLAS', 'Bearer of the World', 8007, 'infrastructure', 'PANTHEON', false),
('sentinel', 'SENTINEL', 'The Gatekeeper', 8019, 'infrastructure', 'PANTHEON', false),
('event-bus', 'EVENT BUS', 'The Neural Network', 8099, 'infrastructure', 'PANTHEON', false),

-- Security - SENTINELS
('panoptes', 'PANOPTES', 'The All-Seeing Eye', 8023, 'security', 'SENTINELS', false),
('asclepius', 'ASCLEPIUS', 'The Divine Physician', 8024, 'security', 'SENTINELS', false),
('cerberus', 'CERBERUS', 'Guardian of the Gates', 8025, 'security', 'SENTINELS', false),

-- Business - CHANCERY
('scholar', 'SCHOLAR', 'Seeker of Truth', 8018, 'business', 'CHANCERY', true),
('chiron', 'CHIRON', 'Wisdom of the Centaur', 8017, 'business', 'CHANCERY', true),
('varys', 'VARYS', 'The Spider', 8020, 'business', 'CHANCERY', false),
('littlefinger', 'PLUTUS', 'Master of Coin', 8205, 'business', 'CHANCERY', true),

-- Creative - ALCHEMY
('muse', 'MUSE', 'Conductor of Creativity', 8030, 'creative', 'ALCHEMY', true),
('calliope', 'CALLIOPE', 'Voice of Eloquence', 8031, 'creative', 'ALCHEMY', true),
('thalia', 'THALIA', 'Artist of the Digital Realm', 8032, 'creative', 'ALCHEMY', false),
('erato', 'ERATO', 'Weaver of Media', 8033, 'creative', 'ALCHEMY', false),
('clio', 'CLIO', 'The Quality Guardian', 8034, 'creative', 'ALCHEMY', true),

-- Personal - THE SHIRE
('aragorn', 'GYM COACH', 'Forge Your Strength', 8110, 'personal', 'THE_SHIRE', true),
('bombadil', 'NUTRITIONIST', 'Wisdom of Wellness', 8101, 'personal', 'THE_SHIRE', true),
('samwise', 'MEAL PLANNER', 'Fuel for the Journey', 8102, 'personal', 'THE_SHIRE', true),
('gandalf', 'ACADEMIC GUIDE', 'The Wise Teacher', 8103, 'personal', 'THE_SHIRE', true),
('arwen', 'EROS', 'Guide of Hearts', 8104, 'personal', 'THE_SHIRE', true)

ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    tagline = EXCLUDED.tagline,
    port = EXCLUDED.port,
    category = EXCLUDED.category,
    domain = EXCLUDED.domain,
    is_llm_powered = EXCLUDED.is_llm_powered;

-- Seed mission documents for VARYS
INSERT INTO varys_mission_documents (document_type, content) VALUES
('MISSION', 'Launch LeverEdge AI automation agency targeting compliance professionals'),
('LAUNCH_DATE', '2026-03-01'),
('REVENUE_GOAL', '$30,000 MRR to leave government job'),
('BOUNDARIES', 'No LinkedIn posting until first clients. No new features that dont serve launch.'),
('PORTFOLIO_TARGET', '$150,000 within 4-5 years')
ON CONFLICT (document_type) DO UPDATE SET content = EXCLUDED.content;
```

---

# PHASE 3: DEV ENVIRONMENT FOR COMMAND CENTER (30 min)

---

## 3.1 Set Up dev.command.leveredgeai.com

### Update Caddyfile
Add to `/home/damon/stack/Caddyfile`:

```
# Command Center DEV
dev.command.leveredgeai.com {
    root * /srv/command-dev
    file_server
    try_files {path} /index.html
    encode gzip
    
    header {
        X-Environment "development"
    }
}

# Command Center PROD (existing)
command.leveredgeai.com {
    root * /srv/command-prod
    file_server
    try_files {path} /index.html
    encode gzip
    
    header {
        X-Environment "production"
    }
}
```

### Update docker-compose.yml volumes
Add to Caddy service volumes:

```yaml
- /opt/leveredge/data-plane/dev/command-center/dist:/srv/command-dev:ro
- /opt/leveredge/data-plane/prod/command-center/dist:/srv/command-prod:ro
```

### Create directory structure
```bash
mkdir -p /opt/leveredge/data-plane/dev/command-center
mkdir -p /opt/leveredge/data-plane/prod/command-center

# Copy existing command center to prod
cp -r /opt/leveredge/command-center/* /opt/leveredge/data-plane/prod/command-center/

# Clone for dev
cp -r /opt/leveredge/command-center/* /opt/leveredge/data-plane/dev/command-center/
```

### Restart Caddy
```bash
cd /home/damon/stack
docker compose restart caddy
```

### Add DNS in Cloudflare
Add A record for `dev.command` pointing to server IP (if not using wildcard).

---

# PHASE 4: AGENT PAGES UI BUILD (Bolt.new) (4-6 hours)

---

## 4.1 Master Bolt.new Prompt - Agent Pages Framework

This goes into Bolt.new FIRST to set up the framework:

```
Add Agent Pages to the ARIA/Command Center frontend.

## DATABASE TABLES
All agent data uses these table prefixes:
- agents (core agent registry)
- agent_health, agent_activity, agent_conversations, agent_messages
- aegis_* (credentials)
- chronos_* (backups)
- hades_* (rollbacks)
- panoptes_*, asclepius_* (integrity/healing)
- hermes_* (notifications)
- argus_* (monitoring/costs)
- aloy_* (audit/anomaly)
- atlas_* (orchestration)
- scholar_* (research)
- chiron_* (coaching)
- varys_* (mission)

## NAVIGATION STRUCTURE

Add "Agents" section to sidebar with expandable categories:

```
─── AGENTS ───
⚙️ Infrastructure (expandable)
   ├── AEGIS (Credentials)
   ├── CHRONOS (Backups)
   ├── HADES (Rollback)
   ├── PANOPTES (Integrity)
   ├── ASCLEPIUS (Healing)
   ├── HERMES (Notifications)
   ├── ARGUS (Monitoring)
   ├── ALOY (Audit)
   └── ATLAS (Orchestration)

💼 Business (expandable)
   ├── SCHOLAR (Research)
   ├── CHIRON (Coach)
   └── VARYS (Mission)

🎨 Creative (expandable)
   └── [Future agents]

🏃 Personal (expandable)
   └── [Future agents]
```

## UNIVERSAL AGENT PAGE TEMPLATE

Every agent page follows this structure:

### Header
- Agent avatar/icon with signature color
- Name and tagline
- Status indicator (🟢 online / 🟡 busy / 🔴 offline)
- Version badge
- Last activity timestamp

### Main Content Area (3-column on desktop, stacked on mobile)

LEFT COLUMN (60%):
- Dashboard metrics (primary metric large, others smaller)
- Data tables/lists specific to agent
- Action buttons panel

RIGHT COLUMN (40%):
- Quick Chat panel (collapsible)
- Agent-specific suggested prompts
- Activity feed (recent actions)

### ADHD-Friendly Design Principles
- ONE primary metric highlighted prominently
- Color-coded status (red/yellow/green)
- Large, clear action buttons
- Minimal text, maximum visual clarity
- Undo buttons where possible

## ROUTES

/agents - Agent overview (grid of all agents with status)
/agents/:category - Category view (infrastructure, business, etc.)
/agents/:name - Individual agent page

## SHARED COMPONENTS

Create these reusable components:
- AgentHeader (avatar, name, status, version)
- MetricGauge (0-100 gauge visualization)
- MetricCard (icon, label, value, trend)
- ActionButton (primary, secondary, danger, warning variants)
- StatusBadge (online, offline, busy, degraded)
- ActivityFeed (list of recent actions)
- QuickChat (collapsible chat panel)
- DataTable (sortable, filterable table)
- Timeline (vertical timeline for events)

## AGENT STATUS FETCHING

Each agent page should:
1. Fetch agent metadata from `agents` table
2. Fetch latest health from `agent_health` table
3. Fetch recent activity from `agent_activity` table
4. Fetch agent-specific data from respective tables

Real-time updates via Supabase subscriptions where applicable.
```

## 4.2 Individual Agent Page Prompts

### AEGIS Page (Credentials)

```
Create the AEGIS agent page at /agents/aegis

## Dashboard Metrics
- PRIMARY: Credential Health Score (gauge 0-100)
- Expiring Soon count (30/60/90 day badges)
- Total Credentials by type
- Failed Auth (24h) - alert if > 0
- Last Rotation timestamp

## Main Content

### Credential List View
Fetch from aegis_credentials table. Display as cards:
- 🔑 Credential name
- Provider badge (OpenAI, Google, AWS, etc.)
- Project badge (LeverEdge, Personal, etc.)
- Status indicator (valid/expiring/expired)
- Last used timestamp
- Actions: [Test] [Rotate] [View Usage] [Delete]

### Filters
- By Project: dropdown
- By Provider: dropdown  
- By Type: dropdown (api_key, oauth_token, password, etc.)
- By Status: tabs (All, Active, Expiring, Expired)

### Actions Panel
- Add Credential (Primary button - opens wizard modal)
- Sync from n8n (Secondary)
- Bulk Health Check (Secondary)
- Rotate Expiring (Warning - with confirmation)
- Export Audit Log (Secondary)
- Emergency Revoke (Danger - with double confirmation)

## Quick Chat Prompts
- "Check if the Salesforce API key is still valid"
- "Rotate all credentials expiring this month"
- "What credentials failed authentication today?"
- "Show me all credentials used by SCHOLAR"

## Personal Vault Section (separate tab)
Fetch from aegis_personal_vault. Display:
- Category grouping (bank, email, subscription, social)
- Name, username, URL
- Copy password button (masked)
- Edit/Delete actions
```

### CHRONOS Page (Backups)

```
Create the CHRONOS agent page at /agents/chronos

## Dashboard Metrics
- PRIMARY: Last Backup (time ago + status badge)
- Storage Used (GB with trend arrow)
- Success Rate % (7 days)
- Next Scheduled (countdown)

## Main Content

### Backup Timeline (Visual)
Show last 7 days as horizontal timeline with dots:
- Green dot = successful backup
- Red dot = failed backup
- Gray dot = no backup
Hovering shows details.

### Backup List
Fetch from chronos_backups. Columns:
- Timestamp
- Type badge (full/incremental/manual)
- Components (icons for each)
- Size
- Duration
- Status
- Actions: [Restore] [Verify] [Download] [Delete]

### Schedule View (tab)
Fetch from chronos_schedules. Show:
- Schedule name
- Cron expression (human readable)
- Next run countdown
- Last run status
- Toggle active/inactive

### Actions Panel
- Backup Now (Primary - opens component selector)
- Test Restore (Secondary - dry run)
- Verify All (Secondary)
- Clean Old Backups (Warning)
- Download Latest (Secondary)

## Quick Chat Prompts
- "Backup everything right now"
- "When was the last successful backup?"
- "Test restoring yesterday's database"
- "How much storage am I using?"
```

### PANOPTES Page (Integrity)

```
Create the PANOPTES agent page at /agents/panoptes

## Dashboard Metrics
- PRIMARY: Health Score (large gauge 0-100, color coded)
- Critical Issues (red badge, pulsing if > 0)
- High Issues (orange badge)
- Medium Issues (yellow badge)
- Last Scan timestamp

## Main Content

### Health Breakdown (Visual)
Horizontal bar chart showing:
- Integrity: ████████░░ 85%
- Agents: ██████████ 100%
- Ports: █████████░ 95%
- Registry: ██████████ 100%
- Services: ███████░░░ 78%

### Issues List
Fetch from panoptes_issues (status = 'open'). Group by severity:

Critical (collapsible, expanded by default):
- 🔴 Description
- Affected components
- Suggested fix
- [Fix Now] [Dismiss] buttons

High, Medium, Low (collapsible)

### Scan History (tab)
Fetch from panoptes_scans. Table:
- Timestamp
- Type
- Health Score
- Issues found
- Duration

### Actions Panel
- Full Scan (Primary)
- Quick Scan (Secondary)
- Fix All Critical (Danger - with confirmation)
- Generate Report (Secondary)
- Set Baseline (Secondary)

## Quick Chat Prompts
- "Scan the system for issues"
- "What's causing the low health score?"
- "Are there any port conflicts?"
- "Generate a compliance report"
```

### ASCLEPIUS Page (Healing)

```
Create the ASCLEPIUS agent page at /agents/asclepius

## Dashboard Metrics
- PRIMARY: Systems Healthy (X/Y count)
- Auto-Heals Today (count)
- Success Rate % (7 days)
- Manual Required (alert if > 0)

## Main Content

### Healing Timeline
Fetch from asclepius_healing_history (last 24h). Vertical timeline:
- ✅ 10:42 - Restarted chronos (auto)
- ✅ 09:15 - Cleared disk space (auto)
- ⚠️ 06:45 - magistrate restart failed (manual needed)

### Pending Plans
Fetch from asclepius_healing_plans (status = 'pending'). Cards:
- Plan #ID
- Actions count
- Risk level badge
- Created timestamp
- [Approve & Execute] [Review] [Reject]

### Healing Strategies (tab)
Fetch from asclepius_strategies. Table:
- Strategy name
- Success rate %
- Avg duration
- Last used
- Toggle active

### Actions Panel
- Auto-Heal Now (Primary)
- Generate Plan (Secondary)
- Manual Heal (Secondary - opens selector)
- Emergency Full (Danger)
- Disable Auto-Healing (Warning toggle)

## Quick Chat Prompts
- "Heal all current issues"
- "What couldn't you fix today?"
- "Restart all unresponsive services"
- "Show me the plan before executing"
```

### ARGUS Page (Monitoring & Costs)

```
Create the ARGUS agent page at /agents/argus

## Dashboard Metrics
- PRIMARY: System Status (healthy/degraded/critical)
- CPU Usage (gauge + trend)
- Memory Usage (gauge + trend)
- Disk Usage (gauge + trend)
- Cost Today ($ amount)

## Main Content

### Agent Fleet Status
Fetch from agents + agent_health. Table/Grid:
- Agent name
- Status indicator
- Port
- Latency (ms)
- Last check

### Cost Tracking
Fetch from argus_cost_tracking. Display:
- Today: $X.XX (progress bar vs budget)
- This Week: $X.XX
- This Month: $X.XX

Cost by Agent (horizontal bar chart):
- SCHOLAR ████████ $12.50
- CHIRON ██████ $8.20
- ARIA █████ $6.40

### Resource Graphs (tab)
Time series charts (last 24h):
- CPU %
- Memory %
- Disk I/O
- Network I/O

### Alerts (tab)
Fetch from argus_alerts. List:
- Alert type
- Condition
- Current value
- Status
- Actions

### Actions Panel
- Full Health Check (Primary)
- View Detailed Metrics (Secondary)
- Export Cost Report (Secondary)
- Set Alert Threshold (Secondary)

## Quick Chat Prompts
- "What's the current system status?"
- "How much did I spend today?"
- "Which agent uses the most resources?"
- "Alert me if costs exceed $5/day"
```

## 4.3 Additional Agent Pages (Brief Specs)

### HADES Page
- Deployment timeline with version history
- Rollback ready status per component
- Emergency rollback button (big red)
- Rollback history table
- Diff viewer for versions

### HERMES Page
- Channel status indicators
- Message delivery rate
- Notification rules list with toggles
- Message log table
- Test notification button

### ALOY Page
- Anomaly feed with dismiss/investigate actions
- Audit log table (filterable)
- Compliance dashboard with pass/fail checks
- Baseline settings

### ATLAS Page
- Active chain executions with progress
- Available chains list with cost/time estimates
- Execution history table
- Batch execution status

### SCHOLAR Page
- Research projects list (active/completed)
- Research type selector
- Results viewer with sources
- Export functionality

### CHIRON Page
- Days to launch countdown (prominent)
- Commitments tracker
- Weekly review history
- Sprint plan viewer
- Framework quick-access buttons

### VARYS Page
- Days to launch (huge number)
- Mission alignment score
- Drift flags with accept/dismiss
- Daily brief viewer
- Mission document editor

---

# PHASE 5: DOCUMENTATION & PORTFOLIO (30 min)

---

## 5.1 Create LOOSE-ENDS-20260118.md

```bash
cat > /opt/leveredge/docs/LOOSE-ENDS-20260118.md << 'EOF'
# LeverEdge Status - January 18, 2026

## 🎯 LAUNCH: 42 DAYS

### Completed Today
- PANOPTES + ASCLEPIUS self-healing infrastructure
- ARIA Frontend V3 with Council, Library, Cost Tracking
- Database schema for all agent pages
- DEV environment for Command Center
- Agent page specifications complete

### In Progress
- Agent page UI builds (Bolt.new)
- Backend API connections

### Remaining
1. Google Workspace email setup
2. SMTP for Supabase Auth
3. Agent page implementations
4. ARIA backend wiring
5. Outreach prep (Feb 1)

## 📊 PORTFOLIO
Current: $58K - $117K across 28+ wins
EOF
```

## 5.2 Update Portfolio

```bash
# Run portfolio update script or SQL
```

```sql
INSERT INTO aria_wins (title, category, description, low_value, high_value, anchor) VALUES
('Agent Pages Database Schema', 'infrastructure', 
 'Designed and implemented comprehensive database schema for 20+ agent UI pages including credentials, backups, rollbacks, integrity monitoring, healing, notifications, costs, audit, orchestration, research, coaching, and mission tracking.',
 4000, 8000, 'Enterprise database design typically costs $200-400/hour'),

('Self-Healing Infrastructure', 'infrastructure',
 'Built PANOPTES integrity guardian and ASCLEPIUS healing agent. System detects issues automatically and heals them. Reduced issues from 83 to 42, achieved zero high-severity issues.',
 3000, 6000, 'DevOps teams charge $150K+/year for this automation'),

('ARIA Frontend V3', 'frontend',
 'Deployed new ARIA personal assistant frontend with Council meetings, Library organization, cost tracking per message, and proper aria_* database integration.',
 2000, 4000, 'Custom AI chat interfaces cost $20K-50K to build')
ON CONFLICT DO NOTHING;
```

## 5.3 Git Commit

```bash
cd /opt/leveredge
git add -A
git commit -m "Jan 18: Mega build - Agent pages schema + infrastructure cleanup

DATABASE:
- Created 30+ tables for agent UI pages
- AEGIS credentials schema
- CHRONOS backup tracking
- HADES deployment/rollback history
- PANOPTES/ASCLEPIUS integrity tracking
- HERMES notification rules and logs
- ARGUS metrics and cost tracking
- ALOY audit events and anomalies
- ATLAS chain/batch executions
- SCHOLAR research projects
- CHIRON commitments and reviews
- VARYS mission and drift tracking
- All RLS policies configured

INFRASTRUCTURE:
- Fixed PANOPTES medium issues
- Updated registry URLs to localhost
- Created maintenance cron jobs
- Storage cleanup
- DEV environment for Command Center

DOCUMENTATION:
- Agent pages UI specification
- Updated loose ends
- Portfolio wins added

Status: 42 days to launch"

git push origin main
```

---

# VERIFICATION CHECKLIST

After completing all phases:

```bash
# 1. ARIA login works
curl -I https://dev.aria.leveredgeai.com

# 2. Command Center DEV works
curl -I https://dev.command.leveredgeai.com

# 3. PANOPTES health score
curl http://localhost:8023/status | python3 -m json.tool | grep health_score

# 4. Database tables exist
# Check in Supabase Studio (DEV)

# 5. Git is clean
cd /opt/leveredge && git status

# 6. Cron jobs installed
crontab -l
```

---

# SUCCESS CRITERIA

- [ ] ARIA password reset complete
- [ ] PANOPTES health score > 85%
- [ ] All agent database tables created
- [ ] DEV Command Center accessible
- [ ] At least AEGIS + PANOPTES pages built
- [ ] Git committed and pushed
- [ ] Documentation updated
- [ ] Portfolio updated

---

# TIME ESTIMATES

| Phase | Estimated Time |
|-------|----------------|
| Infrastructure Loose Ends | 2 hours |
| Database Schema | 1 hour |
| DEV Environment | 30 min |
| Agent Pages (Bolt.new) | 4-6 hours |
| Documentation | 30 min |
| **TOTAL** | **8-10 hours** |

---

**This can be split across multiple sessions. Prioritize in order: Phases 1-2-3 first, then 4-5.**
