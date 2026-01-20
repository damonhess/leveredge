-- =============================================================================
-- ARIA Persistence - Cross-Device Message Sync
-- Adds device tracking and enables realtime for unified threading tables
-- =============================================================================

-- Add device_id to messages for duplicate prevention
ALTER TABLE aria_unified_messages
ADD COLUMN IF NOT EXISTS device_id TEXT;

-- Index for faster conversation queries
CREATE INDEX IF NOT EXISTS idx_unified_messages_conversation_created
ON aria_unified_messages(conversation_id, created_at);

-- Index for user queries
CREATE INDEX IF NOT EXISTS idx_unified_conversations_user
ON aria_unified_conversations(user_id);

-- Enable realtime on unified tables
-- Note: Run these as superuser in Supabase dashboard if they fail
DO $$
BEGIN
    -- Check if publication exists
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        -- Add tables to realtime publication
        ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_messages;
        ALTER PUBLICATION supabase_realtime ADD TABLE aria_unified_conversations;
    END IF;
EXCEPTION
    WHEN duplicate_object THEN
        RAISE NOTICE 'Tables already in publication';
END $$;

-- Grant access to anon and authenticated roles
GRANT SELECT, INSERT, UPDATE ON aria_unified_messages TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON aria_unified_conversations TO anon, authenticated;
GRANT SELECT ON aria_unified_chunks TO anon, authenticated;

-- RLS Policies for unified conversations
ALTER TABLE aria_unified_conversations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own conversations" ON aria_unified_conversations;
CREATE POLICY "Users can view own conversations" ON aria_unified_conversations
    FOR SELECT USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR user_id = auth.uid()::text);

DROP POLICY IF EXISTS "Users can insert own conversations" ON aria_unified_conversations;
CREATE POLICY "Users can insert own conversations" ON aria_unified_conversations
    FOR INSERT WITH CHECK (user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR user_id = auth.uid()::text);

DROP POLICY IF EXISTS "Users can update own conversations" ON aria_unified_conversations;
CREATE POLICY "Users can update own conversations" ON aria_unified_conversations
    FOR UPDATE USING (user_id = current_setting('request.jwt.claims', true)::json->>'sub' OR user_id = auth.uid()::text);

-- RLS Policies for unified messages
ALTER TABLE aria_unified_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own messages" ON aria_unified_messages;
CREATE POLICY "Users can view own messages" ON aria_unified_messages
    FOR SELECT USING (
        conversation_id IN (
            SELECT id FROM aria_unified_conversations
            WHERE user_id = current_setting('request.jwt.claims', true)::json->>'sub'
               OR user_id = auth.uid()::text
        )
    );

DROP POLICY IF EXISTS "Users can insert own messages" ON aria_unified_messages;
CREATE POLICY "Users can insert own messages" ON aria_unified_messages
    FOR INSERT WITH CHECK (
        conversation_id IN (
            SELECT id FROM aria_unified_conversations
            WHERE user_id = current_setting('request.jwt.claims', true)::json->>'sub'
               OR user_id = auth.uid()::text
        )
    );

-- Function to get or create unified conversation (client-callable)
CREATE OR REPLACE FUNCTION get_or_create_unified_conversation_client(p_user_id TEXT)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    -- Check for existing conversation
    SELECT id INTO v_conversation_id
    FROM aria_unified_conversations
    WHERE user_id = p_user_id
    LIMIT 1;

    -- Create if not exists
    IF v_conversation_id IS NULL THEN
        INSERT INTO aria_unified_conversations (user_id)
        VALUES (p_user_id)
        RETURNING id INTO v_conversation_id;
    END IF;

    RETURN v_conversation_id;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION get_or_create_unified_conversation_client(TEXT) TO anon, authenticated;

-- Function to add message (client-callable)
CREATE OR REPLACE FUNCTION add_unified_message_client(
    p_conversation_id UUID,
    p_role TEXT,
    p_content TEXT,
    p_device_id TEXT DEFAULT NULL,
    p_token_count INT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::JSONB
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_message_id UUID;
    v_sequence INT;
BEGIN
    -- Get next sequence number
    SELECT COALESCE(MAX(sequence_num), 0) + 1 INTO v_sequence
    FROM aria_unified_messages
    WHERE conversation_id = p_conversation_id;

    -- Insert message
    INSERT INTO aria_unified_messages (
        conversation_id, role, content, device_id, token_count, metadata, sequence_num, is_in_primary_buffer
    )
    VALUES (
        p_conversation_id, p_role, p_content, p_device_id, p_token_count, p_metadata, v_sequence, TRUE
    )
    RETURNING id INTO v_message_id;

    -- Update conversation stats
    UPDATE aria_unified_conversations
    SET total_messages = total_messages + 1,
        last_message_at = NOW(),
        updated_at = NOW()
    WHERE id = p_conversation_id;

    RETURN v_message_id;
END;
$$;

-- Grant execute to authenticated users
GRANT EXECUTE ON FUNCTION add_unified_message_client(UUID, TEXT, TEXT, TEXT, INT, JSONB) TO anon, authenticated;

-- =============================================================================
-- COMMENTS
-- =============================================================================
COMMENT ON COLUMN aria_unified_messages.device_id IS 'Device identifier to prevent showing own messages from realtime';
