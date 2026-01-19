-- ============================================================
-- LCIS: LEVEREDGE COLLECTIVE INTELLIGENCE SYSTEM
-- Database Schema
-- ============================================================

-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- CORE LESSONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content
    content TEXT NOT NULL,
    title TEXT,
    context TEXT,
    outcome TEXT,
    root_cause TEXT,
    solution TEXT,
    alternatives TEXT[] DEFAULT '{}',

    -- Classification
    type TEXT NOT NULL CHECK (type IN (
        'failure',
        'success',
        'pattern',
        'rule',
        'playbook',
        'warning',
        'insight',
        'anti_pattern'
    )),
    severity TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low')),

    -- Domain & Tags
    domain TEXT NOT NULL,
    subdomain TEXT,
    category TEXT,
    tags TEXT[] DEFAULT '{}',

    -- Source
    source_agent TEXT,
    source_type TEXT CHECK (source_type IN (
        'agent_report',
        'claude_code',
        'manual',
        'professor',
        'import',
        'migration'
    )),
    source_context JSONB DEFAULT '{}',
    related_files TEXT[] DEFAULT '{}',
    related_commands TEXT[] DEFAULT '{}',

    -- Semantic Search
    embedding VECTOR(1536),

    -- Lifecycle
    status TEXT DEFAULT 'active' CHECK (status IN (
        'pending',
        'active',
        'superseded',
        'deprecated',
        'promoted'
    )),
    superseded_by UUID REFERENCES lcis_lessons(id),
    promoted_to_rule_id UUID,

    -- Metrics
    occurrence_count INTEGER DEFAULT 1,
    times_recalled INTEGER DEFAULT 0,
    times_helpful INTEGER DEFAULT 0,
    times_ignored INTEGER DEFAULT 0,
    confidence DECIMAL(5,2) DEFAULT 50.0,

    -- Provenance
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    verified_at TIMESTAMPTZ,
    verified_by TEXT,
    last_occurred TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_domain ON lcis_lessons(domain);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_type ON lcis_lessons(type);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_status ON lcis_lessons(status);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_severity ON lcis_lessons(severity);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_source ON lcis_lessons(source_agent);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_tags ON lcis_lessons USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_created ON lcis_lessons(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_embedding ON lcis_lessons
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- RULES TABLE (Enforced Constraints)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES lcis_lessons(id),

    -- Rule Definition
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    trigger_pattern TEXT,
    trigger_keywords TEXT[] DEFAULT '{}',
    trigger_embedding VECTOR(1536),

    -- Action
    action TEXT NOT NULL CHECK (action IN (
        'block',
        'warn',
        'require',
        'suggest'
    )),

    -- What to do instead
    alternatives JSONB DEFAULT '[]',
    required_action TEXT,

    -- Scope
    applies_to_agents TEXT[] DEFAULT '{}',
    applies_to_domains TEXT[] DEFAULT '{}',

    -- Enforcement
    enforced BOOLEAN DEFAULT TRUE,
    enforcement_count INTEGER DEFAULT 0,
    override_count INTEGER DEFAULT 0,
    last_enforced TIMESTAMPTZ,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_lcis_rules_enforced ON lcis_rules(enforced);
CREATE INDEX IF NOT EXISTS idx_lcis_rules_action ON lcis_rules(action);

-- ============================================================
-- PLAYBOOKS TABLE (Success Recipes)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    description TEXT,
    domain TEXT NOT NULL,
    category TEXT,

    -- Steps (ordered)
    steps JSONB NOT NULL DEFAULT '[]',
    prerequisites JSONB DEFAULT '[]',
    expected_outcome TEXT,
    estimated_duration_minutes INTEGER,

    -- Source
    derived_from_lessons UUID[] DEFAULT '{}',

    -- Metrics
    times_used INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AGENT KNOWLEDGE (Per-Agent Relevant Lessons)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_agent_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL,
    lesson_id UUID REFERENCES lcis_lessons(id) ON DELETE CASCADE,

    relevance_score DECIMAL(5,2) DEFAULT 50.0,
    times_applied INTEGER DEFAULT 0,
    last_applied TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(agent, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_lcis_agent_knowledge_agent ON lcis_agent_knowledge(agent);

-- ============================================================
-- EVENTS (Audit Trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    event_type TEXT NOT NULL CHECK (event_type IN (
        'lesson_created',
        'lesson_recalled',
        'lesson_helpful',
        'lesson_ignored',
        'lesson_verified',
        'lesson_superseded',
        'rule_created',
        'rule_enforced',
        'rule_overridden',
        'pattern_detected',
        'playbook_executed',
        'playbook_success',
        'playbook_failure'
    )),

    lesson_id UUID REFERENCES lcis_lessons(id),
    rule_id UUID REFERENCES lcis_rules(id),
    playbook_id UUID REFERENCES lcis_playbooks(id),

    agent TEXT,
    context JSONB DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lcis_events_type ON lcis_events(event_type);
CREATE INDEX IF NOT EXISTS idx_lcis_events_created ON lcis_events(created_at DESC);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Semantic search for lessons
CREATE OR REPLACE FUNCTION lcis_semantic_search(
    query_embedding VECTOR(1536),
    search_domain TEXT DEFAULT NULL,
    search_type TEXT DEFAULT NULL,
    min_confidence DECIMAL DEFAULT 30.0,
    result_limit INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    type TEXT,
    title TEXT,
    content TEXT,
    solution TEXT,
    severity TEXT,
    confidence DECIMAL,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.type,
        l.title,
        l.content,
        l.solution,
        l.severity,
        l.confidence,
        1 - (l.embedding <=> query_embedding) as similarity
    FROM lcis_lessons l
    WHERE l.status = 'active'
    AND l.confidence >= min_confidence
    AND (search_domain IS NULL OR l.domain = search_domain)
    AND (search_type IS NULL OR l.type = search_type)
    AND l.embedding IS NOT NULL
    ORDER BY l.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Check for blocking rules
CREATE OR REPLACE FUNCTION lcis_check_rules(
    p_action TEXT,
    p_domain TEXT DEFAULT NULL,
    p_agent TEXT DEFAULT NULL
)
RETURNS TABLE (
    rule_id UUID,
    rule_name TEXT,
    action TEXT,
    description TEXT,
    alternatives JSONB,
    required_action TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        r.id as rule_id,
        r.name as rule_name,
        r.action,
        r.description,
        r.alternatives,
        r.required_action
    FROM lcis_rules r
    WHERE r.enforced = TRUE
    AND (r.expires_at IS NULL OR r.expires_at > NOW())
    AND (
        -- Check keyword triggers
        EXISTS (
            SELECT 1 FROM unnest(r.trigger_keywords) kw
            WHERE p_action ILIKE '%' || kw || '%'
        )
        -- Or check pattern
        OR (r.trigger_pattern IS NOT NULL AND p_action ~* r.trigger_pattern)
    )
    AND (
        r.applies_to_domains = '{}'
        OR p_domain = ANY(r.applies_to_domains)
    )
    AND (
        r.applies_to_agents = '{}'
        OR p_agent = ANY(r.applies_to_agents)
        OR '*' = ANY(r.applies_to_agents)
    );
END;
$$ LANGUAGE plpgsql;

-- Record lesson occurrence (dedupe)
CREATE OR REPLACE FUNCTION lcis_record_or_increment(
    p_title TEXT,
    p_domain TEXT,
    p_type TEXT
)
RETURNS UUID AS $$
DECLARE
    existing_id UUID;
BEGIN
    -- Check for existing similar lesson
    SELECT id INTO existing_id
    FROM lcis_lessons
    WHERE title = p_title
    AND domain = p_domain
    AND type = p_type
    AND status = 'active'
    LIMIT 1;

    IF existing_id IS NOT NULL THEN
        -- Increment occurrence
        UPDATE lcis_lessons
        SET occurrence_count = occurrence_count + 1,
            last_occurred = NOW(),
            updated_at = NOW()
        WHERE id = existing_id;

        RETURN existing_id;
    END IF;

    RETURN NULL; -- No existing lesson found
END;
$$ LANGUAGE plpgsql;

-- Get critical lessons for Claude Code context
CREATE OR REPLACE FUNCTION lcis_claude_code_context()
RETURNS TABLE (
    category TEXT,
    lessons JSONB
) AS $$
BEGIN
    -- Critical failures (never repeat)
    RETURN QUERY
    SELECT
        'critical_failures'::TEXT as category,
        jsonb_agg(jsonb_build_object(
            'title', l.title,
            'content', l.content,
            'solution', l.solution,
            'domain', l.domain
        )) as lessons
    FROM lcis_lessons l
    WHERE l.type = 'failure'
    AND l.severity IN ('critical', 'high')
    AND l.status = 'active'
    AND l.confidence >= 70
    ORDER BY l.occurrence_count DESC, l.created_at DESC
    LIMIT 20;

    -- Active rules
    RETURN QUERY
    SELECT
        'active_rules'::TEXT as category,
        jsonb_agg(jsonb_build_object(
            'name', r.name,
            'description', r.description,
            'action', r.action,
            'alternatives', r.alternatives
        )) as lessons
    FROM lcis_rules r
    WHERE r.enforced = TRUE
    AND (r.expires_at IS NULL OR r.expires_at > NOW());

    -- Recent successes (replicate)
    RETURN QUERY
    SELECT
        'recent_successes'::TEXT as category,
        jsonb_agg(jsonb_build_object(
            'title', l.title,
            'content', l.content,
            'domain', l.domain
        )) as lessons
    FROM lcis_lessons l
    WHERE l.type = 'success'
    AND l.status = 'active'
    AND l.confidence >= 70
    ORDER BY l.created_at DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Dashboard view
CREATE OR REPLACE VIEW lcis_dashboard AS
SELECT
    (SELECT COUNT(*) FROM lcis_lessons WHERE status = 'active') as total_lessons,
    (SELECT COUNT(*) FROM lcis_lessons WHERE type = 'failure' AND status = 'active') as failures,
    (SELECT COUNT(*) FROM lcis_lessons WHERE type = 'success' AND status = 'active') as successes,
    (SELECT COUNT(*) FROM lcis_rules WHERE enforced = TRUE) as active_rules,
    (SELECT COUNT(*) FROM lcis_playbooks) as playbooks,
    (SELECT COUNT(*) FROM lcis_lessons WHERE created_at > NOW() - INTERVAL '24 hours') as lessons_today,
    (SELECT COUNT(*) FROM lcis_lessons WHERE created_at > NOW() - INTERVAL '7 days') as lessons_week,
    (SELECT SUM(enforcement_count) FROM lcis_rules) as total_enforcements;

-- ============================================================
-- INITIAL SEED RULES (Critical Anti-Patterns)
-- ============================================================

INSERT INTO lcis_rules (name, description, action, trigger_keywords, alternatives, applies_to_agents) VALUES
(
    'No Direct Prod Database Modifications',
    'All database changes must go through DEV first, then promote-to-prod.sh',
    'block',
    ARRAY['prod supabase', 'production database', 'prod db'],
    '["Use DEV Supabase first", "Run promote-to-prod.sh after testing"]'::jsonb,
    ARRAY['*']
),
(
    'Docker Image Rebuild Required',
    'Files baked into Docker images at build time. Restart does not reload them.',
    'require',
    ARRAY['restart container', 'docker restart'],
    '["docker build -t <image>:<tag> .", "Rebuild before restart if files changed"]'::jsonb,
    ARRAY['*']
),
(
    'ARIA Prompt Protection',
    'ARIA system prompt changes require backup and proper update script',
    'require',
    ARRAY['aria prompt', 'aria_system_prompt', 'aria personality'],
    '["Use /opt/leveredge/scripts/aria-prompt-update.sh", "Backup exists at /opt/leveredge/backups/aria-prompts/"]'::jsonb,
    ARRAY['*']
),
(
    'No n8n Workflow SQL Updates',
    'Never update n8n workflows via direct SQL - breaks versioning',
    'block',
    ARRAY['UPDATE workflow', 'INSERT workflow', 'n8n sql'],
    '["Use n8n-troubleshooter MCP", "Use n8n UI to edit workflows"]'::jsonb,
    ARRAY['*']
),
(
    'Git Commit Before Major Changes',
    'Always commit current state before significant modifications',
    'warn',
    ARRAY['major change', 'refactor', 'migration'],
    '["git add . && git commit -m \"Pre-change checkpoint\""]'::jsonb,
    ARRAY['CLAUDE_CODE']
)
ON CONFLICT DO NOTHING;
