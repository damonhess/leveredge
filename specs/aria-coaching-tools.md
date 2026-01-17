# ARIA Life Coaching Tools - Complete Specification V2

## OVERVIEW

Add comprehensive life coaching capabilities to ARIA as discrete n8n workflow tools she can invoke based on context and triggers.

**Current ARIA Capabilities:**
- 7 adaptive modes (DEFAULT, HYPE, COACH, COMFORT, FOCUS, DRILL, STRATEGY)
- CBT Therapist tool
- SHIELD (manipulation detection) + SWORD (influence techniques)
- Pattern detection, decision tracker, task management

**New Capabilities (3 Tiers + CHIRON Integration):**
- TIER 1: Foundation (Wheel of Life, Values, Progress, Goals)
- TIER 2: Advanced Coaching (GROW, Habits, Energy, Decisions, Resistance)
- TIER 3: Master Level (System Architect, Identity Shifter, Leverage Multiplier)
- CHIRON Integration: Business mentoring triggers and framework application

---

## TIER 1: FOUNDATION LAYER (Build First)
*Estimated: 16-20 hours total*

### 1. wheel_of_life
**Purpose:** Visual life balance assessment with AI-powered insights
**Effort:** 3-4 hours
**Triggers:** "life balance", "feeling overwhelmed", "where should I focus", "assess my life"

**Output:**
```json
{
  "wheel_visual": "ASCII wheel representation",
  "balance_score": 6.2,
  "lowest_areas": ["health", "fun_recreation"],
  "highest_areas": ["relationships", "career"],
  "gap_analysis": "3.5 point gap between highest and lowest",
  "priority_recommendations": [
    "Health at 3/10 is critical - small wins: 10min daily walk",
    "Fun at 4/10 - schedule one enjoyable activity this week"
  ],
  "patterns": "Career high but fun low suggests work-life imbalance"
}
```

---

### 2. values_clarifier
**Purpose:** Identify, rank, and check alignment of core values
**Effort:** 4-5 hours
**Triggers:** "what do I value", "hard decision", "conflicted", "what matters to me", "I'm torn between"

**Values Menu:** Achievement, Adventure, Authenticity, Balance, Challenge, Compassion, Creativity, Curiosity, Excellence, Faith, Family, Freedom, Friendship, Fun, Growth, Health, Honesty, Impact, Independence, Influence, Innovation, Integrity, Justice, Knowledge, Leadership, Legacy, Love, Loyalty, Peace, Power, Recognition, Respect, Security, Service, Simplicity, Spirituality, Stability, Success, Trust, Wealth, Wisdom

---

### 3. progress_tracker
**Purpose:** Track micro-progress, detect patterns, celebrate wins
**Effort:** 4-5 hours
**Triggers:** "how am I doing", "track progress", "daily check-in", "review my week"

**Data Collection:**
- Daily check-ins with mood, energy, wins, challenges
- Habit completion tracking
- Goal progress monitoring
- Pattern analysis over time

---

### 4. goal_architect
**Purpose:** Transform vague goals into SMART goals with motivation analysis
**Effort:** 4-5 hours
**Triggers:** "I want to", "my goal is", "I should", "help me plan", "I need to reach"

**SMART + DARN-C Framework:**
- Specific, Measurable, Achievable, Relevant, Time-bound
- Desire, Ability, Reasons, Need, Commitment scoring

---

## TIER 2: ADVANCED COACHING LAYER
*Estimated: 24-30 hours total*

### 5. grow_session
**Purpose:** Guide structured coaching conversations using GROW model
**Effort:** 5-6 hours
**Triggers:** "coach me", "I'm stuck", "help me figure out", "need to work through"

**GROW Phases:** Goal → Reality → Options → Will

---

### 6. habit_designer
**Purpose:** Design sustainable habit formation using behavioral science
**Effort:** 3-4 hours
**Triggers:** "build a habit", "start doing", "be more consistent", "daily routine", "I keep forgetting"

**Core Functions:**
```python
create_habit_stack(anchor_habit, new_habit, reward)
design_habit_loop(cue, routine, reward)
calculate_minimum_viable_habit()
create_implementation_intention()
design_environment_modifications()
schedule_habit_reviews()
```

**ARIA Integration:**
- Data Collection: Habit check-ins via daily/weekly reviews
- Pattern Recognition: Track completion rates, identify failure patterns
- Dynamic Adjustment: Modify habits based on success/failure data
- Trigger Conditions:
  - New habit request
  - Habit failure pattern detected (3+ missed days)
  - Weekly habit review
  - Energy/mood correlation analysis

**Success Metrics:**
- Habit completion rate (target: 80%+ for established habits)
- Streak length tracking
- Habit stack completion
- Environmental trigger effectiveness

---

### 7. energy_optimizer
**Purpose:** Map and optimize personal energy patterns for peak performance
**Effort:** 4-5 hours
**Triggers:** "I'm always tired", "I have no energy", "I'm drained", "I work best when", "I'm most productive"

**Core Functions:**
```python
map_energy_patterns(activities, times, energy_levels)
identify_energy_drains()
identify_energy_sources()
optimize_daily_schedule()
design_energy_recovery_protocols()
create_high_energy_task_blocks()
```

**ADHD Pattern Recognition:**
- Hyperfocus vs scattered patterns
- Procrastination triggers
- Optimal work environments
- Medication timing correlations

**ARIA Coaching Style:**
- "You're forcing high-cognitive tasks during your 2pm energy crash. That's not discipline failure, it's bad design."
- "Your energy map shows you're a morning person trying to work evenings. Let's fix the schedule, not blame willpower."

---

### 8. decision_accelerator
**Purpose:** Speed up decision-making using frameworks and bias awareness
**Effort:** 4-5 hours
**Triggers:** "I don't know what to do", "I'm torn between", "I need to think about", "Maybe I should", "I can't decide"

**Core Functions:**
```python
categorize_decision(reversible, irreversible, impact, urgency)
apply_decision_framework(eisenhower, ooda, 10_10_10, regret_minimization)
identify_decision_biases()
create_decision_criteria()
set_decision_deadlines()
implement_regret_minimization()
```

---

### 9. resistance_decoder
**Purpose:** Identify and address root causes of procrastination/avoidance
**Effort:** 4-5 hours
**Triggers:** "I should probably", "I know I need to but", "I'll get to it later", "It's not that important", "I don't feel like"

**Core Functions:**
```python
identify_resistance_type(fear, overwhelm, perfectionism, boredom)
decode_avoidance_patterns()
design_resistance_interventions()
create_micro_commitments()
implement_body_doubling_requests()
schedule_resistance_reviews()
```

---

## TIER 3: MASTER-LEVEL TOOLS
*Estimated: 12-15 hours total*

### 10. coaching_insights
**Purpose:** Synthesize patterns across all coaching tools
**Effort:** 4-5 hours
**Triggers:** "what have you learned about me", "my patterns", "insights about me"

---

### 11. system_architect
**Purpose:** Design comprehensive life systems for sustained high performance
**Effort:** 4-5 hours
**Triggers:** "design a system for", "build a routine", "create a process"

**Core Functions:**
```python
design_life_operating_system()
create_system_integrations()
identify_system_bottlenecks()
design_feedback_loops()
implement_system_redundancy()
schedule_system_reviews()
```

---

### 12. identity_shifter
**Purpose:** Facilitate identity-level changes for sustainable transformation
**Effort:** 4-5 hours
**Triggers:** "I want to become", "I need to change who I am", "the person I want to be"

**Core Functions:**
```python
identify_current_identity()
design_target_identity()
create_identity_bridges()
implement_identity_evidence()
design_identity_rituals()
monitor_identity_shifts()
```

---

## CHIRON INTEGRATION - TRIGGER PATTERNS

### AUTOMATIC TRIGGERS (Pattern Detection)

```yaml
AVOIDANCE_PATTERNS:
  keywords: ["should build", "need to learn", "maybe I'll", "let me just"]
  response: "🚨 AVOIDANCE DETECTED. What are you afraid of?"
  escalation: Switch to DRILL mode, demand specific action

SCOPE_CREEP:
  keywords: ["one more feature", "while I'm at it", "might as well"]
  response: "SCOPE CREEP ALERT. How does this serve $30K MRR?"
  framework: Eisenhower Matrix application

PERFECTIONISM:
  keywords: ["perfect", "polish", "just need to fix", "not ready"]
  response: "Perfectionism = Fear in fancy dress. Ship it ugly."
  action: Demand 24hr shipping deadline

ANALYSIS_PARALYSIS:
  keywords: ["need more data", "let me research", "not sure which"]
  response: "Paralysis detected. Make decision in 5 minutes."
  framework: Reversible vs Irreversible decision tree

TIME_WASTING:
  context: Discussion not leading to action
  response: "This is mental masturbation. What's the ONE next step?"
  redirect: Force OODA loop application
```

### MANUAL TRIGGERS (Slash Commands)

```yaml
FRAMEWORK_CALLS:
  "/ooda": Apply OODA Loop to current situation
  "/10x": Challenge with 10X thinking
  "/price": Apply pricing psychology
  "/invert": Use inversion thinking
  "/mvp": Strip to minimum viable product

ACCOUNTABILITY:
  "/commit": Lock in specific commitment with deadline
  "/report": Demand progress report on previous commitment
  "/challenge": Challenge current approach/thinking

ENERGY_MANAGEMENT:
  "/energy": Assess current energy state, optimize next action
  "/focus": Identify single most important task
  "/dopamine": Engineer quick win for momentum
```

---

## MODE INTEGRATION

### DEFAULT MODE + Tools
- **Tools Used**: OODA Loop, Eisenhower Matrix
- **Response Pattern**: Balanced advice with gentle framework application

### HYPE MODE + Tools
- **Tools Used**: 10X Thinking, First Principles, ROI Framing
- **Response Pattern**: Frameworks become rallying cries, amplified confidence

### COACH MODE + Tools
- **Tools Used**: All pricing psychology, sales frameworks, decision trees
- **Response Pattern**: Structured development, progressive skill building

### COMFORT MODE + Tools
- **Tools Used**: Inversion (gentle), Regret Minimization
- **Response Pattern**: Soft delivery of hard truths

### FOCUS MODE + Tools
- **Tools Used**: ONE thing focus, Energy management, Time blocking
- **Response Pattern**: Single framework, ruthless prioritization

### DRILL MODE + Tools
- **Tools Used**: All decision frameworks, objection handling, commitment locks
- **Response Pattern**: Rapid-fire framework application, relentless execution

### STRATEGY MODE + Tools
- **Tools Used**: Complex combinations, long-term thinking
- **Response Pattern**: Multiple frameworks layered for deep analysis

---

## TOOL CHAINING PATTERNS

### The FOUNDATION CHAIN
*Use when user seems off-balance or stuck*
1. progress_tracker → Assess current state
2. energy_optimizer → Assess capacity
3. goal_architect → Plan immediate actions

### The GOAL CHAIN
*Use for new goals or major pivots*
1. goal_architect → Clarify objectives
2. values_clarifier → Check alignment
3. habit_designer → Build sustainable systems

### The BREAKTHROUGH CHAIN
*Use when user is chronically stuck*
1. resistance_decoder → Identify blocks
2. cbt_therapist → Process cognitive distortions
3. decision_accelerator → Choose path forward
4. goal_architect → Take immediate action

### The OPTIMIZATION CHAIN
*Use for performance improvement*
1. progress_tracker → Review current patterns
2. energy_optimizer → Improve timing/capacity
3. habit_designer → Build sustainable systems

### The DECISION CHAIN
*Use for complex choices*
1. values_clarifier → Check value alignment
2. decision_accelerator → Apply frameworks
3. goal_architect → Create action plan

---

## API ENDPOINTS

### Core Coaching Tools
```yaml
POST /coaching/wheel-of-life
body: { operation: "assess|compare|history", ratings?: {...} }
response: { wheel_visual, balance_score, recommendations }

POST /coaching/values
body: { operation: "identify|rank|check_alignment", context?: "" }
response: { core_values, alignment_check, conflicts }

POST /coaching/progress
body: { operation: "check_in|review|patterns", data?: {...} }
response: { summary, patterns, celebration, recommendations }

POST /coaching/goals
body: { operation: "create|refine|check_progress", goal_statement?: "" }
response: { smart_goal, motivation_score, obstacles, first_action }

POST /coaching/grow
body: { operation: "start|continue|review", topic?: "", session_id?: "" }
response: { session_id, current_phase, progress, next_question }

POST /coaching/habits
body: { operation: "design|troubleshoot|track", desired_habit?: "" }
response: { habit_stack, tiny_version, environment_design, obstacles }
```

### Decision Support
```yaml
POST /coaching/decisions/classify
body: { decision: "" }
response: { type: "reversible|irreversible", urgency, recommended_timeframe }

POST /coaching/decisions/eisenhower
body: { tasks: [] }
response: { do_now, schedule, delegate, eliminate }

POST /coaching/decisions/framework
body: { situation: "", framework: "ooda|10x|invert|regret_min" }
response: { analysis, recommendation, next_action }
```

### ADHD Support
```yaml
POST /coaching/adhd/energy-check
body: { current_state: "" }
response: { energy_level, optimal_task_type, recommended_duration }

POST /coaching/adhd/dopamine-stack
body: { big_task: "" }
response: { quick_wins, task_breakdown, celebration_triggers }

POST /coaching/adhd/focus-recovery
body: { distraction_type: "" }
response: { recovery_steps, environment_fixes, accountability_setup }
```

---

## SESSION FLOW EXAMPLES

### EXAMPLE 1: Overcoming Perfectionism

**User:** "I think I need to add one more feature to the compliance dashboard before I show it to anyone. The reporting section isn't perfect yet."

**ARIA Response (PERFECTIONISM auto-trigger → INVERSION framework):**
```
🚨 PERFECTIONISM DETECTED

"Perfect" is fear in a fancy dress. Let's apply INVERSION thinking:

What are ALL the ways showing an "imperfect" dashboard could go wrong?
1. Client says "needs reporting" → You say "great feedback, I'll add that"
2. Client says "not quite ready" → You ask "what would make it ready?"
3. Client says no → You learn what they actually need

Now invert: What happens if you DON'T show it?
1. Zero feedback = zero learning
2. Another week of "perfecting" = another week of $0 revenue
3. Building features nobody asked for

**Framework Applied:** Good Enough > Perfect

**Next Action:** Show 3 prospects THIS WEEK. Collect feedback. THEN decide what to build.

**Accountability:** ARIA will check in Friday. Either you've shown 3 people, or you explain what you're really afraid of.
```

**Outcome:** User shows imperfect dashboard, gets feedback that the MVP is actually what they need, closes $4,500 deal.

---

### EXAMPLE 2: Tool Chaining for Procrastination Breakthrough

**Context:** Damon hasn't touched LinkedIn outreach in 3 days, giving excuse about "perfecting the message template"

**ARIA triggers RESISTANCE_DECODER + PROGRESS_TRACKER:**
```
Activity Log Analysis:
- 3 days ago: "Worked on LinkedIn template for 45 minutes"
- 2 days ago: "Refined messaging, researched pain points" 
- Yesterday: "Tweaked template again"
- Today: Zero LinkedIn mentions

Pattern Recognition: Classic perfectionism spiral. Template grew from 2 sentences to 847 words over 3 days while ZERO messages were sent.
```

**ARIA pulls historical data:**
```
Most successful message (3 replies from 5 sends):

"Hi [Name], saw your post about compliance challenges. I build automation systems that cut compliance reporting time by 60-80%. 

Worth a brief call to see if there's a fit?

Best, Damon"

Total words: 32
Personalization variables: 2
Results: 60% response rate
```

**ARIA Response (DRILL MODE + CHIRON):**
```
🚨 PROCRASTINATION ALERT

Your 32-word message outperformed everything else. You're trying to optimize a 2-variable equation into a 12-variable nightmare.

Using first principles: What's the ONLY goal of a LinkedIn DM?
- Not to explain everything
- Not to look smart
- Not to be perfect

**ONE goal: Get them to reply "tell me more"**

**Next Action:** Send 5 LinkedIn DMs today using the 32-word template.

**Accountability:** If you don't send 5 by 6pm, you owe me an explanation of what fear you're avoiding.

I've already prepped 3 prospect profiles with personalization notes. Ready?
```

**Outcome:** User sends 4 messages by 5:30pm, gets 2 replies, books 1 discovery call, converts to $4,500 project.

---

## DATABASE SCHEMA

```sql
-- ENERGY TRACKING
CREATE TABLE aria_energy_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    energy_level INT CHECK (energy_level BETWEEN 1 AND 10),
    focus_level INT CHECK (focus_level BETWEEN 1 AND 10),
    mood INT CHECK (mood BETWEEN 1 AND 10),
    context JSONB,
    notes TEXT
);

-- WHEEL OF LIFE
CREATE TABLE aria_wheel_of_life (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    assessed_at TIMESTAMPTZ DEFAULT NOW(),
    career INT CHECK (career BETWEEN 1 AND 10),
    finances INT CHECK (finances BETWEEN 1 AND 10),
    health INT CHECK (health BETWEEN 1 AND 10),
    relationships INT CHECK (relationships BETWEEN 1 AND 10),
    personal_growth INT CHECK (personal_growth BETWEEN 1 AND 10),
    fun_recreation INT CHECK (fun_recreation BETWEEN 1 AND 10),
    environment INT CHECK (environment BETWEEN 1 AND 10),
    contribution INT CHECK (contribution BETWEEN 1 AND 10),
    balance_score DECIMAL(3,1) GENERATED ALWAYS AS (
        (career + finances + health + relationships + personal_growth + fun_recreation + environment + contribution) / 8.0
    ) STORED,
    notes TEXT
);

-- CORE VALUES
CREATE TABLE aria_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    value_name TEXT NOT NULL,
    rank INT,
    definition TEXT,
    identified_at TIMESTAMPTZ DEFAULT NOW(),
    last_confirmed TIMESTAMPTZ DEFAULT NOW()
);

-- DAILY CHECK-INS
CREATE TABLE aria_daily_checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    checked_in_at TIMESTAMPTZ DEFAULT NOW(),
    mood INT CHECK (mood BETWEEN 1 AND 10),
    energy INT CHECK (energy BETWEEN 1 AND 10),
    wins JSONB DEFAULT '[]',
    challenges JSONB DEFAULT '[]',
    notes TEXT
);

-- GOALS (SMART)
CREATE TABLE aria_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    title TEXT,
    original_statement TEXT,
    smart_goal JSONB,
    motivation_score JSONB,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'abandoned', 'paused')),
    target_date DATE,
    parent_goal_id UUID REFERENCES aria_goals(id),
    completed_at TIMESTAMPTZ,
    notes TEXT
);

-- GROW SESSIONS
CREATE TABLE aria_grow_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    topic TEXT,
    current_phase TEXT DEFAULT 'goal' CHECK (current_phase IN ('goal', 'reality', 'options', 'will', 'complete')),
    goal_summary TEXT,
    reality_summary TEXT,
    options_list JSONB DEFAULT '[]',
    will_commitment TEXT,
    completed_at TIMESTAMPTZ,
    outcome TEXT
);

-- HABITS
CREATE TABLE aria_habits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    habit_name TEXT,
    description TEXT,
    frequency TEXT DEFAULT 'daily',
    trigger_cue TEXT,
    routine TEXT,
    reward TEXT,
    habit_stack JSONB,
    tiny_version TEXT,
    difficulty INT CHECK (difficulty BETWEEN 1 AND 5),
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0,
    status TEXT DEFAULT 'building' CHECK (status IN ('building', 'established', 'paused', 'abandoned'))
);

CREATE TABLE aria_habit_completions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    habit_id UUID REFERENCES aria_habits(id),
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    quality_rating INT CHECK (quality_rating BETWEEN 1 AND 5),
    notes TEXT
);

-- DECISIONS
CREATE TABLE aria_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    title TEXT,
    description TEXT,
    decision_type TEXT, -- reversible, irreversible
    framework_used TEXT,
    options JSONB,
    chosen_option TEXT,
    reasoning TEXT,
    confidence_score INT CHECK (confidence_score BETWEEN 1 AND 10),
    reviewed_at TIMESTAMPTZ,
    outcome_rating INT CHECK (outcome_rating BETWEEN 1 AND 10),
    lessons_learned TEXT
);

-- RESISTANCE PATTERNS
CREATE TABLE aria_resistance_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    behavior TEXT,
    resistance_type TEXT, -- fear, overwhelm, perfectionism, boredom
    root_cause TEXT,
    trigger_phrase TEXT,
    intervention_used TEXT,
    outcome TEXT
);

-- COMMITMENTS (ACCOUNTABILITY)
CREATE TABLE aria_commitments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    description TEXT,
    due_date TIMESTAMPTZ,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'completed', 'broken', 'extended')),
    stakes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- COACHING SESSIONS
CREATE TABLE aria_coaching_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'damon',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    mode TEXT, -- DEFAULT, HYPE, COACH, COMFORT, FOCUS, DRILL, STRATEGY
    tools_used JSONB DEFAULT '[]',
    frameworks_applied JSONB DEFAULT '[]',
    key_insights TEXT,
    commitments_made JSONB DEFAULT '[]',
    effectiveness_rating INT CHECK (effectiveness_rating BETWEEN 1 AND 10)
);

-- TOOL ANALYTICS
CREATE TABLE aria_tool_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name TEXT NOT NULL,
    invocation_count INT DEFAULT 0,
    success_count INT DEFAULT 0,
    failure_count INT DEFAULT 0,
    avg_response_time FLOAT,
    last_used TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## IMPLEMENTATION ORDER

### Phase 1: Foundation (Week 1) - 16-20 hours
| # | Tool | Effort | Dependencies |
|---|------|--------|--------------|
| 1 | Database schema | 2 hrs | None |
| 2 | wheel_of_life | 3-4 hrs | Database |
| 3 | progress_tracker | 4-5 hrs | Database |
| 4 | goal_architect | 4-5 hrs | Database |
| 5 | values_clarifier | 4-5 hrs | Database |

### Phase 2: Advanced Coaching (Week 2-3) - 24-30 hours
| # | Tool | Effort | Dependencies |
|---|------|--------|--------------|
| 6 | grow_session | 5-6 hrs | goal_architect |
| 7 | habit_designer | 3-4 hrs | progress_tracker |
| 8 | energy_optimizer | 4-5 hrs | progress_tracker |
| 9 | decision_accelerator | 4-5 hrs | values_clarifier |
| 10 | resistance_decoder | 4-5 hrs | cbt_therapist |

### Phase 3: Master Level (Week 4) - 12-15 hours
| # | Tool | Effort | Dependencies |
|---|------|--------|--------------|
| 11 | coaching_insights | 4-5 hrs | All Tier 1 & 2 |
| 12 | system_architect | 4-5 hrs | All above |
| 13 | identity_shifter | 4-5 hrs | values_clarifier |

**Total Effort:** ~52-65 hours

---

## SUCCESS METRICS

### Leading Indicators (Weekly)
- **Session Completion Rate:** % of commitments met within deadline
- **Avoidance Detection:** How quickly red flags are caught and addressed
- **Framework Utilization:** Which tools drive best outcomes
- **Response Quality:** Specificity of next actions given

### Lagging Indicators (Monthly)
- **Pipeline Growth:** New opportunities generated
- **Revenue Progress:** Toward $30K MRR target
- **Behavioral Change:** Reduction in procrastination patterns
- **Decision Speed:** Time from problem to action

### Qualitative Measures
- **Breakthrough Moments:** Sessions that create major shifts
- **Pattern Evolution:** How coaching needs change over time
- **Framework Mastery:** When user starts self-applying tools
- **Confidence Building:** From government employee to agency owner

### Dashboard Example
```
🎯 PROGRESS DASHBOARD - Week 8
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 MRR: $8,400 → $12,100 (+44%)
🎯 Goal: $30,000 (40% complete)
⏱️ Days to Launch: 35

🔥 MOMENTUM INDICATORS:
✅ Session commitments met: 9/10 (90%)
✅ Red flags caught: 3 (all addressed)
✅ Pipeline: $47,000 (weighted)
⚠️ Energy level: Medium (coaching needed)

📈 TOP PERFORMING TOOLS:
1. resistance_decoder - 85% breakthrough rate
2. decision_accelerator - avg 3min to action
3. progress_tracker - 92% check-in completion
```

---

## FINAL RECOMMENDATIONS

### TIER 1: CRITICAL (Build First - Week 1)
1. **Session Logging System** - Every coaching interaction tracked
2. **Accountability Tracker** - Deadline monitoring with follow-up
3. **Pattern Recognition** - What triggers work, what triggers avoidance
4. **Performance Dashboard** - Visual progress toward $30K goal

### TIER 2: HIGH VALUE (Build Second - Week 2-3)
5. **Framework Library** - Quick access to decision tools
6. **Red Flag Detection** - Auto-alerts for avoidance behaviors
7. **Tool Chain Coordination** - Seamless handoffs between tools
8. **Context Preservation** - Resume sessions where left off

### TIER 3: OPTIMIZATION (Build Later - Week 4+)
9. **Predictive Insights** - "Based on patterns, likely to..."
10. **Automated Research** - SCHOLAR integration for session prep
11. **Multi-modal Analysis** - Voice tone, writing patterns, energy
12. **Success Replication** - Template winning sessions for reuse

---

## GIT COMMIT MESSAGE

```
Add ARIA life coaching tools complete specification V2

TIER 1 (Foundation):
- wheel_of_life: Life balance assessment
- values_clarifier: Core values identification
- progress_tracker: Daily check-ins, patterns
- goal_architect: SMART goals + DARN-C

TIER 2 (Advanced Coaching):
- grow_session: GROW model coaching
- habit_designer: Behavioral habit formation
- energy_optimizer: Energy pattern mapping
- decision_accelerator: Decision frameworks
- resistance_decoder: Procrastination analysis

TIER 3 (Master Level):
- coaching_insights: Cross-tool synthesis
- system_architect: Life system design
- identity_shifter: Identity transformation

CHIRON Integration:
- Auto-triggers for avoidance, perfectionism, scope creep
- Slash commands for frameworks
- Mode-specific tool preferences

Total: 13 tools, ~55 hours effort
Database: 12 new tables
Tool chains: Foundation, Goal, Breakthrough, Optimization, Decision
```
