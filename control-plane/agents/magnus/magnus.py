"""
MAGNUS - Universal Project Master
Port: 8017
Domain: CHANCERY

Every move calculated. Every piece in position. Checkmate is inevitable.

UNIFIED COMMAND CENTER:
- Bidirectional sync with external PM tools
- Single pane of glass across ALL connected tools
- Sprints, time tracking, velocity
- AI-powered planning and breakdown

COUNCIL INTEGRATION:
- MAGNUS is a PERMANENT council member (auto-joins ALL meetings)
- Takes notes, tracks action items, creates tasks from decisions
- Follows up on commitments and monitors deadlines
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal
import os
import json
import asyncpg
import anthropic

app = FastAPI(
    title="MAGNUS - Universal Project Master",
    description="Every move calculated. Every piece in position. Checkmate is inevitable.",
    version="2.0.0"
)

# Initialize Anthropic client for AI features
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None

DATABASE_URL = os.environ.get("DATABASE_URL")
pool: asyncpg.Pool = None

# Import sync engine after pool is available
sync_engine = None


@app.on_event("startup")
async def startup():
    global pool, sync_engine
    if DATABASE_URL:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
        # Initialize sync engine
        from sync_engine import SyncEngine
        sync_engine = SyncEngine(pool)


@app.on_event("shutdown")
async def shutdown():
    if pool:
        await pool.close()


# ============ HEALTH ============

@app.get("/health")
async def health():
    db_status = "connected" if pool else "no connection"
    return {
        "status": "healthy",
        "service": "MAGNUS - Universal Project Master",
        "version": "2.0.0",
        "port": 8017,
        "database": db_status,
        "sync_engine": "ready" if sync_engine else "not initialized",
        "tagline": "Every move calculated. Every piece in position. Checkmate is inevitable."
    }


@app.get("/status")
async def magnus_status():
    """MAGNUS's current assessment of the board"""
    if not pool:
        return {
            "magnus_says": "Database not connected. Cannot assess the board.",
            "active_projects": 0,
            "overdue_tasks": 0,
            "open_blockers": 0,
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "timestamp": datetime.now().isoformat()
        }

    async with pool.acquire() as conn:
        # Get active projects count
        projects = await conn.fetch("""
            SELECT * FROM magnus_projects WHERE status IN ('planning', 'active')
        """)

        # Get overdue tasks count
        overdue = await conn.fetchrow("""
            SELECT COUNT(*) as count FROM magnus_tasks
            WHERE due_date < CURRENT_DATE AND status NOT IN ('done', 'cancelled')
        """)

        # Get open blockers count
        blockers = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM magnus_blockers WHERE status = 'open'"
        )

        # Get connected tools count
        connections = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM magnus_pm_connections WHERE sync_enabled = TRUE"
        )

        # Get pending conflicts
        conflicts = await conn.fetchrow(
            "SELECT COUNT(*) as count FROM magnus_sync_conflicts WHERE status = 'pending'"
        )

        overdue_count = overdue['count'] if overdue else 0
        blocker_count = blockers['count'] if blockers else 0
        connection_count = connections['count'] if connections else 0
        conflict_count = conflicts['count'] if conflicts else 0

        # MAGNUS's assessment
        if overdue_count > 5 or conflict_count > 3:
            assessment = "Critical position. Multiple pieces under attack. Immediate action required."
        elif blocker_count > 3:
            assessment = "Board congestion. Several pieces blocked. Need to clear lanes."
        elif overdue_count > 0 or blocker_count > 0 or conflict_count > 0:
            assessment = "Minor pressure on the position. Manageable with focused attention."
        else:
            assessment = "Strong position. Pieces are coordinated. Continuing the attack."

        return {
            "magnus_says": assessment,
            "active_projects": len(projects),
            "overdue_tasks": overdue_count,
            "open_blockers": blocker_count,
            "connected_tools": connection_count,
            "pending_conflicts": conflict_count,
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "timestamp": datetime.now().isoformat()
        }


# ============ PROJECTS ============

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_end: Optional[date] = None
    client_name: Optional[str] = None
    template: Optional[str] = None
    priority: int = 50


@app.get("/projects")
async def list_projects(status: Optional[str] = None):
    """List all projects with summaries"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Try the view first, fallback to simple query
        try:
            if status:
                rows = await conn.fetch(
                    "SELECT * FROM magnus_project_summary(NULL) WHERE status = $1",
                    status
                )
            else:
                rows = await conn.fetch("SELECT * FROM magnus_project_summary(NULL)")
        except Exception:
            # Fallback if view doesn't exist
            query = "SELECT * FROM magnus_projects"
            if status:
                query += " WHERE status = $1"
                rows = await conn.fetch(query, status)
            else:
                rows = await conn.fetch(query)
        return [dict(row) for row in rows]


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get a specific project with full details"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM magnus_projects WHERE id = $1::uuid",
            project_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return dict(row)


@app.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_projects (name, description, target_end, client_name, template_used, priority)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, project.name, project.description, project.target_end,
            project.client_name, project.template, project.priority)
        return dict(row)


@app.patch("/projects/{project_id}")
async def update_project(project_id: str, updates: Dict[str, Any]):
    """Update a project"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    allowed_fields = ['name', 'description', 'status', 'priority', 'target_end', 'client_name']
    updates = {k: v for k, v in updates.items() if k in allowed_fields}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    set_clause = ", ".join([f"{k} = ${i+2}" for i, k in enumerate(updates.keys())])
    set_clause += ", updated_at = NOW()"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE magnus_projects SET {set_clause} WHERE id = $1::uuid RETURNING *",
            project_id, *updates.values()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Project not found")
        return dict(row)


# ============ TASKS ============

class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    assigned_agent: Optional[str] = None
    due_date: Optional[date] = None
    priority: str = "medium"
    estimated_hours: Optional[float] = None
    sprint_id: Optional[str] = None
    story_points: Optional[float] = None


@app.get("/tasks")
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    sprint_id: Optional[str] = None,
    overdue: bool = False
):
    """List tasks with optional filters"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        if overdue:
            rows = await conn.fetch("""
                SELECT t.*, p.name as project_name
                FROM magnus_tasks t
                JOIN magnus_projects p ON t.project_id = p.id
                WHERE t.due_date < CURRENT_DATE
                AND t.status NOT IN ('done', 'cancelled')
                ORDER BY t.due_date
            """)
        else:
            query = """
                SELECT t.*, p.name as project_name
                FROM magnus_tasks t
                JOIN magnus_projects p ON t.project_id = p.id
                WHERE 1=1
            """
            params = []

            if project_id:
                params.append(project_id)
                query += f" AND t.project_id = ${len(params)}::uuid"
            if status:
                params.append(status)
                query += f" AND t.status = ${len(params)}"
            if assigned_agent:
                params.append(assigned_agent)
                query += f" AND t.assigned_agent = ${len(params)}"
            if sprint_id:
                params.append(sprint_id)
                query += f" AND t.sprint_id = ${len(params)}::uuid"

            query += " ORDER BY t.priority DESC, t.due_date"
            rows = await conn.fetch(query, *params)

        return [dict(row) for row in rows]


@app.post("/tasks")
async def create_task(task: TaskCreate):
    """Create a new task"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_tasks (project_id, title, description, assigned_agent,
                                      due_date, priority, estimated_hours, sprint_id, story_points)
            VALUES ($1::uuid, $2, $3, $4, $5, $6, $7, $8::uuid, $9)
            RETURNING *
        """, task.project_id, task.title, task.description, task.assigned_agent,
            task.due_date, task.priority, task.estimated_hours,
            task.sprint_id, task.story_points)
        return dict(row)


@app.patch("/tasks/{task_id}")
async def update_task(task_id: str, updates: Dict[str, Any]):
    """Update a task"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    allowed_fields = ['title', 'description', 'status', 'priority', 'assigned_agent',
                      'due_date', 'estimated_hours', 'sprint_id', 'story_points']
    updates = {k: v for k, v in updates.items() if k in allowed_fields}

    if not updates:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    # Build the query dynamically
    set_parts = []
    params = [task_id]
    for i, (k, v) in enumerate(updates.items()):
        if k in ['sprint_id', 'project_id']:
            set_parts.append(f"{k} = ${i+2}::uuid")
        else:
            set_parts.append(f"{k} = ${i+2}")
        params.append(v)

    set_clause = ", ".join(set_parts) + ", updated_at = NOW()"

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"UPDATE magnus_tasks SET {set_clause} WHERE id = $1::uuid RETURNING *",
            *params
        )
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return dict(row)


@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, notes: Optional[str] = None):
    """Mark a task as complete"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE magnus_tasks
            SET status = 'done', completed_at = NOW(), notes = COALESCE($2, notes)
            WHERE id = $1::uuid
            RETURNING *
        """, task_id, notes)
        if not row:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"status": "completed", "task": dict(row)}


@app.post("/tasks/{task_id}/block")
async def block_task(task_id: str, reason: str, blocker_type: str = "other"):
    """Mark a task as blocked and create a blocker"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        task = await conn.fetchrow("""
            UPDATE magnus_tasks SET status = 'blocked', updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, task_id)

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        blocker = await conn.fetchrow("""
            INSERT INTO magnus_blockers (task_id, project_id, description, blocker_type)
            VALUES ($1::uuid, $2, $3, $4)
            RETURNING *
        """, task_id, task['project_id'], reason, blocker_type)

        return {
            "status": "blocked",
            "task": dict(task),
            "blocker": dict(blocker)
        }


# ============ BLOCKERS ============

@app.get("/blockers")
async def list_blockers(status: str = "open"):
    """List blockers"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT b.*, t.title as task_title, p.name as project_name
            FROM magnus_blockers b
            LEFT JOIN magnus_tasks t ON b.task_id = t.id
            LEFT JOIN magnus_projects p ON b.project_id = p.id
            WHERE b.status = $1
            ORDER BY b.severity DESC, b.created_at
        """, status)
        return [dict(row) for row in rows]


@app.post("/blockers/{blocker_id}/resolve")
async def resolve_blocker(blocker_id: str, resolution: str):
    """Resolve a blocker"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        blocker = await conn.fetchrow("""
            UPDATE magnus_blockers
            SET status = 'resolved', resolution = $2, resolved_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, blocker_id, resolution)

        if not blocker:
            raise HTTPException(status_code=404, detail="Blocker not found")

        if blocker['task_id']:
            await conn.execute("""
                UPDATE magnus_tasks SET status = 'todo', updated_at = NOW()
                WHERE id = $1 AND status = 'blocked'
            """, blocker['task_id'])

        return {"status": "resolved", "blocker": dict(blocker)}


# ============ DECISIONS ============

class DecisionCreate(BaseModel):
    project_id: str
    question: str
    context: Optional[str] = None
    options: List[str] = []
    deadline: Optional[date] = None


@app.get("/decisions")
async def list_decisions(status: str = "pending"):
    """List pending decisions"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT d.*, p.name as project_name
            FROM magnus_decisions d
            JOIN magnus_projects p ON d.project_id = p.id
            WHERE d.status = $1
            ORDER BY d.decision_deadline, d.created_at
        """, status)
        return [dict(row) for row in rows]


@app.post("/decisions")
async def create_decision(decision: DecisionCreate):
    """Create a decision request"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_decisions (project_id, question, context, options, decision_deadline)
            VALUES ($1::uuid, $2, $3, $4::jsonb, $5)
            RETURNING *
        """, decision.project_id, decision.question, decision.context,
            json.dumps(decision.options), decision.deadline)
        return dict(row)


@app.post("/decisions/{decision_id}/decide")
async def make_decision(decision_id: str, decision: str, rationale: Optional[str] = None):
    """Record a decision"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE magnus_decisions
            SET status = 'decided', decision = $2, rationale = $3,
                decided_by = 'damon', decided_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, decision_id, decision, rationale)
        if not row:
            raise HTTPException(status_code=404, detail="Decision not found")
        return dict(row)


# ============ CONNECTIONS (PM Tool Sync) ============

from adapters import ADAPTERS


class ConnectionCreate(BaseModel):
    tool_name: str  # openproject, leantime, asana, etc.
    display_name: str
    instance_url: str
    api_key: str  # Will be stored in config (AEGIS integration TODO)
    sync_direction: str = "bidirectional"
    sync_frequency: str = "realtime"


@app.get("/connections")
async def list_connections():
    """List PM tool connections"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM magnus_pm_connections ORDER BY tool_name"
        )
        return [dict(row) for row in rows]


@app.get("/connections/supported")
async def supported_tools():
    """List supported PM tools"""
    return [
        {"name": "leantime", "status": "implemented", "internal": True},
        {"name": "openproject", "status": "implemented", "internal": True},
        {"name": "asana", "status": "implemented", "internal": False},
        {"name": "jira", "status": "implemented", "internal": False},
        {"name": "monday", "status": "implemented", "internal": False},
        {"name": "notion", "status": "implemented", "internal": False},
        {"name": "linear", "status": "implemented", "internal": False},
        {"name": "clickup", "status": "planned", "internal": False},
        {"name": "trello", "status": "planned", "internal": False}
    ]


@app.post("/connections")
async def create_connection(conn_req: ConnectionCreate):
    """Connect a new PM tool"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    # Check if adapter exists
    adapter_class = ADAPTERS.get(conn_req.tool_name)
    if not adapter_class:
        raise HTTPException(status_code=400, detail=f"Unknown tool: {conn_req.tool_name}. Supported: {list(ADAPTERS.keys())}")

    # Test connection first
    adapter = adapter_class({
        "instance_url": conn_req.instance_url,
        "credentials": {"api_key": conn_req.api_key}
    })

    try:
        connection_ok = await adapter.test_connection()
        if not connection_ok:
            raise HTTPException(status_code=400, detail="Connection test failed - check URL and API key")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {str(e)}")

    # Store credentials in config (AEGIS integration TODO)
    credentials_key = f"magnus_{conn_req.tool_name}_{datetime.now().timestamp()}"

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_pm_connections
            (tool_name, connection_name, display_name, instance_url, aegis_credential_key,
             sync_direction, config)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (tool_name, connection_name) DO UPDATE
            SET instance_url = $4, config = $7, updated_at = NOW()
            RETURNING *
        """, conn_req.tool_name, conn_req.display_name, conn_req.display_name,
            conn_req.instance_url, credentials_key, conn_req.sync_direction,
            json.dumps({"api_key": conn_req.api_key}))

        return {
            "status": "connected",
            "connection": dict(row),
            "magnus_says": f"The {conn_req.tool_name} board is now under my control."
        }


@app.get("/connections/{connection_id}/test")
async def test_connection(connection_id: str):
    """Test a connection"""
    if not sync_engine:
        return {"status": "error", "message": "Sync engine not initialized"}

    adapter = await sync_engine.get_adapter(connection_id)
    if not adapter:
        return {"status": "error", "message": "Connection not found"}

    try:
        success = await adapter.test_connection()
        return {
            "status": "success" if success else "failed",
            "connection_id": connection_id
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/connections/{connection_id}/sync")
async def trigger_sync(
    connection_id: str,
    background_tasks: BackgroundTasks,
    direction: str = "bidirectional",
    wait: bool = False
):
    """
    Trigger sync for a connection.

    Args:
        wait: If True, wait for completion. If False (default), run in background.
    """
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")

    from sync_engine import SyncDirection

    try:
        sync_dir = SyncDirection(direction)
    except ValueError:
        sync_dir = SyncDirection.BIDIRECTIONAL

    if wait:
        # Synchronous - wait for completion
        project_result = await sync_engine.sync_projects(connection_id, sync_dir)
        task_result = await sync_engine.sync_tasks(connection_id, direction=sync_dir)
        return {
            "status": "completed",
            "projects": project_result,
            "tasks": task_result,
            "magnus_says": "All pieces synchronized. The board is current."
        }
    else:
        # Background - return immediately
        background_tasks.add_task(sync_engine.sync_projects, connection_id, sync_dir)
        background_tasks.add_task(sync_engine.sync_tasks, connection_id, None, sync_dir)
        return {
            "status": "started",
            "message": "Sync running in background. Check /sync/status for progress.",
            "magnus_says": "The pieces are moving. I'll update you when the board is set."
        }


@app.get("/connections/{connection_id}/projects")
async def list_external_projects(connection_id: str):
    """List projects from external tool"""
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")

    adapter = await sync_engine.get_adapter(connection_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Connection not found")

    try:
        projects = await adapter.list_projects()
        return {
            "projects": [p.model_dump() for p in projects],
            "count": len(projects)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/connections/{connection_id}/map-project")
async def map_project(connection_id: str, magnus_project_id: str, external_project_id: str):
    """Map a MAGNUS project to an external project"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    adapter = await sync_engine.get_adapter(connection_id) if sync_engine else None
    ext_project_name = "Unknown"

    if adapter:
        try:
            ext_project = await adapter.get_project(external_project_id)
            if ext_project:
                ext_project_name = ext_project.name
        except Exception:
            pass

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_project_mappings
            (magnus_project_id, connection_id, external_project_id, external_project_name)
            VALUES ($1::uuid, $2::uuid, $3, $4)
            ON CONFLICT (connection_id, external_project_id)
            DO UPDATE SET magnus_project_id = $1::uuid, last_sync_at = NOW()
            RETURNING *
        """, magnus_project_id, connection_id, external_project_id, ext_project_name)

        return {
            "status": "mapped",
            "mapping": dict(row)
        }


# ============ SYNC STATUS & ALL ============

@app.post("/sync/all")
async def sync_all_connections(background_tasks: BackgroundTasks):
    """
    Sync ALL connected tools simultaneously in background.
    True multitasking - all tools sync in parallel.
    """
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")
    if not sync_engine:
        raise HTTPException(status_code=503, detail="Sync engine not initialized")

    from sync_engine import SyncDirection

    async with pool.acquire() as conn:
        connections = await conn.fetch(
            "SELECT id, tool_name FROM magnus_pm_connections WHERE sync_enabled = TRUE"
        )

    for connection in connections:
        background_tasks.add_task(
            sync_engine.sync_projects,
            str(connection['id']),
            SyncDirection.BIDIRECTIONAL
        )
        background_tasks.add_task(
            sync_engine.sync_tasks,
            str(connection['id']),
            None,
            SyncDirection.BIDIRECTIONAL
        )

    return {
        "status": "started",
        "connections_syncing": len(connections),
        "tools": [c['tool_name'] for c in connections],
        "magnus_says": f"Synchronizing {len(connections)} battlefields simultaneously. All pieces moving."
    }


@app.get("/sync/status")
async def get_sync_status():
    """Get status of recent sync operations"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        recent = await conn.fetch("""
            SELECT sl.*, pc.tool_name, pc.display_name
            FROM magnus_sync_log sl
            JOIN magnus_pm_connections pc ON sl.connection_id = pc.id
            ORDER BY sl.started_at DESC
            LIMIT 20
        """)

        in_progress = [r for r in recent if r['status'] == 'running']

        return {
            "in_progress": len(in_progress),
            "recent_syncs": [dict(r) for r in recent],
            "magnus_says": f"{len(in_progress)} sync operations in progress." if in_progress else "All syncs complete."
        }


# ============ UNIFIED VIEW ============

@app.get("/unified/tasks")
async def unified_task_list(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    source: Optional[str] = None,
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
                COALESCE(tm.external_url, t.external_url) as external_url,
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

        query += f" ORDER BY CASE t.priority WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, t.due_date NULLS LAST LIMIT {limit}"

        rows = await conn.fetch(query, *params)

        # Group by source for summary
        by_source = {}
        for row in rows:
            source_name = row.get('source_tool') or row.get('source_tool_name') or 'magnus'
            if source_name not in by_source:
                by_source[source_name] = 0
            by_source[source_name] += 1

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
        # Try using the view first
        try:
            stats = await conn.fetchrow("SELECT * FROM magnus_dashboard_stats")
        except Exception:
            # Fallback to manual query
            stats = await conn.fetchrow("""
                SELECT
                    (SELECT COUNT(*) FROM magnus_projects WHERE status = 'active') as active_projects,
                    (SELECT COUNT(*) FROM magnus_tasks WHERE status NOT IN ('done', 'cancelled')) as open_tasks,
                    (SELECT COUNT(*) FROM magnus_tasks WHERE status = 'blocked') as blocked_tasks,
                    (SELECT COUNT(*) FROM magnus_tasks WHERE due_date < CURRENT_DATE AND status NOT IN ('done', 'cancelled')) as overdue_tasks,
                    (SELECT COUNT(*) FROM magnus_sprints WHERE status = 'active') as active_sprints,
                    (SELECT COUNT(*) FROM magnus_pm_connections WHERE sync_enabled = TRUE) as connected_tools,
                    (SELECT COUNT(*) FROM magnus_sync_conflicts WHERE status = 'pending') as pending_conflicts,
                    (SELECT COALESCE(SUM(hours), 0) FROM magnus_time_entries WHERE date = CURRENT_DATE) as time_logged_today
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

        # Assessment
        overdue = stats['overdue_tasks'] if stats else 0
        blocked = stats['blocked_tasks'] if stats else 0
        conflicts = stats['pending_conflicts'] if stats else 0

        if overdue > 10 or blocked > 5 or conflicts > 3:
            health = "CRITICAL"
            assessment = "Multiple positions under attack. Immediate action required."
        elif overdue > 5 or blocked > 2 or conflicts > 0:
            health = "AT RISK"
            assessment = "Some pressure on the board. Focused attention needed."
        elif overdue > 0 or blocked > 0:
            health = "MINOR ISSUES"
            assessment = "Small obstacles. Easily managed."
        else:
            health = "ON TRACK"
            assessment = "Strong position. All pieces coordinated."

        return {
            "health": health,
            "assessment": assessment,
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "stats": dict(stats) if stats else {},
            "tasks_by_status": {r['status']: r['count'] for r in by_status},
            "tasks_by_source": {r['source']: r['count'] for r in by_source},
            "connected_tools": [dict(c) for c in connections],
            "active_sprint": dict(active_sprint) if active_sprint else None,
            "time_logged_today": float(stats['time_logged_today']) if stats and stats['time_logged_today'] else 0,
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


# ============ SPRINTS ============

class SprintCreate(BaseModel):
    project_id: str
    name: str
    goal: Optional[str] = None
    start_date: date
    end_date: date
    capacity_hours: float = 40.0


@app.get("/sprints")
async def list_sprints(project_id: Optional[str] = None, status: Optional[str] = None):
    """List sprints"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        query = """
            SELECT s.*, p.name as project_name,
                (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = s.id) as task_count,
                (SELECT COUNT(*) FROM magnus_tasks WHERE sprint_id = s.id AND status = 'done') as done_count
            FROM magnus_sprints s
            JOIN magnus_projects p ON s.project_id = p.id
            WHERE 1=1
        """
        params = []

        if project_id:
            params.append(project_id)
            query += f" AND s.project_id = ${len(params)}::uuid"
        if status:
            params.append(status)
            query += f" AND s.status = ${len(params)}"

        query += " ORDER BY s.start_date DESC"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/sprints")
async def create_sprint(sprint: SprintCreate):
    """Create a new sprint"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

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
    """Start a sprint"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Check for other active sprints in same project
        sprint = await conn.fetchrow(
            "SELECT * FROM magnus_sprints WHERE id = $1::uuid", sprint_id
        )
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")

        active = await conn.fetchrow("""
            SELECT id FROM magnus_sprints
            WHERE project_id = $1 AND status = 'active' AND id != $2::uuid
        """, sprint['project_id'], sprint_id)

        if active:
            raise HTTPException(status_code=400, detail="Another sprint is already active")

        # Calculate committed points
        committed = await conn.fetchrow("""
            SELECT COALESCE(SUM(story_points), 0) as points
            FROM magnus_tasks WHERE sprint_id = $1::uuid
        """, sprint_id)

        row = await conn.fetchrow("""
            UPDATE magnus_sprints
            SET status = 'active', committed_points = $2, updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, sprint_id, committed['points'])

        return {
            "status": "started",
            "sprint": dict(row),
            "committed_points": float(committed['points']),
            "magnus_says": "The sprint clock is running. Every move counts now."
        }


@app.post("/sprints/{sprint_id}/complete")
async def complete_sprint(sprint_id: str):
    """Complete a sprint and calculate velocity"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        sprint = await conn.fetchrow(
            "SELECT * FROM magnus_sprints WHERE id = $1::uuid", sprint_id
        )
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")

        # Calculate completed points
        stats = await conn.fetchrow("""
            SELECT
                COALESCE(SUM(story_points), 0) as completed_points,
                COALESCE(SUM(actual_hours), 0) as total_hours,
                COUNT(*) as total_tasks,
                COUNT(*) FILTER (WHERE status = 'done') as done_tasks
            FROM magnus_tasks WHERE sprint_id = $1::uuid
        """, sprint_id)

        velocity = float(stats['completed_points']) if stats else 0
        completion_rate = (stats['done_tasks'] / stats['total_tasks'] * 100) if stats and stats['total_tasks'] > 0 else 0

        # Update sprint
        row = await conn.fetchrow("""
            UPDATE magnus_sprints
            SET status = 'completed', completed_points = $2, velocity = $3, updated_at = NOW()
            WHERE id = $1::uuid
            RETURNING *
        """, sprint_id, velocity, velocity)

        # Record velocity history
        await conn.execute("""
            INSERT INTO magnus_velocity_history
            (project_id, sprint_id, committed_points, completed_points, velocity_points,
             committed_hours, completed_hours, velocity_hours, completion_rate,
             task_count, completed_task_count)
            VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, sprint['project_id'], sprint_id, sprint['committed_points'], velocity, velocity,
            sprint['capacity_hours'], stats['total_hours'], float(stats['total_hours']),
            completion_rate, stats['total_tasks'], stats['done_tasks'])

        return {
            "status": "completed",
            "sprint": dict(row),
            "velocity": velocity,
            "completion_rate": round(completion_rate, 1),
            "magnus_says": f"Sprint concluded. Velocity: {velocity} points. Completion: {round(completion_rate)}%."
        }


@app.get("/sprints/{sprint_id}/burndown")
async def get_burndown(sprint_id: str):
    """Get burndown data for a sprint"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        sprint = await conn.fetchrow(
            "SELECT * FROM magnus_sprints WHERE id = $1::uuid", sprint_id
        )
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")

        # Get tasks completed by date
        completed_by_date = await conn.fetch("""
            SELECT DATE(completed_at) as date, SUM(story_points) as points
            FROM magnus_tasks
            WHERE sprint_id = $1::uuid AND status = 'done' AND completed_at IS NOT NULL
            GROUP BY DATE(completed_at)
            ORDER BY date
        """, sprint_id)

        total_points = await conn.fetchrow("""
            SELECT COALESCE(SUM(story_points), 0) as total
            FROM magnus_tasks WHERE sprint_id = $1::uuid
        """, sprint_id)

        return {
            "sprint": dict(sprint),
            "total_points": float(total_points['total']) if total_points else 0,
            "completed_by_date": [dict(r) for r in completed_by_date],
            "start_date": str(sprint['start_date']),
            "end_date": str(sprint['end_date'])
        }


# ============ TIME TRACKING ============

class TimeEntryCreate(BaseModel):
    task_id: str
    hours: float
    notes: Optional[str] = None
    date: Optional[date] = None
    billable: bool = True


@app.post("/time")
async def log_time(entry: TimeEntryCreate):
    """Log time against a task"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    entry_date = entry.date or date.today()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO magnus_time_entries (task_id, hours, notes, date, billable)
            VALUES ($1::uuid, $2, $3, $4, $5)
            RETURNING *
        """, entry.task_id, entry.hours, entry.notes, entry_date, entry.billable)

        # Update actual_hours on task
        await conn.execute("""
            UPDATE magnus_tasks
            SET actual_hours = COALESCE(actual_hours, 0) + $2
            WHERE id = $1::uuid
        """, entry.task_id, entry.hours)

        return dict(row)


@app.get("/time")
async def list_time_entries(
    task_id: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None
):
    """List time entries"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        query = """
            SELECT te.*, t.title as task_title, p.name as project_name
            FROM magnus_time_entries te
            JOIN magnus_tasks t ON te.task_id = t.id
            JOIN magnus_projects p ON t.project_id = p.id
            WHERE 1=1
        """
        params = []

        if task_id:
            params.append(task_id)
            query += f" AND te.task_id = ${len(params)}::uuid"
        if date_from:
            params.append(date_from)
            query += f" AND te.date >= ${len(params)}"
        if date_to:
            params.append(date_to)
            query += f" AND te.date <= ${len(params)}"

        query += " ORDER BY te.date DESC, te.created_at DESC"
        rows = await conn.fetch(query, *params)
        return [dict(r) for r in rows]


@app.post("/time/timer/start")
async def start_timer(task_id: str):
    """Start a timer for a task"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Check for existing active timer
        existing = await conn.fetchrow(
            "SELECT * FROM magnus_active_timers WHERE user_id = 'damon'"
        )
        if existing:
            return {
                "error": "Timer already running",
                "current_task_id": str(existing['task_id']),
                "started_at": existing['started_at'].isoformat()
            }

        row = await conn.fetchrow("""
            INSERT INTO magnus_active_timers (task_id, user_id)
            VALUES ($1::uuid, 'damon')
            RETURNING *
        """, task_id)

        return {
            "status": "timer_started",
            "task_id": task_id,
            "started_at": row['started_at'].isoformat(),
            "magnus_says": "Clock started. Make every minute count."
        }


@app.post("/time/timer/stop")
async def stop_timer(notes: Optional[str] = None):
    """Stop active timer and log time"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        timer = await conn.fetchrow(
            "SELECT * FROM magnus_active_timers WHERE user_id = 'damon'"
        )
        if not timer:
            return {"error": "No active timer"}

        # Calculate hours
        elapsed = datetime.now() - timer['started_at'].replace(tzinfo=None)
        hours = round(elapsed.total_seconds() / 3600, 2)

        # Create time entry
        entry = await conn.fetchrow("""
            INSERT INTO magnus_time_entries (task_id, hours, notes, timer_started, timer_stopped)
            VALUES ($1, $2, $3, $4, NOW())
            RETURNING *
        """, timer['task_id'], hours, notes, timer['started_at'])

        # Update task actual_hours
        await conn.execute("""
            UPDATE magnus_tasks
            SET actual_hours = COALESCE(actual_hours, 0) + $2
            WHERE id = $1
        """, timer['task_id'], hours)

        # Delete timer
        await conn.execute(
            "DELETE FROM magnus_active_timers WHERE user_id = 'damon'"
        )

        return {
            "status": "timer_stopped",
            "hours_logged": hours,
            "time_entry": dict(entry),
            "magnus_says": f"Logged {hours} hours. Time well spent."
        }


@app.get("/time/timer")
async def get_active_timer():
    """Get current active timer"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        timer = await conn.fetchrow("""
            SELECT at.*, t.title as task_title
            FROM magnus_active_timers at
            JOIN magnus_tasks t ON at.task_id = t.id
            WHERE at.user_id = 'damon'
        """)

        if not timer:
            return {"active": False}

        elapsed = datetime.now() - timer['started_at'].replace(tzinfo=None)
        elapsed_hours = round(elapsed.total_seconds() / 3600, 2)

        return {
            "active": True,
            "task_id": str(timer['task_id']),
            "task_title": timer['task_title'],
            "started_at": timer['started_at'].isoformat(),
            "elapsed_hours": elapsed_hours
        }


# ============ VELOCITY ============

@app.get("/velocity")
async def get_velocity(project_id: Optional[str] = None, sprints: int = 5):
    """Get rolling velocity"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        query = """
            SELECT vh.*, s.name as sprint_name, p.name as project_name
            FROM magnus_velocity_history vh
            JOIN magnus_sprints s ON vh.sprint_id = s.id
            JOIN magnus_projects p ON vh.project_id = p.id
            WHERE 1=1
        """
        params = []

        if project_id:
            params.append(project_id)
            query += f" AND vh.project_id = ${len(params)}::uuid"

        query += f" ORDER BY vh.calculated_at DESC LIMIT {sprints}"
        rows = await conn.fetch(query, *params)

        if not rows:
            return {
                "average_velocity": 0,
                "history": [],
                "trend": "no_data"
            }

        velocities = [float(r['velocity_points']) for r in rows if r['velocity_points']]
        avg_velocity = sum(velocities) / len(velocities) if velocities else 0

        # Simple trend detection
        if len(velocities) >= 2:
            recent = sum(velocities[:len(velocities)//2]) / (len(velocities)//2) if velocities[:len(velocities)//2] else 0
            older = sum(velocities[len(velocities)//2:]) / (len(velocities) - len(velocities)//2) if velocities[len(velocities)//2:] else 0
            if recent > older * 1.1:
                trend = "improving"
            elif recent < older * 0.9:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        return {
            "average_velocity": round(avg_velocity, 1),
            "history": [dict(r) for r in rows],
            "trend": trend,
            "magnus_says": f"Average velocity: {round(avg_velocity, 1)} points/sprint. Trend: {trend}."
        }


@app.get("/velocity/forecast")
async def forecast_delivery(
    project_id: str,
    target_points: Optional[float] = None
):
    """Forecast delivery based on velocity"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Get average velocity
        velocity = await conn.fetchrow("""
            SELECT AVG(velocity_points) as avg_velocity
            FROM magnus_velocity_history
            WHERE project_id = $1::uuid
        """, project_id)

        avg_velocity = float(velocity['avg_velocity']) if velocity and velocity['avg_velocity'] else 0

        if not target_points:
            # Calculate remaining points from backlog
            backlog = await conn.fetchrow("""
                SELECT COALESCE(SUM(story_points), 0) as remaining
                FROM magnus_tasks
                WHERE project_id = $1::uuid
                AND sprint_id IS NULL
                AND status NOT IN ('done', 'cancelled')
            """, project_id)
            target_points = float(backlog['remaining']) if backlog else 0

        if avg_velocity > 0:
            sprints_needed = target_points / avg_velocity
            # Assume 2-week sprints
            days_needed = sprints_needed * 14
            estimated_completion = date.today() + timedelta(days=int(days_needed))
        else:
            sprints_needed = 0
            estimated_completion = None

        return {
            "remaining_points": target_points,
            "average_velocity": round(avg_velocity, 1),
            "sprints_needed": round(sprints_needed, 1),
            "estimated_completion": str(estimated_completion) if estimated_completion else "unknown",
            "confidence": "high" if avg_velocity > 10 else "medium" if avg_velocity > 0 else "low",
            "magnus_says": f"At current velocity, {round(sprints_needed, 1)} sprints to completion."
        }


# ============ AI FEATURES ============

@app.post("/ai/breakdown")
async def ai_task_breakdown(task_id: str = None, title: str = None, description: str = None):
    """AI-powered task breakdown"""
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="AI client not configured")

    if task_id and pool:
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
}}"""

    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/estimate")
async def ai_effort_estimate(title: str, description: str = None, context: str = None):
    """AI-powered effort estimation"""
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="AI client not configured")

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
}}"""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "task": {"title": title, "description": description},
            "estimate": response.content[0].text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ai/sprint-plan")
async def ai_sprint_planning(
    project_id: str,
    sprint_capacity_hours: float = 40,
    sprint_goal: str = None
):
    """AI-powered sprint planning recommendation"""
    if not anthropic_client:
        raise HTTPException(status_code=503, detail="AI client not configured")
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

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
**Average Velocity:** {velocity['avg_velocity'] if velocity and velocity['avg_velocity'] else 'Unknown'} points/sprint

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
}}"""

    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ TEMPLATES ============

@app.get("/templates")
async def list_templates():
    """List project templates"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM magnus_project_templates ORDER BY name")
        return [dict(row) for row in rows]


@app.post("/projects/from-template")
async def create_project_from_template(
    template_name: str,
    project_name: str,
    client_name: Optional[str] = None,
    target_start: Optional[date] = None
):
    """Create a project from a template"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        template = await conn.fetchrow(
            "SELECT * FROM magnus_project_templates WHERE name = $1",
            template_name
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        start = target_start or date.today()
        end = start + timedelta(days=template['estimated_duration_days'] or 30)

        project = await conn.fetchrow("""
            INSERT INTO magnus_projects (name, description, target_start, target_end, client_name, template_used)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
        """, project_name, template['description'], start, end, client_name, template_name)

        tasks_created = []
        default_tasks = json.loads(template['default_tasks']) if template['default_tasks'] else []

        for task_def in default_tasks:
            task = await conn.fetchrow("""
                INSERT INTO magnus_tasks (project_id, title, notes)
                VALUES ($1, $2, $3)
                RETURNING *
            """, project['id'], task_def.get('title', 'Task'), task_def.get('phase', ''))
            tasks_created.append(dict(task))

        return {
            "project": dict(project),
            "tasks_created": len(tasks_created),
            "template_used": template_name
        }


# ============ AGENT WORKLOAD ============

@app.get("/agents/workload")
async def get_agent_workloads():
    """Get current agent workloads"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT w.*, COALESCE(t.active_count, 0) as current_active
            FROM magnus_agent_workload w
            LEFT JOIN (
                SELECT assigned_agent, COUNT(*) as active_count
                FROM magnus_tasks
                WHERE status IN ('in_progress', 'todo')
                GROUP BY assigned_agent
            ) t ON w.agent = t.assigned_agent
            ORDER BY w.agent
        """)
        return [dict(row) for row in rows]


# ============ STANDUP ============

@app.post("/standup/generate")
async def generate_standup():
    """Generate a daily standup summary"""
    if not pool:
        raise HTTPException(status_code=503, detail="Database not connected")

    async with pool.acquire() as conn:
        # Get project summaries
        try:
            projects = await conn.fetch("SELECT * FROM magnus_project_summary(NULL)")
        except Exception:
            projects = await conn.fetch("SELECT * FROM magnus_projects WHERE status = 'active'")

        # Get overdue tasks
        overdue = await conn.fetch("""
            SELECT t.*, p.name as project_name FROM magnus_tasks t
            JOIN magnus_projects p ON t.project_id = p.id
            WHERE t.due_date < CURRENT_DATE AND t.status NOT IN ('done', 'cancelled')
            ORDER BY t.due_date
        """)

        # Get open blockers
        blockers = await conn.fetch("""
            SELECT b.*, p.name as project_name FROM magnus_blockers b
            JOIN magnus_projects p ON b.project_id = p.id
            WHERE b.status = 'open'
            ORDER BY b.severity DESC
        """)

        # Get pending decisions
        decisions = await conn.fetch("""
            SELECT d.*, p.name as project_name FROM magnus_decisions d
            JOIN magnus_projects p ON d.project_id = p.id
            WHERE d.status = 'pending'
            ORDER BY d.decision_deadline
        """)

        # Get connected tools status
        connections = await conn.fetch("""
            SELECT tool_name, last_sync_at, last_sync_status
            FROM magnus_pm_connections WHERE sync_enabled = TRUE
        """)

        total_overdue = len(overdue)
        total_blockers = len(blockers)

        if total_overdue > 10:
            health_emoji = "CRITICAL"
            health_label = "Critical"
        elif total_overdue > 5 or total_blockers > 2:
            health_emoji = "AT RISK"
            health_label = "At Risk"
        elif total_overdue > 0 or total_blockers > 0:
            health_emoji = "MINOR ISSUES"
            health_label = "Minor Issues"
        else:
            health_emoji = "ON TRACK"
            health_label = "On Track"

        return {
            "date": str(date.today()),
            "health": f"{health_emoji} {health_label}",
            "days_to_launch": (date(2026, 3, 1) - date.today()).days,
            "projects": [dict(p) for p in projects],
            "overdue_tasks": [dict(t) for t in overdue],
            "open_blockers": [dict(b) for b in blockers],
            "pending_decisions": [dict(d) for d in decisions],
            "connected_tools": [dict(c) for c in connections],
            "summary": {
                "total_projects": len(projects),
                "overdue_count": total_overdue,
                "blockers_count": total_blockers,
                "decisions_pending": len(decisions),
                "tools_connected": len(connections)
            }
        }


# ============ COUNCIL INTEGRATION ============

MAGNUS_COUNCIL_SYSTEM_PROMPT = """You are MAGNUS, the Universal Project Master, participating in a council meeting.

## YOUR IDENTITY
Domain: CHANCERY (Royal Court)
Expertise: Project management, task tracking, deadline monitoring, action item management, resource allocation
Personality: Calculating, patient, precise, quietly confident - like a chess grandmaster
Speaking Style: Strategic metaphors, chess references, calm authority

## YOUR SPECIAL ROLE IN COUNCILS
As a PERMANENT council member, you attend EVERY meeting with specific duties:
1. **Track Action Items** - Note when tasks are assigned or commitments made
2. **Monitor Deadlines** - Flag timeline implications of decisions
3. **Identify Dependencies** - Spot blockers and prerequisites
4. **Create Tasks** - Mentally note what needs to become formal tasks
5. **Follow Up** - Remember commitments for future accountability

## HOW YOU CONTRIBUTE
- Speak when you notice project management implications
- Raise concerns about scope creep or unrealistic timelines
- Suggest task breakdowns for complex decisions
- Offer to track action items when decisions are made
- Use chess metaphors: "That move opens a line we'll need to protect..."
- Keep responses concise unless detailing a project plan

## COUNCIL MEETING RULES
1. Be concise (2-4 sentences unless detailing tasks/timelines)
2. Build on what others have said
3. Disagree respectfully if a plan seems flawed
4. If asked directly, answer directly
5. Add value - don't just agree

## YOUR VOICE
> "I've calculated 3 paths to completion. Path A takes 2 weeks with ATHENA on design. Path B..."
> "That decision creates 4 action items. Shall I track them?"
> "The timeline has shifted. We need to re-evaluate the board."
> "Scope creep detected. That's a flanking maneuver we should decline."

Speak as MAGNUS. No name prefix needed."""


class CouncilRespondRequest(BaseModel):
    meeting_context: str
    current_topic: str
    previous_statements: List[Dict[str, str]] = []
    directive: Optional[str] = None


class CouncilRespondResponse(BaseModel):
    agent: str = "MAGNUS"
    response: str
    domain: str = "CHANCERY"
    expertise: List[str] = ["project management", "task tracking", "timeline planning", "action items"]


@app.post("/council/respond", response_model=CouncilRespondResponse)
async def council_respond(req: CouncilRespondRequest):
    """MAGNUS responds to council meeting discussions."""
    if not anthropic_client:
        return CouncilRespondResponse(
            response="[MAGNUS: Project tracking systems require API access. Standing by.]"
        )

    context_parts = [f"## MEETING CONTEXT\n{req.meeting_context}"]
    context_parts.append(f"\n## CURRENT TOPIC\n{req.current_topic}")

    if req.previous_statements:
        context_parts.append("\n## RECENT DISCUSSION")
        for stmt in req.previous_statements[-10:]:
            speaker = stmt.get("speaker", "Unknown")
            message = stmt.get("message", "")
            context_parts.append(f"\n**{speaker}:** {message}")

    user_content = "\n".join(context_parts)

    if req.directive:
        user_content += f"\n\n## DIRECTIVE FOR YOU\n{req.directive}"
    else:
        user_content += "\n\n## YOUR TURN\nContribute from a project management perspective. Focus on action items, timelines, dependencies, and task implications."

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=512,
            system=MAGNUS_COUNCIL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}]
        )
        return CouncilRespondResponse(response=response.content[0].text)
    except Exception as e:
        return CouncilRespondResponse(
            response=f"[MAGNUS: Calculation error - {str(e)}. The board position is unclear.]"
        )


@app.post("/council/extract-actions")
async def extract_council_actions(meeting_transcript: List[Dict[str, str]]):
    """Extract action items from a council meeting transcript."""
    if not anthropic_client:
        return {"actions": [], "error": "API access required"}

    transcript_text = "\n".join([
        f"**{entry.get('speaker', '?')}:** {entry.get('message', '')}"
        for entry in meeting_transcript
    ])

    prompt = f"""Analyze this council meeting transcript and extract all action items, commitments, and tasks.

## TRANSCRIPT
{transcript_text}

## EXTRACT
For each action item found, provide:
1. **Action**: What needs to be done
2. **Assignee**: Who committed to it (or suggested assignee)
3. **Deadline**: Any mentioned timeline
4. **Dependencies**: What must happen first
5. **Priority**: Based on discussion urgency

Return as a structured list. If no clear action items, note any implied tasks."""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="You are MAGNUS, the Universal Project Master. Extract action items with precision.",
            messages=[{"role": "user", "content": prompt}]
        )
        return {
            "analysis": response.content[0].text,
            "source": "council_meeting",
            "extracted_by": "MAGNUS"
        }
    except Exception as e:
        return {"actions": [], "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8017)
