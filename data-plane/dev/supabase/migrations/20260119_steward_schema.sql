-- ============================================
-- STEWARD: Professional Coordination & Meeting Prep
-- Port: 8220
-- Domain: THE KEEP
-- ============================================

-- ============================================
-- PROFESSIONALS (Your advisors)
-- ============================================
CREATE TABLE IF NOT EXISTS steward_professionals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    role VARCHAR(100) NOT NULL,  -- cpa, attorney, financial_advisor, etc.
    company VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    specialty TEXT,  -- "business tax", "estate planning", etc.
    domain VARCHAR(50),  -- business, personal, both
    notes TEXT,
    last_meeting TIMESTAMPTZ,
    next_meeting TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prof_role ON steward_professionals(role);
CREATE INDEX IF NOT EXISTS idx_prof_domain ON steward_professionals(domain);

-- ============================================
-- MEETINGS
-- ============================================
CREATE TABLE IF NOT EXISTS steward_meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID REFERENCES steward_professionals(id),
    title VARCHAR(255) NOT NULL,
    meeting_date TIMESTAMPTZ NOT NULL,
    duration_minutes INTEGER,
    location VARCHAR(255),  -- address, zoom link, phone
    status VARCHAR(50) DEFAULT 'scheduled',  -- scheduled, completed, cancelled

    -- Prep
    agenda TEXT,
    questions_to_ask JSONB DEFAULT '[]',
    docs_to_bring JSONB DEFAULT '[]',
    context_notes TEXT,  -- What STEWARD prepared

    -- Outcomes
    summary TEXT,
    advice_received JSONB DEFAULT '[]',
    action_items JSONB DEFAULT '[]',
    follow_up_date DATE,

    -- Metadata
    domain VARCHAR(50),  -- business, personal
    topics TEXT[],  -- ['entity_structure', 's_corp_election']
    agents_consulted TEXT[],  -- ['SOLON', 'QUAESTOR']

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meeting_prof ON steward_meetings(professional_id);
CREATE INDEX IF NOT EXISTS idx_meeting_date ON steward_meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_meeting_status ON steward_meetings(status);

-- ============================================
-- ADVICE LOG (What professionals told you)
-- ============================================
CREATE TABLE IF NOT EXISTS steward_advice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_id UUID REFERENCES steward_professionals(id),
    meeting_id UUID REFERENCES steward_meetings(id),

    topic VARCHAR(255) NOT NULL,
    advice TEXT NOT NULL,
    reasoning TEXT,

    -- Classification
    domain VARCHAR(50),  -- business, personal
    category VARCHAR(100),  -- tax, legal, investment, entity, etc.
    urgency VARCHAR(50) DEFAULT 'normal',  -- immediate, soon, normal, fyi

    -- Action
    requires_action BOOLEAN DEFAULT FALSE,
    action_description TEXT,
    action_deadline DATE,
    action_status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, completed, deferred
    action_completed_at TIMESTAMPTZ,

    -- Context
    applies_to VARCHAR(100),  -- leveredge, personal, both
    valid_until DATE,  -- Some advice expires (tax years, etc.)
    superseded_by UUID REFERENCES steward_advice(id),

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_advice_prof ON steward_advice(professional_id);
CREATE INDEX IF NOT EXISTS idx_advice_topic ON steward_advice(topic);
CREATE INDEX IF NOT EXISTS idx_advice_category ON steward_advice(category);
CREATE INDEX IF NOT EXISTS idx_advice_action ON steward_advice(requires_action, action_status);

-- ============================================
-- QUESTIONS (Things to ask professionals)
-- ============================================
CREATE TABLE IF NOT EXISTS steward_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    context TEXT,

    -- Routing
    target_role VARCHAR(100),  -- cpa, attorney, etc.
    target_professional_id UUID REFERENCES steward_professionals(id),
    domain VARCHAR(50),
    category VARCHAR(100),

    -- Status
    priority VARCHAR(50) DEFAULT 'normal',
    status VARCHAR(50) DEFAULT 'pending',  -- pending, scheduled, asked, answered
    scheduled_meeting_id UUID REFERENCES steward_meetings(id),

    -- Answer
    answer TEXT,
    answered_at TIMESTAMPTZ,
    answered_by UUID REFERENCES steward_professionals(id),

    -- Source
    source_agent VARCHAR(50),  -- SOLON, QUAESTOR, user, etc.

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_questions_status ON steward_questions(status);
CREATE INDEX IF NOT EXISTS idx_questions_role ON steward_questions(target_role);

-- ============================================
-- DOCUMENT TRACKER
-- ============================================
CREATE TABLE IF NOT EXISTS steward_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    document_type VARCHAR(100),  -- tax_return, contract, statement, etc.
    year INTEGER,

    -- Status
    status VARCHAR(50) DEFAULT 'needed',  -- needed, requested, received, filed
    due_date DATE,
    received_date DATE,

    -- Location
    file_path TEXT,
    storage_location VARCHAR(255),  -- "Google Drive > Tax > 2025"

    -- Association
    professional_id UUID REFERENCES steward_professionals(id),
    meeting_id UUID REFERENCES steward_meetings(id),

    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_docs_type ON steward_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_docs_status ON steward_documents(status);
