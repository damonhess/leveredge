# UNIFIED THREADING ARCHITECTURE - Specification

## OVERVIEW

Replace multiple separate chat threads with ONE continuous conversation stream that uses smart chunking and semantic retrieval for context management. User should be able to continue ONE conversation indefinitely, with ARIA intelligently retrieving relevant past context on-demand.

**Why This Is Better:**
- 26-90% quality improvement (MemGPT/Mem0 studies)
- 80-90% token reduction while maintaining quality
- Reduced cognitive load for ADHD users
- No context lost between "threads"
- Automatic semantic retrieval vs manual "remember when we..."

**Post-Launch Build** - Not blocking March 1, 2026

---

## CHIRON'S ADHD-OPTIMIZED SPRINT PLAN

**Total Time:** 28 hours | **Target:** 7 days post-launch

### DAY 1 (4 hours) - Research & Architecture
- [ ] Study current ARIA threading implementation (90 min)
- [ ] Design unified stream architecture (90 min)
- [ ] Document semantic chunking strategy (60 min)
- **Done when:** Architecture diagram complete + chunking algorithm defined
- **If stuck:** Study n8n's conversation memory patterns

### DAY 2 (4 hours) - Core Stream Implementation
- [ ] Create unified conversation stream class (2 hrs)
- [ ] Implement basic append/retrieve methods (2 hrs)
- **Done when:** Basic CRUD works - write to stream, read back
- **Quick win:** First message written to unified stream

### DAY 3 (4 hours) - Semantic Chunking Engine
- [ ] Build semantic similarity scorer (1.5 hrs)
- [ ] Implement smart chunking algorithm (2.5 hrs)
- **Done when:** Can chunk by topics, not just message count
- **Quick win:** First semantic chunk created

### DAY 4 (4 hours) - Thread Migration
- [ ] Build migration script (existing → unified) (2 hrs)
- [ ] Test migration with sample conversations (2 hrs)
- **Done when:** All old threads merged without data loss
- **Quick win:** Migration script runs successfully

### DAY 5 (4 hours) - Retrieval System
- [ ] Implement context-aware retrieval (2.5 hrs)
- [ ] Add relevance ranking for retrieved chunks (1.5 hrs)
- **Done when:** ARIA can pull relevant context from any point
- **Checkpoint:** Demo retrieval system

### DAY 6 (4 hours) - Integration & Testing
- [ ] Replace old threading in ARIA core (2 hrs)
- [ ] End-to-end testing (2 hrs)
- **Done when:** ARIA works with unified threading, no regressions
- **Biggest risk:** Integration breaking existing functionality

### DAY 7 (4 hours) - Polish & Documentation
- [ ] Performance optimization (2 hrs)
- [ ] Update documentation (2 hrs)
- **Done when:** System documented, performance acceptable
- **Checkpoint:** Full system deployed

### ADHD OPTIMIZATION NOTES

**Energy Matching:**
- Days 1-3: Hardest cognitive work (fresh post-launch)
- Days 4-5: Implementation (mid-sprint)
- Days 6-7: Testing/polish (need to ship)

**Dopamine Stacks:**
- Day 1: See current system working
- Day 2: First message to unified stream
- Day 3: First semantic chunk created
- Day 4: Migration script success

**Hyperfocus Trap Prevention:**
- No "perfect" chunking algorithm - good enough ships
- No extra features - stick to core replacement
- No AI/ML optimization rabbit holes

**Minimum Viable Product:**
Messages in one stream, retrievable by recency. Everything else is bonus.

**🚨 CALL OUT IF:**
- Adding features not in plan
- Perfectionism on chunking
- Building new UI before core works
- Research rabbit holes beyond Day 1

---

## RESEARCH FINDINGS (Applied)

| Finding | Application |
|---------|-------------|
| LLMs only use 10-20% of long context | Smart retrieval > dumping everything |
| RAG chunking at 400-512 tokens optimal | Chunk conversations at this size |
| 10-20% overlap between chunks | Maintain context continuity |
| Mem0 shows 26% improvement, 90% token reduction | Target metrics |
| MemGPT hierarchical memory (RAM + Disk) | Primary + Archive storage pattern |
| Single thread reduces ADHD cognitive load | Core UX benefit |

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIFIED CONVERSATION STREAM                   │
│                                                                  │
│  User Message → Context Assembler → LLM → Response → Archive    │
│                        ↑                                         │
│                        │                                         │
│            ┌───────────┴───────────┐                            │
│            │   CONTEXT ASSEMBLER   │                            │
│            │                       │                            │
│            │  1. Current buffer    │                            │
│            │  2. Semantic search   │                            │
│            │  3. Recency boost     │                            │
│            │  4. Assemble context  │                            │
│            └───────────────────────┘                            │
│                        ↑                                         │
│            ┌───────────┴───────────┐                            │
│            │                       │                            │
│     ┌──────┴──────┐        ┌──────┴──────┐                     │
│     │   PRIMARY   │        │   ARCHIVE    │                     │
│     │   BUFFER    │        │   STORAGE    │                     │
│     │             │        │              │                     │
│     │ Last 10-20  │        │  Chunked +   │                     │
│     │ messages    │        │  Embedded    │                     │
│     │ (immediate) │        │  (semantic)  │                     │
│     └─────────────┘        └──────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

### Components

**1. Primary Buffer (Hot Storage)**
- Last 10-20 messages (configurable)
- Always included in context
- FIFO - oldest messages move to archive
- Immediate access, no retrieval cost

**2. Archive Storage (Cold Storage)**
- All historical messages, chunked
- Vector embeddings for semantic search
- Retrieved on-demand based on relevance
- Summarized for efficiency

**3. Context Assembler**
- Combines primary buffer + relevant archive chunks
- Respects token budget
- Prioritizes: recency → relevance → importance
- Produces optimal context window

---

## CHUNKING STRATEGY

### Chunk Parameters
```yaml
chunk_size: 400-512 tokens
chunk_overlap: 50-100 tokens (10-20%)
chunk_boundary: message_end  # Don't split mid-message
max_messages_per_chunk: 10
min_messages_per_chunk: 3
```

### Chunk Metadata
```json
{
  "chunk_id": "uuid",
  "conversation_id": "uuid",
  "created_at": "timestamp",
  "message_count": 5,
  "token_count": 487,
  "start_message_id": "uuid",
  "end_message_id": "uuid",
  "topics": ["compliance", "automation", "pricing"],
  "summary": "Discussion about pricing compliance automation at $5K/mo...",
  "embedding": [0.123, -0.456, ...]
}
```

### Chunking Triggers
1. **Token threshold** - When buffer exceeds 4000 tokens
2. **Message count** - Every 20 messages
3. **Topic shift** - Detected via embedding similarity
4. **Time gap** - >4 hours between messages

---

## RETRIEVAL LOGIC

### Query Process
```python
def retrieve_context(query: str, budget_tokens: int = 8000) -> list[Chunk]:
    # 1. Always include primary buffer
    context = primary_buffer.get_all()
    remaining_budget = budget_tokens - context.token_count
    
    # 2. Generate query embedding
    query_embedding = embed(query)
    
    # 3. Semantic search over archive
    candidates = archive.semantic_search(
        query_embedding,
        top_k=20,
        threshold=0.7
    )
    
    # 4. Apply recency boost
    for chunk in candidates:
        age_hours = (now - chunk.created_at).hours
        recency_score = 1.0 / (1 + age_hours / 24)  # Decay over days
        chunk.score = chunk.similarity * 0.7 + recency_score * 0.3
    
    # 5. Sort by combined score
    candidates.sort(key=lambda c: c.score, reverse=True)
    
    # 6. Fill budget
    for chunk in candidates:
        if chunk.token_count <= remaining_budget:
            context.append(chunk)
            remaining_budget -= chunk.token_count
        if remaining_budget < 100:
            break
    
    return context
```

### Relevance Scoring
```yaml
semantic_similarity: 0.7  # Weight for embedding similarity
recency_boost: 0.3        # Weight for time decay
importance_multiplier:
  has_decision: 1.5       # Chunks with decisions
  has_commitment: 1.5     # Chunks with commitments
  has_insight: 1.3        # Chunks with insights
  has_user_preference: 1.4  # Chunks with preferences
```

---

## CONTEXT COMPACTION

### When to Compact
1. **Archive size** - When archive exceeds 1000 chunks
2. **Chunk age** - Chunks older than 90 days
3. **Low retrieval** - Chunks never retrieved in 30 days

### Compaction Process
```python
def compact_old_chunks(chunks: list[Chunk]) -> Chunk:
    # 1. Sort by time
    chunks.sort(key=lambda c: c.created_at)
    
    # 2. Extract key information
    key_info = {
        "decisions": [],
        "commitments": [],
        "preferences": [],
        "insights": [],
        "facts": []
    }
    
    for chunk in chunks:
        key_info["decisions"].extend(extract_decisions(chunk))
        key_info["commitments"].extend(extract_commitments(chunk))
        # ... etc
    
    # 3. Generate summary
    summary = llm_summarize(chunks, key_info)
    
    # 4. Create compacted chunk
    return Chunk(
        type="compacted",
        summary=summary,
        key_info=key_info,
        source_chunk_ids=[c.id for c in chunks],
        token_count=estimate_tokens(summary)
    )
```

### Retention Rules
```yaml
always_keep:
  - Chunks with user preferences
  - Chunks with commitments (active)
  - Chunks with important decisions
  - Last 30 days of chunks

compact_after:
  - 90 days for general conversation
  - 180 days for compacted summaries

delete_after:
  - 365 days for compacted summaries
  - Never delete preferences/facts
```

---

## DATABASE SCHEMA

```sql
-- Conversations (one per user, unified)
CREATE TABLE aria_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL UNIQUE,  -- One conversation per user!
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    total_messages INT DEFAULT 0,
    total_chunks INT DEFAULT 0,
    settings JSONB DEFAULT '{}'
);

-- Messages (all messages in the unified stream)
CREATE TABLE aria_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES aria_conversations(id),
    role TEXT NOT NULL,  -- user, assistant, system
    content TEXT NOT NULL,
    token_count INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',  -- mode, tools_used, etc.
    chunk_id UUID,  -- Which chunk this message belongs to (null = primary buffer)
    
    -- For fast primary buffer retrieval
    sequence_num SERIAL
);

-- Chunks (archived conversation segments)
CREATE TABLE aria_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES aria_conversations(id),
    
    -- Content
    content TEXT NOT NULL,  -- Raw messages concatenated
    summary TEXT,  -- LLM-generated summary
    token_count INT,
    message_count INT,
    
    -- Boundaries
    start_message_id UUID REFERENCES aria_messages(id),
    end_message_id UUID REFERENCES aria_messages(id),
    start_sequence INT,
    end_sequence INT,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    topics JSONB DEFAULT '[]',
    key_entities JSONB DEFAULT '{}',
    importance_score FLOAT DEFAULT 1.0,
    
    -- Retrieval tracking
    retrieval_count INT DEFAULT 0,
    last_retrieved_at TIMESTAMPTZ,
    
    -- Compaction
    is_compacted BOOLEAN DEFAULT FALSE,
    source_chunk_ids UUID[] DEFAULT '{}',
    
    -- Embedding (stored separately for efficiency)
    embedding_id UUID
);

-- Embeddings (vector storage)
CREATE TABLE aria_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID REFERENCES aria_chunks(id) ON DELETE CASCADE,
    embedding vector(1536),  -- OpenAI ada-002 dimension
    model TEXT DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create vector index for semantic search
CREATE INDEX idx_embeddings_vector ON aria_embeddings 
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Key information extracted from chunks
CREATE TABLE aria_extracted_info (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES aria_conversations(id),
    chunk_id UUID REFERENCES aria_chunks(id),
    
    info_type TEXT NOT NULL,  -- decision, commitment, preference, fact, insight
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    
    -- For preferences/facts that should persist
    is_permanent BOOLEAN DEFAULT FALSE,
    superseded_by UUID REFERENCES aria_extracted_info(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ  -- For commitments with deadlines
);

-- Indexes
CREATE INDEX idx_messages_conversation ON aria_messages(conversation_id);
CREATE INDEX idx_messages_chunk ON aria_messages(chunk_id);
CREATE INDEX idx_messages_sequence ON aria_messages(conversation_id, sequence_num DESC);
CREATE INDEX idx_chunks_conversation ON aria_chunks(conversation_id);
CREATE INDEX idx_chunks_created ON aria_chunks(created_at DESC);
CREATE INDEX idx_extracted_type ON aria_extracted_info(info_type);
CREATE INDEX idx_extracted_permanent ON aria_extracted_info(is_permanent) WHERE is_permanent = TRUE;
```

---

## API ENDPOINTS

### Message Handling
```yaml
POST /conversation/message
body: {
  message: string,
  mode?: string,  # ARIA mode
  context_budget?: int  # Token budget for context
}
response: {
  response: string,
  context_used: {
    primary_messages: int,
    retrieved_chunks: int,
    total_tokens: int
  },
  message_id: string
}

GET /conversation/history
query: { limit?: int, before?: timestamp }
response: { messages[], has_more: bool }

GET /conversation/search
query: { q: string, limit?: int }
response: { chunks[], messages[] }
```

### Context Management
```yaml
POST /context/retrieve
body: {
  query: string,
  budget_tokens: int,
  include_primary: bool
}
response: {
  chunks: [],
  total_tokens: int,
  retrieval_scores: {}
}

POST /context/force-chunk
description: "Force chunking of primary buffer"
response: { chunk_id, messages_chunked }

GET /context/stats
response: {
  total_messages: int,
  total_chunks: int,
  archive_size_tokens: int,
  oldest_chunk: timestamp,
  retrieval_stats: {}
}
```

### Information Extraction
```yaml
GET /info/preferences
response: { preferences[] }

GET /info/commitments
query: { status?: active|completed|expired }
response: { commitments[] }

GET /info/decisions
query: { since?: timestamp }
response: { decisions[] }

POST /info/extract
description: "Run extraction on specific chunk"
body: { chunk_id: string }
response: { extracted: [] }
```

---

## INTEGRATION WITH ARIA

### Message Flow
```
User sends message
    │
    ▼
ARIA receives message
    │
    ├── Store in aria_messages (primary buffer)
    │
    ├── Check if chunking needed
    │   └── If yes: chunk oldest messages
    │
    ├── Retrieve relevant context
    │   ├── Get primary buffer (always)
    │   └── Semantic search archive (if needed)
    │
    ├── Assemble context window
    │   └── Primary + Retrieved + System prompt
    │
    ├── Call LLM with assembled context
    │
    ├── Store response in aria_messages
    │
    └── Return response to user
```

### ARIA Tool: `context_search`
```yaml
name: context_search
description: "Search past conversations for relevant context"
params:
  query: string
  max_results: int
returns:
  chunks: array of relevant conversation chunks
  
triggers:
  - "what did we discuss about..."
  - "remember when..."
  - "in our past conversation..."
  - User references something not in primary buffer
```

### ARIA Tool: `context_summary`
```yaml
name: context_summary
description: "Get summary of conversation history"
params:
  topic?: string  # Optional topic filter
  timeframe?: string  # e.g., "last week", "January"
returns:
  summary: string
  key_points: array
  
triggers:
  - "summarize our conversations"
  - "what have we covered about..."
  - "catch me up on..."
```

---

## SUCCESS METRICS

### Quality Metrics
- [ ] Response relevance score ≥ baseline (A/B test)
- [ ] Context retrieval precision ≥ 80%
- [ ] No "I don't remember" when info is in archive

### Efficiency Metrics
- [ ] Token usage reduced 70%+ vs full history
- [ ] Retrieval latency < 500ms
- [ ] Chunking latency < 1s

### User Experience
- [ ] Zero thread management required
- [ ] Seamless context continuity
- [ ] "It just remembers" feedback

---

## COST ESTIMATES

| Operation | Cost | Frequency |
|-----------|------|-----------|
| Embedding generation | $0.0001/1K tokens | Per chunk (~$0.00005/chunk) |
| Storage (Supabase) | Included | - |
| Vector search | Included | - |
| Summarization (compaction) | $0.01/chunk | Monthly batch |

**Monthly estimate:** $5-10 for typical usage (1000 chunks, 100 compactions)

---

## OPEN QUESTIONS

1. **Embedding model choice** - OpenAI ada-002 vs local model?
2. **Chunk overlap tuning** - 10% vs 20% overlap?
3. **Compaction frequency** - Weekly vs monthly?
4. **Multi-device sync** - How to handle concurrent sessions?
5. **Export/import** - User data portability?

---

## BUILD COMMAND

```bash
/gsd /opt/leveredge/specs/unified-threading.md
```

Context: Post-launch build. Implement unified conversation threading for ARIA. Follow CHIRON's 7-day sprint plan. Start with database schema, then core stream, chunking, retrieval, integration.
