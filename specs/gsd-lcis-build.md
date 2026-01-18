# GSD: LCIS - LEVEREDGE COLLECTIVE INTELLIGENCE SYSTEM

**Priority:** HIGH
**Estimated Time:** 14 hours (MVP)
**Spec:** /opt/leveredge/specs/LCIS-COLLECTIVE-INTELLIGENCE.md

---

## MISSION

Build a self-learning system so Claude Code and all agents:
1. Never retry known-failed approaches
2. Auto-capture every failure and success
3. Get relevant lessons injected before taking action
4. Follow enforced rules created from repeated failures

**Mantra:** "Fail once, learn forever."

---

## PHASE 1: DATABASE SCHEMA (2 hours)

### 1.1 Enable pgvector Extension

```sql
-- Run in DEV Supabase
CREATE EXTENSION IF NOT EXISTS vector;
```

### 1.2 Create Core Tables

Create file: `/opt/leveredge/database/migrations/20260118_lcis_schema.sql`

```sql
-- ============================================================
-- LCIS: LEVEREDGE COLLECTIVE INTELLIGENCE SYSTEM
-- Database Schema
-- ============================================================

-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- CORE LESSONS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Content
    content TEXT NOT NULL,
    title TEXT,
    context TEXT,
    outcome TEXT,
    root_cause TEXT,
    solution TEXT,
    alternatives TEXT[] DEFAULT '{}',
    
    -- Classification
    type TEXT NOT NULL CHECK (type IN (
        'failure',
        'success', 
        'pattern',
        'rule',
        'playbook',
        'warning',
        'insight',
        'anti_pattern'
    )),
    severity TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    
    -- Domain & Tags
    domain TEXT NOT NULL,
    subdomain TEXT,
    category TEXT,
    tags TEXT[] DEFAULT '{}',
    
    -- Source
    source_agent TEXT,
    source_type TEXT CHECK (source_type IN (
        'agent_report',
        'claude_code',
        'manual',
        'professor',
        'import',
        'migration'
    )),
    source_context JSONB DEFAULT '{}',
    related_files TEXT[] DEFAULT '{}',
    related_commands TEXT[] DEFAULT '{}',
    
    -- Semantic Search
    embedding VECTOR(1536),
    
    -- Lifecycle
    status TEXT DEFAULT 'active' CHECK (status IN (
        'pending',
        'active',
        'superseded',
        'deprecated',
        'promoted'
    )),
    superseded_by UUID REFERENCES lcis_lessons(id),
    promoted_to_rule_id UUID,
    
    -- Metrics
    occurrence_count INTEGER DEFAULT 1,
    times_recalled INTEGER DEFAULT 0,
    times_helpful INTEGER DEFAULT 0,
    times_ignored INTEGER DEFAULT 0,
    confidence DECIMAL(5,2) DEFAULT 50.0,
    
    -- Provenance
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    verified_at TIMESTAMPTZ,
    verified_by TEXT,
    last_occurred TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_domain ON lcis_lessons(domain);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_type ON lcis_lessons(type);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_status ON lcis_lessons(status);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_severity ON lcis_lessons(severity);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_source ON lcis_lessons(source_agent);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_tags ON lcis_lessons USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_created ON lcis_lessons(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lcis_lessons_embedding ON lcis_lessons 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- RULES TABLE (Enforced Constraints)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES lcis_lessons(id),
    
    -- Rule Definition
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    trigger_pattern TEXT,
    trigger_keywords TEXT[] DEFAULT '{}',
    trigger_embedding VECTOR(1536),
    
    -- Action
    action TEXT NOT NULL CHECK (action IN (
        'block',
        'warn',
        'require',
        'suggest'
    )),
    
    -- What to do instead
    alternatives JSONB DEFAULT '[]',
    required_action TEXT,
    
    -- Scope
    applies_to_agents TEXT[] DEFAULT '{}',
    applies_to_domains TEXT[] DEFAULT '{}',
    
    -- Enforcement
    enforced BOOLEAN DEFAULT TRUE,
    enforcement_count INTEGER DEFAULT 0,
    override_count INTEGER DEFAULT 0,
    last_enforced TIMESTAMPTZ,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,
    expires_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_lcis_rules_enforced ON lcis_rules(enforced);
CREATE INDEX IF NOT EXISTS idx_lcis_rules_action ON lcis_rules(action);

-- ============================================================
-- PLAYBOOKS TABLE (Success Recipes)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL,
    description TEXT,
    domain TEXT NOT NULL,
    category TEXT,
    
    -- Steps (ordered)
    steps JSONB NOT NULL DEFAULT '[]',
    prerequisites JSONB DEFAULT '[]',
    expected_outcome TEXT,
    estimated_duration_minutes INTEGER,
    
    -- Source
    derived_from_lessons UUID[] DEFAULT '{}',
    
    -- Metrics
    times_used INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AGENT KNOWLEDGE (Per-Agent Relevant Lessons)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_agent_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL,
    lesson_id UUID REFERENCES lcis_lessons(id) ON DELETE CASCADE,
    
    relevance_score DECIMAL(5,2) DEFAULT 50.0,
    times_applied INTEGER DEFAULT 0,
    last_applied TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(agent, lesson_id)
);

CREATE INDEX IF NOT EXISTS idx_lcis_agent_knowledge_agent ON lcis_agent_knowledge(agent);

-- ============================================================
-- EVENTS (Audit Trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS lcis_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    event_type TEXT NOT NULL CHECK (event_type IN (
        'lesson_created',
        'lesson_recalled',
        'lesson_helpful',
        'lesson_ignored',
        'lesson_verified',
        'lesson_superseded',
        'rule_created',
        'rule_enforced',
        'rule_overridden',
        'pattern_detected',
        'playbook_executed',
        'playbook_success',
        'playbook_failure'
    )),
    
    lesson_id UUID REFERENCES lcis_lessons(id),
    rule_id UUID REFERENCES lcis_rules(id),
    playbook_id UUID REFERENCES lcis_playbooks(id),
    
    agent TEXT,
    context JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lcis_events_type ON lcis_events(event_type);
CREATE INDEX IF NOT EXISTS idx_lcis_events_created ON lcis_events(created_at DESC);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Semantic search for lessons
CREATE OR REPLACE FUNCTION lcis_semantic_search(
    query_embedding VECTOR(1536),
    search_domain TEXT DEFAULT NULL,
    search_type TEXT DEFAULT NULL,
    min_confidence DECIMAL DEFAULT 30.0,
    result_limit INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    type TEXT,
    title TEXT,
    content TEXT,
    solution TEXT,
    severity TEXT,
    confidence DECIMAL,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.type,
        l.title,
        l.content,
        l.solution,
        l.severity,
        l.confidence,
        1 - (l.embedding <=> query_embedding) as similarity
    FROM lcis_lessons l
    WHERE l.status = 'active'
    AND l.confidence >= min_confidence
    AND (search_domain IS NULL OR l.domain = search_domain)
    AND (search_type IS NULL OR l.type = search_type)
    AND l.embedding IS NOT NULL
    ORDER BY l.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Check for blocking rules
CREATE OR REPLACE FUNCTION lcis_check_rules(
    p_action TEXT,
    p_domain TEXT DEFAULT NULL,
    p_agent TEXT DEFAULT NULL
)
RETURNS TABLE (
    rule_id UUID,
    rule_name TEXT,
    action TEXT,
    description TEXT,
    alternatives JSONB,
    required_action TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        r.id as rule_id,
        r.name as rule_name,
        r.action,
        r.description,
        r.alternatives,
        r.required_action
    FROM lcis_rules r
    WHERE r.enforced = TRUE
    AND (r.expires_at IS NULL OR r.expires_at > NOW())
    AND (
        -- Check keyword triggers
        EXISTS (
            SELECT 1 FROM unnest(r.trigger_keywords) kw 
            WHERE p_action ILIKE '%' || kw || '%'
        )
        -- Or check pattern
        OR (r.trigger_pattern IS NOT NULL AND p_action ~* r.trigger_pattern)
    )
    AND (
        r.applies_to_domains = '{}' 
        OR p_domain = ANY(r.applies_to_domains)
    )
    AND (
        r.applies_to_agents = '{}' 
        OR p_agent = ANY(r.applies_to_agents)
        OR '*' = ANY(r.applies_to_agents)
    );
END;
$$ LANGUAGE plpgsql;

-- Record lesson occurrence (dedupe)
CREATE OR REPLACE FUNCTION lcis_record_or_increment(
    p_title TEXT,
    p_domain TEXT,
    p_type TEXT
)
RETURNS UUID AS $$
DECLARE
    existing_id UUID;
BEGIN
    -- Check for existing similar lesson
    SELECT id INTO existing_id
    FROM lcis_lessons
    WHERE title = p_title 
    AND domain = p_domain 
    AND type = p_type
    AND status = 'active'
    LIMIT 1;
    
    IF existing_id IS NOT NULL THEN
        -- Increment occurrence
        UPDATE lcis_lessons
        SET occurrence_count = occurrence_count + 1,
            last_occurred = NOW(),
            updated_at = NOW()
        WHERE id = existing_id;
        
        RETURN existing_id;
    END IF;
    
    RETURN NULL; -- No existing lesson found
END;
$$ LANGUAGE plpgsql;

-- Get critical lessons for Claude Code context
CREATE OR REPLACE FUNCTION lcis_claude_code_context()
RETURNS TABLE (
    category TEXT,
    lessons JSONB
) AS $$
BEGIN
    -- Critical failures (never repeat)
    RETURN QUERY
    SELECT 
        'critical_failures'::TEXT as category,
        jsonb_agg(jsonb_build_object(
            'title', l.title,
            'content', l.content,
            'solution', l.solution,
            'domain', l.domain
        )) as lessons
    FROM lcis_lessons l
    WHERE l.type = 'failure'
    AND l.severity IN ('critical', 'high')
    AND l.status = 'active'
    AND l.confidence >= 70
    ORDER BY l.occurrence_count DESC, l.created_at DESC
    LIMIT 20;
    
    -- Active rules
    RETURN QUERY
    SELECT 
        'active_rules'::TEXT as category,
        jsonb_agg(jsonb_build_object(
            'name', r.name,
            'description', r.description,
            'action', r.action,
            'alternatives', r.alternatives
        )) as lessons
    FROM lcis_rules r
    WHERE r.enforced = TRUE
    AND (r.expires_at IS NULL OR r.expires_at > NOW());
    
    -- Recent successes (replicate)
    RETURN QUERY
    SELECT 
        'recent_successes'::TEXT as category,
        jsonb_agg(jsonb_build_object(
            'title', l.title,
            'content', l.content,
            'domain', l.domain
        )) as lessons
    FROM lcis_lessons l
    WHERE l.type = 'success'
    AND l.status = 'active'
    AND l.confidence >= 70
    ORDER BY l.created_at DESC
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- Dashboard view
CREATE OR REPLACE VIEW lcis_dashboard AS
SELECT
    (SELECT COUNT(*) FROM lcis_lessons WHERE status = 'active') as total_lessons,
    (SELECT COUNT(*) FROM lcis_lessons WHERE type = 'failure' AND status = 'active') as failures,
    (SELECT COUNT(*) FROM lcis_lessons WHERE type = 'success' AND status = 'active') as successes,
    (SELECT COUNT(*) FROM lcis_rules WHERE enforced = TRUE) as active_rules,
    (SELECT COUNT(*) FROM lcis_playbooks) as playbooks,
    (SELECT COUNT(*) FROM lcis_lessons WHERE created_at > NOW() - INTERVAL '24 hours') as lessons_today,
    (SELECT COUNT(*) FROM lcis_lessons WHERE created_at > NOW() - INTERVAL '7 days') as lessons_week,
    (SELECT SUM(enforcement_count) FROM lcis_rules) as total_enforcements;

-- ============================================================
-- INITIAL SEED RULES (Critical Anti-Patterns)
-- ============================================================

INSERT INTO lcis_rules (name, description, action, trigger_keywords, alternatives, applies_to_agents) VALUES
(
    'No Direct Prod Database Modifications',
    'All database changes must go through DEV first, then promote-to-prod.sh',
    'block',
    ARRAY['prod supabase', 'production database', 'prod db'],
    '["Use DEV Supabase first", "Run promote-to-prod.sh after testing"]'::jsonb,
    ARRAY['*']
),
(
    'Docker Image Rebuild Required',
    'Files baked into Docker images at build time. Restart does not reload them.',
    'require',
    ARRAY['restart container', 'docker restart'],
    '["docker build -t <image>:<tag> .", "Rebuild before restart if files changed"]'::jsonb,
    ARRAY['*']
),
(
    'ARIA Prompt Protection',
    'ARIA system prompt changes require backup and proper update script',
    'require',
    ARRAY['aria prompt', 'aria_system_prompt', 'aria personality'],
    '["Use /opt/leveredge/scripts/aria-prompt-update.sh", "Backup exists at /opt/leveredge/backups/aria-prompts/"]'::jsonb,
    ARRAY['*']
),
(
    'No n8n Workflow SQL Updates',
    'Never update n8n workflows via direct SQL - breaks versioning',
    'block',
    ARRAY['UPDATE workflow', 'INSERT workflow', 'n8n sql'],
    '["Use n8n-troubleshooter MCP", "Use n8n UI to edit workflows"]'::jsonb,
    ARRAY['*']
),
(
    'Git Commit Before Major Changes',
    'Always commit current state before significant modifications',
    'warn',
    ARRAY['major change', 'refactor', 'migration'],
    '["git add . && git commit -m \"Pre-change checkpoint\""]'::jsonb,
    ARRAY['CLAUDE_CODE']
)
ON CONFLICT DO NOTHING;
```

### 1.3 Run Migration

```bash
# Copy to server and run in DEV Supabase
psql $DEV_DATABASE_URL -f /opt/leveredge/database/migrations/20260118_lcis_schema.sql
```

---

## PHASE 2: LIBRARIAN SERVICE (4 hours)

### 2.1 Create Service Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/lcis-librarian
```

### 2.2 Create Main Service

Create `/opt/leveredge/control-plane/agents/lcis-librarian/librarian.py`:

```python
"""
LCIS LIBRARIAN - Knowledge Ingestion Service
Port: 8050
Domain: THE_KEEP

Receives, validates, embeds, and stores all lessons learned.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import os
import httpx
import asyncpg
import json

app = FastAPI(
    title="LCIS LIBRARIAN",
    description="Knowledge Ingestion for LeverEdge Collective Intelligence",
    version="1.0.0"
)

# ============ CONFIGURATION ============

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://...")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"

# ============ MODELS ============

class LessonType(str, Enum):
    FAILURE = "failure"
    SUCCESS = "success"
    PATTERN = "pattern"
    RULE = "rule"
    PLAYBOOK = "playbook"
    WARNING = "warning"
    INSIGHT = "insight"
    ANTI_PATTERN = "anti_pattern"

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class LessonInput(BaseModel):
    """Input for creating a new lesson"""
    content: str = Field(..., min_length=10, description="The lesson learned")
    title: Optional[str] = Field(None, description="Short title")
    context: Optional[str] = Field(None, description="What was happening")
    outcome: Optional[str] = Field(None, description="What resulted")
    root_cause: Optional[str] = Field(None, description="Why it happened")
    solution: Optional[str] = Field(None, description="How to fix/avoid")
    alternatives: List[str] = Field(default_factory=list)
    
    type: LessonType
    severity: Optional[Severity] = Severity.MEDIUM
    
    domain: str = Field(..., description="Domain (THE_KEEP, CHANCERY, etc.)")
    subdomain: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    
    source_agent: str = Field(..., description="Who/what reported this")
    source_type: str = Field(default="agent_report")
    source_context: Dict[str, Any] = Field(default_factory=dict)
    related_files: List[str] = Field(default_factory=list)
    related_commands: List[str] = Field(default_factory=list)

class LessonResponse(BaseModel):
    id: str
    status: str
    duplicate: bool = False
    merged_with: Optional[str] = None
    patterns_detected: int = 0
    escalated: bool = False

# ============ DATABASE ============

pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

# ============ EMBEDDING ============

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding using OpenAI API"""
    if not OPENAI_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": EMBEDDING_MODEL,
                    "input": text[:8000]  # Truncate to limit
                },
                timeout=30.0
            )
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        return None

# ============ DEDUPLICATION ============

async def find_duplicate(content: str, domain: str, lesson_type: str) -> Optional[str]:
    """Check if similar lesson already exists"""
    async with pool.acquire() as conn:
        # First try exact title match
        existing = await conn.fetchrow("""
            SELECT id FROM lcis_lessons 
            WHERE domain = $1 AND type = $2 AND status = 'active'
            AND (
                content ILIKE $3
                OR title ILIKE $3
            )
            LIMIT 1
        """, domain, lesson_type, f"%{content[:100]}%")
        
        if existing:
            return str(existing['id'])
    
    return None

async def increment_occurrence(lesson_id: str):
    """Increment occurrence count for existing lesson"""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE lcis_lessons
            SET occurrence_count = occurrence_count + 1,
                last_occurred = NOW(),
                updated_at = NOW(),
                confidence = LEAST(confidence + 5, 100)
            WHERE id = $1
        """, lesson_id)

# ============ PATTERN DETECTION ============

async def check_for_patterns(lesson: LessonInput) -> int:
    """Check if this lesson forms a pattern with others"""
    if lesson.type != LessonType.FAILURE:
        return 0
    
    async with pool.acquire() as conn:
        # Count similar failures in last 30 days
        similar_count = await conn.fetchval("""
            SELECT COUNT(*) FROM lcis_lessons
            WHERE type = 'failure'
            AND domain = $1
            AND status = 'active'
            AND created_at > NOW() - INTERVAL '30 days'
            AND (
                content ILIKE $2
                OR tags && $3::text[]
            )
        """, lesson.domain, f"%{lesson.content[:50]}%", lesson.tags)
        
        if similar_count >= 3:
            # Auto-create rule
            await create_rule_from_pattern(lesson, similar_count)
            return similar_count
    
    return 0

async def create_rule_from_pattern(lesson: LessonInput, occurrence_count: int):
    """Promote repeated failure to a rule"""
    async with pool.acquire() as conn:
        # Create the rule
        rule_id = await conn.fetchval("""
            INSERT INTO lcis_rules (
                name, description, action, 
                trigger_keywords, alternatives,
                applies_to_domains, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """,
            f"Auto-Rule: {lesson.title or lesson.content[:50]}",
            f"Pattern detected: {occurrence_count} similar failures. {lesson.content}",
            "warn",
            lesson.tags,
            json.dumps(lesson.alternatives),
            [lesson.domain],
            "PROFESSOR"
        )
        
        # Log event
        await conn.execute("""
            INSERT INTO lcis_events (event_type, rule_id, context)
            VALUES ('rule_created', $1, $2)
        """, rule_id, json.dumps({
            "reason": "pattern_detection",
            "occurrence_count": occurrence_count,
            "source_lesson": lesson.content[:100]
        }))
        
        # TODO: Notify ARIA
        print(f"🚨 New rule created from pattern: {rule_id}")

# ============ PROPAGATION ============

async def propagate_to_agents(lesson_id: str, lesson: LessonInput):
    """Add lesson to relevant agents' knowledge"""
    # Map domains to agents
    domain_agents = {
        "THE_KEEP": ["CHRONOS", "HADES", "AEGIS", "DAEDALUS", "HERMES"],
        "SENTINELS": ["PANOPTES", "ASCLEPIUS", "ARGUS", "ALOY"],
        "CHANCERY": ["SCHOLAR", "CHIRON", "CONSUL", "VARYS"],
        "ALCHEMY": ["MUSE", "QUILL", "STAGE", "REEL", "CRITIC"],
        "ARIA_SANCTUM": ["ARIA"],
    }
    
    agents = domain_agents.get(lesson.domain, [])
    
    # Always include ARIA and VARYS
    agents = list(set(agents + ["ARIA", "VARYS"]))
    
    async with pool.acquire() as conn:
        for agent in agents:
            await conn.execute("""
                INSERT INTO lcis_agent_knowledge (agent, lesson_id, relevance_score)
                VALUES ($1, $2, $3)
                ON CONFLICT (agent, lesson_id) DO NOTHING
            """, agent, lesson_id, 70.0 if agent in domain_agents.get(lesson.domain, []) else 50.0)

# ============ ENDPOINTS ============

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "LCIS-LIBRARIAN", "port": 8050}

@app.post("/ingest", response_model=LessonResponse)
async def ingest_lesson(lesson: LessonInput, background_tasks: BackgroundTasks):
    """
    Ingest a new lesson into the knowledge base.
    
    - Checks for duplicates
    - Generates embedding for semantic search
    - Detects patterns
    - Propagates to relevant agents
    """
    
    # Check for duplicate
    duplicate_id = await find_duplicate(lesson.content, lesson.domain, lesson.type.value)
    if duplicate_id:
        await increment_occurrence(duplicate_id)
        return LessonResponse(
            id=duplicate_id,
            status="merged",
            duplicate=True,
            merged_with=duplicate_id
        )
    
    # Generate embedding
    embed_text = f"{lesson.title or ''} {lesson.content} {lesson.context or ''} {lesson.outcome or ''}"
    embedding = await generate_embedding(embed_text)
    
    # Store lesson
    async with pool.acquire() as conn:
        lesson_id = await conn.fetchval("""
            INSERT INTO lcis_lessons (
                content, title, context, outcome, root_cause, solution, alternatives,
                type, severity, domain, subdomain, category, tags,
                source_agent, source_type, source_context, 
                related_files, related_commands, embedding,
                created_by
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7,
                $8, $9, $10, $11, $12, $13,
                $14, $15, $16, $17, $18, $19,
                $20
            )
            RETURNING id
        """,
            lesson.content, lesson.title, lesson.context, lesson.outcome,
            lesson.root_cause, lesson.solution, lesson.alternatives,
            lesson.type.value, lesson.severity.value if lesson.severity else None,
            lesson.domain, lesson.subdomain, lesson.category, lesson.tags,
            lesson.source_agent, lesson.source_type, json.dumps(lesson.source_context),
            lesson.related_files, lesson.related_commands, 
            str(embedding) if embedding else None,
            lesson.source_agent
        )
    
    # Background tasks
    background_tasks.add_task(propagate_to_agents, str(lesson_id), lesson)
    
    # Check for patterns
    patterns_detected = await check_for_patterns(lesson)
    
    # Log event
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO lcis_events (event_type, lesson_id, agent, context)
            VALUES ('lesson_created', $1, $2, $3)
        """, lesson_id, lesson.source_agent, json.dumps({"type": lesson.type.value}))
    
    return LessonResponse(
        id=str(lesson_id),
        status="created",
        patterns_detected=patterns_detected,
        escalated=patterns_detected >= 3
    )

@app.post("/bulk-ingest")
async def bulk_ingest(lessons: List[LessonInput]):
    """Ingest multiple lessons at once (for migration)"""
    results = []
    for lesson in lessons:
        try:
            result = await ingest_lesson(lesson, BackgroundTasks())
            results.append({"status": "success", "id": result.id})
        except Exception as e:
            results.append({"status": "error", "error": str(e)})
    
    return {
        "total": len(lessons),
        "success": sum(1 for r in results if r["status"] == "success"),
        "results": results
    }

@app.get("/lessons")
async def list_lessons(
    domain: Optional[str] = None,
    type: Optional[str] = None,
    status: str = "active",
    limit: int = 50
):
    """List lessons with optional filters"""
    async with pool.acquire() as conn:
        query = """
            SELECT id, title, content, type, severity, domain, 
                   confidence, occurrence_count, created_at
            FROM lcis_lessons
            WHERE status = $1
        """
        params = [status]
        
        if domain:
            query += f" AND domain = ${len(params) + 1}"
            params.append(domain)
        if type:
            query += f" AND type = ${len(params) + 1}"
            params.append(type)
        
        query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.get("/dashboard")
async def dashboard():
    """Get LCIS dashboard metrics"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM lcis_dashboard")
        return dict(row) if row else {}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)
```

### 2.3 Create Dockerfile

Create `/opt/leveredge/control-plane/agents/lcis-librarian/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY librarian.py .

EXPOSE 8050

CMD ["uvicorn", "librarian:app", "--host", "0.0.0.0", "--port", "8050"]
```

### 2.4 Add to Docker Compose

Add to `/opt/leveredge/docker-compose.yml`:

```yaml
  lcis-librarian:
    build: ./control-plane/agents/lcis-librarian
    container_name: lcis-librarian
    restart: unless-stopped
    ports:
      - "8050:8050"
    environment:
      - DATABASE_URL=${DEV_DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - leveredge
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8050/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## PHASE 3: ORACLE SERVICE (4 hours)

### 3.1 Create Service Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/lcis-oracle
```

### 3.2 Create Main Service

Create `/opt/leveredge/control-plane/agents/lcis-oracle/oracle.py`:

```python
"""
LCIS ORACLE - Pre-Action Retrieval Service
Port: 8052
Domain: THE_KEEP

Consult before any action to get relevant knowledge and check rules.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import os
import httpx
import asyncpg
import json

app = FastAPI(
    title="LCIS ORACLE",
    description="Pre-Action Consultation for LeverEdge Collective Intelligence",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# ============ MODELS ============

class ConsultRequest(BaseModel):
    """Request for pre-action consultation"""
    action: str = Field(..., description="What you intend to do")
    domain: Optional[str] = Field(None, description="Domain context")
    agent: Optional[str] = Field(None, description="Which agent is asking")
    context: Optional[str] = Field(None, description="Additional context")

class BlockedRule(BaseModel):
    rule_id: str
    name: str
    reason: str
    alternatives: List[str]

class Warning(BaseModel):
    lesson_id: str
    title: str
    content: str
    severity: str

class Recommendation(BaseModel):
    lesson_id: str
    title: str
    content: str
    confidence: float

class ConsultResponse(BaseModel):
    """Response from Oracle consultation"""
    proceed: bool = True
    blocked: bool = False
    blocked_by: Optional[BlockedRule] = None
    warnings: List[Warning] = []
    recommendations: List[Recommendation] = []
    relevant_playbooks: List[Dict[str, Any]] = []
    confidence: float = 100.0

# ============ DATABASE ============

pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    await pool.close()

# ============ EMBEDDING ============

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding for semantic search"""
    if not OPENAI_API_KEY:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={"model": "text-embedding-3-small", "input": text[:8000]},
                timeout=30.0
            )
            return response.json()["data"][0]["embedding"]
    except:
        return None

# ============ RULE CHECKING ============

async def check_rules(action: str, domain: str, agent: str) -> Optional[BlockedRule]:
    """Check if action matches any blocking rules"""
    async with pool.acquire() as conn:
        rules = await conn.fetch("""
            SELECT id, name, description, action, alternatives, required_action
            FROM lcis_check_rules($1, $2, $3)
        """, action, domain, agent)
        
        for rule in rules:
            if rule['action'] == 'block':
                # Log enforcement
                await conn.execute("""
                    UPDATE lcis_rules SET enforcement_count = enforcement_count + 1, last_enforced = NOW()
                    WHERE id = $1
                """, rule['id'])
                
                await conn.execute("""
                    INSERT INTO lcis_events (event_type, rule_id, agent, context)
                    VALUES ('rule_enforced', $1, $2, $3)
                """, rule['id'], agent, json.dumps({"action": action[:200]}))
                
                return BlockedRule(
                    rule_id=str(rule['id']),
                    name=rule['name'],
                    reason=rule['description'],
                    alternatives=rule['alternatives'] if rule['alternatives'] else []
                )
    
    return None

# ============ SEMANTIC SEARCH ============

async def search_relevant_lessons(action: str, domain: str, limit: int = 10) -> tuple:
    """Search for relevant warnings and recommendations"""
    embedding = await generate_embedding(action)
    
    warnings = []
    recommendations = []
    
    async with pool.acquire() as conn:
        if embedding:
            # Semantic search
            rows = await conn.fetch("""
                SELECT id, type, title, content, solution, severity, confidence,
                       1 - (embedding <=> $1::vector) as similarity
                FROM lcis_lessons
                WHERE status = 'active'
                AND embedding IS NOT NULL
                AND ($2::text IS NULL OR domain = $2)
                ORDER BY embedding <=> $1::vector
                LIMIT $3
            """, str(embedding), domain, limit)
        else:
            # Fallback to keyword search
            rows = await conn.fetch("""
                SELECT id, type, title, content, solution, severity, confidence, 0.5 as similarity
                FROM lcis_lessons
                WHERE status = 'active'
                AND ($1::text IS NULL OR domain = $1)
                AND (content ILIKE $2 OR title ILIKE $2)
                ORDER BY confidence DESC
                LIMIT $3
            """, domain, f"%{action[:50]}%", limit)
        
        for row in rows:
            if row['type'] == 'failure' or row['type'] == 'warning':
                warnings.append(Warning(
                    lesson_id=str(row['id']),
                    title=row['title'] or row['content'][:50],
                    content=row['content'],
                    severity=row['severity'] or 'medium'
                ))
            elif row['type'] == 'success' or row['type'] == 'playbook':
                recommendations.append(Recommendation(
                    lesson_id=str(row['id']),
                    title=row['title'] or row['content'][:50],
                    content=row['solution'] or row['content'],
                    confidence=float(row['confidence'])
                ))
    
    return warnings, recommendations

async def get_relevant_playbooks(domain: str) -> List[Dict]:
    """Get playbooks relevant to domain"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, name, description, steps
            FROM lcis_playbooks
            WHERE domain = $1
            ORDER BY times_used DESC
            LIMIT 5
        """, domain)
        
        return [dict(row) for row in rows]

# ============ ENDPOINTS ============

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "LCIS-ORACLE", "port": 8052}

@app.post("/consult", response_model=ConsultResponse)
async def consult(request: ConsultRequest):
    """
    Consult the Oracle before taking action.
    
    Returns:
    - blocked: True if action is blocked by a rule
    - warnings: Past failures to be aware of
    - recommendations: Success patterns to follow
    - playbooks: Step-by-step guides if available
    """
    
    # Check for blocking rules
    blocked_rule = await check_rules(
        request.action, 
        request.domain, 
        request.agent
    )
    
    if blocked_rule:
        return ConsultResponse(
            proceed=False,
            blocked=True,
            blocked_by=blocked_rule,
            confidence=0.0
        )
    
    # Search for relevant lessons
    warnings, recommendations = await search_relevant_lessons(
        request.action,
        request.domain
    )
    
    # Get playbooks
    playbooks = []
    if request.domain:
        playbooks = await get_relevant_playbooks(request.domain)
    
    # Calculate confidence (lower if more warnings)
    confidence = max(50.0, 100.0 - (len(warnings) * 10))
    
    return ConsultResponse(
        proceed=True,
        blocked=False,
        warnings=warnings[:5],  # Top 5 warnings
        recommendations=recommendations[:5],  # Top 5 recommendations
        relevant_playbooks=playbooks,
        confidence=confidence
    )

@app.get("/rules")
async def list_rules(enforced_only: bool = True):
    """List all active rules"""
    async with pool.acquire() as conn:
        query = "SELECT * FROM lcis_rules"
        if enforced_only:
            query += " WHERE enforced = TRUE"
        query += " ORDER BY enforcement_count DESC"
        
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]

@app.get("/context/claude-code")
async def claude_code_context():
    """
    Get full context for Claude Code session.
    
    This should be injected into EXECUTION_RULES.md or session context.
    """
    async with pool.acquire() as conn:
        # Critical failures
        failures = await conn.fetch("""
            SELECT title, content, solution, domain
            FROM lcis_lessons
            WHERE type = 'failure' AND severity IN ('critical', 'high')
            AND status = 'active' AND confidence >= 70
            ORDER BY occurrence_count DESC, created_at DESC
            LIMIT 10
        """)
        
        # Active rules
        rules = await conn.fetch("""
            SELECT name, description, action, alternatives
            FROM lcis_rules WHERE enforced = TRUE
        """)
        
        # Recent successes
        successes = await conn.fetch("""
            SELECT title, content, domain
            FROM lcis_lessons
            WHERE type = 'success' AND status = 'active'
            ORDER BY created_at DESC LIMIT 5
        """)
    
    return {
        "critical_failures": [dict(r) for r in failures],
        "active_rules": [dict(r) for r in rules],
        "recent_successes": [dict(r) for r in successes],
        "generated_at": datetime.now().isoformat()
    }

@app.post("/feedback/helpful")
async def mark_helpful(lesson_id: str, agent: str):
    """Mark a lesson as helpful (improves confidence)"""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE lcis_lessons
            SET times_helpful = times_helpful + 1,
                confidence = LEAST(confidence + 2, 100)
            WHERE id = $1
        """, lesson_id)
        
        await conn.execute("""
            INSERT INTO lcis_events (event_type, lesson_id, agent)
            VALUES ('lesson_helpful', $1, $2)
        """, lesson_id, agent)
    
    return {"status": "recorded"}

@app.post("/feedback/ignored")
async def mark_ignored(lesson_id: str, agent: str):
    """Mark a lesson as ignored (decreases confidence over time)"""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE lcis_lessons
            SET times_ignored = times_ignored + 1,
                confidence = GREATEST(confidence - 1, 10)
            WHERE id = $1
        """, lesson_id)
        
        await conn.execute("""
            INSERT INTO lcis_events (event_type, lesson_id, agent)
            VALUES ('lesson_ignored', $1, $2)
        """, lesson_id, agent)
    
    return {"status": "recorded"}

if __name__ == "__main__":
    import uvicorn
    from datetime import datetime
    uvicorn.run(app, host="0.0.0.0", port=8052)
```

### 3.3 Create Dockerfile

Create `/opt/leveredge/control-plane/agents/lcis-oracle/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY oracle.py .

EXPOSE 8052

CMD ["uvicorn", "oracle:app", "--host", "0.0.0.0", "--port", "8052"]
```

### 3.4 Add to Docker Compose

```yaml
  lcis-oracle:
    build: ./control-plane/agents/lcis-oracle
    container_name: lcis-oracle
    restart: unless-stopped
    ports:
      - "8052:8052"
    environment:
      - DATABASE_URL=${DEV_DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - leveredge
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8052/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## PHASE 4: HEPHAESTUS MCP INTEGRATION (2 hours)

### 4.1 Add LCIS Tools to HEPHAESTUS

Add to `/opt/leveredge/control-plane/agents/hephaestus/mcp_tools.py`:

```python
# ============ LCIS INTEGRATION ============

@mcp_tool(name="lcis_consult")
async def lcis_consult(
    action: str,
    domain: str = None,
    context: str = None
) -> dict:
    """
    REQUIRED before significant actions.
    
    Consult LCIS Oracle for:
    - Blocking rules
    - Relevant warnings (past failures)
    - Recommendations (success patterns)
    - Playbooks (step-by-step guides)
    
    Example:
        result = await lcis_consult(
            action="Update ARIA system prompt",
            domain="ARIA_SANCTUM",
            context="User wants personality change"
        )
        if result["blocked"]:
            return f"BLOCKED: {result['blocked_by']['reason']}"
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8052/consult",
                json={
                    "action": action,
                    "domain": domain,
                    "agent": "CLAUDE_CODE",
                    "context": context
                },
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e), "proceed": True, "warnings": ["LCIS unavailable"]}

@mcp_tool(name="lcis_report")
async def lcis_report(
    content: str,
    type: str,
    domain: str,
    title: str = None,
    context: str = None,
    outcome: str = None,
    solution: str = None,
    severity: str = "medium",
    tags: list = None
) -> dict:
    """
    Report a lesson learned to LCIS.
    
    Types: failure, success, warning, insight, anti_pattern
    Severity: critical, high, medium, low
    
    Example (failure):
        await lcis_report(
            content="Docker restart doesn't reload baked files",
            type="failure",
            domain="THE_KEEP",
            title="Prompt not updating after restart",
            context="Tried to update ARIA prompt",
            outcome="Prompt unchanged",
            solution="Rebuild Docker image instead",
            severity="high",
            tags=["docker", "aria", "prompt"]
        )
    
    Example (success):
        await lcis_report(
            content="Volume mount allows hot-reload of config files",
            type="success",
            domain="THE_KEEP",
            title="Hot-reload config pattern",
            solution="Mount config as volume instead of baking",
            tags=["docker", "config", "pattern"]
        )
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8050/ingest",
                json={
                    "content": content,
                    "type": type,
                    "domain": domain,
                    "title": title,
                    "context": context,
                    "outcome": outcome,
                    "solution": solution,
                    "severity": severity,
                    "tags": tags or [],
                    "source_agent": "CLAUDE_CODE",
                    "source_type": "claude_code"
                },
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e), "status": "failed"}

@mcp_tool(name="lcis_rules")
async def lcis_rules() -> dict:
    """Get all active LCIS rules that will block or warn."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8052/rules",
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e), "rules": []}

@mcp_tool(name="lcis_context")
async def lcis_context() -> dict:
    """
    Get full LCIS context for current session.
    
    Returns:
    - critical_failures: Things to avoid
    - active_rules: Enforced constraints
    - recent_successes: Patterns to follow
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8052/context/claude-code",
                timeout=10.0
            )
            return response.json()
    except Exception as e:
        return {"error": str(e)}
```

---

## PHASE 5: MIGRATION SCRIPT (2 hours)

### 5.1 Create Migration Script

Create `/opt/leveredge/scripts/migrate-lessons-to-lcis.py`:

```python
#!/usr/bin/env python3
"""
Migrate LESSONS-LEARNED.md and LESSONS-SCRATCH.md to LCIS database.
"""

import re
import httpx
import asyncio
from pathlib import Path

LIBRARIAN_URL = "http://localhost:8050"
LESSONS_LEARNED = Path("/opt/leveredge/LESSONS-LEARNED.md")
LESSONS_SCRATCH = Path("/opt/leveredge/LESSONS-SCRATCH.md")

# Domain mapping from content keywords
DOMAIN_KEYWORDS = {
    "THE_KEEP": ["docker", "container", "backup", "server", "infrastructure", "caddy", "nginx"],
    "SENTINELS": ["security", "auth", "credential", "permission", "ssl", "certificate"],
    "CHANCERY": ["business", "client", "project", "planning", "strategy"],
    "ARIA_SANCTUM": ["aria", "prompt", "personality", "chat"],
    "ALCHEMY": ["content", "creative", "writing", "design"],
}

def infer_domain(content: str) -> str:
    content_lower = content.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(kw in content_lower for kw in keywords):
            return domain
    return "THE_KEEP"  # Default

def infer_type(content: str) -> str:
    content_lower = content.lower()
    if any(w in content_lower for w in ["don't", "never", "avoid", "failed", "error", "broken"]):
        return "failure"
    if any(w in content_lower for w in ["worked", "success", "solution", "fixed"]):
        return "success"
    if any(w in content_lower for w in ["warning", "careful", "watch out"]):
        return "warning"
    return "insight"

def parse_lessons_markdown(content: str) -> list:
    """Parse markdown into individual lessons"""
    lessons = []
    
    # Split by headers or bullet points
    lines = content.split('\n')
    current_lesson = []
    current_section = "general"
    
    for line in lines:
        # Check for section header
        if line.startswith('##'):
            current_section = line.strip('# ').lower()
            continue
        
        # Check for bullet point (lesson start)
        if line.strip().startswith('- ') or line.strip().startswith('* '):
            if current_lesson:
                lessons.append({
                    "content": ' '.join(current_lesson),
                    "section": current_section
                })
            current_lesson = [line.strip('- *').strip()]
        elif line.strip() and current_lesson:
            current_lesson.append(line.strip())
    
    # Don't forget last lesson
    if current_lesson:
        lessons.append({
            "content": ' '.join(current_lesson),
            "section": current_section
        })
    
    return lessons

async def migrate_lesson(lesson: dict) -> dict:
    """Send lesson to LCIS Librarian"""
    content = lesson["content"]
    
    payload = {
        "content": content,
        "title": content[:100] if len(content) > 100 else None,
        "type": infer_type(content),
        "domain": infer_domain(content),
        "severity": "medium",
        "tags": [lesson["section"]],
        "source_agent": "MIGRATION",
        "source_type": "migration",
        "source_context": {"file": "LESSONS-LEARNED.md"}
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{LIBRARIAN_URL}/ingest",
            json=payload,
            timeout=30.0
        )
        return response.json()

async def main():
    print("🧠 LCIS Migration: LESSONS-LEARNED.md → Database")
    print("=" * 50)
    
    # Read lessons file
    if not LESSONS_LEARNED.exists():
        print(f"❌ File not found: {LESSONS_LEARNED}")
        return
    
    content = LESSONS_LEARNED.read_text()
    lessons = parse_lessons_markdown(content)
    
    print(f"📚 Found {len(lessons)} lessons to migrate")
    
    # Migrate each lesson
    success = 0
    failed = 0
    duplicates = 0
    
    for i, lesson in enumerate(lessons, 1):
        try:
            result = await migrate_lesson(lesson)
            if result.get("duplicate"):
                duplicates += 1
                print(f"  [{i}] ⏩ Duplicate: {lesson['content'][:50]}...")
            else:
                success += 1
                print(f"  [{i}] ✅ Migrated: {lesson['content'][:50]}...")
        except Exception as e:
            failed += 1
            print(f"  [{i}] ❌ Failed: {e}")
    
    print("=" * 50)
    print(f"✅ Success: {success}")
    print(f"⏩ Duplicates: {duplicates}")
    print(f"❌ Failed: {failed}")
    
    # Also migrate LESSONS-SCRATCH if exists
    if LESSONS_SCRATCH.exists():
        print("\n📝 Also migrating LESSONS-SCRATCH.md...")
        scratch_content = LESSONS_SCRATCH.read_text()
        scratch_lessons = parse_lessons_markdown(scratch_content)
        
        for lesson in scratch_lessons:
            lesson["source_context"] = {"file": "LESSONS-SCRATCH.md"}
            try:
                await migrate_lesson(lesson)
            except:
                pass
        
        print(f"  Processed {len(scratch_lessons)} scratch lessons")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## EXECUTION RULES UPDATE

Add to `/home/damon/.claude/EXECUTION_RULES.md`:

```markdown
## Rule #13: LCIS INTEGRATION (Collective Intelligence)

LCIS prevents repeated mistakes and promotes success patterns.

### Before Significant Actions

```bash
# Consult ORACLE before risky operations
curl -s -X POST http://localhost:8052/consult \
  -H "Content-Type: application/json" \
  -d '{"action": "YOUR ACTION", "domain": "DOMAIN", "agent": "CLAUDE_CODE"}' | jq .
```

If `blocked: true` - DO NOT proceed. Follow alternatives.
If warnings exist - Review before proceeding.

### After Outcomes

```bash
# Report failures
curl -s -X POST http://localhost:8050/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What happened and why",
    "type": "failure",
    "domain": "THE_KEEP",
    "solution": "How to avoid/fix",
    "severity": "high",
    "source_agent": "CLAUDE_CODE"
  }'

# Report successes (significant ones)
curl -s -X POST http://localhost:8050/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "What worked and why",
    "type": "success",
    "domain": "THE_KEEP",
    "source_agent": "CLAUDE_CODE"
  }'
```

### LCIS Services
- LIBRARIAN (8050): Ingests lessons
- ORACLE (8052): Pre-action consultation
- Dashboard: `curl http://localhost:8050/dashboard`

### Active Rules
Run `curl http://localhost:8052/rules` to see all enforced rules.
```

---

## CADDY ROUTING

Add to Caddyfile:

```
lcis-librarian.leveredgeai.com {
    reverse_proxy localhost:8050
}

lcis-oracle.leveredgeai.com {
    reverse_proxy localhost:8052
}
```

---

## VERIFICATION CHECKLIST

After all phases complete:

```bash
# 1. Check services running
curl http://localhost:8050/health  # LIBRARIAN
curl http://localhost:8052/health  # ORACLE

# 2. Check database tables created
psql $DEV_DATABASE_URL -c "\dt lcis_*"

# 3. Check seed rules exist
curl http://localhost:8052/rules | jq .

# 4. Test lesson ingestion
curl -X POST http://localhost:8050/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test lesson from GSD verification",
    "type": "insight",
    "domain": "THE_KEEP",
    "source_agent": "VERIFICATION"
  }' | jq .

# 5. Test Oracle consultation
curl -X POST http://localhost:8052/consult \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update aria prompt by restarting container",
    "domain": "ARIA_SANCTUM",
    "agent": "CLAUDE_CODE"
  }' | jq .
# Should return blocked=true with alternatives

# 6. Check dashboard
curl http://localhost:8050/dashboard | jq .

# 7. Run migration
python3 /opt/leveredge/scripts/migrate-lessons-to-lcis.py
```

---

## GIT COMMIT

```bash
git add .
git commit -m "LCIS: LeverEdge Collective Intelligence System

- LIBRARIAN (8050): Knowledge ingestion with deduplication
- ORACLE (8052): Pre-action consultation with rule enforcement  
- Database schema with pgvector semantic search
- 5 seed rules (prod protection, docker rebuild, aria prompt, n8n sql, git commit)
- HEPHAESTUS MCP tools (lcis_consult, lcis_report, lcis_rules, lcis_context)
- Migration script for LESSONS-LEARNED.md
- EXECUTION_RULES.md Rule #13"
```

---

## SUCCESS CRITERIA

| Criteria | Test |
|----------|------|
| LIBRARIAN accepts lessons | POST to /ingest returns 200 |
| ORACLE blocks known anti-patterns | Consult returns blocked=true for "restart container" |
| Semantic search works | Similar lessons found by content |
| Rules auto-enforce | Keyword triggers return rule match |
| Migration completes | LESSONS-LEARNED.md entries in database |
| Dashboard shows metrics | /dashboard returns counts |

---

**MANTRA:** "Fail once, learn forever."
