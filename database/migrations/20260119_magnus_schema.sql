-- ============================================================
-- MAGNUS: Universal Project Master
-- Database Schema
-- Created: 2026-01-19
-- ============================================================

-- Projects
CREATE TABLE IF NOT EXISTS magnus_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planning' CHECK (status IN (
        'planning', 'active', 'on_hold', 'completed', 'cancelled'
    )),
    priority INTEGER DEFAULT 50 CHECK (priority >= 1 AND priority <= 100),

    owner TEXT DEFAULT 'damon',
    pm_agent TEXT DEFAULT 'MAGNUS',
    client_name TEXT,
    source_tool TEXT DEFAULT 'leantime',

    target_start DATE,
    target_end DATE,
    actual_start DATE,
    actual_end DATE,

    original_scope JSONB DEFAULT '{}',
    current_scope JSONB DEFAULT '{}',

    tags TEXT[] DEFAULT '{}',
    template_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE IF NOT EXISTS magnus_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES magnus_tasks(id) ON DELETE SET NULL,

    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo' CHECK (status IN (
        'todo', 'in_progress', 'blocked', 'review', 'done', 'cancelled'
    )),
    priority TEXT DEFAULT 'medium' CHECK (priority IN (
        'critical', 'high', 'medium', 'low'
    )),

    assigned_agent TEXT,
    assigned_at TIMESTAMPTZ,

    estimated_hours DECIMAL(6,2),
    actual_hours DECIMAL(6,2) DEFAULT 0,

    due_date DATE,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    depends_on UUID[] DEFAULT '{}',

    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Blockers
CREATE TABLE IF NOT EXISTS magnus_blockers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,

    description TEXT NOT NULL,
    blocker_type TEXT CHECK (blocker_type IN (
        'dependency', 'decision_needed', 'resource', 'external', 'technical', 'other'
    )),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),

    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'escalated', 'resolved')),
    escalated_to TEXT,
    escalated_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decisions
CREATE TABLE IF NOT EXISTS magnus_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES magnus_tasks(id) ON DELETE SET NULL,

    question TEXT NOT NULL,
    context TEXT,
    options JSONB DEFAULT '[]',

    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'decided', 'deferred')),
    decision TEXT,
    decided_by TEXT,
    decided_at TIMESTAMPTZ,
    rationale TEXT,

    decision_deadline DATE,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scope changes
CREATE TABLE IF NOT EXISTS magnus_scope_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,

    change_type TEXT CHECK (change_type IN ('addition', 'removal', 'modification')),
    description TEXT NOT NULL,
    impact_assessment TEXT,

    estimated_hours_added DECIMAL(6,2),
    days_added INTEGER,

    status TEXT DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected')),
    approved_by TEXT,
    approved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily standups
CREATE TABLE IF NOT EXISTS magnus_standups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    standup_date DATE DEFAULT CURRENT_DATE,

    tasks_completed INTEGER DEFAULT 0,
    tasks_in_progress INTEGER DEFAULT 0,
    tasks_blocked INTEGER DEFAULT 0,
    tasks_added INTEGER DEFAULT 0,

    summary TEXT,
    blockers_summary TEXT,
    risks TEXT,
    wins TEXT,
    tomorrow_priorities TEXT,

    velocity_score DECIMAL(5,2),
    health_score DECIMAL(5,2),

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(project_id, standup_date)
);

-- Agent workload
CREATE TABLE IF NOT EXISTS magnus_agent_workload (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL UNIQUE,

    active_tasks INTEGER DEFAULT 0,
    estimated_hours_queued DECIMAL(6,2) DEFAULT 0,
    max_concurrent_tasks INTEGER DEFAULT 5,

    total_tasks_completed INTEGER DEFAULT 0,
    avg_completion_hours DECIMAL(6,2),
    on_time_percentage DECIMAL(5,2),

    last_task_completed TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Action items
CREATE TABLE IF NOT EXISTS magnus_action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    council_id UUID,
    source_type TEXT CHECK (source_type IN ('council', 'standup', 'manual', 'aria')),
    source_context TEXT,

    description TEXT NOT NULL,
    assigned_to TEXT,
    due_date DATE,

    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled')),
    completed_at TIMESTAMPTZ,

    task_id UUID REFERENCES magnus_tasks(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- PM Tool Connections
CREATE TABLE IF NOT EXISTS magnus_pm_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tool_name TEXT NOT NULL,
    connection_name TEXT NOT NULL,

    instance_url TEXT,
    workspace_id TEXT,

    aegis_credential_key TEXT NOT NULL,

    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'error', 'disconnected')),
    last_sync TIMESTAMPTZ,
    last_error TEXT,

    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 15,
    webhook_registered BOOLEAN DEFAULT FALSE,
    webhook_id TEXT,
    webhook_secret TEXT,

    config JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tool_name, connection_name)
);

-- Project mappings
CREATE TABLE IF NOT EXISTS magnus_project_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    magnus_project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,

    external_project_id TEXT NOT NULL,
    external_project_name TEXT,
    external_project_url TEXT,

    sync_direction TEXT DEFAULT 'bidirectional' CHECK (sync_direction IN (
        'from_source', 'to_source', 'bidirectional'
    )),

    field_mappings JSONB DEFAULT '{}',

    last_sync TIMESTAMPTZ,
    last_sync_status TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(connection_id, external_project_id)
);

-- Task mappings
CREATE TABLE IF NOT EXISTS magnus_task_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    magnus_task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,
    project_mapping_id UUID REFERENCES magnus_project_mappings(id) ON DELETE CASCADE,

    external_task_id TEXT NOT NULL,
    external_task_url TEXT,

    last_sync TIMESTAMPTZ,
    last_sync_hash TEXT,
    sync_conflict BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(connection_id, external_task_id)
);

-- Sync log
CREATE TABLE IF NOT EXISTS magnus_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    connection_id UUID REFERENCES magnus_pm_connections(id),
    project_mapping_id UUID REFERENCES magnus_project_mappings(id),

    sync_type TEXT CHECK (sync_type IN ('full', 'incremental', 'webhook', 'manual')),
    direction TEXT CHECK (direction IN ('from_source', 'to_source', 'bidirectional')),

    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,

    items_synced INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,

    error_details JSONB DEFAULT '[]',

    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'partial'))
);

-- Project templates
CREATE TABLE IF NOT EXISTS magnus_project_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL UNIQUE,
    description TEXT,

    phases JSONB DEFAULT '[]',
    default_tasks JSONB DEFAULT '[]',
    estimated_duration_days INTEGER,

    default_tool TEXT DEFAULT 'leantime',
    tags TEXT[] DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_magnus_projects_status ON magnus_projects(status);
CREATE INDEX IF NOT EXISTS idx_magnus_projects_client ON magnus_projects(client_name);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_project ON magnus_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_status ON magnus_tasks(status);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_agent ON magnus_tasks(assigned_agent);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_due ON magnus_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_magnus_blockers_status ON magnus_blockers(status);
CREATE INDEX IF NOT EXISTS idx_magnus_decisions_status ON magnus_decisions(status);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Get project summary
CREATE OR REPLACE FUNCTION magnus_project_summary(p_project_id UUID DEFAULT NULL)
RETURNS TABLE (
    id UUID,
    name TEXT,
    status TEXT,
    client_name TEXT,
    priority INTEGER,
    target_end DATE,
    days_remaining INTEGER,
    tasks_done BIGINT,
    tasks_in_progress BIGINT,
    tasks_todo BIGINT,
    tasks_blocked BIGINT,
    total_tasks BIGINT,
    completion_percentage DECIMAL,
    open_blockers BIGINT,
    pending_decisions BIGINT,
    health_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id,
        p.name,
        p.status,
        p.client_name,
        p.priority,
        p.target_end,
        (p.target_end - CURRENT_DATE)::INTEGER as days_remaining,
        COUNT(t.id) FILTER (WHERE t.status = 'done'),
        COUNT(t.id) FILTER (WHERE t.status = 'in_progress'),
        COUNT(t.id) FILTER (WHERE t.status = 'todo'),
        COUNT(t.id) FILTER (WHERE t.status = 'blocked'),
        COUNT(t.id),
        CASE WHEN COUNT(t.id) > 0
            THEN ROUND(COUNT(t.id) FILTER (WHERE t.status = 'done')::DECIMAL / COUNT(t.id) * 100, 1)
            ELSE 0
        END,
        (SELECT COUNT(*) FROM magnus_blockers b WHERE b.project_id = p.id AND b.status = 'open'),
        (SELECT COUNT(*) FROM magnus_decisions d WHERE d.project_id = p.id AND d.status = 'pending'),
        CASE
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 3 THEN 40
            WHEN (p.target_end - CURRENT_DATE) < 7 AND COUNT(t.id) FILTER (WHERE t.status = 'done')::DECIMAL / NULLIF(COUNT(t.id), 0) < 0.8 THEN 50
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 0 THEN 70
            ELSE 90
        END::DECIMAL
    FROM magnus_projects p
    LEFT JOIN magnus_tasks t ON t.project_id = p.id
    WHERE (p_project_id IS NULL OR p.id = p_project_id)
    AND p.status IN ('planning', 'active')
    GROUP BY p.id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- SEED DATA
-- ============================================================

-- Project templates
INSERT INTO magnus_project_templates (name, description, phases, default_tasks, estimated_duration_days) VALUES
(
    'automation_project',
    'Standard client automation project',
    '[{"name": "Discovery", "duration_days": 3}, {"name": "Design", "duration_days": 5}, {"name": "Build", "duration_days": 10}, {"name": "Test", "duration_days": 3}, {"name": "Deploy", "duration_days": 2}]'::jsonb,
    '[{"title": "Discovery call", "phase": "Discovery"}, {"title": "Requirements doc", "phase": "Discovery"}, {"title": "Solution design", "phase": "Design"}, {"title": "Build automation", "phase": "Build"}, {"title": "Testing", "phase": "Test"}, {"title": "Deploy", "phase": "Deploy"}]'::jsonb,
    25
),
(
    'agent_development',
    'Building a new LeverEdge agent',
    '[{"name": "Specification", "duration_days": 2}, {"name": "Development", "duration_days": 5}, {"name": "Testing", "duration_days": 2}, {"name": "Integration", "duration_days": 2}]'::jsonb,
    '[{"title": "Write agent spec", "phase": "Specification"}, {"title": "Database schema", "phase": "Development"}, {"title": "FastAPI service", "phase": "Development"}, {"title": "Unit tests", "phase": "Testing"}, {"title": "MCP tools", "phase": "Integration"}]'::jsonb,
    12
)
ON CONFLICT (name) DO NOTHING;

-- Internal connections
INSERT INTO magnus_pm_connections (tool_name, connection_name, instance_url, aegis_credential_key, status, config)
VALUES
('leantime', 'LeverEdge Internal', 'http://leantime:8080', 'leantime_internal', 'active', '{"is_primary": true}'::jsonb),
('openproject', 'LeverEdge Enterprise', 'http://openproject:80', 'openproject_internal', 'active', '{"use_for": "enterprise"}'::jsonb)
ON CONFLICT DO NOTHING;

-- LeverEdge Launch project
INSERT INTO magnus_projects (name, description, status, priority, owner, pm_agent, target_start, target_end, source_tool)
VALUES (
    'LeverEdge Agency Launch',
    'Build and launch LeverEdge AI automation agency by March 1, 2026',
    'active', 100, 'damon', 'MAGNUS', '2026-01-11', '2026-03-01', 'leantime'
) ON CONFLICT DO NOTHING;

-- Agent workloads
INSERT INTO magnus_agent_workload (agent, max_concurrent_tasks) VALUES
('CHRONOS', 5), ('HADES', 3), ('AEGIS', 3), ('HERMES', 10),
('SCHOLAR', 3), ('CHIRON', 3), ('ATHENA', 5), ('MUSE', 3),
('QUILL', 5), ('VARYS', 3), ('MAGNUS', 10), ('HEPHAESTUS', 5)
ON CONFLICT (agent) DO NOTHING;

-- ============================================================
-- MIGRATION COMPLETE
-- ============================================================
-- MAGNUS database schema created successfully
-- Tables: 14
-- Indexes: 8
-- Functions: 1
-- Seed data: templates, connections, project, agent workloads
