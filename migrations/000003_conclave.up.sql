-- Migration 000003: CONCLAVE Council Meeting System

-- Council agent profiles
CREATE TABLE IF NOT EXISTS council_agent_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT UNIQUE NOT NULL,
    full_name TEXT,
    role TEXT,
    domain TEXT,
    expertise JSONB DEFAULT '[]',
    personality TEXT,
    speaking_style TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Council meetings
CREATE TABLE IF NOT EXISTS council_meetings (
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
CREATE TABLE IF NOT EXISTS council_transcript (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES council_meetings(id) ON DELETE CASCADE,
    turn_number INT NOT NULL,
    speaker TEXT NOT NULL,
    statement TEXT NOT NULL,
    signals JSONB DEFAULT '[]',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- Meeting decisions
CREATE TABLE IF NOT EXISTS council_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES council_meetings(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    rationale TEXT,
    vote_results JSONB,
    action_items JSONB DEFAULT '[]',
    decided_by TEXT DEFAULT 'DAMON',
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- Council actions (tasks from meetings)
CREATE TABLE IF NOT EXISTS council_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES council_meetings(id) ON DELETE CASCADE,
    decision_id UUID REFERENCES council_decisions(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    assigned_to TEXT,
    due_date TIMESTAMPTZ,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Domain supervisors (agents that oversee specific domains)
CREATE TABLE IF NOT EXISTS domain_supervisors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain TEXT UNIQUE NOT NULL,
    supervisor_agent TEXT NOT NULL,
    backup_agent TEXT,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_council_meetings_status ON council_meetings(status);
CREATE INDEX IF NOT EXISTS idx_council_transcript_meeting ON council_transcript(meeting_id);
CREATE INDEX IF NOT EXISTS idx_council_transcript_turn ON council_transcript(meeting_id, turn_number);
CREATE INDEX IF NOT EXISTS idx_council_decisions_meeting ON council_decisions(meeting_id);
CREATE INDEX IF NOT EXISTS idx_council_actions_meeting ON council_actions(meeting_id);
CREATE INDEX IF NOT EXISTS idx_council_actions_status ON council_actions(status);

SELECT 'CONCLAVE migration complete' as status;
