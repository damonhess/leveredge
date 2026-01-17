#!/usr/bin/env python3
"""
THE CONVENER - Council Meeting Facilitator
Port: 8300

Orchestrates multi-agent council meetings, managing turn-taking,
discussion flow, decisions, and action items.

Named after the one who brings together the council for deliberation.
"""

import os
import sys
import json
import httpx
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="THE CONVENER",
    description="Council Meeting Facilitator - Orchestrates multi-agent councils",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SCRIBE_URL = os.getenv("SCRIBE_URL", "http://scribe:8301")

# Agent endpoints for calling council members
AGENT_ENDPOINTS = {
    # Pantheon
    "ATLAS": "http://atlas:8007",
    "ATHENA": "http://athena:8013",
    "CHIRON": "http://chiron:8017",
    "SCHOLAR": "http://scholar:8018",
    # Alchemy (future)
    "CATALYST": "http://catalyst:8030",
    "SAGA": "http://saga:8031",
    "PRISM": "http://prism:8032",
    "ELIXIR": "http://elixir:8033",
    "RELIC": "http://relic:8034",
    # Guild (future)
    "GUILDMASTER": "http://guildmaster:8200",
    "LOREKEEPER": "http://lorekeeper:8201",
    "ARTIFICER": "http://artificer:8202",
    "PROCTOR": "http://proctor:8203",
}

# Topic-to-agent mapping for auto-selection
TOPIC_AGENT_MAPPING = {
    "design": ["PRISM", "CATALYST"],
    "ui": ["PRISM", "CATALYST"],
    "ux": ["PRISM", "CATALYST"],
    "visual": ["PRISM", "CATALYST"],
    "architecture": ["ARTIFICER", "ATHENA"],
    "build": ["ARTIFICER", "ATHENA"],
    "system": ["ARTIFICER", "ATHENA"],
    "creative": ["SAGA", "ELIXIR", "CATALYST"],
    "content": ["SAGA", "ELIXIR", "CATALYST"],
    "writing": ["SAGA", "ELIXIR"],
    "copy": ["ELIXIR", "SAGA"],
    "research": ["SCHOLAR", "RELIC"],
    "analysis": ["SCHOLAR", "ATHENA"],
    "project": ["GUILDMASTER", "PROCTOR"],
    "timeline": ["GUILDMASTER", "ATHENA"],
    "delivery": ["GUILDMASTER", "PROCTOR"],
    "quality": ["PROCTOR", "ARTIFICER"],
    "strategy": ["CHIRON", "CATALYST"],
    "vision": ["CATALYST", "CHIRON"],
}

# Initialize clients
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
cost_tracker = CostTracker("CONVENER")

# =============================================================================
# MODELS
# =============================================================================

class ConveneRequest(BaseModel):
    """Request to create a new council meeting"""
    title: str
    topic: str
    agenda: List[str] = []
    council_members: Optional[List[str]] = None  # Auto-selected if not provided
    convener: str = "ATLAS"
    scribe: str = "ATHENA"

class StartMeetingResponse(BaseModel):
    """Response when meeting is started"""
    meeting_id: str
    opening_statement: str
    participants: List[str]
    agenda: List[str]

class TurnRequest(BaseModel):
    """Request for next turn in meeting"""
    context: Optional[str] = None  # Additional context for this turn

class InjectRequest(BaseModel):
    """Request to inject a directive from DAMON"""
    message: str
    priority: str = "normal"  # normal, high, urgent

class DecideRequest(BaseModel):
    """Request to synthesize discussion into a decision"""
    topic: Optional[str] = None  # Specific topic to decide on

class ActionRequest(BaseModel):
    """Request to assign an action item"""
    action: str
    assigned_to: str
    due_date: Optional[str] = None

# =============================================================================
# DATABASE HELPERS
# =============================================================================

async def db_query(query: str, params: dict = None) -> List[Dict]:
    """Execute a database query via PostgREST"""
    try:
        async with httpx.AsyncClient() as http:
            # Use RPC for custom queries
            resp = await http.post(
                f"{SUPABASE_URL}/rest/v1/rpc/query",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json={"sql": query, "params": params or {}},
                timeout=10.0
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        print(f"DB query failed: {e}")
    return []

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

async def db_update(table: str, match: dict, data: dict) -> bool:
    """Update records in the database"""
    try:
        params = "&".join([f"{k}=eq.{v}" for k, v in match.items()])
        async with httpx.AsyncClient() as http:
            resp = await http.patch(
                f"{SUPABASE_URL}/rest/v1/{table}?{params}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json"
                },
                json=data,
                timeout=10.0
            )
            return resp.status_code in [200, 204]
    except Exception as e:
        print(f"DB update failed: {e}")
    return False

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

async def get_transcript(meeting_id: str, limit: int = 50) -> List[Dict]:
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

async def get_agent_profile(agent_name: str) -> Optional[Dict]:
    """Get agent profile from database"""
    results = await db_get("council_agent_profiles", {"agent_name": agent_name})
    return results[0] if results else None

async def get_all_agent_profiles() -> Dict[str, Dict]:
    """Get all agent profiles"""
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/council_agent_profiles",
                params={"is_active": "eq.true"},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                profiles = resp.json()
                return {p["agent_name"]: p for p in profiles}
    except Exception as e:
        print(f"Get all profiles failed: {e}")
    return {}

# =============================================================================
# EVENT BUS
# =============================================================================

async def publish_event(event_type: str, data: dict):
    """Publish event to Event Bus"""
    try:
        async with httpx.AsyncClient() as http:
            await http.post(
                f"{EVENT_BUS_URL}/publish",
                json={
                    "event_type": f"council.{event_type}",
                    "source": "CONVENER",
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event publish failed: {e}")

# =============================================================================
# AGENT CALLING
# =============================================================================

async def call_agent_respond(
    agent_name: str,
    meeting_context: str,
    current_topic: str,
    previous_statements: List[Dict],
    directive: Optional[str] = None
) -> str:
    """Call an agent's /council/respond endpoint"""
    endpoint = AGENT_ENDPOINTS.get(agent_name)
    if not endpoint:
        return f"[{agent_name} is not available]"

    try:
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"{endpoint}/council/respond",
                json={
                    "meeting_context": meeting_context,
                    "current_topic": current_topic,
                    "previous_statements": previous_statements,
                    "directive": directive
                },
                timeout=60.0  # LLM calls can be slow
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "[No response]")
            else:
                return f"[{agent_name} returned error: {resp.status_code}]"
    except httpx.ConnectError:
        # Agent not running, use CONVENER to simulate response
        return await simulate_agent_response(
            agent_name, meeting_context, current_topic, previous_statements, directive
        )
    except Exception as e:
        return f"[{agent_name} error: {str(e)}]"

async def simulate_agent_response(
    agent_name: str,
    meeting_context: str,
    current_topic: str,
    previous_statements: List[Dict],
    directive: Optional[str] = None
) -> str:
    """Simulate an agent response using CONVENER's Claude access"""
    profile = await get_agent_profile(agent_name)
    if not profile:
        return f"[{agent_name} profile not found]"

    expertise_str = ", ".join(profile.get("expertise", []))
    contributions_str = ", ".join(profile.get("typical_contributions", []))

    system_prompt = f"""You are {agent_name}, participating in a council meeting.

Domain: {profile.get('domain', 'Unknown')}
Expertise: {expertise_str}
Personality: {profile.get('personality', 'Professional')}
Speaking Style: {profile.get('speaking_style', 'Clear and concise')}
You typically: {contributions_str}

Respond in character. Be concise (2-4 sentences unless asked for detail).
Build on what others have said. Disagree respectfully if warranted.
Stay in your lane - defer to other experts when appropriate.
Do not prefix your response with your name."""

    # Build conversation context
    context_parts = [f"## MEETING CONTEXT\n{meeting_context}"]
    context_parts.append(f"\n## CURRENT TOPIC\n{current_topic}")

    if previous_statements:
        context_parts.append("\n## RECENT DISCUSSION")
        for stmt in previous_statements[-10:]:
            speaker = stmt.get("speaker", "Unknown")
            message = stmt.get("message", "")
            context_parts.append(f"\n**{speaker}:** {message}")

    user_content = "\n".join(context_parts)
    if directive:
        user_content += f"\n\n## DIRECTIVE FOR YOU\n{directive}"
    else:
        user_content += "\n\n## YOUR TURN\nContribute to the discussion."

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}]
        )
        return response.content[0].text
    except Exception as e:
        return f"[{agent_name} simulation failed: {str(e)}]"

# =============================================================================
# CONVENER LLM
# =============================================================================

CONVENER_SYSTEM = """You are ATLAS, the Convener of the Council. You facilitate meetings between AI agents.

Your role:
- Keep discussion focused on the agenda
- Call on agents in logical order based on expertise
- Synthesize viewpoints and identify consensus/disagreement
- Capture decisions clearly
- Assign action items with specific owners
- Be commanding but fair
- Never ramble - be concise and direct

You are NOT a participant with opinions. You are the facilitator who enables productive discussion."""

async def convener_decide_next_speaker(
    meeting: Dict,
    transcript: List[Dict],
    profiles: Dict[str, Dict]
) -> tuple[str, Optional[str]]:
    """Use Claude to decide who speaks next and with what directive"""

    members = meeting.get("council_members", [])
    agenda = meeting.get("agenda", [])
    topic = meeting.get("topic", "")

    # Build context
    recent_speakers = [t["speaker"] for t in transcript[-5:]] if transcript else []
    recent_statements = [{"speaker": t["speaker"], "message": t["message"]} for t in transcript[-5:]]

    # Format agent info
    agent_info = []
    for member in members:
        if member in profiles:
            p = profiles[member]
            expertise = ", ".join(p.get("expertise", []))
            agent_info.append(f"- {member} ({p.get('domain', '?')}): {expertise}")

    prompt = f"""You are facilitating a council meeting.

TOPIC: {topic}
AGENDA: {json.dumps(agenda)}

COUNCIL MEMBERS:
{chr(10).join(agent_info)}

RECENT SPEAKERS (last 5): {recent_speakers}

RECENT DISCUSSION:
{chr(10).join([f"{s['speaker']}: {s['message'][:200]}..." for s in recent_statements]) if recent_statements else "Meeting just started."}

Based on:
1. The agenda progression
2. Who hasn't spoken recently
3. Who has relevant expertise for the current discussion
4. Natural conversation flow

Decide who speaks next.

RESPOND IN JSON FORMAT ONLY:
{{"next_speaker": "AGENT_NAME", "directive": "Optional specific question or null"}}

Choose from: {members}
Do NOT choose yourself (ATLAS) unless wrapping up."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            system=CONVENER_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()
        # Parse JSON
        if "{" in text and "}" in text:
            json_str = text[text.index("{"):text.rindex("}")+1]
            data = json.loads(json_str)
            return data.get("next_speaker", members[0]), data.get("directive")
    except Exception as e:
        print(f"Convener decision failed: {e}")

    # Fallback: round-robin
    for member in members:
        if member not in recent_speakers:
            return member, None
    return members[0], None

async def convener_opening(meeting: Dict) -> str:
    """Generate opening statement for meeting"""
    members = meeting.get("council_members", [])
    agenda = meeting.get("agenda", [])
    topic = meeting.get("topic", "")
    title = meeting.get("title", "Council Meeting")

    prompt = f"""Generate an opening statement for a council meeting.

TITLE: {title}
TOPIC: {topic}
PARTICIPANTS: {', '.join(members)}
AGENDA: {json.dumps(agenda) if agenda else 'Open discussion'}

Keep it brief (3-4 sentences):
1. Welcome the council
2. State the topic/purpose
3. Outline the agenda
4. Invite first speaker

Be commanding and professional. You are ATLAS, the Convener."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=CONVENER_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Welcome, council. Today we discuss: {topic}. Let's begin."

async def convener_synthesize_decision(meeting: Dict, transcript: List[Dict], topic: Optional[str] = None) -> str:
    """Synthesize discussion into a decision"""

    statements = [{"speaker": t["speaker"], "message": t["message"]} for t in transcript[-20:]]

    prompt = f"""Synthesize the council discussion into a clear decision.

MEETING TOPIC: {meeting.get('topic', '')}
SPECIFIC DECISION TOPIC: {topic or 'Overall direction'}

DISCUSSION:
{chr(10).join([f"{s['speaker']}: {s['message'][:300]}" for s in statements])}

Provide:
1. The decision/consensus reached
2. Any dissenting views to note
3. Key rationale
4. Recommended next steps

Be clear and decisive. You are ATLAS, summarizing for the council."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=CONVENER_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"Decision pending - synthesis failed: {str(e)}"

async def convener_closing(meeting: Dict, transcript: List[Dict], decisions: List[Dict], actions: List[Dict]) -> str:
    """Generate closing statement"""

    prompt = f"""Generate a closing statement for a council meeting.

TOPIC: {meeting.get('topic', '')}
PARTICIPANTS: {', '.join(meeting.get('council_members', []))}
DISCUSSION POINTS: {len(transcript)}

DECISIONS MADE:
{chr(10).join([f"- {d.get('decision', '')}" for d in decisions]) or 'None formally recorded'}

ACTION ITEMS:
{chr(10).join([f"- {a.get('action', '')} -> {a.get('assigned_to', '')}" for a in actions]) or 'None assigned'}

Keep it brief (3-4 sentences):
1. Thank the council
2. Summarize key outcomes
3. Note action items
4. Adjourn"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=CONVENER_SYSTEM,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return "Thank you, council. Meeting adjourned."

# =============================================================================
# HELPERS
# =============================================================================

def select_agents_for_topic(topic: str) -> List[str]:
    """Auto-select appropriate agents based on topic keywords"""
    topic_lower = topic.lower()
    selected = set()

    for keyword, agents in TOPIC_AGENT_MAPPING.items():
        if keyword in topic_lower:
            selected.update(agents)

    # Always include core members
    selected.add("ATLAS")  # Convener
    selected.add("ATHENA")  # Scribe

    # If no specific matches, add general advisors
    if len(selected) == 2:
        selected.update(["CHIRON", "ARTIFICER"])

    return list(selected)

async def record_to_transcript(
    meeting_id: str,
    speaker: str,
    message: str,
    message_type: str = "discussion",
    metadata: dict = None
) -> Optional[Dict]:
    """Record an utterance to the transcript"""
    # Get current sequence number
    transcript = await get_transcript(meeting_id)
    seq_num = len(transcript) + 1

    record = await db_insert("council_transcript", {
        "meeting_id": meeting_id,
        "speaker": speaker,
        "message": message,
        "message_type": message_type,
        "sequence_num": seq_num,
        "metadata": metadata or {}
    })

    # Also send to scribe for processing
    try:
        async with httpx.AsyncClient() as http:
            await http.post(
                f"{SCRIBE_URL}/scribe/record",
                json={
                    "meeting_id": meeting_id,
                    "speaker": speaker,
                    "message": message,
                    "message_type": message_type,
                    "sequence_num": seq_num
                },
                timeout=5.0
            )
    except Exception:
        pass  # Scribe might not be running yet

    return record

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "agent": "CONVENER",
        "role": "Council Meeting Facilitator",
        "port": 8300,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/council/convene")
async def convene_meeting(req: ConveneRequest):
    """Create a new council meeting"""

    # Select agents if not provided
    if req.council_members:
        members = req.council_members
    else:
        members = select_agents_for_topic(req.topic)

    # Create meeting record
    meeting_data = {
        "title": req.title,
        "topic": req.topic,
        "agenda": req.agenda,
        "council_members": members,
        "convener": req.convener,
        "scribe": req.scribe,
        "status": "scheduled"
    }

    meeting = await db_insert("council_meetings", meeting_data)
    if not meeting:
        raise HTTPException(status_code=500, detail="Failed to create meeting")

    await publish_event("meeting.created", {
        "meeting_id": meeting["id"],
        "topic": req.topic,
        "members": members
    })

    return {
        "meeting_id": meeting["id"],
        "title": req.title,
        "topic": req.topic,
        "council_members": members,
        "agenda": req.agenda,
        "status": "scheduled",
        "message": "Meeting convened. Call /council/{id}/start to begin."
    }

@app.post("/council/{meeting_id}/start")
async def start_meeting(meeting_id: str):
    """Start a council meeting"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] != "scheduled":
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not scheduled")

    # Update status
    await db_update("council_meetings", {"id": meeting_id}, {
        "status": "active",
        "started_at": datetime.utcnow().isoformat()
    })

    # Generate opening statement
    opening = await convener_opening(meeting)

    # Record opening to transcript
    await record_to_transcript(
        meeting_id,
        "ATLAS",
        opening,
        message_type="summary"
    )

    await publish_event("meeting.started", {
        "meeting_id": meeting_id,
        "topic": meeting["topic"],
        "members": meeting["council_members"]
    })

    return {
        "meeting_id": meeting_id,
        "status": "active",
        "opening_statement": opening,
        "participants": meeting["council_members"],
        "agenda": meeting.get("agenda", [])
    }

@app.post("/council/{meeting_id}/turn")
async def meeting_turn(meeting_id: str, req: TurnRequest = None):
    """Execute one turn of the meeting - an agent speaks"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not active")

    # Get transcript and profiles
    transcript = await get_transcript(meeting_id)
    profiles = await get_all_agent_profiles()

    # Decide who speaks next
    next_speaker, directive = await convener_decide_next_speaker(meeting, transcript, profiles)

    # Build context
    meeting_context = f"Meeting: {meeting['title']}\nTopic: {meeting['topic']}"
    previous_statements = [{"speaker": t["speaker"], "message": t["message"]} for t in transcript[-10:]]

    # Get agent response
    response = await call_agent_respond(
        next_speaker,
        meeting_context,
        meeting["topic"],
        previous_statements,
        directive
    )

    # Record to transcript
    await record_to_transcript(
        meeting_id,
        next_speaker,
        response,
        message_type="discussion"
    )

    await publish_event("agent.spoke", {
        "meeting_id": meeting_id,
        "speaker": next_speaker,
        "directive": directive
    })

    return {
        "speaker": next_speaker,
        "response": response,
        "directive": directive,
        "turn_number": len(transcript) + 1
    }

@app.post("/council/{meeting_id}/inject")
async def inject_directive(meeting_id: str, req: InjectRequest):
    """Inject a directive from DAMON into the meeting"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not active")

    # Record DAMON's directive
    await record_to_transcript(
        meeting_id,
        "DAMON",
        req.message,
        message_type="directive",
        metadata={"priority": req.priority}
    )

    # ATLAS acknowledges
    ack = f"Understood. The council will incorporate this direction: {req.message[:100]}..."
    await record_to_transcript(
        meeting_id,
        "ATLAS",
        ack,
        message_type="discussion"
    )

    await publish_event("directive.injected", {
        "meeting_id": meeting_id,
        "message": req.message[:100],
        "priority": req.priority
    })

    return {
        "status": "injected",
        "message": req.message,
        "acknowledgment": ack
    }

@app.post("/council/{meeting_id}/decide")
async def make_decision(meeting_id: str, req: DecideRequest = None):
    """Synthesize discussion into a formal decision"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not active")

    transcript = await get_transcript(meeting_id)
    topic = req.topic if req else None

    # Synthesize decision
    decision_text = await convener_synthesize_decision(meeting, transcript, topic)

    # Record decision
    decision = await db_insert("council_decisions", {
        "meeting_id": meeting_id,
        "decision": decision_text,
        "proposed_by": "ATLAS",
        "approved_by": meeting["council_members"],
        "status": "approved"
    })

    # Record to transcript
    await record_to_transcript(
        meeting_id,
        "ATLAS",
        f"DECISION RECORDED: {decision_text}",
        message_type="decision"
    )

    await publish_event("decision.made", {
        "meeting_id": meeting_id,
        "decision_id": decision["id"] if decision else None,
        "summary": decision_text[:200]
    })

    return {
        "decision_id": decision["id"] if decision else None,
        "decision": decision_text,
        "status": "approved",
        "approved_by": meeting["council_members"]
    }

@app.post("/council/{meeting_id}/action")
async def assign_action(meeting_id: str, req: ActionRequest):
    """Assign an action item to an agent"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Create action item
    action_data = {
        "meeting_id": meeting_id,
        "action": req.action,
        "assigned_to": req.assigned_to,
        "due_date": req.due_date,
        "status": "pending"
    }

    action = await db_insert("council_actions", action_data)

    # Record to transcript
    await record_to_transcript(
        meeting_id,
        "ATLAS",
        f"ACTION ASSIGNED: {req.action} -> {req.assigned_to}",
        message_type="action_item"
    )

    await publish_event("action.assigned", {
        "meeting_id": meeting_id,
        "action_id": action["id"] if action else None,
        "action": req.action,
        "assigned_to": req.assigned_to
    })

    return {
        "action_id": action["id"] if action else None,
        "action": req.action,
        "assigned_to": req.assigned_to,
        "due_date": req.due_date,
        "status": "pending"
    }

@app.post("/council/{meeting_id}/adjourn")
async def adjourn_meeting(meeting_id: str):
    """End the meeting with a summary"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not active")

    # Get transcript, decisions, actions
    transcript = await get_transcript(meeting_id)
    decisions = await db_get("council_decisions", {"meeting_id": meeting_id})
    actions = await db_get("council_actions", {"meeting_id": meeting_id})

    # Generate closing statement
    closing = await convener_closing(meeting, transcript, decisions, actions)

    # Record closing
    await record_to_transcript(
        meeting_id,
        "ATLAS",
        closing,
        message_type="summary"
    )

    # Update meeting status
    await db_update("council_meetings", {"id": meeting_id}, {
        "status": "completed",
        "ended_at": datetime.utcnow().isoformat()
    })

    await publish_event("meeting.ended", {
        "meeting_id": meeting_id,
        "topic": meeting["topic"],
        "decisions_count": len(decisions),
        "actions_count": len(actions)
    })

    return {
        "meeting_id": meeting_id,
        "status": "completed",
        "closing_statement": closing,
        "decisions_count": len(decisions),
        "actions_count": len(actions),
        "transcript_entries": len(transcript)
    }

@app.get("/council/{meeting_id}/status")
async def get_meeting_status(meeting_id: str):
    """Get current meeting status with transcript, decisions, and actions"""

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = await get_transcript(meeting_id)
    decisions = await db_get("council_decisions", {"meeting_id": meeting_id})
    actions = await db_get("council_actions", {"meeting_id": meeting_id})

    return {
        "meeting": meeting,
        "transcript": transcript,
        "decisions": decisions,
        "actions": actions,
        "summary": {
            "status": meeting["status"],
            "transcript_entries": len(transcript),
            "decisions_count": len(decisions),
            "actions_count": len(actions)
        }
    }

@app.get("/council/active")
async def list_active_meetings():
    """List all active meetings"""
    meetings = await db_get("council_meetings", {"status": "active"})
    return {"active_meetings": meetings}

@app.get("/council/recent")
async def list_recent_meetings():
    """List recent meetings"""
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/council_meetings",
                params={"order": "created_at.desc", "limit": 10},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                return {"recent_meetings": resp.json()}
    except Exception as e:
        print(f"List recent failed: {e}")
    return {"recent_meetings": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
