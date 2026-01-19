-- ============================================
-- COACH CHANNEL - Claude↔Claude Communication
-- ============================================

-- Message passing between Claude Web and Claude Code
CREATE TABLE IF NOT EXISTS coach_channel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Participants
    from_agent VARCHAR(50) NOT NULL,  -- LAUNCH_COACH, CLAUDE_CODE, etc.
    to_agent VARCHAR(50) NOT NULL,    -- LAUNCH_COACH, CLAUDE_CODE, ALL

    -- Message
    message_type VARCHAR(50) NOT NULL,  -- instruction, response, status, question, feedback
    subject VARCHAR(255),
    content TEXT NOT NULL,

    -- Context
    context JSONB DEFAULT '{}',  -- Additional structured data
    reference_id VARCHAR(255),   -- Link to GSD, meeting, task, etc.

    -- Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, read, acknowledged, completed
    read_at TIMESTAMPTZ,
    acknowledged_at TIMESTAMPTZ,

    -- Threading
    thread_id UUID,  -- Group related messages
    reply_to UUID REFERENCES coach_channel(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coach_to ON coach_channel(to_agent, status);
CREATE INDEX IF NOT EXISTS idx_coach_from ON coach_channel(from_agent);
CREATE INDEX IF NOT EXISTS idx_coach_thread ON coach_channel(thread_id);
CREATE INDEX IF NOT EXISTS idx_coach_created ON coach_channel(created_at DESC);

-- ============================================
-- ACTIVE SESSIONS
-- ============================================
CREATE TABLE IF NOT EXISTS coach_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_name VARCHAR(255),

    -- Participants
    coach_agent VARCHAR(50) DEFAULT 'LAUNCH_COACH',
    builder_agent VARCHAR(50) DEFAULT 'CLAUDE_CODE',

    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, paused, completed

    -- Context
    current_task VARCHAR(500),
    gsd_path VARCHAR(500),
    notes TEXT,

    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_coach_sessions_status ON coach_sessions(status);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================
CREATE OR REPLACE FUNCTION coach_unread_count(agent_name VARCHAR)
RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER
    FROM coach_channel
    WHERE to_agent = agent_name
    AND status = 'pending';
$$ LANGUAGE SQL;

COMMENT ON TABLE coach_channel IS 'Message passing between Claude Web (LAUNCH_COACH) and Claude Code';
COMMENT ON TABLE coach_sessions IS 'Active coordination sessions between coach and builder';
COMMENT ON FUNCTION coach_unread_count IS 'Returns count of unread messages for an agent';
