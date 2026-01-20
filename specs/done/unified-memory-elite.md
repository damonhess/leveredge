# UNIFIED MEMORY ELITE - Complete Memory Architecture

## EXECUTIVE SUMMARY

This spec upgrades ARIA's memory from "basic storage" to "elite cognitive architecture" by integrating three systems into one seamless memory layer:

| System | Purpose | Current State | After This Spec |
|--------|---------|---------------|-----------------|
| **Unified Memory** | Cross-session facts, preferences, decisions | Storage only, no retrieval | Full semantic search + consolidation |
| **Unified Threading** | In-conversation context management | Building | Integrated with cross-session memory |
| **Async Multitasking** | Background task results | Built | Results feed into memory automatically |

**End Goal:** ARIA remembers EVERYTHING - across sessions, interfaces, and time. When you mention something once, ARIA knows it forever.

---

## THE VISION

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    ARIA                                          │
│                                                                                  │
│  "Hey ARIA, what did we decide about pricing?"                                  │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      CONTEXT ASSEMBLER                                   │   │
│  │                   (Single entry point for all memory)                    │   │
│  │                                                                          │   │
│  │  Input: User message + current conversation                              │   │
│  │  Output: Perfectly curated context from ALL memory sources               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                     │                                           │
│           ┌─────────────────────────┼─────────────────────────┐                │
│           │                         │                         │                │
│           ▼                         ▼                         ▼                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐           │
│  │ UNIFIED MEMORY  │    │    UNIFIED      │    │     ASYNC       │           │
│  │                 │    │   THREADING     │    │  MULTITASKING   │           │
│  │ • Facts         │    │                 │    │                 │           │
│  │ • Preferences   │    │ • Recent msgs   │    │ • Task results  │           │
│  │ • Decisions     │    │ • Semantic      │    │ • Research      │           │
│  │ • Commitments   │    │   chunks        │    │ • Analysis      │           │
│  │ • Relationships │    │ • Extracted     │    │                 │           │
│  │                 │    │   insights      │    │                 │           │
│  │ CROSS-SESSION   │    │ IN-SESSION      │    │ BACKGROUND      │           │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘           │
│           │                         │                         │                │
│           └─────────────────────────┴─────────────────────────┘                │
│                                     │                                           │
│                                     ▼                                           │
│                          ┌───────────────────┐                                 │
│                          │  MEMORY EVENTS    │                                 │
│                          │  (Event Bus)      │                                 │
│                          │                   │                                 │
│                          │ • memory.stored   │                                 │
│                          │ • memory.updated  │                                 │
│                          │ • memory.conflict │                                 │
│                          │ • memory.expired  │                                 │
│                          └───────────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## PART 1: UNIFIED MEMORY V2 (Cross-Session)

### Current Problems
1. ❌ No embeddings - can't search semantically
2. ❌ No retrieval workflow - data goes in, never comes out
3. ❌ No consolidation - duplicate/conflicting facts pile up
4. ❌ No decay - ancient irrelevant facts clutter searches
5. ❌ No sourcing - can't trace where a memory came from

### Upgraded Schema

```sql
-- Drop and recreate with full features
DROP TABLE IF EXISTS aria_unified_memory CASCADE;

CREATE TABLE aria_unified_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Content
    memory_type TEXT NOT NULL,  -- fact, preference, decision, commitment, relationship, insight
    category TEXT,  -- business, personal, technical, health, financial, etc.
    content TEXT NOT NULL,
    summary TEXT,  -- One-line summary for quick scanning
    
    -- Semantic Search
    embedding vector(1536),  -- OpenAI ada-002
    keywords TEXT[],  -- Extracted keywords for hybrid search
    
    -- Source Tracking
    source_type TEXT NOT NULL,  -- conversation, task_result, manual, import
    source_conversation_id UUID REFERENCES aria_conversations(id) ON DELETE SET NULL,
    source_message_id UUID REFERENCES aria_messages(id) ON DELETE SET NULL,
    source_task_id UUID REFERENCES aria_async_tasks(id) ON DELETE SET NULL,
    source_interface TEXT,  -- web, telegram, cli, api
    
    -- Confidence & Validity
    confidence FLOAT DEFAULT 1.0,  -- 0.0-1.0, decays over time if not reinforced
    is_active BOOLEAN DEFAULT TRUE,
    superseded_by UUID REFERENCES aria_unified_memory(id),
    supersedes UUID REFERENCES aria_unified_memory(id),
    
    -- Temporal
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ,
    access_count INT DEFAULT 0,
    expires_at TIMESTAMPTZ,  -- For commitments with deadlines
    
    -- Privacy (inherited from async multitasking)
    privacy_level TEXT DEFAULT 'normal',  -- normal, private, ephemeral
    
    -- Relationships
    related_memories UUID[],  -- Links to related memories
    tags TEXT[]
);

-- Indexes for fast retrieval
CREATE INDEX idx_memory_embedding ON aria_unified_memory 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_memory_type ON aria_unified_memory(memory_type);
CREATE INDEX idx_memory_category ON aria_unified_memory(category);
CREATE INDEX idx_memory_active ON aria_unified_memory(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_memory_keywords ON aria_unified_memory USING gin(keywords);
CREATE INDEX idx_memory_tags ON aria_unified_memory USING gin(tags);
CREATE INDEX idx_memory_source_conv ON aria_unified_memory(source_conversation_id);
CREATE INDEX idx_memory_source_task ON aria_unified_memory(source_task_id);
CREATE INDEX idx_memory_confidence ON aria_unified_memory(confidence DESC);
CREATE INDEX idx_memory_accessed ON aria_unified_memory(last_accessed_at DESC);

-- Memory relationships table (for complex connections)
CREATE TABLE aria_memory_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_memory_id UUID NOT NULL REFERENCES aria_unified_memory(id) ON DELETE CASCADE,
    target_memory_id UUID NOT NULL REFERENCES aria_unified_memory(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,  -- contradicts, supports, elaborates, supersedes, related_to
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_memory_id, target_memory_id, relationship_type)
);

CREATE INDEX idx_memory_rel_source ON aria_memory_relationships(source_memory_id);
CREATE INDEX idx_memory_rel_target ON aria_memory_relationships(target_memory_id);
CREATE INDEX idx_memory_rel_type ON aria_memory_relationships(relationship_type);
```

### Memory Types

| Type | Description | Example | Decay Rate |
|------|-------------|---------|------------|
| `fact` | Objective information | "Damon's birthday is March 15" | Never |
| `preference` | Personal preferences | "Prefers detailed explanations" | Slow (6 months) |
| `decision` | Choices made | "Decided to focus on compliance professionals" | Never |
| `commitment` | Promises/plans | "Will launch by March 1, 2026" | Until expires |
| `relationship` | People/entity connections | "John is Damon's mentor" | Slow |
| `insight` | Learned patterns | "Gets distracted when tired" | Medium (3 months) |
| `context` | Situational info | "Currently in JUGGERNAUT mode" | Fast (1 week) |

### Memory Functions

```sql
-- Store a new memory with embedding
CREATE OR REPLACE FUNCTION aria_store_memory(
    p_memory_type TEXT,
    p_content TEXT,
    p_category TEXT DEFAULT NULL,
    p_source_type TEXT DEFAULT 'conversation',
    p_source_conversation_id UUID DEFAULT NULL,
    p_source_message_id UUID DEFAULT NULL,
    p_source_task_id UUID DEFAULT NULL,
    p_source_interface TEXT DEFAULT 'web',
    p_confidence FLOAT DEFAULT 1.0,
    p_keywords TEXT[] DEFAULT '{}',
    p_tags TEXT[] DEFAULT '{}',
    p_privacy_level TEXT DEFAULT 'normal',
    p_expires_at TIMESTAMPTZ DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_memory_id UUID;
    v_summary TEXT;
BEGIN
    -- Generate one-line summary (will be done by AI in workflow)
    v_summary := LEFT(p_content, 100);
    
    INSERT INTO aria_unified_memory (
        memory_type, content, summary, category,
        source_type, source_conversation_id, source_message_id, source_task_id, source_interface,
        confidence, keywords, tags, privacy_level, expires_at
    ) VALUES (
        p_memory_type, p_content, v_summary, p_category,
        p_source_type, p_source_conversation_id, p_source_message_id, p_source_task_id, p_source_interface,
        p_confidence, p_keywords, p_tags, p_privacy_level, p_expires_at
    )
    RETURNING id INTO v_memory_id;
    
    RETURN v_memory_id;
END;
$$ LANGUAGE plpgsql;

-- Search memories semantically
CREATE OR REPLACE FUNCTION aria_search_memory(
    p_query_embedding vector(1536),
    p_memory_types TEXT[] DEFAULT NULL,
    p_categories TEXT[] DEFAULT NULL,
    p_min_confidence FLOAT DEFAULT 0.5,
    p_limit INT DEFAULT 10,
    p_include_private BOOLEAN DEFAULT FALSE
) RETURNS TABLE (
    id UUID,
    memory_type TEXT,
    category TEXT,
    content TEXT,
    summary TEXT,
    confidence FLOAT,
    similarity FLOAT,
    created_at TIMESTAMPTZ,
    source_type TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        m.id,
        m.memory_type,
        m.category,
        m.content,
        m.summary,
        m.confidence,
        1 - (m.embedding <=> p_query_embedding) AS similarity,
        m.created_at,
        m.source_type
    FROM aria_unified_memory m
    WHERE m.is_active = TRUE
      AND m.embedding IS NOT NULL
      AND m.confidence >= p_min_confidence
      AND (p_memory_types IS NULL OR m.memory_type = ANY(p_memory_types))
      AND (p_categories IS NULL OR m.category = ANY(p_categories))
      AND (p_include_private OR m.privacy_level = 'normal')
    ORDER BY m.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Hybrid search (semantic + keyword)
CREATE OR REPLACE FUNCTION aria_hybrid_search_memory(
    p_query_embedding vector(1536),
    p_keywords TEXT[],
    p_memory_types TEXT[] DEFAULT NULL,
    p_limit INT DEFAULT 10
) RETURNS TABLE (
    id UUID,
    memory_type TEXT,
    content TEXT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_results AS (
        SELECT 
            m.id,
            m.memory_type,
            m.content,
            1 - (m.embedding <=> p_query_embedding) AS semantic_score
        FROM aria_unified_memory m
        WHERE m.is_active = TRUE AND m.embedding IS NOT NULL
        ORDER BY m.embedding <=> p_query_embedding
        LIMIT p_limit * 2
    ),
    keyword_results AS (
        SELECT 
            m.id,
            m.memory_type,
            m.content,
            CASE WHEN m.keywords && p_keywords THEN 0.3 ELSE 0.0 END AS keyword_score
        FROM aria_unified_memory m
        WHERE m.is_active = TRUE
          AND (m.keywords && p_keywords OR m.content ILIKE ANY(
              SELECT '%' || unnest(p_keywords) || '%'
          ))
    )
    SELECT 
        COALESCE(s.id, k.id) AS id,
        COALESCE(s.memory_type, k.memory_type) AS memory_type,
        COALESCE(s.content, k.content) AS content,
        COALESCE(s.semantic_score, 0) * 0.7 + COALESCE(k.keyword_score, 0) * 0.3 AS combined_score
    FROM semantic_results s
    FULL OUTER JOIN keyword_results k ON s.id = k.id
    ORDER BY combined_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Update memory access stats (for relevance decay)
CREATE OR REPLACE FUNCTION aria_touch_memory(p_memory_id UUID) RETURNS void AS $$
BEGIN
    UPDATE aria_unified_memory
    SET last_accessed_at = NOW(),
        access_count = access_count + 1
    WHERE id = p_memory_id;
END;
$$ LANGUAGE plpgsql;

-- Find and resolve conflicts
CREATE OR REPLACE FUNCTION aria_find_conflicts(p_memory_id UUID) RETURNS TABLE (
    conflicting_id UUID,
    conflict_type TEXT,
    content TEXT
) AS $$
DECLARE
    v_memory RECORD;
BEGIN
    SELECT * INTO v_memory FROM aria_unified_memory WHERE id = p_memory_id;
    
    RETURN QUERY
    SELECT 
        m.id AS conflicting_id,
        CASE 
            WHEN m.memory_type = v_memory.memory_type 
                 AND m.category = v_memory.category 
                 AND 1 - (m.embedding <=> v_memory.embedding) > 0.85
            THEN 'potential_duplicate'
            WHEN m.memory_type = v_memory.memory_type
                 AND m.category = v_memory.category
                 AND 1 - (m.embedding <=> v_memory.embedding) > 0.7
            THEN 'related'
            ELSE 'unknown'
        END AS conflict_type,
        m.content
    FROM aria_unified_memory m
    WHERE m.id != p_memory_id
      AND m.is_active = TRUE
      AND m.memory_type = v_memory.memory_type
      AND m.embedding IS NOT NULL
      AND 1 - (m.embedding <=> v_memory.embedding) > 0.7
    ORDER BY m.embedding <=> v_memory.embedding
    LIMIT 5;
END;
$$ LANGUAGE plpgsql;

-- Confidence decay function (run periodically)
CREATE OR REPLACE FUNCTION aria_decay_confidence() RETURNS void AS $$
BEGIN
    -- Decay context memories quickly (lose 10% per week if not accessed)
    UPDATE aria_unified_memory
    SET confidence = confidence * 0.9
    WHERE memory_type = 'context'
      AND last_accessed_at < NOW() - INTERVAL '7 days'
      AND confidence > 0.1;
    
    -- Decay insights slowly (lose 5% per month if not accessed)
    UPDATE aria_unified_memory
    SET confidence = confidence * 0.95
    WHERE memory_type = 'insight'
      AND last_accessed_at < NOW() - INTERVAL '30 days'
      AND confidence > 0.3;
    
    -- Decay preferences very slowly (lose 2% per 6 months if not accessed)
    UPDATE aria_unified_memory
    SET confidence = confidence * 0.98
    WHERE memory_type = 'preference'
      AND last_accessed_at < NOW() - INTERVAL '180 days'
      AND confidence > 0.5;
    
    -- Deactivate very low confidence memories
    UPDATE aria_unified_memory
    SET is_active = FALSE
    WHERE confidence < 0.1
      AND memory_type NOT IN ('fact', 'decision');
    
    -- Expire commitments past their deadline
    UPDATE aria_unified_memory
    SET is_active = FALSE
    WHERE memory_type = 'commitment'
      AND expires_at IS NOT NULL
      AND expires_at < NOW();
END;
$$ LANGUAGE plpgsql;
```

---

## PART 2: ASYNC MULTITASKING RETROFIT

### Current Problems
1. ❌ Task results live in isolation - not feeding into memory
2. ❌ No extraction of facts/decisions from research results
3. ❌ Task history not searchable semantically

### Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    ASYNC TASK COMPLETES                          │
│                                                                  │
│  Task Result: "Compliance automation market is $4.2B..."        │
│                           │                                      │
│                           ▼                                      │
│              ┌────────────────────────┐                         │
│              │   MEMORY EXTRACTOR     │                         │
│              │                        │                         │
│              │   LLM extracts:        │                         │
│              │   • Facts              │                         │
│              │   • Insights           │                         │
│              │   • Decisions needed   │                         │
│              └───────────┬────────────┘                         │
│                          │                                       │
│           ┌──────────────┼──────────────┐                       │
│           ▼              ▼              ▼                       │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│   │ Store Fact  │ │Store Insight│ │Flag Decision│              │
│   │             │ │             │ │   Needed    │              │
│   │ "Market is  │ │ "Key pain   │ │ "Need to    │              │
│   │  $4.2B"     │ │  point:     │ │  decide on  │              │
│   │             │ │  audit prep"│ │  pricing"   │              │
│   └─────────────┘ └─────────────┘ └─────────────┘              │
│           │              │              │                       │
│           └──────────────┴──────────────┘                       │
│                          │                                       │
│                          ▼                                       │
│              ┌────────────────────────┐                         │
│              │   UNIFIED MEMORY       │                         │
│              │   (with source_task_id)│                         │
│              └────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### New Workflow: Task Result Extractor

```yaml
name: "33 - Task Result Extractor"
trigger: Event Bus (aria.task.completed)

nodes:
  1. Event Bus Trigger (aria.task.completed)
  2. Get Full Task Details (Supabase query)
  3. Skip if ephemeral (privacy check)
  4. AI Memory Extractor:
     prompt: |
       Analyze this task result and extract memories to store:
       
       Task Type: {{ task_type }}
       Input: {{ input }}
       Output: {{ output }}
       
       Extract and categorize:
       1. FACTS - Objective information (numbers, dates, names)
       2. INSIGHTS - Patterns, observations, learnings
       3. DECISIONS_NEEDED - Choices that should be made based on this
       
       Return JSON:
       {
         "facts": [{"content": "...", "category": "...", "confidence": 0.9}],
         "insights": [{"content": "...", "category": "...", "confidence": 0.8}],
         "decisions_needed": [{"content": "...", "urgency": "high|medium|low"}]
       }
  5. Loop: Store each extracted memory
  6. Generate embeddings (OpenAI)
  7. Store in aria_unified_memory (with source_task_id)
  8. Check for conflicts
  9. Publish: memory.stored events
```

### Schema Addition for Async Tasks

```sql
-- Add memory extraction tracking to async tasks
ALTER TABLE aria_async_tasks ADD COLUMN IF NOT EXISTS 
    memories_extracted BOOLEAN DEFAULT FALSE;
ALTER TABLE aria_async_tasks ADD COLUMN IF NOT EXISTS 
    extracted_memory_ids UUID[];

-- Index for finding unextracted tasks
CREATE INDEX IF NOT EXISTS idx_tasks_unextracted 
    ON aria_async_tasks(memories_extracted) 
    WHERE memories_extracted = FALSE AND status = 'delivered';
```

---

## PART 3: UNIFIED THREADING INTEGRATION

### Current Design Issue
Unified Threading manages in-session context but doesn't query cross-session memory.

### Integration: Context Assembly Before LLM Call

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER MESSAGE ARRIVES                          │
│                                                                  │
│  "What pricing should I use for compliance clients?"            │
│                           │                                      │
│                           ▼                                      │
│              ┌────────────────────────┐                         │
│              │   CONTEXT ASSEMBLER    │                         │
│              │   (NEW - Central Hub)  │                         │
│              └───────────┬────────────┘                         │
│                          │                                       │
│     ┌────────────────────┼────────────────────┐                 │
│     │                    │                    │                 │
│     ▼                    ▼                    ▼                 │
│ ┌────────┐         ┌────────┐         ┌────────┐              │
│ │UNIFIED │         │UNIFIED │         │ ASYNC  │              │
│ │THREADING│        │MEMORY  │         │ TASKS  │              │
│ │        │         │        │         │        │              │
│ │Recent  │         │Cross-  │         │Pending │              │
│ │messages│         │session │         │results │              │
│ │+ chunks│         │facts   │         │        │              │
│ └───┬────┘         └───┬────┘         └───┬────┘              │
│     │                  │                  │                    │
│     │ 2000 tokens      │ 1500 tokens      │ 500 tokens        │
│     │                  │                  │                    │
│     └──────────────────┼──────────────────┘                    │
│                        │                                        │
│                        ▼                                        │
│              ┌────────────────────────┐                         │
│              │   ASSEMBLED CONTEXT    │                         │
│              │   (4000 tokens max)    │                         │
│              │                        │                         │
│              │ [Recent conversation]  │                         │
│              │ [Relevant memories]    │                         │
│              │ [Pending task status]  │                         │
│              └───────────┬────────────┘                         │
│                          │                                       │
│                          ▼                                       │
│              ┌────────────────────────┐                         │
│              │        LLM CALL        │                         │
│              └────────────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### Context Assembler Function

```sql
CREATE OR REPLACE FUNCTION aria_assemble_context(
    p_user_id TEXT,
    p_query TEXT,
    p_query_embedding vector(1536),
    p_total_budget INT DEFAULT 4000,
    p_include_private BOOLEAN DEFAULT FALSE
) RETURNS JSONB AS $$
DECLARE
    v_result JSONB;
    v_conversation_id UUID;
    v_recent_messages JSONB;
    v_relevant_memories JSONB;
    v_pending_tasks JSONB;
    v_recent_budget INT;
    v_memory_budget INT;
    v_task_budget INT;
BEGIN
    -- Budget allocation (adjust based on query type)
    v_recent_budget := (p_total_budget * 0.5)::INT;  -- 50% for recent conversation
    v_memory_budget := (p_total_budget * 0.35)::INT; -- 35% for cross-session memory
    v_task_budget := (p_total_budget * 0.15)::INT;   -- 15% for pending tasks

    -- Get unified conversation ID
    v_conversation_id := aria_get_unified_conversation(p_user_id);

    -- 1. Recent conversation (from Unified Threading)
    SELECT jsonb_agg(msg ORDER BY sequence_num DESC)
    INTO v_recent_messages
    FROM (
        SELECT role, content, sequence_num
        FROM aria_messages
        WHERE conversation_id = v_conversation_id
          AND chunk_id IS NULL  -- Primary buffer only
        ORDER BY sequence_num DESC
        LIMIT 20
    ) msg;

    -- 2. Relevant cross-session memories (from Unified Memory)
    SELECT jsonb_agg(mem)
    INTO v_relevant_memories
    FROM (
        SELECT 
            memory_type,
            content,
            confidence,
            1 - (embedding <=> p_query_embedding) AS relevance
        FROM aria_unified_memory
        WHERE is_active = TRUE
          AND embedding IS NOT NULL
          AND (p_include_private OR privacy_level = 'normal')
        ORDER BY embedding <=> p_query_embedding
        LIMIT 10
    ) mem
    WHERE relevance > 0.7;  -- Only highly relevant memories

    -- 3. Pending async tasks
    SELECT jsonb_agg(task)
    INTO v_pending_tasks
    FROM (
        SELECT 
            task_type,
            status,
            progress,
            progress_message,
            CASE WHEN status = 'complete' THEN output ELSE NULL END AS result_preview
        FROM aria_async_tasks
        WHERE user_id = p_user_id
          AND status IN ('pending', 'running', 'complete')
          AND (delivered_at IS NULL OR delivered_at > NOW() - INTERVAL '1 hour')
          AND (p_include_private OR privacy_level = 'normal')
        ORDER BY created_at DESC
        LIMIT 5
    ) task;

    -- Assemble result
    v_result := jsonb_build_object(
        'recent_conversation', COALESCE(v_recent_messages, '[]'::jsonb),
        'relevant_memories', COALESCE(v_relevant_memories, '[]'::jsonb),
        'pending_tasks', COALESCE(v_pending_tasks, '[]'::jsonb),
        'budget_used', jsonb_build_object(
            'recent', v_recent_budget,
            'memory', v_memory_budget,
            'tasks', v_task_budget
        )
    );

    RETURN v_result;
END;
$$ LANGUAGE plpgsql;
```

---

## PART 4: MEMORY CONSOLIDATION ENGINE

### The Problem
Over time, memories accumulate:
- Duplicates ("Damon likes detailed explanations" stored 50 times)
- Contradictions ("Focus on compliance" vs "Focus on legal")
- Outdated info ("Currently building ARIA" when ARIA is done)

### Consolidation Workflow

```yaml
name: "34 - Memory Consolidation"
trigger: Scheduled (daily at 3 AM)

steps:
  1. Find duplicate candidates:
     - Same memory_type
     - Embedding similarity > 0.85
     - Both active
     
  2. For each duplicate pair:
     - AI merges into single authoritative memory
     - Mark older as superseded_by newer
     - Keep higher confidence
     
  3. Find contradictions:
     - Same memory_type + category
     - Embedding similarity > 0.7 but < 0.85
     - AI determines if truly contradictory
     
  4. For contradictions:
     - Flag for user review OR
     - Auto-resolve based on recency + confidence
     
  5. Update outdated context:
     - Find "currently" statements older than 7 days
     - Mark as inactive or update
     
  6. Report:
     - Memories consolidated: X
     - Contradictions found: Y
     - Outdated marked: Z
```

### AI Consolidation Prompt

```
You are a memory consolidation engine. Given these potentially duplicate memories:

Memory A (created: {date_a}, accessed: {accessed_a}, confidence: {conf_a}):
"{content_a}"

Memory B (created: {date_b}, accessed: {accessed_b}, confidence: {conf_b}):
"{content_b}"

Determine:
1. Are these true duplicates? (same information, different wording)
2. Does one supersede the other? (updated information)
3. Are they complementary? (can be merged)
4. Are they contradictory? (conflict)

Return JSON:
{
  "relationship": "duplicate|supersedes|complementary|contradictory|unrelated",
  "action": "merge|keep_newer|keep_both|flag_for_review",
  "merged_content": "...",  // If merging
  "confidence": 0.9,
  "reasoning": "..."
}
```

---

## PART 5: ARIA INTEGRATION

### New ARIA Tools

```yaml
# Memory Search Tool
- name: search_memory
  description: "Search your memory for relevant information across all past conversations and tasks"
  params:
    query: string
    memory_types: array (optional) # fact, preference, decision, etc.
    categories: array (optional)
    limit: int (default 5)
  triggers:
    - "what do you remember about..."
    - "did I ever mention..."
    - "what did we decide about..."

# Memory Store Tool  
- name: store_memory
  description: "Explicitly store something important to remember"
  params:
    content: string
    memory_type: string
    category: string (optional)
    expires_at: datetime (optional)
  triggers:
    - "remember that..."
    - "note that..."
    - "don't forget..."

# Memory Update Tool
- name: update_memory
  description: "Update or correct a stored memory"
  params:
    memory_id: string (optional, finds by content if not provided)
    new_content: string
    reason: string
  triggers:
    - "actually, it's..."
    - "I was wrong about..."
    - "update my preference..."

# Memory Forget Tool
- name: forget_memory
  description: "Mark a memory as inactive (soft delete)"
  params:
    memory_id: string (optional)
    content_match: string (optional)
    confirm: boolean
  triggers:
    - "forget about..."
    - "that's no longer true..."
    - "delete the memory about..."
```

### Automatic Memory Extraction

After every ARIA response, extract potential memories:

```yaml
# In ARIA main workflow, after AI response:

Post-Response Memory Extraction:
  1. AI analyzes conversation turn
  2. Extracts:
     - New facts mentioned by user
     - Decisions made
     - Preferences expressed
     - Commitments made
  3. For each extraction:
     - Generate embedding
     - Check for conflicts
     - Store if confident
  4. Silent (user doesn't see this)
```

### Memory Injection Prompt

Add to ARIA's system prompt:

```
## Your Memory

You have access to memories from past conversations. Relevant memories for this conversation:

### Facts You Know
{facts_list}

### User Preferences  
{preferences_list}

### Recent Decisions
{decisions_list}

### Active Commitments
{commitments_list}

Use these naturally - don't announce "I remember that..." unless specifically asked. Just know things.

If information seems outdated or contradictory, you can:
- Ask for clarification
- Update your memory with the new information
- Note the change
```

---

## PART 6: EVENT BUS INTEGRATION

### Memory Events

```yaml
# Published events
memory.stored:
  memory_id: uuid
  memory_type: string
  source_type: string
  
memory.updated:
  memory_id: uuid
  old_content: string
  new_content: string
  reason: string

memory.conflict_detected:
  memory_ids: [uuid, uuid]
  conflict_type: string
  requires_review: boolean

memory.consolidated:
  merged_into: uuid
  superseded: [uuid]
  
memory.expired:
  memory_id: uuid
  memory_type: string

# Subscribed events
aria.task.completed → Trigger memory extraction
aria.conversation.ended → Trigger memory consolidation check
```

---

## PART 7: IMPLEMENTATION ORDER

### Phase 1: Unified Memory V2 (6-8 hours)
| # | Task | Effort |
|---|------|--------|
| 1 | New schema + migration | 1 hr |
| 2 | Memory functions (store, search, hybrid) | 2 hrs |
| 3 | Embedding generation workflow | 1 hr |
| 4 | Memory search workflow | 1 hr |
| 5 | ARIA tools (search, store, update, forget) | 2 hrs |
| 6 | Testing | 1 hr |

### Phase 2: Async Retrofit (4-5 hours)
| # | Task | Effort |
|---|------|--------|
| 7 | Task Result Extractor workflow | 2 hrs |
| 8 | Schema additions | 30 min |
| 9 | Backfill existing task results | 1 hr |
| 10 | Event Bus integration | 1 hr |
| 11 | Testing | 30 min |

### Phase 3: Context Assembler (4-5 hours)
| # | Task | Effort |
|---|------|--------|
| 12 | Context assembler function | 1.5 hrs |
| 13 | ARIA integration (inject context) | 2 hrs |
| 14 | Budget tuning | 1 hr |
| 15 | Testing end-to-end | 1 hr |

### Phase 4: Consolidation Engine (4-5 hours)
| # | Task | Effort |
|---|------|--------|
| 16 | Consolidation workflow | 2 hrs |
| 17 | Conflict detection | 1 hr |
| 18 | Auto-resolution logic | 1 hr |
| 19 | Reporting/notifications | 30 min |
| 20 | Testing | 30 min |

### Phase 5: Polish & Integration (3-4 hours)
| # | Task | Effort |
|---|------|--------|
| 21 | Memory injection in ARIA prompt | 1 hr |
| 22 | Automatic extraction after responses | 1.5 hrs |
| 23 | Privacy enforcement across all systems | 1 hr |
| 24 | Final integration testing | 1 hr |

**Total Effort:** ~22-27 hours

---

## PART 8: SUCCESS METRICS

### Functional
- [ ] Memory search returns relevant results in < 500ms
- [ ] Cross-session facts surface automatically
- [ ] Task results feed into memory within 30 seconds
- [ ] Context assembly completes in < 1 second
- [ ] Duplicates reduced by 80% after consolidation

### Quality
- [ ] ARIA correctly recalls facts from 30+ days ago
- [ ] No "I don't remember" when memory exists
- [ ] Contradictions flagged or auto-resolved
- [ ] User preferences persist across sessions
- [ ] Decisions are never forgotten

### User Experience
- [ ] "It just knows" feeling
- [ ] No need to repeat information
- [ ] Seamless cross-interface continuity
- [ ] Privacy respected (private memories stay private)

---

## PART 9: EXAMPLE FLOWS

### Flow 1: Natural Memory Recall

```
[Session 1 - January 10]
User: "I've decided to price my Tier 1 services at $500-2500"

ARIA: [Extracts decision, stores in memory]
      "Got it - Tier 1 at $500-2,500. That aligns well with the market 
       research showing entry-level automation typically runs $300-3,000."

[Session 2 - January 20]
User: "A prospect asked about pricing"

ARIA: [Context assembler finds pricing decision]
      "Your Tier 1 services are priced at $500-2,500. For this specific 
       prospect, I'd recommend starting with $1,500 based on their 
       company size..."
```

### Flow 2: Task Result → Memory

```
User: "Research compliance software market size"

ARIA: "🔄 Dispatching SCHOLAR for research..."

[Task completes]

ARIA: "📊 Research complete! The compliance software market is valued at 
       $4.2B, growing 23% YoY. Key players include ServiceNow, Workiva..."

[Behind the scenes - Memory Extractor runs]
Stored memories:
- FACT: "Compliance software market size is $4.2B (2026)"
- FACT: "Compliance market growth rate is 23% YoY"
- FACT: "Key compliance software players: ServiceNow, Workiva, LogicGate"

[Next session]
User: "How big is the market I'm entering?"

ARIA: [Finds market size fact]
      "The compliance software market is $4.2B and growing at 23% annually..."
```

### Flow 3: Memory Consolidation

```
[Memory store has:]
- "Damon prefers detailed technical explanations" (Jan 5)
- "User likes comprehensive explanations" (Jan 8) 
- "Prefers thorough, detailed responses" (Jan 12)

[Consolidation runs at 3 AM]

AI Analysis: These are duplicates expressing same preference

Merged memory: "User prefers detailed, comprehensive technical explanations"
- Supersedes the 3 original memories
- Confidence: 0.95 (reinforced multiple times)
- Access count: combined from all 3
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/unified-memory-elite.md

Context: Build elite unified memory architecture. This integrates Unified Memory (cross-session), Unified Threading (in-session), and Async Multitasking into one seamless cognitive layer.

Key Components:
1. Unified Memory V2 - Full schema with embeddings, search, consolidation
2. Memory functions (store, search, hybrid search, conflict detection)
3. Async Retrofit - Task Result Extractor workflow
4. Context Assembler - Single function that pulls from all three systems
5. Memory Consolidation Engine - Daily dedup and conflict resolution
6. ARIA Tools - search_memory, store_memory, update_memory, forget_memory
7. Automatic extraction after every conversation turn
8. Event Bus integration for memory events

Dependencies: Unified Threading tables must exist. Async Multitasking tables must exist.

N8N MCP TOOLS: Use n8n-troubleshooter MCP for DEV data plane workflows.
```
