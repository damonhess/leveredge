# MNEMOSYNE: LeverEdge Self-Learning Architecture

**Version:** 1.0
**Status:** SPECIFICATION
**Named After:** Greek Titaness of Memory, mother of the Muses

---

## EXECUTIVE SUMMARY

MNEMOSYNE is the collective memory and learning system for LeverEdge. It ensures:

1. **Claude Code never retries known-failed approaches**
2. **Agents learn from their own and others' experiences**
3. **Lessons propagate automatically to relevant contexts**
4. **Patterns are detected and anti-patterns are flagged**
5. **ARIA, VARYS, and supervisors have full visibility**

---

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MNEMOSYNE LEARNING SYSTEM                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      KNOWLEDGE INGESTION                             │   │
│  │                                                                      │   │
│  │   Claude Code ──┐                                                    │   │
│  │   CHRONOS ──────┤                                                    │   │
│  │   HADES ────────┼──→ lesson_reporter.py ──→ MNEMOSYNE API ──┐       │   │
│  │   AEGIS ────────┤                              (Port 8025)   │       │   │
│  │   All Agents ───┘                                            │       │   │
│  └──────────────────────────────────────────────────────────────│───────┘   │
│                                                                 │           │
│  ┌──────────────────────────────────────────────────────────────▼───────┐   │
│  │                      KNOWLEDGE STORE (Supabase)                      │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │
│  │  │ mnemosyne_      │  │ mnemosyne_      │  │ mnemosyne_      │      │   │
│  │  │ lessons         │  │ patterns        │  │ anti_patterns   │      │   │
│  │  │                 │  │                 │  │                 │      │   │
│  │  │ - lesson_type   │  │ - pattern_name  │  │ - trigger       │      │   │
│  │  │ - domain        │  │ - occurrences   │  │ - failure_count │      │   │
│  │  │ - context       │  │ - confidence    │  │ - block_action  │      │   │
│  │  │ - outcome       │  │ - agents        │  │ - alternatives  │      │   │
│  │  │ - embedding     │  │ - last_seen     │  │ - severity      │      │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │   │
│  │                                                                      │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐      │   │
│  │  │ mnemosyne_      │  │ mnemosyne_      │  │ mnemosyne_      │      │   │
│  │  │ agent_memory    │  │ escalations     │  │ validations     │      │   │
│  │  │                 │  │                 │  │                 │      │   │
│  │  │ - agent_id      │  │ - lesson_id     │  │ - lesson_id     │      │   │
│  │  │ - lessons[]     │  │ - escalated_to  │  │ - validated_by  │      │   │
│  │  │ - last_sync     │  │ - reason        │  │ - outcome       │      │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘      │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      KNOWLEDGE RETRIEVAL                              │   │
│  │                                                                       │   │
│  │   Before Action ──→ Query MNEMOSYNE ──→ Get Relevant Lessons         │   │
│  │                          │                                            │   │
│  │                          ├──→ Anti-Pattern Check (BLOCK if matched)  │   │
│  │                          ├──→ Similar Context Search (LEARN from)    │   │
│  │                          └──→ Inject into Prompt/Context             │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                      KNOWLEDGE PROPAGATION                            │   │
│  │                                                                       │   │
│  │   New Lesson ──→ Pattern Detection ──→ Escalation Check              │   │
│  │                          │                     │                      │   │
│  │                          │                     ├──→ ARIA (always)    │   │
│  │                          │                     ├──→ VARYS (project)  │   │
│  │                          │                     └──→ Domain Super     │   │
│  │                          │                                            │   │
│  │                          └──→ Cross-Agent Learning                   │   │
│  │                                (if applicable to other domains)       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## CORE COMPONENTS

### 1. MNEMOSYNE Service (Port 8025)

Central API for all learning operations.

```python
# /opt/leveredge/control-plane/agents/mnemosyne/mnemosyne.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import httpx
from enum import Enum

app = FastAPI(title="MNEMOSYNE - Collective Memory", version="1.0.0")

class LessonType(str, Enum):
    SUCCESS = "success"           # What worked
    FAILURE = "failure"           # What failed
    WORKAROUND = "workaround"     # How to work around a problem
    DISCOVERY = "discovery"       # New information learned
    OPTIMIZATION = "optimization" # Better way to do something
    WARNING = "warning"           # Potential issue to watch for
    ANTI_PATTERN = "anti_pattern" # Never do this

class Severity(str, Enum):
    CRITICAL = "critical"   # Blocks work, must know
    HIGH = "high"           # Important, should know
    MEDIUM = "medium"       # Useful, nice to know
    LOW = "low"             # Minor, optional

class Lesson(BaseModel):
    """A single learned lesson"""
    lesson_type: LessonType
    domain: str                    # infrastructure, security, business, etc.
    category: str                  # More specific: docker, supabase, n8n, etc.
    title: str                     # Short description
    context: str                   # What was happening
    action_taken: str              # What was done
    outcome: str                   # What happened
    root_cause: Optional[str]      # Why it happened
    solution: Optional[str]        # How to fix/avoid
    alternatives: List[str] = []   # Other approaches
    severity: Severity = Severity.MEDIUM
    tags: List[str] = []
    source_agent: str              # Who learned this
    related_files: List[str] = []  # Files involved
    related_commands: List[str] = [] # Commands involved
    confidence: float = 0.8        # How sure are we (0-1)

class AntiPatternCheck(BaseModel):
    """Check if an action matches known anti-patterns"""
    proposed_action: str
    context: str
    domain: str
    agent: str

class AntiPatternResult(BaseModel):
    """Result of anti-pattern check"""
    blocked: bool
    matching_patterns: List[Dict[str, Any]]
    alternatives: List[str]
    warnings: List[str]

class ContextQuery(BaseModel):
    """Query for relevant lessons"""
    context: str
    domain: Optional[str]
    agent: Optional[str]
    include_cross_domain: bool = True
    max_results: int = 10

# ============ INGESTION ENDPOINTS ============

@app.post("/lessons/report")
async def report_lesson(lesson: Lesson) -> Dict[str, Any]:
    """
    Report a new lesson learned.
    
    Called by agents after any significant success, failure, or discovery.
    """
    # Generate embedding for semantic search
    embedding = await generate_embedding(
        f"{lesson.title} {lesson.context} {lesson.outcome}"
    )
    
    # Store in database
    lesson_id = await store_lesson(lesson, embedding)
    
    # Check for pattern formation
    patterns = await detect_patterns(lesson)
    
    # Check if escalation needed
    escalations = await check_escalation(lesson, patterns)
    
    # Propagate to relevant agents
    await propagate_lesson(lesson)
    
    return {
        "lesson_id": lesson_id,
        "patterns_detected": len(patterns),
        "escalated_to": escalations,
        "status": "recorded"
    }

@app.post("/lessons/bulk")
async def report_bulk_lessons(lessons: List[Lesson]) -> Dict[str, Any]:
    """Report multiple lessons at once (e.g., from LESSONS-LEARNED migration)"""
    results = []
    for lesson in lessons:
        result = await report_lesson(lesson)
        results.append(result)
    return {"processed": len(results), "results": results}

# ============ RETRIEVAL ENDPOINTS ============

@app.post("/check/anti-pattern")
async def check_anti_pattern(check: AntiPatternCheck) -> AntiPatternResult:
    """
    Check if a proposed action matches known anti-patterns.
    
    CALL THIS BEFORE TAKING ACTION.
    """
    # Search for matching anti-patterns
    matches = await search_anti_patterns(
        action=check.proposed_action,
        context=check.context,
        domain=check.domain
    )
    
    blocked = any(m["severity"] == "critical" for m in matches)
    
    alternatives = []
    warnings = []
    
    for match in matches:
        if match.get("alternatives"):
            alternatives.extend(match["alternatives"])
        warnings.append(f"⚠️ {match['title']}: {match['why_bad']}")
    
    return AntiPatternResult(
        blocked=blocked,
        matching_patterns=matches,
        alternatives=list(set(alternatives)),
        warnings=warnings
    )

@app.post("/query/relevant")
async def query_relevant_lessons(query: ContextQuery) -> List[Dict[str, Any]]:
    """
    Get lessons relevant to current context.
    
    CALL THIS AT START OF TASK.
    """
    # Generate query embedding
    embedding = await generate_embedding(query.context)
    
    # Semantic search
    results = await semantic_search(
        embedding=embedding,
        domain=query.domain,
        include_cross_domain=query.include_cross_domain,
        limit=query.max_results
    )
    
    # Sort by relevance and recency
    results = sorted(
        results,
        key=lambda x: (x["similarity"] * 0.7 + x["recency_score"] * 0.3),
        reverse=True
    )
    
    return results

@app.get("/agent/{agent_name}/memory")
async def get_agent_memory(agent_name: str) -> Dict[str, Any]:
    """
    Get all lessons relevant to a specific agent.
    
    For injecting into agent system prompts.
    """
    lessons = await get_agent_lessons(agent_name)
    anti_patterns = await get_domain_anti_patterns(agent_name)
    
    return {
        "agent": agent_name,
        "lessons_count": len(lessons),
        "critical_lessons": [l for l in lessons if l["severity"] == "critical"],
        "recent_lessons": lessons[:20],
        "anti_patterns": anti_patterns,
        "last_updated": datetime.now().isoformat()
    }

@app.get("/patterns/emerging")
async def get_emerging_patterns() -> List[Dict[str, Any]]:
    """Get patterns that are forming but not yet confirmed"""
    return await query_emerging_patterns()

@app.get("/escalations/pending")
async def get_pending_escalations() -> List[Dict[str, Any]]:
    """Get lessons that need supervisor review"""
    return await query_pending_escalations()

# ============ VALIDATION ENDPOINTS ============

@app.post("/lessons/{lesson_id}/validate")
async def validate_lesson(
    lesson_id: str, 
    validated: bool, 
    validated_by: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Mark a lesson as validated or invalidated.
    
    Validated lessons get higher confidence and priority.
    """
    await update_lesson_validation(lesson_id, validated, validated_by, notes)
    
    if validated:
        await increase_lesson_confidence(lesson_id)
    else:
        await decrease_lesson_confidence(lesson_id)
    
    return {"status": "validated" if validated else "invalidated"}

@app.post("/patterns/{pattern_id}/confirm")
async def confirm_pattern(pattern_id: str, confirmed_by: str) -> Dict[str, Any]:
    """Confirm a pattern is real and should be enforced"""
    await update_pattern_status(pattern_id, "confirmed", confirmed_by)
    return {"status": "confirmed"}

# ============ CLAUDE CODE INTEGRATION ============

@app.get("/claude-code/context")
async def get_claude_code_context() -> Dict[str, Any]:
    """
    Get full learning context for Claude Code.
    
    This is injected into EXECUTION_RULES.md or session context.
    """
    return {
        "critical_anti_patterns": await get_critical_anti_patterns(),
        "recent_failures": await get_recent_failures(hours=72),
        "active_workarounds": await get_active_workarounds(),
        "domain_lessons": {
            "docker": await get_domain_lessons("docker"),
            "supabase": await get_domain_lessons("supabase"),
            "n8n": await get_domain_lessons("n8n"),
            "caddy": await get_domain_lessons("caddy"),
            "aria": await get_domain_lessons("aria"),
        },
        "last_session_lessons": await get_last_session_lessons(),
        "generated_at": datetime.now().isoformat()
    }

@app.post("/claude-code/session-end")
async def session_end_report(lessons: List[Lesson]) -> Dict[str, Any]:
    """
    Called at end of Claude Code session to report all lessons learned.
    """
    return await report_bulk_lessons(lessons)
```

### 2. Lesson Reporter Module

Shared module for all agents to report lessons.

```python
# /opt/leveredge/shared/lesson_reporter.py

"""
MNEMOSYNE Lesson Reporter

Usage:
    from shared.lesson_reporter import LessonReporter
    
    reporter = LessonReporter("CHRONOS")
    
    # Report a failure
    await reporter.failure(
        title="PostgreSQL permission denied on /var/lib/postgresql/data",
        context="Running backup after container restart",
        action_taken="Attempted to run pg_dump",
        outcome="Permission denied error",
        root_cause="Container UID mismatch after postgres upgrade",
        solution="Run: docker exec <container> chown -R postgres:postgres /var/lib/postgresql/data",
        tags=["docker", "postgres", "permissions"]
    )
    
    # Report a success
    await reporter.success(
        title="Backup completed with streaming compression",
        context="Nightly backup routine",
        action_taken="Used pg_dump | gzip pipeline",
        outcome="Backup size reduced 70%, time reduced 40%",
        tags=["backup", "optimization"]
    )
    
    # Check before taking action
    result = await reporter.check_before_action(
        "docker exec -it container rm -rf /data",
        context="Cleaning up old data"
    )
    if result.blocked:
        print(f"BLOCKED: {result.warnings}")
        print(f"Try instead: {result.alternatives}")
"""

import os
import httpx
from typing import List, Optional, Dict, Any
from enum import Enum

class LessonReporter:
    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.mnemosyne_url = os.environ.get(
            "MNEMOSYNE_URL", 
            "http://localhost:8025"
        )
        self.enabled = os.environ.get("LEARNING_ENABLED", "true").lower() == "true"
        
        # Infer domain from agent
        self.domain = self._infer_domain()
    
    def _infer_domain(self) -> str:
        domain_map = {
            "CHRONOS": "infrastructure",
            "HADES": "infrastructure", 
            "AEGIS": "security",
            "HERMES": "notifications",
            "ARGUS": "monitoring",
            "PANOPTES": "security",
            "ASCLEPIUS": "health",
            "SCHOLAR": "research",
            "CHIRON": "business",
            "CONSUL": "project_management",
            "DAEDALUS": "infrastructure",
            "MUSE": "creative",
            "QUILL": "creative",
            "STAGE": "creative",
            "REEL": "creative",
            "CRITIC": "creative",
            "VARYS": "oversight",
            "ARIA": "assistant",
            "CLAUDE_CODE": "development",
        }
        return domain_map.get(self.agent_name, "general")
    
    async def _report(self, lesson: Dict[str, Any]) -> Dict[str, Any]:
        if not self.enabled:
            return {"status": "disabled"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mnemosyne_url}/lessons/report",
                    json=lesson,
                    timeout=10.0
                )
                return response.json()
        except Exception as e:
            print(f"[{self.agent_name}] Failed to report lesson: {e}")
            return {"status": "error", "error": str(e)}
    
    async def success(
        self,
        title: str,
        context: str,
        action_taken: str,
        outcome: str,
        tags: List[str] = [],
        category: Optional[str] = None,
        confidence: float = 0.9
    ) -> Dict[str, Any]:
        """Report a successful approach"""
        return await self._report({
            "lesson_type": "success",
            "domain": self.domain,
            "category": category or self.domain,
            "title": title,
            "context": context,
            "action_taken": action_taken,
            "outcome": outcome,
            "severity": "medium",
            "tags": tags,
            "source_agent": self.agent_name,
            "confidence": confidence
        })
    
    async def failure(
        self,
        title: str,
        context: str,
        action_taken: str,
        outcome: str,
        root_cause: Optional[str] = None,
        solution: Optional[str] = None,
        alternatives: List[str] = [],
        tags: List[str] = [],
        category: Optional[str] = None,
        severity: str = "medium",
        related_commands: List[str] = []
    ) -> Dict[str, Any]:
        """Report a failure and what was learned"""
        return await self._report({
            "lesson_type": "failure",
            "domain": self.domain,
            "category": category or self.domain,
            "title": title,
            "context": context,
            "action_taken": action_taken,
            "outcome": outcome,
            "root_cause": root_cause,
            "solution": solution,
            "alternatives": alternatives,
            "severity": severity,
            "tags": tags,
            "source_agent": self.agent_name,
            "related_commands": related_commands,
            "confidence": 0.8
        })
    
    async def anti_pattern(
        self,
        title: str,
        why_bad: str,
        example: str,
        alternatives: List[str],
        severity: str = "high",
        tags: List[str] = [],
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Report something that should NEVER be done"""
        return await self._report({
            "lesson_type": "anti_pattern",
            "domain": self.domain,
            "category": category or self.domain,
            "title": title,
            "context": why_bad,
            "action_taken": example,
            "outcome": "BLOCKED - Known anti-pattern",
            "alternatives": alternatives,
            "severity": severity,
            "tags": tags + ["anti-pattern", "blocked"],
            "source_agent": self.agent_name,
            "confidence": 1.0
        })
    
    async def workaround(
        self,
        title: str,
        problem: str,
        workaround: str,
        permanent_fix: Optional[str] = None,
        tags: List[str] = [],
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Report a workaround for a known issue"""
        return await self._report({
            "lesson_type": "workaround",
            "domain": self.domain,
            "category": category or self.domain,
            "title": title,
            "context": problem,
            "action_taken": workaround,
            "outcome": "Issue mitigated",
            "solution": permanent_fix,
            "severity": "medium",
            "tags": tags + ["workaround"],
            "source_agent": self.agent_name,
            "confidence": 0.85
        })
    
    async def discovery(
        self,
        title: str,
        context: str,
        discovery: str,
        implications: List[str] = [],
        tags: List[str] = [],
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Report a new discovery or insight"""
        return await self._report({
            "lesson_type": "discovery",
            "domain": self.domain,
            "category": category or self.domain,
            "title": title,
            "context": context,
            "action_taken": "Investigation/observation",
            "outcome": discovery,
            "alternatives": implications,
            "severity": "medium",
            "tags": tags + ["discovery"],
            "source_agent": self.agent_name,
            "confidence": 0.7
        })
    
    async def check_before_action(
        self,
        proposed_action: str,
        context: str
    ) -> Dict[str, Any]:
        """
        Check if proposed action matches known anti-patterns.
        
        CALL THIS BEFORE TAKING RISKY ACTIONS.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mnemosyne_url}/check/anti-pattern",
                    json={
                        "proposed_action": proposed_action,
                        "context": context,
                        "domain": self.domain,
                        "agent": self.agent_name
                    },
                    timeout=5.0
                )
                return response.json()
        except Exception as e:
            # Don't block on check failure, but warn
            print(f"[{self.agent_name}] Anti-pattern check failed: {e}")
            return {"blocked": False, "warnings": ["Check failed - proceed with caution"]}
    
    async def get_relevant_lessons(self, context: str, max_results: int = 10) -> List[Dict]:
        """Get lessons relevant to current task"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.mnemosyne_url}/query/relevant",
                    json={
                        "context": context,
                        "domain": self.domain,
                        "agent": self.agent_name,
                        "max_results": max_results
                    },
                    timeout=5.0
                )
                return response.json()
        except Exception as e:
            print(f"[{self.agent_name}] Failed to get lessons: {e}")
            return []


# Convenience function for one-off reports
async def quick_lesson(
    agent: str,
    lesson_type: str,
    title: str,
    context: str,
    outcome: str,
    **kwargs
) -> Dict[str, Any]:
    """Quick one-off lesson report"""
    reporter = LessonReporter(agent)
    method = getattr(reporter, lesson_type, reporter.discovery)
    return await method(title=title, context=context, outcome=outcome, **kwargs)
```

### 3. Database Schema

```sql
-- /opt/leveredge/specs/mnemosyne-schema.sql

-- Enable pgvector for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- Main lessons table
CREATE TABLE mnemosyne_lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_type TEXT NOT NULL CHECK (lesson_type IN (
        'success', 'failure', 'workaround', 'discovery', 
        'optimization', 'warning', 'anti_pattern'
    )),
    domain TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    context TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    outcome TEXT NOT NULL,
    root_cause TEXT,
    solution TEXT,
    alternatives TEXT[] DEFAULT '{}',
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    tags TEXT[] DEFAULT '{}',
    source_agent TEXT NOT NULL,
    related_files TEXT[] DEFAULT '{}',
    related_commands TEXT[] DEFAULT '{}',
    confidence DECIMAL(3,2) DEFAULT 0.80,
    
    -- Validation
    validated BOOLEAN DEFAULT FALSE,
    validated_by TEXT,
    validated_at TIMESTAMPTZ,
    validation_notes TEXT,
    
    -- Embeddings for semantic search
    embedding VECTOR(1536),
    
    -- Tracking
    occurrence_count INTEGER DEFAULT 1,
    last_occurred TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_lessons_type ON mnemosyne_lessons(lesson_type);
CREATE INDEX idx_lessons_domain ON mnemosyne_lessons(domain);
CREATE INDEX idx_lessons_category ON mnemosyne_lessons(category);
CREATE INDEX idx_lessons_severity ON mnemosyne_lessons(severity);
CREATE INDEX idx_lessons_agent ON mnemosyne_lessons(source_agent);
CREATE INDEX idx_lessons_tags ON mnemosyne_lessons USING GIN(tags);
CREATE INDEX idx_lessons_embedding ON mnemosyne_lessons 
    USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_lessons_created ON mnemosyne_lessons(created_at DESC);

-- Detected patterns (multiple similar lessons)
CREATE TABLE mnemosyne_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_name TEXT NOT NULL,
    pattern_type TEXT NOT NULL CHECK (pattern_type IN (
        'recurring_failure', 'common_solution', 'best_practice', 
        'anti_pattern', 'optimization'
    )),
    description TEXT NOT NULL,
    domain TEXT NOT NULL,
    categories TEXT[] DEFAULT '{}',
    
    -- Pattern evidence
    lesson_ids UUID[] NOT NULL,
    occurrence_count INTEGER DEFAULT 1,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    
    -- Pattern confidence
    confidence DECIMAL(3,2) DEFAULT 0.50,
    status TEXT DEFAULT 'emerging' CHECK (status IN (
        'emerging', 'confirmed', 'deprecated'
    )),
    confirmed_by TEXT,
    confirmed_at TIMESTAMPTZ,
    
    -- Actions
    recommended_action TEXT,
    prevention_steps TEXT[],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_patterns_type ON mnemosyne_patterns(pattern_type);
CREATE INDEX idx_patterns_domain ON mnemosyne_patterns(domain);
CREATE INDEX idx_patterns_status ON mnemosyne_patterns(status);

-- Anti-patterns (things to block)
CREATE TABLE mnemosyne_anti_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_pattern TEXT NOT NULL,  -- Regex or keyword pattern to match
    trigger_embedding VECTOR(1536), -- For semantic matching
    domain TEXT NOT NULL,
    category TEXT,
    
    -- What it catches
    title TEXT NOT NULL,
    why_bad TEXT NOT NULL,
    example TEXT,
    
    -- What to do instead
    alternatives TEXT[] NOT NULL,
    
    -- Enforcement
    severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    block_action BOOLEAN DEFAULT FALSE,  -- If true, hard block
    
    -- Source
    source_lesson_id UUID REFERENCES mnemosyne_lessons(id),
    source_pattern_id UUID REFERENCES mnemosyne_patterns(id),
    
    -- Stats
    times_triggered INTEGER DEFAULT 0,
    last_triggered TIMESTAMPTZ,
    
    -- Status
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_anti_patterns_domain ON mnemosyne_anti_patterns(domain);
CREATE INDEX idx_anti_patterns_active ON mnemosyne_anti_patterns(active);
CREATE INDEX idx_anti_patterns_severity ON mnemosyne_anti_patterns(severity);

-- Per-agent memory cache
CREATE TABLE mnemosyne_agent_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name TEXT NOT NULL UNIQUE,
    domain TEXT NOT NULL,
    
    -- Cached lessons for this agent
    relevant_lessons JSONB DEFAULT '[]',
    anti_patterns JSONB DEFAULT '[]',
    
    -- Sync tracking
    last_sync TIMESTAMPTZ DEFAULT NOW(),
    lessons_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_agent_memory_name ON mnemosyne_agent_memory(agent_name);

-- Escalations for supervisor review
CREATE TABLE mnemosyne_escalations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES mnemosyne_lessons(id),
    pattern_id UUID REFERENCES mnemosyne_patterns(id),
    
    escalated_to TEXT NOT NULL,  -- ARIA, VARYS, domain supervisor
    reason TEXT NOT NULL,
    priority TEXT NOT NULL CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    
    -- Resolution
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'reviewed', 'resolved', 'dismissed')),
    resolved_by TEXT,
    resolved_at TIMESTAMPTZ,
    resolution_notes TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_escalations_status ON mnemosyne_escalations(status);
CREATE INDEX idx_escalations_to ON mnemosyne_escalations(escalated_to);

-- Validation history
CREATE TABLE mnemosyne_validations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID REFERENCES mnemosyne_lessons(id),
    validated_by TEXT NOT NULL,
    validation_type TEXT NOT NULL CHECK (validation_type IN (
        'confirmed', 'refuted', 'partial', 'outdated'
    )),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Functions for common operations

-- Semantic search for lessons
CREATE OR REPLACE FUNCTION mnemosyne_search(
    query_embedding VECTOR(1536),
    search_domain TEXT DEFAULT NULL,
    search_type TEXT DEFAULT NULL,
    result_limit INT DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    lesson_type TEXT,
    title TEXT,
    context TEXT,
    outcome TEXT,
    solution TEXT,
    severity TEXT,
    confidence DECIMAL,
    similarity FLOAT,
    created_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        l.id,
        l.lesson_type,
        l.title,
        l.context,
        l.outcome,
        l.solution,
        l.severity,
        l.confidence,
        1 - (l.embedding <=> query_embedding) as similarity,
        l.created_at
    FROM mnemosyne_lessons l
    WHERE (search_domain IS NULL OR l.domain = search_domain)
    AND (search_type IS NULL OR l.lesson_type = search_type)
    AND l.embedding IS NOT NULL
    ORDER BY l.embedding <=> query_embedding
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Get critical lessons for an agent
CREATE OR REPLACE FUNCTION mnemosyne_agent_critical(agent_domain TEXT)
RETURNS TABLE (
    id UUID,
    title TEXT,
    solution TEXT,
    severity TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT l.id, l.title, l.solution, l.severity
    FROM mnemosyne_lessons l
    WHERE l.domain = agent_domain
    AND l.severity IN ('critical', 'high')
    AND l.confidence > 0.7
    ORDER BY 
        CASE l.severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 END,
        l.created_at DESC
    LIMIT 20;
END;
$$ LANGUAGE plpgsql;

-- Increment occurrence and update timestamp when same lesson occurs
CREATE OR REPLACE FUNCTION mnemosyne_record_occurrence(
    matching_title TEXT,
    matching_domain TEXT
)
RETURNS UUID AS $$
DECLARE
    lesson_id UUID;
BEGIN
    UPDATE mnemosyne_lessons
    SET occurrence_count = occurrence_count + 1,
        last_occurred = NOW(),
        updated_at = NOW()
    WHERE title = matching_title AND domain = matching_domain
    RETURNING id INTO lesson_id;
    
    RETURN lesson_id;
END;
$$ LANGUAGE plpgsql;

-- View for ARIA dashboard
CREATE VIEW mnemosyne_dashboard AS
SELECT
    (SELECT COUNT(*) FROM mnemosyne_lessons) as total_lessons,
    (SELECT COUNT(*) FROM mnemosyne_lessons WHERE lesson_type = 'failure') as failures,
    (SELECT COUNT(*) FROM mnemosyne_lessons WHERE lesson_type = 'success') as successes,
    (SELECT COUNT(*) FROM mnemosyne_lessons WHERE lesson_type = 'anti_pattern') as anti_patterns,
    (SELECT COUNT(*) FROM mnemosyne_patterns WHERE status = 'confirmed') as confirmed_patterns,
    (SELECT COUNT(*) FROM mnemosyne_escalations WHERE status = 'pending') as pending_escalations,
    (SELECT COUNT(*) FROM mnemosyne_lessons WHERE created_at > NOW() - INTERVAL '24 hours') as lessons_today,
    (SELECT COUNT(*) FROM mnemosyne_lessons WHERE created_at > NOW() - INTERVAL '7 days') as lessons_this_week;
```

### 4. Claude Code Integration

Add to EXECUTION_RULES.md:

```markdown
## Rule #13: MNEMOSYNE LEARNING SYSTEM

Before starting any task, Claude Code should:

1. **Query relevant lessons:**
   ```bash
   curl -s http://localhost:8025/query/relevant \
     -H "Content-Type: application/json" \
     -d '{"context": "YOUR_TASK_DESCRIPTION", "domain": "infrastructure"}' | jq .
   ```

2. **Check anti-patterns before risky actions:**
   ```bash
   curl -s http://localhost:8025/check/anti-pattern \
     -H "Content-Type: application/json" \
     -d '{"proposed_action": "YOUR_COMMAND", "context": "WHY", "domain": "docker", "agent": "CLAUDE_CODE"}' | jq .
   ```

3. **Report lessons at end of session:**
   - All failures encountered
   - All workarounds discovered
   - All successful approaches
   - Any new anti-patterns identified

### Quick Report Commands

```bash
# Report a failure
curl -X POST http://localhost:8025/lessons/report \
  -H "Content-Type: application/json" \
  -d '{
    "lesson_type": "failure",
    "domain": "docker",
    "category": "containers",
    "title": "Brief description",
    "context": "What was happening",
    "action_taken": "What was tried",
    "outcome": "What happened",
    "root_cause": "Why it happened",
    "solution": "How to fix",
    "severity": "high",
    "tags": ["docker", "permissions"],
    "source_agent": "CLAUDE_CODE"
  }'

# Report an anti-pattern (something to NEVER do)
curl -X POST http://localhost:8025/lessons/report \
  -H "Content-Type: application/json" \
  -d '{
    "lesson_type": "anti_pattern",
    "domain": "production",
    "category": "deployment",
    "title": "Never modify prod Supabase directly",
    "context": "All changes must go through DEV first",
    "action_taken": "Direct prod modification",
    "outcome": "Data inconsistency, rollback required",
    "alternatives": ["Use DEV environment", "Use promote-to-prod.sh"],
    "severity": "critical",
    "tags": ["production", "supabase", "anti-pattern"],
    "source_agent": "CLAUDE_CODE"
  }'
```

### Current Anti-Patterns (Auto-Loaded)

The following will be BLOCKED or WARNED:
- Direct production database modifications
- Editing n8n workflows via SQL
- Modifying ARIA system prompt without backup
- Running rm -rf on data directories
- Deploying to prod without dev testing

### Learning Priorities

1. **Critical failures** - Must be reported immediately
2. **Workarounds** - Document so others don't waste time
3. **Anti-patterns** - Prevent future occurrences
4. **Optimizations** - Share efficiency gains
```

---

## IMPLEMENTATION PHASES

### Phase 1: Core Infrastructure (Sprint 1)
- [ ] Create MNEMOSYNE service skeleton (port 8025)
- [ ] Create database tables
- [ ] Create lesson_reporter.py shared module
- [ ] Basic CRUD operations
- [ ] Manual reporting endpoint

### Phase 2: Intelligence (Sprint 2)
- [ ] Embedding generation (OpenAI text-embedding-3-small)
- [ ] Semantic search implementation
- [ ] Anti-pattern matching
- [ ] Pattern detection algorithm

### Phase 3: Integration (Sprint 3)
- [ ] Claude Code integration (EXECUTION_RULES.md)
- [ ] Agent integration (CHRONOS, HADES, AEGIS first)
- [ ] ARIA integration (dashboard, queries)
- [ ] VARYS integration (oversight)

### Phase 4: Automation (Sprint 4)
- [ ] Automatic escalation rules
- [ ] Cross-agent learning propagation
- [ ] Pattern confidence scoring
- [ ] Anti-pattern enforcement

### Phase 5: Migration (Sprint 5)
- [ ] Migrate LESSONS-LEARNED.md to MNEMOSYNE
- [ ] Migrate LESSONS-SCRATCH.md to MNEMOSYNE
- [ ] Deprecate manual files
- [ ] Full system validation

---

## AGENT INTEGRATION

Each agent adds to their startup:

```python
from shared.lesson_reporter import LessonReporter

class MyAgent:
    def __init__(self):
        self.lessons = LessonReporter("MY_AGENT_NAME")
        
    async def startup(self):
        # Load relevant lessons into context
        relevant = await self.lessons.get_relevant_lessons(
            context=f"Starting {self.name} for {self.domain} operations"
        )
        self.context_lessons = relevant
    
    async def before_action(self, action: str, context: str):
        # Check anti-patterns
        check = await self.lessons.check_before_action(action, context)
        if check.get("blocked"):
            raise BlockedActionError(check["warnings"])
        return check.get("warnings", [])
    
    async def on_failure(self, error: Exception, context: str, action: str):
        await self.lessons.failure(
            title=str(error)[:100],
            context=context,
            action_taken=action,
            outcome=str(error),
            tags=["error", "automatic"]
        )
    
    async def on_success(self, action: str, context: str, result: str):
        # Only report significant successes
        if self._is_significant(result):
            await self.lessons.success(
                title=f"Successfully {action}",
                context=context,
                action_taken=action,
                outcome=result
            )
```

---

## ESCALATION RULES

```python
ESCALATION_RULES = {
    # Always escalate to ARIA
    "aria": [
        {"condition": "severity == 'critical'", "reason": "Critical issue"},
        {"condition": "lesson_type == 'anti_pattern'", "reason": "New anti-pattern"},
        {"condition": "occurrence_count > 3", "reason": "Recurring issue"},
    ],
    
    # Escalate to VARYS for project-related
    "varys": [
        {"condition": "domain == 'project'", "reason": "Project impact"},
        {"condition": "'deadline' in tags", "reason": "Deadline risk"},
        {"condition": "'launch' in tags", "reason": "Launch impact"},
    ],
    
    # Escalate to domain supervisors
    "domain_supervisor": [
        {"condition": "severity in ['critical', 'high']", "reason": "Domain issue"},
        {"condition": "lesson_type == 'failure' and confidence > 0.8", "reason": "Confirmed failure"},
    ],
}
```

---

## SUCCESS CRITERIA

1. **Claude Code never retries known-failed approaches**
   - Anti-pattern check before risky actions
   - Context includes relevant past failures

2. **Agents learn from each other**
   - Cross-domain lessons propagate
   - Pattern detection identifies common issues

3. **ARIA knows everything**
   - Dashboard shows learning metrics
   - Can query any lesson or pattern
   - Receives all critical escalations

4. **Zero manual documentation**
   - LESSONS-LEARNED.md deprecated
   - All learning flows through MNEMOSYNE
   - Automatic pattern detection

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/MNEMOSYNE-SPEC.md

Context: Implement MNEMOSYNE self-learning system.
Start with Phase 1: Core infrastructure.
Creates shared module for all agents.
Port 8025 in THE_KEEP domain.
```
