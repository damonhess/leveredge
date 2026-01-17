# HERACLES - AI-Powered Project Management Agent

**Agent Type:** Business Operations
**Named After:** Heracles (Hercules) - the legendary hero who completed the 12 labors through meticulous planning, resource management, and relentless execution
**Port:** 8200
**Status:** PLANNED

---

## EXECUTIVE SUMMARY

HERACLES is an AI-powered project management agent providing sprint planning, task breakdown, time tracking, velocity measurement, and external PM tool integration. It serves as the central project coordination brain for LeverEdge operations and can be deployed for client project management needs.

### Value Proposition
- 40% reduction in sprint planning overhead
- Real-time velocity tracking for accurate forecasting
- Automated task breakdown from epics to actionable work items
- Seamless sync with OpenProject/Leantime for enterprise compatibility
- Premium pricing tier ($5K-15K deployments)

---

## CORE CAPABILITIES

### 1. Sprint Planning Engine
**Purpose:** AI-assisted sprint creation with capacity planning and goal setting

**Features:**
- Sprint goal definition with measurable outcomes
- Team capacity calculation (hours available)
- Task assignment based on skills and availability
- Sprint backlog prioritization using AI
- Velocity-based sprint capacity recommendations
- Risk identification for overcommitted sprints

**Sprint States:**
| State | Description | Actions Available |
|-------|-------------|-------------------|
| Planning | Sprint being defined | Add tasks, set capacity, define goals |
| Active | Sprint in progress | Update tasks, log time, track progress |
| Review | Sprint ending | Generate reports, calculate velocity |
| Completed | Sprint finished | Archive, analyze performance |
| Cancelled | Sprint aborted | Document reasons, redistribute tasks |

### 2. Task Breakdown System
**Purpose:** Hierarchical work decomposition from epics to actionable tasks

**Features:**
- Epic to story decomposition with AI assistance
- Story to task breakdown with estimates
- Dependency mapping between tasks
- Automatic subtask generation for complex items
- Template-based task creation for common patterns
- Acceptance criteria generation

**Hierarchy:**
```
Epic (large initiative, multi-sprint)
  └── Story (user-facing feature, single sprint)
        └── Task (actionable work item, hours)
              └── Subtask (granular step, minutes to hours)
```

### 3. OpenProject/Leantime Integration
**Purpose:** Bidirectional sync with enterprise project management tools

**Features:**
- Project structure synchronization
- Task/issue import and export
- Status mapping between systems
- Time entry synchronization
- Automatic conflict resolution
- Webhook-based real-time updates

**Supported Integrations:**
| Tool | Sync Direction | Features |
|------|---------------|----------|
| OpenProject | Bidirectional | Projects, work packages, time entries |
| Leantime | Bidirectional | Projects, tasks, time tracking |
| Jira | Import | Issues, sprints (future) |
| Linear | Import | Issues, cycles (future) |

### 4. Time Tracking System
**Purpose:** Accurate time logging with automatic calculations and reporting

**Features:**
- Manual time entry with notes
- Timer-based tracking (start/stop)
- Automatic rounding rules
- Billable vs non-billable categorization
- Time approval workflows
- Weekly timesheets generation

**Tracking Modes:**
- **Manual:** Enter hours after completion
- **Timer:** Start/stop clock for real-time tracking
- **Automatic:** AI-estimated based on task completion (optional)

### 5. Velocity Tracking Engine
**Purpose:** Sprint velocity measurement and forecasting

**Features:**
- Story point velocity calculation
- Hours-based velocity tracking
- Rolling average velocity (3/5/10 sprints)
- Team performance trends
- Individual contribution metrics
- Forecast accuracy tracking

**Metrics Calculated:**
- Committed vs Completed points/hours
- Sprint burndown rate
- Cycle time per task type
- Lead time from creation to completion
- Throughput trends

---

## TECHNICAL ARCHITECTURE

### Stack
```
Framework: FastAPI (Python 3.11+)
Database: PostgreSQL (Supabase)
Message Queue: Event Bus (Port 8099)
ML/AI: Claude API for task breakdown and planning
Container: Docker
```

### Directory Structure
```
/opt/leveredge/control-plane/agents/heracles/
├── heracles.py              # Main FastAPI application
├── Dockerfile
├── requirements.txt
├── config/
│   ├── integrations.yaml    # External PM tool configs
│   ├── templates.yaml       # Task templates
│   └── metrics.yaml         # Velocity calculation rules
├── modules/
│   ├── sprint_planner.py    # Sprint planning logic
│   ├── task_breakdown.py    # AI-powered task decomposition
│   ├── time_tracker.py      # Time entry management
│   ├── velocity_engine.py   # Velocity calculations
│   ├── sync_manager.py      # External tool synchronization
│   └── report_generator.py  # Sprint and project reports
└── tests/
    └── test_heracles.py
```

### Database Schema

```sql
-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active',       -- active, on_hold, completed, cancelled
    start_date DATE,
    target_date DATE,
    owner TEXT NOT NULL,
    settings JSONB DEFAULT '{}',        -- project-specific settings
    metadata JSONB DEFAULT '{}',        -- custom fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_owner ON projects(owner);

-- Sprints table
CREATE TABLE sprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    goal TEXT,                          -- sprint goal/objective
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'planning',     -- planning, active, review, completed, cancelled
    capacity_hours FLOAT DEFAULT 0,     -- team capacity in hours
    committed_points FLOAT DEFAULT 0,   -- story points committed
    completed_points FLOAT DEFAULT 0,   -- story points completed
    velocity FLOAT,                     -- calculated at sprint end
    retrospective JSONB,                -- sprint retro notes
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sprints_project ON sprints(project_id);
CREATE INDEX idx_sprints_status ON sprints(status);
CREATE INDEX idx_sprints_dates ON sprints(start_date, end_date);

-- Tasks table (hierarchical)
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sprint_id UUID REFERENCES sprints(id) ON DELETE SET NULL,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES tasks(id) ON DELETE CASCADE,  -- for subtasks
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT DEFAULT 'task',      -- epic, story, task, subtask, bug
    status TEXT DEFAULT 'todo',         -- todo, in_progress, review, done, blocked
    priority TEXT DEFAULT 'medium',     -- critical, high, medium, low
    estimate_hours FLOAT,               -- estimated hours
    actual_hours FLOAT DEFAULT 0,       -- logged hours
    story_points FLOAT,                 -- for stories/epics
    assignee TEXT,
    labels TEXT[],                      -- tags/labels
    due_date DATE,
    blocked_by UUID[],                  -- dependency tracking
    acceptance_criteria JSONB,          -- definition of done
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_tasks_sprint ON tasks(sprint_id);
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_tasks_parent ON tasks(parent_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assignee ON tasks(assignee);
CREATE INDEX idx_tasks_type ON tasks(task_type);

-- Time entries table
CREATE TABLE time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    date DATE NOT NULL,
    hours FLOAT NOT NULL,
    notes TEXT,
    billable BOOLEAN DEFAULT TRUE,
    approved BOOLEAN DEFAULT FALSE,
    approved_by TEXT,
    timer_started TIMESTAMPTZ,          -- for timer mode
    timer_stopped TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_time_task ON time_entries(task_id);
CREATE INDEX idx_time_user ON time_entries(user_id);
CREATE INDEX idx_time_date ON time_entries(date);

-- External sync tracking
CREATE TABLE external_sync (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    external_system TEXT NOT NULL,      -- openproject, leantime, jira
    external_id TEXT NOT NULL,          -- ID in external system
    entity_type TEXT NOT NULL,          -- project, task, time_entry
    local_entity_id UUID,               -- local ID reference
    last_sync TIMESTAMPTZ DEFAULT NOW(),
    sync_status TEXT DEFAULT 'synced',  -- synced, pending, error, conflict
    sync_direction TEXT,                -- inbound, outbound, bidirectional
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sync_project ON external_sync(project_id);
CREATE INDEX idx_sync_external ON external_sync(external_system, external_id);
CREATE INDEX idx_sync_status ON external_sync(sync_status);
CREATE UNIQUE INDEX idx_sync_unique ON external_sync(external_system, external_id, entity_type);

-- Velocity history for tracking
CREATE TABLE velocity_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    sprint_id UUID REFERENCES sprints(id) ON DELETE CASCADE,
    velocity_points FLOAT,
    velocity_hours FLOAT,
    committed_points FLOAT,
    completed_points FLOAT,
    committed_hours FLOAT,
    completed_hours FLOAT,
    team_size INT,
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_velocity_project ON velocity_history(project_id);
CREATE INDEX idx_velocity_sprint ON velocity_history(sprint_id);
```

---

## API ENDPOINTS

### Health & Status
```
GET /health              # Agent health + project overview
GET /status              # Current sprints and project status
GET /metrics             # Prometheus-compatible metrics
```

### Project Management
```
POST /projects           # Create new project
GET /projects            # List all projects
GET /projects/{id}       # Get project details
PUT /projects/{id}       # Update project
DELETE /projects/{id}    # Archive project
GET /projects/{id}/summary   # Project summary with metrics
```

### Sprint Management
```
POST /sprints            # Create new sprint
GET /sprints             # List sprints (filter by project, status)
GET /sprints/{id}        # Get sprint details
PUT /sprints/{id}        # Update sprint
POST /sprints/{id}/start # Start a sprint
POST /sprints/{id}/complete  # Complete a sprint
GET /sprints/{id}/burndown   # Get burndown chart data
GET /sprints/{id}/report     # Full sprint report
```

### Task Management
```
POST /tasks              # Create task
GET /tasks               # List tasks (filter by sprint, project, status)
GET /tasks/{id}          # Get task details
PUT /tasks/{id}          # Update task
DELETE /tasks/{id}       # Delete task
POST /tasks/{id}/breakdown   # AI-breakdown into subtasks
POST /tasks/{id}/move    # Move task to different sprint
GET /tasks/{id}/history  # Task change history
```

### Time Tracking
```
POST /time               # Log time entry
GET /time                # List time entries (filter by task, user, date)
PUT /time/{id}           # Update time entry
DELETE /time/{id}        # Delete time entry
POST /time/timer/start   # Start timer for task
POST /time/timer/stop    # Stop timer
GET /time/summary        # Time summary report
GET /time/timesheet      # Weekly timesheet
```

### Velocity & Analytics
```
GET /velocity            # Current velocity metrics
GET /velocity/history    # Velocity over time
GET /velocity/forecast   # Forecast based on velocity
GET /analytics/cycle-time    # Cycle time analysis
GET /analytics/throughput    # Throughput metrics
GET /analytics/team          # Team performance metrics
```

### External Sync
```
POST /sync/connect       # Connect to external PM tool
GET /sync/status         # Sync status overview
POST /sync/trigger       # Trigger manual sync
GET /sync/conflicts      # List sync conflicts
POST /sync/resolve       # Resolve sync conflict
DELETE /sync/{id}        # Disconnect integration
```

---

## INTEGRATION REQUIREMENTS

### Unified Memory Integration
```python
# Store project insights
await aria_store_memory(
    memory_type="fact",
    content=f"Sprint velocity: {velocity} points/sprint (3-sprint average)",
    category="project_management",
    source_type="agent_result",
    tags=["heracles", "velocity", project_name]
)

# Store project decisions
await aria_store_memory(
    memory_type="decision",
    content=f"Sprint {sprint_name} capacity set to {capacity} hours based on team availability",
    category="project_management",
    source_type="automated"
)

# Store project learnings
await aria_store_memory(
    memory_type="lesson",
    content=f"Team consistently over-commits by 20% - adjust capacity factor",
    category="project_management",
    source_type="analysis"
)
```

### ARIA Awareness
ARIA should be able to:
- Ask "What's the sprint status?"
- Request "Create a sprint for next week"
- Query "How much time was logged yesterday?"
- Get "What's our velocity trend?"
- Request "Break down this epic into tasks"

**ARIA Tool Definitions:**
```python
# Tool: pm.create_sprint
{
    "name": "pm.create_sprint",
    "description": "Create a new sprint for a project with goals and capacity",
    "parameters": {
        "project_id": "UUID of the project",
        "name": "Sprint name",
        "goal": "Sprint goal/objective",
        "start_date": "Start date (YYYY-MM-DD)",
        "end_date": "End date (YYYY-MM-DD)",
        "capacity_hours": "Team capacity in hours"
    }
}

# Tool: pm.add_task
{
    "name": "pm.add_task",
    "description": "Add a new task to a sprint or project backlog",
    "parameters": {
        "title": "Task title",
        "description": "Task description",
        "sprint_id": "Optional sprint ID",
        "project_id": "Project ID",
        "task_type": "epic|story|task|subtask|bug",
        "estimate_hours": "Estimated hours",
        "priority": "critical|high|medium|low",
        "assignee": "Optional assignee"
    }
}

# Tool: pm.task_status
{
    "name": "pm.task_status",
    "description": "Update the status of a task",
    "parameters": {
        "task_id": "Task UUID",
        "status": "todo|in_progress|review|done|blocked",
        "notes": "Optional status update notes"
    }
}

# Tool: pm.sprint_report
{
    "name": "pm.sprint_report",
    "description": "Get sprint progress report with burndown and metrics",
    "parameters": {
        "sprint_id": "Sprint UUID",
        "include_tasks": "Include task details (default: true)",
        "include_time": "Include time entries (default: true)"
    }
}

# Tool: pm.log_time
{
    "name": "pm.log_time",
    "description": "Log time spent on a task",
    "parameters": {
        "task_id": "Task UUID",
        "hours": "Hours worked",
        "date": "Date (YYYY-MM-DD, default: today)",
        "notes": "Optional work notes",
        "billable": "Is time billable (default: true)"
    }
}
```

**Routing Triggers:**
```javascript
const heraclesPatterns = [
  /sprint (plan|status|report|create)/i,
  /task (breakdown|create|update|status)/i,
  /time (track|log|entry|sheet)/i,
  /velocity|burndown|capacity/i,
  /project (status|plan|progress)/i,
  /epic|story|backlog/i,
  /openproject|leantime|jira/i
];
```

### Event Bus Integration
```python
# Published events
"pm.sprint.created"          # New sprint created
"pm.sprint.started"          # Sprint activated
"pm.sprint.completed"        # Sprint finished
"pm.task.created"            # New task added
"pm.task.completed"          # Task marked done
"pm.task.blocked"            # Task blocked
"pm.blocker.detected"        # Blocker identified
"pm.velocity.calculated"     # Velocity updated
"pm.time.logged"             # Time entry added
"pm.sync.completed"          # External sync finished
"pm.sync.conflict"           # Sync conflict detected

# Subscribed events
"agent.task.requested"       # ARIA requests task creation
"calendar.deadline.approaching"  # CHRONOS deadline alerts
"team.capacity.updated"      # Team availability changes
"client.project.created"     # New client project
```

### Cost Tracking
```python
from shared.cost_tracker import CostTracker

cost_tracker = CostTracker("HERACLES")

# Log AI task breakdown costs
await cost_tracker.log_usage(
    endpoint="/tasks/{id}/breakdown",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"task_type": "epic", "subtasks_generated": 5}
)

# Log sprint planning AI costs
await cost_tracker.log_usage(
    endpoint="/sprints/ai-plan",
    model="claude-sonnet-4-20250514",
    input_tokens=input_tokens,
    output_tokens=output_tokens,
    metadata={"sprint_name": sprint_name}
)
```

---

## SYSTEM PROMPT

```python
def build_system_prompt(project_context: dict) -> str:
    return f"""You are HERACLES - Elite Project Management Agent for LeverEdge AI.

Named after the legendary hero who completed the 12 labors through meticulous planning, resource management, and relentless execution, you help teams achieve their project goals with precision.

## TIME AWARENESS
- Current: {project_context['current_time']}
- Days to Launch: {project_context['days_to_launch']}

## YOUR IDENTITY
You are the project management brain of LeverEdge. You plan sprints, break down work, track time, measure velocity, and keep projects on track.

## CURRENT PROJECT STATUS
- Active Projects: {project_context['active_projects']}
- Active Sprints: {project_context['active_sprints']}
- Tasks In Progress: {project_context['tasks_in_progress']}
- Average Velocity: {project_context['avg_velocity']} points/sprint
- Team Capacity: {project_context['team_capacity']} hours this sprint

## YOUR CAPABILITIES

### Sprint Planning
- Create sprints with clear goals and capacity
- Assign tasks based on skills and availability
- Calculate realistic sprint capacity
- Identify overcommitment risks

### Task Breakdown
- Decompose epics into stories
- Break stories into actionable tasks
- Generate acceptance criteria
- Estimate effort for tasks

### Time Tracking
- Log time entries against tasks
- Track billable vs non-billable hours
- Generate timesheets and reports
- Timer-based tracking support

### Velocity Management
- Calculate sprint velocity
- Track velocity trends
- Forecast delivery dates
- Identify performance patterns

### External Integration
- Sync with OpenProject/Leantime
- Import tasks from external systems
- Export time entries
- Resolve sync conflicts

## TEAM COORDINATION
- Route financial tasks -> ATLAS
- Request calendar events -> CHRONOS
- Send notifications -> HERMES
- Log insights -> ARIA via Unified Memory
- Publish events -> Event Bus

## RESPONSE FORMAT
For sprint planning:
1. Sprint goal and duration
2. Capacity analysis
3. Task recommendations
4. Risk assessment
5. Success metrics

For task breakdown:
1. Task hierarchy
2. Estimates for each item
3. Dependencies identified
4. Acceptance criteria

## YOUR MISSION
Keep projects on track through effective planning and execution.
No task goes untracked.
Every sprint delivers value.
Velocity improves continuously.
"""
```

---

## IMPLEMENTATION PHASES

### Phase 1: Foundation (Sprint 1-2)
**Goal:** Basic agent with project and task management

- [ ] Create FastAPI agent structure
- [ ] Implement /health and /status endpoints
- [ ] Database schema setup and migrations
- [ ] Basic project CRUD operations
- [ ] Basic task CRUD operations
- [ ] Deploy and test

**Done When:** HERACLES runs and can create projects and tasks

### Phase 2: Sprint Management (Sprint 3-4)
**Goal:** Full sprint lifecycle management

- [ ] Sprint CRUD operations
- [ ] Sprint state transitions (planning -> active -> complete)
- [ ] Task-to-sprint assignment
- [ ] Sprint backlog management
- [ ] Basic sprint reports
- [ ] Burndown data generation

**Done When:** Can plan, run, and complete a full sprint

### Phase 3: Time Tracking (Sprint 5)
**Goal:** Comprehensive time entry system

- [ ] Time entry CRUD
- [ ] Timer-based tracking (start/stop)
- [ ] Billable/non-billable categorization
- [ ] Weekly timesheet generation
- [ ] Time summary reports
- [ ] Time approval workflow

**Done When:** Team can log and report time accurately

### Phase 4: Velocity & Analytics (Sprint 6-7)
**Goal:** Velocity tracking and forecasting

- [ ] Velocity calculation engine
- [ ] Historical velocity tracking
- [ ] Rolling average calculations
- [ ] Cycle time analysis
- [ ] Throughput metrics
- [ ] Forecasting based on velocity

**Done When:** Accurate velocity metrics and forecasts available

### Phase 5: AI-Powered Features (Sprint 8-9)
**Goal:** Intelligent task breakdown and planning

- [ ] AI-powered epic breakdown
- [ ] Story decomposition suggestions
- [ ] Acceptance criteria generation
- [ ] Sprint capacity recommendations
- [ ] Risk identification
- [ ] ARIA tool integration

**Done When:** AI assists in planning and task creation

### Phase 6: External Integration (Sprint 10-11)
**Goal:** OpenProject and Leantime synchronization

- [ ] OpenProject connector
- [ ] Leantime connector
- [ ] Bidirectional sync logic
- [ ] Conflict detection and resolution
- [ ] Webhook handlers
- [ ] Sync status dashboard

**Done When:** Projects sync seamlessly with external tools

---

## EFFORT ESTIMATES

| Phase | Tasks | Est. Hours | Sprint |
|-------|-------|------------|--------|
| Foundation | 6 | 12 | 1-2 |
| Sprint Management | 6 | 14 | 3-4 |
| Time Tracking | 6 | 10 | 5 |
| Velocity & Analytics | 6 | 12 | 6-7 |
| AI-Powered Features | 6 | 16 | 8-9 |
| External Integration | 6 | 14 | 10-11 |
| **Total** | **36** | **78** | **11 sprints** |

---

## SUCCESS CRITERIA

### Functional
- [ ] Sprint creation and management in < 2 minutes
- [ ] Task breakdown AI generates 5+ subtasks from an epic
- [ ] Time entries logged within 30 seconds
- [ ] Velocity calculated within 1 minute of sprint completion
- [ ] External sync completes within 5 minutes

### Quality
- [ ] 99%+ uptime
- [ ] < 500ms API response time for standard operations
- [ ] Zero data loss on sync conflicts
- [ ] All time entries accurate to 0.25 hours

### Integration
- [ ] ARIA can create sprints and tasks via tools
- [ ] Events publish to Event Bus reliably
- [ ] Insights stored in Unified Memory
- [ ] Costs tracked per AI operation
- [ ] OpenProject/Leantime sync working bidirectionally

---

## RISKS & MITIGATIONS

| Risk | Impact | Mitigation |
|------|--------|------------|
| Sync conflicts with external tools | Data inconsistency | Last-write-wins with manual resolution |
| Velocity calculations inaccurate | Bad forecasting | Use multiple calculation methods, show confidence |
| Time tracking adoption low | Poor data quality | Make logging easy, timer feature, reminders |
| AI task breakdown poor quality | Wasted effort | Human review required, feedback loop |
| Overengineered for small teams | Complexity overhead | Minimal viable features first, progressive complexity |

---

## GIT COMMIT

```
Add HERACLES - AI-powered project management agent spec

- Sprint planning with capacity and velocity tracking
- Hierarchical task breakdown (epic -> story -> task)
- Time tracking with timer and manual entry
- OpenProject/Leantime integration
- ARIA tools: pm.create_sprint, pm.add_task, pm.task_status, pm.sprint_report, pm.log_time
- Event Bus events: pm.sprint.*, pm.task.*, pm.blocker.detected
- 6-phase implementation plan (11 sprints)
- Full database schema with 6 tables
- Integration with Unified Memory, Event Bus, ARIA
```

---

## BUILD COMMAND

```
/gsd /opt/leveredge/specs/agents/PROJECT-MANAGER.md

Context: Build HERACLES project management agent. Start with Phase 1 foundation.
```
