-- ==========================================
-- ARIA UNIFIED THREADING - DATABASE SCHEMA
-- Migration: 20260118_unified_threading_tables
-- Target: DEV Supabase (postgres_dev)
-- ==========================================
--
-- EXTENDS existing aria_conversations and aria_messages tables with:
-- - Chunking support (aria_chunks table)
-- - Semantic retrieval (aria_chunk_embeddings for chunks)
-- - Context compaction for old chunks
-- - Unified stream tracking (sequence numbers, buffer management)
--
-- Existing tables: aria_conversations, aria_messages, aria_unified_memory
-- New tables: aria_chunks, aria_chunk_embeddings, aria_extracted_info
-- ==========================================

-- pgvector already enabled (existing tables have vector columns)

-- ==========================================
-- EXTEND EXISTING TABLES
-- ==========================================

-- Add unified threading columns to aria_conversations
ALTER TABLE aria_conversations
    ADD COLUMN IF NOT EXISTS total_messages INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS total_chunks INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_message_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS threading_settings JSONB DEFAULT '{
        "primary_buffer_size": 20,
        "chunk_token_threshold": 4000,
        "chunk_message_threshold": 20,
        "topic_shift_threshold": 0.3,
        "time_gap_hours": 4,
        "context_budget_tokens": 8000,
        "recency_weight": 0.3,
        "semantic_weight": 0.7
    }'::JSONB;

-- Add chunking columns to aria_messages
ALTER TABLE aria_messages
    ADD COLUMN IF NOT EXISTS chunk_id UUID,
    ADD COLUMN IF NOT EXISTS sequence_num SERIAL;

-- Add token_count if not exists (existing has input_tokens, output_tokens)
ALTER TABLE aria_messages
    ADD COLUMN IF NOT EXISTS token_count INT;

-- Create index for primary buffer (messages not yet chunked)
CREATE INDEX IF NOT EXISTS idx_aria_messages_primary_buffer ON aria_messages(conversation_id, sequence_num DESC)
    WHERE chunk_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_aria_messages_sequence ON aria_messages(conversation_id, sequence_num DESC);

-- ==========================================
-- NEW TABLES
-- ==========================================

-- Chunks (archived conversation segments)
CREATE TABLE IF NOT EXISTS aria_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES aria_conversations(id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,  -- Raw messages concatenated
    summary TEXT,           -- LLM-generated summary
    token_count INT NOT NULL,
    message_count INT NOT NULL,

    -- Boundaries
    start_message_id UUID REFERENCES aria_messages(id),
    end_message_id UUID REFERENCES aria_messages(id),
    start_sequence INT NOT NULL,
    end_sequence INT NOT NULL,

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    topics JSONB DEFAULT '[]'::JSONB,
    key_entities JSONB DEFAULT '{}'::JSONB,
    importance_score FLOAT DEFAULT 1.0,

    -- Retrieval tracking
    retrieval_count INT DEFAULT 0,
    last_retrieved_at TIMESTAMPTZ,

    -- Compaction tracking
    is_compacted BOOLEAN DEFAULT FALSE,
    source_chunk_ids UUID[] DEFAULT '{}',
    compacted_at TIMESTAMPTZ,

    -- Embedding reference
    embedding_id UUID
);

CREATE INDEX IF NOT EXISTS idx_aria_chunks_conversation ON aria_chunks(conversation_id);
CREATE INDEX IF NOT EXISTS idx_aria_chunks_created ON aria_chunks(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_aria_chunks_retrieval ON aria_chunks(conversation_id, retrieval_count DESC);
CREATE INDEX IF NOT EXISTS idx_aria_chunks_importance ON aria_chunks(conversation_id, importance_score DESC);
CREATE INDEX IF NOT EXISTS idx_aria_chunks_compacted ON aria_chunks(is_compacted) WHERE is_compacted = FALSE;

-- Add foreign key from messages to chunks
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_message_chunk'
    ) THEN
        ALTER TABLE aria_messages
            ADD CONSTRAINT fk_message_chunk
            FOREIGN KEY (chunk_id) REFERENCES aria_chunks(id) ON DELETE SET NULL;
    END IF;
END$$;

-- Chunk embeddings (separate table for vector storage efficiency)
CREATE TABLE IF NOT EXISTS aria_chunk_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES aria_chunks(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,  -- OpenAI ada-002 dimension
    model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector index for semantic search
CREATE INDEX IF NOT EXISTS idx_aria_chunk_embeddings_vector ON aria_chunk_embeddings
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_aria_chunk_embeddings_chunk ON aria_chunk_embeddings(chunk_id);

-- Extracted information (extends aria_unified_memory concept)
CREATE TABLE IF NOT EXISTS aria_extracted_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES aria_conversations(id) ON DELETE CASCADE,
    chunk_id UUID REFERENCES aria_chunks(id) ON DELETE SET NULL,
    message_id UUID REFERENCES aria_messages(id) ON DELETE SET NULL,

    -- Extracted content
    info_type TEXT NOT NULL CHECK (info_type IN (
        'decision', 'commitment', 'preference', 'fact', 'insight',
        'goal', 'task', 'emotion', 'topic_shift'
    )),
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),

    -- Persistence flags
    is_permanent BOOLEAN DEFAULT FALSE,
    superseded_by UUID REFERENCES aria_extracted_info(id),

    -- Temporal
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,

    -- Retrieval boost
    importance_weight FLOAT DEFAULT 1.0
);

CREATE INDEX IF NOT EXISTS idx_aria_extracted_type ON aria_extracted_info(info_type);
CREATE INDEX IF NOT EXISTS idx_aria_extracted_permanent ON aria_extracted_info(is_permanent) WHERE is_permanent = TRUE;
CREATE INDEX IF NOT EXISTS idx_aria_extracted_conversation ON aria_extracted_info(conversation_id);
CREATE INDEX IF NOT EXISTS idx_aria_extracted_expires ON aria_extracted_info(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_aria_extracted_active ON aria_extracted_info(conversation_id, info_type)
    WHERE superseded_by IS NULL AND (expires_at IS NULL OR expires_at > NOW());

-- ==========================================
-- HELPER FUNCTIONS
-- ==========================================

-- Get or create unified conversation for user
-- Uses session_id 'unified' for the single stream approach
CREATE OR REPLACE FUNCTION aria_get_unified_conversation(p_user_id TEXT DEFAULT 'damon')
RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    -- Try to get existing unified conversation
    SELECT id INTO v_conversation_id
    FROM aria_conversations
    WHERE session_id = 'unified-' || p_user_id;

    -- Create if not exists
    IF v_conversation_id IS NULL THEN
        INSERT INTO aria_conversations (session_id, title, total_messages, total_chunks)
        VALUES ('unified-' || p_user_id, 'Unified Conversation Stream', 0, 0)
        RETURNING id INTO v_conversation_id;
    END IF;

    RETURN v_conversation_id;
END;
$$ LANGUAGE plpgsql;

-- Add message to unified stream
CREATE OR REPLACE FUNCTION aria_stream_add_message(
    p_user_id TEXT DEFAULT 'damon',
    p_role TEXT DEFAULT 'user',
    p_content TEXT DEFAULT '',
    p_token_count INT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::JSONB
) RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
    v_message_id UUID;
BEGIN
    -- Get unified conversation
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    -- Insert message
    INSERT INTO aria_messages (conversation_id, role, content, token_count, metadata)
    VALUES (v_conversation_id, p_role, p_content, p_token_count, p_metadata)
    RETURNING id INTO v_message_id;

    -- Update conversation stats
    UPDATE aria_conversations
    SET
        last_message_at = NOW(),
        updated_at = NOW(),
        total_messages = COALESCE(total_messages, 0) + 1
    WHERE id = v_conversation_id;

    RETURN v_message_id;
END;
$$ LANGUAGE plpgsql;

-- Get primary buffer (recent messages not yet chunked)
CREATE OR REPLACE FUNCTION aria_get_primary_buffer(
    p_user_id TEXT DEFAULT 'damon',
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
DECLARE
    v_conversation_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    RETURN QUERY
    SELECT
        m.id, m.role, m.content, COALESCE(m.token_count, m.input_tokens + COALESCE(m.output_tokens, 0)),
        m.created_at, m.metadata, m.sequence_num
    FROM aria_messages m
    WHERE m.conversation_id = v_conversation_id
      AND m.chunk_id IS NULL
    ORDER BY m.sequence_num DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Get buffer stats for chunking decision
CREATE OR REPLACE FUNCTION aria_get_buffer_stats(p_user_id TEXT DEFAULT 'damon')
RETURNS TABLE (
    conv_id UUID,
    message_count BIGINT,
    total_tokens BIGINT,
    oldest_message_at TIMESTAMPTZ,
    newest_message_at TIMESTAMPTZ,
    time_gap_hours NUMERIC
) AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    RETURN QUERY
    SELECT
        v_conversation_id,
        COUNT(*)::BIGINT as message_count,
        COALESCE(SUM(COALESCE(m.token_count, m.input_tokens + COALESCE(m.output_tokens, 0))), 0)::BIGINT as total_tokens,
        MIN(m.created_at) as oldest_message_at,
        MAX(m.created_at) as newest_message_at,
        EXTRACT(EPOCH FROM (MAX(m.created_at) - MIN(m.created_at))) / 3600 as time_gap_hours
    FROM aria_messages m
    WHERE m.conversation_id = v_conversation_id
      AND m.chunk_id IS NULL;
END;
$$ LANGUAGE plpgsql;

-- Create a chunk from messages
CREATE OR REPLACE FUNCTION aria_create_chunk(
    p_user_id TEXT DEFAULT 'damon',
    p_start_sequence INT DEFAULT NULL,
    p_end_sequence INT DEFAULT NULL,
    p_content TEXT DEFAULT '',
    p_summary TEXT DEFAULT NULL,
    p_token_count INT DEFAULT 0,
    p_topics JSONB DEFAULT '[]'::JSONB
) RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
    v_chunk_id UUID;
    v_message_count BIGINT;
    v_start_message_id UUID;
    v_end_message_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    -- Get message IDs and count for the sequence range
    SELECT
        COUNT(*),
        MIN(id),
        MAX(id)
    INTO v_message_count, v_start_message_id, v_end_message_id
    FROM aria_messages
    WHERE conversation_id = v_conversation_id
      AND sequence_num >= p_start_sequence
      AND sequence_num <= p_end_sequence;

    -- Create chunk
    INSERT INTO aria_chunks (
        conversation_id, content, summary, token_count, message_count,
        start_message_id, end_message_id, start_sequence, end_sequence, topics
    )
    VALUES (
        v_conversation_id, p_content, p_summary, p_token_count, v_message_count::INT,
        v_start_message_id, v_end_message_id, p_start_sequence, p_end_sequence, p_topics
    )
    RETURNING id INTO v_chunk_id;

    -- Update messages to reference chunk
    UPDATE aria_messages
    SET chunk_id = v_chunk_id
    WHERE conversation_id = v_conversation_id
      AND sequence_num >= p_start_sequence
      AND sequence_num <= p_end_sequence;

    -- Update conversation stats
    UPDATE aria_conversations
    SET total_chunks = COALESCE(total_chunks, 0) + 1
    WHERE id = v_conversation_id;

    RETURN v_chunk_id;
END;
$$ LANGUAGE plpgsql;

-- Store embedding for a chunk
CREATE OR REPLACE FUNCTION aria_store_chunk_embedding(
    p_chunk_id UUID,
    p_embedding vector(1536),
    p_model TEXT DEFAULT 'text-embedding-ada-002'
) RETURNS UUID AS $$
DECLARE
    v_embedding_id UUID;
BEGIN
    -- Insert embedding
    INSERT INTO aria_chunk_embeddings (chunk_id, embedding, model)
    VALUES (p_chunk_id, p_embedding, p_model)
    RETURNING id INTO v_embedding_id;

    -- Update chunk with embedding reference
    UPDATE aria_chunks
    SET embedding_id = v_embedding_id
    WHERE id = p_chunk_id;

    RETURN v_embedding_id;
END;
$$ LANGUAGE plpgsql;

-- Semantic search with recency boost
CREATE OR REPLACE FUNCTION aria_semantic_search(
    p_user_id TEXT DEFAULT 'damon',
    p_query_embedding vector(1536),
    p_limit INT DEFAULT 10,
    p_threshold FLOAT DEFAULT 0.7,
    p_recency_weight FLOAT DEFAULT 0.3,
    p_semantic_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    summary TEXT,
    similarity FLOAT,
    recency_score FLOAT,
    combined_score FLOAT,
    created_at TIMESTAMPTZ,
    topics JSONB,
    token_count INT
) AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    RETURN QUERY
    SELECT
        c.id as chunk_id,
        c.content,
        c.summary,
        (1 - (e.embedding <=> p_query_embedding))::FLOAT as similarity,
        (1.0 / (1 + EXTRACT(EPOCH FROM (NOW() - c.created_at)) / 86400))::FLOAT as recency_score,
        (
            (1 - (e.embedding <=> p_query_embedding)) * p_semantic_weight +
            (1.0 / (1 + EXTRACT(EPOCH FROM (NOW() - c.created_at)) / 86400)) * p_recency_weight
        )::FLOAT as combined_score,
        c.created_at,
        c.topics,
        c.token_count
    FROM aria_chunks c
    JOIN aria_chunk_embeddings e ON e.chunk_id = c.id
    WHERE c.conversation_id = v_conversation_id
      AND (1 - (e.embedding <=> p_query_embedding)) >= p_threshold
    ORDER BY combined_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Record chunk retrieval (for analytics)
CREATE OR REPLACE FUNCTION aria_record_retrieval(p_chunk_ids UUID[])
RETURNS VOID AS $$
BEGIN
    UPDATE aria_chunks
    SET
        retrieval_count = retrieval_count + 1,
        last_retrieved_at = NOW()
    WHERE id = ANY(p_chunk_ids);
END;
$$ LANGUAGE plpgsql;

-- Get conversation statistics
CREATE OR REPLACE FUNCTION aria_conversation_stats(p_user_id TEXT DEFAULT 'damon')
RETURNS TABLE (
    conv_id UUID,
    total_messages BIGINT,
    total_chunks BIGINT,
    buffer_messages BIGINT,
    buffer_tokens BIGINT,
    archive_tokens BIGINT,
    oldest_message TIMESTAMPTZ,
    newest_message TIMESTAMPTZ,
    most_retrieved_chunk UUID,
    least_retrieved_chunk UUID
) AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    RETURN QUERY
    SELECT
        v_conversation_id,
        (SELECT COUNT(*) FROM aria_messages m WHERE m.conversation_id = v_conversation_id),
        (SELECT COUNT(*) FROM aria_chunks c WHERE c.conversation_id = v_conversation_id),
        (SELECT COUNT(*) FROM aria_messages m WHERE m.conversation_id = v_conversation_id AND m.chunk_id IS NULL),
        (SELECT COALESCE(SUM(COALESCE(m.token_count, m.input_tokens)), 0) FROM aria_messages m WHERE m.conversation_id = v_conversation_id AND m.chunk_id IS NULL),
        (SELECT COALESCE(SUM(c.token_count), 0) FROM aria_chunks c WHERE c.conversation_id = v_conversation_id),
        (SELECT MIN(m.created_at) FROM aria_messages m WHERE m.conversation_id = v_conversation_id),
        (SELECT MAX(m.created_at) FROM aria_messages m WHERE m.conversation_id = v_conversation_id),
        (SELECT c.id FROM aria_chunks c WHERE c.conversation_id = v_conversation_id ORDER BY c.retrieval_count DESC LIMIT 1),
        (SELECT c.id FROM aria_chunks c WHERE c.conversation_id = v_conversation_id ORDER BY c.retrieval_count ASC LIMIT 1);
END;
$$ LANGUAGE plpgsql;

-- Extract and store key information
CREATE OR REPLACE FUNCTION aria_extract_info(
    p_user_id TEXT DEFAULT 'damon',
    p_chunk_id UUID DEFAULT NULL,
    p_message_id UUID DEFAULT NULL,
    p_info_type TEXT DEFAULT 'fact',
    p_content TEXT DEFAULT '',
    p_confidence FLOAT DEFAULT 1.0,
    p_is_permanent BOOLEAN DEFAULT FALSE,
    p_expires_at TIMESTAMPTZ DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
    v_info_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    INSERT INTO aria_extracted_info (
        conversation_id, chunk_id, message_id, info_type,
        content, confidence, is_permanent, expires_at
    )
    VALUES (
        v_conversation_id, p_chunk_id, p_message_id, p_info_type,
        p_content, p_confidence, p_is_permanent, p_expires_at
    )
    RETURNING id INTO v_info_id;

    RETURN v_info_id;
END;
$$ LANGUAGE plpgsql;

-- Get active extracted information by type
CREATE OR REPLACE FUNCTION aria_get_info(
    p_user_id TEXT DEFAULT 'damon',
    p_info_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    info_type TEXT,
    content TEXT,
    confidence FLOAT,
    is_permanent BOOLEAN,
    created_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ
) AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    RETURN QUERY
    SELECT
        e.id, e.info_type, e.content, e.confidence::FLOAT,
        e.is_permanent, e.created_at, e.expires_at
    FROM aria_extracted_info e
    WHERE e.conversation_id = v_conversation_id
      AND e.superseded_by IS NULL
      AND (e.expires_at IS NULL OR e.expires_at > NOW())
      AND (p_info_type IS NULL OR e.info_type = p_info_type)
    ORDER BY e.importance_weight DESC, e.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Get chunks ready for compaction
CREATE OR REPLACE FUNCTION aria_get_compaction_candidates(
    p_user_id TEXT DEFAULT 'damon',
    p_min_age_days INT DEFAULT 90,
    p_max_retrieval_count INT DEFAULT 5
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ,
    retrieval_count INT,
    age_days INT
) AS $$
DECLARE
    v_conversation_id UUID;
BEGIN
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    RETURN QUERY
    SELECT
        c.id as chunk_id,
        c.content,
        c.summary,
        c.created_at,
        c.retrieval_count,
        EXTRACT(DAY FROM NOW() - c.created_at)::INT as age_days
    FROM aria_chunks c
    WHERE c.conversation_id = v_conversation_id
      AND c.is_compacted = FALSE
      AND c.created_at < NOW() - (p_min_age_days || ' days')::INTERVAL
      AND c.retrieval_count <= p_max_retrieval_count
    ORDER BY c.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Compact multiple chunks into one
CREATE OR REPLACE FUNCTION aria_compact_chunks(
    p_chunk_ids UUID[],
    p_summary TEXT,
    p_token_count INT,
    p_key_info JSONB DEFAULT '{}'::JSONB
) RETURNS UUID AS $$
DECLARE
    v_conversation_id UUID;
    v_compacted_chunk_id UUID;
    v_total_messages INT;
    v_min_sequence INT;
    v_max_sequence INT;
BEGIN
    -- Get conversation from first chunk
    SELECT conversation_id INTO v_conversation_id
    FROM aria_chunks WHERE id = p_chunk_ids[1];

    -- Get aggregate stats
    SELECT
        SUM(message_count)::INT,
        MIN(start_sequence),
        MAX(end_sequence)
    INTO v_total_messages, v_min_sequence, v_max_sequence
    FROM aria_chunks
    WHERE id = ANY(p_chunk_ids);

    -- Create compacted chunk
    INSERT INTO aria_chunks (
        conversation_id, content, summary, token_count, message_count,
        start_sequence, end_sequence, is_compacted, source_chunk_ids,
        compacted_at, key_entities
    )
    VALUES (
        v_conversation_id, p_summary, p_summary, p_token_count, v_total_messages,
        v_min_sequence, v_max_sequence, TRUE, p_chunk_ids,
        NOW(), p_key_info
    )
    RETURNING id INTO v_compacted_chunk_id;

    -- Delete old chunks (embeddings cascade)
    DELETE FROM aria_chunks WHERE id = ANY(p_chunk_ids);

    RETURN v_compacted_chunk_id;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- VIEWS
-- ==========================================

-- View: Unified conversation with buffer stats
CREATE OR REPLACE VIEW aria_unified_stream_overview AS
SELECT
    c.id as conversation_id,
    c.session_id,
    COALESCE(c.total_messages, 0) as total_messages,
    COALESCE(c.total_chunks, 0) as total_chunks,
    c.last_message_at,
    c.created_at,
    c.threading_settings,
    (SELECT COUNT(*) FROM aria_messages m WHERE m.conversation_id = c.id AND m.chunk_id IS NULL) as buffer_messages,
    (SELECT COALESCE(SUM(COALESCE(token_count, input_tokens)), 0) FROM aria_messages m WHERE m.conversation_id = c.id AND m.chunk_id IS NULL) as buffer_tokens,
    (SELECT COUNT(*) FROM aria_extracted_info e WHERE e.conversation_id = c.id AND e.superseded_by IS NULL) as active_extracted_info
FROM aria_conversations c
WHERE c.session_id LIKE 'unified-%';

-- View: Chunks with embedding status
CREATE OR REPLACE VIEW aria_chunks_overview AS
SELECT
    c.id as chunk_id,
    c.conversation_id,
    c.message_count,
    c.token_count,
    c.created_at,
    c.is_compacted,
    c.retrieval_count,
    c.last_retrieved_at,
    c.importance_score,
    c.topics,
    e.id IS NOT NULL as has_embedding,
    LEFT(c.summary, 100) as summary_preview
FROM aria_chunks c
LEFT JOIN aria_chunk_embeddings e ON e.chunk_id = c.id
ORDER BY c.created_at DESC;

-- ==========================================
-- GRANTS
-- ==========================================

GRANT ALL ON aria_chunks TO anon, authenticated, service_role;
GRANT ALL ON aria_chunk_embeddings TO anon, authenticated, service_role;
GRANT ALL ON aria_extracted_info TO anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

-- ==========================================
-- MIGRATION COMPLETE
-- ==========================================
--
-- Extended tables:
--   - aria_conversations (added threading settings, stats)
--   - aria_messages (added chunk_id, sequence_num, token_count)
--
-- New tables:
--   - aria_chunks (archived conversation segments)
--   - aria_chunk_embeddings (vector storage for chunks)
--   - aria_extracted_info (decisions, preferences, facts)
--
-- Key functions:
--   - aria_get_unified_conversation()
--   - aria_stream_add_message()
--   - aria_get_primary_buffer()
--   - aria_create_chunk()
--   - aria_store_chunk_embedding()
--   - aria_semantic_search()
--   - aria_extract_info()
--   - aria_compact_chunks()
--
-- Next steps:
--   1. Run this migration on DEV Supabase
--   2. Build Python service for chunking/embedding
--   3. Integrate with ARIA workflow
-- ==========================================
