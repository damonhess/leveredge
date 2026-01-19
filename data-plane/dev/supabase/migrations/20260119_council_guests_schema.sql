-- ============================================
-- COUNCIL GUESTS SCHEMA
-- Support for MCP-connected guest advisors
-- ============================================

-- Add invited_guests column to council_meetings
ALTER TABLE council_meetings
ADD COLUMN IF NOT EXISTS invited_guests JSONB DEFAULT '[]';

-- Guest participation history
CREATE TABLE IF NOT EXISTS council_guests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES council_meetings(id) ON DELETE CASCADE,
    guest_id VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(255),
    connection_type VARCHAR(50) DEFAULT 'mcp',
    permissions JSONB DEFAULT '["speak", "listen", "vote"]',
    joined_at TIMESTAMPTZ,
    left_at TIMESTAMPTZ,
    statements_count INTEGER DEFAULT 0,
    votes_cast JSONB DEFAULT '[]',
    last_activity TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_council_guests_meeting ON council_guests(meeting_id);
CREATE INDEX IF NOT EXISTS idx_council_guests_name ON council_guests(name);

-- Guest-specific transcript entries marker (if council_transcripts exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'council_transcripts') THEN
        ALTER TABLE council_transcripts ADD COLUMN IF NOT EXISTS is_guest BOOLEAN DEFAULT FALSE;
        ALTER TABLE council_transcripts ADD COLUMN IF NOT EXISTS guest_display_name VARCHAR(255);
    END IF;
END $$;

COMMENT ON TABLE council_guests IS 'Tracks external advisors who join meetings via MCP';
COMMENT ON COLUMN council_guests.permissions IS 'What the guest can do: speak, listen, vote (advisory only)';
COMMENT ON COLUMN council_guests.connection_type IS 'How guest connected: mcp, api, webhook';
