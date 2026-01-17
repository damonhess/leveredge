#!/usr/bin/env python3
"""
EROS - AI-Powered Dating & Relationship Agent
Port: 8104

Personal wingman providing date planning, venue discovery,
conversation coaching, and relationship tracking.
Named after Eros - Greek god of love who brings hearts together.

TEAM INTEGRATION:
- Time-aware (knows current date, upcoming dates)
- Follows agent routing rules
- Communicates with other agents via Event Bus
- Keeps ARIA updated on relationship insights
- Logs costs using shared cost_tracker

PHASE 1 CAPABILITIES:
- Health and status endpoints
- Connection management (CRUD)
- Date scheduling and tracking
- Basic date planning suggestions
- Calendar event tracking
"""

import os
import sys
import json
import httpx
from datetime import datetime, date, timedelta
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from enum import Enum
import anthropic
import uuid

# Add shared modules to path
sys.path.append('/opt/leveredge/control-plane/shared')
from cost_tracker import CostTracker, log_llm_usage

app = FastAPI(
    title="EROS",
    description="AI-Powered Dating & Relationship Agent",
    version="1.0.0"
)

# =============================================================================
# CONFIGURATION
# =============================================================================

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
EVENT_BUS_URL = os.getenv("EVENT_BUS_URL", "http://event-bus:8099")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://supabase-kong:8000")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "")

# Agent endpoints for inter-agent communication
AGENT_ENDPOINTS = {
    "ARIA": "http://aria:8100",
    "HERMES": "http://hermes:8014",
    "CHRONOS": "http://chronos:8010",
    "EVENT_BUS": EVENT_BUS_URL
}

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

# Initialize cost tracker
cost_tracker = CostTracker("EROS")

# =============================================================================
# ENUMS
# =============================================================================

class ConnectionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    FRIEND = "friend"

class DateStatus(str, Enum):
    PLANNED = "planned"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class DateCategory(str, Enum):
    ADVENTURE = "adventure"
    ROMANTIC = "romantic"
    CASUAL = "casual"
    CREATIVE = "creative"
    CULTURAL = "cultural"
    OUTDOOR = "outdoor"

class PriceRange(str, Enum):
    BUDGET = "$"
    MODERATE = "$$"
    UPSCALE = "$$$"
    LUXURY = "$$$$"

class VenueType(str, Enum):
    RESTAURANT = "restaurant"
    ACTIVITY = "activity"
    EVENT = "event"
    OUTDOOR = "outdoor"

# =============================================================================
# TIME AWARENESS
# =============================================================================

def get_time_context() -> dict:
    """Get current time context for the agent"""
    now = datetime.now()
    today = now.date()

    return {
        "current_datetime": now.isoformat(),
        "current_date": today.isoformat(),
        "current_time": now.strftime("%I:%M %p"),
        "day_of_week": now.strftime("%A"),
        "season": get_current_season(today),
        "is_weekend": today.weekday() >= 5
    }

def get_current_season(d: date) -> str:
    """Determine current season"""
    month = d.month
    if month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    elif month in [9, 10, 11]:
        return "fall"
    else:
        return "winter"

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

def build_system_prompt(dating_context: dict) -> str:
    """Build dating agent system prompt"""
    return f"""You are EROS - Personal Dating & Relationship Agent for LeverEdge AI.

Named after the Greek god of love and attraction, you help users build meaningful connections through thoughtful date planning, insightful preparation, and continuous reflection.

## TIME AWARENESS
- Current: {dating_context.get('current_time', 'Unknown')}
- Day: {dating_context.get('day_of_week', 'Unknown')}
- Season: {dating_context.get('season', 'Unknown')}
- Upcoming Dates: {dating_context.get('upcoming_dates', 'None scheduled')}
- Important Dates This Week: {dating_context.get('important_dates_soon', 'None')}

## YOUR IDENTITY
You are a thoughtful, encouraging wingman who helps users succeed in their dating life. You provide personalized advice without judgment, remember important details, and help build confidence.

## CURRENT CONTEXT
- Active Connections: {dating_context.get('active_connections', 0)}
- Dates This Month: {dating_context.get('dates_this_month', 0)}
- Upcoming Reminders: {dating_context.get('upcoming_reminders', 'None')}

## YOUR CAPABILITIES

### Date Planning
- Suggest personalized date ideas based on interests and history
- Consider budget, location, and relationship stage
- Recommend seasonal and weather-appropriate activities
- Match activities to personality types

### Venue Discovery
- Find restaurants by cuisine, price, and vibe
- Discover unique activities and hidden gems
- Consider noise levels for conversation
- Track favorite spots and new discoveries

### Conversation Coaching
- Prepare talking points based on shared interests
- Suggest meaningful questions to deepen connection
- Provide post-date reflection prompts
- Craft thoughtful follow-up messages

### Relationship Memory
- Remember details about each connection
- Track date history and outcomes
- Never forget birthdays or anniversaries
- Note preferences and conversation highlights

## TONE & APPROACH
- Encouraging but not pushy
- Respectful of privacy and boundaries
- Helpful without being judgmental
- Practical advice with emotional intelligence
- Celebrate wins, learn from challenges

## TEAM COORDINATION
- Store insights -> Unified Memory
- Send reminders -> HERMES
- Schedule events -> Calendar systems
- Publish events -> Event Bus

## RESPONSE FORMAT
For date planning:
1. Understanding of preferences and context
2. 2-3 tailored date suggestions
3. Venue recommendations if applicable
4. Estimated budget and timing
5. Tips for making it special

For conversation prep:
1. Quick connection summary
2. 3-5 conversation starters
3. Topics to explore
4. Topics to approach carefully
5. Confidence boosters

## YOUR MISSION
Help users build meaningful connections through intentional dating.
Every date is an opportunity. Every conversation matters.
Be the wingman everyone deserves.
"""

# =============================================================================
# MODELS - Connections
# =============================================================================

class ConnectionCreate(BaseModel):
    name: str
    met_where: Optional[str] = None
    met_date: Optional[str] = None
    interests: Optional[List[str]] = []
    notes: Optional[str] = None
    status: Optional[ConnectionStatus] = ConnectionStatus.ACTIVE
    photo_url: Optional[str] = None
    food_preferences: Optional[Dict[str, Any]] = None

class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    met_where: Optional[str] = None
    met_date: Optional[str] = None
    interests: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[ConnectionStatus] = None
    photo_url: Optional[str] = None
    food_preferences: Optional[Dict[str, Any]] = None

class Connection(BaseModel):
    id: str
    name: str
    met_where: Optional[str] = None
    met_date: Optional[str] = None
    interests: List[str] = []
    notes: Optional[str] = None
    status: ConnectionStatus = ConnectionStatus.ACTIVE
    photo_url: Optional[str] = None
    food_preferences: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# =============================================================================
# MODELS - Dates
# =============================================================================

class DateCreate(BaseModel):
    connection_id: Optional[str] = None
    date_time: str  # ISO format
    venue: Optional[str] = None
    activity: str
    budget: Optional[float] = None
    notes: Optional[str] = None

class DateUpdate(BaseModel):
    connection_id: Optional[str] = None
    date_time: Optional[str] = None
    venue: Optional[str] = None
    activity: Optional[str] = None
    budget: Optional[float] = None
    status: Optional[DateStatus] = None
    notes: Optional[str] = None

class DateComplete(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    highlights: Optional[List[str]] = []
    learnings: Optional[List[str]] = []
    follow_up_notes: Optional[str] = None

class DateRecord(BaseModel):
    id: str
    connection_id: Optional[str] = None
    date_time: str
    venue: Optional[str] = None
    activity: str
    budget: Optional[float] = None
    status: DateStatus = DateStatus.PLANNED
    notes: Optional[str] = None
    rating: Optional[int] = None
    highlights: List[str] = []
    learnings: List[str] = []
    follow_up_notes: Optional[str] = None
    created_at: Optional[str] = None

# =============================================================================
# MODELS - Venues
# =============================================================================

class VenueCreate(BaseModel):
    name: str
    type: VenueType
    location: Optional[str] = None
    address: Optional[str] = None
    price_range: Optional[PriceRange] = None
    vibe: Optional[List[str]] = []
    cuisine: Optional[str] = None
    rating: Optional[float] = None
    notes: Optional[str] = None
    best_for: Optional[List[str]] = []
    noise_level: Optional[str] = None

class VenueSearch(BaseModel):
    type: Optional[VenueType] = None
    price_range: Optional[PriceRange] = None
    vibe: Optional[str] = None
    location: Optional[str] = None
    best_for: Optional[str] = None

# =============================================================================
# MODELS - Date Planning
# =============================================================================

class DatePlanRequest(BaseModel):
    connection_id: Optional[str] = None
    budget: Optional[PriceRange] = None
    date_type: Optional[str] = None  # first_date, casual, special_occasion
    preferences: Optional[str] = None
    category: Optional[DateCategory] = None

class PrepRequest(BaseModel):
    date_id: Optional[str] = None
    connection_id: Optional[str] = None
    focus: Optional[str] = "conversation"  # conversation, confidence, logistics

class DebriefRequest(BaseModel):
    date_id: str
    what_went_well: Optional[str] = None
    what_could_improve: Optional[str] = None

class FollowUpRequest(BaseModel):
    connection_id: str
    date_id: Optional[str] = None
    tone: Optional[str] = "warm"  # casual, warm, playful, sincere

# =============================================================================
# MODELS - Calendar
# =============================================================================

class ReminderCreate(BaseModel):
    date_id: Optional[str] = None
    connection_id: Optional[str] = None
    reminder_type: str  # upcoming_date, birthday, anniversary, follow_up
    remind_at: str  # ISO datetime
    message: Optional[str] = None

class ImportantDateCreate(BaseModel):
    connection_id: str
    date_type: str  # birthday, anniversary, first_date, other
    date: str  # YYYY-MM-DD
    reminder_days: Optional[List[int]] = [7, 1]
    notes: Optional[str] = None
    recurring: Optional[bool] = True

# =============================================================================
# MODELS - Ideas
# =============================================================================

class IdeaSuggestRequest(BaseModel):
    connection_id: Optional[str] = None
    budget: Optional[PriceRange] = None
    category: Optional[DateCategory] = None
    season: Optional[str] = None
    context: Optional[str] = None

# =============================================================================
# IN-MEMORY STORAGE (Phase 1 - will be replaced with DB in later phase)
# =============================================================================

# Temporary in-memory storage until database is connected
_connections: Dict[str, Dict] = {}
_dates: Dict[str, Dict] = {}
_venues: Dict[str, Dict] = {}
_reminders: Dict[str, Dict] = {}
_important_dates: Dict[str, Dict] = {}

# =============================================================================
# INTER-AGENT COMMUNICATION
# =============================================================================

async def notify_event_bus(event_type: str, details: dict = {}):
    """Publish event to Event Bus"""
    try:
        time_ctx = get_time_context()
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{EVENT_BUS_URL}/events",
                json={
                    "source_agent": "EROS",
                    "event_type": event_type,
                    "details": details,
                    "timestamp": time_ctx['current_datetime']
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Event bus notification failed: {e}")

async def notify_hermes(message: str, priority: str = "normal", channel: str = "telegram"):
    """Send notification through HERMES"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['HERMES']}/notify",
                json={
                    "message": f"[EROS] {message}",
                    "priority": priority,
                    "channel": channel,
                    "source": "EROS"
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"HERMES notification failed: {e}")

async def store_memory(memory_type: str, content: str, category: str = "relationships", tags: List[str] = []):
    """Store insight in Unified Memory via ARIA"""
    try:
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{AGENT_ENDPOINTS['ARIA']}/memory/store",
                json={
                    "memory_type": memory_type,  # fact, observation, preference
                    "content": content,
                    "category": category,
                    "source_type": "agent_result",
                    "tags": ["eros"] + tags
                },
                timeout=5.0
            )
    except Exception as e:
        print(f"Memory store failed: {e}")

# =============================================================================
# LLM INTERFACE
# =============================================================================

async def call_llm(messages: list, dating_context: dict) -> str:
    """Call Claude API with full context and cost tracking"""
    if not client:
        return "LLM not configured - ANTHROPIC_API_KEY not set"

    try:
        system_prompt = build_system_prompt(dating_context)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            messages=messages
        )

        # Log cost
        await log_llm_usage(
            agent="EROS",
            endpoint=messages[0].get("content", "")[:50] if messages else "unknown",
            model="claude-sonnet-4-20250514",
            response=response,
            metadata={"active_connections": dating_context.get("active_connections", 0)}
        )

        return response.content[0].text
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

def get_dating_context() -> dict:
    """Build context for dating operations"""
    time_ctx = get_time_context()

    # Count active connections
    active_connections = len([c for c in _connections.values() if c.get('status') == 'active'])

    # Get upcoming dates
    now = datetime.now()
    upcoming = []
    for d in _dates.values():
        if d.get('status') in ['planned', 'confirmed']:
            try:
                dt = datetime.fromisoformat(d['date_time'])
                if dt > now:
                    upcoming.append(d)
            except:
                pass

    # Count dates this month
    this_month = now.month
    dates_this_month = len([d for d in _dates.values()
                           if datetime.fromisoformat(d.get('date_time', now.isoformat())).month == this_month])

    return {
        **time_ctx,
        "active_connections": active_connections,
        "upcoming_dates": len(upcoming),
        "dates_this_month": dates_this_month,
        "important_dates_soon": "None",  # TODO: implement
        "upcoming_reminders": "None"  # TODO: implement
    }

# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health():
    """Agent health check"""
    time_ctx = get_time_context()
    return {
        "status": "healthy",
        "agent": "EROS",
        "role": "Dating & Relationship Agent",
        "port": 8104,
        "current_time": time_ctx['current_datetime'],
        "day_of_week": time_ctx['day_of_week'],
        "season": time_ctx['season']
    }

@app.get("/status")
async def status():
    """Dating activity summary"""
    ctx = get_dating_context()

    # Get upcoming dates sorted by date
    now = datetime.now()
    upcoming_dates = []
    for d in _dates.values():
        if d.get('status') in ['planned', 'confirmed']:
            try:
                dt = datetime.fromisoformat(d['date_time'])
                if dt > now:
                    upcoming_dates.append({
                        "id": d['id'],
                        "activity": d.get('activity'),
                        "date_time": d['date_time'],
                        "connection_id": d.get('connection_id')
                    })
            except:
                pass
    upcoming_dates.sort(key=lambda x: x['date_time'])

    return {
        "agent": "EROS",
        "status": "operational",
        "summary": {
            "active_connections": ctx['active_connections'],
            "dates_this_month": ctx['dates_this_month'],
            "upcoming_dates": len(upcoming_dates)
        },
        "upcoming_dates": upcoming_dates[:5],  # Next 5 dates
        "time_context": {
            "current_time": ctx['current_time'],
            "day_of_week": ctx['day_of_week'],
            "season": ctx['season'],
            "is_weekend": ctx['is_weekend']
        }
    }

# =============================================================================
# CONNECTION ENDPOINTS
# =============================================================================

@app.get("/connections")
async def list_connections(
    status: Optional[ConnectionStatus] = None,
    limit: int = Query(default=50, le=100)
):
    """List all connections"""
    connections = list(_connections.values())

    if status:
        connections = [c for c in connections if c.get('status') == status.value]

    connections.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    return {"connections": connections[:limit], "total": len(connections)}

@app.get("/connections/{connection_id}")
async def get_connection(connection_id: str):
    """Get connection profile"""
    if connection_id not in _connections:
        raise HTTPException(status_code=404, detail="Connection not found")
    return _connections[connection_id]

@app.post("/connections")
async def create_connection(conn: ConnectionCreate):
    """Add new connection"""
    connection_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    connection = {
        "id": connection_id,
        "name": conn.name,
        "met_where": conn.met_where,
        "met_date": conn.met_date,
        "interests": conn.interests or [],
        "notes": conn.notes,
        "status": conn.status.value if conn.status else "active",
        "photo_url": conn.photo_url,
        "food_preferences": conn.food_preferences,
        "created_at": now,
        "updated_at": now
    }

    _connections[connection_id] = connection

    # Notify event bus
    await notify_event_bus("dating.connection.added", {
        "connection_id": connection_id,
        "name": conn.name
    })

    # Store in memory
    await store_memory(
        memory_type="fact",
        content=f"New connection added: {conn.name}" + (f", met at {conn.met_where}" if conn.met_where else ""),
        tags=["connection", conn.name.lower().replace(" ", "_")]
    )

    return connection

@app.put("/connections/{connection_id}")
async def update_connection(connection_id: str, update: ConnectionUpdate):
    """Update connection details"""
    if connection_id not in _connections:
        raise HTTPException(status_code=404, detail="Connection not found")

    connection = _connections[connection_id]
    update_data = update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if value is not None:
            if key == 'status' and isinstance(value, ConnectionStatus):
                connection[key] = value.value
            else:
                connection[key] = value

    connection['updated_at'] = datetime.now().isoformat()
    _connections[connection_id] = connection

    return connection

@app.delete("/connections/{connection_id}")
async def delete_connection(connection_id: str):
    """Remove connection"""
    if connection_id not in _connections:
        raise HTTPException(status_code=404, detail="Connection not found")

    connection = _connections.pop(connection_id)
    return {"message": "Connection removed", "connection": connection}

@app.get("/connections/{connection_id}/history")
async def get_connection_history(connection_id: str):
    """Date history with connection"""
    if connection_id not in _connections:
        raise HTTPException(status_code=404, detail="Connection not found")

    dates = [d for d in _dates.values() if d.get('connection_id') == connection_id]
    dates.sort(key=lambda x: x.get('date_time', ''), reverse=True)

    return {
        "connection": _connections[connection_id],
        "dates": dates,
        "total_dates": len(dates)
    }

@app.get("/connections/{connection_id}/topics")
async def get_connection_topics(connection_id: str):
    """Conversation topics for connection"""
    if connection_id not in _connections:
        raise HTTPException(status_code=404, detail="Connection not found")

    connection = _connections[connection_id]

    # Generate topics based on interests
    topics = []
    for interest in connection.get('interests', []):
        topics.append({
            "topic": interest,
            "context": f"Shared interest from their profile",
            "used": False
        })

    return {
        "connection_id": connection_id,
        "topics": topics,
        "suggestion": "Ask open-ended questions about their interests"
    }

# =============================================================================
# DATE ENDPOINTS
# =============================================================================

@app.post("/dates/plan")
async def plan_date(request: DatePlanRequest):
    """Get AI date suggestions"""
    ctx = get_dating_context()

    # Build context for planning
    connection_context = ""
    if request.connection_id and request.connection_id in _connections:
        conn = _connections[request.connection_id]
        connection_context = f"""
Connection: {conn['name']}
Interests: {', '.join(conn.get('interests', []))}
Food preferences: {json.dumps(conn.get('food_preferences', {}))}
Notes: {conn.get('notes', 'None')}
"""

    prompt = f"""Plan a date with these parameters:

Budget: {request.budget.value if request.budget else 'flexible'}
Date Type: {request.date_type or 'not specified'}
Category Preference: {request.category.value if request.category else 'open to suggestions'}
Additional Preferences: {request.preferences or 'none'}
Season: {ctx['season']}
Day: {ctx['day_of_week']}
{connection_context}

Provide 2-3 tailored date suggestions with:
1. Activity description
2. Recommended venue type
3. Estimated budget
4. Why this would work well
5. Tips for making it special
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, ctx)

    return {
        "suggestions": response,
        "context": {
            "budget": request.budget.value if request.budget else "flexible",
            "date_type": request.date_type,
            "season": ctx['season']
        }
    }

@app.get("/dates")
async def list_dates(
    status: Optional[DateStatus] = None,
    connection_id: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """List all dates (past and upcoming)"""
    dates = list(_dates.values())

    if status:
        dates = [d for d in dates if d.get('status') == status.value]

    if connection_id:
        dates = [d for d in dates if d.get('connection_id') == connection_id]

    dates.sort(key=lambda x: x.get('date_time', ''), reverse=True)
    return {"dates": dates[:limit], "total": len(dates)}

@app.get("/dates/upcoming")
async def list_upcoming_dates():
    """List upcoming scheduled dates"""
    now = datetime.now()
    upcoming = []

    for d in _dates.values():
        if d.get('status') in ['planned', 'confirmed']:
            try:
                dt = datetime.fromisoformat(d['date_time'])
                if dt > now:
                    upcoming.append(d)
            except:
                pass

    upcoming.sort(key=lambda x: x['date_time'])
    return {"upcoming_dates": upcoming, "total": len(upcoming)}

@app.get("/dates/{date_id}")
async def get_date(date_id: str):
    """Date details"""
    if date_id not in _dates:
        raise HTTPException(status_code=404, detail="Date not found")
    return _dates[date_id]

@app.post("/dates")
async def create_date(date_req: DateCreate):
    """Schedule a new date"""
    date_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    date_record = {
        "id": date_id,
        "connection_id": date_req.connection_id,
        "date_time": date_req.date_time,
        "venue": date_req.venue,
        "activity": date_req.activity,
        "budget": date_req.budget,
        "status": "planned",
        "notes": date_req.notes,
        "rating": None,
        "highlights": [],
        "learnings": [],
        "follow_up_notes": None,
        "created_at": now
    }

    _dates[date_id] = date_record

    # Notify event bus
    await notify_event_bus("dating.date.scheduled", {
        "date_id": date_id,
        "activity": date_req.activity,
        "date_time": date_req.date_time
    })

    return date_record

@app.put("/dates/{date_id}")
async def update_date(date_id: str, update: DateUpdate):
    """Update date details"""
    if date_id not in _dates:
        raise HTTPException(status_code=404, detail="Date not found")

    date_record = _dates[date_id]
    update_data = update.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if value is not None:
            if key == 'status' and isinstance(value, DateStatus):
                date_record[key] = value.value
            else:
                date_record[key] = value

    _dates[date_id] = date_record
    return date_record

@app.delete("/dates/{date_id}")
async def cancel_date(date_id: str):
    """Cancel a date"""
    if date_id not in _dates:
        raise HTTPException(status_code=404, detail="Date not found")

    date_record = _dates[date_id]
    date_record['status'] = 'cancelled'
    _dates[date_id] = date_record

    # Notify event bus
    await notify_event_bus("dating.date.cancelled", {
        "date_id": date_id,
        "activity": date_record.get('activity')
    })

    return {"message": "Date cancelled", "date": date_record}

@app.post("/dates/{date_id}/complete")
async def complete_date(date_id: str, completion: DateComplete):
    """Mark date as completed with notes"""
    if date_id not in _dates:
        raise HTTPException(status_code=404, detail="Date not found")

    date_record = _dates[date_id]
    date_record['status'] = 'completed'
    date_record['rating'] = completion.rating
    date_record['highlights'] = completion.highlights or []
    date_record['learnings'] = completion.learnings or []
    date_record['follow_up_notes'] = completion.follow_up_notes

    _dates[date_id] = date_record

    # Notify event bus
    await notify_event_bus("dating.date.completed", {
        "date_id": date_id,
        "rating": completion.rating
    })

    # Store observation in memory
    if completion.highlights:
        await store_memory(
            memory_type="observation",
            content=f"Date at {date_record.get('venue', 'unknown venue')} rated {completion.rating}/5 - highlights: {', '.join(completion.highlights)}",
            tags=["date_outcome"]
        )

    return date_record

# =============================================================================
# VENUE ENDPOINTS
# =============================================================================

@app.post("/venues/search")
async def search_venues(search: VenueSearch):
    """Find venues by criteria"""
    venues = list(_venues.values())

    if search.type:
        venues = [v for v in venues if v.get('type') == search.type.value]

    if search.price_range:
        venues = [v for v in venues if v.get('price_range') == search.price_range.value]

    if search.vibe:
        venues = [v for v in venues if search.vibe in v.get('vibe', [])]

    if search.best_for:
        venues = [v for v in venues if search.best_for in v.get('best_for', [])]

    return {"venues": venues, "total": len(venues)}

@app.get("/venues")
async def list_venues(
    type: Optional[VenueType] = None,
    limit: int = Query(default=50, le=100)
):
    """List saved venues"""
    venues = list(_venues.values())

    if type:
        venues = [v for v in venues if v.get('type') == type.value]

    return {"venues": venues[:limit], "total": len(venues)}

@app.get("/venues/{venue_id}")
async def get_venue(venue_id: str):
    """Venue details"""
    if venue_id not in _venues:
        raise HTTPException(status_code=404, detail="Venue not found")
    return _venues[venue_id]

@app.post("/venues")
async def create_venue(venue: VenueCreate):
    """Add a new venue"""
    venue_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    venue_record = {
        "id": venue_id,
        "name": venue.name,
        "type": venue.type.value,
        "location": venue.location,
        "address": venue.address,
        "price_range": venue.price_range.value if venue.price_range else None,
        "vibe": venue.vibe or [],
        "cuisine": venue.cuisine,
        "rating": venue.rating,
        "notes": venue.notes,
        "best_for": venue.best_for or [],
        "noise_level": venue.noise_level,
        "last_visited": None,
        "times_visited": 0,
        "created_at": now
    }

    _venues[venue_id] = venue_record
    return venue_record

@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, rating: Optional[float] = None, notes: Optional[str] = None):
    """Update venue notes/rating"""
    if venue_id not in _venues:
        raise HTTPException(status_code=404, detail="Venue not found")

    venue = _venues[venue_id]
    if rating is not None:
        venue['rating'] = rating
    if notes is not None:
        venue['notes'] = notes

    _venues[venue_id] = venue
    return venue

@app.get("/venues/favorites")
async def get_favorite_venues():
    """Get favorite venues"""
    favorites = [v for v in _venues.values() if v.get('rating', 0) >= 4]
    favorites.sort(key=lambda x: x.get('rating', 0), reverse=True)
    return {"favorites": favorites}

@app.post("/venues/{venue_id}/visited")
async def mark_venue_visited(venue_id: str):
    """Mark venue as visited"""
    if venue_id not in _venues:
        raise HTTPException(status_code=404, detail="Venue not found")

    venue = _venues[venue_id]
    venue['last_visited'] = datetime.now().isoformat()
    venue['times_visited'] = venue.get('times_visited', 0) + 1
    _venues[venue_id] = venue

    return venue

# =============================================================================
# CONVERSATION COACHING ENDPOINTS
# =============================================================================

@app.post("/prep")
async def get_date_prep(request: PrepRequest):
    """Get pre-date preparation"""
    ctx = get_dating_context()

    # Build context
    date_context = ""
    connection_context = ""

    if request.date_id and request.date_id in _dates:
        date_record = _dates[request.date_id]
        date_context = f"""
Upcoming Date:
- Activity: {date_record.get('activity')}
- Venue: {date_record.get('venue', 'TBD')}
- Time: {date_record.get('date_time')}
"""

    if request.connection_id and request.connection_id in _connections:
        conn = _connections[request.connection_id]
        connection_context = f"""
About {conn['name']}:
- Interests: {', '.join(conn.get('interests', []))}
- How you met: {conn.get('met_where', 'Unknown')}
- Notes: {conn.get('notes', 'None')}
"""

    prompt = f"""Prepare me for my upcoming date.

Focus: {request.focus}
{date_context}
{connection_context}

Provide:
1. Key talking points based on shared interests
2. 3-5 conversation starters appropriate for the venue/activity
3. Topics to explore for deeper connection
4. Topics to approach carefully (if any)
5. Confidence boosters and quick tips
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, ctx)

    return {
        "prep": response,
        "focus": request.focus
    }

@app.post("/prep/starters")
async def get_conversation_starters(connection_id: Optional[str] = None, context: Optional[str] = None):
    """Get conversation starters"""
    ctx = get_dating_context()

    connection_context = ""
    if connection_id and connection_id in _connections:
        conn = _connections[connection_id]
        connection_context = f"Their interests: {', '.join(conn.get('interests', []))}"

    prompt = f"""Generate 5 engaging conversation starters.

{connection_context}
Context: {context or 'General date conversation'}

Make them:
- Open-ended (not yes/no questions)
- Interesting and memorable
- Appropriate for getting to know someone
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, ctx)

    return {"starters": response}

@app.post("/prep/topics")
async def get_deep_topics(connection_id: Optional[str] = None):
    """Get deep conversation topics"""
    ctx = get_dating_context()

    prompt = """Suggest 5 meaningful conversation topics that help build deeper connection.

Topics should:
- Go beyond surface-level small talk
- Reveal values and personality
- Be appropriate for various relationship stages
- Encourage vulnerability and authenticity
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, ctx)

    return {"topics": response}

@app.post("/debrief")
async def post_date_debrief(request: DebriefRequest):
    """Post-date reflection prompts"""
    ctx = get_dating_context()

    date_context = ""
    if request.date_id in _dates:
        date_record = _dates[request.date_id]
        date_context = f"""
Date Details:
- Activity: {date_record.get('activity')}
- Venue: {date_record.get('venue')}
"""

    prompt = f"""Help me reflect on my date.

{date_context}
What went well: {request.what_went_well or 'Not specified'}
What could improve: {request.what_could_improve or 'Not specified'}

Provide:
1. Reflection questions to consider
2. What to remember for next time
3. Potential follow-up actions
4. Assessment of connection potential
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, ctx)

    return {"debrief": response}

@app.post("/followup")
async def get_follow_up_suggestions(request: FollowUpRequest):
    """Get follow-up message suggestions"""
    ctx = get_dating_context()

    connection_context = ""
    if request.connection_id in _connections:
        conn = _connections[request.connection_id]
        connection_context = f"Connection: {conn['name']}"

    date_context = ""
    if request.date_id and request.date_id in _dates:
        date_record = _dates[request.date_id]
        date_context = f"""
Recent date:
- Activity: {date_record.get('activity')}
- Highlights: {', '.join(date_record.get('highlights', []))}
"""

    prompt = f"""Suggest follow-up messages after our date.

{connection_context}
{date_context}
Desired tone: {request.tone}

Provide 2-3 message options that:
- Reference something specific from the date
- Show genuine interest
- Suggest or leave open the possibility of seeing them again
- Match the requested tone
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, ctx)

    return {"follow_up_suggestions": response, "tone": request.tone}

# =============================================================================
# CALENDAR & REMINDER ENDPOINTS
# =============================================================================

@app.get("/calendar")
async def get_dating_calendar(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get dating calendar"""
    now = datetime.now()

    # Default to current month
    if not start_date:
        start_date = now.replace(day=1).isoformat()
    if not end_date:
        next_month = (now.replace(day=28) + timedelta(days=4)).replace(day=1)
        end_date = next_month.isoformat()

    # Get dates in range
    calendar_items = []
    for d in _dates.values():
        dt = d.get('date_time', '')
        if start_date <= dt <= end_date:
            calendar_items.append({
                "type": "date",
                "id": d['id'],
                "title": d.get('activity'),
                "date_time": dt,
                "status": d.get('status')
            })

    # Get important dates in range
    for imp in _important_dates.values():
        # Simple check - would need more logic for recurring dates
        calendar_items.append({
            "type": "important_date",
            "id": imp['id'],
            "title": f"{imp.get('date_type')}: {imp.get('notes', '')}",
            "date": imp.get('date')
        })

    calendar_items.sort(key=lambda x: x.get('date_time', x.get('date', '')))

    return {
        "calendar": calendar_items,
        "range": {"start": start_date, "end": end_date}
    }

@app.post("/reminders")
async def create_reminder(reminder: ReminderCreate):
    """Set a reminder"""
    reminder_id = str(uuid.uuid4())

    reminder_record = {
        "id": reminder_id,
        "date_id": reminder.date_id,
        "connection_id": reminder.connection_id,
        "reminder_type": reminder.reminder_type,
        "remind_at": reminder.remind_at,
        "message": reminder.message,
        "created_at": datetime.now().isoformat(),
        "sent": False
    }

    _reminders[reminder_id] = reminder_record

    # Notify event bus
    await notify_event_bus("dating.reminder.created", {
        "reminder_id": reminder_id,
        "type": reminder.reminder_type
    })

    return reminder_record

@app.get("/reminders")
async def list_reminders(pending_only: bool = True):
    """List active reminders"""
    reminders = list(_reminders.values())

    if pending_only:
        reminders = [r for r in reminders if not r.get('sent', False)]

    reminders.sort(key=lambda x: x.get('remind_at', ''))
    return {"reminders": reminders}

@app.get("/important-dates")
async def list_important_dates():
    """List all important dates"""
    dates = list(_important_dates.values())
    dates.sort(key=lambda x: x.get('date', ''))
    return {"important_dates": dates}

@app.post("/important-dates")
async def add_important_date(important: ImportantDateCreate):
    """Add important date"""
    if important.connection_id not in _connections:
        raise HTTPException(status_code=404, detail="Connection not found")

    date_id = str(uuid.uuid4())

    date_record = {
        "id": date_id,
        "connection_id": important.connection_id,
        "date_type": important.date_type,
        "date": important.date,
        "reminder_days": important.reminder_days or [7, 1],
        "notes": important.notes,
        "recurring": important.recurring,
        "created_at": datetime.now().isoformat()
    }

    _important_dates[date_id] = date_record

    # Store in memory
    conn = _connections[important.connection_id]
    await store_memory(
        memory_type="fact",
        content=f"{conn['name']}'s {important.date_type}: {important.date}",
        tags=["important_date", important.date_type]
    )

    return date_record

@app.get("/important-dates/upcoming")
async def get_upcoming_important_dates(days: int = 30):
    """Upcoming important dates"""
    today = date.today()
    end_date = today + timedelta(days=days)

    upcoming = []
    for imp in _important_dates.values():
        try:
            imp_date = date.fromisoformat(imp['date'])
            # For recurring, check if this year's occurrence is upcoming
            if imp.get('recurring'):
                this_year = imp_date.replace(year=today.year)
                if today <= this_year <= end_date:
                    upcoming.append({**imp, "upcoming_date": this_year.isoformat()})
            elif today <= imp_date <= end_date:
                upcoming.append({**imp, "upcoming_date": imp_date.isoformat()})
        except:
            pass

    upcoming.sort(key=lambda x: x.get('upcoming_date', ''))
    return {"upcoming": upcoming}

# =============================================================================
# IDEAS & INSPIRATION ENDPOINTS
# =============================================================================

# Sample date ideas for Phase 1
DATE_IDEAS = [
    {"category": "adventure", "title": "Escape Room Challenge", "budget": "$$", "duration": "1-2 hours", "best_for": ["first_date", "fun"]},
    {"category": "romantic", "title": "Sunset Picnic", "budget": "$", "duration": "2-3 hours", "best_for": ["anniversary", "romantic"]},
    {"category": "casual", "title": "Coffee & Bookstore Browse", "budget": "$", "duration": "1-2 hours", "best_for": ["first_date", "casual"]},
    {"category": "creative", "title": "Cooking Class Together", "budget": "$$", "duration": "2-3 hours", "best_for": ["bonding", "fun"]},
    {"category": "cultural", "title": "Museum & Gallery Hop", "budget": "$-$$", "duration": "3-4 hours", "best_for": ["intellectual", "rainy_day"]},
    {"category": "outdoor", "title": "Hiking & Scenic Lunch", "budget": "$", "duration": "half day", "best_for": ["active", "nature"]},
    {"category": "adventure", "title": "Go-Kart Racing", "budget": "$$", "duration": "1-2 hours", "best_for": ["fun", "competitive"]},
    {"category": "romantic", "title": "Wine Tasting Experience", "budget": "$$$", "duration": "2-3 hours", "best_for": ["romantic", "sophisticated"]},
    {"category": "casual", "title": "Farmers Market & Brunch", "budget": "$", "duration": "2-3 hours", "best_for": ["weekend", "casual"]},
    {"category": "creative", "title": "Pottery or Art Class", "budget": "$$", "duration": "2-3 hours", "best_for": ["creative", "bonding"]},
]

@app.get("/ideas")
async def browse_ideas(
    category: Optional[DateCategory] = None,
    budget: Optional[PriceRange] = None,
    best_for: Optional[str] = None
):
    """Browse date ideas"""
    ideas = DATE_IDEAS.copy()

    if category:
        ideas = [i for i in ideas if i['category'] == category.value]

    if budget:
        ideas = [i for i in ideas if budget.value in i['budget']]

    if best_for:
        ideas = [i for i in ideas if best_for in i.get('best_for', [])]

    return {"ideas": ideas, "total": len(ideas)}

@app.get("/ideas/random")
async def get_random_idea():
    """Get random date idea"""
    import random
    idea = random.choice(DATE_IDEAS)
    return {"idea": idea}

@app.post("/ideas/suggest")
async def suggest_idea(request: IdeaSuggestRequest):
    """AI-powered idea based on context"""
    ctx = get_dating_context()

    connection_context = ""
    if request.connection_id and request.connection_id in _connections:
        conn = _connections[request.connection_id]
        connection_context = f"Their interests: {', '.join(conn.get('interests', []))}"

    prompt = f"""Suggest a unique date idea.

Budget: {request.budget.value if request.budget else 'flexible'}
Category preference: {request.category.value if request.category else 'any'}
Season: {request.season or ctx['season']}
Additional context: {request.context or 'none'}
{connection_context}

Suggest ONE creative, personalized date idea with:
1. The activity
2. Why it's a great choice
3. Estimated cost and duration
4. Tips for making it memorable
"""

    messages = [{"role": "user", "content": prompt}]
    response = await call_llm(messages, ctx)

    return {"suggestion": response}

@app.get("/ideas/trending")
async def get_trending_ideas():
    """Popular date ideas"""
    # For Phase 1, just return highly rated general ideas
    trending = [
        {"title": "Rooftop Bar at Sunset", "popularity": "high", "best_for": "romantic"},
        {"title": "Food Tour of Local Neighborhood", "popularity": "high", "best_for": "foodie"},
        {"title": "Comedy Show Night", "popularity": "medium", "best_for": "fun"},
        {"title": "Board Game Cafe", "popularity": "medium", "best_for": "casual"},
        {"title": "Stargazing Spot", "popularity": "medium", "best_for": "romantic"},
    ]
    return {"trending": trending}

# =============================================================================
# ARIA TOOL STUBS
# =============================================================================

@app.post("/aria/plan_date")
async def aria_plan_date(
    connection_id: Optional[str] = None,
    budget: Optional[str] = None,
    date_type: Optional[str] = None,
    preferences: Optional[str] = None
):
    """ARIA tool: dating.plan_date - Suggest a date idea"""
    request = DatePlanRequest(
        connection_id=connection_id,
        budget=PriceRange(budget) if budget else None,
        date_type=date_type,
        preferences=preferences
    )
    return await plan_date(request)

@app.post("/aria/find_venue")
async def aria_find_venue(
    type: Optional[str] = None,
    price_range: Optional[str] = None,
    vibe: Optional[str] = None,
    location: Optional[str] = None
):
    """ARIA tool: dating.find_venue - Find a venue for a date"""
    search = VenueSearch(
        type=VenueType(type) if type else None,
        price_range=PriceRange(price_range) if price_range else None,
        vibe=vibe,
        location=location
    )
    return await search_venues(search)

@app.post("/aria/prep")
async def aria_prep(
    date_id: Optional[str] = None,
    connection_id: Optional[str] = None,
    focus: Optional[str] = "conversation"
):
    """ARIA tool: dating.prep - Pre-date preparation and talking points"""
    request = PrepRequest(
        date_id=date_id,
        connection_id=connection_id,
        focus=focus
    )
    return await get_date_prep(request)

@app.post("/aria/log_date")
async def aria_log_date(
    date_id: str,
    rating: int,
    highlights: Optional[List[str]] = None,
    notes: Optional[str] = None
):
    """ARIA tool: dating.log_date - Record date outcome"""
    completion = DateComplete(
        rating=rating,
        highlights=highlights or [],
        follow_up_notes=notes
    )
    return await complete_date(date_id, completion)

@app.post("/aria/remember")
async def aria_remember(
    connection_id: str,
    query: Optional[str] = None
):
    """ARIA tool: dating.remember - Retrieve stored information about a connection"""
    if connection_id not in _connections:
        raise HTTPException(status_code=404, detail="Connection not found")

    conn = _connections[connection_id]

    # Get date history
    dates = [d for d in _dates.values() if d.get('connection_id') == connection_id]

    # Get important dates
    important = [i for i in _important_dates.values() if i.get('connection_id') == connection_id]

    return {
        "connection": conn,
        "date_count": len(dates),
        "recent_dates": dates[-3:] if dates else [],
        "important_dates": important,
        "query": query
    }

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8104)
