"""
LCIS ORACLE - Pre-Action Retrieval Service
Port: 8052
Domain: THE_KEEP

Consult before any action to get relevant knowledge and check rules.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import httpx
import asyncpg
import json

app = FastAPI(
    title="LCIS ORACLE",
    description="Pre-Action Consultation for LeverEdge Collective Intelligence",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:54323/postgres")
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
    if pool:
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
            SELECT rule_id, rule_name, description, action, alternatives, required_action
            FROM lcis_check_rules($1, $2, $3)
        """, action, domain, agent)

        for rule in rules:
            if rule['action'] == 'block':
                # Log enforcement
                await conn.execute("""
                    UPDATE lcis_rules SET enforcement_count = enforcement_count + 1, last_enforced = NOW()
                    WHERE id = $1
                """, rule['rule_id'])

                await conn.execute("""
                    INSERT INTO lcis_events (event_type, rule_id, agent, context)
                    VALUES ('rule_enforced', $1, $2, $3)
                """, rule['rule_id'], agent, json.dumps({"action": action[:200]}))

                alternatives = rule['alternatives'] if rule['alternatives'] else []
                if isinstance(alternatives, str):
                    try:
                        alternatives = json.loads(alternatives)
                    except:
                        alternatives = [alternatives]

                return BlockedRule(
                    rule_id=str(rule['rule_id']),
                    name=rule['rule_name'],
                    reason=rule['description'],
                    alternatives=alternatives
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
    uvicorn.run(app, host="0.0.0.0", port=8052)
