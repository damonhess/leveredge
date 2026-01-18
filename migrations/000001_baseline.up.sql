-- Migration 000001: Baseline
-- Documents existing shared schema as of January 18, 2026
-- Both DEV and PROD already have these tables

-- Core ARIA tables
CREATE TABLE IF NOT EXISTS aria_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    source TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    UNIQUE(category, key)
);

CREATE TABLE IF NOT EXISTS aria_wins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    value_low DECIMAL(10,2),
    value_high DECIMAL(10,2),
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    tags JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS aria_portfolio_summary (
    id SERIAL PRIMARY KEY,
    total_wins INT,
    total_value_low DECIMAL(12,2),
    total_value_high DECIMAL(12,2),
    categories JSONB,
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS aria_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    message_count INT DEFAULT 0,
    context JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS aria_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES aria_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    tokens_used INT,
    model TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'
);

-- LLM usage tracking
CREATE TABLE IF NOT EXISTS llm_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INT NOT NULL,
    output_tokens INT NOT NULL,
    estimated_cost_usd DECIMAL(10,6),
    context TEXT,
    operation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- N8N chat histories
CREATE TABLE IF NOT EXISTS n8n_chat_histories (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    message JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent usage logs (PROD-specific but valuable)
CREATE TABLE IF NOT EXISTS agent_usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    input_data JSONB,
    output_data JSONB,
    duration_ms INT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- LLM budget alerts
CREATE TABLE IF NOT EXISTS llm_budget_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type TEXT NOT NULL,
    threshold DECIMAL(10,2),
    current_value DECIMAL(10,2),
    message TEXT,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for baseline tables
CREATE INDEX IF NOT EXISTS idx_aria_knowledge_category ON aria_knowledge(category);
CREATE INDEX IF NOT EXISTS idx_aria_knowledge_key ON aria_knowledge(key);
CREATE INDEX IF NOT EXISTS idx_aria_wins_category ON aria_wins(category);
CREATE INDEX IF NOT EXISTS idx_aria_wins_completed ON aria_wins(completed_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_agent ON llm_usage(agent_name);
CREATE INDEX IF NOT EXISTS idx_llm_usage_created ON llm_usage(created_at);
CREATE INDEX IF NOT EXISTS idx_aria_messages_conversation ON aria_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_n8n_chat_session ON n8n_chat_histories(session_id);

SELECT 'Baseline migration complete' as status;
