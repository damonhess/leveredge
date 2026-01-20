-- =============================================================================
-- UNIFIED THREADING ARCHITECTURE
-- Migration: Create unified conversation threading schema for ARIA
-- Date: 2026-01-20
-- =============================================================================

-- Enable pgvector extension for semantic search (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================================================
-- CORE TABLES
-- =============================================================================

-- Conversations (one per user, unified stream)
CREATE TABLE IF NOT EXISTS aria_unified_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE,  -- One conversation per user!
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    total_messages INT DEFAULT 0,
    total_chunks INT DEFAULT 0,
    primary_buffer_size INT DEFAULT 20,  -- Configurable buffer size
    settings JSONB DEFAULT '{}',

    -- Metadata
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Messages (all messages in the unified stream)
CREATE TABLE IF NOT EXISTS aria_unified_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES aria_unified_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    token_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Message metadata
    metadata JSONB DEFAULT '{}',  -- mode, tools_used, etc.

    -- Chunking status
    chunk_id UUID,  -- Which chunk this message belongs to (null = primary buffer)
    is_in_primary_buffer BOOLEAN DEFAULT TRUE,

    -- For fast primary buffer retrieval
    sequence_num SERIAL
);

-- Chunks (archived conversation segments)
CREATE TABLE IF NOT EXISTS aria_unified_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES aria_unified_conversations(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,  -- Raw messages concatenated
    summary TEXT,  -- LLM-generated summary
    token_count INT NOT NULL,
    message_count INT NOT NULL,

    -- Boundaries
    start_message_id UUID,
    end_message_id UUID,
    start_sequence INT,
    end_sequence INT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    messages_start_at TIMESTAMPTZ,  -- Timestamp of first message in chunk
    messages_end_at TIMESTAMPTZ,    -- Timestamp of last message in chunk

    -- Semantic metadata
    topics JSONB DEFAULT '[]',
    key_entities JSONB DEFAULT '{}',
    importance_score FLOAT DEFAULT 1.0,

    -- Retrieval tracking
    retrieval_count INT DEFAULT 0,
    last_retrieved_at TIMESTAMPTZ,

    -- Compaction
    is_compacted BOOLEAN DEFAULT FALSE,
    source_chunk_ids UUID[] DEFAULT '{}',
    compacted_at TIMESTAMPTZ
);

-- Embeddings (vector storage for semantic search)
CREATE TABLE IF NOT EXISTS aria_unified_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID REFERENCES aria_unified_chunks(id) ON DELETE CASCADE,
    embedding vector(1536),  -- OpenAI ada-002 dimension
    model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(chunk_id)  -- One embedding per chunk
);

-- Key information extracted from chunks
CREATE TABLE IF NOT EXISTS aria_extracted_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES aria_unified_conversations(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES aria_unified_chunks(id) ON DELETE SET NULL,

    info_type TEXT NOT NULL CHECK (info_type IN ('decision', 'commitment', 'preference', 'fact', 'insight')),
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,

    -- For preferences/facts that should persist
    is_permanent BOOLEAN DEFAULT FALSE,
    superseded_by UUID REFERENCES aria_extracted_info(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- For commitments with deadlines

    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- =============================================================================
-- INDEXES
-- =============================================================================

-- Conversation indexes
CREATE INDEX IF NOT EXISTS idx_unified_conv_user ON aria_unified_conversations(user_id);

-- Message indexes
CREATE INDEX IF NOT EXISTS idx_unified_msg_conversation ON aria_unified_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_unified_msg_chunk ON aria_unified_messages(chunk_id);
CREATE INDEX IF NOT EXISTS idx_unified_msg_sequence ON aria_unified_messages(conversation_id, sequence_num DESC);
CREATE INDEX IF NOT EXISTS idx_unified_msg_primary ON aria_unified_messages(conversation_id, is_in_primary_buffer)
    WHERE is_in_primary_buffer = TRUE;
CREATE INDEX IF NOT EXISTS idx_unified_msg_created ON aria_unified_messages(created_at DESC);

-- Chunk indexes
CREATE INDEX IF NOT EXISTS idx_unified_chunk_conversation ON aria_unified_chunks(conversation_id);
CREATE INDEX IF NOT EXISTS idx_unified_chunk_created ON aria_unified_chunks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_unified_chunk_importance ON aria_unified_chunks(importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_unified_chunk_compacted ON aria_unified_chunks(is_compacted);

-- Vector index for semantic search
CREATE INDEX IF NOT EXISTS idx_unified_embeddings_vector ON aria_unified_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Extracted info indexes
CREATE INDEX IF NOT EXISTS idx_extracted_type ON aria_extracted_info(info_type);
CREATE INDEX IF NOT EXISTS idx_extracted_permanent ON aria_extracted_info(is_permanent) WHERE is_permanent = TRUE;
CREATE INDEX IF NOT EXISTS idx_extracted_conversation ON aria_extracted_info(conversation_id);
CREATE INDEX IF NOT EXISTS idx_extracted_active_commitments ON aria_extracted_info(expires_at)
    WHERE info_type = 'commitment' AND expires_at > NOW();

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to get or create unified conversation for a user
CREATE OR REPLACE FUNCTION get_or_create_unified_conversation(p_user_id TEXT)
RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    SELECT id INTO v_conversation_id
    FROM aria_unified_conversations
    WHERE user_id = p_user_id;

    IF v_conversation_id IS NULL THEN
        INSERT INTO aria_unified_conversations (user_id)
        VALUES (p_user_id)
        RETURNING id INTO v_conversation_id;
    END IF;

    RETURN v_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- Function to add message to unified stream
CREATE OR REPLACE FUNCTION add_unified_message(
    p_user_id TEXT,
    p_role TEXT,
    p_content TEXT,
    p_token_count INT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'
)
RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
    v_message_id UUID;
BEGIN
    -- Get or create conversation
    v_conversation_id := get_or_create_unified_conversation(p_user_id);

    -- Insert message
    INSERT INTO aria_unified_messages (
        conversation_id, role, content, token_count, metadata, is_in_primary_buffer
    )
    VALUES (
        v_conversation_id, p_role, p_content, p_token_count, p_metadata, TRUE
    )
    RETURNING id INTO v_message_id;

    -- Update conversation stats
    UPDATE aria_unified_conversations
    SET
        last_message_at = NOW(),
        total_messages = total_messages + 1,
        updated_at = NOW()
    WHERE id = v_conversation_id;

    RETURN v_message_id;
END;
$$ LANGUAGE plpgsql;

-- Function to get primary buffer messages
CREATE OR REPLACE FUNCTION get_primary_buffer(
    p_user_id TEXT,
    p_limit INT DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    role TEXT,
    content TEXT,
    token_count INT,
    created_at TIMESTAMPTZ,
    metadata JSONB,
    sequence_num INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.role,
        m.content,
        m.token_count,
        m.created_at,
        m.metadata,
        m.sequence_num
    FROM aria_unified_messages m
    JOIN aria_unified_conversations c ON m.conversation_id = c.id
    WHERE c.user_id = p_user_id
      AND m.is_in_primary_buffer = TRUE
    ORDER BY m.sequence_num DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to search chunks by semantic similarity
CREATE OR REPLACE FUNCTION search_chunks_semantic(
    p_user_id TEXT,
    p_embedding vector(1536),
    p_limit INT DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    summary TEXT,
    token_count INT,
    similarity FLOAT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS chunk_id,
        c.content,
        c.summary,
        c.token_count,
        1 - (e.embedding <=> p_embedding) AS similarity,
        c.created_at
    FROM aria_unified_chunks c
    JOIN aria_unified_embeddings e ON c.id = e.chunk_id
    JOIN aria_unified_conversations conv ON c.conversation_id = conv.id
    WHERE conv.user_id = p_user_id
      AND 1 - (e.embedding <=> p_embedding) >= p_threshold
    ORDER BY e.embedding <=> p_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to move messages from primary buffer to chunk
CREATE OR REPLACE FUNCTION create_chunk_from_buffer(
    p_conversation_id UUID,
    p_message_ids UUID[],
    p_content TEXT,
    p_token_count INT,
    p_summary TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_chunk_id UUID;
    v_start_seq INT;
    v_end_seq INT;
    v_start_time TIMESTAMPTZ;
    v_end_time TIMESTAMPTZ;
BEGIN
    -- Get sequence boundaries
    SELECT MIN(sequence_num), MAX(sequence_num), MIN(created_at), MAX(created_at)
    INTO v_start_seq, v_end_seq, v_start_time, v_end_time
    FROM aria_unified_messages
    WHERE id = ANY(p_message_ids);

    -- Create chunk
    INSERT INTO aria_unified_chunks (
        conversation_id,
        content,
        summary,
        token_count,
        message_count,
        start_message_id,
        end_message_id,
        start_sequence,
        end_sequence,
        messages_start_at,
        messages_end_at
    )
    VALUES (
        p_conversation_id,
        p_content,
        p_summary,
        p_token_count,
        array_length(p_message_ids, 1),
        p_message_ids[1],
        p_message_ids[array_length(p_message_ids, 1)],
        v_start_seq,
        v_end_seq,
        v_start_time,
        v_end_time
    )
    RETURNING id INTO v_chunk_id;

    -- Update messages to reference chunk and remove from primary buffer
    UPDATE aria_unified_messages
    SET
        chunk_id = v_chunk_id,
        is_in_primary_buffer = FALSE
    WHERE id = ANY(p_message_ids);

    -- Update conversation chunk count
    UPDATE aria_unified_conversations
    SET
        total_chunks = total_chunks + 1,
        updated_at = NOW()
    WHERE id = p_conversation_id;

    RETURN v_chunk_id;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Trigger to update conversation updated_at
CREATE OR REPLACE FUNCTION update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE aria_unified_conversations
    SET updated_at = NOW()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_message_update_conversation ON aria_unified_messages;
CREATE TRIGGER trg_message_update_conversation
    AFTER INSERT ON aria_unified_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_timestamp();

-- =============================================================================
-- END MIGRATION
-- =============================================================================
