# GSD: LCIS Cleanup & Verification

**Priority:** HIGH
**Time:** ~10 min
**Purpose:** Fix LCIS paths, remove duplicates, verify collective memory works

---

## ISSUES FOUND

| Issue | Details |
|-------|---------|
| Ghost entry | `librarian` in docker-compose points to non-existent `/control-plane/agents/librarian/` |
| Duplicate concept | Both `librarian` (8201) and `lcis-librarian` (8050) - unclear which is canonical |
| Database schema | Need to verify LCIS tables exist |

---

## WHAT LCIS SHOULD BE

**LCIS = LeverEdge Collective Intelligence System**

| Agent | Port | Purpose |
|-------|------|---------|
| **LIBRARIAN** | 8050 | Ingest lessons, embed, store |
| **ORACLE** | 8052 | Pre-action consultation |

The separate "librarian" at 8201 appears to be a duplicate concept. Remove it.

---

## PHASE 1: REMOVE GHOST ENTRY

In `docker-compose.fleet.yml`, remove or comment out the `librarian:` service block (port 8201) since:
1. Directory doesn't exist
2. LCIS-LIBRARIAN already does this job

```yaml
# REMOVE THIS ENTIRE BLOCK:
  # librarian:
  #   build:
  #     context: ./control-plane/agents/librarian
  #     ...
```

---

## PHASE 2: DATABASE SCHEMA

Verify/create LCIS tables:

```sql
-- ============================================
-- LESSONS LEARNED
-- ============================================
CREATE TABLE IF NOT EXISTS lcis_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Content
    title VARCHAR(255),
    content TEXT NOT NULL,
    context TEXT,
    outcome TEXT,
    root_cause TEXT,
    solution TEXT,
    alternatives JSONB DEFAULT '[]',
    
    -- Classification
    type VARCHAR(50) NOT NULL,  -- failure, success, pattern, rule, playbook, warning, insight, anti_pattern
    severity VARCHAR(50) DEFAULT 'medium',  -- critical, high, medium, low
    domain VARCHAR(100),  -- which domain this applies to
    agents TEXT[],  -- which agents this is relevant to
    tags TEXT[],
    
    -- Source
    source_agent VARCHAR(100),  -- who submitted this
    source_conversation VARCHAR(255),  -- reference to conversation
    source_file VARCHAR(500),  -- file path if from code
    
    -- Embedding for semantic search
    embedding vector(1536),  -- OpenAI text-embedding-3-small
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, superseded, archived
    superseded_by UUID REFERENCES lcis_lessons(id),
    
    -- Metrics
    times_retrieved INTEGER DEFAULT 0,
    times_useful INTEGER DEFAULT 0,  -- positive feedback
    times_ignored INTEGER DEFAULT 0,  -- negative feedback
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lessons_type ON lcis_lessons(type);
CREATE INDEX idx_lessons_severity ON lcis_lessons(severity);
CREATE INDEX idx_lessons_domain ON lcis_lessons(domain);
CREATE INDEX idx_lessons_status ON lcis_lessons(status);
CREATE INDEX idx_lessons_agents ON lcis_lessons USING GIN(agents);
CREATE INDEX idx_lessons_tags ON lcis_lessons USING GIN(tags);

-- For vector similarity search (requires pgvector)
-- CREATE INDEX idx_lessons_embedding ON lcis_lessons USING ivfflat (embedding vector_cosine_ops);

-- ============================================
-- RULES (Hard blocks)
-- ============================================
CREATE TABLE IF NOT EXISTS lcis_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    
    -- Matching
    trigger_patterns JSONB NOT NULL,  -- patterns that trigger this rule
    domain VARCHAR(100),
    agents TEXT[],  -- which agents this applies to, NULL = all
    
    -- Action
    action VARCHAR(50) NOT NULL,  -- block, warn, suggest
    reason TEXT NOT NULL,
    alternatives JSONB DEFAULT '[]',
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    priority INTEGER DEFAULT 50,  -- higher = checked first
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_rules_domain ON lcis_rules(domain);
CREATE INDEX idx_rules_status ON lcis_rules(status);
CREATE INDEX idx_rules_priority ON lcis_rules(priority DESC);

-- ============================================
-- CONSULTATION LOG
-- ============================================
CREATE TABLE IF NOT EXISTS lcis_consultations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Request
    agent VARCHAR(100),
    action TEXT NOT NULL,
    domain VARCHAR(100),
    context TEXT,
    
    -- Response
    proceed BOOLEAN,
    blocked BOOLEAN DEFAULT FALSE,
    blocked_by UUID REFERENCES lcis_rules(id),
    warnings_count INTEGER DEFAULT 0,
    recommendations_count INTEGER DEFAULT 0,
    
    -- Full response stored
    response JSONB,
    
    -- Feedback
    feedback VARCHAR(50),  -- helpful, not_helpful, ignored
    feedback_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_consult_agent ON lcis_consultations(agent);
CREATE INDEX idx_consult_blocked ON lcis_consultations(blocked);
CREATE INDEX idx_consult_created ON lcis_consultations(created_at DESC);

-- ============================================
-- SEED CRITICAL RULES
-- ============================================
INSERT INTO lcis_rules (name, description, trigger_patterns, action, reason, alternatives, priority) VALUES
(
    'No Direct SQL on n8n',
    'Never update n8n workflows via direct SQL',
    '{"patterns": ["UPDATE.*n8n", "INSERT.*n8n_workflow", "sql.*n8n"]}',
    'block',
    'Direct SQL breaks n8n versioning. Always use n8n MCP tools.',
    '["Use n8n-troubleshooter MCP", "Use n8n-control MCP", "Use n8n API"]',
    100
),
(
    'Dev First Workflow',
    'All changes go to dev environment first',
    '{"patterns": ["deploy.*prod", "prod.*direct", "skip.*dev"]}',
    'warn',
    'Dev-first workflow: test in dev, then promote-to-prod.sh',
    '["Deploy to dev first", "Run promote-to-prod.sh after testing"]',
    90
),
(
    'CHRONOS Before Risky Changes',
    'Create backup before major changes',
    '{"patterns": ["delete.*table", "drop.*", "truncate", "major.*change", "migration"]}',
    'warn',
    'Create CHRONOS backup before destructive operations',
    '["Call CHRONOS backup first", "Document rollback plan"]',
    80
),
(
    'AEGIS for Credentials',
    'Never hardcode or expose credentials',
    '{"patterns": ["password.*=", "api_key.*=", "secret.*=", "token.*="]}',
    'block',
    'Use AEGIS for credential management. Never expose values.',
    '["Use AEGIS to apply credentials", "Use environment variables"]',
    95
)
ON CONFLICT DO NOTHING;
```

---

## PHASE 3: VERIFY AGENTS

Check LCIS-LIBRARIAN has all required endpoints:

```python
# Required endpoints for LIBRARIAN:
GET  /health
POST /lessons              # Ingest new lesson
GET  /lessons              # List lessons
GET  /lessons/{id}         # Get specific lesson
POST /lessons/search       # Semantic search
GET  /lessons/recent       # Recent lessons
POST /lessons/{id}/feedback  # Mark helpful/not helpful

# Required endpoints for ORACLE:
GET  /health
POST /consult              # Pre-action consultation
GET  /rules                # List active rules
POST /rules                # Add new rule
GET  /consultations/recent # Recent consultations
```

---

## PHASE 4: TEST LCIS

```bash
# Start LCIS
docker compose -f docker-compose.fleet.yml up -d lcis-librarian lcis-oracle

# Wait for healthy
sleep 10

# Test LIBRARIAN health
curl http://localhost:8050/health

# Test ORACLE health  
curl http://localhost:8052/health

# Test consultation
curl -X POST http://localhost:8052/consult \
  -H "Content-Type: application/json" \
  -d '{"action": "UPDATE n8n_workflows SET active = true", "agent": "TEST"}'

# Should return blocked: true (matches rule)

# Test lesson ingestion
curl -X POST http://localhost:8050/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Always use n8n MCP tools instead of direct SQL",
    "title": "n8n MCP Required",
    "type": "rule",
    "severity": "critical",
    "domain": "infrastructure"
  }'
```

---

## PHASE 5: UPDATE AGENT-ROUTING.md

Add LCIS to routing documentation:

```markdown
### LCIS (Collective Intelligence)

| Agent | Port | Purpose |
|-------|------|---------|
| LIBRARIAN | 8050 | Ingest lessons, embed, store |
| ORACLE | 8052 | Pre-action consultation |

**Usage:**
- Before risky operations: Consult ORACLE
- After learning something: Tell LIBRARIAN
- All agents should integrate ORACLE checks
```

---

## DELIVERABLES

- [ ] Remove ghost `librarian` entry from docker-compose
- [ ] Run database schema
- [ ] Verify LIBRARIAN endpoints
- [ ] Verify ORACLE endpoints
- [ ] Test consultation with seeded rules
- [ ] Test lesson ingestion
- [ ] Update AGENT-ROUTING.md

---

## COMMIT MESSAGE

```
LCIS: Cleanup and verification

- Remove duplicate librarian entry (ghost)
- Verify database schema
- Seed critical rules (n8n SQL, dev-first, CHRONOS backup, AEGIS)
- Test consultation flow
- Document in AGENT-ROUTING.md

The collective memory is ready to learn.
```
