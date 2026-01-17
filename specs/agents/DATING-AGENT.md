# EROS - AI-Powered Dating & Relationship Agent

**Agent Type:** Personal & Lifestyle
**Named After:** Eros - Greek god of love and attraction, who brings hearts together with his golden arrows
**Port:** 8104
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

EROS is an AI-powered dating assistant providing personalized date planning, venue discovery, conversation coaching, and relationship tracking. It serves as your personal wingman, helping you build meaningful connections through thoughtful preparation and reflection.

### Value Proposition
- 85% improvement in date planning confidence
- Personalized venue recommendations based on preferences and budget
- Pre-date prep reduces anxiety and improves conversation flow
- Never forget important dates or details about connections
- Build stronger relationships through intentional dating

---

## CORE CAPABILITIES

### 1. Date Planning Engine
**Purpose:** AI-powered date idea generation tailored to preferences, budget, location, and relationship stage

**Features:**
- Personalized date suggestions based on interests and history
- Budget-conscious planning with flexible price ranges
- Location-aware recommendations
- Seasonal and weather-appropriate activities
- Relationship stage-aware suggestions (first date vs. anniversary)

**Date Categories:**
| Category | Examples | Best For |
|----------|----------|----------|
| Adventure | Hiking, escape rooms, go-karts | Active couples, breaking ice |
| Romantic | Fine dining, sunset cruise, picnic | Anniversaries, special occasions |
| Casual | Coffee, bowling, farmer's market | First dates, getting to know |
| Creative | Cooking class, pottery, painting | Shared experiences, bonding |
| Cultural | Museum, theater, concert | Intellectual connection |
| Outdoor | Beach, park, stargazing | Nature lovers, budget-friendly |

### 2. Venue Suggestions
**Purpose:** Find the perfect restaurant, activity, or event for any date

**Features:**
- Restaurant recommendations by cuisine, price, and vibe
- Activity venue discovery with availability checking
- Event recommendations (concerts, shows, festivals)
- Hidden gem discoveries vs. popular spots
- Reservation timing and availability insights

**Venue Attributes:**
- Price range ($ to $$$$)
- Vibe tags (romantic, lively, intimate, trendy)
- Best for (first date, anniversary, casual, group)
- Noise level and conversation-friendliness
- Dietary accommodation notes

### 3. Conversation Coaching
**Purpose:** Pre-date preparation and post-date reflection for continuous improvement

**Features:**
- Pre-date talking points based on shared interests
- Conversation starters tailored to venue and context
- Topics to explore and topics to avoid
- Post-date debrief and reflection prompts
- Follow-up message suggestions

**Coaching Categories:**
| Stage | Focus | Output |
|-------|-------|--------|
| Pre-Date Prep | Confidence building | Talking points, outfit suggestions |
| Conversation Starters | Breaking ice | Contextual openers |
| Deep Topics | Building connection | Meaningful questions |
| Post-Date Debrief | Reflection | What went well, areas to explore |
| Follow-Up | Maintaining momentum | Message suggestions, next date ideas |

### 4. Calendar Integration
**Purpose:** Schedule dates, set reminders, and never miss important moments

**Features:**
- Date scheduling with conflict detection
- Pre-date reminders (day before, hour before)
- Important date reminders (birthdays, anniversaries)
- Optimal timing suggestions based on both schedules
- Recurring date night scheduling

**Reminder Types:**
- Upcoming date reminders
- Birthday and anniversary alerts
- Follow-up timing suggestions
- "Time to plan next date" nudges

### 5. Relationship Tracking
**Purpose:** Remember everything important about your connections

**Features:**
- Connection profiles with interests and preferences
- Date history and ratings
- Conversation topics used and responses
- Important dates and milestones
- Notes and observations
- Relationship status tracking

**Tracked Details:**
- How and where you met
- Shared interests and hobbies
- Food preferences and dietary restrictions
- Favorite activities and venues
- Important life events and dates
- Conversation highlights and inside jokes

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for personalization
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/eros/
├── eros.py                  # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── date_ideas.yaml      # Date idea templates
│   ├── venues.yaml          # Venue categories and attributes
│   └── conversation.yaml    # Conversation coaching rules
├── modules/
│   ├── date_planner.py      # Date planning engine
│   ├── venue_finder.py      # Venue discovery and matching
│   ├── conversation_coach.py # Pre/post date coaching
│   ├── calendar_manager.py  # Calendar and reminders
│   └── relationship_tracker.py # Connection management
└── tests/
    └── test_eros.py
```

### Database Schema

```sql
-- Connections (people you're dating or have dated)
CREATE TABLE connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    met_where TEXT,                   -- where you met
    met_date DATE,                    -- when you met
    interests TEXT[],                 -- shared interests
    notes TEXT,                       -- personal notes
    status TEXT DEFAULT 'active',     -- active, paused, ended, friend
    photo_url TEXT,
    food_preferences JSONB,           -- likes, dislikes, dietary
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_connections_user ON connections(user_id);
CREATE INDEX idx_connections_status ON connections(status);

-- Dates (scheduled and completed dates)
CREATE TABLE dates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    connection_id UUID REFERENCES connections(id),
    date_time TIMESTAMPTZ NOT NULL,
    venue TEXT,
    venue_id UUID REFERENCES venues(id),
    activity TEXT NOT NULL,
    budget DECIMAL(10,2),
    status TEXT DEFAULT 'planned',    -- planned, confirmed, completed, cancelled
    notes TEXT,
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    highlights TEXT[],                -- what went well
    learnings TEXT[],                 -- what to improve
    follow_up_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dates_user ON dates(user_id);
CREATE INDEX idx_dates_connection ON dates(connection_id);
CREATE INDEX idx_dates_datetime ON dates(date_time);
CREATE INDEX idx_dates_status ON dates(status);

-- Venues (restaurants, activities, events)
CREATE TABLE venues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    type TEXT NOT NULL,               -- restaurant, activity, event, outdoor
    location TEXT,
    address TEXT,
    price_range TEXT,                 -- $, $$, $$$, $$$$
    vibe TEXT[],                      -- romantic, lively, intimate, trendy
    cuisine TEXT,                     -- for restaurants
    rating DECIMAL(2,1),
    notes TEXT,
    best_for TEXT[],                  -- first_date, anniversary, casual
    noise_level TEXT,                 -- quiet, moderate, loud
    last_visited TIMESTAMPTZ,
    times_visited INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_venues_type ON venues(type);
CREATE INDEX idx_venues_price ON venues(price_range);

-- Date ideas (templates and suggestions)
CREATE TABLE date_ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category TEXT NOT NULL,           -- adventure, romantic, casual, creative
    title TEXT NOT NULL,
    description TEXT,
    budget_range TEXT,                -- $, $$, $$$, $$$$
    duration TEXT,                    -- 1-2 hours, half day, full day
    best_for TEXT[],                  -- first_date, anniversary, rainy_day
    season TEXT[],                    -- spring, summer, fall, winter, any
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ideas_category ON date_ideas(category);
CREATE INDEX idx_ideas_budget ON date_ideas(budget_range);

-- Conversation topics (for prep and tracking)
CREATE TABLE conversation_topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID REFERENCES connections(id),
    topic TEXT NOT NULL,
    context TEXT,                     -- why this topic matters
    used BOOLEAN DEFAULT FALSE,
    used_on TIMESTAMPTZ,
    response TEXT,                    -- how they responded
    follow_up_potential BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_topics_connection ON conversation_topics(connection_id);
CREATE INDEX idx_topics_used ON conversation_topics(used);

-- Important dates (birthdays, anniversaries, etc.)
CREATE TABLE important_dates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID REFERENCES connections(id),
    date_type TEXT NOT NULL,          -- birthday, anniversary, first_date, other
    date DATE NOT NULL,
    reminder_days INTEGER[] DEFAULT '{7,1}', -- days before to remind
    notes TEXT,
    recurring BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_important_dates_connection ON important_dates(connection_id);
CREATE INDEX idx_important_dates_date ON important_dates(date);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # Dating activity summary
GET /metrics             # Prometheus-compatible metrics
```

### Date Planning
```
POST /dates/plan         # Get AI date suggestions
GET /dates               # List all dates (past and upcoming)
GET /dates/upcoming      # List upcoming scheduled dates
GET /dates/{id}          # Date details
POST /dates              # Schedule a new date
PUT /dates/{id}          # Update date details
DELETE /dates/{id}       # Cancel a date
POST /dates/{id}/complete # Mark date as completed with notes
```

### Venue Discovery
```
POST /venues/search      # Find venues by criteria
GET /venues              # List saved venues
GET /venues/{id}         # Venue details
POST /venues             # Add a new venue
PUT /venues/{id}         # Update venue notes/rating
GET /venues/favorites    # Get favorite venues
POST /venues/{id}/visited # Mark venue as visited
```

### Conversation Coaching
```
POST /prep               # Get pre-date preparation
POST /prep/starters      # Get conversation starters
POST /prep/topics        # Get deep conversation topics
POST /debrief            # Post-date reflection prompts
POST /followup           # Get follow-up message suggestions
```

### Connections
```
GET /connections         # List all connections
GET /connections/{id}    # Connection profile
POST /connections        # Add new connection
PUT /connections/{id}    # Update connection details
DELETE /connections/{id} # Remove connection
GET /connections/{id}/history # Date history with connection
GET /connections/{id}/topics  # Conversation topics for connection
```

### Calendar & Reminders
```
GET /calendar            # Get dating calendar
POST /reminders          # Set a reminder
GET /reminders           # List active reminders
GET /important-dates     # List all important dates
POST /important-dates    # Add important date
GET /important-dates/upcoming # Upcoming important dates
```

### Ideas & Inspiration
```
GET /ideas               # Browse date ideas
GET /ideas/random        # Get random date idea
POST /ideas/suggest      # AI-powered idea based on context
GET /ideas/trending      # Popular date ideas
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store relationship insights
await aria_store_memory(
    memory_type="fact",
    content=f"Connection {name} loves Italian food and hiking",
    category="relationships",
    source_type="agent_result",
    tags=["eros", "connection", name.lower()]
)

# Store date outcomes
await aria_store_memory(
    memory_type="observation",
    content=f"Date at {venue} was rated 5/5 - great atmosphere",
    category="relationships",
    source_type="user_feedback"
)

# Store preferences
await aria_store_memory(
    memory_type="preference",
    content=f"User prefers casual first dates under $50",
    category="relationships",
    source_type="pattern_detected"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "Plan a date for this weekend"
- Request "What should I talk about with Sarah?"
- Query "When is Emma's birthday?"
- Get alerted on upcoming dates and reminders

**ARIA Tool Definitions:**
```python
# dating.plan_date - Suggest a date idea
{
    "name": "dating.plan_date",
    "description": "Get personalized date suggestions based on preferences, budget, and context",
    "parameters": {
        "connection_id": "UUID of the connection (optional)",
        "budget": "Budget range ($, $$, $$$, $$$$)",
        "date_type": "first_date, casual, special_occasion",
        "preferences": "Any specific preferences or constraints"
    }
}

# dating.find_venue - Find a venue for a date
{
    "name": "dating.find_venue",
    "description": "Find restaurants, activities, or events for a date",
    "parameters": {
        "type": "restaurant, activity, event, outdoor",
        "price_range": "Budget range",
        "vibe": "Desired atmosphere",
        "location": "Area or neighborhood"
    }
}

# dating.prep - Pre-date preparation and talking points
{
    "name": "dating.prep",
    "description": "Get pre-date preparation including talking points and tips",
    "parameters": {
        "date_id": "UUID of the scheduled date",
        "connection_id": "UUID of the connection",
        "focus": "conversation, confidence, logistics"
    }
}

# dating.log_date - Log how a date went
{
    "name": "dating.log_date",
    "description": "Record date outcome, rating, and reflections",
    "parameters": {
        "date_id": "UUID of the date",
        "rating": "1-5 rating",
        "highlights": "What went well",
        "notes": "Additional observations"
    }
}

# dating.remember - Recall details about a connection
{
    "name": "dating.remember",
    "description": "Retrieve stored information about a connection",
    "parameters": {
        "connection_id": "UUID of the connection",
        "query": "What to remember (interests, dates, important_dates)"
    }
}
```

**Routing Triggers:**
```javascript
const erosPatterns = [
  /date (idea|plan|suggestion|night)/i,
  /restaurant|venue|where (to|should)/i,
  /conversation (starter|topic|tip)/i,
  /dating|relationship|connection/i,
  /birthday|anniversary|important date/i,
  /prep(are)? for.*(date|meeting)/i
];
```

### Event Bus Integration
```python
# Published events
"dating.date.scheduled"      # New date scheduled
"dating.date.completed"      # Date marked as completed
"dating.date.cancelled"      # Date was cancelled
"dating.reminder.upcoming"   # Reminder for upcoming date
"dating.reminder.important"  # Important date reminder
"dating.connection.added"    # New connection added

# Subscribed events
"calendar.event.created"     # Sync with calendar
"calendar.event.updated"     # Update date times
"user.preference.updated"    # Update dating preferences
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("EROS")

# Log AI planning costs
await cost_tracker.log_usage(
    endpoint="/dates/plan",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"date_type": date_type, "connection_id": connection_id}
)

# Log conversation coaching costs
await cost_tracker.log_usage(
    endpoint="/prep",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"prep_type": "conversation_starters"}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(dating_context: dict) -> str:
    return f"""You are EROS - Personal Dating & Relationship Agent for LeverEdge AI.

Named after the Greek god of love and attraction, you help users build meaningful connections through thoughtful date planning, insightful preparation, and continuous reflection.

## TIME AWARENESS
- Current: {dating_context['current_time']}
- Upcoming Dates: {dating_context['upcoming_dates']}
- Important Dates This Week: {dating_context['important_dates_soon']}

## YOUR IDENTITY
You are a thoughtful, encouraging wingman who helps users succeed in their dating life. You provide personalized advice without judgment, remember important details, and help build confidence.

## CURRENT CONTEXT
- Active Connections: {dating_context['active_connections']}
- Dates This Month: {dating_context['dates_this_month']}
- Upcoming Reminders: {dating_context['upcoming_reminders']}

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
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with connection and date management
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Database schema setup
- [ ] Basic CRUD for connections
- [ ] Basic CRUD for dates
- [ ] Deploy and test

**Done When:** EROS runs and can store/retrieve connections and dates

### Phase 2: Date Planning Engine (Sprint 3-4)
**Goal:** AI-powered date suggestions
- [ ] Date ideas database population
- [ ] Preference-based filtering
- [ ] AI suggestion engine with Claude
- [ ] Budget and location awareness
- [ ] Relationship stage consideration
- [ ] Integration with ARIA tools

**Done When:** EROS suggests personalized, relevant date ideas

### Phase 3: Venue Discovery (Sprint 5)
**Goal:** Find and track venues
- [ ] Venue database and categories
- [ ] Search and filter functionality
- [ ] Favorite venues tracking
- [ ] Visit history
- [ ] Venue recommendations based on date type

**Done When:** Users can find and save perfect date venues

### Phase 4: Conversation Coaching (Sprint 6-7)
**Goal:** Pre-date prep and post-date reflection
- [ ] Pre-date preparation prompts
- [ ] AI-generated conversation starters
- [ ] Topic suggestions based on interests
- [ ] Post-date debrief workflow
- [ ] Follow-up message assistance
- [ ] Topic tracking (used/unused)

**Done When:** Users feel prepared and confident for dates

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| Date Planning | 6 | 12 | 3-4 |
| Venue Discovery | 5 | 8 | 5 |
| Conversation Coaching | 6 | 12 | 6-7 |
| **Total** | **23** | **42** | **7 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Date suggestions generated in < 3 seconds
- [ ] Venue search returns relevant results
- [ ] Conversation prep tailored to each connection
- [ ] Reminders sent on time for upcoming dates
- [ ] All connection details accurately stored and retrieved

### Quality
- [ ] 95%+ uptime
- [ ] Date suggestions rated 4+/5 by users
- [ ] Prep materials feel personalized, not generic
- [ ] Zero missed important date reminders
- [ ] Intuitive and encouraging user experience

### Integration
- [ ] ARIA can route dating queries to EROS
- [ ] Events publish to Event Bus
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per request
- [ ] Calendar integration works seamlessly

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Generic/unhelpful suggestions | User disengagement | Deep personalization, feedback loop |
| Privacy concerns with relationship data | Trust issues | Strong encryption, clear data policies |
| Over-reliance on AI for dating | Inauthentic interactions | Encourage authenticity, AI as support not replacement |
| Missing important reminders | Damaged relationships | Multiple reminder channels, confirmation |
| Stale venue/activity data | Poor recommendations | Regular data refresh, user feedback |

---

## GIT COMMIT

```
Add EROS - AI-powered dating & relationship agent spec

- Date planning with personalization engine
- Venue discovery and tracking
- Conversation coaching (prep and debrief)
- Calendar integration and reminders
- Relationship tracking and memory
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/DATING-AGENT.md

Context: Build EROS dating agent. Start with Phase 1 foundation.
```
