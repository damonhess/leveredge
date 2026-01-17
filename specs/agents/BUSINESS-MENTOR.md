# BUSINESS MENTOR - Personalized Business Coach & Accountability Agent

**Agent Type:** Business & Personal Development
**Named After:** Mentor - the wise advisor to Odysseus's son Telemachus in Homer's Odyssey, who guided him during his father's absence
**Port:** 8204
**Status:** PLANNED
**Extends:** CHIRON (Port 8017) - A more personalized, data-driven complement

---

## EXECUTIVE SUMMARY

BUSINESS MENTOR is a personalized AI business coach providing strategic guidance, revenue tracking, daily accountability, ADHD-aware planning, and win celebration. While CHIRON focuses on strategic frameworks and session-based mentoring, BUSINESS MENTOR tracks longitudinal data, maintains persistent accountability state, and provides deeply personalized coaching based on historical patterns.

### Value Proposition
- Persistent revenue tracking (MRR/ARR/milestones) with trend analysis
- ADHD-optimized planning with effectiveness tracking over time
- Accountability system with check-in history and pattern detection
- Win tracking for motivation and portfolio building
- Personalized insights based on YOUR data, not generic advice

### Relationship to CHIRON
| Aspect | CHIRON | BUSINESS MENTOR |
|--------|--------|-----------------|
| Focus | Strategic frameworks, decision-making | Daily execution, accountability, data tracking |
| Sessions | Stateless mentoring sessions | Persistent state across sessions |
| Data | Uses portfolio context | Owns revenue, wins, commitment data |
| Style | Direct challenger | Supportive accountability partner |
| Calls | On-demand strategy | Daily/weekly check-ins |

---

## CORE CAPABILITIES

### 1. Strategic Guidance
**Purpose:** Provide business strategy advice grounded in personal context and history

**Features:**
- Strategic advice based on your actual revenue data
- Pattern recognition from past decisions and outcomes
- Framework recommendations personalized to ADHD patterns
- Integration with CHIRON for complex strategy sessions
- Mentor session logging for continuity

**Guidance Categories:**
| Category | Example Topics | Data Sources |
|----------|---------------|--------------|
| Revenue Strategy | Pricing, upsells, churn prevention | revenue_log, mentor_sessions |
| Growth Planning | Scaling, hiring, automation | commitments, wins |
| Time Management | Focus periods, energy optimization | daily_check_ins, adhd_strategies |
| Decision Support | Go/no-go, prioritization | mentor_sessions, commitments |

### 2. Revenue Tracking
**Purpose:** Track MRR, ARR, revenue milestones with trend analysis

**Features:**
- Log all revenue events (new deals, renewals, churn)
- Calculate MRR/ARR automatically
- Track progress toward $30K MRR goal
- Celebrate revenue milestones automatically
- Forecast future revenue based on trends
- Churn analysis and prevention alerts

**Revenue Metrics:**
- Current MRR/ARR
- MRR Growth Rate
- Revenue by source/type
- Days to $30K goal (based on current trajectory)
- Milestone tracking (first $1K, $5K, $10K, $20K, $30K)

### 3. Accountability System
**Purpose:** Daily/weekly check-ins on commitments with pattern tracking

**Features:**
- Commitment registration with clear deadlines
- Daily nudges for overdue commitments
- Pattern detection (what types of commitments slip?)
- Adjustable commitment styles for ADHD
- Follow-through scoring over time
- Escalation to CHIRON when patterns indicate deeper issues

**Accountability Flow:**
1. Register commitment with deadline
2. Daily status checks (automated)
3. On deadline: outcome recording
4. Pattern analysis over time
5. Strategy adjustment recommendations

### 4. ADHD-Aware Planning
**Purpose:** Break work into ADHD-friendly chunks with effectiveness tracking

**Features:**
- Task chunking with time estimates (15-30 min blocks)
- Energy level matching (hard tasks when fresh)
- Dopamine stacking (quick wins first)
- Strategy effectiveness tracking over time
- Personal productivity pattern discovery
- Bad day protocols (what works when struggling)

**ADHD Strategies Tracked:**
- Body doubling effectiveness
- Time block durations that work
- Break patterns that maintain focus
- Environment factors that help
- Recovery strategies after derailment

### 5. Win Tracking
**Purpose:** Celebrate wins, maintain motivation, build portfolio evidence

**Features:**
- Log wins of all sizes (micro to major)
- Categorize wins for portfolio building
- Impact level assessment
- Celebration triggers (notifications, hype)
- Win streaks and momentum tracking
- Evidence accumulation for imposter syndrome moments

**Win Categories:**
| Category | Examples | Impact Levels |
|----------|----------|---------------|
| Revenue | Closed deal, upsell, renewal | Low ($100) to High ($10K+) |
| Technical | Agent built, feature shipped | Low to High based on complexity |
| Business | Partnership, testimonial, referral | Medium to High |
| Personal | Habit maintained, fear overcome | Low to Medium |
| Learning | Skill acquired, certification | Low to Medium |

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
AI: Claude API for personalized coaching
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/business-mentor/
├── business_mentor.py          # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── milestones.yaml         # Revenue milestone definitions
│   ├── adhd_strategies.yaml    # Default ADHD strategy library
│   └── check_in_templates.yaml # Check-in question templates
├── modules/
│   ├── revenue_tracker.py      # MRR/ARR calculations
│   ├── accountability.py       # Commitment tracking
│   ├── win_manager.py          # Win logging and celebration
│   ├── adhd_planner.py         # ADHD-optimized planning
│   └── mentor_engine.py        # AI coaching logic
└── tests/
    └── test_business_mentor.py
```

### Database Schema

```sql
-- Revenue logging
CREATE TABLE revenue_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    amount DECIMAL(12,2) NOT NULL,
    source TEXT NOT NULL,              -- client name, product, etc.
    type TEXT NOT NULL,                -- new_deal, renewal, upsell, one_time, churn
    recurring BOOLEAN DEFAULT FALSE,    -- is this MRR?
    monthly_value DECIMAL(12,2),       -- normalized monthly value
    contract_length_months INTEGER,
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_revenue_date ON revenue_log(date DESC);
CREATE INDEX idx_revenue_type ON revenue_log(type);
CREATE INDEX idx_revenue_recurring ON revenue_log(recurring);
CREATE INDEX idx_revenue_source ON revenue_log(source);

-- Commitments tracking
CREATE TABLE commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    commitment TEXT NOT NULL,
    context TEXT,                       -- why this matters
    deadline TIMESTAMPTZ NOT NULL,
    status TEXT DEFAULT 'active',       -- active, completed, missed, cancelled
    check_ins JSONB DEFAULT '[]',       -- array of {date, note, status}
    result TEXT,                        -- final outcome description
    result_date TIMESTAMPTZ,
    category TEXT,                      -- revenue, technical, personal, learning
    difficulty TEXT DEFAULT 'medium',   -- easy, medium, hard, stretch
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_commitments_status ON commitments(status);
CREATE INDEX idx_commitments_deadline ON commitments(deadline);
CREATE INDEX idx_commitments_user ON commitments(user_id);
CREATE INDEX idx_commitments_category ON commitments(category);

-- Daily check-ins
CREATE TABLE daily_check_ins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 10),
    focus_rating INTEGER CHECK (focus_rating BETWEEN 1 AND 10),
    mood TEXT,                          -- energized, neutral, tired, stressed, excited
    wins JSONB DEFAULT '[]',            -- array of wins for the day
    blockers JSONB DEFAULT '[]',        -- array of blockers encountered
    plan JSONB DEFAULT '[]',            -- planned tasks for day
    actual JSONB DEFAULT '[]',          -- what actually got done
    notes TEXT,
    adhd_strategies_used JSONB DEFAULT '[]',  -- which strategies helped
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

CREATE INDEX idx_checkins_date ON daily_check_ins(date DESC);
CREATE INDEX idx_checkins_user ON daily_check_ins(user_id);
CREATE INDEX idx_checkins_energy ON daily_check_ins(energy_level);

-- Win tracking
CREATE TABLE wins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    description TEXT NOT NULL,
    category TEXT NOT NULL,             -- revenue, technical, business, personal, learning
    impact_level TEXT DEFAULT 'medium', -- micro, small, medium, large, major
    celebrated BOOLEAN DEFAULT FALSE,
    celebration_type TEXT,              -- notification, hype_session, milestone_alert
    evidence_url TEXT,                  -- link to proof (screenshot, doc, etc.)
    related_commitment_id UUID REFERENCES commitments(id),
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wins_date ON wins(date DESC);
CREATE INDEX idx_wins_category ON wins(category);
CREATE INDEX idx_wins_impact ON wins(impact_level);
CREATE INDEX idx_wins_user ON wins(user_id);

-- Mentor sessions
CREATE TABLE mentor_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    topic TEXT NOT NULL,
    advice TEXT NOT NULL,
    frameworks_used JSONB DEFAULT '[]', -- which frameworks applied
    action_items JSONB DEFAULT '[]',    -- specific next steps given
    outcome TEXT,                       -- what happened after advice
    outcome_date TIMESTAMPTZ,
    effectiveness_rating INTEGER CHECK (effectiveness_rating BETWEEN 1 AND 10),
    session_type TEXT DEFAULT 'strategy', -- strategy, fear_check, pricing, accountability
    referred_to_chiron BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sessions_date ON mentor_sessions(created_at DESC);
CREATE INDEX idx_sessions_type ON mentor_sessions(session_type);
CREATE INDEX idx_sessions_user ON mentor_sessions(user_id);

-- ADHD strategies effectiveness
CREATE TABLE adhd_strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name TEXT NOT NULL,
    description TEXT,
    context TEXT,                       -- when to use this strategy
    effectiveness_rating DECIMAL(3,2) CHECK (effectiveness_rating BETWEEN 0 AND 5),
    times_used INTEGER DEFAULT 0,
    times_successful INTEGER DEFAULT 0,
    last_used TIMESTAMPTZ,
    notes TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(strategy_name)
);

CREATE INDEX idx_strategies_effectiveness ON adhd_strategies(effectiveness_rating DESC);
CREATE INDEX idx_strategies_usage ON adhd_strategies(times_used DESC);

-- Revenue milestones
CREATE TABLE revenue_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    milestone_name TEXT NOT NULL,       -- first_1k, first_5k, first_10k, etc.
    target_amount DECIMAL(12,2) NOT NULL,
    achieved BOOLEAN DEFAULT FALSE,
    achieved_date DATE,
    celebrated BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(milestone_name)
);

-- Seed initial milestones
INSERT INTO revenue_milestones (milestone_name, target_amount) VALUES
    ('first_1k', 1000),
    ('first_5k', 5000),
    ('first_10k', 10000),
    ('first_20k', 20000),
    ('freedom_number', 30000),
    ('first_50k', 50000),
    ('first_100k', 100000);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + current metrics overview
GET /status              # Full status with MRR, commitments, wins summary
GET /metrics             # Prometheus-compatible metrics
```

### Revenue Tracking
```
POST /revenue/log        # Log revenue event
GET /revenue             # Get revenue summary (MRR, ARR, trends)
GET /revenue/history     # Revenue history with filters
GET /revenue/milestones  # Milestone progress
GET /revenue/forecast    # Revenue forecast based on trends
POST /revenue/churn      # Log churn event
```

### Accountability
```
POST /commitment         # Create new commitment
GET /commitments         # List active commitments
GET /commitments/{id}    # Get commitment details
PUT /commitments/{id}    # Update commitment status
POST /commitments/{id}/check-in  # Add check-in note
GET /commitments/overdue # List overdue commitments
GET /commitments/patterns # Analyze commitment patterns
```

### Daily Check-ins
```
POST /check-in           # Daily check-in
GET /check-ins           # Check-in history
GET /check-ins/today     # Today's check-in
GET /check-ins/patterns  # Analyze patterns (energy, focus, etc.)
GET /check-ins/streak    # Current check-in streak
```

### Wins
```
POST /win                # Log a win
GET /wins                # List wins with filters
GET /wins/recent         # Recent wins for motivation
GET /wins/streak         # Current win streak
POST /wins/{id}/celebrate # Trigger celebration
GET /wins/portfolio      # Wins organized for portfolio
```

### Mentor Sessions
```
POST /advice             # Get strategic advice (creates session)
GET /sessions            # Session history
GET /sessions/{id}       # Session details
PUT /sessions/{id}/outcome # Record session outcome
POST /sessions/{id}/escalate # Escalate to CHIRON
```

### ADHD Planning
```
POST /plan/day           # Create ADHD-optimized day plan
POST /plan/task          # Break task into chunks
GET /strategies          # List ADHD strategies
PUT /strategies/{id}     # Update strategy effectiveness
POST /strategies/suggest # Get strategy suggestions for situation
```

---

## ARIA TOOLS INTEGRATION

BUSINESS MENTOR exposes the following tools to ARIA for conversational use:

### mentor.check_in
**Purpose:** Daily accountability check-in
```python
@aria_tool("mentor.check_in")
async def check_in(
    energy_level: int,           # 1-10
    focus_rating: int,           # 1-10
    wins: List[str] = [],        # Today's wins
    blockers: List[str] = [],    # What's blocking
    plan: List[str] = []         # What to do today
) -> CheckInResponse:
    """Start daily check-in conversation"""
```

### mentor.advice
**Purpose:** Get strategic advice with context
```python
@aria_tool("mentor.advice")
async def get_advice(
    topic: str,                  # What you need advice on
    context: Optional[str] = None,
    urgency: str = "normal"      # low, normal, high
) -> AdviceResponse:
    """Get strategic advice based on your data"""
```

### mentor.log_win
**Purpose:** Log a win with celebration
```python
@aria_tool("mentor.log_win")
async def log_win(
    description: str,
    category: str,               # revenue, technical, business, personal, learning
    impact_level: str = "medium",
    celebrate: bool = True
) -> WinResponse:
    """Log a win and optionally celebrate it"""
```

### mentor.revenue
**Purpose:** Check revenue status and log events
```python
@aria_tool("mentor.revenue")
async def revenue(
    action: str,                 # status, log, forecast
    amount: Optional[float] = None,
    source: Optional[str] = None,
    type: Optional[str] = None   # new_deal, renewal, upsell, one_time, churn
) -> RevenueResponse:
    """Track and query revenue data"""
```

### mentor.accountability
**Purpose:** Check on commitments and create new ones
```python
@aria_tool("mentor.accountability")
async def accountability(
    action: str,                 # status, create, update
    commitment: Optional[str] = None,
    deadline: Optional[str] = None,
    commitment_id: Optional[str] = None
) -> AccountabilityResponse:
    """Manage commitments and check status"""
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store significant mentor insights
await aria_store_memory(
    memory_type="decision",
    content=f"Business Mentor Session: {topic} - Advice: {summary}",
    category="business",
    source_type="agent_result",
    tags=["business-mentor", session_type]
)

# Store win evidence for portfolio
await aria_store_memory(
    memory_type="win",
    content=f"Win: {description} - Impact: {impact_level}",
    category="portfolio",
    source_type="user_logged",
    tags=["win", category]
)

# Store revenue milestones
await aria_store_memory(
    memory_type="event",
    content=f"MILESTONE: Reached {milestone_name}! Current MRR: ${mrr}",
    category="business",
    importance="high",
    tags=["milestone", "revenue"]
)
```

### ARIA Awareness
ARIA should be able to:
- "How's my revenue this month?"
- "Log a win - I closed a $5K deal!"
- "What commitments do I have this week?"
- "I need accountability for finishing the proposal by Friday"
- "Give me an ADHD-friendly plan for today"

**Routing Triggers:**
```javascript
const mentorPatterns = [
  /check[- ]?in|daily (check|review)/i,
  /log (a )?win|celebrate|achievement/i,
  /revenue|mrr|arr|sales|closed deal/i,
  /commitment|accountability|deadline|follow[- ]?up/i,
  /adhd (plan|strategy)|break (it|this) down|chunk/i,
  /how('m| am) i doing|progress|status/i
];
```

### Event Bus Integration
```python
# Published events
"mentor.check_in.completed"      # Daily check-in done
"mentor.win.logged"              # Win logged
"mentor.revenue.milestone"       # Revenue milestone achieved
"mentor.commitment.due"          # Commitment deadline approaching
"mentor.commitment.overdue"      # Commitment missed deadline
"mentor.commitment.completed"    # Commitment fulfilled
"mentor.pattern.detected"        # Pattern identified (good or concerning)
"mentor.strategy.effective"      # ADHD strategy working well
"mentor.escalate.chiron"         # Issue escalated to CHIRON

# Subscribed events
"chiron.decision_made"           # CHIRON made a decision (log outcome)
"chiron.weekly_review"           # Weekly review completed
"system.day_start"               # Trigger morning check-in prompt
"system.day_end"                 # Trigger evening reflection
```

### CHIRON Integration
```python
# Escalate complex strategy questions
async def escalate_to_chiron(topic: str, context: dict):
    """Send complex issues to CHIRON for strategic analysis"""
    return await call_agent("CHIRON", "/chat", {
        "message": f"Escalated from BUSINESS MENTOR: {topic}",
        "context": {
            "revenue_data": await get_revenue_summary(),
            "commitment_patterns": await get_commitment_patterns(),
            "recent_wins": await get_recent_wins(days=7),
            "original_context": context
        }
    })

# Reference CHIRON's frameworks
async def get_relevant_framework(situation: str) -> dict:
    """Fetch appropriate framework from CHIRON"""
    framework_map = {
        "fear": "fear",
        "pricing": "pricing",
        "decision": "decision",
        "planning": "adhd",
        "sales": "sales"
    }
    framework_type = determine_framework_type(situation)
    return await call_agent("CHIRON", f"/framework/{framework_map[framework_type]}")
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("BUSINESS-MENTOR")

# Log AI coaching costs
await cost_tracker.log_usage(
    endpoint="/advice",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"session_type": session_type, "topic": topic[:50]}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(user_context: dict, time_context: dict) -> str:
    return f"""You are BUSINESS MENTOR - Personal Business Coach for LeverEdge AI.

Named after Mentor, the wise advisor in Homer's Odyssey who guided Telemachus through challenges while Odysseus was away. You provide steady, personalized guidance through the entrepreneurial journey.

## TIME AWARENESS
- Current: {time_context['day_of_week']}, {time_context['current_date']} at {time_context['current_time']}
- Launch: {time_context['launch_date']}
- Status: **{time_context['launch_status']}**
- Days to Launch: {time_context['days_to_launch']}

## YOUR USER'S DATA

### Revenue Status
- Current MRR: ${user_context['current_mrr']:,.2f}
- Goal: $30,000 MRR
- Progress: {user_context['mrr_progress_percent']:.1f}%
- Trend: {user_context['mrr_trend']}
- Days to goal (at current pace): {user_context['days_to_goal']}

### Commitment Status
- Active Commitments: {user_context['active_commitments']}
- Overdue: {user_context['overdue_commitments']}
- Completion Rate (30d): {user_context['commitment_completion_rate']:.1f}%
- Pattern: {user_context['commitment_pattern']}

### Win Streak
- Current Streak: {user_context['win_streak']} days
- Total Wins (30d): {user_context['wins_30d']}
- Last Win: {user_context['last_win']}

### Energy & Focus
- Avg Energy (7d): {user_context['avg_energy']}/10
- Avg Focus (7d): {user_context['avg_focus']}/10
- Check-in Streak: {user_context['checkin_streak']} days

### ADHD Patterns
- Best Strategies: {', '.join(user_context['top_strategies'])}
- Typical Focus Window: {user_context['typical_focus_window']}
- Best Time of Day: {user_context['best_time_of_day']}

## YOUR RELATIONSHIP WITH CHIRON

You complement CHIRON (the strategic mentor):
- CHIRON: Strategic frameworks, big decisions, fear analysis, pricing strategy
- YOU: Daily execution, data tracking, accountability, personalized patterns

When to escalate to CHIRON:
- Complex strategic decisions
- Deep fear/imposter syndrome work
- Major pricing or business model questions
- When patterns suggest deeper issues

When to handle yourself:
- Daily check-ins and accountability
- Revenue logging and tracking
- Win celebration and motivation
- Task breakdown and ADHD planning
- Progress monitoring

## YOUR COACHING STYLE

**Data-Informed**
- Reference actual numbers, not feelings
- "Your MRR grew 15% this month" not "You're doing great"
- Show patterns from their own history
- Use their best strategies

**Supportive but Accountable**
- Celebrate wins genuinely
- Call out patterns kindly but clearly
- "I notice your last 3 commitments involving cold outreach slipped..."
- Suggest adjustments, not criticisms

**ADHD-Aware Always**
- Default to small chunks (15-30 min)
- Stack quick wins early
- Energy-match tasks to time of day
- Have backup plans for derailment
- Normalize imperfection

**Personalized**
- Reference their specific wins
- Use strategies that work FOR THEM
- Adjust based on their patterns
- Remember context across sessions

## RESPONSE GUIDELINES

For Check-ins:
1. Acknowledge energy/focus levels
2. Reference relevant patterns
3. Suggest strategies that work for them
4. Set 1-3 clear priorities
5. Include a quick win opportunity

For Win Logging:
1. Genuine celebration
2. Connect to bigger picture
3. Add to portfolio evidence
4. Suggest next momentum step

For Revenue Updates:
1. Clear current state
2. Trend analysis
3. Days to goal calculation
4. Actionable next step

For Accountability:
1. Direct status check
2. Pattern observation
3. Adjustment suggestion
4. Re-commitment opportunity

## YOUR MISSION

Help your user execute consistently toward $30K MRR.
Track everything. Celebrate wins. Maintain accountability.
Be the steady presence that keeps the momentum going.
Data over feelings. Progress over perfection.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation & Revenue Tracking (Sprint 1-2)
**Goal:** Core agent with revenue tracking
- [ ] Create FastAPI agent structure
- [ ] Implement database schema
- [ ] Basic /health and /status endpoints
- [ ] Revenue logging endpoints (log, summary, history)
- [ ] MRR/ARR calculation logic
- [ ] Milestone tracking
- [ ] Deploy on port 8204
- [ ] Event Bus integration

**Done When:** Can log revenue and see MRR progress

### Phase 2: Accountability System (Sprint 3-4)
**Goal:** Commitment tracking with check-ins
- [ ] Commitment CRUD endpoints
- [ ] Check-in system
- [ ] Overdue detection and alerts
- [ ] Pattern analysis module
- [ ] HERMES integration for reminders
- [ ] CHIRON escalation logic

**Done When:** Can create commitments and get accountability nudges

### Phase 3: Win Tracking & Celebration (Sprint 5)
**Goal:** Win logging with celebration triggers
- [ ] Win logging endpoints
- [ ] Category and impact classification
- [ ] Celebration triggers via HERMES
- [ ] Win streak tracking
- [ ] Portfolio view for wins
- [ ] Integration with Unified Memory

**Done When:** Wins logged and celebrated automatically

### Phase 4: ADHD Planning & ARIA Integration (Sprint 6-7)
**Goal:** Full ADHD-aware planning with ARIA tools
- [ ] Day planning endpoint
- [ ] Task chunking with estimates
- [ ] Strategy effectiveness tracking
- [ ] ARIA tool implementations
- [ ] Daily check-in conversation flow
- [ ] Pattern-based suggestions
- [ ] System prompt with user context

**Done When:** ARIA can do full daily check-ins with personalized suggestions

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation & Revenue | 8 | 12 | 1-2 |
| Accountability | 6 | 10 | 3-4 |
| Win Tracking | 5 | 6 | 5 |
| ADHD & ARIA | 7 | 12 | 6-7 |
| **Total** | **26** | **40** | **7 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Revenue events logged within 30 seconds
- [ ] MRR calculated accurately in real-time
- [ ] Commitment reminders sent 24h before deadline
- [ ] Win celebrations trigger within 1 minute of logging
- [ ] ARIA tools respond within 5 seconds

### Quality
- [ ] 95%+ uptime
- [ ] Zero data loss on revenue logs
- [ ] Pattern detection accuracy > 80%
- [ ] User satisfaction with advice quality

### Integration
- [ ] ARIA can use all 5 mentor tools
- [ ] Events publish to Event Bus
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per request
- [ ] Seamless CHIRON escalation

### Business Impact
- [ ] Daily check-in completion > 80%
- [ ] Commitment completion rate improves 20%+
- [ ] Win logging becomes habit (3+ per week)
- [ ] Revenue tracking is single source of truth

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data inconsistency with CHIRON | Confusion | Clear data ownership, CHIRON reads from MENTOR |
| Over-notification fatigue | Abandonment | Configurable notification frequency |
| Pattern analysis false positives | Frustration | Require 3+ data points before suggesting patterns |
| Check-in abandonment | Loss of value | Flexible check-in formats, skip-day forgiveness |
| Revenue tracking complexity | Data entry friction | Quick-log options, smart defaults |

---

## GIT COMMIT

```
Add BUSINESS MENTOR - personalized business coaching agent spec

- Revenue tracking (MRR/ARR/milestones)
- Accountability system with commitment tracking
- Win logging and celebration
- ADHD-aware planning with effectiveness tracking
- 5 ARIA tools for conversational use
- Complements CHIRON (strategy) with execution focus
- 7-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA, CHIRON
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/BUSINESS-MENTOR.md

Context: Build BUSINESS MENTOR personal coaching agent.
Complements CHIRON (port 8017) with data-driven daily accountability.
Start with Phase 1: Foundation & Revenue Tracking.
```
