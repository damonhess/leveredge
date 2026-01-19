# GSD: MAGNUS - Unified Command Center

**Priority:** CRITICAL
**Estimated Time:** 8-12 hours (can be done in phases)
**Purpose:** Make MAGNUS the badass PM orchestrator that rules ALL your tools

---

## THE VISION

MAGNUS becomes the **single pane of glass** for all project management:
- Connect OpenProject, Leantime, Asana, Jira, whatever
- Bidirectional sync - changes flow BOTH ways
- Single unified view across ALL tools
- Sprints, time tracking, velocity across everything
- AI-powered planning and breakdown

**This is a $15K+ capability.** Clients pay big money for cross-tool PM orchestration.

---

## ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    MAGNUS COMMAND CENTER                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   UNIFIED   │  │    SYNC     │  │     AI      │             │
│  │    VIEW     │  │   ENGINE    │  │   BRAIN     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │               │                │                      │
│  ┌──────┴───────────────┴────────────────┴──────┐              │
│  │              ADAPTER LAYER                    │              │
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐    │              │
│  │  │OP   │ │LT   │ │Asana│ │Jira │ │More │    │              │
│  └──┴─────┴─┴─────┴─┴─────┴─┴─────┴─┴─────┴────┘              │
│         │       │       │       │       │                       │
└─────────┼───────┼───────┼───────┼───────┼───────────────────────┘
          ▼       ▼       ▼       ▼       ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
    │OpenProj │ │Leantime │ │ Asana   │ │  Jira   │
    └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

---

## PHASE 1: SYNC ENGINE CORE (2-3 hours)

### 1.1 Database Schema

```sql
-- ============================================
-- PM CONNECTIONS (enhanced)
-- ============================================
DROP TABLE IF EXISTS magnus_pm_connections CASCADE;
CREATE TABLE magnus_pm_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_name VARCHAR(50) NOT NULL,  -- openproject, leantime, asana, jira, etc.
    display_name VARCHAR(255) NOT NULL,  -- "Client X OpenProject", "Personal Leantime"
    instance_url VARCHAR(500) NOT NULL,
    credentials_key VARCHAR(255),  -- Reference to AEGIS secret
    sync_direction VARCHAR(20) DEFAULT 'bidirectional',  -- bidirectional, push, pull
    sync_frequency VARCHAR(20) DEFAULT 'realtime',  -- realtime, hourly, daily, manual
    sync_enabled BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    last_sync_status VARCHAR(50),
    last_sync_error TEXT,
    config JSONB DEFAULT '{}',  -- Tool-specific config
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tool_name, instance_url)
);

-- ============================================
-- PROJECT MAPPINGS
-- ============================================
CREATE TABLE magnus_project_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    magnus_project_id UUID REFERENCES magnus_projects(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,
    external_project_id VARCHAR(255) NOT NULL,
    external_project_name VARCHAR(500),
    sync_enabled BOOLEAN DEFAULT TRUE,
    sync_direction VARCHAR(20) DEFAULT 'bidirectional',
    last_sync_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(connection_id, external_project_id)
);

CREATE INDEX idx_project_mappings_magnus ON magnus_project_mappings(magnus_project_id);
CREATE INDEX idx_project_mappings_connection ON magnus_project_mappings(connection_id);

-- ============================================
-- TASK MAPPINGS
-- ============================================
CREATE TABLE magnus_task_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    magnus_task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,
    external_task_id VARCHAR(255) NOT NULL,
    external_url VARCHAR(500),
    last_sync_at TIMESTAMPTZ,
    last_synced_hash VARCHAR(64),  -- For change detection
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(connection_id, external_task_id)
);

CREATE INDEX idx_task_mappings_magnus ON magnus_task_mappings(magnus_task_id);
CREATE INDEX idx_task_mappings_connection ON magnus_task_mappings(connection_id);

-- ============================================
-- SYNC LOG
-- ============================================
CREATE TABLE magnus_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL,  -- full, incremental, single_task, single_project
    direction VARCHAR(20) NOT NULL,  -- push, pull
    status VARCHAR(50) NOT NULL,  -- started, completed, failed, partial
    items_synced INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    conflicts_detected INTEGER DEFAULT 0,
    conflicts_resolved INTEGER DEFAULT 0,
    error_message TEXT,
    details JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_sync_log_connection ON magnus_sync_log(connection_id);
CREATE INDEX idx_sync_log_started ON magnus_sync_log(started_at DESC);

-- ============================================
-- SYNC CONFLICTS
-- ============================================
CREATE TABLE magnus_sync_conflicts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    connection_id UUID REFERENCES magnus_pm_connections(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,  -- project, task
    magnus_entity_id UUID,
    external_entity_id VARCHAR(255),
    magnus_data JSONB NOT NULL,
    external_data JSONB NOT NULL,
    conflict_fields JSONB NOT NULL,  -- Which fields conflict
    status VARCHAR(50) DEFAULT 'pending',  -- pending, resolved_magnus, resolved_external, merged
    resolution JSONB,
    resolved_at TIMESTAMPTZ,
    resolved_by VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sync_conflicts_status ON magnus_sync_conflicts(status);

-- ============================================
-- SPRINTS (from HERACLES)
-- ============================================
CREATE TABLE magnus_sprints (
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

CREATE INDEX idx_sprints_project ON magnus_sprints(project_id);
CREATE INDEX idx_sprints_status ON magnus_sprints(status);
CREATE INDEX idx_sprints_dates ON magnus_sprints(start_date, end_date);

-- ============================================
-- ENHANCE TASKS TABLE
-- ============================================
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS sprint_id UUID REFERENCES magnus_sprints(id);
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS story_points DECIMAL(10,2);
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS actual_hours DECIMAL(10,2) DEFAULT 0;
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS source_tool VARCHAR(50);  -- Where task originated
ALTER TABLE magnus_tasks ADD COLUMN IF NOT EXISTS external_url VARCHAR(500);  -- Link to external tool

CREATE INDEX idx_tasks_sprint ON magnus_tasks(sprint_id);
CREATE INDEX idx_tasks_source ON magnus_tasks(source_tool);

-- ============================================
-- TIME ENTRIES (from HERACLES)
-- ============================================
CREATE TABLE magnus_time_entries (
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
    synced_to JSONB DEFAULT '[]',  -- Which external tools this was synced to
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_time_task ON magnus_time_entries(task_id);
CREATE INDEX idx_time_user ON magnus_time_entries(user_id);
CREATE INDEX idx_time_date ON magnus_time_entries(date);

-- ============================================
-- ACTIVE TIMERS
-- ============================================
CREATE TABLE magnus_active_timers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES magnus_tasks(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL DEFAULT 'damon',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, task_id)
);

-- ============================================
-- VELOCITY HISTORY
-- ============================================
CREATE TABLE magnus_velocity_history (
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

CREATE INDEX idx_velocity_project ON magnus_velocity_history(project_id);
CREATE INDEX idx_velocity_sprint ON magnus_velocity_history(sprint_id);
```

### 1.2 Sync Engine Class

Create `/opt/leveredge/control-plane/agents/magnus/sync_engine.py`:

```python
"""
MAGNUS Sync Engine

Orchestrates bidirectional sync between MAGNUS and external PM tools.
"""

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import asyncpg

from adapters.base import PMAdapter, UnifiedProject, UnifiedTask
from adapters.openproject import OpenProjectAdapter
from adapters.leantime import LeantimeAdapter
from adapters.asana import AsanaAdapter
from adapters.jira import JiraAdapter
from adapters.monday import MondayAdapter
from adapters.linear import LinearAdapter
from adapters.notion import NotionAdapter


class SyncDirection(Enum):
    PUSH = "push"       # MAGNUS → External
    PULL = "pull"       # External → MAGNUS
    BIDIRECTIONAL = "bidirectional"


class ConflictResolution(Enum):
    MAGNUS_WINS = "magnus_wins"
    EXTERNAL_WINS = "external_wins"
    NEWEST_WINS = "newest_wins"
    MANUAL = "manual"


ADAPTER_REGISTRY = {
    "openproject": OpenProjectAdapter,
    "leantime": LeantimeAdapter,
    "asana": AsanaAdapter,
    "jira": JiraAdapter,
    "monday": MondayAdapter,
    "linear": LinearAdapter,
    "notion": NotionAdapter,
}


class SyncEngine:
    """
    Orchestrates sync between MAGNUS and external PM tools.
    
    Features:
    - Bidirectional sync with conflict detection
    - Change tracking via hashing
    - Conflict resolution strategies
    - Detailed sync logging
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
        self.adapters: Dict[str, PMAdapter] = {}
    
    async def get_adapter(self, connection_id: str) -> Optional[PMAdapter]:
        """Get or create adapter for a connection"""
        if connection_id in self.adapters:
            return self.adapters[connection_id]
        
        async with self.pool.acquire() as conn:
            connection = await conn.fetchrow(
                "SELECT * FROM magnus_pm_connections WHERE id = $1",
                connection_id
            )
            
            if not connection:
                return None
            
            tool_name = connection['tool_name']
            adapter_class = ADAPTER_REGISTRY.get(tool_name)
            
            if not adapter_class:
                return None
            
            # Get credentials from AEGIS (or fallback to config)
            credentials = await self._get_credentials(connection['credentials_key'])
            
            config = {
                "instance_url": connection['instance_url'],
                "credentials": credentials,
                **(connection['config'] or {})
            }
            
            adapter = adapter_class(config)
            self.adapters[connection_id] = adapter
            return adapter
    
    async def _get_credentials(self, credentials_key: str) -> dict:
        """Get credentials from AEGIS"""
        # TODO: Integrate with AEGIS
        # For now, credentials stored in config
        return {}
    
    def _compute_hash(self, data: dict) -> str:
        """Compute hash of entity data for change detection"""
        # Normalize and hash key fields
        normalized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    async def _log_sync(
        self,
        connection_id: str,
        sync_type: str,
        direction: str,
        status: str,
        items_synced: int = 0,
        items_failed: int = 0,
        conflicts: int = 0,
        error: str = None,
        details: dict = None
    ) -> str:
        """Log sync operation"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO magnus_sync_log 
                (connection_id, sync_type, direction, status, items_synced, 
                 items_failed, conflicts_detected, error_message, details, completed_at)
                VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8, $9, 
                        CASE WHEN $4 IN ('completed', 'failed', 'partial') THEN NOW() ELSE NULL END)
                RETURNING id
            """, connection_id, sync_type, direction, status, items_synced,
                items_failed, conflicts, error, json.dumps(details or {}))
            return str(row['id'])
    
    # =========================================
    # PROJECT SYNC
    # =========================================
    
    async def sync_projects(
        self,
        connection_id: str,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    ) -> dict:
        """Sync all projects for a connection"""
        adapter = await self.get_adapter(connection_id)
        if not adapter:
            return {"error": "Connection not found or adapter unavailable"}
        
        log_id = await self._log_sync(connection_id, "full", direction.value, "started")
        
        try:
            results = {
                "pulled": 0,
                "pushed": 0,
                "conflicts": 0,
                "errors": []
            }
            
            if direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
                pull_result = await self._pull_projects(connection_id, adapter)
                results["pulled"] = pull_result["synced"]
                results["conflicts"] += pull_result["conflicts"]
                results["errors"].extend(pull_result.get("errors", []))
            
            if direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
                push_result = await self._push_projects(connection_id, adapter)
                results["pushed"] = push_result["synced"]
                results["errors"].extend(push_result.get("errors", []))
            
            await self._log_sync(
                connection_id, "full", direction.value, "completed",
                items_synced=results["pulled"] + results["pushed"],
                conflicts=results["conflicts"],
                details=results
            )
            
            return results
            
        except Exception as e:
            await self._log_sync(
                connection_id, "full", direction.value, "failed",
                error=str(e)
            )
            return {"error": str(e)}
    
    async def _pull_projects(self, connection_id: str, adapter: PMAdapter) -> dict:
        """Pull projects from external tool into MAGNUS"""
        result = {"synced": 0, "conflicts": 0, "errors": []}
        
        try:
            external_projects = await adapter.list_projects()
            
            async with self.pool.acquire() as conn:
                for ext_proj in external_projects:
                    try:
                        # Check if mapping exists
                        mapping = await conn.fetchrow("""
                            SELECT * FROM magnus_project_mappings
                            WHERE connection_id = $1::uuid AND external_project_id = $2
                        """, connection_id, ext_proj.external_id)
                        
                        if mapping:
                            # Update existing project
                            await conn.execute("""
                                UPDATE magnus_projects
                                SET name = $2, description = $3, updated_at = NOW()
                                WHERE id = $1
                            """, mapping['magnus_project_id'], ext_proj.name, ext_proj.description)
                            
                            await conn.execute("""
                                UPDATE magnus_project_mappings
                                SET last_sync_at = NOW(), external_project_name = $3
                                WHERE id = $1
                            """, mapping['id'], ext_proj.name)
                        else:
                            # Create new project in MAGNUS
                            new_proj = await conn.fetchrow("""
                                INSERT INTO magnus_projects (name, description, status)
                                VALUES ($1, $2, 'active')
                                RETURNING id
                            """, ext_proj.name, ext_proj.description)
                            
                            # Create mapping
                            await conn.execute("""
                                INSERT INTO magnus_project_mappings
                                (magnus_project_id, connection_id, external_project_id, external_project_name)
                                VALUES ($1, $2::uuid, $3, $4)
                            """, new_proj['id'], connection_id, ext_proj.external_id, ext_proj.name)
                        
                        result["synced"] += 1
                        
                    except Exception as e:
                        result["errors"].append(f"Project {ext_proj.name}: {str(e)}")
            
            # Update connection last sync
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    UPDATE magnus_pm_connections
                    SET last_sync_at = NOW(), last_sync_status = 'success'
                    WHERE id = $1::uuid
                """, connection_id)
                
        except Exception as e:
            result["errors"].append(str(e))
        
        return result
    
    async def _push_projects(self, connection_id: str, adapter: PMAdapter) -> dict:
        """Push MAGNUS projects to external tool"""
        result = {"synced": 0, "errors": []}
        
        async with self.pool.acquire() as conn:
            # Get MAGNUS projects that have mappings to this connection
            mappings = await conn.fetch("""
                SELECT pm.*, p.name, p.description, p.status
                FROM magnus_project_mappings pm
                JOIN magnus_projects p ON pm.magnus_project_id = p.id
                WHERE pm.connection_id = $1::uuid AND pm.sync_enabled = TRUE
            """, connection_id)
            
            for mapping in mappings:
                try:
                    project = UnifiedProject(
                        external_id=mapping['external_project_id'],
                        name=mapping['name'],
                        description=mapping['description'],
                        status=mapping['status']
                    )
                    
                    await adapter.update_project(project)
                    
                    await conn.execute("""
                        UPDATE magnus_project_mappings
                        SET last_sync_at = NOW()
                        WHERE id = $1
                    """, mapping['id'])
                    
                    result["synced"] += 1
                    
                except Exception as e:
                    result["errors"].append(f"Project {mapping['name']}: {str(e)}")
        
        return result
    
    # =========================================
    # TASK SYNC
    # =========================================
    
    async def sync_tasks(
        self,
        connection_id: str,
        project_mapping_id: str = None,
        direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    ) -> dict:
        """Sync tasks for a connection (optionally filtered by project)"""
        adapter = await self.get_adapter(connection_id)
        if not adapter:
            return {"error": "Connection not found"}
        
        log_id = await self._log_sync(connection_id, "incremental", direction.value, "started")
        
        try:
            results = {"pulled": 0, "pushed": 0, "conflicts": 0, "errors": []}
            
            # Get project mappings
            async with self.pool.acquire() as conn:
                if project_mapping_id:
                    mappings = await conn.fetch(
                        "SELECT * FROM magnus_project_mappings WHERE id = $1",
                        project_mapping_id
                    )
                else:
                    mappings = await conn.fetch("""
                        SELECT * FROM magnus_project_mappings
                        WHERE connection_id = $1::uuid AND sync_enabled = TRUE
                    """, connection_id)
            
            for mapping in mappings:
                if direction in [SyncDirection.PULL, SyncDirection.BIDIRECTIONAL]:
                    pull_result = await self._pull_tasks(connection_id, adapter, mapping)
                    results["pulled"] += pull_result["synced"]
                    results["conflicts"] += pull_result["conflicts"]
                    results["errors"].extend(pull_result.get("errors", []))
                
                if direction in [SyncDirection.PUSH, SyncDirection.BIDIRECTIONAL]:
                    push_result = await self._push_tasks(connection_id, adapter, mapping)
                    results["pushed"] += push_result["synced"]
                    results["errors"].extend(push_result.get("errors", []))
            
            await self._log_sync(
                connection_id, "incremental", direction.value, "completed",
                items_synced=results["pulled"] + results["pushed"],
                conflicts=results["conflicts"],
                details=results
            )
            
            return results
            
        except Exception as e:
            await self._log_sync(
                connection_id, "incremental", direction.value, "failed",
                error=str(e)
            )
            return {"error": str(e)}
    
    async def _pull_tasks(self, connection_id: str, adapter: PMAdapter, project_mapping: dict) -> dict:
        """Pull tasks from external tool"""
        result = {"synced": 0, "conflicts": 0, "errors": []}
        
        try:
            external_tasks = await adapter.list_tasks(project_mapping['external_project_id'])
            
            async with self.pool.acquire() as conn:
                for ext_task in external_tasks:
                    try:
                        # Check if mapping exists
                        task_mapping = await conn.fetchrow("""
                            SELECT tm.*, t.title, t.status, t.updated_at as magnus_updated
                            FROM magnus_task_mappings tm
                            JOIN magnus_tasks t ON tm.magnus_task_id = t.id
                            WHERE tm.connection_id = $1::uuid AND tm.external_task_id = $2
                        """, connection_id, ext_task.external_id)
                        
                        new_hash = self._compute_hash({
                            "title": ext_task.title,
                            "description": ext_task.description,
                            "status": ext_task.status,
                            "priority": ext_task.priority
                        })
                        
                        if task_mapping:
                            # Check for changes
                            if task_mapping['last_synced_hash'] != new_hash:
                                # Conflict detection (simplified - newest wins)
                                await conn.execute("""
                                    UPDATE magnus_tasks
                                    SET title = $2, description = $3, status = $4, 
                                        priority = $5, updated_at = NOW()
                                    WHERE id = $1
                                """, task_mapping['magnus_task_id'], ext_task.title,
                                    ext_task.description, ext_task.status, ext_task.priority)
                            
                            await conn.execute("""
                                UPDATE magnus_task_mappings
                                SET last_sync_at = NOW(), last_synced_hash = $2
                                WHERE id = $1
                            """, task_mapping['id'], new_hash)
                        else:
                            # Create new task in MAGNUS
                            new_task = await conn.fetchrow("""
                                INSERT INTO magnus_tasks 
                                (project_id, title, description, status, priority, 
                                 source_tool, external_url)
                                VALUES ($1, $2, $3, $4, $5, $6, $7)
                                RETURNING id
                            """, project_mapping['magnus_project_id'], ext_task.title,
                                ext_task.description, ext_task.status, ext_task.priority,
                                adapter.tool_name, ext_task.url)
                            
                            # Create mapping
                            await conn.execute("""
                                INSERT INTO magnus_task_mappings
                                (magnus_task_id, connection_id, external_task_id, 
                                 external_url, last_synced_hash)
                                VALUES ($1, $2::uuid, $3, $4, $5)
                            """, new_task['id'], connection_id, ext_task.external_id,
                                ext_task.url, new_hash)
                        
                        result["synced"] += 1
                        
                    except Exception as e:
                        result["errors"].append(f"Task {ext_task.title}: {str(e)}")
                        
        except Exception as e:
            result["errors"].append(str(e))
        
        return result
    
    async def _push_tasks(self, connection_id: str, adapter: PMAdapter, project_mapping: dict) -> dict:
        """Push MAGNUS tasks to external tool"""
        result = {"synced": 0, "errors": []}
        
        async with self.pool.acquire() as conn:
            # Get MAGNUS tasks for this project that need syncing
            tasks = await conn.fetch("""
                SELECT t.*, tm.external_task_id, tm.id as mapping_id
                FROM magnus_tasks t
                LEFT JOIN magnus_task_mappings tm ON t.id = tm.magnus_task_id 
                    AND tm.connection_id = $2::uuid
                WHERE t.project_id = $1
            """, project_mapping['magnus_project_id'], connection_id)
            
            for task in tasks:
                try:
                    unified_task = UnifiedTask(
                        external_id=task['external_task_id'] or "",
                        project_external_id=project_mapping['external_project_id'],
                        title=task['title'],
                        description=task.get('description'),
                        status=task['status'],
                        priority=task.get('priority', 'medium'),
                        due_date=task.get('due_date'),
                        estimated_hours=task.get('estimated_hours')
                    )
                    
                    if task['external_task_id']:
                        # Update existing
                        await adapter.update_task(unified_task)
                    else:
                        # Create new
                        created = await adapter.create_task(unified_task)
                        
                        # Create mapping
                        await conn.execute("""
                            INSERT INTO magnus_task_mappings
                            (magnus_task_id, connection_id, external_task_id, external_url)
                            VALUES ($1, $2::uuid, $3, $4)
                        """, task['id'], connection_id, created.external_id, created.url)
                        
                        # Update task with external URL
                        await conn.execute("""
                            UPDATE magnus_tasks
                            SET external_url = $2, source_tool = $3
                            WHERE id = $1
                        """, task['id'], created.url, adapter.tool_name)
                    
                    result["synced"] += 1
                    
                except Exception as e:
                    result["errors"].append(f"Task {task['title']}: {str(e)}")
        
        return result
    
    # =========================================
    # SINGLE ENTITY SYNC
    # =========================================
    
    async def sync_single_task(
        self,
        magnus_task_id: str,
        direction: SyncDirection = SyncDirection.PUSH
    ) -> dict:
        """Sync a single task to/from all connected tools"""
        results = {"synced_to": [], "errors": []}
        
        async with self.pool.acquire() as conn:
            # Get task and its mappings
            task = await conn.fetchrow(
                "SELECT * FROM magnus_tasks WHERE id = $1::uuid", magnus_task_id
            )
            
            if not task:
                return {"error": "Task not found"}
            
            # Get all connections for this project
            mappings = await conn.fetch("""
                SELECT pm.*, pc.tool_name, pc.instance_url
                FROM magnus_project_mappings pm
                JOIN magnus_pm_connections pc ON pm.connection_id = pc.id
                WHERE pm.magnus_project_id = $1 AND pm.sync_enabled = TRUE
            """, task['project_id'])
            
            for mapping in mappings:
                try:
                    adapter = await self.get_adapter(str(mapping['connection_id']))
                    if not adapter:
                        continue
                    
                    # Check for existing task mapping
                    task_mapping = await conn.fetchrow("""
                        SELECT * FROM magnus_task_mappings
                        WHERE magnus_task_id = $1::uuid AND connection_id = $2
                    """, magnus_task_id, mapping['connection_id'])
                    
                    unified_task = UnifiedTask(
                        external_id=task_mapping['external_task_id'] if task_mapping else "",
                        project_external_id=mapping['external_project_id'],
                        title=task['title'],
                        description=task.get('description'),
                        status=task['status'],
                        priority=task.get('priority', 'medium'),
                        due_date=task.get('due_date')
                    )
                    
                    if task_mapping:
                        await adapter.update_task(unified_task)
                    else:
                        created = await adapter.create_task(unified_task)
                        await conn.execute("""
                            INSERT INTO magnus_task_mappings
                            (magnus_task_id, connection_id, external_task_id, external_url)
                            VALUES ($1::uuid, $2, $3, $4)
                        """, magnus_task_id, mapping['connection_id'], 
                            created.external_id, created.url)
                    
                    results["synced_to"].append(mapping['tool_name'])
                    
                except Exception as e:
                    results["errors"].append(f"{mapping['tool_name']}: {str(e)}")
        
        return results
    
    # =========================================
    # CONFLICT RESOLUTION
    # =========================================
    
    async def resolve_conflict(
        self,
        conflict_id: str,
        resolution: ConflictResolution,
        merged_data: dict = None
    ) -> dict:
        """Resolve a sync conflict"""
        async with self.pool.acquire() as conn:
            conflict = await conn.fetchrow(
                "SELECT * FROM magnus_sync_conflicts WHERE id = $1::uuid",
                conflict_id
            )
            
            if not conflict:
                return {"error": "Conflict not found"}
            
            if resolution == ConflictResolution.MAGNUS_WINS:
                final_data = conflict['magnus_data']
                status = "resolved_magnus"
            elif resolution == ConflictResolution.EXTERNAL_WINS:
                final_data = conflict['external_data']
                status = "resolved_external"
            elif resolution == ConflictResolution.MANUAL and merged_data:
                final_data = merged_data
                status = "merged"
            else:
                return {"error": "Invalid resolution"}
            
            # Apply the resolution
            if conflict['entity_type'] == 'task':
                await conn.execute("""
                    UPDATE magnus_tasks
                    SET title = $2, description = $3, status = $4, updated_at = NOW()
                    WHERE id = $1::uuid
                """, conflict['magnus_entity_id'], final_data.get('title'),
                    final_data.get('description'), final_data.get('status'))
            
            # Mark conflict resolved
            await conn.execute("""
                UPDATE magnus_sync_conflicts
                SET status = $2, resolution = $3, resolved_at = NOW(), resolved_by = 'damon'
                WHERE id = $1::uuid
            """, conflict_id, status, json.dumps(final_data))
            
            return {"status": "resolved", "resolution": status}
```

---

## PHASE 2: CONNECTION MANAGEMENT ENDPOINTS (1-2 hours)

Add to `magnus.py`:

```python
# ============ CONNECTIONS ============

class ConnectionCreate(BaseModel):
    tool_name: str  # openproject, leantime, asana, etc.
    display_name: str
    instance_url: str
    api_key: str  # Will be stored in AEGIS
    sync_direction: str = "bidirectional"
    sync_frequency: str = "realtime"


@app.post("/connections")
async def create_connection(conn_req: ConnectionCreate):
    """Connect a new PM tool"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    # Store API key in AEGIS (TODO: integrate with AEGIS)
    credentials_key = f"magnus_{conn_req.tool_name}_{datetime.now().timestamp()}"
    
    async with pool.acquire() as conn:
        # Test connection first
        adapter_class = ADAPTER_REGISTRY.get(conn_req.tool_name)
        if not adapter_class:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {conn_req.tool_name}")
        
        adapter = adapter_class({
            "instance_url": conn_req.instance_url,
            "credentials": {"api_key": conn_req.api_key}
        })
        
        if not await adapter.test_connection():
            raise HTTPException(status_code=400, detail="Connection test failed")
        
        row = await conn.fetchrow("""
            INSERT INTO magnus_pm_connections 
            (tool_name, display_name, instance_url, credentials_key, 
             sync_direction, sync_frequency, config)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, conn_req.tool_name, conn_req.display_name, conn_req.instance_url,
            credentials_key, conn_req.sync_direction, conn_req.sync_frequency,
            json.dumps({"api_key": conn_req.api_key}))  # Temporary - use AEGIS
        
        return {
            "status": "connected",
            "connection": dict(row),
            "magnus_says": f"The {conn_req.tool_name} board is now under my control."
        }


@app.get("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test a connection"""
    adapter = await sync_engine.get_adapter(connection_id)
    if not adapter:
        return {"status": "error", "message": "Connection not found"}
    
    success = await adapter.test_connection()
    return {
        "status": "success" if success else "failed",
        "connection_id": connection_id
    }


@app.post("/connections/{connection_id}/sync")
async def trigger_sync(connection_id: str, direction: str = "bidirectional"):
    """Trigger manual sync for a connection"""
    sync_dir = SyncDirection(direction)
    
    # Sync projects first
    project_result = await sync_engine.sync_projects(connection_id, sync_dir)
    
    # Then sync tasks
    task_result = await sync_engine.sync_tasks(connection_id, direction=sync_dir)
    
    return {
        "status": "completed",
        "projects": project_result,
        "tasks": task_result,
        "magnus_says": "All pieces synchronized. The board is current."
    }


@app.get("/connections/{connection_id}/projects")
async def list_external_projects(connection_id: str):
    """List projects from external tool"""
    adapter = await sync_engine.get_adapter(connection_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    projects = await adapter.list_projects()
    return {
        "projects": [p.dict() for p in projects],
        "count": len(projects)
    }


@app.post("/connections/{connection_id}/map-project")
async def map_project(connection_id: str, magnus_project_id: str, external_project_id: str):
    """Map a MAGNUS project to an external project"""
    async with pool.acquire() as conn:
        # Get external project name
        adapter = await sync_engine.get_adapter(connection_id)
        ext_project = await adapter.get_project(external_project_id)
        
        row = await conn.fetchrow("""
            INSERT INTO magnus_project_mappings
            (magnus_project_id, connection_id, external_project_id, external_project_name)
            VALUES ($1::uuid, $2::uuid, $3, $4)
            ON CONFLICT (connection_id, external_project_id) 
            DO UPDATE SET magnus_project_id = $1::uuid
            RETURNING *
        """, magnus_project_id, connection_id, external_project_id,
            ext_project.name if ext_project else "Unknown")
        
        return {
            "status": "mapped",
            "mapping": dict(row)
        }
```

---

## PHASE 3: UNIFIED VIEW ENDPOINTS (1-2 hours)

```python
# ============ UNIFIED VIEW ============

@app.get("/unified/tasks")
async def unified_task_list(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,  # Filter by source tool
    project_id: Optional[str] = None,
    limit: int = 100
):
    """
    Get unified task list across ALL connected tools.
    This is THE view - everything in one place.
    """
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        query = """
            SELECT 
                t.*,
                p.name as project_name,
                s.name as sprint_name,
                tm.external_task_id,
                tm.external_url,
                pc.tool_name as source_tool_name,
                pc.display_name as source_display_name
            FROM magnus_tasks t
            JOIN magnus_projects p ON t.project_id = p.id
            LEFT JOIN magnus_sprints s ON t.sprint_id = s.id
            LEFT JOIN magnus_task_mappings tm ON t.id = tm.magnus_task_id
            LEFT JOIN magnus_pm_connections pc ON tm.connection_id = pc.id
            WHERE 1=1
        """
        params = []
        
        if status:
            params.append(status)
            query += f" AND t.status = ${len(params)}"
        if priority:
            params.append(priority)
            query += f" AND t.priority = ${len(params)}"
        if source:
            params.append(source)
            query += f" AND (t.source_tool = ${len(params)} OR pc.tool_name = ${len(params)})"
        if project_id:
            params.append(project_id)
            query += f" AND t.project_id = ${len(params)}::uuid"
        
        query += f" ORDER BY t.priority DESC, t.due_date NULLS LAST LIMIT {limit}"
        
        rows = await conn.fetch(query, *params)
        
        # Group by source for summary
        by_source = {}
        for row in rows:
            source = row['source_tool'] or 'magnus'
            if source not in by_source:
                by_source[source] = 0
            by_source[source] += 1
        
        return {
            "tasks": [dict(r) for r in rows],
            "total": len(rows),
            "by_source": by_source,
            "magnus_says": f"Viewing {len(rows)} tasks across {len(by_source)} sources."
        }


@app.get("/unified/dashboard")
async def unified_dashboard():
    """
    The command center dashboard - everything at a glance.
    """
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        # Overall stats
        stats = await conn.fetchrow("""
            SELECT 
                (SELECT COUNT(*) FROM magnus_projects WHERE status = 'active') as active_projects,
                (SELECT COUNT(*) FROM magnus_tasks WHERE status NOT IN ('done', 'cancelled')) as open_tasks,
                (SELECT COUNT(*) FROM magnus_tasks WHERE status = 'blocked') as blocked_tasks,
                (SELECT COUNT(*) FROM magnus_tasks WHERE due_date < CURRENT_DATE AND status NOT IN ('done', 'cancelled')) as overdue_tasks,
                (SELECT COUNT(*) FROM magnus_sprints WHERE status = 'active') as active_sprints,
                (SELECT COUNT(*) FROM magnus_pm_connections WHERE sync_enabled = TRUE) as connected_tools,
                (SELECT COUNT(*) FROM magnus_sync_conflicts WHERE status = 'pending') as pending_conflicts
        """)
        
        # Tasks by status
        by_status = await conn.fetch("""
            SELECT status, COUNT(*) as count
            FROM magnus_tasks
            GROUP BY status
        """)
        
        # Tasks by source tool
        by_source = await conn.fetch("""
            SELECT COALESCE(source_tool, 'magnus') as source, COUNT(*) as count
            FROM magnus_tasks
            GROUP BY source_tool
        """)
        
        # Connected tools status
        connections = await conn.fetch("""
            SELECT tool_name, display_name, last_sync_at, last_sync_status, sync_enabled
            FROM magnus_pm_connections
            ORDER BY tool_name
        """)
        
        # Active sprint progress
        active_sprint = await conn.fetchrow("""
            SELECT s.*,
                (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = s.id) as total_tasks,
                (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = s.id AND status = 'done') as done_tasks
            FROM magnus_sprints s
            WHERE s.status = 'active'
            LIMIT 1
        """)
        
        # Today's time logged
        time_today = await conn.fetchrow("""
            SELECT COALESCE(SUM(hours), 0) as hours
            FROM magnus_time_entries
            WHERE date = CURRENT_DATE
        """)
        
        # Assessment
        overdue = stats['overdue_tasks']
        blocked = stats['blocked_tasks']
        conflicts = stats['pending_conflicts']
        
        if overdue > 10 or blocked > 5 or conflicts > 3:
            health = "🚨 CRITICAL"
            assessment = "Multiple positions under attack. Immediate action required."
        elif overdue > 5 or blocked > 2 or conflicts > 0:
            health = "⚠️ AT RISK"
            assessment = "Some pressure on the board. Focused attention needed."
        elif overdue > 0 or blocked > 0:
            health = "🔶 MINOR ISSUES"
            assessment = "Small obstacles. Easily managed."
        else:
            health = "✅ ON TRACK"
            assessment = "Strong position. All pieces coordinated."
        
        return {
            "health": health,
            "assessment": assessment,
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "stats": dict(stats),
            "tasks_by_status": {r['status']: r['count'] for r in by_status},
            "tasks_by_source": {r['source']: r['count'] for r in by_source},
            "connected_tools": [dict(c) for c in connections],
            "active_sprint": dict(active_sprint) if active_sprint else None,
            "time_logged_today": float(time_today['hours']) if time_today else 0,
            "timestamp": datetime.now().isoformat()
        }


@app.get("/unified/overdue")
async def unified_overdue():
    """Get all overdue tasks across all sources"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT t.*, p.name as project_name, 
                   COALESCE(t.source_tool, 'magnus') as source
            FROM magnus_tasks t
            JOIN magnus_projects p ON t.project_id = p.id
            WHERE t.due_date < CURRENT_DATE 
            AND t.status NOT IN ('done', 'cancelled')
            ORDER BY t.due_date, t.priority DESC
        """)
        
        return {
            "overdue_tasks": [dict(r) for r in rows],
            "count": len(rows),
            "magnus_says": f"{len(rows)} pieces behind schedule. Time to accelerate."
        }
```

---

## PHASE 4: SPRINTS + TIME TRACKING (2 hours)

See original HERACLES merge spec for detailed sprint and time tracking endpoints.

Key additions:
- POST /sprints - Create sprint
- POST /sprints/{id}/start - Start sprint
- POST /sprints/{id}/complete - Complete + calculate velocity
- GET /sprints/{id}/burndown - Burndown data
- POST /time - Log time
- POST /time/timer/start - Start timer
- POST /time/timer/stop - Stop timer + auto-log
- GET /velocity - Rolling velocity
- GET /velocity/forecast - Delivery forecast

---

## PHASE 5: AI FEATURES (1-2 hours)

```python
# ============ AI BRAIN ============

@app.post("/ai/breakdown")
async def ai_task_breakdown(task_id: str = None, title: str = None, description: str = None):
    """AI-powered task breakdown"""
    if task_id:
        async with pool.acquire() as conn:
            task = await conn.fetchrow(
                "SELECT * FROM magnus_tasks WHERE id = $1::uuid", task_id
            )
            if task:
                title = task['title']
                description = task.get('description', '')
    
    if not title:
        raise HTTPException(status_code=400, detail="Title required")
    
    prompt = f"""Break down this task into actionable subtasks:

**Task:** {title}
**Description:** {description or 'No description'}

Provide 3-7 subtasks with:
1. Clear, action-oriented title
2. Brief description
3. Estimated hours
4. Priority (critical/high/medium/low)
5. Any dependencies

Format as JSON:
{{
  "subtasks": [
    {{"title": "...", "description": "...", "estimated_hours": N, "priority": "...", "depends_on": []}}
  ],
  "total_estimate": N,
  "suggested_sprint_points": N,
  "notes": "..."
}}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "original_task": {"title": title, "description": description},
        "breakdown": response.content[0].text,
        "magnus_says": "I've analyzed the position. Here's how to break it down."
    }


@app.post("/ai/estimate")
async def ai_effort_estimate(title: str, description: str = None, context: str = None):
    """AI-powered effort estimation"""
    prompt = f"""Estimate the effort for this task:

**Task:** {title}
**Description:** {description or 'No description'}
**Context:** {context or 'General software/automation work'}

Provide:
1. Estimated hours (pessimistic, likely, optimistic)
2. Story points (1, 2, 3, 5, 8, 13, 21)
3. Risk factors that could extend the estimate
4. Confidence level (low/medium/high)

Format as JSON:
{{
  "hours": {{"optimistic": N, "likely": N, "pessimistic": N}},
  "story_points": N,
  "risk_factors": ["..."],
  "confidence": "...",
  "notes": "..."
}}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "task": {"title": title, "description": description},
        "estimate": response.content[0].text
    }


@app.post("/ai/sprint-plan")
async def ai_sprint_planning(
    project_id: str,
    sprint_capacity_hours: float = 40,
    sprint_goal: str = None
):
    """AI-powered sprint planning recommendation"""
    async with pool.acquire() as conn:
        # Get backlog tasks
        tasks = await conn.fetch("""
            SELECT * FROM magnus_tasks
            WHERE project_id = $1::uuid 
            AND sprint_id IS NULL
            AND status NOT IN ('done', 'cancelled')
            ORDER BY priority DESC, created_at
        """, project_id)
        
        # Get velocity history
        velocity = await conn.fetchrow("""
            SELECT AVG(velocity_points) as avg_velocity
            FROM magnus_velocity_history
            WHERE project_id = $1::uuid
        """, project_id)
    
    backlog_summary = "\n".join([
        f"- {t['title']} ({t['priority']}, {t.get('estimated_hours', '?')}h, {t.get('story_points', '?')}pts)"
        for t in tasks[:20]
    ])
    
    prompt = f"""Plan a sprint with these constraints:

**Capacity:** {sprint_capacity_hours} hours
**Sprint Goal:** {sprint_goal or 'Not specified'}
**Average Velocity:** {velocity['avg_velocity'] if velocity else 'Unknown'} points/sprint

**Backlog (top 20):**
{backlog_summary}

Recommend:
1. Which tasks to include (by title)
2. Total estimated hours
3. Total story points
4. Risk assessment
5. What to deprioritize

Format as JSON:
{{
  "recommended_tasks": ["task title 1", "task title 2", ...],
  "total_hours": N,
  "total_points": N,
  "utilization_pct": N,
  "risk_level": "low|medium|high",
  "risk_factors": ["..."],
  "deprioritized": ["..."],
  "notes": "..."
}}
"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return {
        "capacity_hours": sprint_capacity_hours,
        "backlog_count": len(tasks),
        "recommendation": response.content[0].text,
        "magnus_says": "I've calculated the optimal sprint composition."
    }
```

---

## PHASE 6: WEBHOOKS (Optional - Post-Launch)

Real-time updates from external tools via webhooks.

---

## DELIVERABLES CHECKLIST

- [ ] Database schema (connections, mappings, sync log, conflicts)
- [ ] Database schema (sprints, time entries, velocity)
- [ ] SyncEngine class with bidirectional sync
- [ ] Connection management endpoints
- [ ] Unified view endpoints (tasks, dashboard, overdue)
- [ ] Sprint management endpoints
- [ ] Time tracking with timers
- [ ] Velocity + forecasting
- [ ] AI breakdown, estimation, sprint planning
- [ ] Updated status/standup with unified view
- [ ] Tests for sync engine

---

## COMMIT MESSAGE

```
MAGNUS: Unified Command Center - The Badass PM

SYNC ENGINE:
- Bidirectional sync with OpenProject, Leantime, Asana, Jira, Monday, Linear, Notion
- Conflict detection and resolution
- Change tracking via hashing
- Detailed sync logging

UNIFIED VIEW:
- Single pane of glass across ALL connected tools
- Cross-tool task list with source tracking
- Unified dashboard with health assessment
- Overdue tasks from everywhere

SPRINTS & TIME:
- Sprint management with capacity planning
- Time tracking with start/stop timers
- Velocity calculations + history
- Delivery forecasting

AI BRAIN:
- Task breakdown
- Effort estimation
- Sprint planning recommendations

Every PM tool is now a piece on MAGNUS's board.
Checkmate is inevitable.
```

---

*"I don't just manage projects. I orchestrate armies across multiple battlefields. Every tool, every task, every timeline - all pieces on my board."*
