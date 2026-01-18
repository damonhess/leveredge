# LEVEREDGE COLLECTIVE INTELLIGENCE SYSTEM (LCIS)

**Version:** 1.0
**Status:** SPECIFICATION
**Created:** January 18, 2026

---

## EXECUTIVE SUMMARY

The LeverEdge Collective Intelligence System (LCIS) transforms the agent fleet from isolated tools into a learning organism. Every failure teaches. Every success reinforces. Knowledge flows up to supervisors and down to specialists. Claude Code stops repeating mistakes. Agents get smarter in their domains.

**Core Principle:** "Fail once, learn forever. Succeed once, replicate everywhere."

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          COLLECTIVE INTELLIGENCE LAYER                          │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      KNOWLEDGE GRAPH (Supabase + pgvector)              │   │
│  │                                                                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │  FAILURES   │  │  SUCCESSES  │  │  PATTERNS   │  │  RULES      │   │   │
│  │  │  (never     │  │  (replicate │  │  (detected  │  │  (enforced  │   │   │
│  │  │   repeat)   │  │   always)   │  │   trends)   │  │   always)   │   │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │   │
│  │                                                                         │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │              SEMANTIC SEARCH (pgvector embeddings)              │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│                              ▲                    │                             │
│                              │ LEARN              │ RECALL                      │
│                              │                    ▼                             │
│                                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │     LIBRARIAN    │  │    PROFESSOR     │  │     ORACLE       │              │
│  │  (Knowledge      │  │  (Pattern        │  │  (Pre-action     │              │
│  │   Ingestion)     │  │   Detection)     │  │   Retrieval)     │              │
│  │   Port: 8050     │  │   Port: 8051     │  │   Port: 8052     │              │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘              │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
            │ CLAUDE CODE │   │   AGENTS    │   │    ARIA     │
            │             │   │ (all 35+)   │   │  (Supreme)  │
            │ Pre-action  │   │             │   │             │
            │ injection   │   │ Domain      │   │ Full        │
            │ via MCP     │   │ learning    │   │ awareness   │
            └─────────────┘   └─────────────┘   └─────────────┘
```

---

## CORE COMPONENTS

### 1. LIBRARIAN (Port 8050) - Knowledge Ingestion

**Purpose:** Receives, validates, categorizes, and stores all lessons learned.

**Inputs:**
- Failure reports from any agent
- Success reports from any agent
- Manual lessons from Claude Code/Damon
- Pattern observations from PROFESSOR
- External knowledge imports

**Processing:**
```python
class Librarian:
    async def ingest_lesson(self, lesson: Lesson) -> str:
        """
        Process incoming lesson:
        1. Validate structure
        2. Check for duplicates (semantic similarity > 0.9)
        3. Generate embedding
        4. Categorize by domain, type, severity
        5. Link to related lessons
        6. Store with full provenance
        7. Notify relevant supervisors
        8. Update agent domain knowledge
        """
        
        # Duplicate detection
        similar = await self.find_similar(lesson.content, threshold=0.9)
        if similar:
            return await self.merge_lessons(similar, lesson)
        
        # Generate embedding for semantic search
        embedding = await self.embed(lesson.content)
        
        # Auto-categorize
        categories = await self.categorize(lesson)
        
        # Store
        lesson_id = await self.store(lesson, embedding, categories)
        
        # Propagate to relevant agents
        await self.propagate(lesson, categories)
        
        return lesson_id
```

### 2. PROFESSOR (Port 8051) - Pattern Detection

**Purpose:** Analyzes lessons to detect patterns, trends, and emergent rules.

**Capabilities:**
- Detect repeated failure patterns
- Identify success formulas
- Recognize domain crossover opportunities
- Generate "meta-lessons" from clusters
- Promote patterns to enforced rules

**Processing:**
```python
class Professor:
    async def analyze_patterns(self):
        """
        Continuous pattern detection:
        1. Cluster similar lessons
        2. Detect failure hotspots
        3. Identify success recipes
        4. Find cross-domain applicability
        5. Generate meta-lessons
        6. Recommend rule promotions
        """
        
        # Find failure clusters
        failure_clusters = await self.cluster_failures()
        for cluster in failure_clusters:
            if cluster.count >= 3:
                # Same mistake 3+ times = create RULE
                await self.promote_to_rule(cluster)
                await self.notify_aria(f"New rule created: {cluster.summary}")
        
        # Find success patterns
        success_patterns = await self.cluster_successes()
        for pattern in success_patterns:
            if pattern.confidence >= 0.8:
                await self.create_playbook(pattern)
```

### 3. ORACLE (Port 8052) - Pre-Action Retrieval

**Purpose:** Before any agent or Claude Code takes action, ORACLE provides relevant knowledge.

**Integration Points:**
- Claude Code (via MCP tool)
- All agents (via HTTP middleware)
- n8n workflows (via webhook node)

**Query Types:**
```python
class Oracle:
    async def consult(self, context: ActionContext) -> Guidance:
        """
        Before any action, provide:
        1. Relevant failures to AVOID
        2. Relevant successes to REPLICATE
        3. Applicable rules to FOLLOW
        4. Related patterns to CONSIDER
        5. Confidence score for proceeding
        """
        
        # Semantic search for relevant knowledge
        relevant = await self.search(
            query=context.intended_action,
            filters={
                "domain": context.domain,
                "agent": context.agent,
                "type": ["failure", "rule", "success"]
            },
            limit=10
        )
        
        # Check for blocking rules
        blocking_rules = [r for r in relevant if r.type == "rule" and r.blocks_action(context)]
        if blocking_rules:
            return Guidance(
                proceed=False,
                reason=f"Blocked by rule: {blocking_rules[0].content}",
                alternatives=blocking_rules[0].alternatives
            )
        
        # Compile guidance
        return Guidance(
            proceed=True,
            warnings=[f.content for f in relevant if f.type == "failure"],
            recommendations=[s.content for s in relevant if s.type == "success"],
            confidence=self.calculate_confidence(relevant)
        )
```

---

## DATABASE SCHEMA

```sql
-- Core lessons table
CREATE TABLE lcis_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Content
    content TEXT NOT NULL,                    -- The lesson itself
    context TEXT,                             -- What was happening
    outcome TEXT,                             -- What resulted
    
    -- Classification
    type TEXT NOT NULL CHECK (type IN (
        'failure',      -- Something that didn't work
        'success',      -- Something that worked well
        'pattern',      -- Detected trend
        'rule',         -- Enforced constraint
        'playbook',     -- Step-by-step success recipe
        'warning',      -- Caution without blocking
        'insight'       -- General knowledge
    )),
    severity TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    
    -- Domain
    domain TEXT NOT NULL,                     -- THE_KEEP, CHANCERY, etc.
    subdomain TEXT,                           -- More specific area
    tags TEXT[] DEFAULT '{}',                 -- Searchable tags
    
    -- Source
    source_agent TEXT,                        -- Which agent learned this
    source_type TEXT CHECK (source_type IN (
        'agent_report',   -- Agent self-reported
        'claude_code',    -- Claude Code learned
        'manual',         -- Damon entered
        'professor',      -- Pattern detection
        'import'          -- External import
    )),
    source_context JSONB DEFAULT '{}',        -- Full context of learning
    
    -- Semantic search
    embedding VECTOR(1536),                   -- For similarity search
    
    -- Lifecycle
    status TEXT DEFAULT 'active' CHECK (status IN (
        'pending',        -- Awaiting verification
        'active',         -- In use
        'superseded',     -- Replaced by newer lesson
        'deprecated',     -- No longer applicable
        'promoted'        -- Elevated to rule
    )),
    superseded_by UUID REFERENCES lcis_lessons(id),
    
    -- Metrics
    times_recalled INTEGER DEFAULT 0,         -- How often retrieved
    times_helpful INTEGER DEFAULT 0,          -- Confirmed helpful
    times_ignored INTEGER DEFAULT 0,          -- Retrieved but ignored
    confidence DECIMAL(5,2) DEFAULT 50.0,     -- 0-100 confidence score
    
    -- Provenance
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by TEXT,                          -- Who/what created
    verified_at TIMESTAMPTZ,
    verified_by TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast retrieval
CREATE INDEX idx_lcis_lessons_domain ON lcis_lessons(domain);
CREATE INDEX idx_lcis_lessons_type ON lcis_lessons(type);
CREATE INDEX idx_lcis_lessons_status ON lcis_lessons(status);
CREATE INDEX idx_lcis_lessons_tags ON lcis_lessons USING gin(tags);
CREATE INDEX idx_lcis_lessons_embedding ON lcis_lessons 
    USING ivfflat (embedding vector_cosine_ops);

-- Rules table (promoted lessons that BLOCK actions)
CREATE TABLE lcis_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES lcis_lessons(id),
    
    -- Rule definition
    name TEXT NOT NULL,                       -- Short name
    description TEXT NOT NULL,                -- Full description
    condition TEXT NOT NULL,                  -- When this rule applies
    action TEXT NOT NULL CHECK (action IN (
        'block',          -- Prevent the action
        'warn',           -- Allow but warn
        'require',        -- Must do something first
        'suggest'         -- Recommend alternative
    )),
    
    -- Scope
    applies_to TEXT[] DEFAULT '{}',           -- Agents this applies to ('*' = all)
    domains TEXT[] DEFAULT '{}',              -- Domains this applies to
    
    -- Alternatives
    alternatives JSONB DEFAULT '[]',          -- What to do instead
    
    -- Enforcement
    enforced BOOLEAN DEFAULT TRUE,
    enforcement_count INTEGER DEFAULT 0,      -- Times enforced
    override_count INTEGER DEFAULT 0,         -- Times overridden
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ                    -- Optional expiration
);

-- Playbooks (success recipes)
CREATE TABLE lcis_playbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL,
    description TEXT,
    domain TEXT NOT NULL,
    
    -- Steps
    steps JSONB NOT NULL,                     -- Ordered steps to follow
    prerequisites JSONB DEFAULT '[]',         -- What must be true first
    expected_outcome TEXT,
    
    -- Metrics
    times_used INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2),
    average_duration_minutes INTEGER,
    
    -- Source
    derived_from UUID[] DEFAULT '{}',         -- Lesson IDs this came from
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent domain knowledge (what each agent has learned)
CREATE TABLE lcis_agent_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL,
    lesson_id UUID REFERENCES lcis_lessons(id),
    
    relevance_score DECIMAL(5,2),             -- How relevant to this agent
    times_applied INTEGER DEFAULT 0,
    last_applied TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(agent, lesson_id)
);

-- Learning events (audit trail)
CREATE TABLE lcis_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    event_type TEXT NOT NULL CHECK (event_type IN (
        'lesson_created',
        'lesson_recalled',
        'lesson_helpful',
        'lesson_ignored',
        'lesson_superseded',
        'rule_enforced',
        'rule_overridden',
        'pattern_detected',
        'playbook_executed'
    )),
    
    lesson_id UUID REFERENCES lcis_lessons(id),
    rule_id UUID REFERENCES lcis_rules(id),
    playbook_id UUID REFERENCES lcis_playbooks(id),
    
    agent TEXT,
    context JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Function: Get relevant lessons before action
CREATE OR REPLACE FUNCTION lcis_consult(
    p_action TEXT,
    p_domain TEXT DEFAULT NULL,
    p_agent TEXT DEFAULT NULL,
    p_limit INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    type TEXT,
    content TEXT,
    severity TEXT,
    confidence DECIMAL,
    action_required TEXT
) AS $$
BEGIN
    -- First check for blocking rules
    RETURN QUERY
    SELECT 
        r.id,
        'rule'::TEXT as type,
        r.description as content,
        'critical'::TEXT as severity,
        100.0::DECIMAL as confidence,
        r.action as action_required
    FROM lcis_rules r
    WHERE r.enforced = TRUE
    AND (r.applies_to = '{}' OR r.applies_to @> ARRAY[p_agent] OR '*' = ANY(r.applies_to))
    AND (r.domains = '{}' OR r.domains @> ARRAY[p_domain])
    AND r.condition ILIKE '%' || p_action || '%';
    
    -- Then get relevant lessons
    RETURN QUERY
    SELECT 
        l.id,
        l.type,
        l.content,
        l.severity,
        l.confidence,
        NULL::TEXT as action_required
    FROM lcis_lessons l
    WHERE l.status = 'active'
    AND (p_domain IS NULL OR l.domain = p_domain)
    AND l.type IN ('failure', 'success', 'warning')
    ORDER BY l.confidence DESC, l.times_helpful DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;
```

---

## INTEGRATION POINTS

### 1. Claude Code Integration (MCP Tool)

Add to HEPHAESTUS MCP server:

```python
@mcp_tool
async def consult_oracle(
    intended_action: str,
    domain: str = None,
    context: str = None
) -> dict:
    """
    REQUIRED before any significant action.
    Returns relevant lessons, rules, and guidance.
    
    Usage:
        result = await consult_oracle(
            intended_action="Update ARIA's system prompt",
            domain="ARIA_SANCTUM",
            context="User requested personality change"
        )
        
        if not result["proceed"]:
            # Action blocked by rule
            return result["reason"]
        
        # Apply warnings
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
    """
    response = await httpx.post(
        "http://localhost:8052/consult",
        json={
            "action": intended_action,
            "domain": domain,
            "context": context,
            "agent": "claude_code"
        }
    )
    return response.json()

@mcp_tool
async def report_lesson(
    lesson: str,
    type: str,  # failure, success, insight
    domain: str,
    context: str = None,
    severity: str = "medium"
) -> dict:
    """
    Report a lesson learned.
    
    Usage:
        await report_lesson(
            lesson="Docker restart doesn't reload baked-in files - must rebuild image",
            type="failure",
            domain="THE_KEEP",
            context="Tried to update ARIA prompt by restarting container",
            severity="high"
        )
    """
    response = await httpx.post(
        "http://localhost:8050/ingest",
        json={
            "content": lesson,
            "type": type,
            "domain": domain,
            "context": context,
            "severity": severity,
            "source_agent": "claude_code",
            "source_type": "claude_code"
        }
    )
    return response.json()
```

### 2. Agent Integration (Middleware)

Every agent includes LCIS middleware:

```python
from lcis import LCISMiddleware

app = FastAPI()

# Add LCIS middleware
app.add_middleware(
    LCISMiddleware,
    agent_name="CHRONOS",
    domain="THE_KEEP",
    auto_consult=True,      # Auto-consult before actions
    auto_report=True        # Auto-report outcomes
)

@app.post("/backup")
async def create_backup(request: BackupRequest, lcis: LCISContext = Depends()):
    # LCIS middleware already consulted oracle
    if lcis.blocked:
        raise HTTPException(400, lcis.block_reason)
    
    # Warnings are in context
    for warning in lcis.warnings:
        logger.warning(f"LCIS Warning: {warning}")
    
    # Perform action
    result = await perform_backup()
    
    # Report outcome (auto if auto_report=True)
    if result.success:
        await lcis.report_success(
            f"Backup completed: {result.size}MB in {result.duration}s"
        )
    else:
        await lcis.report_failure(
            f"Backup failed: {result.error}",
            severity="high"
        )
    
    return result
```

### 3. n8n Integration

Create LCIS nodes for n8n workflows:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ LCIS Consult    │────▶│ Your Workflow   │────▶│ LCIS Report     │
│                 │     │                 │     │                 │
│ Before action,  │     │ Do the thing    │     │ After action,   │
│ check for rules │     │                 │     │ report outcome  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 4. ARIA Integration

ARIA has full read access to all knowledge:

```python
# In ARIA's context injection
async def get_lcis_context() -> str:
    """Get recent lessons relevant to current conversation"""
    
    # Get recent failures (last 24h)
    recent_failures = await lcis.get_recent(type="failure", hours=24, limit=5)
    
    # Get active rules
    active_rules = await lcis.get_rules(enforced=True)
    
    # Get relevant playbooks
    playbooks = await lcis.get_playbooks(domain=current_domain)
    
    return f"""
## COLLECTIVE INTELLIGENCE CONTEXT

**Recent Failures (Don't Repeat):**
{format_lessons(recent_failures)}

**Active Rules:**
{format_rules(active_rules)}

**Available Playbooks:**
{format_playbooks(playbooks)}
"""
```

---

## KNOWLEDGE FLOW

### 1. Learning From Failure

```
Agent Fails
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ LIBRARIAN receives failure report                    │
│ - What was attempted                                 │
│ - What went wrong                                    │
│ - What was the context                               │
│ - What would have worked                             │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ LIBRARIAN processes:                                 │
│ 1. Generate embedding                                │
│ 2. Check for duplicates                              │
│ 3. Categorize by domain                              │
│ 4. Assign severity                                   │
│ 5. Store lesson                                      │
│ 6. Propagate to relevant agents                      │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ PROFESSOR analyzes:                                  │
│ - Is this a repeat? (create RULE if 3+)             │
│ - Related to other failures?                         │
│ - Domain-specific or global?                         │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ Future: Agent attempts similar action                │
│ ORACLE blocks/warns with lesson                      │
└─────────────────────────────────────────────────────┘
```

### 2. Learning From Success

```
Agent Succeeds
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ LIBRARIAN receives success report                    │
│ - What was attempted                                 │
│ - What worked                                        │
│ - Why it worked                                      │
│ - Steps taken                                        │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ PROFESSOR analyzes:                                  │
│ - Is this a repeatable pattern?                      │
│ - Can it become a playbook?                          │
│ - Applicable to other domains?                       │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ If pattern detected:                                 │
│ - Create playbook                                    │
│ - Propagate to relevant agents                       │
│ - Notify ARIA                                        │
└─────────────────────────────────────────────────────┘
```

### 3. Rule Promotion

```
Same failure 3+ times
    │
    ▼
┌─────────────────────────────────────────────────────┐
│ PROFESSOR detects pattern:                           │
│ "Container restart doesn't reload baked files"       │
│ occurred 4 times in 7 days                           │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ Create RULE:                                         │
│ Name: "Docker Image Rebuild Required"                │
│ Condition: "update.*prompt|config.*change"           │
│ Action: REQUIRE                                      │
│ Requirement: "Rebuild Docker image, not just restart"│
│ Applies to: ['*']                                    │
└───────────────────────────┬─────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────┐
│ ORACLE now enforces:                                 │
│ Any agent attempting to update configs               │
│ gets requirement to rebuild image                    │
└─────────────────────────────────────────────────────┘
```

---

## CLAUDE CODE EXECUTION RULES INTEGRATION

Add to EXECUTION_RULES.md:

```markdown
## Rule #13: LCIS INTEGRATION (Collective Intelligence)

Before ANY significant action, Claude Code MUST:

1. **Consult ORACLE:**
   ```python
   guidance = await consult_oracle(
       intended_action="description of what you're about to do",
       domain="relevant domain",
       context="why you're doing it"
   )
   
   if not guidance["proceed"]:
       # STOP - action blocked by rule
       # Report to user, suggest alternatives
   
   if guidance["warnings"]:
       # Review warnings before proceeding
   ```

2. **Report Outcomes:**
   ```python
   # After success
   await report_lesson(
       lesson="What worked and why",
       type="success",
       domain="domain",
       context="full context"
   )
   
   # After failure
   await report_lesson(
       lesson="What failed and why",
       type="failure",
       domain="domain",
       severity="high" if critical else "medium"
   )
   ```

3. **Never Retry Known Failures:**
   If ORACLE returns a matching failure, DO NOT attempt the same approach.
   Ask user for alternative or suggest one based on lessons.

4. **Follow Playbooks:**
   If ORACLE returns a relevant playbook, FOLLOW IT.
   Don't improvise when a proven recipe exists.
```

---

## INITIAL KNOWLEDGE SEEDING

Import existing lessons from LESSONS-LEARNED.md:

```python
# One-time migration
async def seed_from_lessons_learned():
    lessons_md = open("/opt/leveredge/LESSONS-LEARNED.md").read()
    
    # Parse markdown into lessons
    lessons = parse_lessons_markdown(lessons_md)
    
    for lesson in lessons:
        await librarian.ingest_lesson(Lesson(
            content=lesson.content,
            type=lesson.type,
            domain=lesson.domain,
            source_type="import",
            source_context={"source": "LESSONS-LEARNED.md migration"}
        ))
```

---

## BUILD PHASES

| Phase | Components | Effort | Priority |
|-------|------------|--------|----------|
| 1 | Database schema + tables | 2 hrs | HIGH |
| 2 | LIBRARIAN (ingestion) | 4 hrs | HIGH |
| 3 | ORACLE (retrieval) | 4 hrs | HIGH |
| 4 | Claude Code MCP tools | 2 hrs | HIGH |
| 5 | PROFESSOR (patterns) | 4 hrs | MEDIUM |
| 6 | Agent middleware | 4 hrs | MEDIUM |
| 7 | n8n nodes | 3 hrs | LOW |
| 8 | ARIA integration | 2 hrs | MEDIUM |
| 9 | Migration script | 2 hrs | HIGH |

**Total: ~27 hours**

**Recommended MVP:** Phases 1, 2, 3, 4, 9 = ~14 hours
This gives you:
- Database to store lessons
- Ingestion endpoint
- Retrieval endpoint
- Claude Code integration
- Existing lessons migrated

---

## SUCCESS CRITERIA

### Functional
- [ ] Claude Code consults ORACLE before actions
- [ ] Failures are auto-reported
- [ ] Duplicate failures are blocked
- [ ] Successes create playbooks
- [ ] Rules enforce constraints

### Quality
- [ ] Same mistake never happens twice
- [ ] Success patterns are replicated
- [ ] Cross-domain learning occurs
- [ ] Confidence scores improve over time

### Visibility
- [ ] ARIA knows all lessons
- [ ] VARYS tracks learning metrics
- [ ] Damon can query knowledge base
- [ ] Dashboard shows learning trends

---

## EXAMPLE INTERACTIONS

### Claude Code Prevented From Repeating Mistake

```
Claude Code: I'll update the ARIA prompt by editing the file and restarting the container.

ORACLE Response:
{
  "proceed": false,
  "blocked_by_rule": "Docker Image Rebuild Required",
  "reason": "Prompt is baked into image at build time. Restart won't reload.",
  "alternatives": [
    "Rebuild Docker image: docker build -t aria-chat:dev .",
    "Use volume mount for hot-reload (recommended for dev)"
  ],
  "related_failures": [
    "Jan 18: ARIA prompt not updating after restart (4 occurrences)"
  ]
}

Claude Code: I'll rebuild the Docker image instead.
```

### Agent Auto-Learning

```
CHRONOS: Backup to /tmp failed - no space left on device.

LIBRARIAN: Ingested lesson:
- Type: failure
- Severity: high
- Content: "Backup to /tmp fails when temp space is limited"
- Domain: THE_KEEP
- Tags: [backup, disk_space, tmp]

PROFESSOR: Pattern detected - third backup space failure this week.
Creating rule: "Check disk space before backup operations"

Future: All backup attempts now check disk space first (ORACLE enforces)
```

---

## GIT COMMIT MESSAGE

```
Add LCIS (LeverEdge Collective Intelligence System) specification

- LIBRARIAN (8050): Knowledge ingestion and storage
- PROFESSOR (8051): Pattern detection and rule promotion
- ORACLE (8052): Pre-action retrieval and enforcement
- Database schema with pgvector for semantic search
- Claude Code MCP integration
- Agent middleware specification
- Migration plan from LESSONS-LEARNED.md
```

---

*"The fleet that learns together, wins together."*
