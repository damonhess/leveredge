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

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:54323/postgres")
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
    if pool:
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

        print(f"New rule created from pattern: {rule_id}")

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
