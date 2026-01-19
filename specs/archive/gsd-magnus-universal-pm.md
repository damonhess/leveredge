# GSD: MAGNUS - Universal Project Master

**Priority:** HIGH
**Estimated Time:** 28 hours (full) / 12 hours (MVP)
**Spec:** /opt/leveredge/specs/MAGNUS-UNIVERSAL-PM-SPEC.md

---

## MISSION

Build MAGNUS - the chess master PM agent who:
1. Sees the entire board (all projects, all tools, all dependencies)
2. Calculates 10 moves ahead (risk assessment, critical path)
3. Speaks every PM language (Asana, Jira, Monday, Notion, Linear, etc.)
4. Uses Leantime internally (ADHD-friendly)
5. Adapts to any client's preferred tool

**Tagline:** "Every move calculated. Every piece in position. Checkmate is inevitable."

---

## CRITICAL: NAMING CONVENTION

- Agent name: **MAGNUS**
- Database tables: `magnus_*` (NOT consul_*)
- API endpoints: `/magnus/*` or standard REST
- MCP tools: `magnus_*`
- Service name: `magnus`
- Container: `magnus`
- Port: **8019** (CHIRON uses 8017)

---

## PHASE 1: DEPLOY PM TOOLS (2 hours)

### 1.1 Create PM Tools Directory

```bash
mkdir -p /opt/leveredge/pm-tools
```

### 1.2 Create Docker Compose

Create `/opt/leveredge/pm-tools/docker-compose.yml`:

```yaml
version: '3.8'

services:
  # ============ LEANTIME (ADHD-Friendly Daily Driver) ============
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

  # ============ OPENPROJECT (Enterprise/Complex Projects) ============
  openproject:
    image: openproject/community:13
    container_name: openproject
    restart: unless-stopped
    ports:
      - "8041:80"
    environment:
      OPENPROJECT_SECRET_KEY_BASE: ${OPENPROJECT_SECRET:-supersecretkeybase123456789}
      OPENPROJECT_HOST__NAME: projects.leveredgeai.com
      OPENPROJECT_HTTPS: "true"
      OPENPROJECT_DEFAULT__LANGUAGE: en
      DATABASE_URL: postgres://openproject:${OPENPROJECT_DB_PASSWORD:-openprojectpass123}@openproject-db/openproject
    volumes:
      - openproject_data:/var/openproject/assets
    depends_on:
      - openproject-db
    networks:
      - leveredge-network

  openproject-db:
    image: postgres:13
    container_name: openproject-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: openproject
      POSTGRES_PASSWORD: ${OPENPROJECT_DB_PASSWORD:-openprojectpass123}
      POSTGRES_DB: openproject
    volumes:
      - openproject_postgres:/var/lib/postgresql/data
    networks:
      - leveredge-network

volumes:
  leantime_data:
  leantime_plugins:
  leantime_mysql:
  openproject_data:
  openproject_postgres:

networks:
  leveredge-network:
    external: true
```

### 1.3 Start PM Tools

```bash
cd /opt/leveredge/pm-tools
docker compose up -d
```

### 1.4 Add Caddy Routes

Add to Caddyfile:
```
pm.leveredgeai.com {
    reverse_proxy localhost:8040
}

projects.leveredgeai.com {
    reverse_proxy localhost:8041
}

magnus.leveredgeai.com {
    reverse_proxy localhost:8017
}
```

### 1.5 Create DNS Records
- pm.leveredgeai.com → server IP (Leantime)
- projects.leveredgeai.com → server IP (OpenProject)
- magnus.leveredgeai.com → server IP (MAGNUS API)

### 1.6 Reload Caddy
```bash
sudo systemctl reload caddy
```

### 1.7 Initial Setup
1. **Leantime:** https://pm.leveredgeai.com - Complete wizard, create admin
2. **OpenProject:** https://projects.leveredgeai.com - Complete wizard, create admin
3. **Store credentials in AEGIS**

---

## PHASE 2: MAGNUS DATABASE SCHEMA (2 hours)

### 2.1 Create Migration

Create `/opt/leveredge/database/migrations/20260119_magnus_schema.sql`:

```sql
-- ============================================================
-- MAGNUS: Universal Project Master
-- Database Schema
-- ============================================================

-- Projects
CREATE TABLE IF NOT EXISTS magnus_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'planning' CHECK (status IN (
        'planning', 'active', 'on_hold', 'completed', 'cancelled'
    )),
    priority INTEGER DEFAULT 50 CHECK (priority >= 1 AND priority <= 100),
    
    owner TEXT DEFAULT 'damon',
    pm_agent TEXT DEFAULT 'MAGNUS',
    client_name TEXT,
    source_tool TEXT DEFAULT 'leantime',
    
    target_start DATE,
    target_end DATE,
    actual_start DATE,
    actual_end DATE,
    
    original_scope JSONB DEFAULT '{}',
    current_scope JSONB DEFAULT '{}',
    
    tags TEXT[] DEFAULT '{}',
    template_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Tasks
CREATE TABLE IF NOT EXISTS magnus_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    parent_task_id UUID REFERENCES magnus_tasks(id) ON DELETE SET NULL,
    
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'todo' CHECK (status IN (
        'todo', 'in_progress', 'blocked', 'review', 'done', 'cancelled'
    )),
    priority TEXT DEFAULT 'medium' CHECK (priority IN (
        'critical', 'high', 'medium', 'low'
    )),
    
    assigned_agent TEXT,
    assigned_at TIMESTAMPTZ,
    
    estimated_hours DECIMAL(6,2),
    actual_hours DECIMAL(6,2) DEFAULT 0,
    
    due_date DATE,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    depends_on UUID[] DEFAULT '{}',
    
    tags TEXT[] DEFAULT '{}',
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Blockers
CREATE TABLE IF NOT EXISTS magnus_blockers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    
    description TEXT NOT NULL,
    blocker_type TEXT CHECK (blocker_type IN (
        'dependency', 'decision_needed', 'resource', 'external', 'technical', 'other'
    )),
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'escalated', 'resolved')),
    escalated_to TEXT,
    escalated_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    resolution TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decisions
CREATE TABLE IF NOT EXISTS magnus_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    task_id UUID REFERENCES magnus_tasks(id) ON DELETE SET NULL,
    
    question TEXT NOT NULL,
    context TEXT,
    options JSONB DEFAULT '[]',
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'decided', 'deferred')),
    decision TEXT,
    decided_by TEXT,
    decided_at TIMESTAMPTZ,
    rationale TEXT,
    
    decision_deadline DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scope changes
CREATE TABLE IF NOT EXISTS magnus_scope_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    
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
CREATE TABLE IF NOT EXISTS magnus_standups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
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
CREATE TABLE IF NOT EXISTS magnus_agent_workload (
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

-- Action items
CREATE TABLE IF NOT EXISTS magnus_action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    council_id UUID,
    source_type TEXT CHECK (source_type IN ('council', 'standup', 'manual', 'aria')),
    source_context TEXT,
    
    description TEXT NOT NULL,
    assigned_to TEXT,
    due_date DATE,
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled')),
    completed_at TIMESTAMPTZ,
    
    task_id UUID REFERENCES magnus_tasks(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- PM Tool Connections
CREATE TABLE IF NOT EXISTS magnus_pm_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    tool_name TEXT NOT NULL,
    connection_name TEXT NOT NULL,
    
    instance_url TEXT,
    workspace_id TEXT,
    
    aegis_credential_key TEXT NOT NULL,
    
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'error', 'disconnected')),
    last_sync TIMESTAMPTZ,
    last_error TEXT,
    
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 15,
    webhook_registered BOOLEAN DEFAULT FALSE,
    webhook_id TEXT,
    webhook_secret TEXT,
    
    config JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tool_name, connection_name)
);

-- Project mappings
CREATE TABLE IF NOT EXISTS magnus_project_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    magnus_project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,
    
    external_project_id TEXT NOT NULL,
    external_project_name TEXT,
    external_project_url TEXT,
    
    sync_direction TEXT DEFAULT 'bidirectional' CHECK (sync_direction IN (
        'from_source', 'to_source', 'bidirectional'
    )),
    
    field_mappings JSONB DEFAULT '{}',
    
    last_sync TIMESTAMPTZ,
    last_sync_status TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(connection_id, external_project_id)
);

-- Task mappings
CREATE TABLE IF NOT EXISTS magnus_task_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    magnus_task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,
    project_mapping_id UUID REFERENCES magnus_project_mappings(id) ON DELETE CASCADE,
    
    external_task_id TEXT NOT NULL,
    external_task_url TEXT,
    
    last_sync TIMESTAMPTZ,
    last_sync_hash TEXT,
    sync_conflict BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(connection_id, external_task_id)
);

-- Sync log
CREATE TABLE IF NOT EXISTS magnus_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    connection_id UUID REFERENCES magnus_pm_connections(id),
    project_mapping_id UUID REFERENCES magnus_project_mappings(id),
    
    sync_type TEXT CHECK (sync_type IN ('full', 'incremental', 'webhook', 'manual')),
    direction TEXT CHECK (direction IN ('from_source', 'to_source', 'bidirectional')),
    
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    items_synced INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_deleted INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    
    error_details JSONB DEFAULT '[]',
    
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'partial'))
);

-- Project templates
CREATE TABLE IF NOT EXISTS magnus_project_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    
    phases JSONB DEFAULT '[]',
    default_tasks JSONB DEFAULT '[]',
    estimated_duration_days INTEGER,
    
    default_tool TEXT DEFAULT 'leantime',
    tags TEXT[] DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_magnus_projects_status ON magnus_projects(status);
CREATE INDEX IF NOT EXISTS idx_magnus_projects_client ON magnus_projects(client_name);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_project ON magnus_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_status ON magnus_tasks(status);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_agent ON magnus_tasks(assigned_agent);
CREATE INDEX IF NOT EXISTS idx_magnus_tasks_due ON magnus_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_magnus_blockers_status ON magnus_blockers(status);
CREATE INDEX IF NOT EXISTS idx_magnus_decisions_status ON magnus_decisions(status);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Get project summary
CREATE OR REPLACE FUNCTION magnus_project_summary(p_project_id UUID DEFAULT NULL)
RETURNS TABLE (
    id UUID,
    name TEXT,
    status TEXT,
    client_name TEXT,
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
        p.client_name,
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
        (SELECT COUNT(*) FROM magnus_blockers b WHERE b.project_id = p.id AND b.status = 'open'),
        (SELECT COUNT(*) FROM magnus_decisions d WHERE d.project_id = p.id AND d.status = 'pending'),
        CASE 
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 3 THEN 40
            WHEN (p.target_end - CURRENT_DATE) < 7 AND COUNT(t.id) FILTER (WHERE t.status = 'done')::DECIMAL / NULLIF(COUNT(t.id), 0) < 0.8 THEN 50
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 0 THEN 70
            ELSE 90
        END::DECIMAL
    FROM magnus_projects p
    LEFT JOIN magnus_tasks t ON t.project_id = p.id
    WHERE (p_project_id IS NULL OR p.id = p_project_id)
    AND p.status IN ('planning', 'active')
    GROUP BY p.id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- SEED DATA
-- ============================================================

-- Project templates
INSERT INTO magnus_project_templates (name, description, phases, default_tasks, estimated_duration_days) VALUES
(
    'automation_project',
    'Standard client automation project',
    '[{"name": "Discovery", "duration_days": 3}, {"name": "Design", "duration_days": 5}, {"name": "Build", "duration_days": 10}, {"name": "Test", "duration_days": 3}, {"name": "Deploy", "duration_days": 2}]'::jsonb,
    '[{"title": "Discovery call", "phase": "Discovery"}, {"title": "Requirements doc", "phase": "Discovery"}, {"title": "Solution design", "phase": "Design"}, {"title": "Build automation", "phase": "Build"}, {"title": "Testing", "phase": "Test"}, {"title": "Deploy", "phase": "Deploy"}]'::jsonb,
    25
),
(
    'agent_development',
    'Building a new LeverEdge agent',
    '[{"name": "Specification", "duration_days": 2}, {"name": "Development", "duration_days": 5}, {"name": "Testing", "duration_days": 2}, {"name": "Integration", "duration_days": 2}]'::jsonb,
    '[{"title": "Write agent spec", "phase": "Specification"}, {"title": "Database schema", "phase": "Development"}, {"title": "FastAPI service", "phase": "Development"}, {"title": "Unit tests", "phase": "Testing"}, {"title": "MCP tools", "phase": "Integration"}]'::jsonb,
    12
)
ON CONFLICT (name) DO NOTHING;

-- Internal connections
INSERT INTO magnus_pm_connections (tool_name, connection_name, instance_url, aegis_credential_key, status, config)
VALUES 
('leantime', 'LeverEdge Internal', 'http://leantime:80', 'leantime_internal', 'active', '{"is_primary": true}'::jsonb),
('openproject', 'LeverEdge Enterprise', 'http://openproject:80', 'openproject_internal', 'active', '{"use_for": "enterprise"}'::jsonb)
ON CONFLICT DO NOTHING;

-- LeverEdge Launch project
INSERT INTO magnus_projects (name, description, status, priority, owner, pm_agent, target_start, target_end, source_tool)
VALUES (
    'LeverEdge Agency Launch',
    'Build and launch LeverEdge AI automation agency by March 1, 2026',
    'active', 100, 'damon', 'MAGNUS', '2026-01-11', '2026-03-01', 'leantime'
) ON CONFLICT DO NOTHING;

-- Agent workloads
INSERT INTO magnus_agent_workload (agent, max_concurrent_tasks) VALUES
('CHRONOS', 5), ('HADES', 3), ('AEGIS', 3), ('HERMES', 10),
('SCHOLAR', 3), ('CHIRON', 3), ('ATHENA', 5), ('MUSE', 3),
('QUILL', 5), ('VARYS', 3), ('MAGNUS', 10), ('HEPHAESTUS', 5)
ON CONFLICT (agent) DO NOTHING;
```

### 2.2 Run Migration

```bash
psql $DEV_DATABASE_URL -f /opt/leveredge/database/migrations/20260119_magnus_schema.sql
```

---

## PHASE 3: MAGNUS SERVICE (4 hours)

### 3.1 Create Service Structure

```bash
mkdir -p /opt/leveredge/control-plane/agents/magnus/adapters
```

### 3.2 Create Adapter Base Class

Create `/opt/leveredge/control-plane/agents/magnus/adapters/base.py`
(Use the PMAdapter base class from the full CONSUL spec)

### 3.3 Create Leantime Adapter

Create `/opt/leveredge/control-plane/agents/magnus/adapters/leantime.py`
(Implement LeantimeAdapter as specified in full spec)

### 3.4 Create Main Service

Create `/opt/leveredge/control-plane/agents/magnus/magnus.py`:

```python
"""
MAGNUS - Universal Project Master
Port: 8017
Domain: CHANCERY

Every move calculated. Every piece in position. Checkmate is inevitable.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
import os
import asyncpg
import httpx
import json

app = FastAPI(
    title="MAGNUS - Universal Project Master",
    description="Every move calculated. Every piece in position. Checkmate is inevitable.",
    version="1.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")
pool: asyncpg.Pool = None

@app.on_event("startup")
async def startup():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()

# ============ HEALTH ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "MAGNUS - Universal Project Master",
        "port": 8017,
        "tagline": "Every move calculated. Every piece in position. Checkmate is inevitable."
    }

@app.get("/status")
async def magnus_status():
    """MAGNUS's current assessment of the board"""
    async with pool.acquire() as conn:
        projects = await conn.fetch("SELECT * FROM magnus_project_summary(NULL)")
        overdue = await conn.fetch("""
            SELECT COUNT(*) as count FROM magnus_tasks 
            WHERE due_date < CURRENT_DATE AND status NOT IN ('done', 'cancelled')
        """)
        blockers = await conn.fetch(
            "SELECT COUNT(*) as count FROM magnus_blockers WHERE status = 'open'"
        )
        
        overdue_count = overdue[0]['count'] if overdue else 0
        blocker_count = blockers[0]['count'] if blockers else 0
        
        if overdue_count > 5:
            assessment = "🚨 Critical position. Multiple pieces under attack. Immediate action required."
        elif blocker_count > 3:
            assessment = "⚠️ Board congestion. Several pieces blocked. Need to clear lanes."
        else:
            assessment = "✅ Strong position. Pieces are coordinated. Continuing the attack."
        
        return {
            "magnus_says": assessment,
            "active_projects": len([p for p in projects if p['status'] == 'active']),
            "overdue_tasks": overdue_count,
            "open_blockers": blocker_count,
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "timestamp": datetime.now().isoformat()
        }

# ============ PROJECTS ============

@app.get("/projects")
async def list_projects():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM magnus_project_summary(NULL)")
        return [dict(row) for row in rows]

@app.post("/projects")
async def create_project(
    name: str,
    description: str = None,
    target_end: date = None,
    client_name: str = None,
    template: str = None
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_projects (name, description, target_end, client_name, template_used)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, name, description, target_end, client_name, template)
        return dict(row)

# ============ TASKS ============

@app.get("/tasks")
async def list_tasks(
    project_id: str = None,
    status: str = None,
    overdue: bool = False
):
    async with pool.acquire() as conn:
        if overdue:
            rows = await conn.fetch("""
                SELECT t.*, p.name as project_name
                FROM magnus_tasks t
                JOIN magnus_projects p ON t.project_id = p.id
                WHERE t.due_date < CURRENT_DATE
                AND t.status NOT IN ('done', 'cancelled')
            """)
        else:
            query = "SELECT * FROM magnus_tasks WHERE 1=1"
            params = []
            if project_id:
                params.append(project_id)
                query += f" AND project_id = ${len(params)}"
            if status:
                params.append(status)
                query += f" AND status = ${len(params)}"
            query += " ORDER BY priority DESC, due_date"
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.post("/tasks")
async def create_task(
    project_id: str,
    title: str,
    assigned_agent: str = None,
    due_date: date = None,
    priority: str = "medium",
    estimated_hours: float = None
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_tasks (project_id, title, assigned_agent, due_date, priority, estimated_hours)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, project_id, title, assigned_agent, due_date, priority, estimated_hours)
        return dict(row)

@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, notes: str = None):
    async with pool.acquire() as conn:
        await conn.execute("""
            UPDATE magnus_tasks SET status = 'done', completed_at = NOW(), notes = COALESCE($2, notes)
            WHERE id = $1
        """, task_id, notes)
        return {"status": "completed", "task_id": task_id}

# ============ STANDUP ============

@app.post("/standup/generate")
async def generate_standup():
    async with pool.acquire() as conn:
        projects = await conn.fetch("SELECT * FROM magnus_project_summary(NULL)")
        overdue = await conn.fetch("""
            SELECT t.*, p.name as project_name FROM magnus_tasks t
            JOIN magnus_projects p ON t.project_id = p.id
            WHERE t.due_date < CURRENT_DATE AND t.status NOT IN ('done', 'cancelled')
        """)
        blockers = await conn.fetch("SELECT * FROM magnus_blockers WHERE status = 'open'")
        
        return {
            "date": str(date.today()),
            "projects": [dict(p) for p in projects],
            "overdue_tasks": [dict(t) for t in overdue],
            "open_blockers": [dict(b) for b in blockers],
            "summary": {
                "total_projects": len(projects),
                "overdue_count": len(overdue),
                "blockers_count": len(blockers)
            }
        }

# ============ CONNECTIONS ============

@app.get("/connections")
async def list_connections():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM magnus_pm_connections ORDER BY tool_name")
        return [dict(row) for row in rows]

@app.get("/connections/supported")
async def supported_tools():
    return [
        {"name": "leantime", "status": "implemented"},
        {"name": "openproject", "status": "stub"},
        {"name": "asana", "status": "planned"},
        {"name": "jira", "status": "planned"},
        {"name": "monday", "status": "planned"},
        {"name": "notion", "status": "planned"},
        {"name": "linear", "status": "planned"},
        {"name": "clickup", "status": "planned"},
        {"name": "trello", "status": "planned"}
    ]

# ============ TEMPLATES ============

@app.get("/templates")
async def list_templates():
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM magnus_project_templates")
        return [dict(row) for row in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
```

### 3.5 Create Dockerfile

Create `/opt/leveredge/control-plane/agents/magnus/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    asyncpg \
    httpx \
    pydantic

COPY adapters/ ./adapters/
COPY magnus.py .

EXPOSE 8017

CMD ["uvicorn", "magnus:app", "--host", "0.0.0.0", "--port", "8017"]
```

### 3.6 Build and Run

```bash
cd /opt/leveredge/control-plane/agents/magnus
docker build -t magnus:dev .

docker run -d --name magnus \
  --network leveredge-network \
  -p 8017:8017 \
  -e DATABASE_URL="$DEV_DATABASE_URL" \
  magnus:dev
```

---

## PHASE 4: MCP TOOLS (2 hours)

Add to HEPHAESTUS MCP:

```python
# ============ MAGNUS PM TOOLS ============

@mcp_tool(name="magnus_status")
async def magnus_status() -> dict:
    """Get MAGNUS's assessment of the board"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8017/status")
        return response.json()

@mcp_tool(name="magnus_create_project")
async def magnus_create_project(
    name: str,
    description: str = None,
    target_end: str = None,
    client_name: str = None,
    template: str = None
) -> dict:
    """Create a project"""

@mcp_tool(name="magnus_create_task")
async def magnus_create_task(
    project_id: str,
    title: str,
    assigned_agent: str = None,
    due_date: str = None,
    priority: str = "medium"
) -> dict:
    """Create a task"""

@mcp_tool(name="magnus_standup")
async def magnus_standup() -> dict:
    """Generate daily standup"""

@mcp_tool(name="magnus_complete_task")
async def magnus_complete_task(task_id: str, notes: str = None) -> dict:
    """Mark task complete"""

@mcp_tool(name="magnus_overdue")
async def magnus_overdue() -> dict:
    """Get overdue tasks"""

@mcp_tool(name="magnus_templates")
async def magnus_templates() -> dict:
    """List project templates"""
```

---

## VERIFICATION

```bash
# 1. PM Tools running
curl http://localhost:8040  # Leantime
curl http://localhost:8041  # OpenProject

# 2. MAGNUS healthy
curl http://localhost:8017/health | jq .

# 3. Status
curl http://localhost:8017/status | jq .

# 4. Projects
curl http://localhost:8017/projects | jq .

# 5. Templates
curl http://localhost:8017/templates | jq .

# 6. Generate standup
curl -X POST http://localhost:8017/standup/generate | jq .
```

---

## GIT COMMIT

```bash
git add .
git commit -m "MAGNUS: Universal Project Master

- Leantime + OpenProject deployment
- MAGNUS service (port 8017)
- Database schema with magnus_* tables
- Project templates
- MCP tools integration
- LeverEdge Launch project seeded

Chess master. Every move calculated."
```

---

## MAGNUS'S FIRST WORDS

```json
{
  "magnus_says": "✅ Strong position. Pieces are coordinated. Continuing the attack.",
  "active_projects": 1,
  "overdue_tasks": 0,
  "open_blockers": 0,
  "days_to_launch": 41,
  "timestamp": "2026-01-19T..."
}
```

---

*"Every move calculated. Every piece in position. Checkmate is inevitable."*
