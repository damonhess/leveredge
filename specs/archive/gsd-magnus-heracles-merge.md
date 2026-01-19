# GSD: Merge HERACLES Features into MAGNUS

**Priority:** HIGH
**Estimated Time:** 3-4 hours
**Purpose:** Make MAGNUS a true "Universal Project Master" by adding Agile PM features from HERACLES

---

## CONTEXT

HERACLES (8200) was killed in the agent cleanup, but it had unique features MAGNUS lacks:
- Sprint management with capacity planning
- Time tracking with start/stop timers
- Velocity calculations + forecasting
- Burndown chart data
- AI-powered task breakdown
- Team metrics + analytics

MAGNUS currently has: Projects, Tasks, Blockers, Decisions, Templates, PM tool connections

After merge, MAGNUS will be the **complete** project management solution.

---

## PHASE 1: DATABASE SCHEMA ADDITIONS

Add new tables to Supabase for sprint/time features. Run in DEV first.

```sql
-- ============================================
-- SPRINTS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS magnus_sprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    goal TEXT,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(50) DEFAULT 'planning' CHECK (status IN ('planning', 'active', 'completed', 'cancelled')),
    capacity_hours DECIMAL(10,2) DEFAULT 40.0,
    committed_points DECIMAL(10,2) DEFAULT 0,
    completed_points DECIMAL(10,2) DEFAULT 0,
    velocity DECIMAL(10,2),
    retrospective JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_magnus_sprints_project ON magnus_sprints(project_id);
CREATE INDEX idx_magnus_sprints_status ON magnus_sprints(status);

-- ============================================
-- ADD SPRINT FIELDS TO TASKS
-- ============================================
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS sprint_id UUID REFERENCES magnus_sprints(id);
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS story_points DECIMAL(10,2);
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS actual_hours DECIMAL(10,2) DEFAULT 0;
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;

CREATE INDEX idx_magnus_tasks_sprint ON magnus_tasks(sprint_id);

-- ============================================
-- TIME ENTRIES TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS magnus_time_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL DEFAULT 'damon',
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    hours DECIMAL(10,2) NOT NULL,
    notes TEXT,
    billable BOOLEAN DEFAULT TRUE,
    approved BOOLEAN DEFAULT FALSE,
    approved_by VARCHAR(255),
    timer_started TIMESTAMPTZ,
    timer_stopped TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_magnus_time_task ON magnus_time_entries(task_id);
CREATE INDEX idx_magnus_time_user ON magnus_time_entries(user_id);
CREATE INDEX idx_magnus_time_date ON magnus_time_entries(date);

-- ============================================
-- ACTIVE TIMERS TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS magnus_active_timers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL DEFAULT 'damon',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, task_id)
);

-- ============================================
-- VELOCITY HISTORY TABLE
-- ============================================
CREATE TABLE IF NOT EXISTS magnus_velocity_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    sprint_id UUID REFERENCES magnus_sprints(id) ON DELETE CASCADE,
    committed_points DECIMAL(10,2),
    completed_points DECIMAL(10,2),
    velocity_points DECIMAL(10,2),
    committed_hours DECIMAL(10,2),
    completed_hours DECIMAL(10,2),
    velocity_hours DECIMAL(10,2),
    completion_rate DECIMAL(5,2),
    task_count INTEGER,
    completed_task_count INTEGER,
    calculated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_magnus_velocity_project ON magnus_velocity_history(project_id);

-- ============================================
-- HELPER FUNCTIONS
-- ============================================

-- Calculate sprint velocity
CREATE OR REPLACE FUNCTION magnus_calculate_sprint_velocity(p_sprint_id UUID)
RETURNS TABLE (
    committed_points DECIMAL,
    completed_points DECIMAL,
    velocity_points DECIMAL,
    committed_hours DECIMAL,
    completed_hours DECIMAL,
    completion_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(SUM(t.story_points), 0) as committed_points,
        COALESCE(SUM(CASE WHEN t.status = 'done' THEN t.story_points ELSE 0 END), 0) as completed_points,
        COALESCE(SUM(CASE WHEN t.status = 'done' THEN t.story_points ELSE 0 END), 0) as velocity_points,
        COALESCE(SUM(t.estimated_hours), 0) as committed_hours,
        COALESCE(SUM(CASE WHEN t.status = 'done' THEN t.actual_hours ELSE 0 END), 0) as completed_hours,
        CASE 
            WHEN COALESCE(SUM(t.story_points), 0) > 0 
            THEN (COALESCE(SUM(CASE WHEN t.status = 'done' THEN t.story_points ELSE 0 END), 0) / SUM(t.story_points) * 100)
            ELSE 0 
        END as completion_rate
    FROM magnus_tasks t
    WHERE t.sprint_id = p_sprint_id;
END;
$$ LANGUAGE plpgsql;

-- Rolling velocity for project
CREATE OR REPLACE FUNCTION magnus_rolling_velocity(p_project_id UUID, p_sprint_count INTEGER DEFAULT 3)
RETURNS TABLE (
    avg_velocity_points DECIMAL,
    avg_velocity_hours DECIMAL,
    sprint_count INTEGER,
    trend VARCHAR
) AS $$
DECLARE
    recent_velocities DECIMAL[];
    trend_result VARCHAR;
BEGIN
    SELECT array_agg(velocity_points ORDER BY calculated_at DESC)
    INTO recent_velocities
    FROM (
        SELECT velocity_points, calculated_at
        FROM magnus_velocity_history
        WHERE project_id = p_project_id
        ORDER BY calculated_at DESC
        LIMIT p_sprint_count
    ) sub;
    
    IF array_length(recent_velocities, 1) >= 2 THEN
        IF recent_velocities[1] > recent_velocities[2] * 1.1 THEN
            trend_result := 'improving';
        ELSIF recent_velocities[1] < recent_velocities[2] * 0.9 THEN
            trend_result := 'declining';
        ELSE
            trend_result := 'stable';
        END IF;
    ELSE
        trend_result := 'insufficient_data';
    END IF;
    
    RETURN QUERY
    SELECT 
        COALESCE(AVG(vh.velocity_points), 0)::DECIMAL as avg_velocity_points,
        COALESCE(AVG(vh.velocity_hours), 0)::DECIMAL as avg_velocity_hours,
        COUNT(*)::INTEGER as sprint_count,
        trend_result as trend
    FROM magnus_velocity_history vh
    WHERE vh.project_id = p_project_id
    ORDER BY vh.calculated_at DESC
    LIMIT p_sprint_count;
END;
$$ LANGUAGE plpgsql;

-- Analyze sprint capacity
CREATE OR REPLACE FUNCTION magnus_sprint_capacity(p_sprint_id UUID)
RETURNS TABLE (
    capacity_hours DECIMAL,
    committed_hours DECIMAL,
    committed_points DECIMAL,
    utilization_pct DECIMAL,
    available_hours DECIMAL,
    task_count INTEGER,
    unestimated_count INTEGER,
    blocked_count INTEGER,
    risk_level VARCHAR
) AS $$
DECLARE
    sprint_capacity DECIMAL;
    total_estimate DECIMAL;
    total_points DECIMAL;
    task_total INTEGER;
    unestimated INTEGER;
    blocked INTEGER;
    risk VARCHAR;
    utilization DECIMAL;
BEGIN
    SELECT s.capacity_hours INTO sprint_capacity
    FROM magnus_sprints s WHERE s.id = p_sprint_id;
    
    SELECT 
        COALESCE(SUM(t.estimated_hours), 0),
        COALESCE(SUM(t.story_points), 0),
        COUNT(*),
        COUNT(*) FILTER (WHERE t.estimated_hours IS NULL),
        COUNT(*) FILTER (WHERE t.status = 'blocked')
    INTO total_estimate, total_points, task_total, unestimated, blocked
    FROM magnus_tasks t
    WHERE t.sprint_id = p_sprint_id;
    
    utilization := CASE WHEN sprint_capacity > 0 THEN (total_estimate / sprint_capacity * 100) ELSE 0 END;
    
    IF utilization > 100 OR blocked > 2 THEN
        risk := 'high';
    ELSIF utilization > 85 OR unestimated > 3 OR blocked > 0 THEN
        risk := 'medium';
    ELSE
        risk := 'low';
    END IF;
    
    RETURN QUERY SELECT
        sprint_capacity,
        total_estimate,
        total_points,
        utilization,
        GREATEST(0, sprint_capacity - total_estimate),
        task_total,
        unestimated,
        blocked,
        risk;
END;
$$ LANGUAGE plpgsql;
```

---

## PHASE 2: ADD ENDPOINTS TO MAGNUS

Update `/opt/leveredge/control-plane/agents/magnus/magnus.py` to add these endpoints:

### Sprint Endpoints
```
POST   /sprints                  - Create sprint
GET    /sprints                  - List sprints (filter by project_id, status)
GET    /sprints/{sprint_id}      - Get sprint details
PATCH  /sprints/{sprint_id}      - Update sprint
POST   /sprints/{sprint_id}/start    - Start sprint
POST   /sprints/{sprint_id}/complete - Complete sprint + calculate velocity
GET    /sprints/{sprint_id}/burndown - Get burndown data
GET    /sprints/{sprint_id}/report   - Full sprint report
```

### Time Tracking Endpoints
```
POST   /time                     - Log time entry
GET    /time                     - List entries (filter by task, user, date range)
PUT    /time/{entry_id}          - Update entry
DELETE /time/{entry_id}          - Delete entry
POST   /time/timer/start         - Start timer
POST   /time/timer/stop          - Stop timer + auto-log
GET    /time/timers/active       - List active timers
GET    /time/summary             - Time summary report
GET    /time/timesheet           - Weekly timesheet
```

### Velocity Endpoints
```
GET    /velocity                 - Current velocity (all projects or specific)
GET    /velocity/{project_id}    - Rolling velocity for project
GET    /velocity/history         - Velocity history
GET    /velocity/forecast        - Delivery forecast based on velocity
```

### Analytics Endpoints
```
GET    /analytics/cycle-time     - Cycle time analysis
GET    /analytics/throughput     - Throughput metrics
GET    /analytics/team           - Team performance metrics
```

### AI Endpoints
```
POST   /tasks/{task_id}/breakdown - AI-powered task breakdown
POST   /ai/breakdown              - Standalone AI breakdown
```

---

## PHASE 3: UPDATE TASK ENDPOINTS

Modify existing task endpoints to support sprint assignment:

```python
class TaskCreate(BaseModel):
    # ... existing fields ...
    sprint_id: Optional[str] = None      # NEW
    story_points: Optional[float] = None  # NEW

class TaskUpdate(BaseModel):
    # ... existing fields ...
    sprint_id: Optional[str] = None
    story_points: Optional[float] = None
    actual_hours: Optional[float] = None
```

Add task move endpoint:
```
POST   /tasks/{task_id}/move     - Move task to different sprint
```

---

## PHASE 4: IMPLEMENT CORE FEATURES

### 4.1 Sprint Management

```python
@app.post("/sprints")
async def create_sprint(sprint: SprintCreate):
    """Create a new sprint"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_sprints (project_id, name, goal, start_date, end_date, capacity_hours)
            VALUES ($1::uuid, $2, $3, $4, $5, $6)
            RETURNING *
        """, sprint.project_id, sprint.name, sprint.goal, 
            sprint.start_date, sprint.end_date, sprint.capacity_hours)
        return dict(row)

@app.post("/sprints/{sprint_id}/start")
async def start_sprint(sprint_id: str):
    """Start a sprint - moves it to active status"""
    async with pool.acquire() as conn:
        # Calculate committed points at start
        row = await conn.fetchrow("""
            UPDATE magnus_sprints s
            SET status = 'active',
                committed_points = (
                    SELECT COALESCE(SUM(story_points), 0)
                    FROM magnus_tasks WHERE sprint_id = $1::uuid
                ),
                updated_at = NOW()
            WHERE id = $1::uuid AND status = 'planning'
            RETURNING *
        """, sprint_id)
        
        if not row:
            raise HTTPException(status_code=400, detail="Sprint not in planning status")
        
        return {
            "status": "started",
            "sprint": dict(row),
            "capacity": await get_sprint_capacity(sprint_id)
        }

@app.post("/sprints/{sprint_id}/complete")
async def complete_sprint(sprint_id: str):
    """Complete sprint and record velocity"""
    async with pool.acquire() as conn:
        # Calculate velocity
        velocity = await conn.fetchrow(
            "SELECT * FROM magnus_calculate_sprint_velocity($1::uuid)", sprint_id
        )
        
        # Update sprint
        sprint = await conn.fetchrow("""
            UPDATE magnus_sprints
            SET status = 'completed',
                completed_points = $2,
                velocity = $2,
                updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, sprint_id, velocity['completed_points'])
        
        # Record velocity history
        await conn.execute("""
            INSERT INTO magnus_velocity_history 
            (project_id, sprint_id, committed_points, completed_points, velocity_points,
             committed_hours, completed_hours, velocity_hours, completion_rate, task_count, completed_task_count)
            SELECT 
                s.project_id, $1::uuid, $2, $3, $3, $4, $5, $5, $6,
                (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = $1::uuid),
                (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = $1::uuid AND status = 'done')
            FROM magnus_sprints s WHERE s.id = $1::uuid
        """, sprint_id, velocity['committed_points'], velocity['completed_points'],
             velocity['committed_hours'], velocity['completed_hours'], velocity['completion_rate'])
        
        return {
            "status": "completed",
            "sprint": dict(sprint),
            "velocity": dict(velocity)
        }
```

### 4.2 Time Tracking

```python
@app.post("/time")
async def log_time(entry: TimeEntryCreate):
    """Log a time entry"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_time_entries (task_id, user_id, date, hours, notes, billable)
            VALUES ($1::uuid, $2, $3, $4, $5, $6)
            RETURNING *
        """, entry.task_id, entry.user_id, entry.date, 
            entry.hours, entry.notes, entry.billable)
        
        # Update task actual hours
        await conn.execute("""
            UPDATE magnus_tasks 
            SET actual_hours = COALESCE(actual_hours, 0) + $2
            WHERE id = $1::uuid
        """, entry.task_id, entry.hours)
        
        return dict(row)

@app.post("/time/timer/start")
async def start_timer(task_id: str, user_id: str = "damon"):
    """Start a timer for a task"""
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow("""
                INSERT INTO magnus_active_timers (task_id, user_id)
                VALUES ($1::uuid, $2)
                RETURNING *
            """, task_id, user_id)
            return {"status": "started", "timer": dict(row)}
        except Exception:
            raise HTTPException(status_code=400, detail="Timer already running for this task")

@app.post("/time/timer/stop")
async def stop_timer(task_id: str, user_id: str = "damon", notes: str = None):
    """Stop timer and log time"""
    async with pool.acquire() as conn:
        timer = await conn.fetchrow("""
            DELETE FROM magnus_active_timers 
            WHERE task_id = $1::uuid AND user_id = $2
            RETURNING *
        """, task_id, user_id)
        
        if not timer:
            raise HTTPException(status_code=404, detail="No active timer found")
        
        # Calculate duration
        started = timer['started_at']
        stopped = datetime.now()
        hours = round((stopped - started).total_seconds() / 3600, 2)
        
        # Log the time
        entry = await conn.fetchrow("""
            INSERT INTO magnus_time_entries 
            (task_id, user_id, date, hours, notes, timer_started, timer_stopped)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, task_id, user_id, stopped.date(), hours, notes, started, stopped)
        
        # Update task actual hours
        await conn.execute("""
            UPDATE magnus_tasks 
            SET actual_hours = COALESCE(actual_hours, 0) + $2
            WHERE id = $1::uuid
        """, task_id, hours)
        
        return {
            "status": "stopped",
            "duration_hours": hours,
            "time_entry": dict(entry)
        }
```

### 4.3 AI Task Breakdown

```python
@app.post("/tasks/{task_id}/breakdown")
async def breakdown_task(task_id: str):
    """AI-powered task breakdown into subtasks"""
    async with pool.acquire() as conn:
        task = await conn.fetchrow(
            "SELECT * FROM magnus_tasks WHERE id = $1::uuid", task_id
        )
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
    
    prompt = f"""Break down this task into subtasks:

**Task:** {task['title']}
**Description:** {task.get('description', 'No description')}
**Estimated Hours:** {task.get('estimated_hours', 'Not estimated')}

Provide:
1. A list of 3-7 subtasks
2. For each: title, description, estimated hours, priority
3. Dependencies between subtasks
4. Total estimated hours

Format as JSON:
{{
  "subtasks": [
    {{"title": "...", "description": "...", "estimated_hours": N, "priority": "high|medium|low", "depends_on": []}}
  ],
  "total_estimate": N,
  "notes": "..."
}}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "task_id": task_id,
        "original_task": dict(task),
        "breakdown_suggestion": response.content[0].text
    }
```

---

## PHASE 5: UPDATE STATUS/STANDUP

Update the `/status` and `/standup/generate` endpoints to include sprint info:

```python
@app.get("/status")
async def magnus_status():
    """MAGNUS's current assessment including sprint progress"""
    async with pool.acquire() as conn:
        # ... existing code ...
        
        # Add active sprint info
        active_sprint = await conn.fetchrow("""
            SELECT s.*, 
                   (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = s.id) as task_count,
                   (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = s.id AND status = 'done') as done_count
            FROM magnus_sprints s
            WHERE s.status = 'active'
            LIMIT 1
        """)
        
        # Get today's time logged
        time_today = await conn.fetchrow("""
            SELECT COALESCE(SUM(hours), 0) as hours
            FROM magnus_time_entries
            WHERE date = CURRENT_DATE
        """)
        
        return {
            # ... existing fields ...
            "active_sprint": dict(active_sprint) if active_sprint else None,
            "time_logged_today": float(time_today['hours']) if time_today else 0,
            "active_timers": await conn.fetchval(
                "SELECT COUNT(*) FROM magnus_active_timers"
            )
        }
```

---

## PHASE 6: VERIFY & COMMIT

```bash
# Test sprint creation
curl -X POST http://localhost:8019/sprints \
  -H "Content-Type: application/json" \
  -d '{"project_id": "...", "name": "Sprint 1", "start_date": "2026-01-20", "end_date": "2026-02-02", "capacity_hours": 40}'

# Test time logging
curl -X POST http://localhost:8019/time \
  -H "Content-Type: application/json" \
  -d '{"task_id": "...", "hours": 2.5, "notes": "Working on feature X"}'

# Test timer
curl -X POST "http://localhost:8019/time/timer/start?task_id=...&user_id=damon"
# ... work ...
curl -X POST "http://localhost:8019/time/timer/stop?task_id=...&user_id=damon&notes=Completed"

# Commit
git add .
git commit -m "MAGNUS: Merge HERACLES features for complete Agile PM

ADDED:
- Sprint management (create, start, complete, burndown)
- Time tracking with start/stop timers
- Velocity calculations + forecasting
- Capacity analysis
- AI-powered task breakdown
- Analytics (cycle time, throughput, team metrics)

NEW TABLES:
- magnus_sprints
- magnus_time_entries
- magnus_active_timers
- magnus_velocity_history

MODIFIED:
- magnus_tasks (added sprint_id, story_points, actual_hours)

MAGNUS is now the complete Universal Project Master.
Checkmate is inevitable."
```

---

## DELIVERABLES

1. ✅ New database tables and functions
2. ✅ Sprint management endpoints
3. ✅ Time tracking with timers
4. ✅ Velocity calculations
5. ✅ AI task breakdown
6. ✅ Updated status/standup with sprint info
7. ✅ Documentation updated

---

## FUTURE (Post-Launch)

- PLUTUS resurrection for personal investing
- Burndown chart visualization in Command Center
- Sprint retrospective workflow
- Team velocity comparisons

---

*"The pieces from HERACLES now serve the board under MAGNUS. Checkmate remains inevitable."*
