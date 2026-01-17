#!/usr/bin/env python3
"""
THE SCRIBE - Council Meeting Secretary
Port: 8301

Records meeting transcripts, extracts decisions and action items,
generates summaries, and maintains searchable meeting history.

Works alongside CONVENER to capture everything that happens in council meetings.
"""

import os
import sys
import json
import httpx
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="THE SCRIBE",
    description="Council Meeting Secretary - Records and summarizes meetings",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
ARIA_OMNISCIENCE_URL = os.getenv("ARIA_OMNISCIENCE_URL", "http://aria-omniscience:8400")

# Initialize clients
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
cost_tracker = CostTracker("SCRIBE")

# =============================================================================
# MODELS
# =============================================================================

class RecordRequest(BaseModel):
    """Record an utterance from the meeting"""
    meeting_id: str
    speaker: str
    message: str
    message_type: str = "discussion"
    sequence_num: int

class SummarizeRequest(BaseModel):
    """Request parameters for summary"""
    detail_level: str = "standard"  # brief, standard, detailed

class SearchRequest(BaseModel):
    """Search across meeting transcripts"""
    query: str
    meeting_ids: Optional[List[str]] = None
    limit: int = 20

# =============================================================================
# DATABASE HELPERS
# =============================================================================

async def db_insert(table: str, data: dict) -> Optional[Dict]:
    """Insert a record into the database"""
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{SUPABASE_URL}/rest/v1/{table}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation"
                },
                json=data,
                timeout=10.0
            )
            if resp.status_code in [200, 201]:
                result = resp.json()
                return result[0] if isinstance(result, list) else result
    except Exception as e:
        print(f"DB insert failed: {e}")
    return None

async def db_get(table: str, match: dict) -> List[Dict]:
    """Get records from database"""
    try:
        params = "&".join([f"{k}=eq.{v}" for k, v in match.items()])
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/{table}?{params}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"DB get failed: {e}")
    return []

async def get_meeting(meeting_id: str) -> Optional[Dict]:
    """Get meeting by ID"""
    results = await db_get("council_meetings", {"id": meeting_id})
    return results[0] if results else None

async def get_transcript(meeting_id: str, limit: int = 500) -> List[Dict]:
    """Get meeting transcript"""
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/council_transcript",
                params={
                    "meeting_id": f"eq.{meeting_id}",
                    "order": "sequence_num.asc",
                    "limit": limit
                },
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"Get transcript failed: {e}")
    return []

async def get_decisions(meeting_id: str) -> List[Dict]:
    """Get decisions for a meeting"""
    return await db_get("council_decisions", {"meeting_id": meeting_id})

async def get_actions(meeting_id: str) -> List[Dict]:
    """Get action items for a meeting"""
    return await db_get("council_actions", {"meeting_id": meeting_id})

async def search_transcripts(query: str, meeting_ids: Optional[List[str]] = None, limit: int = 20) -> List[Dict]:
    """Search transcripts using text search"""
    try:
        async with httpx.AsyncClient() as http:
            # Use basic text search - Supabase supports ilike
            params = {
                "message": f"ilike.*{query}*",
                "order": "timestamp.desc",
                "limit": limit
            }
            if meeting_ids:
                params["meeting_id"] = f"in.({','.join(meeting_ids)})"

            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/council_transcript",
                params=params,
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"Search failed: {e}")
    return []

# =============================================================================
# ARIA OMNISCIENCE INTEGRATION
# =============================================================================

async def update_aria_knowledge(meeting_id: str, summary: str, decisions: List[Dict], actions: List[Dict]):
    """Send meeting knowledge to ARIA OMNISCIENCE"""
    try:
        meeting = await get_meeting(meeting_id)
        if not meeting:
            return

        # Format content for ARIA
        content = f"""## Council Meeting Summary

**Topic:** {meeting.get('topic', 'Unknown')}
**Title:** {meeting.get('title', 'Untitled')}
**Date:** {meeting.get('created_at', 'Unknown')}
**Participants:** {', '.join(meeting.get('council_members', []))}

### Summary
{summary}

### Decisions Made
"""
        for d in decisions:
            content += f"- {d.get('decision', 'Unknown')}\n"

        content += "\n### Action Items\n"
        for a in actions:
            content += f"- {a.get('action', 'Unknown')} -> {a.get('assigned_to', 'Unassigned')}\n"

        # Send to ARIA OMNISCIENCE
        async with httpx.AsyncClient() as http:
            await http.post(
                f"{ARIA_OMNISCIENCE_URL}/ingest/event",
                json={
                    "event_type": "council_meeting_completed",
                    "source": "SCRIBE",
                    "data": {
                        "meeting_id": meeting_id,
                        "topic": meeting.get("topic"),
                        "summary": summary,
                        "decisions": decisions,
                        "actions": actions
                    }
                },
                timeout=10.0
            )
    except Exception as e:
        print(f"ARIA update failed: {e}")

# =============================================================================
# LLM FUNCTIONS
# =============================================================================

SCRIBE_SYSTEM = """You are ATHENA, serving as the Scribe for the Council.
Your role is to:
- Accurately summarize discussions
- Extract key decisions and action items
- Maintain clear, organized records
- Be thorough but concise

You are thoughtful, precise, and thorough. Your writing is detailed, organized,
and references prior context when relevant."""

async def extract_items_from_message(message: str, message_type: str) -> Dict[str, Any]:
    """Extract decisions/actions from a message using Claude Haiku"""

    if message_type in ["decision", "action_item"]:
        # Already categorized, just return
        return {"type": message_type, "content": message}

    # Use Haiku for efficient extraction
    prompt = f"""Analyze this council meeting statement and extract any:
1. Decisions made (explicit agreements, conclusions)
2. Action items (tasks assigned to specific agents)

Statement: "{message}"

Return JSON:
{{"decisions": ["decision text if any"], "actions": [{{"action": "task", "assigned_to": "AGENT"}}]}}

If none found, return empty arrays."""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()
        if "{" in text and "}" in text:
            json_str = text[text.index("{"):text.rindex("}")+1]
            return json.loads(json_str)
    except Exception as e:
        print(f"Extraction failed: {e}")

    return {"decisions": [], "actions": []}

async def generate_summary(meeting: Dict, transcript: List[Dict], detail_level: str = "standard") -> str:
    """Generate meeting summary using Claude Haiku"""

    # Build transcript text
    transcript_text = "\n".join([
        f"**{t['speaker']}:** {t['message']}"
        for t in transcript
    ])

    detail_instructions = {
        "brief": "Write a 2-3 sentence summary of the key outcome.",
        "standard": "Write a summary with: 1) Main topic, 2) Key discussion points, 3) Decisions, 4) Action items. About 1 paragraph.",
        "detailed": "Write a comprehensive summary including: 1) Meeting purpose, 2) All participants' contributions, 3) Key debates/discussions, 4) All decisions with rationale, 5) All action items with owners, 6) Next steps. 2-3 paragraphs."
    }

    prompt = f"""Summarize this council meeting.

MEETING TITLE: {meeting.get('title', 'Untitled')}
TOPIC: {meeting.get('topic', 'Unknown')}
PARTICIPANTS: {', '.join(meeting.get('council_members', []))}

TRANSCRIPT:
{transcript_text}

{detail_instructions.get(detail_level, detail_instructions['standard'])}"""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=1024,
            system=SCRIBE_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Summary generation failed: {str(e)}"

async def semantic_search(query: str, transcripts: List[Dict]) -> List[Dict]:
    """Use Claude to find relevant excerpts"""

    # Build context
    excerpts = "\n\n".join([
        f"[Meeting: {t.get('meeting_id', '?')[:8]}, Speaker: {t.get('speaker', '?')}]\n{t.get('message', '')}"
        for t in transcripts[:30]  # Limit context
    ])

    prompt = f"""Find the most relevant excerpts for this query.

QUERY: {query}

AVAILABLE EXCERPTS:
{excerpts}

Return the meeting IDs and speakers of the most relevant 3-5 excerpts, explaining why each is relevant.
Format: List the relevant excerpts with brief explanations."""

    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        return {"analysis": response.content[0].text, "excerpts": transcripts[:10]}
    except Exception as e:
        return {"error": str(e), "excerpts": transcripts}

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "SCRIBE",
        "role": "Council Meeting Secretary",
        "port": 8301,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/scribe/record")
async def record_utterance(req: RecordRequest):
    """Record an utterance and extract any decisions/actions"""

    # Store to transcript (CONVENER may have already done this)
    # Check if already exists
    existing = await db_get("council_transcript", {
        "meeting_id": req.meeting_id,
        "sequence_num": req.sequence_num
    })

    if not existing:
        await db_insert("council_transcript", {
            "meeting_id": req.meeting_id,
            "speaker": req.speaker,
            "message": req.message,
            "message_type": req.message_type,
            "sequence_num": req.sequence_num
        })

    # Extract decisions/actions if it's a substantial message
    extracted = {"decisions": [], "actions": []}
    if len(req.message) > 50:
        extracted = await extract_items_from_message(req.message, req.message_type)

        # Store extracted decisions
        for decision in extracted.get("decisions", []):
            if decision:
                await db_insert("council_decisions", {
                    "meeting_id": req.meeting_id,
                    "decision": decision,
                    "proposed_by": req.speaker,
                    "status": "proposed"
                })

        # Store extracted actions
        for action in extracted.get("actions", []):
            if action and action.get("action"):
                await db_insert("council_actions", {
                    "meeting_id": req.meeting_id,
                    "action": action.get("action"),
                    "assigned_to": action.get("assigned_to", "UNASSIGNED"),
                    "status": "pending"
                })

    return {
        "recorded": True,
        "meeting_id": req.meeting_id,
        "sequence_num": req.sequence_num,
        "extracted_decisions": len(extracted.get("decisions", [])),
        "extracted_actions": len(extracted.get("actions", []))
    }

@app.post("/scribe/summarize/{meeting_id}")
async def summarize_meeting(meeting_id: str, req: SummarizeRequest = None):
    """Generate a meeting summary"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = await get_transcript(meeting_id)
    decisions = await get_decisions(meeting_id)
    actions = await get_actions(meeting_id)

    detail_level = req.detail_level if req else "standard"
    summary = await generate_summary(meeting, transcript, detail_level)

    # Update ARIA with meeting knowledge
    await update_aria_knowledge(meeting_id, summary, decisions, actions)

    return {
        "meeting_id": meeting_id,
        "title": meeting.get("title"),
        "topic": meeting.get("topic"),
        "summary": summary,
        "detail_level": detail_level,
        "decisions_count": len(decisions),
        "actions_count": len(actions)
    }

@app.get("/scribe/notes/{meeting_id}")
async def get_meeting_notes(meeting_id: str):
    """Get formatted meeting notes"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = await get_transcript(meeting_id)
    decisions = await get_decisions(meeting_id)
    actions = await get_actions(meeting_id)

    # Generate summary
    summary = await generate_summary(meeting, transcript, "standard")

    # Format notes
    notes = f"""# Council Meeting Notes

## {meeting.get('title', 'Untitled Meeting')}

**Date:** {meeting.get('created_at', 'Unknown')}
**Topic:** {meeting.get('topic', 'Unknown')}
**Status:** {meeting.get('status', 'Unknown')}
**Convener:** {meeting.get('convener', 'ATLAS')}
**Participants:** {', '.join(meeting.get('council_members', []))}

---

## Summary

{summary}

---

## Decisions

"""
    for d in decisions:
        notes += f"- **{d.get('status', 'proposed').upper()}:** {d.get('decision', '')}\n"
        notes += f"  - Proposed by: {d.get('proposed_by', '?')}\n"

    notes += "\n---\n\n## Action Items\n\n"
    for a in actions:
        status_emoji = "[ ]" if a.get("status") == "pending" else "[x]"
        notes += f"- {status_emoji} **{a.get('assigned_to', '?')}:** {a.get('action', '')}\n"
        if a.get("due_date"):
            notes += f"  - Due: {a.get('due_date')}\n"

    notes += "\n---\n\n## Full Transcript\n\n"
    for t in transcript:
        msg_type = t.get('message_type', 'discussion')
        prefix = ""
        if msg_type == "decision":
            prefix = "[DECISION] "
        elif msg_type == "action_item":
            prefix = "[ACTION] "
        elif msg_type == "directive":
            prefix = "[DIRECTIVE] "
        elif msg_type == "summary":
            prefix = "[SUMMARY] "

        notes += f"**{t.get('speaker', '?')}:** {prefix}{t.get('message', '')}\n\n"

    notes += f"\n---\n*Notes generated by SCRIBE at {datetime.utcnow().isoformat()}*\n"

    return {
        "meeting_id": meeting_id,
        "notes": notes,
        "transcript_entries": len(transcript),
        "decisions_count": len(decisions),
        "actions_count": len(actions)
    }

@app.get("/scribe/actions/{meeting_id}")
async def get_meeting_actions(meeting_id: str):
    """Get action items for a meeting"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    actions = await get_actions(meeting_id)

    # Group by assignee
    by_assignee = {}
    for a in actions:
        assignee = a.get("assigned_to", "UNASSIGNED")
        if assignee not in by_assignee:
            by_assignee[assignee] = []
        by_assignee[assignee].append(a)

    return {
        "meeting_id": meeting_id,
        "meeting_topic": meeting.get("topic"),
        "actions": actions,
        "by_assignee": by_assignee,
        "total_count": len(actions),
        "pending_count": len([a for a in actions if a.get("status") == "pending"]),
        "completed_count": len([a for a in actions if a.get("status") == "completed"])
    }

@app.get("/scribe/actions/agent/{agent_name}")
async def get_agent_actions(agent_name: str):
    """Get all action items assigned to an agent"""

    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/council_actions",
                params={
                    "assigned_to": f"eq.{agent_name}",
                    "order": "created_at.desc"
                },
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                actions = resp.json()
                return {
                    "agent": agent_name,
                    "actions": actions,
                    "total_count": len(actions),
                    "pending_count": len([a for a in actions if a.get("status") == "pending"])
                }
    except Exception as e:
        print(f"Get agent actions failed: {e}")

    return {"agent": agent_name, "actions": [], "total_count": 0}

@app.post("/scribe/search")
async def search_meetings(req: SearchRequest):
    """Semantic search across meeting transcripts"""

    # First do text search
    results = await search_transcripts(req.query, req.meeting_ids, req.limit)

    if results:
        # Use Claude to find most relevant
        analysis = await semantic_search(req.query, results)
        return {
            "query": req.query,
            "results_count": len(results),
            "analysis": analysis.get("analysis", ""),
            "excerpts": results[:10]
        }

    return {
        "query": req.query,
        "results_count": 0,
        "analysis": "No matching transcripts found.",
        "excerpts": []
    }

@app.get("/scribe/recent")
async def get_recent_notes():
    """Get notes from recent meetings"""

    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/council_meetings",
                params={
                    "status": "eq.completed",
                    "order": "ended_at.desc",
                    "limit": 5
                },
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                meetings = resp.json()
                return {
                    "recent_meetings": [
                        {
                            "id": m["id"],
                            "title": m.get("title"),
                            "topic": m.get("topic"),
                            "ended_at": m.get("ended_at"),
                            "notes_url": f"/scribe/notes/{m['id']}"
                        }
                        for m in meetings
                    ]
                }
    except Exception as e:
        print(f"Get recent failed: {e}")

    return {"recent_meetings": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8301)
