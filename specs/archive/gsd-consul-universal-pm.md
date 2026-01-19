# GSD: CONSUL - Universal Project Master (Full Build)

**Priority:** HIGH
**Estimated Time:** 28 hours (full) / 12 hours (MVP)
**Spec:** /opt/leveredge/specs/CONSUL-UNIVERSAL-PM-SPEC.md

---

## MISSION

Build CONSUL as the Universal Project Master who:
1. Speaks EVERY PM tool language (Asana, Jira, Monday, Notion, Linear, etc.)
2. Owns the LeverEdge build via Leantime (ADHD-friendly)
3. Manages enterprise/client projects via OpenProject
4. Interfaces with ANY client's preferred PM tool
5. Maintains unified view across ALL connected tools

**Tagline:** "I speak every PM language. Nothing escapes my attention."

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
  # ============ LEANTIME (ADHD-Friendly) ============
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

  # ============ OPENPROJECT (Enterprise) ============
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

consul.leveredgeai.com {
    reverse_proxy localhost:8017
}
```

### 1.5 Create DNS Records
- pm.leveredgeai.com → server IP (Leantime)
- projects.leveredgeai.com → server IP (OpenProject)
- consul.leveredgeai.com → server IP (CONSUL API)

### 1.6 Reload Caddy
```bash
sudo systemctl reload caddy
```

### 1.7 Initial Setup
1. **Leantime:** https://pm.leveredgeai.com - Complete wizard, create admin
2. **OpenProject:** https://projects.leveredgeai.com - Complete wizard, create admin
3. **Store credentials in AEGIS**

---

## PHASE 2: CONSUL DATABASE SCHEMA (2 hours)

### 2.1 Create Migration

Create `/opt/leveredge/database/migrations/20260119_consul_universal_schema.sql`:

```sql
-- ============================================================
-- CONSUL: Universal Project Master
-- Database Schema v2.0
-- ============================================================

-- ============================================================
-- CORE TABLES
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
    client_name TEXT,                      -- For client projects
    
    -- Source tool (where it was created)
    source_tool TEXT DEFAULT 'leantime',
    
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
    template_used TEXT,
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
    priority TEXT DEFAULT 'medium' CHECK (priority IN (
        'critical', 'high', 'medium', 'low'
    )),
    
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
    
    -- Dependencies
    depends_on UUID[] DEFAULT '{}',
    
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
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'decided', 'deferred')),
    decision TEXT,
    decided_by TEXT,
    decided_at TIMESTAMPTZ,
    rationale TEXT,
    
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
    
    council_id UUID,
    source_type TEXT CHECK (source_type IN ('council', 'standup', 'manual', 'aria')),
    source_context TEXT,
    
    description TEXT NOT NULL,
    assigned_to TEXT,
    due_date DATE,
    
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'done', 'cancelled')),
    completed_at TIMESTAMPTZ,
    
    task_id UUID REFERENCES consul_tasks(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PM TOOL INTEGRATION TABLES
-- ============================================================

-- PM Tool Connections
CREATE TABLE IF NOT EXISTS consul_pm_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    tool_name TEXT NOT NULL,               -- "leantime", "asana", "jira", etc.
    connection_name TEXT NOT NULL,          -- "LeverEdge Internal", "Client ABC's Jira"
    
    instance_url TEXT,                      -- For self-hosted tools
    workspace_id TEXT,                      -- Workspace/org identifier
    
    aegis_credential_key TEXT NOT NULL,     -- Reference to AEGIS
    
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'error', 'disconnected')),
    last_sync TIMESTAMPTZ,
    last_error TEXT,
    
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_interval_minutes INTEGER DEFAULT 15,
    webhook_registered BOOLEAN DEFAULT FALSE,
    webhook_id TEXT,
    webhook_secret TEXT,
    
    -- Tool-specific config
    config JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(tool_name, connection_name)
);

-- Project mappings to external tools
CREATE TABLE IF NOT EXISTS consul_project_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    consul_project_id UUID REFERENCES consul_projects(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    
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

-- Task mappings to external tools
CREATE TABLE IF NOT EXISTS consul_task_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    consul_task_id UUID REFERENCES consul_tasks(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    project_mapping_id UUID REFERENCES consul_project_mappings(id) ON DELETE CASCADE,
    
    external_task_id TEXT NOT NULL,
    external_task_url TEXT,
    
    last_sync TIMESTAMPTZ,
    last_sync_hash TEXT,
    sync_conflict BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(connection_id, external_task_id)
);

-- Status mappings per connection
CREATE TABLE IF NOT EXISTS consul_status_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    
    consul_status TEXT NOT NULL,
    external_status TEXT NOT NULL,
    
    UNIQUE(connection_id, consul_status),
    UNIQUE(connection_id, external_status)
);

-- Priority mappings per connection
CREATE TABLE IF NOT EXISTS consul_priority_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    connection_id UUID REFERENCES consul_pm_connections(id) ON DELETE CASCADE,
    
    consul_priority TEXT NOT NULL,
    external_priority TEXT NOT NULL,
    
    UNIQUE(connection_id, consul_priority),
    UNIQUE(connection_id, external_priority)
);

-- Sync log
CREATE TABLE IF NOT EXISTS consul_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    connection_id UUID REFERENCES consul_pm_connections(id),
    project_mapping_id UUID REFERENCES consul_project_mappings(id),
    
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
CREATE TABLE IF NOT EXISTS consul_project_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    
    -- Template structure
    phases JSONB DEFAULT '[]',
    default_tasks JSONB DEFAULT '[]',
    estimated_duration_days INTEGER,
    
    -- Settings
    default_tool TEXT DEFAULT 'leantime',
    tags TEXT[] DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_consul_projects_status ON consul_projects(status);
CREATE INDEX IF NOT EXISTS idx_consul_projects_client ON consul_projects(client_name);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_project ON consul_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_status ON consul_tasks(status);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_agent ON consul_tasks(assigned_agent);
CREATE INDEX IF NOT EXISTS idx_consul_tasks_due ON consul_tasks(due_date);
CREATE INDEX IF NOT EXISTS idx_consul_blockers_status ON consul_blockers(status);
CREATE INDEX IF NOT EXISTS idx_consul_decisions_status ON consul_decisions(status);
CREATE INDEX IF NOT EXISTS idx_consul_standups_date ON consul_standups(standup_date DESC);
CREATE INDEX IF NOT EXISTS idx_consul_pm_connections_tool ON consul_pm_connections(tool_name);
CREATE INDEX IF NOT EXISTS idx_consul_pm_connections_status ON consul_pm_connections(status);
CREATE INDEX IF NOT EXISTS idx_consul_project_mappings_external ON consul_project_mappings(external_project_id);
CREATE INDEX IF NOT EXISTS idx_consul_task_mappings_external ON consul_task_mappings(external_task_id);
CREATE INDEX IF NOT EXISTS idx_consul_sync_log_connection ON consul_sync_log(connection_id);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Get project summary
CREATE OR REPLACE FUNCTION consul_project_summary(p_project_id UUID DEFAULT NULL)
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
    health_score DECIMAL,
    connected_tools TEXT[]
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
        (SELECT COUNT(*) FROM consul_blockers b WHERE b.project_id = p.id AND b.status = 'open'),
        (SELECT COUNT(*) FROM consul_decisions d WHERE d.project_id = p.id AND d.status = 'pending'),
        CASE 
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 3 THEN 40
            WHEN (p.target_end - CURRENT_DATE) < 7 AND COUNT(t.id) FILTER (WHERE t.status = 'done')::DECIMAL / NULLIF(COUNT(t.id), 0) < 0.8 THEN 50
            WHEN COUNT(t.id) FILTER (WHERE t.status = 'blocked') > 0 THEN 70
            ELSE 90
        END::DECIMAL,
        (SELECT ARRAY_AGG(DISTINCT c.tool_name) FROM consul_project_mappings pm 
         JOIN consul_pm_connections c ON pm.connection_id = c.id 
         WHERE pm.consul_project_id = p.id)
    FROM consul_projects p
    LEFT JOIN consul_tasks t ON t.project_id = p.id
    WHERE (p_project_id IS NULL OR p.id = p_project_id)
    AND p.status IN ('planning', 'active')
    GROUP BY p.id;
END;
$$ LANGUAGE plpgsql;

-- Get unified cross-tool status
CREATE OR REPLACE FUNCTION consul_unified_status()
RETURNS TABLE (
    total_projects INTEGER,
    total_tasks INTEGER,
    tasks_overdue INTEGER,
    blockers_open INTEGER,
    decisions_pending INTEGER,
    connections_active INTEGER,
    connections_error INTEGER,
    sync_pending INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        (SELECT COUNT(*)::INTEGER FROM consul_projects WHERE status = 'active'),
        (SELECT COUNT(*)::INTEGER FROM consul_tasks WHERE status NOT IN ('done', 'cancelled')),
        (SELECT COUNT(*)::INTEGER FROM consul_tasks WHERE due_date < CURRENT_DATE AND status NOT IN ('done', 'cancelled')),
        (SELECT COUNT(*)::INTEGER FROM consul_blockers WHERE status = 'open'),
        (SELECT COUNT(*)::INTEGER FROM consul_decisions WHERE status = 'pending'),
        (SELECT COUNT(*)::INTEGER FROM consul_pm_connections WHERE status = 'active'),
        (SELECT COUNT(*)::INTEGER FROM consul_pm_connections WHERE status = 'error'),
        (SELECT COUNT(*)::INTEGER FROM consul_project_mappings WHERE last_sync < NOW() - INTERVAL '1 hour');
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- SEED DATA
-- ============================================================

-- Project templates
INSERT INTO consul_project_templates (name, description, phases, default_tasks, estimated_duration_days, default_tool) VALUES
(
    'automation_project',
    'Standard client automation project',
    '[
        {"name": "Discovery", "duration_days": 3},
        {"name": "Design", "duration_days": 5},
        {"name": "Build", "duration_days": 10},
        {"name": "Test", "duration_days": 3},
        {"name": "Deploy", "duration_days": 2},
        {"name": "Handoff", "duration_days": 2}
    ]'::jsonb,
    '[
        {"title": "Discovery call", "phase": "Discovery", "estimated_hours": 1},
        {"title": "Requirements document", "phase": "Discovery", "estimated_hours": 2},
        {"title": "Solution design", "phase": "Design", "estimated_hours": 4},
        {"title": "Client approval", "phase": "Design", "estimated_hours": 1},
        {"title": "Build automation", "phase": "Build", "estimated_hours": 20},
        {"title": "Testing", "phase": "Test", "estimated_hours": 4},
        {"title": "Deploy to production", "phase": "Deploy", "estimated_hours": 2},
        {"title": "Documentation", "phase": "Handoff", "estimated_hours": 3},
        {"title": "Training session", "phase": "Handoff", "estimated_hours": 2}
    ]'::jsonb,
    25,
    'leantime'
),
(
    'agent_development',
    'Building a new LeverEdge agent',
    '[
        {"name": "Specification", "duration_days": 2},
        {"name": "Development", "duration_days": 5},
        {"name": "Testing", "duration_days": 2},
        {"name": "Integration", "duration_days": 2},
        {"name": "Documentation", "duration_days": 1}
    ]'::jsonb,
    '[
        {"title": "Write agent spec", "phase": "Specification", "estimated_hours": 4},
        {"title": "Create database schema", "phase": "Development", "estimated_hours": 2},
        {"title": "Build FastAPI service", "phase": "Development", "estimated_hours": 8},
        {"title": "Create Dockerfile", "phase": "Development", "estimated_hours": 1},
        {"title": "Unit tests", "phase": "Testing", "estimated_hours": 3},
        {"title": "Integration tests", "phase": "Testing", "estimated_hours": 2},
        {"title": "Add MCP tools", "phase": "Integration", "estimated_hours": 2},
        {"title": "Register with ATLAS", "phase": "Integration", "estimated_hours": 1},
        {"title": "Update docs", "phase": "Documentation", "estimated_hours": 2}
    ]'::jsonb,
    12,
    'leantime'
),
(
    'client_onboarding',
    'Onboarding a new client',
    '[
        {"name": "Setup", "duration_days": 1},
        {"name": "Discovery", "duration_days": 2},
        {"name": "Proposal", "duration_days": 2},
        {"name": "Contract", "duration_days": 3}
    ]'::jsonb,
    '[
        {"title": "Create client workspace", "phase": "Setup", "estimated_hours": 0.5},
        {"title": "Connect client PM tool", "phase": "Setup", "estimated_hours": 1},
        {"title": "Discovery call", "phase": "Discovery", "estimated_hours": 1},
        {"title": "Document requirements", "phase": "Discovery", "estimated_hours": 2},
        {"title": "Create proposal", "phase": "Proposal", "estimated_hours": 3},
        {"title": "Present proposal", "phase": "Proposal", "estimated_hours": 1},
        {"title": "Contract negotiation", "phase": "Contract", "estimated_hours": 2},
        {"title": "Contract signed", "phase": "Contract", "estimated_hours": 0.5}
    ]'::jsonb,
    8,
    'leantime'
)
ON CONFLICT (name) DO NOTHING;

-- Default status mappings for common tools
-- (These will be used as defaults when connecting new tools)

-- Internal Leantime connection
INSERT INTO consul_pm_connections (tool_name, connection_name, instance_url, aegis_credential_key, status, config)
VALUES (
    'leantime',
    'LeverEdge Internal',
    'http://leantime:80',
    'leantime_internal',
    'active',
    '{"is_primary": true}'::jsonb
) ON CONFLICT DO NOTHING;

-- Internal OpenProject connection  
INSERT INTO consul_pm_connections (tool_name, connection_name, instance_url, aegis_credential_key, status, config)
VALUES (
    'openproject',
    'LeverEdge Enterprise',
    'http://openproject:80',
    'openproject_internal',
    'active',
    '{"is_primary": false, "use_for": "enterprise_clients"}'::jsonb
) ON CONFLICT DO NOTHING;

-- LeverEdge Launch project
INSERT INTO consul_projects (
    name, description, status, priority, owner, pm_agent,
    target_start, target_end, source_tool, original_scope
) VALUES (
    'LeverEdge Agency Launch',
    'Build and launch LeverEdge AI automation agency by March 1, 2026',
    'active',
    100,
    'damon',
    'CONSUL',
    '2026-01-11',
    '2026-03-01',
    'leantime',
    '{
        "phases": ["Infrastructure", "Outreach Prep", "Active Outreach", "Launch"],
        "goals": ["$30K MRR", "3 clients", "Repeatable process"],
        "non_goals": ["Enterprise features", "Multiple verticals"],
        "success_criteria": ["First paying client by March 1"]
    }'::jsonb
) ON CONFLICT DO NOTHING;

-- Initialize agent workloads
INSERT INTO consul_agent_workload (agent, max_concurrent_tasks) VALUES
    ('CHRONOS', 5), ('HADES', 3), ('AEGIS', 3), ('HERMES', 10),
    ('SCHOLAR', 3), ('CHIRON', 3), ('ATHENA', 5), ('MUSE', 3),
    ('QUILL', 5), ('STAGE', 3), ('REEL', 3), ('CRITIC', 5),
    ('DAEDALUS', 3), ('VARYS', 3), ('CONSUL', 10), ('HEPHAESTUS', 5),
    ('PANOPTES', 3), ('ASCLEPIUS', 3), ('ARGUS', 3), ('ALOY', 3)
ON CONFLICT (agent) DO NOTHING;
```

### 2.2 Run Migration

```bash
psql $DEV_DATABASE_URL -f /opt/leveredge/database/migrations/20260119_consul_universal_schema.sql
```

---

## PHASE 3: CONSUL CORE SERVICE (4 hours)

### 3.1 Create Service Structure

```bash
mkdir -p /opt/leveredge/control-plane/agents/consul/adapters
```

### 3.2 Create Base Adapter Interface

Create `/opt/leveredge/control-plane/agents/consul/adapters/base.py`:

```python
"""
Base PM Adapter Interface
All PM tool adapters must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import date, datetime
from enum import Enum

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

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class UnifiedProject(BaseModel):
    id: Optional[str] = None
    external_id: Optional[str] = None
    source: str
    
    name: str
    description: Optional[str] = None
    status: ProjectStatus = ProjectStatus.PLANNING
    
    owner: Optional[str] = None
    team: List[str] = []
    
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    custom_fields: Dict[str, Any] = {}

class UnifiedTask(BaseModel):
    id: Optional[str] = None
    external_id: Optional[str] = None
    source: str
    project_id: str
    
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    
    assignee: Optional[str] = None
    assignee_external_id: Optional[str] = None
    
    due_date: Optional[date] = None
    estimated_hours: Optional[float] = None
    actual_hours: float = 0
    
    parent_task_id: Optional[str] = None
    depends_on: List[str] = []
    
    tags: List[str] = []
    custom_fields: Dict[str, Any] = {}

class UnifiedComment(BaseModel):
    id: Optional[str] = None
    task_id: str
    author: str
    content: str
    created_at: datetime

class UnifiedTimeEntry(BaseModel):
    id: Optional[str] = None
    task_id: str
    user: str
    hours: float
    description: Optional[str] = None
    date: date

class SyncResult(BaseModel):
    success: bool
    items_synced: int = 0
    items_created: int = 0
    items_updated: int = 0
    items_deleted: int = 0
    errors: List[str] = []

class PMAdapter(ABC):
    """Base class for all PM tool adapters"""
    
    name: str
    requires_oauth: bool = False
    api_base_url: str = ""
    
    def __init__(self):
        self.connected = False
        self.credentials = {}
    
    # ============ CONNECTION ============
    
    @abstractmethod
    async def connect(self, credentials: dict) -> bool:
        """Establish connection with credentials"""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify connection is working"""
        pass
    
    async def disconnect(self) -> bool:
        """Clean up connection"""
        self.connected = False
        return True
    
    # ============ PROJECTS ============
    
    @abstractmethod
    async def list_projects(self) -> List[UnifiedProject]:
        """Get all accessible projects"""
        pass
    
    @abstractmethod
    async def get_project(self, project_id: str) -> UnifiedProject:
        """Get single project by ID"""
        pass
    
    @abstractmethod
    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        """Create new project"""
        pass
    
    @abstractmethod
    async def update_project(self, project_id: str, updates: dict) -> UnifiedProject:
        """Update existing project"""
        pass
    
    # ============ TASKS ============
    
    @abstractmethod
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        """Get tasks in a project"""
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> UnifiedTask:
        """Get single task"""
        pass
    
    @abstractmethod
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        """Create new task"""
        pass
    
    @abstractmethod
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        """Update existing task"""
        pass
    
    @abstractmethod
    async def delete_task(self, task_id: str) -> bool:
        """Delete task"""
        pass
    
    async def move_task(self, task_id: str, new_status: str) -> UnifiedTask:
        """Change task status"""
        return await self.update_task(task_id, {"status": new_status})
    
    async def assign_task(self, task_id: str, assignee: str, assignee_external_id: str = None) -> UnifiedTask:
        """Assign task to user"""
        updates = {"assignee": assignee}
        if assignee_external_id:
            updates["assignee_external_id"] = assignee_external_id
        return await self.update_task(task_id, updates)
    
    # ============ COMMENTS ============
    
    async def list_comments(self, task_id: str) -> List[UnifiedComment]:
        """Get comments on a task (optional)"""
        return []
    
    async def add_comment(self, task_id: str, content: str) -> UnifiedComment:
        """Add comment to task (optional)"""
        raise NotImplementedError(f"{self.name} adapter does not support comments")
    
    # ============ TIME TRACKING ============
    
    async def log_time(self, task_id: str, hours: float, description: str = None) -> UnifiedTimeEntry:
        """Log time against a task (optional)"""
        raise NotImplementedError(f"{self.name} adapter does not support time tracking")
    
    async def get_time_entries(self, task_id: str) -> List[UnifiedTimeEntry]:
        """Get time entries for a task (optional)"""
        return []
    
    # ============ SYNC ============
    
    async def sync_from_source(self, project_id: str) -> SyncResult:
        """Pull changes from source system"""
        # Default implementation: full refresh
        tasks = await self.list_tasks(project_id)
        return SyncResult(success=True, items_synced=len(tasks))
    
    async def sync_to_source(self, tasks: List[UnifiedTask]) -> SyncResult:
        """Push changes to source system"""
        results = SyncResult(success=True)
        for task in tasks:
            try:
                if task.external_id:
                    await self.update_task(task.external_id, task.dict())
                    results.items_updated += 1
                else:
                    await self.create_task(task)
                    results.items_created += 1
                results.items_synced += 1
            except Exception as e:
                results.errors.append(str(e))
        results.success = len(results.errors) == 0
        return results
    
    # ============ WEBHOOKS ============
    
    async def register_webhook(self, project_id: str, callback_url: str, events: List[str]) -> str:
        """Register for real-time updates (optional)"""
        raise NotImplementedError(f"{self.name} adapter does not support webhooks")
    
    async def handle_webhook(self, payload: dict) -> Dict[str, Any]:
        """Process incoming webhook (optional)"""
        raise NotImplementedError(f"{self.name} adapter does not support webhooks")
    
    # ============ HELPERS ============
    
    def _map_status_to_consul(self, external_status: str) -> TaskStatus:
        """Override in subclass to map tool-specific statuses"""
        status_map = {
            "to do": TaskStatus.TODO,
            "todo": TaskStatus.TODO,
            "open": TaskStatus.TODO,
            "new": TaskStatus.TODO,
            "in progress": TaskStatus.IN_PROGRESS,
            "in_progress": TaskStatus.IN_PROGRESS,
            "doing": TaskStatus.IN_PROGRESS,
            "blocked": TaskStatus.BLOCKED,
            "review": TaskStatus.REVIEW,
            "in review": TaskStatus.REVIEW,
            "done": TaskStatus.DONE,
            "complete": TaskStatus.DONE,
            "completed": TaskStatus.DONE,
            "closed": TaskStatus.DONE,
            "cancelled": TaskStatus.CANCELLED,
            "canceled": TaskStatus.CANCELLED,
        }
        return status_map.get(external_status.lower(), TaskStatus.TODO)
    
    def _map_status_from_consul(self, consul_status: TaskStatus) -> str:
        """Override in subclass to map to tool-specific statuses"""
        return consul_status.value
    
    def _map_priority_to_consul(self, external_priority: str) -> Priority:
        """Override in subclass to map tool-specific priorities"""
        priority_map = {
            "critical": Priority.CRITICAL,
            "highest": Priority.CRITICAL,
            "urgent": Priority.CRITICAL,
            "high": Priority.HIGH,
            "medium": Priority.MEDIUM,
            "normal": Priority.MEDIUM,
            "low": Priority.LOW,
            "lowest": Priority.LOW,
        }
        return priority_map.get(external_priority.lower(), Priority.MEDIUM)
```

### 3.3 Create Leantime Adapter

Create `/opt/leveredge/control-plane/agents/consul/adapters/leantime.py`:

```python
"""Leantime PM Adapter"""

import httpx
from typing import List, Optional, Dict, Any
from .base import (
    PMAdapter, UnifiedProject, UnifiedTask, UnifiedComment,
    UnifiedTimeEntry, SyncResult, ProjectStatus, TaskStatus, Priority
)

class LeantimeAdapter(PMAdapter):
    name = "leantime"
    requires_oauth = False
    
    def __init__(self, base_url: str = "http://leantime:80"):
        super().__init__()
        self.api_base_url = f"{base_url}/api/jsonrpc"
        self.session: Optional[httpx.AsyncClient] = None
    
    async def connect(self, credentials: dict) -> bool:
        self.credentials = credentials
        self.session = httpx.AsyncClient(timeout=30.0)
        
        # Leantime uses session-based auth
        login_response = await self.session.post(
            f"{self.api_base_url}",
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.auth.login",
                "params": {
                    "username": credentials.get("username"),
                    "password": credentials.get("password")
                },
                "id": 1
            }
        )
        
        result = login_response.json()
        self.connected = result.get("result", {}).get("status") == "success"
        return self.connected
    
    async def test_connection(self) -> bool:
        if not self.session:
            return False
        try:
            response = await self.session.post(
                self.api_base_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "leantime.rpc.projects.getAll",
                    "id": 1
                }
            )
            return response.status_code == 200
        except:
            return False
    
    async def list_projects(self) -> List[UnifiedProject]:
        response = await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.projects.getAll",
                "id": 1
            }
        )
        
        projects = []
        for p in response.json().get("result", []):
            projects.append(UnifiedProject(
                external_id=str(p["id"]),
                source="leantime",
                name=p["name"],
                description=p.get("details", ""),
                status=self._map_project_status(p.get("state", "open")),
                start_date=p.get("start"),
                end_date=p.get("end"),
            ))
        return projects
    
    async def get_project(self, project_id: str) -> UnifiedProject:
        response = await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.projects.get",
                "params": {"id": project_id},
                "id": 1
            }
        )
        p = response.json().get("result", {})
        return UnifiedProject(
            external_id=str(p["id"]),
            source="leantime",
            name=p["name"],
            description=p.get("details", ""),
            status=self._map_project_status(p.get("state", "open")),
        )
    
    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        response = await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.projects.create",
                "params": {
                    "name": project.name,
                    "details": project.description or "",
                    "start": str(project.start_date) if project.start_date else None,
                    "end": str(project.end_date) if project.end_date else None,
                },
                "id": 1
            }
        )
        result = response.json().get("result", {})
        project.external_id = str(result.get("id"))
        return project
    
    async def update_project(self, project_id: str, updates: dict) -> UnifiedProject:
        await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.projects.update",
                "params": {"id": project_id, **updates},
                "id": 1
            }
        )
        return await self.get_project(project_id)
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        response = await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.tickets.getAll",
                "params": {"projectId": project_id},
                "id": 1
            }
        )
        
        tasks = []
        for t in response.json().get("result", []):
            tasks.append(UnifiedTask(
                external_id=str(t["id"]),
                source="leantime",
                project_id=f"leantime:{project_id}",
                title=t["headline"],
                description=t.get("description", ""),
                status=self._map_status_to_consul(t.get("status", "new")),
                priority=self._map_priority_to_consul(t.get("priority", "medium")),
                assignee=t.get("editorFirstname", "") + " " + t.get("editorLastname", ""),
                due_date=t.get("dateToFinish"),
                estimated_hours=t.get("planHours"),
                actual_hours=t.get("hourRemaining", 0),
                tags=t.get("tags", "").split(",") if t.get("tags") else [],
            ))
        
        # Apply filters
        if filters:
            if filters.get("status"):
                tasks = [t for t in tasks if t.status.value == filters["status"]]
            if filters.get("assignee"):
                tasks = [t for t in tasks if filters["assignee"].lower() in t.assignee.lower()]
        
        return tasks
    
    async def get_task(self, task_id: str) -> UnifiedTask:
        response = await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.tickets.get",
                "params": {"id": task_id},
                "id": 1
            }
        )
        t = response.json().get("result", {})
        return UnifiedTask(
            external_id=str(t["id"]),
            source="leantime",
            project_id=f"leantime:{t['projectId']}",
            title=t["headline"],
            description=t.get("description", ""),
            status=self._map_status_to_consul(t.get("status", "new")),
            priority=self._map_priority_to_consul(t.get("priority", "medium")),
            due_date=t.get("dateToFinish"),
        )
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        project_id = task.project_id.replace("leantime:", "")
        response = await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.tickets.create",
                "params": {
                    "projectId": project_id,
                    "headline": task.title,
                    "description": task.description or "",
                    "status": self._map_status_from_consul(task.status),
                    "priority": task.priority.value,
                    "dateToFinish": str(task.due_date) if task.due_date else None,
                    "planHours": task.estimated_hours,
                },
                "id": 1
            }
        )
        result = response.json().get("result", {})
        task.external_id = str(result.get("id"))
        return task
    
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        # Map status if present
        if "status" in updates and isinstance(updates["status"], TaskStatus):
            updates["status"] = self._map_status_from_consul(updates["status"])
        
        await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.tickets.update",
                "params": {"id": task_id, **updates},
                "id": 1
            }
        )
        return await self.get_task(task_id)
    
    async def delete_task(self, task_id: str) -> bool:
        response = await self.session.post(
            self.api_base_url,
            json={
                "jsonrpc": "2.0",
                "method": "leantime.rpc.tickets.delete",
                "params": {"id": task_id},
                "id": 1
            }
        )
        return response.json().get("result", {}).get("status") == "success"
    
    def _map_project_status(self, status: str) -> ProjectStatus:
        mapping = {
            "open": ProjectStatus.ACTIVE,
            "closed": ProjectStatus.COMPLETED,
            "archived": ProjectStatus.COMPLETED,
        }
        return mapping.get(status.lower(), ProjectStatus.ACTIVE)
    
    def _map_status_from_consul(self, status: TaskStatus) -> str:
        mapping = {
            TaskStatus.TODO: "new",
            TaskStatus.IN_PROGRESS: "in_progress",
            TaskStatus.BLOCKED: "blocked",
            TaskStatus.REVIEW: "in_review",
            TaskStatus.DONE: "done",
            TaskStatus.CANCELLED: "cancelled",
        }
        return mapping.get(status, "new")
```

### 3.4 Create Main CONSUL Service

Create `/opt/leveredge/control-plane/agents/consul/consul.py`:

```python
"""
CONSUL - Universal Project Master
Port: 8017
Domain: CHANCERY

I speak every PM language. Nothing escapes my attention.
Nothing falls through the cracks.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import os
import asyncpg
import httpx
import json
import importlib

# Import adapters
from adapters.base import (
    PMAdapter, UnifiedProject, UnifiedTask, UnifiedComment,
    TaskStatus, ProjectStatus, Priority, SyncResult
)
from adapters.leantime import LeantimeAdapter

app = FastAPI(
    title="CONSUL - Universal Project Master",
    description="I speak every PM language. Nothing escapes my attention. Nothing falls through the cracks.",
    version="2.0.0"
)

DATABASE_URL = os.environ.get("DATABASE_URL")

# Registry of available adapters
ADAPTERS: Dict[str, type] = {
    "leantime": LeantimeAdapter,
    # Add more as implemented
    # "openproject": OpenProjectAdapter,
    # "asana": AsanaAdapter,
    # "jira": JiraAdapter,
    # "monday": MondayAdapter,
    # "notion": NotionAdapter,
    # "linear": LinearAdapter,
}

# Active adapter instances
active_adapters: Dict[str, PMAdapter] = {}

# ============ MODELS ============

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    priority: int = Field(default=50, ge=1, le=100)
    target_start: Optional[date] = None
    target_end: Optional[date] = None
    client_name: Optional[str] = None
    source_tool: str = "leantime"
    tags: List[str] = []
    template: Optional[str] = None

class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    priority: str = "medium"
    assigned_agent: Optional[str] = None
    estimated_hours: Optional[float] = None
    due_date: Optional[date] = None
    depends_on: List[str] = []
    tags: List[str] = []
    sync_to_external: bool = True

class ConnectionCreate(BaseModel):
    tool_name: str
    connection_name: str
    instance_url: Optional[str] = None
    workspace_id: Optional[str] = None
    credentials: Dict[str, Any]

class BlockerCreate(BaseModel):
    task_id: Optional[str] = None
    project_id: str
    description: str
    blocker_type: str = "other"
    severity: str = "medium"

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
    
    # Initialize internal adapters
    await initialize_internal_connections()

@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()
    for adapter in active_adapters.values():
        await adapter.disconnect()

async def initialize_internal_connections():
    """Initialize connections to internal PM tools"""
    async with pool.acquire() as conn:
        connections = await conn.fetch("""
            SELECT * FROM consul_pm_connections 
            WHERE status = 'active' 
            AND tool_name IN ('leantime', 'openproject')
        """)
        
        for conn_row in connections:
            tool = conn_row['tool_name']
            if tool in ADAPTERS:
                try:
                    # Get credentials from AEGIS
                    creds = await get_credentials_from_aegis(conn_row['aegis_credential_key'])
                    
                    adapter = ADAPTERS[tool](conn_row['instance_url'])
                    if await adapter.connect(creds):
                        active_adapters[str(conn_row['id'])] = adapter
                        print(f"✅ Connected to {tool}: {conn_row['connection_name']}")
                except Exception as e:
                    print(f"❌ Failed to connect to {tool}: {e}")

async def get_credentials_from_aegis(key: str) -> dict:
    """Get credentials from AEGIS credential manager"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8012/credentials/{key}",
                timeout=5.0
            )
            if response.status_code == 200:
                return response.json()
    except:
        pass
    
    # Fallback to environment variables
    return {
        "username": os.environ.get(f"{key.upper()}_USERNAME"),
        "password": os.environ.get(f"{key.upper()}_PASSWORD"),
        "api_key": os.environ.get(f"{key.upper()}_API_KEY"),
    }

# ============ HELPER FUNCTIONS ============

async def notify_aria(message: str, priority: str = "normal"):
    """Send notification to ARIA"""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8111/notify",
                json={"message": message, "source": "CONSUL", "priority": priority},
                timeout=5.0
            )
    except:
        pass

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

# ============ HEALTH & STATUS ============

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "CONSUL - Universal Project Master",
        "version": "2.0.0",
        "port": 8017,
        "tagline": "I speak every PM language. Nothing escapes my attention.",
        "active_connections": len(active_adapters),
        "supported_tools": list(ADAPTERS.keys())
    }

@app.get("/status")
async def consul_status():
    """CONSUL's current assessment"""
    async with pool.acquire() as conn:
        stats = await conn.fetchrow("SELECT * FROM consul_unified_status()")
        projects = await conn.fetch("SELECT * FROM consul_project_summary(NULL)")
        
        # Assessment logic
        if stats['tasks_overdue'] > 5:
            assessment = "🚨 Critical: Multiple overdue tasks require immediate attention."
        elif stats['blockers_open'] > 3:
            assessment = "⚠️ Warning: Several blockers are impeding progress."
        elif stats['connections_error'] > 0:
            assessment = "⚠️ Warning: Some PM tool connections have errors."
        elif any(p['health_score'] and p['health_score'] < 50 for p in projects):
            assessment = "⚠️ Warning: Project health declining. Review needed."
        else:
            assessment = "✅ All systems nominal. Progress is on track."
        
        return {
            "consul_says": assessment,
            "stats": dict(stats),
            "projects": [dict(p) for p in projects],
            "timestamp": datetime.now().isoformat()
        }

# ============ CONNECTION MANAGEMENT ============

@app.get("/connections")
async def list_connections():
    """List all PM tool connections"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, tool_name, connection_name, instance_url, workspace_id,
                   status, last_sync, last_error, sync_enabled
            FROM consul_pm_connections
            ORDER BY tool_name, connection_name
        """)
        return [dict(row) for row in rows]

@app.post("/connections")
async def create_connection(connection: ConnectionCreate):
    """Create a new PM tool connection"""
    if connection.tool_name not in ADAPTERS:
        raise HTTPException(400, f"Unsupported tool: {connection.tool_name}. Supported: {list(ADAPTERS.keys())}")
    
    # Store credentials in AEGIS
    aegis_key = f"consul_{connection.tool_name}_{connection.connection_name.lower().replace(' ', '_')}"
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8012/credentials",
                json={"key": aegis_key, "value": connection.credentials},
                timeout=5.0
            )
    except Exception as e:
        raise HTTPException(500, f"Failed to store credentials: {e}")
    
    # Create connection record
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO consul_pm_connections 
            (tool_name, connection_name, instance_url, workspace_id, aegis_credential_key)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        """, connection.tool_name, connection.connection_name, 
            connection.instance_url, connection.workspace_id, aegis_key)
        
        # Try to connect
        try:
            adapter = ADAPTERS[connection.tool_name](connection.instance_url)
            if await adapter.connect(connection.credentials):
                active_adapters[str(row['id'])] = adapter
                await conn.execute(
                    "UPDATE consul_pm_connections SET status = 'active' WHERE id = $1",
                    row['id']
                )
                await notify_aria(f"✅ Connected to {connection.tool_name}: {connection.connection_name}")
            else:
                await conn.execute(
                    "UPDATE consul_pm_connections SET status = 'error', last_error = 'Connection failed' WHERE id = $1",
                    row['id']
                )
        except Exception as e:
            await conn.execute(
                "UPDATE consul_pm_connections SET status = 'error', last_error = $2 WHERE id = $1",
                row['id'], str(e)
            )
        
        return dict(row)

@app.post("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test a PM tool connection"""
    if connection_id in active_adapters:
        adapter = active_adapters[connection_id]
        success = await adapter.test_connection()
        return {"success": success, "tool": adapter.name}
    else:
        raise HTTPException(404, "Connection not found or not active")

@app.get("/connections/supported")
async def supported_tools():
    """List supported PM tools"""
    tools = []
    for name, adapter_class in ADAPTERS.items():
        tools.append({
            "name": name,
            "requires_oauth": adapter_class.requires_oauth,
            "status": "implemented"
        })
    
    # Also list planned
    planned = ["openproject", "asana", "jira", "monday", "notion", "linear", "clickup", "trello"]
    for name in planned:
        if name not in ADAPTERS:
            tools.append({"name": name, "status": "planned"})
    
    return tools

# ============ PROJECT ENDPOINTS ============

@app.post("/projects")
async def create_project(project: ProjectCreate, background_tasks: BackgroundTasks):
    """Create a new project"""
    # Apply template if specified
    template_tasks = []
    if project.template:
        async with pool.acquire() as conn:
            template = await conn.fetchrow(
                "SELECT * FROM consul_project_templates WHERE name = $1",
                project.template
            )
            if template:
                template_tasks = template['default_tasks']
                if not project.target_end and template['estimated_duration_days']:
                    project.target_end = date.today() + timedelta(days=template['estimated_duration_days'])
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO consul_projects 
            (name, description, priority, target_start, target_end, client_name, source_tool, tags, template_used)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, project.name, project.description, project.priority,
            project.target_start, project.target_end, project.client_name,
            project.source_tool, project.tags, project.template)
        
        project_id = str(row['id'])
        
        # Create template tasks
        for task_def in template_tasks:
            await conn.execute("""
                INSERT INTO consul_tasks (project_id, title, estimated_hours, tags)
                VALUES ($1, $2, $3, $4)
            """, row['id'], task_def['title'], task_def.get('estimated_hours'),
                [task_def.get('phase', '')])
        
        await notify_aria(f"📋 New project created: {project.name}")
        
        return dict(row)

@app.get("/projects")
async def list_projects(
    status: Optional[str] = None,
    client: Optional[str] = None,
    include_summary: bool = True
):
    """List all projects"""
    async with pool.acquire() as conn:
        if include_summary:
            rows = await conn.fetch("SELECT * FROM consul_project_summary(NULL)")
        else:
            query = "SELECT * FROM consul_projects WHERE 1=1"
            params = []
            if status:
                params.append(status)
                query += f" AND status = ${len(params)}"
            if client:
                params.append(client)
                query += f" AND client_name = ${len(params)}"
            query += " ORDER BY priority DESC"
            rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]

@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project with full details"""
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
            "SELECT * FROM consul_tasks WHERE project_id = $1 ORDER BY priority DESC, due_date",
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
        
        mappings = await conn.fetch("""
            SELECT pm.*, c.tool_name, c.connection_name
            FROM consul_project_mappings pm
            JOIN consul_pm_connections c ON pm.connection_id = c.id
            WHERE pm.consul_project_id = $1
        """, project_id)
        
        return {
            "project": dict(project),
            "summary": dict(summary) if summary else None,
            "tasks": [dict(t) for t in tasks],
            "open_blockers": [dict(b) for b in blockers],
            "pending_decisions": [dict(d) for d in decisions],
            "external_mappings": [dict(m) for m in mappings]
        }

# ============ TASK ENDPOINTS ============

@app.post("/tasks")
async def create_task(task: TaskCreate, background_tasks: BackgroundTasks):
    """Create a task"""
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO consul_tasks 
            (project_id, title, description, priority, assigned_agent, 
             estimated_hours, due_date, depends_on, tags)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, task.project_id, task.title, task.description, task.priority,
            task.assigned_agent, task.estimated_hours, task.due_date,
            task.depends_on, task.tags)
        
        if task.assigned_agent:
            background_tasks.add_task(update_agent_workload, task.assigned_agent, 1)
        
        # Sync to external tool if enabled
        if task.sync_to_external:
            background_tasks.add_task(sync_task_to_external, str(row['id']))
        
        return dict(row)

@app.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    overdue: bool = False
):
    """List tasks with filters"""
    async with pool.acquire() as conn:
        if overdue:
            rows = await conn.fetch("""
                SELECT t.*, p.name as project_name
                FROM consul_tasks t
                JOIN consul_projects p ON t.project_id = p.id
                WHERE t.due_date < CURRENT_DATE
                AND t.status NOT IN ('done', 'cancelled')
                ORDER BY t.due_date
            """)
        else:
            query = """
                SELECT t.*, p.name as project_name
                FROM consul_tasks t
                JOIN consul_projects p ON t.project_id = p.id
                WHERE 1=1
            """
            params = []
            
            if project_id:
                params.append(project_id)
                query += f" AND t.project_id = ${len(params)}"
            if status:
                params.append(status)
                query += f" AND t.status = ${len(params)}"
            if assigned_agent:
                params.append(assigned_agent)
                query += f" AND t.assigned_agent = ${len(params)}"
            
            query += " ORDER BY t.priority DESC, t.due_date"
            rows = await conn.fetch(query, *params)
        
        return [dict(row) for row in rows]

@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, notes: Optional[str] = None):
    """Mark task complete"""
    async with pool.acquire() as conn:
        task = await conn.fetchrow(
            "SELECT * FROM consul_tasks WHERE id = $1", task_id
        )
        if not task:
            raise HTTPException(404, "Task not found")
        
        await conn.execute("""
            UPDATE consul_tasks 
            SET status = 'done', completed_at = NOW(), notes = COALESCE($2, notes)
            WHERE id = $1
        """, task_id, notes)
        
        if task['assigned_agent']:
            await update_agent_workload(task['assigned_agent'], -1)
        
        await notify_aria(f"✅ Task completed: {task['title']}")
        
        # Check for unblocked tasks
        unblocked = await conn.fetch("""
            SELECT id, title FROM consul_tasks 
            WHERE $1 = ANY(depends_on) AND status = 'blocked'
        """, task_id)
        
        for t in unblocked:
            await conn.execute(
                "UPDATE consul_tasks SET status = 'todo' WHERE id = $1", t['id']
            )
        
        return {"status": "completed", "unblocked": len(unblocked)}

@app.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, agent: str):
    """Assign task to agent"""
    async with pool.acquire() as conn:
        current = await conn.fetchrow(
            "SELECT assigned_agent FROM consul_tasks WHERE id = $1", task_id
        )
        
        await conn.execute("""
            UPDATE consul_tasks 
            SET assigned_agent = $2, assigned_at = NOW()
            WHERE id = $1
        """, task_id, agent)
        
        if current and current['assigned_agent']:
            await update_agent_workload(current['assigned_agent'], -1)
        await update_agent_workload(agent, 1)
        
        return {"status": "assigned", "agent": agent}

# ============ STANDUP ============

@app.post("/standup/generate")
async def generate_standup():
    """Generate comprehensive daily standup"""
    async with pool.acquire() as conn:
        projects = await conn.fetch("SELECT * FROM consul_project_summary(NULL)")
        overdue = await conn.fetch("""
            SELECT t.*, p.name as project_name
            FROM consul_tasks t
            JOIN consul_projects p ON t.project_id = p.id
            WHERE t.due_date < CURRENT_DATE
            AND t.status NOT IN ('done', 'cancelled')
        """)
        blockers = await conn.fetch(
            "SELECT * FROM consul_blockers WHERE status = 'open' ORDER BY severity DESC"
        )
        decisions = await conn.fetch(
            "SELECT * FROM consul_decisions WHERE status = 'pending'"
        )
        agents = await conn.fetch("SELECT * FROM consul_agent_workload ORDER BY active_tasks DESC")
        
        report = {
            "date": str(date.today()),
            "generated_at": datetime.now().isoformat(),
            "projects": [dict(p) for p in projects],
            "overdue_tasks": [dict(t) for t in overdue],
            "open_blockers": [dict(b) for b in blockers],
            "pending_decisions": [dict(d) for d in decisions],
            "agent_workloads": [dict(a) for a in agents],
            "summary": {
                "total_projects": len(projects),
                "overdue_count": len(overdue),
                "blockers_count": len(blockers),
                "critical_blockers": sum(1 for b in blockers if b['severity'] in ['critical', 'high']),
                "decisions_pending": len(decisions)
            }
        }
        
        # Compose message for ARIA
        msg = f"""📊 **CONSUL Daily Standup - {date.today()}**

**Projects:** {len(projects)} active
**Overdue:** {len(overdue)} tasks
**Blockers:** {len(blockers)} ({sum(1 for b in blockers if b['severity'] in ['critical', 'high'])} critical/high)
**Decisions:** {len(decisions)} pending

{"🚨 ATTENTION NEEDED" if len(overdue) > 0 or len(blockers) > 0 else "✅ On track"}"""
        
        await notify_aria(msg)
        
        return report

# ============ SYNC HELPERS ============

async def sync_task_to_external(task_id: str):
    """Sync a task to connected external tools"""
    async with pool.acquire() as conn:
        task = await conn.fetchrow("SELECT * FROM consul_tasks WHERE id = $1", task_id)
        if not task:
            return
        
        # Get project mappings
        mappings = await conn.fetch("""
            SELECT pm.*, c.id as connection_id
            FROM consul_project_mappings pm
            JOIN consul_pm_connections c ON pm.connection_id = c.id
            WHERE pm.consul_project_id = $1
            AND pm.sync_direction IN ('to_source', 'bidirectional')
            AND c.status = 'active'
        """, task['project_id'])
        
        for mapping in mappings:
            conn_id = str(mapping['connection_id'])
            if conn_id in active_adapters:
                adapter = active_adapters[conn_id]
                try:
                    unified_task = UnifiedTask(
                        source=adapter.name,
                        project_id=mapping['external_project_id'],
                        title=task['title'],
                        description=task['description'],
                        status=TaskStatus(task['status']),
                        priority=Priority(task['priority']),
                        due_date=task['due_date'],
                        estimated_hours=task['estimated_hours'],
                        tags=task['tags'] or []
                    )
                    result = await adapter.create_task(unified_task)
                    
                    # Save mapping
                    await conn.execute("""
                        INSERT INTO consul_task_mappings 
                        (consul_task_id, connection_id, project_mapping_id, external_task_id)
                        VALUES ($1, $2, $3, $4)
                    """, task_id, mapping['connection_id'], mapping['id'], result.external_id)
                    
                except Exception as e:
                    print(f"Failed to sync task to {adapter.name}: {e}")

# ============ TEMPLATES ============

@app.get("/templates")
async def list_templates():
    """List available project templates"""
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM consul_project_templates ORDER BY name")
        return [dict(row) for row in rows]

@app.post("/projects/from-template")
async def create_from_template(
    template_name: str,
    project_name: str,
    client_name: Optional[str] = None,
    target_end: Optional[date] = None
):
    """Create a project from template"""
    project = ProjectCreate(
        name=project_name,
        client_name=client_name,
        target_end=target_end,
        template=template_name
    )
    return await create_project(project, BackgroundTasks())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
```

### 3.5 Create Dockerfile

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

COPY adapters/ ./adapters/
COPY consul.py .

EXPOSE 8017

CMD ["uvicorn", "consul:app", "--host", "0.0.0.0", "--port", "8017"]
```

### 3.6 Build and Run

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

## PHASE 4: ADDITIONAL ADAPTERS (Stubs for future)

Create stub files for planned adapters:

```bash
# Create adapter stubs
for adapter in openproject asana jira monday notion linear clickup trello; do
  cat > /opt/leveredge/control-plane/agents/consul/adapters/${adapter}.py << 'EOF'
"""${adapter^} PM Adapter - STUB"""

from .base import PMAdapter, UnifiedProject, UnifiedTask
from typing import List

class ${adapter^}Adapter(PMAdapter):
    name = "${adapter}"
    requires_oauth = True  # Most cloud tools use OAuth
    
    async def connect(self, credentials: dict) -> bool:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def test_connection(self) -> bool:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def list_projects(self) -> List[UnifiedProject]:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def get_project(self, project_id: str) -> UnifiedProject:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def create_project(self, project: UnifiedProject) -> UnifiedProject:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def update_project(self, project_id: str, updates: dict) -> UnifiedProject:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def list_tasks(self, project_id: str, filters: dict = None) -> List[UnifiedTask]:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def get_task(self, task_id: str) -> UnifiedTask:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def create_task(self, task: UnifiedTask) -> UnifiedTask:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def update_task(self, task_id: str, updates: dict) -> UnifiedTask:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
    
    async def delete_task(self, task_id: str) -> bool:
        raise NotImplementedError("${adapter^} adapter not yet implemented")
EOF
done
```

---

## PHASE 5: MCP TOOLS (2 hours)

Add to HEPHAESTUS MCP:

```python
# ============ CONSUL UNIVERSAL PM TOOLS ============

@mcp_tool(name="consul_status")
async def consul_status() -> dict:
    """Get CONSUL's current assessment of all projects"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8017/status")
        return response.json()

@mcp_tool(name="consul_create_project")
async def consul_create_project(
    name: str,
    description: str = None,
    target_end: str = None,
    client_name: str = None,
    template: str = None
) -> dict:
    """Create a project (optionally from template)"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8017/projects",
            json={
                "name": name,
                "description": description,
                "target_end": target_end,
                "client_name": client_name,
                "template": template
            }
        )
        return response.json()

@mcp_tool(name="consul_create_task")
async def consul_create_task(
    project_id: str,
    title: str,
    assigned_agent: str = None,
    due_date: str = None,
    priority: str = "medium",
    estimated_hours: float = None
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
                "priority": priority,
                "estimated_hours": estimated_hours
            }
        )
        return response.json()

@mcp_tool(name="consul_standup")
async def consul_standup() -> dict:
    """Generate daily standup report"""
    async with httpx.AsyncClient() as client:
        response = await client.post("http://localhost:8017/standup/generate")
        return response.json()

@mcp_tool(name="consul_connect_tool")
async def consul_connect_tool(
    tool_name: str,
    connection_name: str,
    credentials: dict,
    instance_url: str = None
) -> dict:
    """Connect CONSUL to an external PM tool (Asana, Jira, etc.)"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8017/connections",
            json={
                "tool_name": tool_name,
                "connection_name": connection_name,
                "credentials": credentials,
                "instance_url": instance_url
            }
        )
        return response.json()

@mcp_tool(name="consul_list_connections")
async def consul_list_connections() -> dict:
    """List all PM tool connections"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8017/connections")
        return response.json()

@mcp_tool(name="consul_complete_task")
async def consul_complete_task(task_id: str, notes: str = None) -> dict:
    """Mark a task complete"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"http://localhost:8017/tasks/{task_id}/complete",
            params={"notes": notes}
        )
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

@mcp_tool(name="consul_list_templates")
async def consul_list_templates() -> dict:
    """List available project templates"""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8017/templates")
        return response.json()

@mcp_tool(name="consul_overdue")
async def consul_overdue() -> dict:
    """Get all overdue tasks"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8017/tasks",
            params={"overdue": True}
        )
        return response.json()
```

---

## VERIFICATION

```bash
# 1. PM Tools running
curl http://localhost:8040  # Leantime
curl http://localhost:8041  # OpenProject

# 2. CONSUL healthy
curl http://localhost:8017/health | jq .

# 3. Connections
curl http://localhost:8017/connections | jq .

# 4. Supported tools
curl http://localhost:8017/connections/supported | jq .

# 5. Projects
curl http://localhost:8017/projects | jq .

# 6. Templates
curl http://localhost:8017/templates | jq .

# 7. Status
curl http://localhost:8017/status | jq .

# 8. Generate standup
curl -X POST http://localhost:8017/standup/generate | jq .
```

---

## GIT COMMIT

```bash
git add .
git commit -m "CONSUL: Universal Project Master v2.0

- Universal PM adapter architecture
- Leantime + OpenProject deployment
- Adapter interface for any PM tool
- Leantime adapter implemented
- Stubs for: Asana, Jira, Monday, Notion, Linear, ClickUp, Trello
- Project templates: automation_project, agent_development, client_onboarding
- Cross-tool sync infrastructure
- 10 MCP tools for HEPHAESTUS
- LeverEdge Launch project seeded"
```

---

**CONSUL speaks every PM language.** 🎯

*"I speak Asana. I speak Jira. I speak Monday. I speak Notion. I speak Linear. Whatever your clients use, I adapt. Nothing escapes my attention. Nothing falls through the cracks."*
