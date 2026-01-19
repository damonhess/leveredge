"""
STEWARD - Professional Coordination & Meeting Prep
Port: 8220
Domain: THE KEEP

I serve the household. I remember what was said, prepare what is needed,
and ensure nothing falls through the cracks.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import os
import asyncpg
import httpx
import json

app = FastAPI(
    title="STEWARD - Professional Coordination",
    description="I serve the household. I remember, prepare, and coordinate.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
EVENT_BUS_URL = os.environ.get("EVENT_BUS_URL", "http://event-bus:8099")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

pool: asyncpg.Pool = None

# Agent endpoints for consultation
AGENT_ENDPOINTS = {
    "SOLON": "http://solon:8210",
    "QUAESTOR": "http://quaestor:8211",
    "MIDAS": "http://midas:8205",
    "LITTLEFINGER": "http://littlefinger:8020",
    "SATOSHI": "http://satoshi:8206",
}


@app.on_event("startup")
async def startup():
    global pool
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


# ============ MODELS ============

class ProfessionalCreate(BaseModel):
    name: str
    role: str  # cpa, attorney, financial_advisor
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    specialty: Optional[str] = None
    domain: str = "both"  # business, personal, both


class MeetingCreate(BaseModel):
    professional_id: str
    title: str
    meeting_date: datetime
    duration_minutes: int = 60
    location: Optional[str] = None
    domain: str = "business"
    topics: List[str] = []


class AdviceCreate(BaseModel):
    professional_id: str
    meeting_id: Optional[str] = None
    topic: str
    advice: str
    reasoning: Optional[str] = None
    domain: str = "business"
    category: str
    urgency: str = "normal"
    requires_action: bool = False
    action_description: Optional[str] = None
    action_deadline: Optional[date] = None


class QuestionCreate(BaseModel):
    question: str
    context: Optional[str] = None
    target_role: str  # cpa, attorney
    domain: str = "business"
    category: Optional[str] = None
    priority: str = "normal"
    source_agent: Optional[str] = None


class MeetingComplete(BaseModel):
    summary: str
    advice_received: List[Dict] = []
    action_items: List[Dict] = []
    follow_up_date: Optional[date] = None


class DocumentCreate(BaseModel):
    name: str
    document_type: str
    year: Optional[int] = None
    due_date: Optional[date] = None
    status: str = "needed"


# ============ HEALTH ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "STEWARD",
        "agent": "STEWARD",
        "port": 8220,
        "database": "connected" if pool else "no connection",
        "tagline": "I serve the household. I remember, prepare, and coordinate.",
        "capabilities": ["professional_tracking", "meeting_prep", "advice_synthesis", "action_tracking"]
    }


# ============ PROFESSIONALS ============

@app.get("/professionals")
async def list_professionals(role: Optional[str] = None, domain: Optional[str] = None):
    if not pool:
        return []

    async with pool.acquire() as conn:
        query = "SELECT * FROM steward_professionals WHERE status = 'active'"
        params = []

        if role:
            params.append(role)
            query += f" AND role = ${len(params)}"
        if domain:
            params.append(domain)
            query += f" AND (domain = ${len(params)} OR domain = 'both')"

        query += " ORDER BY role, name"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/professionals")
async def add_professional(prof: ProfessionalCreate):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO steward_professionals (name, role, company, email, phone, specialty, domain)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, prof.name, prof.role, prof.company, prof.email, prof.phone, prof.specialty, prof.domain)
        return dict(row)


@app.get("/professionals/{prof_id}")
async def get_professional(prof_id: str):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        prof = await conn.fetchrow(
            "SELECT * FROM steward_professionals WHERE id = $1::uuid", prof_id
        )
        if not prof:
            raise HTTPException(status_code=404, detail="Professional not found")

        # Get recent meetings
        meetings = await conn.fetch("""
            SELECT id, title, meeting_date, status
            FROM steward_meetings
            WHERE professional_id = $1::uuid
            ORDER BY meeting_date DESC LIMIT 5
        """, prof_id)

        # Get advice count
        advice_count = await conn.fetchval(
            "SELECT COUNT(*) FROM steward_advice WHERE professional_id = $1::uuid", prof_id
        )

        # Get pending questions
        questions = await conn.fetch("""
            SELECT id, question, priority
            FROM steward_questions
            WHERE target_professional_id = $1::uuid AND status = 'pending'
        """, prof_id)

        return {
            "professional": dict(prof),
            "recent_meetings": [dict(m) for m in meetings],
            "advice_count": advice_count,
            "pending_questions": [dict(q) for q in questions]
        }


# ============ MEETINGS ============

@app.get("/meetings")
async def list_meetings(status: Optional[str] = None, upcoming: bool = False):
    if not pool:
        return []

    async with pool.acquire() as conn:
        query = """
            SELECT m.*, p.name as professional_name, p.role as professional_role
            FROM steward_meetings m
            LEFT JOIN steward_professionals p ON m.professional_id = p.id
            WHERE 1=1
        """
        params = []

        if status:
            params.append(status)
            query += f" AND m.status = ${len(params)}"
        if upcoming:
            query += " AND m.meeting_date > NOW() AND m.status = 'scheduled'"

        query += " ORDER BY m.meeting_date DESC"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/meetings")
async def create_meeting(meeting: MeetingCreate):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO steward_meetings
            (professional_id, title, meeting_date, duration_minutes, location, domain, topics)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, meeting.professional_id, meeting.title, meeting.meeting_date,
            meeting.duration_minutes, meeting.location, meeting.domain, meeting.topics)

        # Update professional's next_meeting
        await conn.execute("""
            UPDATE steward_professionals SET next_meeting = $2 WHERE id = $1::uuid
        """, meeting.professional_id, meeting.meeting_date)

        return dict(row)


@app.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        meeting = await conn.fetchrow("""
            SELECT m.*, p.name as professional_name, p.role as professional_role, p.company
            FROM steward_meetings m
            LEFT JOIN steward_professionals p ON m.professional_id = p.id
            WHERE m.id = $1::uuid
        """, meeting_id)

        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Get pending questions for this professional
        questions = await conn.fetch("""
            SELECT * FROM steward_questions
            WHERE (target_professional_id = $1::uuid OR scheduled_meeting_id = $2::uuid)
            AND status IN ('pending', 'scheduled')
        """, meeting['professional_id'], meeting_id)

        # Get relevant prior advice
        prior_advice = await conn.fetch("""
            SELECT topic, advice, created_at
            FROM steward_advice
            WHERE professional_id = $1::uuid
            ORDER BY created_at DESC LIMIT 10
        """, meeting['professional_id'])

        return {
            "meeting": dict(meeting),
            "questions_to_ask": [dict(q) for q in questions],
            "prior_advice": [dict(a) for a in prior_advice]
        }


@app.post("/meetings/{meeting_id}/prep")
async def prepare_meeting(meeting_id: str, background_tasks: BackgroundTasks):
    """Generate meeting prep using AI"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    background_tasks.add_task(do_meeting_prep, meeting_id)
    return {"status": "preparing", "message": "Check meeting details in a moment"}


async def do_meeting_prep(meeting_id: str):
    """Background task to prepare meeting"""
    if not pool or not ANTHROPIC_API_KEY:
        return

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    async with pool.acquire() as conn:
        meeting = await conn.fetchrow("""
            SELECT m.*, p.name, p.role, p.specialty
            FROM steward_meetings m
            JOIN steward_professionals p ON m.professional_id = p.id
            WHERE m.id = $1::uuid
        """, meeting_id)

        if not meeting:
            return

        # Get pending questions
        questions = await conn.fetch("""
            SELECT question, context FROM steward_questions
            WHERE target_professional_id = $1::uuid AND status = 'pending'
        """, meeting['professional_id'])

        # Get prior advice
        prior = await conn.fetch("""
            SELECT topic, advice FROM steward_advice
            WHERE professional_id = $1::uuid
            ORDER BY created_at DESC LIMIT 5
        """, meeting['professional_id'])

        # Consult relevant agents
        agent_context = await gather_agent_context(meeting['role'], meeting['topics'])

        prompt = f"""Prepare me for a meeting with my {meeting['role']}.

Professional: {meeting['name']} ({meeting['specialty'] or 'general'})
Meeting: {meeting['title']}
Topics: {', '.join(meeting['topics'] or [])}
Date: {meeting['meeting_date']}

Prior advice from this professional:
{json.dumps([dict(p) for p in prior], indent=2)}

Questions I want to ask:
{json.dumps([dict(q) for q in questions], indent=2)}

Context from my AI advisors:
{agent_context}

Please provide:
1. A brief agenda
2. Key questions to ask (prioritized)
3. Documents I should bring or have ready
4. Context notes (what to remember going in)
5. Any warnings or things to watch out for

Be specific and actionable."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        prep_content = response.content[0].text

        # Update meeting with prep
        await conn.execute("""
            UPDATE steward_meetings
            SET context_notes = $2, updated_at = NOW()
            WHERE id = $1::uuid
        """, meeting_id, prep_content)


async def gather_agent_context(role: str, topics: List[str]) -> str:
    """Gather relevant context from other agents"""
    context_parts = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if role in ['cpa', 'accountant']:
                # Get LITTLEFINGER status
                try:
                    resp = await client.get(f"{AGENT_ENDPOINTS['LITTLEFINGER']}/status")
                    if resp.status_code == 200:
                        data = resp.json()
                        context_parts.append(f"Business Finances: MRR ${data.get('mrr', 0):,.0f}, "
                                           f"MTD Revenue ${data.get('revenue_mtd', 0):,.0f}")
                except:
                    pass

                # Get QUAESTOR insights
                try:
                    resp = await client.get(f"{AGENT_ENDPOINTS['QUAESTOR']}/status")
                    if resp.status_code == 200:
                        context_parts.append(f"Tax Context: {resp.json().get('summary', 'N/A')}")
                except:
                    pass

            elif role == 'attorney':
                # Get SOLON context
                try:
                    resp = await client.get(f"{AGENT_ENDPOINTS['SOLON']}/status")
                    if resp.status_code == 200:
                        context_parts.append(f"Legal Context: {resp.json().get('summary', 'N/A')}")
                except:
                    pass

            elif role == 'financial_advisor':
                # Get MIDAS summary
                try:
                    resp = await client.get(f"{AGENT_ENDPOINTS['MIDAS']}/portfolio/summary")
                    if resp.status_code == 200:
                        data = resp.json()
                        context_parts.append(f"Portfolio: ${data.get('total_value', 0):,.0f}")
                except:
                    pass
    except:
        pass

    return "\n".join(context_parts) if context_parts else "No additional context available"


@app.post("/meetings/{meeting_id}/complete")
async def complete_meeting(meeting_id: str, data: MeetingComplete):
    """Record meeting outcomes"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE steward_meetings
            SET status = 'completed', summary = $2, advice_received = $3,
                action_items = $4, follow_up_date = $5, updated_at = NOW()
            WHERE id = $1::uuid
        """, meeting_id, data.summary, json.dumps(data.advice_received),
            json.dumps(data.action_items), data.follow_up_date)

        meeting = await conn.fetchrow(
            "SELECT professional_id FROM steward_meetings WHERE id = $1::uuid", meeting_id
        )

        # Update professional's last_meeting
        await conn.execute("""
            UPDATE steward_professionals SET last_meeting = NOW() WHERE id = $1::uuid
        """, meeting['professional_id'])

        # Log each piece of advice
        for advice in data.advice_received:
            await conn.execute("""
                INSERT INTO steward_advice
                (professional_id, meeting_id, topic, advice, category, requires_action,
                 action_description, action_deadline)
                VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8)
            """, meeting['professional_id'], meeting_id,
                advice.get('topic', 'General'),
                advice.get('advice', ''),
                advice.get('category', 'general'),
                advice.get('requires_action', False),
                advice.get('action_description'),
                advice.get('action_deadline'))

        return {"status": "completed"}


# ============ ADVICE ============

@app.get("/advice")
async def list_advice(
    category: Optional[str] = None,
    requires_action: Optional[bool] = None,
    action_status: Optional[str] = None
):
    if not pool:
        return []

    async with pool.acquire() as conn:
        query = """
            SELECT a.*, p.name as professional_name, p.role
            FROM steward_advice a
            LEFT JOIN steward_professionals p ON a.professional_id = p.id
            WHERE 1=1
        """
        params = []

        if category:
            params.append(category)
            query += f" AND a.category = ${len(params)}"
        if requires_action is not None:
            params.append(requires_action)
            query += f" AND a.requires_action = ${len(params)}"
        if action_status:
            params.append(action_status)
            query += f" AND a.action_status = ${len(params)}"

        query += " ORDER BY a.created_at DESC"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/advice")
async def add_advice(advice: AdviceCreate):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO steward_advice
            (professional_id, meeting_id, topic, advice, reasoning, domain, category,
             urgency, requires_action, action_description, action_deadline)
            VALUES ($1::uuid, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING *
        """, advice.professional_id, advice.meeting_id, advice.topic, advice.advice,
            advice.reasoning, advice.domain, advice.category, advice.urgency,
            advice.requires_action, advice.action_description, advice.action_deadline)
        return dict(row)


@app.get("/advice/actions")
async def get_action_items():
    """Get all pending action items from advice"""
    if not pool:
        return []

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT a.*, p.name as professional_name, p.role
            FROM steward_advice a
            LEFT JOIN steward_professionals p ON a.professional_id = p.id
            WHERE a.requires_action = TRUE AND a.action_status IN ('pending', 'in_progress')
            ORDER BY a.action_deadline NULLS LAST, a.urgency DESC
        """)
        return [dict(r) for r in rows]


@app.put("/advice/{advice_id}/action")
async def update_action_status(advice_id: str, status: str, notes: Optional[str] = None):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        completed_at = datetime.now() if status == 'completed' else None
        await conn.execute("""
            UPDATE steward_advice
            SET action_status = $2, action_completed_at = $3
            WHERE id = $1::uuid
        """, advice_id, status, completed_at)
        return {"status": "updated"}


# ============ QUESTIONS ============

@app.get("/questions")
async def list_questions(status: Optional[str] = None, target_role: Optional[str] = None):
    if not pool:
        return []

    async with pool.acquire() as conn:
        query = "SELECT * FROM steward_questions WHERE 1=1"
        params = []

        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"
        if target_role:
            params.append(target_role)
            query += f" AND target_role = ${len(params)}"

        query += " ORDER BY priority DESC, created_at"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/questions")
async def add_question(q: QuestionCreate):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Find appropriate professional if not specified
        prof_id = None
        if q.target_role:
            prof = await conn.fetchrow("""
                SELECT id FROM steward_professionals
                WHERE role = $1 AND status = 'active'
                LIMIT 1
            """, q.target_role)
            if prof:
                prof_id = prof['id']

        row = await conn.fetchrow("""
            INSERT INTO steward_questions
            (question, context, target_role, target_professional_id, domain, category, priority, source_agent)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING *
        """, q.question, q.context, q.target_role, prof_id,
            q.domain, q.category, q.priority, q.source_agent)
        return dict(row)


@app.put("/questions/{q_id}/answer")
async def answer_question(q_id: str, answer: str, professional_id: Optional[str] = None):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE steward_questions
            SET status = 'answered', answer = $2, answered_at = NOW(), answered_by = $3::uuid
            WHERE id = $1::uuid
        """, q_id, answer, professional_id)
        return {"status": "answered"}


# ============ DOCUMENTS ============

@app.get("/documents")
async def list_documents(status: Optional[str] = None, document_type: Optional[str] = None):
    if not pool:
        return []

    async with pool.acquire() as conn:
        query = "SELECT * FROM steward_documents WHERE 1=1"
        params = []

        if status:
            params.append(status)
            query += f" AND status = ${len(params)}"
        if document_type:
            params.append(document_type)
            query += f" AND document_type = ${len(params)}"

        query += " ORDER BY due_date NULLS LAST, name"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/documents")
async def add_document(doc: DocumentCreate):
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO steward_documents (name, document_type, year, due_date, status)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, doc.name, doc.document_type, doc.year, doc.due_date, doc.status)
        return dict(row)


# ============ DASHBOARD ============

@app.get("/status")
async def steward_status():
    """Get STEWARD dashboard"""
    if not pool:
        return {
            "professionals": 0,
            "upcoming_meetings": [],
            "pending_actions": 0,
            "pending_questions": 0,
            "steward_says": "The household awaits its advisors."
        }

    async with pool.acquire() as conn:
        prof_count = await conn.fetchval(
            "SELECT COUNT(*) FROM steward_professionals WHERE status = 'active'"
        )

        upcoming = await conn.fetch("""
            SELECT m.id, m.title, m.meeting_date, p.name, p.role
            FROM steward_meetings m
            JOIN steward_professionals p ON m.professional_id = p.id
            WHERE m.status = 'scheduled' AND m.meeting_date > NOW()
            ORDER BY m.meeting_date LIMIT 5
        """)

        pending_actions = await conn.fetchval("""
            SELECT COUNT(*) FROM steward_advice
            WHERE requires_action = TRUE AND action_status IN ('pending', 'in_progress')
        """)

        pending_questions = await conn.fetchval(
            "SELECT COUNT(*) FROM steward_questions WHERE status = 'pending'"
        )

        overdue_actions = await conn.fetchval("""
            SELECT COUNT(*) FROM steward_advice
            WHERE requires_action = TRUE AND action_status = 'pending'
            AND action_deadline < CURRENT_DATE
        """)

        return {
            "professionals": prof_count,
            "upcoming_meetings": [dict(m) for m in upcoming],
            "pending_actions": pending_actions,
            "overdue_actions": overdue_actions,
            "pending_questions": pending_questions,
            "steward_says": generate_steward_status(upcoming, pending_actions, overdue_actions)
        }


def generate_steward_status(upcoming, pending_actions, overdue_actions):
    if overdue_actions > 0:
        return f"Sir, {overdue_actions} action items are overdue. Your advisors await your attention."
    elif upcoming:
        next_meeting = upcoming[0]
        return f"Your next meeting: {next_meeting['name']} ({next_meeting['role']}) - {next_meeting['title']}. Shall I prepare?"
    elif pending_actions > 0:
        return f"{pending_actions} action items pending from your advisors. The household runs smoothly."
    else:
        return "All is in order. No pending matters require attention."


# ============ SYNTHESIS ============

@app.post("/synthesize")
async def synthesize_advice(topic: str, domain: str = "business"):
    """Synthesize advice across all relevant professionals and agents"""
    if not pool or not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="Service not available")

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    async with pool.acquire() as conn:
        # Get all relevant advice
        advice = await conn.fetch("""
            SELECT a.topic, a.advice, a.reasoning, a.category, p.name, p.role
            FROM steward_advice a
            JOIN steward_professionals p ON a.professional_id = p.id
            WHERE (a.topic ILIKE $1 OR a.category ILIKE $1)
            AND (a.domain = $2 OR a.domain = 'both')
            AND (a.valid_until IS NULL OR a.valid_until > CURRENT_DATE)
            ORDER BY a.created_at DESC
        """, f"%{topic}%", domain)

    # Gather agent perspectives
    agent_context = await gather_agent_context_for_topic(topic, domain)

    prompt = f"""Synthesize advice on: {topic}

Professional advice received:
{json.dumps([dict(a) for a in advice], indent=2)}

AI agent analysis:
{agent_context}

Please provide:
1. Summary of key points across all sources
2. Any conflicts or disagreements between advisors
3. Recommended action plan
4. Questions that still need answers
5. Which professional to consult next (if any)

Be practical and actionable."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "topic": topic,
        "synthesis": response.content[0].text,
        "sources": {
            "professionals": len(advice),
            "agents_consulted": list(AGENT_ENDPOINTS.keys())
        }
    }


async def gather_agent_context_for_topic(topic: str, domain: str) -> str:
    """Get relevant agent perspectives on a topic"""
    # Simplified - would expand based on topic keywords
    return "Agent context gathering in progress..."


# ============ HELPERS ============

async def publish_event(event_type: str, data: dict):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": f"steward.{event_type}",
                    "source": "STEWARD",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                },
                timeout=5.0
            )
    except:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8220)
