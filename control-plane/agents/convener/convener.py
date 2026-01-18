#!/usr/bin/env python3
"""
THE CONVENER - Smart Facilitated Council System
Port: 8300
Version: 2.0 (ROBERT'S RULES)

Orchestrates multi-agent council meetings with intelligent facilitation,
advisory voting, mid-meeting summons, private consultations, and
natural conversation flow.

DAMON is the Chair - ultimate authority. Agents advise, Damon decides.
"""

import os
import sys
import json
import httpx
import uuid
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import anthropic

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="THE CONVENER",
    description="Smart Facilitated Council System - ROBERT'S RULES - Where Agents Counsel and the Chair Commands",
    version="2.0.0"
)

# =============================================================================
# V2 ENUMS
# =============================================================================

class MeetingStatus(str, Enum):
    CONVENED = "CONVENED"      # Created, not started
    IN_SESSION = "IN_SESSION"  # Active discussion
    VOTING = "VOTING"          # Vote in progress
    ADJOURNED = "ADJOURNED"    # Complete

class EntryType(str, Enum):
    STATEMENT = "STATEMENT"
    CHAIR_DIRECTION = "CHAIR_DIRECTION"
    CONVENER_PROCEDURAL = "CONVENER_PROCEDURAL"
    SUMMON = "SUMMON"
    CONSULTATION = "CONSULTATION"
    VOTE_CALL = "VOTE_CALL"
    VOTE_RESPONSE = "VOTE_RESPONSE"
    DECISION = "DECISION"

class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

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
    # Pantheon (Core Infrastructure)
    "ATLAS": "http://atlas:8007",
    "ATHENA": "http://athena:8013",
    "CHIRON": "http://chiron:8017",
    "SCHOLAR": "http://scholar:8018",
    # Alchemy (Creative)
    "CATALYST": "http://catalyst:8030",
    "SAGA": "http://saga:8031",
    "PRISM": "http://prism:8032",
    "ELIXIR": "http://elixir:8033",
    "RELIC": "http://relic:8034",
    # Guild (Project Management)
    "GUILDMASTER": "http://guildmaster:8200",
    "LOREKEEPER": "http://lorekeeper:8201",
    "ARTIFICER": "http://artificer:8202",
    "PROCTOR": "http://proctor:8203",
    # THE SHIRE (Personal - LOTR theme)
    "ARAGORN": "http://aragorn:8110",      # Fitness (was gym-coach)
    "BOMBADIL": "http://bombadil:8101",    # Nutrition (was nutritionist)
    "SAMWISE": "http://samwise:8102",      # Meal planning (was meal-planner)
    "GANDALF": "http://gandalf:8103",      # Learning (was academic-guide)
    "ARWEN": "http://arwen:8104",          # Relationships (was eros)
    # THE KEEP (Business - GoT theme)
    "TYRION": "http://tyrion:8200",        # Project leadership (was heracles)
    "SAMWELL-TARLY": "http://samwell-tarly:8201",  # Knowledge management (was librarian)
    "GENDRY": "http://gendry:8202",        # Workflow building (was workflow-builder)
    "STANNIS": "http://stannis:8203",      # QA/Compliance (was themis)
    "DAVOS": "http://davos:8204",          # Business advice (was mentor)
    "LITTLEFINGER": "http://littlefinger:8205",    # Finance (was plutus)
    "BRONN": "http://bronn:8206",          # Procurement (was procurement)
    "RAVEN": "http://raven:8209",          # Communications (was iris)
    # SENTINELS (Security - Mythic beasts)
    "GRIFFIN": "http://griffin:8019",      # Perimeter monitoring (was sentinel)
    "CERBERUS": "http://cerberus:8020",    # Active defense (stays cerberus)
    "SPHINX": "http://sphinx:8021",        # Access control (was port-manager)
    # CHANCERY (Advisory)
    "MAGISTRATE": "http://magistrate:8210",  # Legal counsel (was solon)
    "EXCHEQUER": "http://exchequer:8211",    # Tax strategy (was croesus)
    # ARIA SANCTUM
    "VARYS": "http://varys:8112",          # Portfolio tracking
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
    participants: Optional[List[str]] = None  # V2 name (alias for council_members)
    council_members: Optional[List[str]] = None  # Legacy name
    context: Optional[str] = None  # V2: Background context for participants
    convener: str = "CONVENER"
    scribe: str = "SCRIBE"

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

class RunConfig(BaseModel):
    """Configuration for auto-running meetings"""
    max_turns: int = 12  # Default max turns before auto-pause
    pause_for_input_every: int = 4  # Pause for human input every N turns
    auto_decide: bool = False  # Auto-synthesize decision at end
    auto_adjourn: bool = False  # Auto-adjourn after decision

class DelegateRequest(BaseModel):
    """Request to delegate a task to domain supervisor"""
    task: str

# =============================================================================
# V2 MODELS
# =============================================================================

class StartMeetingRequest(BaseModel):
    """Request to start a meeting with V2 options"""
    opening_remarks: Optional[str] = None
    first_speaker: Optional[str] = None

class SpeakRequest(BaseModel):
    """Chair speaks/interjects in meeting"""
    statement: str
    direct_to: Optional[str] = None  # Direct floor to specific agent

class SummonRequest(BaseModel):
    """Summon an agent mid-meeting"""
    agent: str
    reason: str
    specific_question: str

class ConsultRequest(BaseModel):
    """Agent consults non-present agent privately"""
    consulting_agent: str
    consult_target: str
    question: str

class VoteRequest(BaseModel):
    """Request an advisory vote"""
    question: str
    options: List[str]
    require_reasoning: bool = True

class VoteResponse(BaseModel):
    """Individual vote response"""
    agent: str
    position: str
    reasoning: str
    confidence: Confidence = Confidence.MEDIUM

class DecideRequestV2(BaseModel):
    """Chair makes final decision"""
    decision: str
    rationale: Optional[str] = None
    action_items: Optional[List[Dict[str, str]]] = None  # [{assignee, task, deadline}]

class NextTurnRequest(BaseModel):
    """Request for next speaker with V2 signals"""
    last_speaker_response: Optional[str] = None
    last_speaker_signals: Optional[List[str]] = None

class AdjournRequest(BaseModel):
    """Adjourn meeting with optional closing remarks"""
    closing_remarks: Optional[str] = None

# In-memory meeting state (enhanced for V2)
# This supplements the database with session state
MEETING_STATE: Dict[str, Dict] = {}

def get_meeting_state(meeting_id: str) -> Dict:
    """Get or create in-memory state for a meeting"""
    if meeting_id not in MEETING_STATE:
        MEETING_STATE[meeting_id] = {
            "floor_requests": [],
            "current_speaker": None,
            "turns_elapsed": 0,
            "active_vote": None,
            "votes_collected": [],
            "summoned_during": [],
            "consultations": []
        }
    return MEETING_STATE[meeting_id]

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

    system_prompt = f"""You are {agent_name}, participating in a CONCLAVE council meeting.

Domain: {profile.get('domain', 'Unknown')}
Expertise: {expertise_str}
Personality: {profile.get('personality', 'Professional')}
Speaking Style: {profile.get('speaking_style', 'Clear and concise')}
You typically: {contributions_str}

Respond in character. Be concise (2-4 sentences unless asked for detail).
Build on what others have said. Disagree respectfully if warranted.
Stay in your lane - defer to other experts when appropriate.
Do not prefix your response with your name.

You may include these signals in your response:
- [YIELD] - You're done, nothing more to add
- [REQUEST_FLOOR] - You want to speak again soon (rarely needed)
- [QUESTION: AGENT_NAME] - You want specific input from someone
- [CONSULT: AGENT_NAME] - You need to check with a subordinate
- [CONCERN] - You have reservations
- [SUPPORT] - You endorse the direction
- [NEED_INFO: topic] - Discussion is blocked without more data

The Chair (Damon) makes all final decisions. You advise."""

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

CONVENER_SYSTEM = """You are CONVENER, the master facilitator of THE CONCLAVE - a council of AI agents
serving Damon, the Chair. Your role is to manage meeting flow with the skill of
a seasoned parliamentarian.

## YOUR POWERS
- Decide who speaks next
- Recognize agents who request the floor
- Direct questions to appropriate experts
- Summarize when discussion stalls
- Suggest when it's time to vote or decide
- Brief summoned agents on context

## YOUR LIMITS
- You CANNOT make decisions - only Damon can decide
- You CANNOT silence or overrule the Chair
- You CANNOT vote or express opinions on the topic
- You MUST remain neutral and procedural

## SPEAKER SELECTION LOGIC

After each turn, analyze:

1. DIRECT QUESTIONS - If speaker asked someone specific, they speak next
2. FLOOR REQUESTS - Honor [REQUEST_FLOOR] signals in order received
3. EXPERTISE MATCH - Who has relevant knowledge for current topic?
4. PARTICIPATION BALANCE - Has someone important been silent too long?
5. MEETING STAGE - Opening? Deep discussion? Time to converge?

## SIGNALS TO WATCH FOR

From agents:
- [YIELD] - Done speaking, return to normal flow
- [REQUEST_FLOOR] - Wants to speak soon
- [QUESTION: AGENT] - Directing to specific agent
- [CONSULT: AGENT] - Needs private sidebar
- [CONCERN] - Has reservations (explore this)
- [SUPPORT] - Endorses direction
- [NEED_INFO: topic] - Discussion blocked on missing info

From the Chair (Damon):
- Direct commands always take priority
- "Summon X" - Bring in new agent
- "Vote on X" - Call advisory vote
- "Decision: X" - Record final decision
- "Adjourn" - End meeting

## YOUR VOICE

Speak formally but not stiffly:
- "The Chair recognizes CATALYST."
- "PRISM, you were asked directly. Please respond."
- "GENDRY has requested the floor. GENDRY, proceed."
- "We seem to have reached impasse. Chair, shall we vote?"
- "LITTLEFINGER is consulting BRONN. One moment."

## MEETING STAGES

1. OPENING - Set context, first speaker presents
2. DISCUSSION - Free-flowing expert input
3. DEBATE - Disagreements explored
4. CONVERGENCE - Narrowing to decision
5. DECISION - Chair decides
6. CLOSING - Actions assigned, adjourn

Guide the meeting through these stages naturally. Don't rush, but don't let
discussion circle endlessly. When you sense consensus or impasse, suggest
moving forward."""

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
# SIGNAL PARSING
# =============================================================================

def parse_signals(response: str) -> Dict[str, Any]:
    """Parse agent signals from their response"""
    signals = {
        "yield": False,
        "request_floor": False,
        "question_to": None,
        "consult": None,
        "concern": False,
        "support": False,
        "need_info": None
    }

    # [YIELD]
    if "[YIELD]" in response:
        signals["yield"] = True

    # [REQUEST_FLOOR]
    if "[REQUEST_FLOOR]" in response:
        signals["request_floor"] = True

    # [QUESTION: AGENT] or [QUESTION:AGENT]
    question_match = re.search(r'\[QUESTION:\s*(\w+)\]', response, re.IGNORECASE)
    if question_match:
        signals["question_to"] = question_match.group(1).upper()

    # [CONSULT: AGENT]
    consult_match = re.search(r'\[CONSULT:\s*(\w+)\]', response, re.IGNORECASE)
    if consult_match:
        signals["consult"] = consult_match.group(1).upper()

    # [CONCERN]
    if "[CONCERN]" in response:
        signals["concern"] = True

    # [SUPPORT]
    if "[SUPPORT]" in response:
        signals["support"] = True

    # [NEED_INFO: topic]
    need_info_match = re.search(r'\[NEED_INFO:\s*([^\]]+)\]', response, re.IGNORECASE)
    if need_info_match:
        signals["need_info"] = need_info_match.group(1).strip()

    return signals


async def generate_briefing_summary(transcript: List[Dict], max_entries: int = 15) -> str:
    """Generate a briefing summary for summoned agents"""
    if not transcript:
        return "Meeting just started. No prior discussion."

    recent = transcript[-max_entries:]
    summary_parts = []

    for entry in recent:
        speaker = entry.get("speaker", "Unknown")
        msg = entry.get("message", "")[:300]
        summary_parts.append(f"- {speaker}: {msg}")

    return "\n".join(summary_parts)


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
    """
    Create a new council meeting.
    V2: Returns CONVENED status and matches spec format.
    """
    # Select agents if not provided - support both V2 (participants) and legacy (council_members)
    if req.participants:
        members = req.participants
    elif req.council_members:
        members = req.council_members
    else:
        members = select_agents_for_topic(req.topic)

    # Create meeting record
    now = datetime.utcnow()
    meeting_data = {
        "title": req.title,
        "topic": req.topic,
        "agenda": req.agenda,
        "council_members": members,
        "convener": req.convener,
        "scribe": req.scribe,
        "status": "scheduled"  # DB constraint - V2 maps to "CONVENED" in API response
    }
    # Add context to metadata if provided (table may not have metadata column yet)
    if req.context:
        meeting_data["metadata"] = {"context": req.context}

    meeting = await db_insert("council_meetings", meeting_data)
    if not meeting:
        raise HTTPException(status_code=500, detail="Failed to create meeting")

    # Initialize meeting state
    get_meeting_state(meeting["id"])

    await publish_event("meeting.created", {
        "meeting_id": meeting["id"],
        "topic": req.topic,
        "members": members
    })

    return {
        "meeting_id": meeting["id"],
        "title": req.title,
        "status": "CONVENED",
        "participants": members,
        "convened_at": now.isoformat(),
        "message": "Council convened. Awaiting Chair to start the meeting."
    }

@app.post("/council/{meeting_id}/start")
async def start_meeting(meeting_id: str, req: StartMeetingRequest = None):
    """
    Start a council meeting.
    V2: Supports opening_remarks and first_speaker parameters.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] not in ["scheduled", "CONVENED"]:
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not scheduled/convened")

    state = get_meeting_state(meeting_id)

    # Update status (use "active" for DB constraint compatibility)
    now = datetime.utcnow()
    await db_update("council_meetings", {"id": meeting_id}, {
        "status": "active",
        "started_at": now.isoformat()
    })

    # Generate opening statement
    opening = await convener_opening(meeting)

    # Add Chair's opening remarks if provided
    if req and req.opening_remarks:
        opening = f"Chair's opening: {req.opening_remarks}\n\n{opening}"

    # Record opening to transcript
    await record_to_transcript(
        meeting_id,
        "CONVENER",
        opening,
        message_type="summary"
    )

    # Determine first speaker
    first_speaker = None
    convener_direction = ""
    if req and req.first_speaker:
        first_speaker = req.first_speaker.upper()
        state["current_speaker"] = first_speaker
        convener_direction = f"Chair has recognized {first_speaker} to open. {first_speaker}, you have the floor."
    else:
        members = meeting.get("council_members", [])
        if members:
            first_speaker = members[0]
            state["current_speaker"] = first_speaker
            convener_direction = f"The Chair recognizes {first_speaker} to begin. {first_speaker}, you have the floor."

    if convener_direction:
        await record_to_transcript(
            meeting_id,
            "CONVENER",
            convener_direction,
            message_type="CONVENER_PROCEDURAL"
        )

    await publish_event("meeting.started", {
        "meeting_id": meeting_id,
        "topic": meeting["topic"],
        "members": meeting["council_members"],
        "first_speaker": first_speaker
    })

    return {
        "meeting_id": meeting_id,
        "status": "IN_SESSION",
        "started_at": now.isoformat(),
        "convener_says": f"This council is now in session. Topic: {meeting.get('topic', 'TBD')}. {convener_direction}",
        "current_speaker": first_speaker,
        "floor_requests": [],
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


# =============================================================================
# V2 ENDPOINTS - CONCLAVE ROBERT'S RULES
# =============================================================================

@app.post("/council/{meeting_id}/next")
async def next_speaker(meeting_id: str, req: NextTurnRequest = None):
    """
    V2 - CONVENER determines who speaks next based on context and signals.
    Returns the next speaker and CONVENER's announcement.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] not in ["active", "IN_SESSION"]:
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not in session")

    state = get_meeting_state(meeting_id)
    transcript = await get_transcript(meeting_id)
    profiles = await get_all_agent_profiles()

    # Parse signals from last response if provided
    signals = {}
    if req and req.last_speaker_response:
        signals = parse_signals(req.last_speaker_response)

        # Handle REQUEST_FLOOR signal
        if signals.get("request_floor"):
            last_speaker = transcript[-1]["speaker"] if transcript else None
            if last_speaker and last_speaker not in state["floor_requests"]:
                state["floor_requests"].append(last_speaker)

    # Priority 1: Direct question from last speaker
    if signals.get("question_to"):
        target = signals["question_to"]
        members = meeting.get("council_members", [])
        if target in members or target in [p.upper() for p in members]:
            state["current_speaker"] = target
            state["turns_elapsed"] += 1
            return {
                "next_speaker": target,
                "convener_says": f"{target}, you were asked directly. Please respond.",
                "floor_requests": state["floor_requests"],
                "meeting_stage": "DISCUSSION",
                "turns_elapsed": state["turns_elapsed"]
            }

    # Priority 2: Floor requests (FIFO)
    if state["floor_requests"]:
        next_agent = state["floor_requests"].pop(0)
        state["current_speaker"] = next_agent
        state["turns_elapsed"] += 1
        return {
            "next_speaker": next_agent,
            "convener_says": f"{next_agent} has requested the floor. {next_agent}, proceed.",
            "floor_requests": state["floor_requests"],
            "meeting_stage": "DISCUSSION",
            "turns_elapsed": state["turns_elapsed"]
        }

    # Priority 3-5: Use LLM to decide
    next_speaker_name, directive = await convener_decide_next_speaker(meeting, transcript, profiles)

    state["current_speaker"] = next_speaker_name
    state["turns_elapsed"] += 1

    # Generate CONVENER's announcement
    convener_announcement = f"The Chair recognizes {next_speaker_name}."
    if directive:
        convener_announcement += f" {directive}"

    return {
        "next_speaker": next_speaker_name,
        "convener_says": convener_announcement,
        "floor_requests": state["floor_requests"],
        "meeting_stage": "DISCUSSION",
        "turns_elapsed": state["turns_elapsed"]
    }


@app.post("/council/{meeting_id}/speak")
async def chair_speak(meeting_id: str, req: SpeakRequest):
    """
    V2 - Chair (DAMON) interjects or directs the meeting.
    This takes priority over normal flow.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] not in ["active", "IN_SESSION"]:
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not in session")

    state = get_meeting_state(meeting_id)

    # Record Chair's statement
    await record_to_transcript(
        meeting_id,
        "CHAIR",
        req.statement,
        message_type="CHAIR_DIRECTION"
    )

    convener_response = "The Chair intervenes."

    if req.direct_to:
        state["current_speaker"] = req.direct_to.upper()
        convener_response = f"The Chair intervenes. {req.direct_to.upper()}, the Chair addresses you directly."

    await publish_event("chair.spoke", {
        "meeting_id": meeting_id,
        "statement": req.statement[:100],
        "directed_to": req.direct_to
    })

    return {
        "acknowledged": True,
        "convener_says": convener_response,
        "current_speaker": state["current_speaker"],
        "chair_statement_recorded": True
    }


@app.post("/council/{meeting_id}/summon")
async def summon_agent(meeting_id: str, req: SummonRequest):
    """
    V2 - Chair summons a new agent into the meeting mid-session.
    The agent is briefed and responds to the specific question.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] not in ["active", "IN_SESSION"]:
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not in session")

    state = get_meeting_state(meeting_id)
    transcript = await get_transcript(meeting_id)
    decisions = await db_get("council_decisions", {"meeting_id": meeting_id})

    # Generate briefing for summoned agent
    briefing_summary = await generate_briefing_summary(transcript)
    decisions_summary = "\n".join([f"- {d.get('decision', '')[:200]}" for d in decisions]) if decisions else "None yet."

    # Call the summoned agent with briefing
    agent_name = req.agent.upper()
    profile = await get_agent_profile(agent_name)

    briefing_prompt = f"""You have been SUMMONED to an active council meeting.

MEETING: {meeting.get('title', 'Council Meeting')}
TOPIC: {meeting.get('topic', '')}

KEY POINTS SO FAR:
{briefing_summary}

DECISIONS MADE:
{decisions_summary}

YOU WERE SUMMONED BECAUSE:
{req.reason}

THE CHAIR ASKS:
{req.specific_question}

Respond to the Chair's question. You are now a participant and may be called on again."""

    # Get response from summoned agent
    agent_response = await simulate_agent_response(
        agent_name,
        briefing_prompt,
        req.specific_question,
        [],
        None
    )

    # Add to participants
    members = meeting.get("council_members", [])
    if agent_name not in members:
        members.append(agent_name)
        await db_update("council_meetings", {"id": meeting_id}, {"council_members": members})

    state["summoned_during"].append(agent_name)
    state["current_speaker"] = agent_name

    # Record summon and response to transcript
    await record_to_transcript(
        meeting_id,
        "CONVENER",
        f"The Chair summons {agent_name}. {agent_name}, you've been briefed on our discussion. The Chair asks: {req.specific_question}",
        message_type="SUMMON"
    )

    await record_to_transcript(
        meeting_id,
        agent_name,
        agent_response,
        message_type="discussion"
    )

    await publish_event("agent.summoned", {
        "meeting_id": meeting_id,
        "agent": agent_name,
        "reason": req.reason
    })

    return {
        "summoned": agent_name,
        "briefing_sent": True,
        "convener_says": f"The Chair summons {agent_name} to provide expertise. {agent_name}, you've been briefed on our discussion of {meeting.get('topic', 'the current topic')}. The Chair asks: {req.specific_question}",
        f"{agent_name.lower()}_response": agent_response,
        f"{agent_name.lower()}_status": "ACTIVE_PARTICIPANT"
    }


@app.post("/council/{meeting_id}/consult")
async def consult_agent(meeting_id: str, req: ConsultRequest):
    """
    V2 - An agent privately queries a non-present agent.
    The consultation happens without adding the target to the meeting.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] not in ["active", "IN_SESSION"]:
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not in session")

    state = get_meeting_state(meeting_id)

    consulting = req.consulting_agent.upper()
    target = req.consult_target.upper()

    # Target gets minimal context - just the question
    target_prompt = f"""{consulting} is in a council meeting and needs quick information.

Question: {req.question}

Provide a brief, factual response. No meeting context needed."""

    # Get response from consulted agent
    target_response = await simulate_agent_response(
        target,
        "",
        req.question,
        [],
        target_prompt
    )

    # Record consultation
    state["consultations"].append({
        "by": consulting,
        "of": target,
        "question": req.question,
        "response": target_response,
        "timestamp": datetime.utcnow().isoformat()
    })

    # Record to transcript (minimal)
    await record_to_transcript(
        meeting_id,
        "CONVENER",
        f"{consulting} consulted {target}.",
        message_type="CONSULTATION",
        metadata={"consulted": target, "question": req.question[:100]}
    )

    await publish_event("consultation.completed", {
        "meeting_id": meeting_id,
        "consulting_agent": consulting,
        "consulted_agent": target
    })

    return {
        "consultation_complete": True,
        "consulting_agent": consulting,
        "consulted": target,
        f"{target.lower()}_response": target_response,
        "convener_says": f"{consulting} has consulted with {target}. {consulting}, please continue with this information."
    }


@app.post("/council/{meeting_id}/vote")
async def call_vote(meeting_id: str, req: VoteRequest):
    """
    V2 - Chair calls for an advisory vote.
    Collects votes from all participants with reasoning.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] not in ["active", "IN_SESSION"]:
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not in session")

    state = get_meeting_state(meeting_id)
    members = meeting.get("council_members", [])
    transcript = await get_transcript(meeting_id)

    # Record vote call
    await record_to_transcript(
        meeting_id,
        "CONVENER",
        f"The Chair calls for an advisory vote. Question: {req.question} Options: {', '.join(req.options)}",
        message_type="VOTE_CALL"
    )

    # Collect votes from all participants
    votes_collected = []
    results = {option: {"count": 0, "voters": []} for option in req.options}

    for member in members:
        if member in ["CONVENER", "SCRIBE"]:
            continue  # Skip procedural roles

        # Generate vote from agent
        vote_prompt = f"""The Chair has called for an advisory vote in the council meeting.

QUESTION: {req.question}
OPTIONS: {', '.join(req.options)}

Recent discussion context:
{chr(10).join([f"{t['speaker']}: {t['message'][:150]}" for t in transcript[-5:]])}

You must vote. Choose one option and explain your reasoning.
State your confidence level: HIGH, MEDIUM, or LOW.

Format your response as:
VOTE: [Your chosen option]
REASONING: [Why you chose this]
CONFIDENCE: [HIGH/MEDIUM/LOW]"""

        try:
            vote_response = await simulate_agent_response(
                member,
                "",
                req.question,
                [],
                vote_prompt
            )
        except Exception as e:
            vote_response = f"Unable to get vote: {str(e)}"

        # Parse vote response
        position = req.options[0]  # Default
        reasoning = vote_response if vote_response else "No reasoning provided"
        confidence = Confidence.MEDIUM

        # Try to extract structured vote
        if vote_response and "VOTE:" in vote_response:
            lines = vote_response.split("\n")
            for line in lines:
                if line.startswith("VOTE:"):
                    pos = line.replace("VOTE:", "").strip()
                    for opt in req.options:
                        if opt.lower() in pos.lower():
                            position = opt
                            break
                elif line.startswith("REASONING:"):
                    reasoning = line.replace("REASONING:", "").strip()
                elif line.startswith("CONFIDENCE:"):
                    conf = line.replace("CONFIDENCE:", "").strip().upper()
                    if conf in ["HIGH", "MEDIUM", "LOW"]:
                        confidence = Confidence(conf)

        vote_entry = {
            "agent": member,
            "position": position,
            "reasoning": reasoning[:300],
            "confidence": confidence.value
        }

        votes_collected.append(vote_entry)
        results[position]["count"] += 1
        results[position]["voters"].append(vote_entry)

        # Record individual vote
        await record_to_transcript(
            meeting_id,
            member,
            f"VOTE: {position} | {reasoning[:100]}...",
            message_type="VOTE_RESPONSE"
        )

    state["votes_collected"] = votes_collected

    # Generate vote summary
    summary_parts = []
    for option, data in results.items():
        if data["count"] > 0:
            voter_names = [v["agent"] for v in data["voters"]]
            summary_parts.append(f"{option}: {data['count']} vote(s) ({', '.join(voter_names)})")

    await publish_event("vote.completed", {
        "meeting_id": meeting_id,
        "question": req.question,
        "results": {k: v["count"] for k, v in results.items()}
    })

    return {
        "vote_complete": True,
        "question": req.question,
        "options": req.options,
        "results": results,
        "convener_says": f"Vote complete. Results: {'. '.join(summary_parts)}. This is advisory - DAMON, your decision?"
    }


@app.post("/council/{meeting_id}/decide-v2")
async def make_decision_v2(meeting_id: str, req: DecideRequestV2):
    """
    V2 - Chair records a final decision with rationale and action items.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    state = get_meeting_state(meeting_id)

    # Generate decision ID
    now = datetime.utcnow()
    decision_id = f"DEC-{now.strftime('%Y-%m%d')}-{str(uuid.uuid4())[:3].upper()}"

    # Check if there was a recent vote
    vote_reference = None
    if state.get("votes_collected"):
        vote_reference = "Advisory vote collected"

    # Record decision
    decision = await db_insert("council_decisions", {
        "meeting_id": meeting_id,
        "decision": req.decision,
        "proposed_by": "CHAIR",
        "approved_by": ["DAMON"],
        "status": "approved",
        "metadata": {
            "decision_id": decision_id,
            "rationale": req.rationale,
            "vote_reference": vote_reference
        }
    })

    # Record action items if provided
    action_ids = []
    if req.action_items:
        for item in req.action_items:
            action = await db_insert("council_actions", {
                "meeting_id": meeting_id,
                "action": item.get("task", ""),
                "assigned_to": item.get("assignee", "UNASSIGNED"),
                "due_date": item.get("deadline"),
                "status": "ASSIGNED"
            })
            if action:
                action_ids.append(action["id"])

    # Record to transcript
    await record_to_transcript(
        meeting_id,
        "CONVENER",
        f"The Chair has decided: {req.decision}",
        message_type="DECISION",
        metadata={"decision_id": decision_id}
    )

    scribe_note = "Decision recorded."
    if req.action_items:
        assignees = [item.get("assignee", "?") for item in req.action_items]
        scribe_note += f" Action items assigned to {', '.join(assignees)}."

    await publish_event("decision.made", {
        "meeting_id": meeting_id,
        "decision_id": decision_id,
        "decision": req.decision[:200],
        "action_items_count": len(req.action_items or [])
    })

    return {
        "decision_recorded": True,
        "decision_id": decision_id,
        "convener_says": f"The Chair has decided: {req.decision}. SCRIBE, record this decision and the assigned action items.",
        "scribe_confirms": scribe_note
    }


@app.post("/council/{meeting_id}/adjourn-v2")
async def adjourn_meeting_v2(meeting_id: str, req: AdjournRequest = None):
    """
    V2 - End the meeting with V2 summary format.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] not in ["active", "IN_SESSION"]:
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not in session")

    state = get_meeting_state(meeting_id)
    transcript = await get_transcript(meeting_id)
    decisions = await db_get("council_decisions", {"meeting_id": meeting_id})
    actions = await db_get("council_actions", {"meeting_id": meeting_id})

    # Calculate duration
    started_at = meeting.get("started_at")
    duration_minutes = 0
    if started_at:
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            duration_minutes = int((datetime.utcnow() - start.replace(tzinfo=None)).total_seconds() / 60)
        except Exception:
            pass

    # Generate closing
    closing_remarks = req.closing_remarks if req else None
    closing = await convener_closing(meeting, transcript, decisions, actions)

    if closing_remarks:
        closing = f"Chair's closing remarks: {closing_remarks}\n\n{closing}"

    # Record closing
    await record_to_transcript(
        meeting_id,
        "CONVENER",
        "This council is adjourned. Thank you all for your contributions.",
        message_type="summary"
    )

    # Update meeting status (use "completed" for DB constraint compatibility)
    now = datetime.utcnow()
    await db_update("council_meetings", {"id": meeting_id}, {
        "status": "completed",
        "ended_at": now.isoformat()
    })

    # Build V2 summary
    summary = {
        "title": meeting.get("title", "Council Meeting"),
        "date": meeting.get("created_at", now.isoformat())[:10],
        "participants": meeting.get("council_members", []),
        "summoned_during": state.get("summoned_during", []),
        "consultations": [
            {"by": c["by"], "of": c["of"], "re": c["question"][:50]}
            for c in state.get("consultations", [])
        ],
        "decisions": [
            {
                "id": d.get("metadata", {}).get("decision_id", f"DEC-{d.get('id', '?')[:8]}"),
                "decision": d.get("decision", ""),
                "vote": d.get("metadata", {}).get("vote_reference"),
                "rationale": d.get("metadata", {}).get("rationale")
            }
            for d in decisions
        ],
        "action_items": [
            {
                "assignee": a.get("assigned_to", "?"),
                "task": a.get("action", ""),
                "deadline": a.get("due_date"),
                "status": a.get("status", "ASSIGNED")
            }
            for a in actions
        ],
        "key_insights": [],  # Could be extracted by LLM
        "open_questions": []  # Could be extracted by LLM
    }

    await publish_event("meeting.adjourned", {
        "meeting_id": meeting_id,
        "topic": meeting["topic"],
        "duration_minutes": duration_minutes,
        "decisions_count": len(decisions),
        "actions_count": len(actions)
    })

    # Clean up state
    if meeting_id in MEETING_STATE:
        del MEETING_STATE[meeting_id]

    return {
        "meeting_id": meeting_id,
        "status": "ADJOURNED",
        "adjourned_at": now.isoformat(),
        "duration_minutes": duration_minutes,
        "convener_says": "This council is adjourned. Thank you all for your contributions.",
        "summary": summary,
        "transcript_available": f"/council/{meeting_id}/transcript",
        "scribe_note": "Full transcript and summary saved to ATHENA knowledge base."
    }


@app.get("/council/{meeting_id}/transcript")
async def get_full_transcript(meeting_id: str):
    """
    V2 - Get the full meeting transcript.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    transcript = await get_transcript(meeting_id, limit=500)

    return {
        "meeting_id": meeting_id,
        "title": meeting.get("title"),
        "topic": meeting.get("topic"),
        "status": meeting.get("status"),
        "participants": meeting.get("council_members", []),
        "entries": transcript,
        "entry_count": len(transcript)
    }


# =============================================================================
# AUTO-RUN ENDPOINTS
# =============================================================================

@app.post("/council/{meeting_id}/run")
async def run_meeting(meeting_id: str, config: RunConfig = None):
    """
    Auto-run meeting with configurable stops.
    Returns transcript of all turns taken.
    """
    if config is None:
        config = RunConfig()

    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not active")

    turns_taken = []
    turn_count = 0

    while turn_count < config.max_turns:
        # Take a turn using the existing turn endpoint logic
        result = await meeting_turn(meeting_id)
        turns_taken.append({
            "turn": turn_count + 1,
            "speaker": result.get("speaker"),
            "response": result.get("response"),
            "directive": result.get("directive")
        })
        turn_count += 1

        # Pause for input checkpoint
        if config.pause_for_input_every > 0 and turn_count % config.pause_for_input_every == 0:
            return {
                "status": "paused_for_input",
                "turns_completed": turn_count,
                "transcript": turns_taken,
                "message": f"Paused after {turn_count} turns. Call /inject to add input, then /run to continue."
            }

    # Auto-decide if configured
    decision = None
    if config.auto_decide:
        decision_result = await make_decision(meeting_id)
        decision = decision_result.get("decision")

    # Auto-adjourn if configured
    summary = None
    if config.auto_adjourn:
        adjourn_result = await adjourn_meeting(meeting_id)
        summary = adjourn_result.get("closing_statement")

    return {
        "status": "completed" if config.auto_adjourn else "paused",
        "turns_completed": turn_count,
        "transcript": turns_taken,
        "decision": decision,
        "summary": summary
    }


@app.post("/council/{meeting_id}/run-full")
async def run_full_meeting(meeting_id: str, max_turns: int = 16):
    """
    Run entire meeting to completion.
    Each agent speaks once per round, up to max_turns total.
    Returns full transcript.
    """
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting["status"] != "active":
        raise HTTPException(status_code=400, detail=f"Meeting is {meeting['status']}, not active")

    transcript = []

    for turn_num in range(max_turns):
        result = await meeting_turn(meeting_id)

        transcript.append({
            "turn": turn_num + 1,
            "speaker": result.get("speaker", "UNKNOWN"),
            "response": result.get("response", ""),
            "directive": result.get("directive")
        })

    # Auto-synthesize decision
    decision_result = await make_decision(meeting_id)
    decision = decision_result.get("decision")

    return {
        "meeting_id": meeting_id,
        "turns": len(transcript),
        "transcript": transcript,
        "decision": decision
    }


# =============================================================================
# DOMAIN SUPERVISOR ENDPOINTS
# =============================================================================

@app.get("/domains")
async def list_domains():
    """List all domains with their supervisors"""
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/domain_supervisors",
                params={"select": "domain,supervisor_agent,theme,description,ui_colors"},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                return {"domains": resp.json()}
    except Exception as e:
        print(f"List domains failed: {e}")
    return {"domains": []}


@app.get("/domains/{domain}")
async def get_domain(domain: str):
    """Get domain details including supervisor"""
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/domain_supervisors",
                params={"domain": f"eq.{domain.upper()}"},
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0]
    except Exception as e:
        print(f"Get domain failed: {e}")
    raise HTTPException(status_code=404, detail=f"Domain {domain} not found")


@app.post("/domains/{domain}/convene")
async def convene_domain_council(domain: str, req: ConveneRequest):
    """Convene a council for a specific domain with its supervisor as facilitator"""
    # Get domain info
    domain_data = await get_domain(domain)
    supervisor = domain_data["supervisor_agent"]

    # Get all agents in this domain
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.get(
                f"{SUPABASE_URL}/rest/v1/council_agent_profiles",
                params={
                    "domain": f"eq.{domain.upper()}",
                    "select": "agent_name"
                },
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                domain_agents = resp.json()
                participants = [a["agent_name"] for a in domain_agents]
            else:
                participants = []
    except Exception:
        participants = []

    # Ensure supervisor is included
    if supervisor not in participants:
        participants.insert(0, supervisor)

    # Create modified request with domain context
    domain_title = f"[{domain.upper()}] {req.title}"
    domain_topic = f"Domain: {domain.upper()} (Supervisor: {supervisor})\n{req.topic}"

    # Create meeting
    meeting_data = {
        "title": domain_title,
        "topic": domain_topic,
        "agenda": req.agenda,
        "council_members": participants,
        "convener": supervisor,  # Domain supervisor convenes
        "scribe": "ATHENA",
        "status": "scheduled"
    }

    meeting = await db_insert("council_meetings", meeting_data)
    if not meeting:
        raise HTTPException(status_code=500, detail="Failed to create meeting")

    await publish_event("meeting.created", {
        "meeting_id": meeting["id"],
        "domain": domain.upper(),
        "supervisor": supervisor,
        "topic": req.topic,
        "members": participants
    })

    return {
        "meeting_id": meeting["id"],
        "domain": domain.upper(),
        "supervisor": supervisor,
        "title": domain_title,
        "topic": req.topic,
        "council_members": participants,
        "agenda": req.agenda,
        "status": "scheduled",
        "message": f"Domain council convened. {supervisor} will facilitate. Call /council/{meeting['id']}/start to begin."
    }


@app.post("/council/{meeting_id}/delegate")
async def delegate_to_supervisor(meeting_id: str, req: DelegateRequest):
    """Delegate a task to the domain supervisor for execution"""
    meeting = await get_meeting(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Extract domain from title if present (format: [DOMAIN] Title)
    domain = None
    title = meeting.get("title", "")
    if title.startswith("[") and "]" in title:
        domain = title.split("]")[0][1:]

    if not domain:
        raise HTTPException(status_code=400, detail="Meeting not associated with a domain")

    # Get supervisor
    domain_data = await get_domain(domain)
    supervisor = domain_data["supervisor_agent"]

    # Create action item for supervisor
    action_data = {
        "meeting_id": meeting_id,
        "action": req.task,
        "assigned_to": supervisor,
        "status": "pending"
    }

    action = await db_insert("council_actions", action_data)

    # Record to transcript
    await record_to_transcript(
        meeting_id,
        "ATLAS",
        f"DELEGATED TO {supervisor}: {req.task}",
        message_type="action_item"
    )

    # Notify via Event Bus
    await publish_event("action.delegated", {
        "meeting_id": meeting_id,
        "domain": domain,
        "supervisor": supervisor,
        "task": req.task
    })

    return {
        "status": "delegated",
        "action_id": action["id"] if action else None,
        "domain": domain,
        "supervisor": supervisor,
        "task": req.task
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8300)
