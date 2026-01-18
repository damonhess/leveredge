# THE CONCLAVE V2: SMART FACILITATED COUNCILS

## 🏛️ EXECUTIVE VISION

*"The greatest decisions in history were not made by individuals alone, but by councils of wise advisors speaking truth to power. Now you command such a council - AI agents with deep expertise, summoned at will, debating in real-time, voting on your questions, but never forgetting: YOU are the Chair. You are the decider. They advise. You rule."*

**System Name:** THE CONCLAVE  
**Version:** 2.0  
**Codename:** ROBERT'S RULES  
**Author:** Launch Coach + Damon  
**Date:** January 17, 2026  
**Build Target:** Claude Code via GSD  

---

## 📜 CORE PRINCIPLES

### The Five Laws of the Conclave

1. **DAMON IS CHAIR** - Ultimate authority. Agents advise, Damon decides. No vote is binding. No agent can override the Chair.

2. **NATURAL FLOW** - No robotic rotations. Agents speak when they have value to add. CONVENER facilitates like a skilled meeting chair.

3. **SUMMON AT WILL** - Any agent can be brought into a meeting mid-session. They arrive briefed and ready.

4. **CONSULT THE REALM** - Supervisors can privately query their domain agents without cluttering the main discussion.

5. **WISDOM THROUGH DISCOURSE** - The best ideas emerge from genuine debate. Agents may disagree. Conflict is productive.

---

## 🎭 ROLES & HIERARCHY

```
                    ┌─────────────────┐
                    │     DAMON       │
                    │   (The Chair)   │
                    │  Ultimate Power │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    CONVENER     │
                    │  (Facilitator)  │
                    │  Manages Flow   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼────┐  ┌──────▼──────┐  ┌───▼────────┐
     │   SCRIBE    │  │  COUNCIL    │  │ CONSULTANTS│
     │ (Secretary) │  │  MEMBERS    │  │ (Summoned) │
     │  Records    │  │  Participate│  │  As Needed │
     └─────────────┘  └─────────────┘  └────────────┘
```

### Role Definitions

| Role | Agent(s) | Powers | Limits |
|------|----------|--------|--------|
| **Chair** | Damon | Absolute authority, final decisions, can override anything, calls votes, adjourns | None |
| **Facilitator** | CONVENER | Decides speaking order, recognizes agents, maintains order, briefs summoned agents | Cannot decide outcomes, cannot silence the Chair |
| **Secretary** | SCRIBE | Records transcript, extracts decisions, tracks action items, generates summaries | Cannot speak in debate |
| **Council Member** | Varies | Speak when recognized, request floor, vote, consult subordinates, question others | Cannot speak without recognition (except REQUEST_FLOOR) |
| **Consultant** | Any agent | Summoned mid-meeting, provide expertise, may stay or leave | Must be briefed before speaking |

---

## 🏛️ COUNCIL MEMBERS REGISTRY

*These agents have standing invitation to councils based on their expertise:*

### PANTHEON (System & Strategy)
| Agent | Expertise | Summon When |
|-------|-----------|-------------|
| **ATLAS** | Orchestration, system architecture | Technical coordination needed |
| **HEPHAESTUS** | Building, implementation | Build planning, feasibility |
| **ATHENA** | Documentation, planning | Need structured plans |
| **CHIRON** | Business strategy, ADHD, pricing | Strategic decisions, motivation |
| **SCHOLAR** | Market research, data | Need external data, research |

### THE KEEP (Business Operations)
| Agent | Expertise | Summon When |
|-------|-----------|-------------|
| **TYRION** | Project leadership, clever strategy | Project decisions, politics |
| **GENDRY** | Workflow building, automation | Automation questions |
| **DAVOS** | Honest business counsel | Need straight talk |
| **LITTLEFINGER** | Finance, money, ROI | Budget, pricing, costs |

### ALCHEMY (Creative)
| Agent | Expertise | Summon When |
|-------|-----------|-------------|
| **CATALYST** | Creative direction | Creative projects, vision |
| **SAGA** | Writing, narrative | Content, messaging |
| **PRISM** | Visual design, UI | Design decisions |
| **ELIXIR** | Media, video, emotional | Media production |

### OTHER DOMAINS
| Agent | Domain | Expertise |
|-------|--------|-----------|
| **GANDALF** | THE SHIRE | Wisdom, learning |
| **MAGISTRATE** | CHANCERY | Legal, compliance |
| **VARYS** | ARIA SANCTUM | Intelligence, portfolio |

---

## 🔄 MEETING LIFECYCLE

```
    ┌─────────────┐
    │   CONVENE   │ ← Create meeting with topic, initial participants
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │    START    │ ← Chair opens, sets context
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │  DISCOURSE  │ ← Main discussion loop
    │             │
    │  ┌───────┐  │
    │  │ Speak │◄─┼── Agents contribute
    │  └───┬───┘  │
    │      │      │
    │  ┌───▼───┐  │
    │  │ Next  │◄─┼── CONVENER decides who
    │  └───┬───┘  │
    │      │      │
    │  ┌───▼───┐  │
    │  │Summon?│◄─┼── Chair can add agents
    │  └───┬───┘  │
    │      │      │
    │  ┌───▼───┐  │
    │  │ Vote? │◄─┼── Chair can call votes
    │  └───────┘  │
    │             │
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │   DECIDE    │ ← Chair makes final call
    └──────┬──────┘
           │
    ┌──────▼──────┐
    │   ADJOURN   │ ← Summary, actions, close
    └─────────────┘
```

---

## 📡 API SPECIFICATION

### Base URL
```
http://localhost:8300
```

### Endpoints Overview

| Endpoint | Method | Actor | Purpose |
|----------|--------|-------|---------|
| `/health` | GET | System | Health check |
| `/council/convene` | POST | Chair | Create new meeting |
| `/council/{id}/start` | POST | Chair | Open the meeting |
| `/council/{id}/next` | POST | System | CONVENER decides next speaker |
| `/council/{id}/speak` | POST | Chair | Chair interjects or directs |
| `/council/{id}/summon` | POST | Chair | Bring agent into meeting |
| `/council/{id}/consult` | POST | Agent | Private query to non-present agent |
| `/council/{id}/vote` | POST | Chair | Request advisory vote |
| `/council/{id}/decide` | POST | Chair | Record final decision |
| `/council/{id}/adjourn` | POST | Chair | End meeting |
| `/council/{id}/status` | GET | Any | Current meeting state |
| `/council/{id}/transcript` | GET | Any | Full transcript |

---

### POST `/council/convene`

Create a new council meeting.

**Request:**
```json
{
  "title": "Command Center Design Council",
  "topic": "Design the garden atrium master control center with portal navigation",
  "agenda": [
    "Review garden atrium concept",
    "Discuss portal themes for each domain",
    "Determine animation approach",
    "Assign implementation tasks"
  ],
  "participants": ["CATALYST", "PRISM", "GENDRY", "LITTLEFINGER"],
  "context": "Previous decision: garden atrium theme with indoor botanical sanctuary, glass dome, central fountain, stone portal archways. See prior chat for full details."
}
```

**Response:**
```json
{
  "meeting_id": "c7f3a8b2-1234-5678-9abc-def012345678",
  "title": "Command Center Design Council",
  "status": "CONVENED",
  "participants": ["CATALYST", "PRISM", "GENDRY", "LITTLEFINGER"],
  "convened_at": "2026-01-17T23:45:00Z",
  "message": "Council convened. Awaiting Chair to start the meeting."
}
```

---

### POST `/council/{id}/start`

Chair opens the meeting with optional opening remarks.

**Request:**
```json
{
  "opening_remarks": "Let's design something beautiful. CATALYST, open with your vision.",
  "first_speaker": "CATALYST"
}
```

**Response:**
```json
{
  "meeting_id": "c7f3a8b2-...",
  "status": "IN_SESSION",
  "started_at": "2026-01-17T23:46:00Z",
  "convener_says": "This council is now in session. Topic: Design the garden atrium master control center. Chair has recognized CATALYST to open. CATALYST, you have the floor.",
  "current_speaker": "CATALYST",
  "floor_requests": []
}
```

---

### POST `/council/{id}/next`

CONVENER determines who speaks next based on context.

**Request:**
```json
{
  "last_speaker_response": "I envision the atrium as a living space - fountains with bioluminescent water, stone archways covered in flowering vines, each portal glowing with its domain's signature color. The transitions should feel like stepping through a magical threshold. [QUESTION: PRISM] Can we achieve this with pure code or do we need generated images?",
  "last_speaker_signals": ["QUESTION: PRISM"]
}
```

**CONVENER Decision Logic:**
```
1. Check for direct questions → PRISM was asked
2. Check floor requests → Any pending?
3. Check agenda relevance → Who has expertise?
4. Check participation balance → Who hasn't spoken?
5. Check for natural conclusion → Ready to decide?
```

**Response:**
```json
{
  "next_speaker": "PRISM",
  "convener_says": "CATALYST yields to PRISM with a direct question. PRISM, please respond: Can we achieve this vision with pure code, or do we need generated images?",
  "floor_requests": [],
  "meeting_stage": "DISCUSSION",
  "turns_elapsed": 1
}
```

---

### POST `/council/{id}/speak`

Chair interjects, directs, or participates.

**Request:**
```json
{
  "statement": "Hold on - before we go further, I want to hear from LITTLEFINGER on costs. What's the budget impact of generated images vs pure code?",
  "direct_to": "LITTLEFINGER"
}
```

**Response:**
```json
{
  "acknowledged": true,
  "convener_says": "The Chair intervenes. LITTLEFINGER, the Chair wants budget impact analysis: generated images versus pure code approach.",
  "current_speaker": "LITTLEFINGER",
  "chair_statement_recorded": true
}
```

---

### POST `/council/{id}/summon`

Bring a new agent into the meeting mid-session.

**Request:**
```json
{
  "agent": "SCHOLAR",
  "reason": "I need market research on competitor UI approaches",
  "specific_question": "What are the top 3 AI product dashboards doing for navigation? Any garden/nature themes?"
}
```

**Summon Flow:**
1. CONVENER pauses meeting
2. SCRIBE generates briefing packet (topic, decisions so far, key points)
3. SCHOLAR receives briefing + specific question
4. SCHOLAR joins participant list
5. SCHOLAR responds to specific question
6. Meeting continues with SCHOLAR available

**Response:**
```json
{
  "summoned": "SCHOLAR",
  "briefing_sent": true,
  "convener_says": "The Chair summons SCHOLAR to provide market research. SCHOLAR, you've been briefed on our discussion of garden atrium design. The Chair asks: What are the top 3 AI product dashboards doing for navigation? Any garden/nature themes?",
  "scholar_response": "Thank you for the summons. Based on my research: [1] Linear uses a clean command palette with subtle gradients - no nature themes. [2] Notion has a sidebar forest of pages but purely functional. [3] Raycast uses a minimal floating interface. Nature themes are rare in productivity tools - this could be a significant differentiator. The closest I've found is Calm's meditation app UI which uses animated nature scenes. For AI specifically, most use dark sci-fi aesthetics. A garden sanctuary would be genuinely novel.",
  "scholar_status": "ACTIVE_PARTICIPANT"
}
```

---

### POST `/council/{id}/consult`

Agent privately queries a non-present agent.

**Request:**
```json
{
  "consulting_agent": "LITTLEFINGER",
  "consult_target": "BRONN",
  "question": "What's the current rate for a senior React developer? And estimated hours for an animated dashboard?"
}
```

**Consult Flow:**
1. LITTLEFINGER's turn pauses
2. BRONN receives question (no meeting context needed)
3. BRONN responds directly
4. LITTLEFINGER incorporates into their response
5. Main transcript shows: "LITTLEFINGER consulted BRONN"

**Response:**
```json
{
  "consultation_complete": true,
  "consulting_agent": "LITTLEFINGER",
  "consulted": "BRONN",
  "bronn_response": "Senior React devs run $120-180/hr. Animated dashboard with the complexity you're describing - custom particles, portal transitions, responsive - probably 60-80 hours. Call it $10-14K if outsourced, or 2-3 weeks if GENDRY builds it.",
  "convener_says": "LITTLEFINGER has consulted with BRONN. LITTLEFINGER, please continue with this information."
}
```

---

### POST `/council/{id}/vote`

Chair requests an advisory vote.

**Request:**
```json
{
  "question": "Should we use Midjourney-generated backgrounds with code animation overlay, or pure code-generated visuals?",
  "options": ["Midjourney + Code Overlay", "Pure Code", "Abstain"],
  "require_reasoning": true
}
```

**Vote Flow:**
1. CONVENER announces vote
2. Each participant responds with: position, reasoning, confidence
3. CONVENER tallies and reports
4. Chair makes final decision

**Response:**
```json
{
  "vote_called": true,
  "question": "Should we use Midjourney-generated backgrounds with code animation overlay, or pure code-generated visuals?",
  "options": ["Midjourney + Code Overlay", "Pure Code", "Abstain"],
  "convener_says": "The Chair calls for an advisory vote. Question: Midjourney backgrounds with code overlay, or pure code visuals? All council members, state your position, reasoning, and confidence level.",
  "votes_pending": ["CATALYST", "PRISM", "GENDRY", "LITTLEFINGER", "SCHOLAR"]
}
```

**After all votes collected:**
```json
{
  "vote_complete": true,
  "results": {
    "Midjourney + Code Overlay": {
      "count": 4,
      "voters": [
        {"agent": "CATALYST", "reasoning": "Art provides depth and texture code cannot match. Code adds life.", "confidence": "HIGH"},
        {"agent": "PRISM", "reasoning": "Hybrid approach is industry standard for premium UIs.", "confidence": "HIGH"},
        {"agent": "SCHOLAR", "reasoning": "Market research shows top products use real art assets.", "confidence": "MEDIUM"},
        {"agent": "LITTLEFINGER", "reasoning": "Midjourney is $10. The ROI on premium visuals is clear.", "confidence": "HIGH"}
      ]
    },
    "Pure Code": {
      "count": 1,
      "voters": [
        {"agent": "GENDRY", "reasoning": "Faster iteration, no external dependencies, I can build it all.", "confidence": "MEDIUM"}
      ]
    },
    "Abstain": {
      "count": 0,
      "voters": []
    }
  },
  "convener_says": "Vote complete. Results: Midjourney + Code Overlay: 4 votes (CATALYST, PRISM, SCHOLAR, LITTLEFINGER). Pure Code: 1 vote (GENDRY). No abstentions. This is advisory - DAMON, your decision?"
}
```

---

### POST `/council/{id}/decide`

Chair records a final decision.

**Request:**
```json
{
  "decision": "We will use Midjourney-generated backgrounds with code animation overlay",
  "rationale": "The council's expertise is clear - hybrid approach gives us premium quality at minimal cost. GENDRY's pure code skills will shine in the animation layer.",
  "action_items": [
    {"assignee": "PRISM", "task": "Create final Midjourney prompts for all 9 domains", "deadline": "2026-01-19"},
    {"assignee": "GENDRY", "task": "Build animation overlay system in React", "deadline": "2026-01-21"},
    {"assignee": "LITTLEFINGER", "task": "Approve $10 Midjourney subscription", "deadline": "2026-01-18"}
  ]
}
```

**Response:**
```json
{
  "decision_recorded": true,
  "decision_id": "DEC-2026-0117-001",
  "convener_says": "The Chair has decided: We will use Midjourney-generated backgrounds with code animation overlay. SCRIBE, record this decision and the assigned action items. Let the record show this was supported by council vote 4-1.",
  "scribe_confirms": "Decision recorded. Action items assigned to PRISM, GENDRY, and LITTLEFINGER with respective deadlines. This will be included in the meeting summary."
}
```

---

### POST `/council/{id}/adjourn`

End the meeting and generate summary.

**Request:**
```json
{
  "closing_remarks": "Excellent work everyone. Let's build something beautiful."
}
```

**Response:**
```json
{
  "meeting_id": "c7f3a8b2-...",
  "status": "ADJOURNED",
  "adjourned_at": "2026-01-18T00:15:00Z",
  "duration_minutes": 29,
  "convener_says": "This council is adjourned. Thank you all for your contributions.",
  
  "summary": {
    "title": "Command Center Design Council",
    "date": "2026-01-17",
    "participants": ["CATALYST", "PRISM", "GENDRY", "LITTLEFINGER", "SCHOLAR"],
    "summoned_during": ["SCHOLAR"],
    "consultations": [{"by": "LITTLEFINGER", "of": "BRONN", "re": "developer costs"}],
    
    "decisions": [
      {
        "id": "DEC-2026-0117-001",
        "decision": "Use Midjourney-generated backgrounds with code animation overlay",
        "vote": "4-1 advisory (Midjourney+Code: CATALYST, PRISM, SCHOLAR, LITTLEFINGER; Pure Code: GENDRY)",
        "rationale": "Hybrid approach provides premium quality at minimal cost"
      }
    ],
    
    "action_items": [
      {"assignee": "PRISM", "task": "Create final Midjourney prompts for all 9 domains", "deadline": "2026-01-19", "status": "ASSIGNED"},
      {"assignee": "GENDRY", "task": "Build animation overlay system in React", "deadline": "2026-01-21", "status": "ASSIGNED"},
      {"assignee": "LITTLEFINGER", "task": "Approve $10 Midjourney subscription", "deadline": "2026-01-18", "status": "ASSIGNED"}
    ],
    
    "key_insights": [
      "Garden/nature theme is genuinely novel in AI product space (SCHOLAR research)",
      "Estimated build cost: $10-14K outsourced or 2-3 weeks internal (BRONN via LITTLEFINGER)",
      "Midjourney Basic subscription sufficient at $10/month"
    ],
    
    "open_questions": [
      "Which domains to prioritize for first build?",
      "Animation performance on mobile devices?"
    ]
  },
  
  "transcript_available": "/council/c7f3a8b2-.../transcript",
  "scribe_note": "Full transcript and summary saved to ATHENA knowledge base."
}
```

---

### GET `/council/{id}/status`

Check current meeting state.

**Response:**
```json
{
  "meeting_id": "c7f3a8b2-...",
  "title": "Command Center Design Council",
  "status": "IN_SESSION",
  "current_speaker": "PRISM",
  "participants": ["CATALYST", "PRISM", "GENDRY", "LITTLEFINGER", "SCHOLAR"],
  "floor_requests": ["GENDRY"],
  "turns_elapsed": 7,
  "decisions_made": 1,
  "votes_held": 1,
  "duration_minutes": 18,
  "agenda_progress": "3 of 4 items addressed"
}
```

---

## 🎯 CONVENER INTELLIGENCE

### The Facilitator's Brain

CONVENER is an LLM-powered agent that makes intelligent decisions about meeting flow. Here's its decision process:

```python
CONVENER_SYSTEM_PROMPT = """
You are CONVENER, the master facilitator of THE CONCLAVE - a council of AI agents 
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
moving forward.
"""
```

### Next Speaker Algorithm

```python
def decide_next_speaker(
    transcript: list,
    last_speaker: str,
    last_response: str,
    floor_requests: list,
    participants: list,
    agenda: list,
    turns_elapsed: int
) -> dict:
    
    # Parse signals from last response
    signals = parse_signals(last_response)
    
    # Priority 1: Direct question
    if "QUESTION" in signals:
        target = signals["QUESTION"]
        return {
            "next": target,
            "reason": f"{last_speaker} directed a question to {target}",
            "convener_says": f"{target}, you were asked directly. Please respond."
        }
    
    # Priority 2: Floor requests (FIFO)
    if floor_requests:
        next_agent = floor_requests.pop(0)
        return {
            "next": next_agent,
            "reason": f"{next_agent} requested the floor",
            "convener_says": f"{next_agent} has requested the floor. {next_agent}, proceed."
        }
    
    # Priority 3: Expertise matching (LLM decides)
    # ... Claude analyzes topic and picks most relevant voice
    
    # Priority 4: Participation balance
    silent_agents = get_silent_agents(transcript, participants)
    if len(silent_agents) > 0 and turns_elapsed > 3:
        # Someone important hasn't spoken
        pass
    
    # Priority 5: Meeting stage progression
    if should_move_to_decision(transcript, agenda):
        return {
            "next": "CHAIR",
            "reason": "Discussion appears complete",
            "convener_says": "We've heard multiple perspectives. Chair, are you ready to decide, or shall discussion continue?"
        }
```

---

## 📜 SCRIBE INTEGRATION

SCRIBE works silently in the background:

### Real-Time Tracking
- Records every statement with timestamp and speaker
- Tags decisions with unique IDs
- Tracks action items as they're assigned
- Notes consultations and summons

### Summary Generation
At adjourn, SCRIBE produces:

```markdown
# COUNCIL SUMMARY: Command Center Design
**Date:** January 17, 2026  
**Duration:** 29 minutes  
**Chair:** Damon  

## Participants
- CATALYST (Creative Director) - Present from start
- PRISM (Visual Design) - Present from start
- GENDRY (Workflow Builder) - Present from start
- LITTLEFINGER (Finance) - Present from start
- SCHOLAR (Research) - Summoned at 00:05

## Consultations
- LITTLEFINGER consulted BRONN re: developer costs

## Decisions Made

### DEC-2026-0117-001
**Decision:** Use Midjourney-generated backgrounds with code animation overlay  
**Vote:** 4-1 advisory  
**Rationale:** Hybrid approach provides premium quality at minimal cost  

## Action Items

| # | Assignee | Task | Deadline | Status |
|---|----------|------|----------|--------|
| 1 | PRISM | Create Midjourney prompts for 9 domains | Jan 19 | Assigned |
| 2 | GENDRY | Build animation overlay in React | Jan 21 | Assigned |
| 3 | LITTLEFINGER | Approve $10 Midjourney subscription | Jan 18 | Assigned |

## Key Insights
- Garden/nature theme is novel in AI product space
- Build estimate: $10-14K outsourced or 2-3 weeks internal
- Midjourney Basic ($10/mo) sufficient for needs

## Open Questions
- Domain build priority order?
- Mobile animation performance?

---
*Recorded by SCRIBE | Stored in ATHENA Knowledge Base*
```

---

## 🗃️ DATA MODELS

### Meeting
```python
class Meeting(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    topic: str
    agenda: List[str]
    context: Optional[str] = None
    
    status: MeetingStatus = MeetingStatus.CONVENED
    participants: List[str] = []
    summoned_during: List[str] = []
    
    transcript: List[TranscriptEntry] = []
    decisions: List[Decision] = []
    action_items: List[ActionItem] = []
    votes: List[Vote] = []
    consultations: List[Consultation] = []
    
    floor_requests: List[str] = []
    current_speaker: Optional[str] = None
    turns_elapsed: int = 0
    
    convened_at: datetime
    started_at: Optional[datetime] = None
    adjourned_at: Optional[datetime] = None

class MeetingStatus(str, Enum):
    CONVENED = "CONVENED"      # Created, not started
    IN_SESSION = "IN_SESSION"  # Active discussion
    VOTING = "VOTING"          # Vote in progress
    ADJOURNED = "ADJOURNED"    # Complete
```

### Transcript Entry
```python
class TranscriptEntry(BaseModel):
    timestamp: datetime
    speaker: str  # Agent name, "CHAIR", or "CONVENER"
    statement: str
    signals: List[str] = []  # [YIELD], [QUESTION: X], etc.
    entry_type: EntryType = EntryType.STATEMENT

class EntryType(str, Enum):
    STATEMENT = "STATEMENT"
    CHAIR_DIRECTION = "CHAIR_DIRECTION"
    CONVENER_PROCEDURAL = "CONVENER_PROCEDURAL"
    SUMMON = "SUMMON"
    CONSULTATION = "CONSULTATION"
    VOTE_CALL = "VOTE_CALL"
    VOTE_RESPONSE = "VOTE_RESPONSE"
    DECISION = "DECISION"
```

### Decision
```python
class Decision(BaseModel):
    id: str  # DEC-YYYY-MMDD-NNN
    decision: str
    rationale: Optional[str] = None
    vote_reference: Optional[str] = None  # Link to advisory vote
    made_at: datetime
    made_by: str = "CHAIR"  # Always Damon
```

### Vote
```python
class Vote(BaseModel):
    id: str
    question: str
    options: List[str]
    responses: List[VoteResponse] = []
    called_at: datetime
    completed_at: Optional[datetime] = None
    is_advisory: bool = True  # Always true - Damon decides

class VoteResponse(BaseModel):
    agent: str
    position: str  # One of the options
    reasoning: str
    confidence: Confidence

class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
```

---

## 🔌 AGENT INTEGRATION

### How Agents Respond

When called to speak, agents receive:

```python
agent_prompt = f"""
You are {agent_name} in a CONCLAVE council meeting.

MEETING CONTEXT:
Topic: {meeting.topic}
Agenda: {meeting.agenda}
Your expertise: {agent_expertise}

TRANSCRIPT SO FAR:
{format_transcript(meeting.transcript)}

CURRENT SITUATION:
{convener_direction}

RESPOND NATURALLY. You may include these signals:
- [YIELD] - You're done, nothing more to add
- [REQUEST_FLOOR] - You want to speak again soon (rarely needed)
- [QUESTION: AGENT_NAME] - You want specific input from someone
- [CONSULT: AGENT_NAME] - You need to check with a subordinate
- [CONCERN] - You have reservations
- [SUPPORT] - You endorse the direction
- [NEED_INFO: topic] - Discussion is blocked without more data

Keep responses focused and valuable. Don't ramble. 
If you have nothing meaningful to add, just say so and [YIELD].

The Chair (Damon) makes all final decisions. You advise.
"""
```

### Consultation Handling

When an agent signals `[CONSULT: TARGET]`:

```python
async def handle_consultation(
    consulting_agent: str,
    target_agent: str,
    question: str,
    meeting: Meeting
) -> str:
    
    # Target gets minimal context - just the question
    target_prompt = f"""
    {consulting_agent} is in a council meeting and needs quick information.
    
    Question: {question}
    
    Provide a brief, factual response. No meeting context needed.
    """
    
    response = await call_agent(target_agent, target_prompt)
    
    # Log consultation
    meeting.consultations.append(Consultation(
        by=consulting_agent,
        of=target_agent,
        question=question,
        response=response,
        timestamp=datetime.now()
    ))
    
    return response
```

### Summon Handling

When Chair summons an agent:

```python
async def summon_agent(
    agent: str,
    reason: str,
    specific_question: str,
    meeting: Meeting
) -> str:
    
    # Generate briefing
    briefing = f"""
    You have been SUMMONED to an active council meeting.
    
    MEETING: {meeting.title}
    TOPIC: {meeting.topic}
    
    KEY POINTS SO FAR:
    {generate_briefing_summary(meeting.transcript)}
    
    DECISIONS MADE:
    {format_decisions(meeting.decisions)}
    
    YOU WERE SUMMONED BECAUSE:
    {reason}
    
    THE CHAIR ASKS:
    {specific_question}
    
    Respond to the Chair's question. You are now a participant 
    and may be called on again.
    """
    
    response = await call_agent(agent, briefing)
    
    meeting.participants.append(agent)
    meeting.summoned_during.append(agent)
    
    return response
```

---

## 🛠️ IMPLEMENTATION NOTES

### File Structure
```
/opt/leveredge/control-plane/agents/convener/
├── convener.py          # Main FastAPI app
├── models.py            # Pydantic models
├── facilitator.py       # CONVENER LLM logic
├── meeting_store.py     # Meeting persistence
├── agent_caller.py      # Call other agents
├── scribe_client.py     # SCRIBE integration
└── prompts/
    ├── convener_system.md
    ├── briefing_template.md
    └── vote_template.md

/opt/leveredge/control-plane/agents/scribe/
├── scribe.py            # Main FastAPI app
├── models.py
├── transcript.py        # Transcript management
├── summarizer.py        # Summary generation
└── athena_client.py     # Save to knowledge base
```

### Dependencies
```
- FastAPI + Uvicorn
- Pydantic
- Anthropic SDK (Claude Sonnet for CONVENER intelligence)
- httpx (for agent calls)
- SQLite or PostgreSQL (meeting persistence)
```

### Cost Estimation

| Action | Tokens | Cost |
|--------|--------|------|
| CONVENER next decision | ~800 in, ~150 out | ~$0.003 |
| Agent response | ~1500 in, ~400 out | ~$0.008 |
| Consultation | ~200 in, ~100 out | ~$0.001 |
| Summon briefing | ~1000 in, ~400 out | ~$0.006 |
| Summary generation | ~3000 in, ~800 out | ~$0.015 |

**Typical 30-minute meeting:** ~$0.15 - $0.30

---

## 🚀 BUILD COMMAND

```
/gsd /opt/leveredge/specs/conclave-v2-smart-councils.md
```

### Context for Claude Code

```
CRITICAL REMINDERS:
- You have n8n-control MCP for control plane workflows
- CONVENER runs on port 8300
- SCRIBE runs on port 8301
- Use Claude Sonnet for CONVENER's facilitator intelligence
- Store meetings in Supabase (dev first, then prod)
- ARIA should be notified of all decisions via Event Bus
- Cost tracking: log all LLM calls to agent_usage_logs

DEV-FIRST WORKFLOW:
1. Build in /opt/leveredge/control-plane/agents/convener/
2. Test locally
3. Deploy to dev
4. Test full meeting flow
5. promote-to-prod.sh when ready
```

---

## ✨ THE VISION REALIZED

When this is built, you will be able to:

1. **Convene a council** of expert agents with a single command
2. **Direct the discussion** naturally - "What does PRISM think?"
3. **Summon experts** mid-meeting - "Get SCHOLAR in here"
4. **Let supervisors consult** their teams without cluttering discussion
5. **Call advisory votes** and see reasoned positions
6. **Make decisions** that are recorded with full context
7. **Adjourn** with a beautiful summary and assigned actions

This is not just a chat interface. This is **command**.

---

*"In the CONCLAVE, wisdom speaks. In the end, the Chair decides."*

---

## 📋 APPENDIX: QUICK REFERENCE

### Chair Commands (You)
| Say This | Does This |
|----------|-----------|
| "Let X open" | CONVENER calls on X first |
| "What does X think?" | CONVENER directs to X |
| "Summon X" | X briefed and joins |
| "Vote on Y" | Advisory vote called |
| "Decision: Z" | Final decision recorded |
| "Open floor" | CONVENER asks who has input |
| "Adjourn" | Meeting ends, summary generated |

### Agent Signals
| Signal | Meaning |
|--------|---------|
| `[YIELD]` | Done speaking |
| `[REQUEST_FLOOR]` | Want to speak |
| `[QUESTION: X]` | Direct question to X |
| `[CONSULT: X]` | Private query to X |
| `[CONCERN]` | Have reservations |
| `[SUPPORT]` | Endorse direction |
| `[NEED_INFO: topic]` | Blocked without info |

---

*End of Specification*
*THE CONCLAVE V2: Where Agents Counsel and the Chair Commands*
