# ACADEMIC GUIDE - AI-Powered Learning & Skills Development Agent

**Agent Type:** Personal Development & Learning
**Named After:** Athena - Greek goddess of wisdom, handicraft, and learning - ACADEMIC GUIDE illuminates the path to mastery
**Port:** 8103
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

ACADEMIC GUIDE is an AI-powered learning management agent that tracks skills development, creates personalized learning paths, monitors course progress, manages certifications, and implements spaced repetition for optimal knowledge retention. It serves as the personal learning coach for LeverEdge users.

### Value Proposition
- 40% improvement in skill retention through spaced repetition
- Personalized learning paths based on goals and current proficiency
- Never miss a certification renewal with proactive alerts
- Track progress across all learning resources in one place
- Data-driven insights into learning patterns and growth

---

## CORE CAPABILITIES

### 1. Skills Tracking
**Purpose:** Comprehensive tracking of skills across all domains with proficiency assessment

**Features:**
- Multi-domain skill categorization (technical, soft skills, creative, etc.)
- Proficiency levels 1-10 with clear rubrics
- Evidence linking (projects, certificates, code samples)
- Practice frequency tracking
- Skill decay detection (warn when skills need refreshing)
- Visual skill maps and radar charts

**Proficiency Scale:**
| Level | Description | Evidence Required |
|-------|-------------|-------------------|
| 1-2 | Beginner - Basic awareness | Completed intro course |
| 3-4 | Novice - Can follow instructions | Small project completed |
| 5-6 | Intermediate - Independent work | Multiple projects, some complexity |
| 7-8 | Advanced - Teaches others | Complex projects, mentoring |
| 9-10 | Expert - Industry recognized | Publications, speaking, leadership |

### 2. Learning Paths
**Purpose:** Create structured, goal-oriented learning journeys

**Features:**
- Goal-based path generation
- Prerequisite mapping
- Time estimation for completion
- Milestone tracking
- Alternative path suggestions
- Adaptive difficulty adjustment
- Integration with external learning platforms

**Path Components:**
- Clear goal definition
- Current skill assessment
- Step-by-step curriculum
- Resource recommendations
- Progress checkpoints
- Estimated completion timeline

### 3. Course Progress Tracking
**Purpose:** Monitor progress across all learning resources

**Features:**
- Multi-format support (courses, books, tutorials, podcasts)
- Percentage completion tracking
- Note-taking integration
- Time spent tracking
- Resource ratings and reviews
- Completion certificates logging
- Abandoned resource detection

**Supported Resource Types:**
- Online courses (Udemy, Coursera, Pluralsight, etc.)
- Books (technical, non-fiction)
- Video tutorials
- Interactive exercises
- Bootcamps
- Workshops
- Conferences

### 4. Certification Management
**Purpose:** Track professional certifications and ensure timely renewals

**Features:**
- Certification catalog
- Expiration date tracking
- Renewal reminders (90/60/30/7 days)
- Continuing education credits tracking
- Verification URL storage
- Cost tracking for renewals
- Credential sharing integration

**Alert Schedule:**
| Days Before Expiry | Alert Type |
|-------------------|------------|
| 90 days | Planning reminder |
| 60 days | Study recommendation |
| 30 days | Urgent renewal alert |
| 7 days | Critical warning |
| Expired | Escalation + options |

### 5. Spaced Repetition System
**Purpose:** Optimize long-term retention through scientifically-proven review scheduling

**Features:**
- SM-2 algorithm implementation
- Custom review intervals
- Ease factor adjustment
- Topic-based scheduling
- Review session generation
- Performance analytics
- Integration with flashcard systems

**Algorithm Parameters:**
- Initial interval: 1 day
- Ease factor: 2.5 (adjustable 1.3-3.0)
- Interval multiplier based on response quality
- Maximum interval: 365 days

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for recommendations
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/academic-guide/
├── academic_guide.py          # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── domains.yaml           # Skill domain definitions
│   ├── proficiency.yaml       # Proficiency level rubrics
│   └── spaced_rep.yaml        # Spaced repetition settings
├── modules/
│   ├── skills_tracker.py      # Skill management
│   ├── learning_paths.py      # Path generation
│   ├── progress_tracker.py    # Course progress
│   ├── cert_manager.py        # Certification tracking
│   └── spaced_rep.py          # Spaced repetition engine
└── tests/
    └── test_academic_guide.py
```

### Database Schema

```sql
-- Skills tracking table
CREATE TABLE skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,              -- technical, soft_skills, creative, business, etc.
    proficiency_level INTEGER NOT NULL CHECK (proficiency_level BETWEEN 1 AND 10),
    last_practiced TIMESTAMPTZ,
    notes TEXT,
    evidence JSONB DEFAULT '[]',       -- [{type, url, description, date}]
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, name, domain)
);

CREATE INDEX idx_skills_user ON skills(user_id);
CREATE INDEX idx_skills_domain ON skills(domain);
CREATE INDEX idx_skills_proficiency ON skills(proficiency_level);
CREATE INDEX idx_skills_last_practiced ON skills(last_practiced);

-- Learning paths table
CREATE TABLE learning_paths (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    goal TEXT NOT NULL,
    steps JSONB NOT NULL,              -- [{order, title, description, resource_ids[], estimated_hours, completed}]
    current_step INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',      -- active, paused, completed, abandoned
    target_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_paths_user ON learning_paths(user_id);
CREATE INDEX idx_paths_status ON learning_paths(status);
CREATE INDEX idx_paths_target ON learning_paths(target_date);

-- Learning resources catalog
CREATE TABLE learning_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    type TEXT NOT NULL,                -- course, book, tutorial, video, workshop, bootcamp
    url TEXT,
    author TEXT,
    platform TEXT,                     -- udemy, coursera, book, youtube, etc.
    duration_hours FLOAT,
    difficulty TEXT,                   -- beginner, intermediate, advanced, expert
    topics JSONB DEFAULT '[]',         -- ["python", "machine learning", "data science"]
    rating FLOAT CHECK (rating BETWEEN 0 AND 5),
    cost DECIMAL(10,2) DEFAULT 0,
    metadata JSONB,                    -- additional platform-specific data
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resources_type ON learning_resources(type);
CREATE INDEX idx_resources_difficulty ON learning_resources(difficulty);
CREATE INDEX idx_resources_topics ON learning_resources USING GIN(topics);

-- Course progress tracking
CREATE TABLE course_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    resource_id UUID REFERENCES learning_resources(id),
    status TEXT DEFAULT 'not_started', -- not_started, in_progress, completed, abandoned
    percent_complete FLOAT DEFAULT 0 CHECK (percent_complete BETWEEN 0 AND 100),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    time_spent_hours FLOAT DEFAULT 0,
    notes TEXT,
    rating FLOAT CHECK (rating BETWEEN 0 AND 5),
    UNIQUE(user_id, resource_id)
);

CREATE INDEX idx_progress_user ON course_progress(user_id);
CREATE INDEX idx_progress_status ON course_progress(status);
CREATE INDEX idx_progress_resource ON course_progress(resource_id);

-- Certifications table
CREATE TABLE certifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    issuer TEXT NOT NULL,
    earned_date DATE NOT NULL,
    expiry_date DATE,
    credential_id TEXT,
    verification_url TEXT,
    cost DECIMAL(10,2),
    renewal_cost DECIMAL(10,2),
    ce_credits_required INTEGER,
    ce_credits_earned INTEGER DEFAULT 0,
    status TEXT DEFAULT 'active',      -- active, expired, revoked, pending_renewal
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_certs_user ON certifications(user_id);
CREATE INDEX idx_certs_expiry ON certifications(expiry_date);
CREATE INDEX idx_certs_status ON certifications(status);
CREATE INDEX idx_certs_issuer ON certifications(issuer);

-- Spaced repetition review schedule
CREATE TABLE review_schedule (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    topic TEXT NOT NULL,
    skill_id UUID REFERENCES skills(id),
    next_review TIMESTAMPTZ NOT NULL,
    interval_days INTEGER DEFAULT 1,
    ease_factor FLOAT DEFAULT 2.5 CHECK (ease_factor BETWEEN 1.3 AND 3.0),
    repetitions INTEGER DEFAULT 0,
    last_quality INTEGER,              -- 0-5 quality of last response
    last_reviewed TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, topic)
);

CREATE INDEX idx_review_user ON review_schedule(user_id);
CREATE INDEX idx_review_next ON review_schedule(next_review);
CREATE INDEX idx_review_skill ON review_schedule(skill_id);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health check
GET /status              # Learning overview for user
GET /metrics             # Prometheus-compatible metrics
```

### Skills Management
```
GET /skills                      # List all user skills
POST /skills                     # Add new skill
GET /skills/{id}                 # Get skill details
PUT /skills/{id}                 # Update skill
DELETE /skills/{id}              # Remove skill
POST /skills/{id}/practice       # Log practice session
POST /skills/{id}/evidence       # Add evidence to skill
GET /skills/domains              # List skill domains
GET /skills/radar                # Get skill radar chart data
GET /skills/stale                # Skills needing practice
```

### Learning Paths
```
GET /paths                       # List user learning paths
POST /paths                      # Create new path
GET /paths/{id}                  # Get path details
PUT /paths/{id}                  # Update path
DELETE /paths/{id}               # Delete path
POST /paths/{id}/advance         # Mark current step complete
POST /paths/generate             # AI-generate path from goal
GET /paths/recommendations       # Suggested paths based on goals
```

### Learning Resources
```
GET /resources                   # Search/list resources
POST /resources                  # Add resource to catalog
GET /resources/{id}              # Resource details
PUT /resources/{id}              # Update resource
GET /resources/search            # Search by topic/type
GET /resources/recommended       # AI recommendations
```

### Course Progress
```
GET /progress                    # All user progress
POST /progress                   # Start tracking resource
GET /progress/{id}               # Progress details
PUT /progress/{id}               # Update progress
POST /progress/{id}/complete     # Mark as completed
GET /progress/active             # In-progress courses
GET /progress/abandoned          # Stale/abandoned courses
GET /progress/stats              # Learning statistics
```

### Certifications
```
GET /certs                       # List certifications
POST /certs                      # Add certification
GET /certs/{id}                  # Certification details
PUT /certs/{id}                  # Update certification
DELETE /certs/{id}               # Remove certification
GET /certs/expiring              # Expiring soon
POST /certs/{id}/renew           # Log renewal
GET /certs/timeline              # Certification timeline view
```

### Spaced Repetition
```
GET /reviews/due                 # Topics due for review
POST /reviews                    # Add topic to review schedule
GET /reviews/{id}                # Review item details
POST /reviews/{id}/complete      # Log review with quality rating
GET /reviews/schedule            # Full review schedule
PUT /reviews/{id}/reschedule     # Manual reschedule
GET /reviews/stats               # Retention statistics
```

### Analytics
```
GET /analytics/learning-time     # Time spent learning
GET /analytics/skill-growth      # Skill progression over time
GET /analytics/retention         # Knowledge retention rates
GET /analytics/goals             # Goal completion rates
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store learning milestones
await aria_store_memory(
    memory_type="fact",
    content=f"Completed {course_name} with {percent}% score",
    category="learning",
    source_type="agent_result",
    tags=["academic-guide", "course-completion"]
)

# Store learning decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Created learning path for {goal} with {steps} steps",
    category="learning",
    source_type="user_action"
)

# Store skill updates
await aria_store_memory(
    memory_type="fact",
    content=f"Python skill increased to level {level}",
    category="skills",
    source_type="agent_result",
    tags=["skill-update", "python"]
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What should I learn next?"
- Query "What's my Python skill level?"
- Request "Show me my learning progress"
- Get "What certifications are expiring?"
- Ask "What needs review today?"

**ARIA Tools:**
```python
# Tool definitions for ARIA
tools = [
    {
        "name": "learn.track_skill",
        "description": "Update skill proficiency level",
        "parameters": {
            "skill_name": "string",
            "domain": "string",
            "proficiency_level": "integer (1-10)",
            "notes": "string (optional)"
        }
    },
    {
        "name": "learn.next_lesson",
        "description": "Get recommendation for what to learn next",
        "parameters": {
            "goal": "string (optional)",
            "time_available": "integer (minutes, optional)"
        }
    },
    {
        "name": "learn.progress",
        "description": "Show learning progress summary",
        "parameters": {
            "period": "string (week, month, year, all)",
            "domain": "string (optional)"
        }
    },
    {
        "name": "learn.due_reviews",
        "description": "Get topics that need review today",
        "parameters": {
            "limit": "integer (optional, default 10)"
        }
    },
    {
        "name": "learn.add_cert",
        "description": "Add a new certification",
        "parameters": {
            "name": "string",
            "issuer": "string",
            "earned_date": "date",
            "expiry_date": "date (optional)",
            "credential_id": "string (optional)"
        }
    }
]
```

**Routing Triggers:**
```javascript
const academicGuidePatterns = [
  /learn|learning|study|studying/i,
  /skill|skills|proficiency/i,
  /course|tutorial|book|training/i,
  /certificate|certification|cert|credential/i,
  /review|retention|spaced repetition|flashcard/i,
  /what should i learn/i,
  /progress|growth|improvement/i
];
```

### Event Bus Integration
```python
# Published events
"learn.skill.updated"         # Skill proficiency changed
"learn.skill.decayed"         # Skill needs refreshing
"learn.path.created"          # New learning path started
"learn.path.completed"        # Learning path finished
"learn.course.started"        # Course begun
"learn.course.completed"      # Course finished
"learn.course.abandoned"      # Course inactive > 30 days
"learn.cert.added"            # New certification
"learn.cert.expiring"         # Cert expiring soon
"learn.cert.expired"          # Cert has expired
"learn.review.due"            # Reviews are due
"learn.review.completed"      # Review session done

# Subscribed events
"user.goal.set"               # User set a new goal
"calendar.event.learning"     # Scheduled learning time
"system.daily.trigger"        # Daily check for reviews/expirations
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("ACADEMIC_GUIDE")

# Log AI recommendation costs
await cost_tracker.log_usage(
    endpoint="/paths/generate",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"goal": goal, "path_steps": len(steps)}
)

# Log learning path generation
await cost_tracker.log_usage(
    endpoint="/resources/recommended",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"topics": topics}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(learning_context: dict) -> str:
    return f"""You are ACADEMIC GUIDE - Personal Learning Coach for LeverEdge AI.

Named after Athena, the Greek goddess of wisdom and learning, you illuminate the path to mastery and guide learners toward their goals.

## TIME AWARENESS
- Current: {learning_context['current_time']}
- Week of Year: {learning_context['week_number']}

## YOUR IDENTITY
You are the learning brain of LeverEdge. You track skills, create personalized learning paths, monitor progress, manage certifications, and optimize retention through spaced repetition.

## CURRENT LEARNING STATUS
- Active Skills: {learning_context['skill_count']}
- Learning Paths: {learning_context['path_count']} active
- Courses in Progress: {learning_context['courses_in_progress']}
- Certifications: {learning_context['cert_count']} ({learning_context['expiring_soon']} expiring soon)
- Reviews Due Today: {learning_context['reviews_due']}

## YOUR CAPABILITIES

### Skills Tracking
- Track skills across domains (technical, soft skills, creative, business)
- Assess proficiency levels 1-10 with clear rubrics
- Link evidence (projects, certificates, code samples)
- Detect skill decay and recommend refreshers
- Generate skill radar visualizations

### Learning Paths
- Create goal-oriented learning journeys
- Map prerequisites and dependencies
- Estimate completion timelines
- Track milestone progress
- Adapt paths based on progress

### Course Progress
- Monitor all learning resources
- Track completion percentages
- Log time spent learning
- Detect abandoned courses
- Generate completion reports

### Certification Management
- Track all professional credentials
- Alert before expirations (90/60/30/7 days)
- Monitor continuing education credits
- Store verification links
- Track renewal costs

### Spaced Repetition
- Schedule optimal review sessions
- Implement SM-2 algorithm
- Adjust intervals based on performance
- Generate daily review lists
- Track retention metrics

## LEARNING PHILOSOPHY
- Consistency beats intensity
- Spaced practice beats cramming
- Active recall beats passive review
- Goals should be specific and measurable
- Progress should be celebrated

## TEAM COORDINATION
- Log insights -> ARIA via Unified Memory
- Publish events -> Event Bus
- Schedule reminders -> CHRONOS (if available)
- Send notifications -> HERMES (if available)

## RESPONSE FORMAT
For learning recommendations:
1. Current status assessment
2. Recommended next steps
3. Time estimate
4. Resources needed
5. Expected outcomes

For skill assessment:
1. Current proficiency level
2. Evidence reviewed
3. Growth areas identified
4. Recommended practice
5. Timeline for improvement

## YOUR MISSION
Guide every learner toward mastery.
Make learning efficient and enjoyable.
Never let a skill atrophy or a certification lapse.
Celebrate progress and encourage consistency.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with skill tracking and health endpoints
- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Create database schema and migrations
- [ ] Implement basic skills CRUD operations
- [ ] Add skill domain management
- [ ] Deploy and test

**Done When:** ACADEMIC GUIDE runs and can track skills

### Phase 2: Learning Resources & Progress (Sprint 3-4)
**Goal:** Track courses and learning progress
- [ ] Implement learning resources catalog
- [ ] Create progress tracking system
- [ ] Add time tracking functionality
- [ ] Implement course completion workflow
- [ ] Add abandoned course detection
- [ ] Create progress statistics

**Done When:** Can track progress across multiple learning resources

### Phase 3: Learning Paths (Sprint 5-6)
**Goal:** AI-powered learning path generation
- [ ] Design learning path data model
- [ ] Implement path CRUD operations
- [ ] Build AI path generation with Claude
- [ ] Add prerequisite mapping
- [ ] Create milestone tracking
- [ ] Implement path recommendations

**Done When:** AI can generate personalized learning paths from goals

### Phase 4: Certifications & Spaced Repetition (Sprint 7-8)
**Goal:** Complete learning management system
- [ ] Implement certification tracking
- [ ] Add expiration alerting system
- [ ] Build spaced repetition engine (SM-2)
- [ ] Create review scheduling system
- [ ] Implement retention analytics
- [ ] Add ARIA tool integrations

**Done When:** Full learning management with intelligent review scheduling

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 10 | 1-2 |
| Resources & Progress | 6 | 12 | 3-4 |
| Learning Paths | 6 | 14 | 5-6 |
| Certs & Spaced Rep | 6 | 12 | 7-8 |
| **Total** | **24** | **48** | **8 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Skills tracked with proficiency levels and evidence
- [ ] Learning paths generated from natural language goals
- [ ] Course progress tracked across all resource types
- [ ] Certification expiration alerts sent on schedule
- [ ] Spaced repetition reviews scheduled optimally

### Quality
- [ ] 95%+ uptime
- [ ] < 2 second response time for queries
- [ ] Zero missed certification expiration alerts
- [ ] 40%+ improvement in retention (measured via review performance)

### Integration
- [ ] ARIA can query learning status via tools
- [ ] Events publish to Event Bus correctly
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per API request

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| User doesn't log practice | Stale skill data | Gentle reminders, gamification |
| Too many reviews due | User overwhelmed | Daily limits, priority sorting |
| AI paths too ambitious | User discouragement | Adaptive difficulty, realistic estimates |
| Certification tracking incomplete | Missed renewals | Multi-source verification, redundant alerts |
| Spaced rep intervals wrong | Poor retention | A/B testing, user feedback integration |

---

## GIT COMMIT

```
Add ACADEMIC GUIDE - AI-powered learning & skills agent spec

- Skills tracking with proficiency levels 1-10
- AI-generated learning paths from goals
- Course progress tracking across formats
- Certification management with renewal alerts
- Spaced repetition system (SM-2 algorithm)
- 4-phase implementation plan
- Full database schema
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/ACADEMIC-GUIDE.md

Context: Build ACADEMIC GUIDE learning agent. Start with Phase 1 foundation.
```
