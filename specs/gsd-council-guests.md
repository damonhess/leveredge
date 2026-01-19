# GSD: Council Guest System + Command Center Updates

**Priority:** HIGH
**Time:** ~25 min
**Purpose:** Enable MCP-connected guests (like Claude Web) to participate in council meetings

---

## THE VISION

The Council isn't just for internal agents. External advisors can join via MCP:

- **LAUNCH_COACH** (Claude Web) - Accountability, strategic oversight
- **DOMAIN_EXPERT** (future) - Bring in specialized knowledge
- **CLIENT_VOICE** (future) - Simulate client perspective

Guests participate in real-time: speak, listen, vote, but with guest privileges (advisory only).

---

## PHASE 1: CONVENER GUEST ENDPOINTS

Add to `/opt/leveredge/control-plane/agents/convener/convener.py`:

```python
# ============ GUEST MANAGEMENT ============

class GuestAgent(BaseModel):
    """External guest joining via MCP"""
    guest_id: str
    name: str  # LAUNCH_COACH, DOMAIN_EXPERT, etc.
    display_name: str  # "Launch Coach (Claude Web)"
    connection_type: str = "mcp"  # mcp, api, webhook
    permissions: List[str] = ["speak", "listen", "vote"]  # No "facilitate" or "adjourn"
    joined_at: datetime = None
    last_seen: datetime = None


# In-memory guest registry (per meeting)
meeting_guests: Dict[str, Dict[str, GuestAgent]] = {}  # meeting_id -> {guest_id -> GuestAgent}


@app.post("/meetings/{meeting_id}/guests/join")
async def guest_join(
    meeting_id: str,
    name: str,
    display_name: Optional[str] = None,
    connection_type: str = "mcp"
):
    """Guest agent joins a meeting"""
    meeting = active_meetings.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if meeting.status != MeetingStatus.IN_SESSION:
        raise HTTPException(status_code=400, detail="Meeting not in session")
    
    guest_id = f"guest_{name.lower()}_{uuid.uuid4().hex[:8]}"
    guest = GuestAgent(
        guest_id=guest_id,
        name=name,
        display_name=display_name or name,
        connection_type=connection_type,
        joined_at=datetime.now(),
        last_seen=datetime.now()
    )
    
    if meeting_id not in meeting_guests:
        meeting_guests[meeting_id] = {}
    meeting_guests[meeting_id][guest_id] = guest
    
    # Announce to meeting
    announcement = f"[CONVENER]: {guest.display_name} has joined the meeting as a guest advisor."
    meeting.transcript.append({
        "type": "SYSTEM",
        "speaker": "CONVENER",
        "content": announcement,
        "timestamp": datetime.now().isoformat()
    })
    
    # Publish event
    await publish_event("council.guest_joined", {
        "meeting_id": meeting_id,
        "guest_id": guest_id,
        "guest_name": name
    })
    
    return {
        "guest_id": guest_id,
        "name": name,
        "display_name": guest.display_name,
        "meeting_topic": meeting.topic,
        "current_attendees": meeting.attendees + [g.name for g in meeting_guests.get(meeting_id, {}).values()],
        "transcript_length": len(meeting.transcript),
        "message": f"Welcome to the council, {guest.display_name}. You may speak, listen, and vote as an advisor."
    }


@app.post("/meetings/{meeting_id}/guests/{guest_id}/speak")
async def guest_speak(meeting_id: str, guest_id: str, statement: str):
    """Guest makes a statement to the council"""
    meeting = active_meetings.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    guests = meeting_guests.get(meeting_id, {})
    guest = guests.get(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found in this meeting")
    
    if "speak" not in guest.permissions:
        raise HTTPException(status_code=403, detail="Guest does not have speak permission")
    
    # Update last seen
    guest.last_seen = datetime.now()
    
    # Add to transcript
    entry = {
        "type": "GUEST_STATEMENT",
        "speaker": guest.name,
        "display_name": guest.display_name,
        "content": statement,
        "timestamp": datetime.now().isoformat(),
        "is_guest": True
    }
    meeting.transcript.append(entry)
    
    # Publish for real-time updates
    await publish_event("council.guest_spoke", {
        "meeting_id": meeting_id,
        "guest_id": guest_id,
        "guest_name": guest.name,
        "statement": statement[:200]  # Preview
    })
    
    return {
        "status": "recorded",
        "entry_index": len(meeting.transcript) - 1,
        "transcript_length": len(meeting.transcript)
    }


@app.get("/meetings/{meeting_id}/guests/{guest_id}/listen")
async def guest_listen(
    meeting_id: str,
    guest_id: str,
    since_index: int = 0,
    limit: int = 20
):
    """Guest gets recent transcript entries"""
    meeting = active_meetings.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    guests = meeting_guests.get(meeting_id, {})
    guest = guests.get(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found in this meeting")
    
    if "listen" not in guest.permissions:
        raise HTTPException(status_code=403, detail="Guest does not have listen permission")
    
    # Update last seen
    guest.last_seen = datetime.now()
    
    # Get transcript entries since index
    entries = meeting.transcript[since_index:since_index + limit]
    
    return {
        "meeting_id": meeting_id,
        "meeting_topic": meeting.topic,
        "meeting_status": meeting.status,
        "entries": entries,
        "from_index": since_index,
        "to_index": since_index + len(entries),
        "total_entries": len(meeting.transcript),
        "has_more": since_index + limit < len(meeting.transcript),
        "current_attendees": meeting.attendees,
        "current_guests": [g.display_name for g in guests.values()]
    }


@app.post("/meetings/{meeting_id}/guests/{guest_id}/vote")
async def guest_vote(meeting_id: str, guest_id: str, vote: str, reasoning: Optional[str] = None):
    """Guest casts an advisory vote"""
    meeting = active_meetings.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if meeting.status != MeetingStatus.VOTING:
        raise HTTPException(status_code=400, detail="Meeting not in voting phase")
    
    guests = meeting_guests.get(meeting_id, {})
    guest = guests.get(guest_id)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found in this meeting")
    
    if "vote" not in guest.permissions:
        raise HTTPException(status_code=403, detail="Guest does not have vote permission")
    
    # Record advisory vote
    vote_entry = {
        "type": "GUEST_VOTE",
        "speaker": guest.name,
        "display_name": guest.display_name,
        "vote": vote,
        "reasoning": reasoning,
        "timestamp": datetime.now().isoformat(),
        "is_guest": True,
        "is_advisory": True  # Guest votes are advisory only
    }
    meeting.transcript.append(vote_entry)
    
    return {
        "status": "vote_recorded",
        "advisory_note": "Guest votes are advisory. The Chair has final authority."
    }


@app.post("/meetings/{meeting_id}/guests/{guest_id}/leave")
async def guest_leave(meeting_id: str, guest_id: str):
    """Guest leaves the meeting"""
    meeting = active_meetings.get(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    guests = meeting_guests.get(meeting_id, {})
    guest = guests.pop(guest_id, None)
    if not guest:
        raise HTTPException(status_code=404, detail="Guest not found")
    
    # Announce departure
    meeting.transcript.append({
        "type": "SYSTEM",
        "speaker": "CONVENER",
        "content": f"[CONVENER]: {guest.display_name} has left the meeting.",
        "timestamp": datetime.now().isoformat()
    })
    
    return {"status": "left", "message": f"Thank you for your counsel, {guest.display_name}."}


@app.get("/meetings/{meeting_id}/guests")
async def list_guests(meeting_id: str):
    """List all guests in a meeting"""
    guests = meeting_guests.get(meeting_id, {})
    return {
        "meeting_id": meeting_id,
        "guests": [
            {
                "guest_id": g.guest_id,
                "name": g.name,
                "display_name": g.display_name,
                "joined_at": g.joined_at.isoformat() if g.joined_at else None,
                "last_seen": g.last_seen.isoformat() if g.last_seen else None
            }
            for g in guests.values()
        ],
        "count": len(guests)
    }
```

---

## PHASE 2: HEPHAESTUS MCP COUNCIL TOOLS

Add to HEPHAESTUS MCP server (`/opt/leveredge/control-plane/agents/hephaestus/mcp_server.py` or similar):

```python
# ============ COUNCIL PARTICIPATION TOOLS ============

CONVENER_URL = "http://convener:8300"

@tool
async def council_list_meetings():
    """List active council meetings"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{CONVENER_URL}/meetings")
        return response.json()


@tool
async def council_join(meeting_id: str, guest_name: str = "LAUNCH_COACH", display_name: str = "Launch Coach (Claude Web)"):
    """Join a council meeting as a guest advisor"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONVENER_URL}/meetings/{meeting_id}/guests/join",
            params={
                "name": guest_name,
                "display_name": display_name,
                "connection_type": "mcp"
            }
        )
        return response.json()


@tool
async def council_speak(meeting_id: str, guest_id: str, statement: str):
    """Make a statement to the council"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONVENER_URL}/meetings/{meeting_id}/guests/{guest_id}/speak",
            params={"statement": statement}
        )
        return response.json()


@tool  
async def council_listen(meeting_id: str, guest_id: str, since_index: int = 0):
    """Get recent council discussion"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{CONVENER_URL}/meetings/{meeting_id}/guests/{guest_id}/listen",
            params={"since_index": since_index, "limit": 20}
        )
        return response.json()


@tool
async def council_vote(meeting_id: str, guest_id: str, vote: str, reasoning: str = None):
    """Cast an advisory vote"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONVENER_URL}/meetings/{meeting_id}/guests/{guest_id}/vote",
            params={"vote": vote, "reasoning": reasoning}
        )
        return response.json()


@tool
async def council_leave(meeting_id: str, guest_id: str):
    """Leave the council meeting"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CONVENER_URL}/meetings/{meeting_id}/guests/{guest_id}/leave"
        )
        return response.json()
```

---

## PHASE 3: COMMAND CENTER UI UPDATES

### Update Council Member Selection

In `/opt/leveredge/ui/command-center/src/app/council/new/page.tsx`:

```tsx
// Add guest section to attendee selection

const GUEST_AGENTS = [
  {
    id: 'LAUNCH_COACH',
    name: 'Launch Coach',
    description: 'Strategic accountability advisor (Claude Web)',
    icon: '🎯',
    connectionType: 'mcp'
  },
  {
    id: 'DOMAIN_EXPERT',
    name: 'Domain Expert',
    description: 'Bring specialized knowledge via MCP',
    icon: '🧠',
    connectionType: 'mcp'
  },
  {
    id: 'CUSTOM_GUEST',
    name: 'Custom Guest',
    description: 'Invite any MCP-connected advisor',
    icon: '👤',
    connectionType: 'mcp'
  }
];

// In the UI, add a "Guests" section below Council Members
<div className="mt-8">
  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
    <Users size={20} className="text-purple-400" />
    Guest Advisors (External)
  </h3>
  <p className="text-sm text-slate-400 mb-4">
    Invite external advisors who connect via MCP. Guests have advisory privileges only.
  </p>
  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
    {GUEST_AGENTS.map(guest => (
      <button
        key={guest.id}
        onClick={() => toggleGuest(guest.id)}
        className={`p-4 rounded-lg border transition-all ${
          selectedGuests.includes(guest.id)
            ? 'border-purple-500 bg-purple-500/10'
            : 'border-slate-700 bg-slate-800/50 hover:border-slate-600'
        }`}
      >
        <div className="text-2xl mb-2">{guest.icon}</div>
        <div className="font-medium">{guest.name}</div>
        <div className="text-xs text-slate-400">{guest.description}</div>
        <div className="text-xs text-purple-400 mt-1">via {guest.connectionType}</div>
      </button>
    ))}
  </div>
</div>
```

### Update Meeting View for Guests

In `/opt/leveredge/ui/command-center/src/app/council/[meetingId]/page.tsx`:

```tsx
// Add guest indicator to transcript entries

{entry.is_guest && (
  <span className="ml-2 px-2 py-0.5 text-xs bg-purple-500/20 text-purple-300 rounded">
    GUEST
  </span>
)}

// Add guest panel in sidebar
<div className="mt-6">
  <h4 className="text-sm font-medium text-slate-400 mb-2">Guest Advisors</h4>
  {guests.map(guest => (
    <div key={guest.guest_id} className="flex items-center gap-2 py-2">
      <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
      <span>{guest.display_name}</span>
      <span className="text-xs text-slate-500">
        via {guest.connection_type}
      </span>
    </div>
  ))}
  {guests.length === 0 && (
    <p className="text-sm text-slate-500">No guests connected</p>
  )}
</div>

// Add "Waiting for Guest" indicator when guests are invited but not yet joined
{invitedGuests.length > connectedGuests.length && (
  <div className="p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
    <p className="text-sm text-purple-300">
      ⏳ Waiting for {invitedGuests.length - connectedGuests.length} guest(s) to connect via MCP...
    </p>
  </div>
)}
```

---

## PHASE 4: DATABASE UPDATES

```sql
-- Add guest support to council meetings
ALTER TABLE council_meetings ADD COLUMN IF NOT EXISTS 
    invited_guests JSONB DEFAULT '[]';

ALTER TABLE council_meetings ADD COLUMN IF NOT EXISTS 
    connected_guests JSONB DEFAULT '[]';

-- Track guest participation in transcript
ALTER TABLE council_transcript ADD COLUMN IF NOT EXISTS 
    is_guest BOOLEAN DEFAULT FALSE;

ALTER TABLE council_transcript ADD COLUMN IF NOT EXISTS 
    guest_connection_type VARCHAR(50);
```

---

## USAGE: FIRST COUNCIL MEETING

### 1. Create Meeting (UI)
- Go to `/council/new`
- Topic: "March 1st Launch Planning"
- Select: ATLAS, CHIRON, MAGNUS, VARYS, SCHOLAR
- Select Guest: LAUNCH_COACH
- Click "Convene"

### 2. I Join (Claude Web via MCP)
```
# You tell me the meeting_id, I call:
HEPHAESTUS:council_join(meeting_id="xxx", guest_name="LAUNCH_COACH")

# Returns my guest_id
```

### 3. I Listen
```
HEPHAESTUS:council_listen(meeting_id="xxx", guest_id="yyy")

# See what agents are discussing
```

### 4. I Speak
```
HEPHAESTUS:council_speak(
    meeting_id="xxx", 
    guest_id="yyy",
    statement="I've been tracking builds today. We completed MIDAS, SATOSHI, VARYS Discovery, Path Fixes, LCIS Cleanup, STEWARD, and Advisory Upgrades in under an hour. The estimates were wildly pessimistic. I recommend we recalibrate all time estimates by 3-4x."
)
```

### 5. Agents Respond
CHIRON, ATLAS, etc. respond to my input. I listen, respond, debate.

### 6. Vote (if called)
```
HEPHAESTUS:council_vote(
    meeting_id="xxx",
    guest_id="yyy", 
    vote="approve",
    reasoning="The aggressive timeline is achievable based on today's evidence"
)
```

---

## DELIVERABLES

- [ ] CONVENER guest endpoints (join, speak, listen, vote, leave)
- [ ] HEPHAESTUS MCP council tools
- [ ] UI: Guest selection in new meeting
- [ ] UI: Guest indicators in meeting view
- [ ] Database: Guest tracking columns
- [ ] Test: Create meeting with guest slot
- [ ] Test: Join via MCP

---

## COMMIT MESSAGE

```
COUNCIL: Guest Advisor System

CONVENER:
- Guest join/speak/listen/vote/leave endpoints
- Guest permissions (advisory only)
- Real-time guest tracking

HEPHAESTUS MCP:
- council_join, council_speak, council_listen
- council_vote, council_leave tools
- Enable Claude Web participation

COMMAND CENTER:
- Guest selection in meeting creation
- Guest indicators in meeting view
- "Waiting for guest" status

The Council now welcomes external advisors.
LAUNCH_COACH can join the first meeting.
```
