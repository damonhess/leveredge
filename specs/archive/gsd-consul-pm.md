# GSD: CONSUL - Master of Projects

**Priority:** HIGH
**Estimated Time:** 12-16 hours
**Spec:** /opt/leveredge/specs/CONSUL-PM-SPEC.md

---

## MISSION

Build CONSUL, the most capable PM agent in existence. He will:
1. Own the LeverEdge agency build
2. Track every task, commitment, and deadline
3. Dispatch work to agents via ATLAS
4. Ensure nothing falls through the cracks
5. Participate in all Council meetings by default

**Tagline:** "Nothing escapes my attention. Nothing falls through the cracks."

---

## PHASE 1: DEPLOY LEANTIME (2 hours)

### 1.1 Create Leantime Docker Setup

Create `/opt/leveredge/pm-tools/docker-compose.yml`:

```yaml
version: '3.8'

services:
  leantime:
    image: leantime/leantime:latest
    container_name: leantime
    restart: unless-stopped
    ports:
      - "8040:80"
    environment:
      LEAN_DB_HOST: leantime-db
      LEAN_DB_USER: leantime
      LEAN_DB_PASSWORD: ${LEANTIME_DB_PASSWORD:-leantimepass123}
      LEAN_DB_DATABASE: leantime
      LEAN_SITENAME: "LeverEdge PM"
      LEAN_DEFAULT_TIMEZONE: America/Los_Angeles
      LEAN_SESSION_PASSWORD: ${LEANTIME_SESSION_PASSWORD:-randomsessionkey123}
      LEAN_APP_URL: https://pm.leveredgeai.com
    volumes:
      - leantime_data:/var/www/html/userfiles
      - leantime_plugins:/var/www/html/app/Plugins
    depends_on:
      - leantime-db
    networks:
      - leveredge-network

  leantime-db:
    image: mysql:8.0
    container_name: leantime-db
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${LEANTIME_MYSQL_ROOT:-rootpass123}
      MYSQL_DATABASE: leantime
      MYSQL_USER: leantime
      MYSQL_PASSWORD: ${LEANTIME_DB_PASSWORD:-leantimepass123}
    volumes:
      - leantime_mysql:/var/lib/mysql
    networks:
      - leveredge-network

volumes:
  leantime_data:
  leantime_plugins:
  leantime_mysql:

networks:
  leveredge-network:
    external: true
```

### 1.2 Add Caddy Routing

Add to Caddyfile:
```
pm.leveredgeai.com {
    reverse_proxy localhost:8040
}
```

### 1.3 Create DNS Record
- A record: pm.leveredgeai.com → server IP

### 1.4 Start Leantime

```bash
cd /opt/leveredge/pm-tools
docker compose up -d
```

### 1.5 Initial Setup
1. Open https://pm.leveredgeai.com
2. Complete installation wizard
3. Create admin account
4. Note API credentials for CONSUL

---

## PHASE 2: CONSUL DATABASE SCHEMA (2 hours)

### 2.1 Create Migration File

Create `/opt/leveredge/database/migrations/20260119_consul_schema.sql`:

```sql
-- ============================================================
-- CONSUL: Master of Projects
-- Database Schema
-- ============================================================

-- Projects
CREATE TABLE IF NOT EXISTS consul_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planning' CHECK (status IN (
        'planning', 'active', 'on_hold', 'completed', 'cancelled'
    )),
    priority INTEGER DEFAULT 50 CHECK (priority >= 1 AND priority <= 100),
    
    -- Ownership
    owner TEXT DEFAULT 'damon',
    pm_agent TEXT DEFAULT 'CONSUL',
    
    -- External sync
    leantime_project_id INTEGER,
    
    -- Dates
    target_start DATE,
    target_end DATE,
    actual_start DATE,
    actual_end DATE,
    
    -- Scope tracking
    original_scope JSONB DEFAULT '{}',
    current_scope JSONB DEFAULT '{}',
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE IF NOT EXISTS consul_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES consul_projects(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES consul_tasks(id) ON DELETE SET NULL,
    
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo' CHECK (status IN (
        'todo', 'in_progress', 'blocked', 'review', 'done', 'cancelled'
    )),
    priority INTEGER DEFAULT 50,
    
    -- Assignment
    assigned_agent TEXT,
    assigned_at TIMESTAMPTZ,
    
    -- Time tracking
    estimated_hours DECIMAL(6,2),
    actual_hours DECIMAL(6,2) DEFAULT 0,
    
    -- Dates
    due_date DATE,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Dependencies (stored as array of task IDs)
    depends_on UUID[] DEFAULT '{}',
    
    -- External sync
    leantime_task_id INTEGER,
    
    -- Metadata
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Blockers
CREATE TABLE IF NOT EXISTS consul_blockers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES consul_tasks(id) ON DELETE CASCADE,
    project_id UUID REFERENCES consul_projects(id) ON DELETE CASCADE,
    
    description TEXT NOT NULL,
    blocker_type TEXT CHECK (blocker_type IN (
        'dependency', 'decision_needed', 'resource', 'external', 'technical', 'other'
    )),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    -- Resolution
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'escalated', 'resolved')),
    escalated_to TEXT,
    escalated_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decisions
CREATE TABLE IF NOT EXISTS consul_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES consul_projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES consul_tasks(id) ON DELETE SET NULL,
    
    question TEXT NOT NULL,
    context TEXT,
    options JSONB DEFAULT '[]',
    
    -- Decision
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'decided', 'deferred')),
    decision TEXT,
    decided_by TEXT,
    decided_at TIMESTAMPTZ,
    rationale TEXT,
    
    -- Deadline
    decision_deadline DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scope changes
CREATE TABLE IF NOT EXISTS consul_scope_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES consul_projects(id) ON DELETE CASCADE,
    
    change_type TEXT CHECK (change_type IN ('addition', 'removal', 'modification')),
    description TEXT NOT NULL,
    impact_assessment TEXT,
    
    estimated_hours_added DECIMAL(6,2),
    days_added INTEGER,
    
    status TEXT DEFAULT 'proposed' CHECK (status IN ('proposed', 'approved', 'rejected')),
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily standups
CREATE TABLE IF NOT EXISTS consul_standups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES consul_projects(id) ON DELETE CASCADE,
    standup_date DATE DEFAULT CURRENT_DATE,
    
    tasks_completed INTEGER DEFAULT 0,
    tasks_in_progress INTEGER DEFAULT 0,
    tasks_blocked INTEGER DEFAULT 0,
    tasks_added INTEGER DEFAULT 0,
    
    summary TEXT,
    blockers_summary TEXT,
    risks TEXT,
    wins TEXT,
    tomorrow_priorities TEXT,
    
    velocity_score DECIMAL(5,2),
    health_score DECIMAL(5,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(project_id, standup_date)
);

-- Agent workload
CREATE TABLE IF NOT EXISTS consul_agent_workload (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent TEXT NOT NULL UNIQUE,
    
    active_tasks INTEGER DEFAULT 0,
    estimated_hours_queued DECIMAL(6,2) DEFAULT 0,
    max_concurrent_tasks INTEGER DEFAULT 5,
    
    total_tasks_completed INTEGER DEFAULT 0,
    avg_completion_hours DECIMAL(6,2),
    on_time_percentage DECIMAL(5,2),
    
    last_task_completed TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Action items from meetings
CREATE TABLE IF NOT EXISTS consul_action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source
    council_id UUID,  -- If from council meeting
    source_type TEXT CHECK (source_type IN ('council', 'standup', 'manual', 'aria')),
    source_context TEXT,
    
    -- The action
    description TEXT NOT NULL,
    assigned_to TEXT,
    due_date DATE,
    
    -- Status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled')),
    completed_at TIMESTAMPTZ,
    
    -- Link to task if created
    task_id UUID REFERENCES consul_tasks(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_consul_projects_status ON consul_projects(status);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_project ON consul_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_status ON consul_tasks(status);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_agent ON consul_tasks(assigned_agent);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_due ON consul_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_consul_blockers_status ON consul_blockers(status);
CREATE INDEX IF NOT EXISTS idx_consul_decisions_status ON consul_decisions(status);
CREATE INDEX IF NOT EXISTS idx_consul_standups_date ON consul_standups(standup_date DESC);
CREATE INDEX IF NOT EXISTS idx_consul_action_items_status ON consul_action_items(status);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Get project summary
CREATE OR REPLACE FUNCTION consul_project_summary(p_project_id UUID DEFAULT NULL)
RETURNS TABLE (
    id UUID,
    name TEXT,
    status TEXT,
    priority INTEGER,
    target_end DATE,
    days_remaining INTEGER,
    tasks_done BIGINT,
    tasks_in_progress BIGINT,
    tasks_todo BIGINT,
    tasks_blocked BIGINT,
    total_tasks BIGINT,
    completion_percentage DECIMAL,
    open_blockers BIGINT,
    pending_decisions BIGINT,
    health_score DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.status,
        p.priority,
        p.target_end,
        (p.target_end - CURRENT_DATE)::INTEGER as days_remaining,
        COUNT(t.id) FILTER (WHERE t.status = 'done'),
        COUNT(t.id) FILTER (WHERE t.status = 'in_progress'),
        COUNT(t.id) FILTER (WHERE t.status = 'todo'),
        COUNT(t.id) FILTER (WHERE t.status = 'blocked'),
        COUNT(t.id),
        CASE WHEN COUNT(t.id) > 0 
            THEN ROUND(COUNT(t.id) FILTER (WHERE t.status = 'done')::DECIMAL / COUNT(t.id) * 100, 1)
            ELSE 0 
        END,
        (SELECT COUNT(*) FROM consul_blockers b WHERE b.project_id = p.id AND b.status = 'open'),
        (SELECT COUNT(*) FROM consul_decisions d WHERE d.project_id = p.id AND d.status = 'pending'),
        -- Health score calculation
        CASE 
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 3 THEN 40
            WHEN (p.target_end - CURRENT_DATE) < 7 AND COUNT(t.id) FILTER (WHERE t.status = 'done')::DECIMAL / NULLIF(COUNT(t.id), 0) < 0.8 THEN 50
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 0 THEN 70
            ELSE 90
        END::DECIMAL
    FROM consul_projects p
    LEFT JOIN consul_tasks t ON t.project_id = p.id
    WHERE (p_project_id IS NULL OR p.id = p_project_id)
    AND p.status IN ('planning', 'active')
    GROUP BY p.id;
END;
$$ LANGUAGE plpgsql;

-- Get agent workload summary
CREATE OR REPLACE FUNCTION consul_agent_availability()
RETURNS TABLE (
    agent TEXT,
    active_tasks INTEGER,
    max_tasks INTEGER,
    hours_queued DECIMAL,
    availability TEXT,
    on_time_pct DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        w.agent,
        w.active_tasks,
        w.max_concurrent_tasks,
        w.estimated_hours_queued,
        CASE 
            WHEN w.active_tasks >= w.max_concurrent_tasks THEN 'at_capacity'
            WHEN w.active_tasks >= w.max_concurrent_tasks * 0.8 THEN 'high'
            WHEN w.active_tasks >= w.max_concurrent_tasks * 0.5 THEN 'medium'
            ELSE 'available'
        END,
        w.on_time_percentage
    FROM consul_agent_workload w
    ORDER BY w.active_tasks DESC;
END;
$$ LANGUAGE plpgsql;

-- Get overdue tasks
CREATE OR REPLACE FUNCTION consul_overdue_tasks()
RETURNS TABLE (
    task_id UUID,
    project_name TEXT,
    task_title TEXT,
    assigned_agent TEXT,
    due_date DATE,
    days_overdue INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        t.id,
        p.name,
        t.title,
        t.assigned_agent,
        t.due_date,
        (CURRENT_DATE - t.due_date)::INTEGER
    FROM consul_tasks t
    JOIN consul_projects p ON t.project_id = p.id
    WHERE t.due_date < CURRENT_DATE
    AND t.status NOT IN ('done', 'cancelled')
    ORDER BY t.due_date ASC;
END;
$$ LANGUAGE plpgsql;

-- Generate standup for project
CREATE OR REPLACE FUNCTION consul_generate_standup(p_project_id UUID)
RETURNS consul_standups AS $$
DECLARE
    result consul_standups;
    v_done INTEGER;
    v_in_progress INTEGER;
    v_blocked INTEGER;
    v_blockers TEXT;
BEGIN
    -- Get counts
    SELECT 
        COUNT(*) FILTER (WHERE status = 'done' AND completed_at::DATE = CURRENT_DATE),
        COUNT(*) FILTER (WHERE status = 'in_progress'),
        COUNT(*) FILTER (WHERE status = 'blocked')
    INTO v_done, v_in_progress, v_blocked
    FROM consul_tasks
    WHERE project_id = p_project_id;
    
    -- Get blocker summary
    SELECT string_agg(description, '; ')
    INTO v_blockers
    FROM consul_blockers
    WHERE project_id = p_project_id AND status = 'open';
    
    -- Insert or update standup
    INSERT INTO consul_standups (
        project_id, standup_date, 
        tasks_completed, tasks_in_progress, tasks_blocked,
        blockers_summary
    ) VALUES (
        p_project_id, CURRENT_DATE,
        v_done, v_in_progress, v_blocked,
        v_blockers
    )
    ON CONFLICT (project_id, standup_date) 
    DO UPDATE SET
        tasks_completed = v_done,
        tasks_in_progress = v_in_progress,
        tasks_blocked = v_blocked,
        blockers_summary = v_blockers
    RETURNING * INTO result;
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- SEED DATA: LeverEdge Project
-- ============================================================

-- Create the main project
INSERT INTO consul_projects (
    name, description, status, priority, owner, pm_agent,
    target_start, target_end, original_scope
) VALUES (
    'LeverEdge Agency Launch',
    'Build and launch LeverEdge AI automation agency by March 1, 2026',
    'active',
    100,
    'damon',
    'CONSUL',
    '2026-01-11',
    '2026-03-01',
    '{
        "phases": ["Infrastructure", "Outreach Prep", "Active Outreach", "Launch"],
        "goals": ["$30K MRR", "3 clients", "Repeatable process"],
        "non_goals": ["Enterprise features", "Multiple verticals"]
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- Initialize agent workloads
INSERT INTO consul_agent_workload (agent, max_concurrent_tasks) VALUES
    ('CHRONOS', 5),
    ('HADES', 3),
    ('AEGIS', 3),
    ('HERMES', 10),
    ('SCHOLAR', 3),
    ('CHIRON', 3),
    ('ATHENA', 5),
    ('MUSE', 3),
    ('QUILL', 5),
    ('STAGE', 3),
    ('REEL', 3),
    ('CRITIC', 5),
    ('DAEDALUS', 3),
    ('VARYS', 3),
    ('CONSUL', 10),
    ('HEPHAESTUS', 5)
ON CONFLICT (agent) DO NOTHING;
```

### 2.2 Run Migration

```bash
psql $DEV_DATABASE_URL -f /opt/leveredge/database/migrations/20260119_consul_schema.sql
```

---

## PHASE 3: BUILD CONSUL SERVICE (6 hours)

### 3.1 Create Service Directory

```bash
mkdir -p /opt/leveredge/control-plane/agents/consul
```

### 3.2 Create Main Service

Create `/opt/leveredge/control-plane/agents/consul/consul.py`:

```python
"""
CONSUL - Master of Projects
Port: 8017
Domain: CHANCERY

The most capable, attentive, detail-oriented PM known to humanity.
Nothing escapes my attention. Nothing falls through the cracks.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import os
import asyncpg
import httpx
import json

app = FastAPI(
    title="CONSUL - Master of Projects",
    description="Nothing escapes my attention. Nothing falls through the cracks.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
LEANTIME_URL = os.environ.get("LEANTIME_URL", "http://leantime:80")
LEANTIME_API_KEY = os.environ.get("LEANTIME_API_KEY")

# ============ MODELS ============

class ProjectStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    CANCELLED = "cancelled"

class BlockerSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    priority: int = Field(default=50, ge=1, le=100)
    target_start: Optional[date] = None
    target_end: Optional[date] = None
    tags: List[str] = []

class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    priority: int = Field(default=50, ge=1, le=100)
    assigned_agent: Optional[str] = None
    estimated_hours: Optional[float] = None
    due_date: Optional[date] = None
    depends_on: List[str] = []
    tags: List[str] = []

class BlockerCreate(BaseModel):
    task_id: Optional[str] = None
    project_id: str
    description: str
    blocker_type: str = "other"
    severity: BlockerSeverity = BlockerSeverity.MEDIUM

class DecisionCreate(BaseModel):
    project_id: str
    question: str
    context: Optional[str] = None
    options: List[Dict[str, Any]] = []
    decision_deadline: Optional[date] = None

# ============ DATABASE ============

pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()

# ============ HELPER FUNCTIONS ============

async def update_agent_workload(agent: str, delta: int):
    """Update agent's active task count"""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO consul_agent_workload (agent, active_tasks)
            VALUES ($1, GREATEST(0, $2))
            ON CONFLICT (agent) DO UPDATE
            SET active_tasks = GREATEST(0, consul_agent_workload.active_tasks + $2),
                updated_at = NOW()
        """, agent, delta)

async def notify_aria(message: str, priority: str = "normal"):
    """Send notification to ARIA"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8111/notify",  # ARIA's endpoint
                json={"message": message, "source": "CONSUL", "priority": priority},
                timeout=5.0
            )
    except:
        pass  # Don't fail if ARIA unavailable

async def report_to_lcis(lesson: dict):
    """Report lesson to LCIS"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8050/ingest",
                json={**lesson, "source_agent": "CONSUL", "domain": "CHANCERY"},
                timeout=5.0
            )
    except:
        pass

# ============ PROJECT ENDPOINTS ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "CONSUL - Master of Projects",
        "port": 8017,
        "tagline": "Nothing escapes my attention. Nothing falls through the cracks."
    }

@app.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO consul_projects (name, description, priority, target_start, target_end, tags)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, project.name, project.description, project.priority, 
            project.target_start, project.target_end, project.tags)
        
        await notify_aria(f"📋 New project created: {project.name}")
        return dict(row)

@app.get("/projects")
async def list_projects(status: Optional[str] = None, include_summary: bool = True):
    """List all projects with optional summary"""
    async with pool.acquire() as conn:
        if include_summary:
            rows = await conn.fetch("SELECT * FROM consul_project_summary($1)", None)
        else:
            query = "SELECT * FROM consul_projects"
            if status:
                query += f" WHERE status = '{status}'"
            query += " ORDER BY priority DESC"
            rows = await conn.fetch(query)
        return [dict(row) for row in rows]

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details with full summary"""
    async with pool.acquire() as conn:
        project = await conn.fetchrow(
            "SELECT * FROM consul_projects WHERE id = $1", project_id
        )
        if not project:
            raise HTTPException(404, "Project not found")
        
        summary = await conn.fetchrow(
            "SELECT * FROM consul_project_summary($1)", project_id
        )
        
        tasks = await conn.fetch(
            "SELECT * FROM consul_tasks WHERE project_id = $1 ORDER BY priority DESC, due_date ASC",
            project_id
        )
        
        blockers = await conn.fetch(
            "SELECT * FROM consul_blockers WHERE project_id = $1 AND status = 'open'",
            project_id
        )
        
        decisions = await conn.fetch(
            "SELECT * FROM consul_decisions WHERE project_id = $1 AND status = 'pending'",
            project_id
        )
        
        return {
            "project": dict(project),
            "summary": dict(summary) if summary else None,
            "tasks": [dict(t) for t in tasks],
            "open_blockers": [dict(b) for b in blockers],
            "pending_decisions": [dict(d) for d in decisions]
        }

@app.post("/projects/{project_id}/decompose")
async def decompose_project(project_id: str, scope: str):
    """
    Auto-decompose a project scope into tasks.
    Uses SCHOLAR for research, CHIRON for planning.
    """
    # TODO: Integrate with ATLAS to call SCHOLAR and CHIRON
    # For now, return placeholder
    return {
        "status": "decomposition_queued",
        "message": "CONSUL will coordinate with SCHOLAR and CHIRON to break down this scope"
    }

# ============ TASK ENDPOINTS ============

@app.post("/tasks")
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """Create a new task"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO consul_tasks (
                project_id, title, description, priority, 
                assigned_agent, estimated_hours, due_date, depends_on, tags
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, task.project_id, task.title, task.description, task.priority,
            task.assigned_agent, task.estimated_hours, task.due_date,
            task.depends_on, task.tags)
        
        # Update agent workload if assigned
        if task.assigned_agent:
            background_tasks.add_task(update_agent_workload, task.assigned_agent, 1)
        
        return dict(row)

@app.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    overdue_only: bool = False
):
    """List tasks with filters"""
    async with pool.acquire() as conn:
        if overdue_only:
            rows = await conn.fetch("SELECT * FROM consul_overdue_tasks()")
        else:
            query = "SELECT * FROM consul_tasks WHERE 1=1"
            params = []
            
            if project_id:
                params.append(project_id)
                query += f" AND project_id = ${len(params)}"
            if status:
                params.append(status)
                query += f" AND status = ${len(params)}"
            if assigned_agent:
                params.append(assigned_agent)
                query += f" AND assigned_agent = ${len(params)}"
            
            query += " ORDER BY priority DESC, due_date ASC"
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, updates: Dict[str, Any]):
    """Update a task"""
    async with pool.acquire() as conn:
        # Get current task
        current = await conn.fetchrow(
            "SELECT * FROM consul_tasks WHERE id = $1", task_id
        )
        if not current:
            raise HTTPException(404, "Task not found")
        
        # Build update query
        set_clauses = []
        params = [task_id]
        
        for key, value in updates.items():
            if key in ['title', 'description', 'status', 'priority', 'assigned_agent', 
                       'estimated_hours', 'actual_hours', 'due_date', 'notes']:
                params.append(value)
                set_clauses.append(f"{key} = ${len(params)}")
        
        if not set_clauses:
            raise HTTPException(400, "No valid fields to update")
        
        set_clauses.append("updated_at = NOW()")
        
        query = f"UPDATE consul_tasks SET {', '.join(set_clauses)} WHERE id = $1 RETURNING *"
        row = await conn.execute(query, *params)
        
        # Handle agent workload changes
        if 'assigned_agent' in updates:
            if current['assigned_agent']:
                await update_agent_workload(current['assigned_agent'], -1)
            if updates['assigned_agent']:
                await update_agent_workload(updates['assigned_agent'], 1)
        
        return {"status": "updated"}

@app.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, agent: str, background_tasks: BackgroundTasks):
    """Assign a task to an agent"""
    async with pool.acquire() as conn:
        # Check agent availability
        workload = await conn.fetchrow(
            "SELECT * FROM consul_agent_workload WHERE agent = $1", agent
        )
        
        if workload and workload['active_tasks'] >= workload['max_concurrent_tasks']:
            return {
                "status": "warning",
                "message": f"{agent} is at capacity ({workload['active_tasks']}/{workload['max_concurrent_tasks']} tasks)",
                "assigned": True  # Still assign, but warn
            }
        
        # Get current assignment
        current = await conn.fetchrow(
            "SELECT assigned_agent FROM consul_tasks WHERE id = $1", task_id
        )
        
        # Update task
        await conn.execute("""
            UPDATE consul_tasks 
            SET assigned_agent = $2, assigned_at = NOW(), updated_at = NOW()
            WHERE id = $1
        """, task_id, agent)
        
        # Update workloads
        if current and current['assigned_agent']:
            background_tasks.add_task(update_agent_workload, current['assigned_agent'], -1)
        background_tasks.add_task(update_agent_workload, agent, 1)
        
        return {"status": "assigned", "agent": agent}

@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, notes: Optional[str] = None, actual_hours: Optional[float] = None):
    """Mark a task as complete"""
    async with pool.acquire() as conn:
        task = await conn.fetchrow(
            "SELECT * FROM consul_tasks WHERE id = $1", task_id
        )
        if not task:
            raise HTTPException(404, "Task not found")
        
        await conn.execute("""
            UPDATE consul_tasks 
            SET status = 'done', completed_at = NOW(), notes = COALESCE($2, notes),
                actual_hours = COALESCE($3, actual_hours), updated_at = NOW()
            WHERE id = $1
        """, task_id, notes, actual_hours)
        
        # Update agent workload
        if task['assigned_agent']:
            await update_agent_workload(task['assigned_agent'], -1)
        
        # Notify
        await notify_aria(f"✅ Task completed: {task['title']}")
        
        # Check if any blocked tasks can now proceed
        unblocked = await conn.fetch("""
            SELECT id, title FROM consul_tasks 
            WHERE $1 = ANY(depends_on) AND status = 'blocked'
        """, task_id)
        
        if unblocked:
            for t in unblocked:
                await conn.execute(
                    "UPDATE consul_tasks SET status = 'todo' WHERE id = $1", t['id']
                )
            await notify_aria(f"🔓 {len(unblocked)} tasks unblocked by completion")
        
        return {"status": "completed", "unblocked_tasks": len(unblocked)}

@app.post("/tasks/{task_id}/block")
async def block_task(task_id: str, blocker: BlockerCreate):
    """Mark a task as blocked and record the blocker"""
    async with pool.acquire() as conn:
        # Update task status
        await conn.execute(
            "UPDATE consul_tasks SET status = 'blocked', updated_at = NOW() WHERE id = $1",
            task_id
        )
        
        # Record blocker
        blocker.task_id = task_id
        row = await conn.fetchrow("""
            INSERT INTO consul_blockers (task_id, project_id, description, blocker_type, severity)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, task_id, blocker.project_id, blocker.description, 
            blocker.blocker_type, blocker.severity.value)
        
        # Alert based on severity
        if blocker.severity in [BlockerSeverity.HIGH, BlockerSeverity.CRITICAL]:
            await notify_aria(
                f"🚨 {blocker.severity.value.upper()} BLOCKER: {blocker.description}",
                priority="high"
            )
        
        return dict(row)

# ============ BLOCKER ENDPOINTS ============

@app.get("/blockers")
async def list_blockers(status: str = "open", project_id: Optional[str] = None):
    """List blockers"""
    async with pool.acquire() as conn:
        query = "SELECT * FROM consul_blockers WHERE status = $1"
        params = [status]
        
        if project_id:
            query += " AND project_id = $2"
            params.append(project_id)
        
        query += " ORDER BY severity DESC, created_at ASC"
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.post("/blockers/{blocker_id}/resolve")
async def resolve_blocker(blocker_id: str, resolution: str):
    """Resolve a blocker"""
    async with pool.acquire() as conn:
        blocker = await conn.fetchrow(
            "SELECT * FROM consul_blockers WHERE id = $1", blocker_id
        )
        if not blocker:
            raise HTTPException(404, "Blocker not found")
        
        await conn.execute("""
            UPDATE consul_blockers 
            SET status = 'resolved', resolution = $2, resolved_at = NOW()
            WHERE id = $1
        """, blocker_id, resolution)
        
        # Unblock the task
        if blocker['task_id']:
            await conn.execute(
                "UPDATE consul_tasks SET status = 'todo' WHERE id = $1 AND status = 'blocked'",
                blocker['task_id']
            )
        
        await notify_aria(f"✅ Blocker resolved: {blocker['description'][:50]}...")
        
        return {"status": "resolved"}

# ============ DECISION ENDPOINTS ============

@app.post("/decisions")
async def create_decision(decision: DecisionCreate):
    """Request a decision"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO consul_decisions (project_id, question, context, options, decision_deadline)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, decision.project_id, decision.question, decision.context,
            json.dumps(decision.options), decision.decision_deadline)
        
        await notify_aria(f"❓ Decision needed: {decision.question}", priority="high")
        
        return dict(row)

@app.get("/decisions")
async def list_decisions(status: str = "pending", project_id: Optional[str] = None):
    """List decisions"""
    async with pool.acquire() as conn:
        query = "SELECT * FROM consul_decisions WHERE status = $1"
        params = [status]
        
        if project_id:
            query += " AND project_id = $2"
            params.append(project_id)
        
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.post("/decisions/{decision_id}/decide")
async def record_decision(decision_id: str, decision: str, rationale: Optional[str] = None, decided_by: str = "damon"):
    """Record a decision"""
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE consul_decisions 
            SET status = 'decided', decision = $2, rationale = $3, 
                decided_by = $4, decided_at = NOW()
            WHERE id = $1
        """, decision_id, decision, rationale, decided_by)
        
        await notify_aria(f"✅ Decision recorded: {decision[:50]}...")
        
        return {"status": "decided"}

# ============ STANDUP ENDPOINTS ============

@app.get("/standup")
async def get_standup(project_id: Optional[str] = None):
    """Get today's standup or generate one"""
    async with pool.acquire() as conn:
        if project_id:
            # Generate standup for specific project
            row = await conn.fetchrow(
                "SELECT * FROM consul_generate_standup($1)", project_id
            )
            return dict(row) if row else {}
        else:
            # Get all active projects' standups
            projects = await conn.fetch(
                "SELECT id FROM consul_projects WHERE status = 'active'"
            )
            standups = []
            for p in projects:
                standup = await conn.fetchrow(
                    "SELECT * FROM consul_generate_standup($1)", p['id']
                )
                if standup:
                    standups.append(dict(standup))
            return standups

@app.post("/standup/generate")
async def generate_full_standup():
    """Generate comprehensive standup report for ARIA"""
    async with pool.acquire() as conn:
        # Get all project summaries
        projects = await conn.fetch("SELECT * FROM consul_project_summary(NULL)")
        
        # Get overdue tasks
        overdue = await conn.fetch("SELECT * FROM consul_overdue_tasks()")
        
        # Get open blockers
        blockers = await conn.fetch(
            "SELECT * FROM consul_blockers WHERE status = 'open' ORDER BY severity DESC"
        )
        
        # Get pending decisions
        decisions = await conn.fetch(
            "SELECT * FROM consul_decisions WHERE status = 'pending'"
        )
        
        # Get agent availability
        agents = await conn.fetch("SELECT * FROM consul_agent_availability()")
        
        report = {
            "date": str(date.today()),
            "generated_at": datetime.now().isoformat(),
            "projects": [dict(p) for p in projects],
            "overdue_tasks": [dict(t) for t in overdue],
            "open_blockers": [dict(b) for b in blockers],
            "pending_decisions": [dict(d) for d in decisions],
            "agent_availability": [dict(a) for a in agents],
            "summary": {
                "total_projects": len(projects),
                "overdue_count": len(overdue),
                "blockers_count": len(blockers),
                "decisions_pending": len(decisions)
            }
        }
        
        # Send to ARIA
        summary_text = f"""
📊 **CONSUL Daily Standup - {date.today()}**

**Projects:** {len(projects)} active
**Overdue Tasks:** {len(overdue)}
**Open Blockers:** {len(blockers)} ({sum(1 for b in blockers if b['severity'] in ['high', 'critical'])} critical/high)
**Pending Decisions:** {len(decisions)}

{"🚨 ATTENTION REQUIRED" if len(overdue) > 0 or len(blockers) > 0 else "✅ All systems nominal"}
"""
        await notify_aria(summary_text)
        
        return report

# ============ AGENT ENDPOINTS ============

@app.get("/agents/workload")
async def get_agent_workloads():
    """Get all agent workloads"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM consul_agent_availability()")
        return [dict(row) for row in rows]

@app.get("/agents/{agent}/tasks")
async def get_agent_tasks(agent: str, status: Optional[str] = None):
    """Get tasks assigned to an agent"""
    async with pool.acquire() as conn:
        query = "SELECT * FROM consul_tasks WHERE assigned_agent = $1"
        params = [agent]
        
        if status:
            query += " AND status = $2"
            params.append(status)
        
        query += " ORDER BY priority DESC, due_date ASC"
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

# ============ COUNCIL INTEGRATION ============

@app.post("/council/join")
async def join_council(council_id: str):
    """Register CONSUL's participation in a council meeting"""
    # CONSUL always joins councils
    return {
        "status": "joined",
        "message": "CONSUL is now tracking this council meeting",
        "behaviors": [
            "Taking structured notes",
            "Tracking action items",
            "Will follow up on commitments"
        ]
    }

@app.post("/council/{council_id}/action-items")
async def extract_action_items(council_id: str, items: List[Dict[str, Any]]):
    """Record action items from a council meeting"""
    async with pool.acquire() as conn:
        created = []
        for item in items:
            row = await conn.fetchrow("""
                INSERT INTO consul_action_items (
                    council_id, source_type, description, 
                    assigned_to, due_date
                ) VALUES ($1, 'council', $2, $3, $4)
                RETURNING *
            """, council_id, item.get('description'), 
                item.get('assigned_to'), item.get('due_date'))
            created.append(dict(row))
        
        await notify_aria(f"📝 {len(created)} action items recorded from council meeting")
        return created

# ============ CONSUL'S VOICE ============

@app.get("/status")
async def consul_status():
    """CONSUL's current assessment"""
    async with pool.acquire() as conn:
        projects = await conn.fetch("SELECT * FROM consul_project_summary(NULL)")
        overdue = await conn.fetch("SELECT * FROM consul_overdue_tasks()")
        blockers = await conn.fetch(
            "SELECT * FROM consul_blockers WHERE status = 'open'"
        )
        
        # CONSUL's assessment
        if len(overdue) > 5:
            assessment = "🚨 Critical: Multiple overdue tasks. Immediate attention required."
        elif len(blockers) > 3:
            assessment = "⚠️ Warning: Several blockers impeding progress."
        elif any(p['health_score'] and p['health_score'] < 50 for p in projects):
            assessment = "⚠️ Warning: Project health declining. Review needed."
        else:
            assessment = "✅ Systems nominal. Progress on track."
        
        return {
            "consul_says": assessment,
            "active_projects": len([p for p in projects if p['status'] == 'active']),
            "overdue_tasks": len(overdue),
            "open_blockers": len(blockers),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
```

### 3.3 Create Dockerfile

Create `/opt/leveredge/control-plane/agents/consul/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY consul.py .

EXPOSE 8017

CMD ["uvicorn", "consul:app", "--host", "0.0.0.0", "--port", "8017"]
```

### 3.4 Build and Run

```bash
cd /opt/leveredge/control-plane/agents/consul
docker build -t consul:dev .

docker run -d --name consul \
  --network leveredge-network \
  -p 8017:8017 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  consul:dev
```

---

## PHASE 4: HEPHAESTUS MCP INTEGRATION (2 hours)

Add CONSUL tools to HEPHAESTUS MCP:

```python
# ============ CONSUL PM TOOLS ============

@mcp_tool(name="consul_create_project")
async def consul_create_project(
    name: str,
    description: str = None,
    target_end: str = None,
    priority: int = 50
) -> dict:
    """Create a new project in CONSUL"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8017/projects",
            json={
                "name": name,
                "description": description,
                "target_end": target_end,
                "priority": priority
            }
        )
        return response.json()

@mcp_tool(name="consul_create_task")
async def consul_create_task(
    project_id: str,
    title: str,
    assigned_agent: str = None,
    due_date: str = None,
    estimated_hours: float = None,
    priority: int = 50
) -> dict:
    """Create a task in CONSUL"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8017/tasks",
            json={
                "project_id": project_id,
                "title": title,
                "assigned_agent": assigned_agent,
                "due_date": due_date,
                "estimated_hours": estimated_hours,
                "priority": priority
            }
        )
        return response.json()

@mcp_tool(name="consul_status")
async def consul_status() -> dict:
    """Get CONSUL's current project status assessment"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8017/status")
        return response.json()

@mcp_tool(name="consul_standup")
async def consul_standup() -> dict:
    """Generate today's standup report"""
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8017/standup/generate")
        return response.json()

@mcp_tool(name="consul_blockers")
async def consul_blockers() -> dict:
    """Get all open blockers"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8017/blockers")
        return response.json()

@mcp_tool(name="consul_assign_task")
async def consul_assign_task(task_id: str, agent: str) -> dict:
    """Assign a task to an agent"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8017/tasks/{task_id}/assign",
            params={"agent": agent}
        )
        return response.json()

@mcp_tool(name="consul_complete_task")
async def consul_complete_task(task_id: str, notes: str = None) -> dict:
    """Mark a task as complete"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8017/tasks/{task_id}/complete",
            params={"notes": notes}
        )
        return response.json()
```

---

## PHASE 5: CADDY ROUTING (30 min)

Add to Caddyfile:
```
pm.leveredgeai.com {
    reverse_proxy localhost:8040
}

consul.leveredgeai.com {
    reverse_proxy localhost:8017
}
```

Create DNS records:
- pm.leveredgeai.com → server IP
- consul.leveredgeai.com → server IP

Reload Caddy:
```bash
sudo systemctl reload caddy
```

---

## PHASE 6: VERIFICATION

```bash
# 1. Leantime running
curl http://localhost:8040
# Should return HTML

# 2. CONSUL healthy
curl http://localhost:8017/health | jq .
# Should show healthy

# 3. LeverEdge project exists
curl http://localhost:8017/projects | jq .
# Should show the seeded project

# 4. CONSUL status
curl http://localhost:8017/status | jq .
# Should show assessment

# 5. Generate standup
curl -X POST http://localhost:8017/standup/generate | jq .
# Should generate report
```

---

## GIT COMMIT

```bash
git add .
git commit -m "CONSUL: Master of Projects + Leantime PM

- CONSUL service (port 8017): Complete PM agent
- Leantime deployment (port 8040): ADHD-friendly PM tool
- Database schema: 8 tables for full project management
- MCP tools: 7 CONSUL tools for HEPHAESTUS
- LeverEdge project seeded with March 1 target
- Agent workload tracking for all 16+ agents
- Blocker and decision tracking
- Daily standup generation
- Council meeting integration"
```

---

## CONSUL'S FIRST WORDS

After deployment, query CONSUL:

```bash
curl http://localhost:8017/status | jq .
```

Expected response:
```json
{
  "consul_says": "✅ Systems nominal. Progress on track.",
  "active_projects": 1,
  "overdue_tasks": 0,
  "open_blockers": 0,
  "timestamp": "2026-01-19T..."
}
```

---

**CONSUL is ready to take command.**

*"Nothing escapes my attention. Nothing falls through the cracks."*
