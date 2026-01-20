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
import re
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


# ============ TRANSCRIPT ANALYZER (Phase 2) ============

class TranscriptRequest(BaseModel):
    """Request to analyze a Claude Code transcript"""
    transcript_path: str = Field(..., description="Path to the transcript file")


class ExtractedLesson(BaseModel):
    title: str
    symptom: str
    cause: str
    fix: str
    prevention: Optional[str] = None
    severity: str = "medium"
    domain: str = "DEBUGGING"


@app.post("/analyze-transcript")
async def analyze_transcript(req: TranscriptRequest, background_tasks: BackgroundTasks):
    """
    Analyze a Claude Code transcript for lessons.
    Uses LLM to extract:
    - Problem symptoms
    - Root causes found
    - Fixes applied
    - Prevention recommendations
    """
    import pathlib

    # Verify file exists
    transcript_path = pathlib.Path(req.transcript_path)
    if not transcript_path.exists():
        raise HTTPException(status_code=404, detail=f"Transcript not found: {req.transcript_path}")

    # Read transcript (limit to last 50KB to avoid token limits)
    try:
        content = transcript_path.read_text()
        if len(content) > 50000:
            content = content[-50000:]  # Last 50KB
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read transcript: {e}")

    # Check for debugging patterns
    debug_patterns = ["fixed", "resolved", "root cause", "the issue was", "found the problem", "that was it", "now working"]
    has_debug_content = any(p.lower() in content.lower() for p in debug_patterns)

    if not has_debug_content:
        return {"lessons_captured": 0, "message": "No debugging content detected in transcript"}

    # Extract lessons using OpenAI
    if not OPENAI_API_KEY:
        # Fallback: Create a basic lesson without LLM analysis
        lesson = LessonInput(
            type=LessonType.PATTERN,
            source_agent="CLAUDE_SESSION",
            title=f"Debug session from transcript",
            content=f"Auto-captured debugging session. Review transcript at: {req.transcript_path}",
            domain="DEBUGGING",
            severity=Severity.MEDIUM,
            tags=["auto-captured", "claude-session", "needs-review"]
        )
        result = await ingest_lesson(lesson, background_tasks)
        return {"lessons_captured": 1, "lesson_ids": [result.id], "method": "heuristic"}

    # Use OpenAI to extract structured lessons
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": """You analyze debugging transcripts and extract lessons learned.
For each distinct issue found and fixed, extract:
- title: Short descriptive title
- symptom: What broke or wasn't working
- cause: The root cause discovered
- fix: How it was fixed
- prevention: How to avoid in future (optional)
- severity: low/medium/high
- domain: DEBUGGING, DEPLOYMENT, SCHEMA, AGENT_HEALTH, INFRASTRUCTURE

Return valid JSON: {"lessons": [...]}
If no clear lessons found, return {"lessons": []}"""
                        },
                        {
                            "role": "user",
                            "content": f"Extract lessons from this debugging transcript:\n\n{content[:30000]}"
                        }
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0
            )
            data = response.json()
            lessons_data = json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"LLM extraction failed: {e}")
        # Fallback to basic lesson
        lesson = LessonInput(
            type=LessonType.PATTERN,
            source_agent="CLAUDE_SESSION",
            title=f"Debug session (LLM extraction failed)",
            content=f"Auto-captured debugging session. LLM extraction error: {e}\nReview transcript at: {req.transcript_path}",
            domain="DEBUGGING",
            severity=Severity.MEDIUM,
            tags=["auto-captured", "claude-session", "needs-review", "extraction-failed"]
        )
        result = await ingest_lesson(lesson, background_tasks)
        return {"lessons_captured": 1, "lesson_ids": [result.id], "method": "fallback", "error": str(e)}

    # Process extracted lessons
    lesson_ids = []
    for lesson_data in lessons_data.get("lessons", []):
        try:
            lesson = LessonInput(
                type=LessonType.FAILURE,
                source_agent="CLAUDE_SESSION",
                title=lesson_data.get("title", "Debugging lesson"),
                content=f"Symptom: {lesson_data.get('symptom', 'Unknown')}\nCause: {lesson_data.get('cause', 'Unknown')}\nFix: {lesson_data.get('fix', 'Unknown')}",
                solution=lesson_data.get("fix"),
                root_cause=lesson_data.get("cause"),
                domain=lesson_data.get("domain", "DEBUGGING"),
                severity=Severity(lesson_data.get("severity", "medium")),
                tags=["auto-captured", "claude-session", "llm-extracted"],
                source_context={"transcript_path": req.transcript_path, "prevention": lesson_data.get("prevention")}
            )
            result = await ingest_lesson(lesson, background_tasks)
            lesson_ids.append(result.id)
        except Exception as e:
            print(f"Failed to ingest lesson: {e}")

    return {"lessons_captured": len(lesson_ids), "lesson_ids": lesson_ids, "method": "llm"}


# ============ EVENT BUS INTEGRATION (Phase 3) ============

LCIS_EVENT_TOPICS = [
    # Agent health
    "agent.error",
    "agent.restart",
    "agent.health.failed",
    "agent.health.recovered",
    # Deployments
    "deployment.started",
    "deployment.completed",
    "deployment.failed",
    "deployment.rollback",
    # Schema
    "schema.migration.applied",
    "schema.migration.failed",
    "schema.drift.detected",
    # GSD workflow
    "gsd.completed",
    "gsd.failed",
    "gsd.phase.completed",
    # Legacy events
    "error.resolved",
    "issue.healed",
    "integrity.restored",
]

# Error tracking for correlation
pending_errors: Dict[str, Dict[str, Any]] = {}

EVENT_BUS_URL = os.environ.get("EVENT_BUS_URL", "http://localhost:8099")


async def subscribe_to_event_bus():
    """Subscribe to Event Bus for automatic lesson capture"""
    try:
        async with httpx.AsyncClient() as client:
            for topic in LCIS_EVENT_TOPICS:
                try:
                    await client.post(
                        f"{EVENT_BUS_URL}/subscribe",
                        json={
                            "topic": topic,
                            "callback_url": "http://localhost:8050/event-callback"
                        },
                        timeout=5.0
                    )
                    print(f"LCIS subscribed to: {topic}")
                except Exception as e:
                    print(f"Failed to subscribe to {topic}: {e}")
    except Exception as e:
        print(f"Event Bus subscription failed: {e}")


@app.post("/event-callback")
async def handle_event_callback(event: Dict[str, Any], background_tasks: BackgroundTasks):
    """Handle events from Event Bus and convert to lessons"""
    event_type = event.get("type", event.get("event", "unknown"))

    # Determine lesson type and severity
    if "failed" in event_type or "error" in event_type:
        lesson_type = LessonType.FAILURE
        severity = Severity.HIGH
    elif "rollback" in event_type:
        lesson_type = LessonType.FAILURE
        severity = Severity.CRITICAL
    else:
        lesson_type = LessonType.SUCCESS
        severity = Severity.LOW

    # Determine domain
    domain = "INFRASTRUCTURE"
    if "agent" in event_type:
        domain = "AGENT_HEALTH"
    elif "deployment" in event_type:
        domain = "DEPLOYMENT"
    elif "schema" in event_type:
        domain = "SCHEMA"
    elif "gsd" in event_type:
        domain = "WORKFLOW"

    # Handle error correlation
    agent = event.get("agent", event.get("source", "unknown"))
    if "error" in event_type or "failed" in event_type:
        pending_errors[agent] = {
            "error": event.get("error", event.get("details", {})),
            "timestamp": datetime.utcnow().isoformat(),
            "event": event
        }
    elif "recovered" in event_type or "resolved" in event_type:
        if agent in pending_errors:
            error_info = pending_errors.pop(agent)
            # Create correlated lesson
            lesson = LessonInput(
                type=LessonType.FAILURE,
                source_agent="EVENT_BUS",
                title=f"{agent} error resolved",
                content=f"Error: {error_info['error']}\nRecovery: {event.get('details', 'Unknown')}",
                domain=domain,
                severity=Severity.MEDIUM,
                tags=["auto-captured", "event-bus", "error-resolved", agent.lower()]
            )
            await ingest_lesson(lesson, background_tasks)
            return {"status": "correlated_lesson_created"}

    # Create standard lesson from event
    lesson = LessonInput(
        type=lesson_type,
        source_agent=event.get("source", "EVENT_BUS"),
        title=event.get("summary", event_type),
        content=json.dumps(event.get("details", event), indent=2),
        domain=domain,
        severity=severity,
        tags=["auto-captured", "event-bus", event_type]
    )

    result = await ingest_lesson(lesson, background_tasks)
    return {"status": "lesson_created", "lesson_id": result.id}


# Subscribe to Event Bus on startup
@app.on_event("startup")
async def startup_event_bus():
    """Subscribe to Event Bus after main startup"""
    import asyncio
    # Delay subscription to allow Event Bus to be ready
    asyncio.create_task(delayed_subscription())


async def delayed_subscription():
    """Subscribe after a short delay"""
    import asyncio
    await asyncio.sleep(5)  # Wait for Event Bus
    await subscribe_to_event_bus()


# ============ CONSULTATION ENDPOINT (OMNISCIENCE) ============

class ConsultRequest(BaseModel):
    """Request to consult LCIS before an action"""
    action: str = Field(..., description="build, edit, deploy, delete, create")
    target: str = Field(..., description="Service/file/agent being acted upon")
    context: Optional[str] = None
    agent: str = Field(default="UNKNOWN", description="Which agent is asking")


class ConsultResponse(BaseModel):
    consultation_id: str
    action: str
    target: str
    proceed: bool
    blockers: List[str]
    warnings: List[str]
    recommendations: List[str]
    relevant_lessons: List[Dict[str, Any]]
    must_acknowledge: bool


@app.post("/consult", response_model=ConsultResponse)
async def consult_before_action(request: ConsultRequest):
    """
    MANDATORY check before any build, edit, or deployment.

    Returns:
    - relevant_lessons: Past experiences related to this action
    - warnings: Known issues or failure patterns to watch for
    - recommendations: Suggested approaches based on history
    - blockers: If any, action should NOT proceed
    """
    import uuid

    consultation_id = str(uuid.uuid4())[:8]
    blockers = []
    warnings = []
    recommendations = []
    relevant_lessons = []

    async with pool.acquire() as conn:
        # Check for blocking rules
        block_rules = await conn.fetch("""
            SELECT name, description, trigger_pattern, trigger_keywords
            FROM lcis_rules
            WHERE action = 'block'
            AND enforced = true
            AND (expires_at IS NULL OR expires_at > NOW())
        """)

        for rule in block_rules:
            pattern = rule['trigger_pattern']
            keywords = rule['trigger_keywords'] or []

            # Check pattern match
            if pattern:
                try:
                    if re.search(pattern, f"{request.action} {request.target}", re.IGNORECASE):
                        blockers.append(rule['description'])
                        # Update enforcement count
                        await conn.execute("""
                            UPDATE lcis_rules
                            SET enforcement_count = enforcement_count + 1,
                                last_enforced = NOW()
                            WHERE name = $1
                        """, rule['name'])
                except re.error:
                    pass

            # Check keyword match
            for kw in keywords:
                if kw.lower() in f"{request.action} {request.target}".lower():
                    blockers.append(rule['description'])
                    break

        # Check for warning rules
        warn_rules = await conn.fetch("""
            SELECT name, description, trigger_pattern, trigger_keywords
            FROM lcis_rules
            WHERE action = 'warn'
            AND enforced = true
            AND (expires_at IS NULL OR expires_at > NOW())
        """)

        for rule in warn_rules:
            pattern = rule['trigger_pattern']
            keywords = rule['trigger_keywords'] or []

            if pattern:
                try:
                    if re.search(pattern, f"{request.action} {request.target}", re.IGNORECASE):
                        warnings.append(rule['description'])
                except re.error:
                    pass

            for kw in keywords:
                if kw.lower() in f"{request.action} {request.target}".lower():
                    warnings.append(rule['description'])
                    break

        # Check for suggestion rules
        suggest_rules = await conn.fetch("""
            SELECT name, description, trigger_pattern, trigger_keywords
            FROM lcis_rules
            WHERE action = 'suggest'
            AND enforced = true
            AND (expires_at IS NULL OR expires_at > NOW())
        """)

        for rule in suggest_rules:
            pattern = rule['trigger_pattern']
            keywords = rule['trigger_keywords'] or []

            if pattern:
                try:
                    if re.search(pattern, f"{request.action} {request.target}", re.IGNORECASE):
                        recommendations.append(rule['description'])
                except re.error:
                    pass

            for kw in keywords:
                if kw.lower() in f"{request.action} {request.target}".lower():
                    recommendations.append(rule['description'])
                    break

        # Find relevant past lessons
        lessons = await conn.fetch("""
            SELECT id, title, content, type, solution, domain
            FROM lcis_lessons
            WHERE status = 'active'
            AND (
                content ILIKE $1
                OR content ILIKE $2
                OR title ILIKE $1
                OR title ILIKE $2
            )
            ORDER BY
                CASE WHEN type = 'failure' THEN 0 ELSE 1 END,
                occurrence_count DESC,
                created_at DESC
            LIMIT 5
        """, f"%{request.action}%", f"%{request.target}%")

        relevant_lessons = [
            {
                "id": str(row['id']),
                "title": row['title'],
                "content": row['content'][:200] if row['content'] else None,
                "type": row['type'],
                "solution": row['solution'],
                "domain": row['domain']
            }
            for row in lessons
        ]

        # Log the consultation
        await conn.execute("""
            INSERT INTO lcis_events (event_type, agent, context)
            VALUES ('consultation', $1, $2)
        """, request.agent, json.dumps({
            "action": request.action,
            "target": request.target,
            "blockers_count": len(blockers),
            "warnings_count": len(warnings),
            "proceed": len(blockers) == 0
        }))

    return ConsultResponse(
        consultation_id=consultation_id,
        action=request.action,
        target=request.target,
        proceed=len(blockers) == 0,
        blockers=list(set(blockers)),
        warnings=list(set(warnings)),
        recommendations=list(set(recommendations)),
        relevant_lessons=relevant_lessons,
        must_acknowledge=len(blockers) > 0 or len(warnings) > 2
    )


@app.post("/outcome")
async def report_outcome(
    consultation_id: str,
    success: bool,
    notes: Optional[str] = None,
    error: Optional[str] = None
):
    """Report the outcome of a consulted action"""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO lcis_events (event_type, context)
            VALUES ('outcome', $1)
        """, json.dumps({
            "consultation_id": consultation_id,
            "success": success,
            "notes": notes,
            "error": error
        }))

    return {"status": "recorded", "consultation_id": consultation_id}


@app.get("/status")
async def lcis_status():
    """LCIS system status and statistics"""
    async with pool.acquire() as conn:
        total_lessons = await conn.fetchval("SELECT COUNT(*) FROM lcis_lessons WHERE status = 'active'")
        lessons_today = await conn.fetchval("""
            SELECT COUNT(*) FROM lcis_lessons
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        errors_captured = await conn.fetchval("""
            SELECT COUNT(*) FROM lcis_lessons WHERE type = 'failure'
        """)
        fixes_captured = await conn.fetchval("""
            SELECT COUNT(*) FROM lcis_lessons WHERE type IN ('success', 'pattern')
        """)
        consultations_today = await conn.fetchval("""
            SELECT COUNT(*) FROM lcis_events
            WHERE event_type = 'consultation'
            AND created_at > NOW() - INTERVAL '24 hours'
        """)
        blocks_today = await conn.fetchval("""
            SELECT COUNT(*) FROM lcis_events
            WHERE event_type = 'consultation'
            AND created_at > NOW() - INTERVAL '24 hours'
            AND context::jsonb->>'blockers_count' != '0'
        """)
        active_rules = await conn.fetchval("""
            SELECT COUNT(*) FROM lcis_rules WHERE enforced = true
        """)

    return {
        "status": "operational",
        "version": "2.0.0",
        "mode": "omniscient",
        "stats": {
            "total_lessons": total_lessons,
            "lessons_today": lessons_today,
            "errors_captured": errors_captured,
            "fixes_captured": fixes_captured,
            "consultations_today": consultations_today,
            "blocks_today": blocks_today,
            "active_rules": active_rules
        },
        "watchers": {
            "docker_logs": "active",
            "event_bus": "active",
            "git_commits": "active"
        }
    }


@app.get("/recent")
async def recent_activity(limit: int = 20):
    """Recent LCIS activity"""
    async with pool.acquire() as conn:
        lessons = await conn.fetch("""
            SELECT id, title, content, type, domain, created_at
            FROM lcis_lessons
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)

        events = await conn.fetch("""
            SELECT event_type, agent, context, created_at
            FROM lcis_events
            ORDER BY created_at DESC
            LIMIT $1
        """, limit)

    return {
        "lessons": [dict(row) for row in lessons],
        "events": [dict(row) for row in events]
    }


@app.get("/rules")
async def list_rules():
    """List all active rules"""
    async with pool.acquire() as conn:
        rules = await conn.fetch("""
            SELECT id, name, description, action, trigger_pattern, trigger_keywords,
                   enforced, enforcement_count, created_at
            FROM lcis_rules
            WHERE enforced = true
            ORDER BY action, name
        """)
    return {"rules": [dict(row) for row in rules]}


@app.get("/context/{agent}")
async def get_agent_context(agent: str):
    """Get context for a specific agent - failures to avoid, rules to follow"""
    async with pool.acquire() as conn:
        # Get recent failures relevant to this agent
        failures = await conn.fetch("""
            SELECT l.content, l.solution, l.domain
            FROM lcis_lessons l
            LEFT JOIN lcis_agent_knowledge ak ON l.id = ak.lesson_id
            WHERE l.type = 'failure'
            AND l.status = 'active'
            AND (ak.agent = $1 OR l.domain IN (
                SELECT UNNEST(applies_to_domains) FROM lcis_rules
                WHERE $1 = ANY(applies_to_agents)
            ))
            ORDER BY l.created_at DESC
            LIMIT 10
        """, agent.upper())

        # Get rules for this agent
        rules = await conn.fetch("""
            SELECT name, description, action
            FROM lcis_rules
            WHERE enforced = true
            AND ($1 = ANY(applies_to_agents) OR applies_to_agents = '{}')
        """, agent.upper())

    return {
        "agent": agent,
        "failures_to_avoid": [dict(row) for row in failures],
        "rules_to_follow": [dict(row) for row in rules]
    }


# =============================================================================
# POST-GSD VALIDATION
# =============================================================================

import subprocess
from pathlib import Path

SPECS_DIR = Path("/opt/leveredge/specs")
SPECS_DONE_DIR = Path("/opt/leveredge/specs/done")

@app.post("/validate/gsd-completion")
async def validate_gsd_completion(spec_name: str):
    """
    Validate that a GSD was properly completed:
    1. Spec moved to done/
    2. LCIS lesson logged
    3. Git committed
    """
    issues = []
    passed = []

    # 1. Check spec location
    spec_in_active = SPECS_DIR / spec_name
    spec_in_done = SPECS_DONE_DIR / spec_name

    if spec_in_active.exists():
        issues.append({
            "check": "spec_moved",
            "status": "failed",
            "message": f"Spec still in /specs/: {spec_name}",
            "fix": f"mv /opt/leveredge/specs/{spec_name} /opt/leveredge/specs/done/"
        })
    elif spec_in_done.exists():
        passed.append({"check": "spec_moved", "status": "passed"})
    else:
        issues.append({
            "check": "spec_moved",
            "status": "warning",
            "message": f"Spec not found in either location: {spec_name}"
        })

    # 2. Check LCIS lesson
    if pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, created_at FROM lcis_lessons
                WHERE content ILIKE $1
                AND created_at > NOW() - INTERVAL '1 hour'
                ORDER BY created_at DESC LIMIT 1
            """, f"%{spec_name.replace('.md', '').replace('gsd-', '')}%")

            if row:
                passed.append({"check": "lcis_logged", "status": "passed", "lesson_id": str(row["id"])})
            else:
                issues.append({
                    "check": "lcis_logged",
                    "status": "failed",
                    "message": "No LCIS lesson found for this GSD in the last hour",
                    "fix": "Log completion lesson to LCIS"
                })

    # 3. Check git status
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=5,
            cwd="/opt/leveredge"
        )
        recent_commits = result.stdout.lower()
        gsd_keywords = spec_name.replace(".md", "").replace("gsd-", "").replace("-", " ").split()

        # Check if any keyword appears in recent commits
        found_commit = any(kw in recent_commits for kw in gsd_keywords if len(kw) > 3)

        if found_commit:
            passed.append({"check": "git_committed", "status": "passed"})
        else:
            # Check for uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5,
                cwd="/opt/leveredge"
            )
            if status_result.stdout.strip():
                issues.append({
                    "check": "git_committed",
                    "status": "failed",
                    "message": "Uncommitted changes detected",
                    "fix": "git add -A && git commit -m 'feat: <GSD description>'"
                })
            else:
                passed.append({"check": "git_committed", "status": "passed"})
    except Exception as e:
        issues.append({
            "check": "git_committed",
            "status": "error",
            "message": f"Could not check git: {str(e)}"
        })

    # Overall result
    all_passed = len(issues) == 0

    # Alert if issues found
    if issues:
        await alert_incomplete_gsd(spec_name, issues)

    return {
        "spec": spec_name,
        "complete": all_passed,
        "passed": passed,
        "issues": issues,
        "fix_commands": [i.get("fix") for i in issues if i.get("fix")]
    }


async def alert_incomplete_gsd(spec_name: str, issues: list):
    """Alert via HERMES about incomplete GSD cleanup"""
    try:
        issue_list = "\n".join([f"- {i['check']}: {i['message']}" for i in issues])
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                "http://hermes:8014/alert",
                json={
                    "severity": "warning",
                    "source": "LCIS",
                    "title": f"GSD Cleanup Incomplete: {spec_name}",
                    "message": f"The following cleanup steps are pending:\n{issue_list}"
                }
            )
    except:
        pass


@app.get("/validate/pending-cleanups")
async def get_pending_cleanups():
    """List all specs that appear to be completed but not moved to done/"""
    pending = []

    # Ensure done directory exists
    SPECS_DONE_DIR.mkdir(parents=True, exist_ok=True)

    # Find specs that look completed (mentioned in recent LCIS lessons or git)
    for spec_file in SPECS_DIR.glob("gsd-*.md"):
        if spec_file.name.startswith("gsd-"):
            # Check if there's a recent lesson mentioning completion
            if pool:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow("""
                        SELECT id FROM lcis_lessons
                        WHERE (content ILIKE '%complete%' OR content ILIKE '%deployed%' OR content ILIKE '%success%')
                        AND content ILIKE $1
                        AND created_at > NOW() - INTERVAL '24 hours'
                    """, f"%{spec_file.stem.replace('gsd-', '')}%")

                    if row:
                        pending.append({
                            "spec": spec_file.name,
                            "status": "likely_complete",
                            "fix": f"mv {spec_file} /opt/leveredge/specs/done/"
                        })

    return {
        "pending_cleanups": pending,
        "count": len(pending),
        "batch_fix": "cd /opt/leveredge && " + " && ".join([f"mv specs/{p['spec']} specs/done/" for p in pending]) if pending else None
    }


async def check_gsd_cleanup_before_new_gsd(action: str, target: str) -> dict:
    """Check if previous GSD cleanup is complete before starting new one"""

    if "gsd" not in target.lower():
        return {"proceed": True, "blockers": [], "warnings": [], "recommendations": []}

    # Check for incomplete cleanups
    pending = []
    for spec_file in SPECS_DIR.glob("gsd-*.md"):
        # Check if this spec was recently worked on (has matching LCIS entries)
        if pool:
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT id FROM lcis_lessons
                    WHERE content ILIKE $1
                    AND created_at > NOW() - INTERVAL '4 hours'
                """, f"%{spec_file.stem}%")

                if row:
                    pending.append(spec_file.name)

    if pending:
        return {
            "proceed": False,
            "blockers": [f"Previous GSD specs not moved to done/: {', '.join(pending)}"],
            "warnings": [],
            "recommendations": [
                f"Run: mv /opt/leveredge/specs/{pending[0]} /opt/leveredge/specs/done/",
                "Then retry the new GSD"
            ]
        }

    return {"proceed": True, "blockers": [], "warnings": [], "recommendations": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8050)
