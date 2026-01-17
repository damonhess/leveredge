# GYM COACH - AI-Powered Fitness & Workout Agent

**Agent Type:** Personal Life - Health & Fitness
**Named After:** Apollo - Greek god of athletics, physical perfection, and bodily health
**Port:** 8100
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

GYM COACH is an AI-powered fitness agent providing personalized workout programming, progressive overload tracking, exercise guidance, form analysis, and recovery management. It serves as the personal trainer brain for LeverEdge users, delivering science-backed fitness guidance accessible through ARIA.

### Value Proposition
- Personalized workout programs adapted to individual goals and equipment
- Progressive overload tracking ensures continuous strength gains
- Form guidance reduces injury risk and maximizes effectiveness
- Recovery optimization prevents overtraining and burnout
- First agent in Personal Life range (8100-8199)

---

## CORE CAPABILITIES

### 1. Workout Planning
**Purpose:** Create personalized workout programs based on user goals, equipment, and schedule

**Features:**
- Goal-based program generation (strength, hypertrophy, endurance, fat loss)
- Equipment-aware programming (home gym, full gym, bodyweight only)
- Frequency customization (2-6 days per week)
- Progressive periodization (linear, undulating, block)
- Deload week scheduling
- Exercise substitution based on equipment/injuries

**Program Types:**
| Goal | Structure | Rep Ranges | Rest Periods |
|------|-----------|------------|--------------|
| Strength | Low volume, high intensity | 1-5 reps | 3-5 min |
| Hypertrophy | Moderate volume, moderate intensity | 8-12 reps | 60-90 sec |
| Endurance | High volume, low intensity | 15-25 reps | 30-60 sec |
| Power | Explosive movements | 3-6 reps | 2-3 min |
| Fat Loss | Circuit-based, supersets | 10-15 reps | 30-45 sec |

### 2. Progressive Overload Engine
**Purpose:** Track performance and suggest intelligent progression

**Features:**
- Automatic weight progression recommendations
- Rep/set progression tracking
- Volume load calculations (sets x reps x weight)
- Plateau detection and breakthrough strategies
- Personal record (PR) tracking and celebration
- Estimated 1RM calculations

**Progression Methods:**
- Linear: Add 2.5-5 lbs per session (beginner)
- Double progression: Hit top of rep range before adding weight
- Wave loading: Vary intensity across weeks
- RPE-based: Adjust based on perceived effort

### 3. Exercise Library
**Purpose:** Comprehensive database of exercises with form cues and variations

**Features:**
- 500+ exercises with detailed instructions
- Muscle group targeting (primary, secondary)
- Equipment requirements
- Difficulty ratings (beginner, intermediate, advanced)
- Video references for form
- Common mistakes and corrections
- Injury-safe alternatives

**Muscle Group Categories:**
- Push: Chest, shoulders, triceps
- Pull: Back, biceps, rear delts
- Legs: Quads, hamstrings, glutes, calves
- Core: Abs, obliques, lower back
- Compound: Full body movements

### 4. Form Guidance
**Purpose:** AI analysis of form descriptions to prevent injuries and optimize movements

**Features:**
- Natural language form check ("my lower back hurts during deadlifts")
- Cue recommendations based on common issues
- Injury prevention guidance
- Mobility/flexibility recommendations
- Warm-up sequence generation
- Cool-down and stretching protocols

**Analysis Categories:**
| Issue | Detection | Recommendation |
|-------|-----------|----------------|
| Lower back rounding | Deadlift form description | Hip hinge drills, core bracing |
| Knee cave | Squat form description | Glute activation, band work |
| Elbow flare | Bench press issues | Tuck elbows, grip width |
| Shoulder impingement | Overhead press pain | Mobility work, angle adjustment |
| Wrist pain | Front squat grip | Alternative grips, stretches |

### 5. Recovery Tracking
**Purpose:** Optimize rest and recovery for maximum gains

**Features:**
- Rest day recommendations based on volume/intensity
- Sleep quality correlation with performance
- Soreness level tracking (DOMS monitoring)
- Fatigue accumulation detection
- Deload recommendations
- Nutrition timing suggestions

**Recovery Metrics:**
- Sleep hours and quality (1-10)
- Muscle soreness by body part (1-10)
- Energy level (1-10)
- Stress level (1-10)
- Heart rate variability (if available)

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for analysis and recommendations
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/gym-coach/
├── gym_coach.py              # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── exercises.yaml        # Exercise database seed
│   ├── programs.yaml         # Program templates
│   └── progression.yaml      # Progression algorithms
├── modules/
│   ├── workout_planner.py    # Program generation engine
│   ├── progression_engine.py # Progressive overload logic
│   ├── exercise_library.py   # Exercise database management
│   ├── form_analyzer.py      # AI-powered form guidance
│   └── recovery_tracker.py   # Recovery optimization
└── tests/
    └── test_gym_coach.py
```

### Database Schema

```sql
-- Workout programs table
CREATE TABLE workout_programs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    goal TEXT NOT NULL,              -- strength, hypertrophy, endurance, power, fat_loss
    frequency INTEGER NOT NULL,       -- days per week
    split_type TEXT,                  -- ppl, upper_lower, full_body, bro_split
    duration_weeks INTEGER DEFAULT 12,
    current_week INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    settings JSONB                    -- rest times, progression rules, etc.
);

CREATE INDEX idx_programs_user ON workout_programs(user_id);
CREATE INDEX idx_programs_active ON workout_programs(active);

-- Workout sessions table
CREATE TABLE workout_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id UUID REFERENCES workout_programs(id),
    user_id TEXT NOT NULL,
    scheduled_date DATE,
    actual_date DATE,
    workout_name TEXT,                -- "Push Day", "Leg Day A", etc.
    duration_minutes INTEGER,
    notes TEXT,
    energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 10),
    overall_rating INTEGER CHECK (overall_rating BETWEEN 1 AND 10),
    completed BOOLEAN DEFAULT FALSE,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    location TEXT                     -- home, gym, outdoor
);

CREATE INDEX idx_sessions_user ON workout_sessions(user_id);
CREATE INDEX idx_sessions_program ON workout_sessions(program_id);
CREATE INDEX idx_sessions_date ON workout_sessions(actual_date DESC);

-- Exercise library table
CREATE TABLE exercises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    muscle_groups TEXT[] NOT NULL,    -- primary muscles worked
    secondary_muscles TEXT[],
    equipment TEXT[],                 -- barbell, dumbbell, cable, bodyweight, etc.
    difficulty TEXT DEFAULT 'intermediate', -- beginner, intermediate, advanced
    movement_type TEXT,               -- compound, isolation
    force_type TEXT,                  -- push, pull, static
    instructions TEXT NOT NULL,
    form_cues TEXT[],
    common_mistakes TEXT[],
    video_url TEXT,
    thumbnail_url TEXT,
    alternatives TEXT[],              -- substitute exercise names
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_exercises_name ON exercises(name);
CREATE INDEX idx_exercises_muscle ON exercises USING GIN(muscle_groups);
CREATE INDEX idx_exercises_equipment ON exercises USING GIN(equipment);

-- Exercise logs table
CREATE TABLE exercise_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES workout_sessions(id) ON DELETE CASCADE,
    exercise_id UUID REFERENCES exercises(id),
    exercise_name TEXT NOT NULL,      -- denormalized for quick access
    set_number INTEGER NOT NULL,
    reps INTEGER,
    weight DECIMAL(6,2),              -- in user's preferred unit
    weight_unit TEXT DEFAULT 'lbs',   -- lbs or kg
    rpe INTEGER CHECK (rpe BETWEEN 1 AND 10),  -- rate of perceived exertion
    rest_seconds INTEGER,
    tempo TEXT,                       -- e.g., "3-1-2-0" for eccentric-pause-concentric-pause
    notes TEXT,
    is_warmup BOOLEAN DEFAULT FALSE,
    is_pr BOOLEAN DEFAULT FALSE,
    logged_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_logs_session ON exercise_logs(session_id);
CREATE INDEX idx_logs_exercise ON exercise_logs(exercise_id);
CREATE INDEX idx_logs_pr ON exercise_logs(is_pr) WHERE is_pr = TRUE;

-- Body metrics table
CREATE TABLE body_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    weight DECIMAL(5,2),
    weight_unit TEXT DEFAULT 'lbs',
    body_fat_percentage DECIMAL(4,2),
    measurements JSONB,               -- chest, waist, hips, arms, thighs, etc.
    photos JSONB,                     -- progress photo URLs
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

CREATE INDEX idx_metrics_user ON body_metrics(user_id);
CREATE INDEX idx_metrics_date ON body_metrics(date DESC);

-- Recovery logs table
CREATE TABLE recovery_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    sleep_hours DECIMAL(3,1),
    sleep_quality INTEGER CHECK (sleep_quality BETWEEN 1 AND 10),
    energy_level INTEGER CHECK (energy_level BETWEEN 1 AND 10),
    stress_level INTEGER CHECK (stress_level BETWEEN 1 AND 10),
    soreness JSONB,                   -- { "legs": 7, "chest": 3, "back": 5 }
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date)
);

CREATE INDEX idx_recovery_user ON recovery_logs(user_id);
CREATE INDEX idx_recovery_date ON recovery_logs(date DESC);

-- Personal records table
CREATE TABLE personal_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    exercise_id UUID REFERENCES exercises(id),
    exercise_name TEXT NOT NULL,
    record_type TEXT NOT NULL,        -- 1rm, 3rm, 5rm, max_reps, max_volume
    value DECIMAL(8,2) NOT NULL,
    weight_unit TEXT DEFAULT 'lbs',
    previous_value DECIMAL(8,2),
    achieved_at TIMESTAMPTZ DEFAULT NOW(),
    session_id UUID REFERENCES workout_sessions(id),
    notes TEXT
);

CREATE INDEX idx_pr_user ON personal_records(user_id);
CREATE INDEX idx_pr_exercise ON personal_records(exercise_id);
CREATE INDEX idx_pr_achieved ON personal_records(achieved_at DESC);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # Current training status overview
GET /metrics             # Prometheus-compatible metrics
```

### Workout Programs
```
GET /programs                    # List user's programs
POST /programs                   # Create new program
GET /programs/{id}               # Get program details
PUT /programs/{id}               # Update program
DELETE /programs/{id}            # Delete program
POST /programs/{id}/activate     # Set as active program
GET /programs/{id}/schedule      # Get weekly schedule
POST /programs/generate          # AI-generate program from goals
```

### Workout Sessions
```
GET /sessions                    # List recent sessions
POST /sessions                   # Create/start a session
GET /sessions/{id}               # Get session details
PUT /sessions/{id}               # Update session
POST /sessions/{id}/complete     # Mark session complete
GET /sessions/next               # Get next scheduled workout
GET /sessions/today              # Get today's workout
DELETE /sessions/{id}            # Delete session
```

### Exercise Library
```
GET /exercises                   # List/search exercises
GET /exercises/{id}              # Get exercise details
GET /exercises/search            # Search by name/muscle/equipment
GET /exercises/muscle/{group}    # Get exercises for muscle group
POST /exercises                  # Add custom exercise
PUT /exercises/{id}              # Update exercise
GET /exercises/{id}/alternatives # Get substitute exercises
POST /exercises/{id}/form-check  # AI form analysis
```

### Exercise Logging
```
POST /logs                       # Log a set
GET /logs/session/{session_id}   # Get all logs for session
PUT /logs/{id}                   # Update log entry
DELETE /logs/{id}                # Delete log entry
GET /logs/exercise/{exercise_id} # History for specific exercise
GET /logs/progress/{exercise_id} # Progress chart data
```

### Body Metrics
```
GET /metrics/body                # Get body metrics history
POST /metrics/body               # Log body metrics
GET /metrics/body/latest         # Get most recent metrics
GET /metrics/body/progress       # Progress over time
```

### Recovery
```
GET /recovery                    # Get recovery history
POST /recovery                   # Log recovery data
GET /recovery/today              # Today's recovery status
GET /recovery/readiness          # Training readiness score
POST /recovery/check-in          # Quick daily check-in
```

### Progress & Analytics
```
GET /progress                    # Overall progress summary
GET /progress/exercise/{id}      # Progress for specific lift
GET /progress/volume             # Volume trends over time
GET /progress/prs                # Personal record history
GET /progress/streaks            # Training streak info
GET /analytics/summary           # Weekly/monthly summary
```

### AI Features
```
POST /ai/suggest-weight          # Suggest weight for next set
POST /ai/form-check              # Analyze form description
POST /ai/program-advice          # Get program recommendations
POST /ai/recovery-advice         # Get recovery recommendations
POST /ai/plateau-break           # Strategies for breaking plateau
```

---

## ARIA TOOLS

Tools exposed to ARIA for natural language fitness queries:

### gym.log_workout
**Purpose:** Log a completed workout session
```python
@aria_tool("gym.log_workout")
async def log_workout(
    exercises: List[dict],    # [{name, sets, reps, weight}]
    duration_minutes: int,
    energy_level: int = None,
    notes: str = None
) -> dict:
    """Log a completed workout with all exercises performed."""
    # Create session and log all exercises
    # Detect PRs and milestones
    # Return summary with any achievements
```

### gym.get_program
**Purpose:** Get user's current workout program
```python
@aria_tool("gym.get_program")
async def get_program(
    user_id: str
) -> dict:
    """Get the user's current active workout program."""
    # Return program details, current week, schedule
```

### gym.next_workout
**Purpose:** Get the next scheduled workout
```python
@aria_tool("gym.next_workout")
async def next_workout(
    user_id: str
) -> dict:
    """Get what workout is scheduled next."""
    # Return workout name, exercises, suggested weights
```

### gym.progress
**Purpose:** Show progress on specific lifts over time
```python
@aria_tool("gym.progress")
async def progress(
    user_id: str,
    exercise_name: str = None,  # Specific exercise or overall
    period: str = "month"       # week, month, quarter, year
) -> dict:
    """Show progress on lifts over time."""
    # Return progress data, PRs, volume trends
```

### gym.suggest_weight
**Purpose:** Suggest weight for next set based on history
```python
@aria_tool("gym.suggest_weight")
async def suggest_weight(
    user_id: str,
    exercise_name: str,
    target_reps: int,
    target_rpe: int = 8
) -> dict:
    """Suggest appropriate weight for next set."""
    # Analyze history, calculate recommendation
    # Consider fatigue, recovery status
```

---

## EVENT BUS INTEGRATION

### Published Events
```python
# Workout events
"gym.workout.started"           # User started a workout
"gym.workout.completed"         # User completed a workout

# Achievement events
"gym.milestone.reached"         # PR, streak, or goal achieved
"gym.pr.set"                    # New personal record
"gym.streak.achieved"           # X days/weeks streak

# Program events
"gym.program.created"           # New program created
"gym.program.updated"           # Program modified
"gym.program.completed"         # Program cycle completed

# Recovery events
"gym.recovery.low"              # Recovery metrics indicate fatigue
"gym.deload.recommended"        # System recommends deload
```

### Subscribed Events
```python
"user.profile.updated"          # Update user preferences
"calendar.schedule.changed"     # Adjust workout schedule
"health.sleep.logged"           # Integrate sleep data
"nutrition.meal.logged"         # Consider nutrition timing
```

### Event Payload Examples
```python
# gym.workout.completed
{
    "user_id": "user_123",
    "session_id": "sess_456",
    "workout_name": "Push Day A",
    "duration_minutes": 65,
    "exercises_completed": 6,
    "total_volume": 15000,  # lbs
    "prs_set": 1,
    "energy_level": 8
}

# gym.milestone.reached
{
    "user_id": "user_123",
    "milestone_type": "pr",  # pr, streak, goal
    "description": "New bench press PR: 225 lbs x 5",
    "exercise_name": "bench_press",
    "value": 225,
    "previous_best": 220
}
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store workout insights
await aria_store_memory(
    memory_type="fact",
    content=f"User hit new bench PR of 225 lbs",
    category="fitness",
    source_type="agent_result",
    tags=["gym-coach", "pr", "bench_press"]
)

# Store preferences
await aria_store_memory(
    memory_type="preference",
    content=f"User prefers morning workouts between 6-8am",
    category="fitness",
    source_type="user_stated"
)

# Store progress summaries
await aria_store_memory(
    memory_type="fact",
    content=f"User completed 12-week strength program, increased squat by 40 lbs",
    category="fitness",
    source_type="agent_result",
    tags=["gym-coach", "program_complete"]
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What's my workout today?"
- Request "Log my workout: bench 185x8x3, rows 135x10x3"
- Query "How's my bench press progress?"
- Get "What weight should I use for squats?"
- Ask "Am I recovered enough to train today?"

**Routing Triggers:**
```javascript
const gymCoachPatterns = [
  /workout|exercise|gym|training/i,
  /bench|squat|deadlift|press/i,
  /sets?|reps?|weight/i,
  /muscle|gains?|strength|hypertrophy/i,
  /pr|personal record/i,
  /recovery|soreness|rest day/i,
  /program|routine|split/i
];
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("GYM_COACH")

# Log AI program generation costs
await cost_tracker.log_usage(
    endpoint="/programs/generate",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"goal": goal, "frequency": frequency}
)

# Log form analysis costs
await cost_tracker.log_usage(
    endpoint="/exercises/{id}/form-check",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"exercise": exercise_name}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(fitness_context: dict) -> str:
    return f"""You are GYM COACH - Elite Fitness & Training Agent for LeverEdge AI.

Named after Apollo, Greek god of athletics and physical perfection, you guide users toward their fitness goals with science-backed training wisdom.

## TIME AWARENESS
- Current: {fitness_context['current_time']}
- User's Program Week: {fitness_context['current_week']}

## YOUR IDENTITY
You are the personal trainer brain of LeverEdge. You design programs, track progress, analyze form, and ensure users train effectively and safely.

## CURRENT FITNESS STATUS
- Active Program: {fitness_context['active_program']}
- Current Week: {fitness_context['current_week']}/12
- Workouts This Week: {fitness_context['workouts_this_week']}
- Last Workout: {fitness_context['last_workout']}
- Recent PRs: {fitness_context['recent_prs']}
- Recovery Status: {fitness_context['recovery_status']}

## YOUR CAPABILITIES

### Workout Planning
- Create personalized programs (strength, hypertrophy, endurance)
- Adjust frequency based on schedule and recovery
- Design splits (PPL, Upper/Lower, Full Body, Bro Split)
- Plan periodization and deload weeks
- Substitute exercises based on equipment/injuries

### Progressive Overload
- Track all lifts and suggest weight increases
- Monitor volume and intensity trends
- Detect plateaus and recommend breakthrough strategies
- Celebrate PRs and milestones
- Calculate estimated 1RMs

### Exercise Guidance
- Access library of 500+ exercises
- Provide form cues and common mistake corrections
- Suggest alternatives and variations
- Recommend warm-up and mobility work
- Guide injury-safe training modifications

### Form Analysis
- Analyze form descriptions for issues
- Provide cue recommendations
- Suggest mobility/flexibility work
- Identify movement pattern problems
- Recommend corrective exercises

### Recovery Optimization
- Track sleep, soreness, and energy
- Recommend rest days and deloads
- Consider stress and fatigue accumulation
- Optimize training frequency
- Prevent overtraining

## TRAINING PRINCIPLES
1. Progressive overload is the key to gains
2. Consistency beats intensity
3. Recovery is when growth happens
4. Form before weight, always
5. Track everything to improve anything

## RESPONSE FORMAT
For workout queries:
1. Acknowledge current status/recovery
2. Provide clear exercise prescription
3. Include weight suggestions based on history
4. Note any form cues or considerations
5. Motivate and encourage

## TEAM COORDINATION
- Log insights and PRs -> ARIA via Unified Memory
- Publish achievements -> Event Bus
- Send milestone notifications -> HERMES
- Coordinate with nutrition (future) -> DEMETER

## YOUR MISSION
Help users achieve their fitness goals safely and effectively.
Every rep counts. Every PR matters.
Build strength, build confidence, build better humans.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Week 1-2)
**Goal:** Basic agent with exercise library and simple logging

**Tasks:**
- [ ] Create FastAPI agent structure on port 8100
- [ ] Implement /health and /status endpoints
- [ ] Set up PostgreSQL schema in Supabase
- [ ] Seed exercise library (100 core exercises)
- [ ] Basic CRUD for workout sessions
- [ ] Simple exercise logging
- [ ] Deploy and test

**Done When:** Can log workouts and view exercise library

### Phase 2: Programs & Progression (Week 3-4)
**Goal:** Workout program management and progressive overload

**Tasks:**
- [ ] Program CRUD operations
- [ ] AI-powered program generation
- [ ] Progressive overload algorithm
- [ ] Weight suggestion engine
- [ ] PR detection and tracking
- [ ] Volume calculations
- [ ] ARIA tools integration (gym.log_workout, gym.get_program)

**Done When:** Users can follow AI-generated programs with weight suggestions

### Phase 3: Form & Recovery (Week 5-6)
**Goal:** Form analysis and recovery tracking

**Tasks:**
- [ ] Form analysis AI module
- [ ] Recovery logging system
- [ ] Training readiness score
- [ ] Deload recommendations
- [ ] Soreness tracking by muscle group
- [ ] Sleep quality integration
- [ ] ARIA tools (gym.next_workout, gym.suggest_weight)

**Done When:** System provides form guidance and recovery-aware recommendations

### Phase 4: Analytics & Polish (Week 7-8)
**Goal:** Progress tracking, analytics, and full integration

**Tasks:**
- [ ] Progress visualization data endpoints
- [ ] Weekly/monthly summaries
- [ ] Streak tracking
- [ ] Event Bus integration (all events)
- [ ] Unified Memory integration
- [ ] Cost tracking implementation
- [ ] Complete ARIA tools (gym.progress)
- [ ] Full test coverage
- [ ] Documentation

**Done When:** Full-featured fitness agent with all integrations active

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Timeline |
|-------|-------|------------|----------|
| Foundation | 7 | 16 | Week 1-2 |
| Programs & Progression | 7 | 20 | Week 3-4 |
| Form & Recovery | 7 | 18 | Week 5-6 |
| Analytics & Polish | 9 | 22 | Week 7-8 |
| **Total** | **30** | **76** | **8 weeks** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Users can create and follow personalized workout programs
- [ ] Progressive overload suggestions are accurate within 5% of optimal
- [ ] Exercise library contains 100+ exercises with full details
- [ ] Form analysis provides actionable feedback
- [ ] Recovery tracking integrates with training recommendations

### Quality
- [ ] 99%+ uptime
- [ ] API response time < 200ms for standard queries
- [ ] AI responses < 3 seconds for program generation
- [ ] All data persists correctly across sessions
- [ ] Mobile-friendly API responses

### Integration
- [ ] ARIA can query fitness status naturally
- [ ] All 5 ARIA tools functional
- [ ] Events publish to Event Bus correctly
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per AI request

### User Experience
- [ ] Workout logging takes < 30 seconds per exercise
- [ ] Weight suggestions feel accurate and progressive
- [ ] Form guidance is clear and actionable
- [ ] Recovery recommendations match perceived fatigue

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Injury from bad recommendations | User harm, liability | Conservative weight suggestions, form emphasis, disclaimers |
| Inaccurate weight predictions | User frustration, stalled progress | Base on multiple data points, allow manual override |
| Over-reliance on AI | Loss of body awareness | Encourage RPE tracking, recovery self-assessment |
| Data privacy concerns | Trust erosion | Clear data policies, user-controlled deletion |
| Exercise library gaps | User can't find exercises | Allow custom exercises, continuous expansion |

---

## FUTURE ENHANCEMENTS

### Phase 5+ Ideas
- Video form analysis (computer vision)
- Wearable device integration (heart rate, HRV)
- Nutrition coordination with DEMETER agent
- Social features (workout partners, challenges)
- Gym equipment availability awareness
- Voice logging during workouts
- AR form overlay guidance

---

## GIT COMMIT

```
Add GYM COACH - AI-powered fitness and workout agent spec

- Personalized workout program generation
- Progressive overload tracking and weight suggestions
- Exercise library with form guidance
- Recovery tracking and training readiness
- ARIA tools: log_workout, get_program, next_workout, progress, suggest_weight
- Event Bus integration for achievements and milestones
- 4-phase implementation plan (8 weeks)
- Full PostgreSQL schema for Supabase
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/GYM-COACH.md

Context: Build GYM COACH fitness agent. Start with Phase 1 foundation.
```
